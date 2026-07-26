"""
server.py — FastMCP server exposing LocalFind as MCP tools.

DESIGN PHILOSOPHY:
This server is environment-agnostic. It doesn't know whether it's
being called by Claude Desktop or the local Ollama agent. It just
returns data cleanly and lets each client handle it appropriately.

For images specifically:
- The server returns the FILE PATH only (not bytes, not base64,
  not a description). This is intentional — see view_image below.
- Claude Desktop uses its own Filesystem connector to fetch the
  actual file. The server tells Claude to do this if it needs the image.
- The Ollama agent (agent_service.py) reads the path from the tool
  result, loads the file itself, and passes base64 to Ollama directly.

For text and audio:
- Returned as plain text. Both Claude Desktop and the local agent
  handle plain text identically, so no environment-specific logic needed.

TRANSPORT:
Runs over stdio, spawned as a subprocess by agent_service.py (local agent)
or registered in claude_desktop_config.json (Claude Desktop).

Run with:
  python server.py
"""
import os
import httpx
from pathlib import Path
from mcp.server.fastmcp import FastMCP

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

mcp = FastMCP("localfind_server")


# ── search_documents ────────────────────────────────────────────────────────

@mcp.tool()
async def search_documents(query: str, top_k: int = 2,
                           modalities: str = "text,image,audio,video") -> dict:
    """
    Search indexed documents by semantic similarity across text, images, audio, and video.
    Video results are surfaced as keyframe images — the agent receives the frame path
    and can call view_image on it exactly like any other image.

    WHY THIS RETURNS IMAGE PATHS INSTEAD OF IMAGE DATA:
    Returning raw image bytes or base64 through MCP tool results is unreliable:
    - Claude Desktop's chat UI doesn't consistently render MCP ImageContent blocks.
    - The openai-agents SDK (used by the local agent) has an unfixed bug where
      MCP ImageContent blocks are passed to Ollama as plain text strings, not
      as vision messages. Ollama never sees the actual pixels.
    
    So instead we return the file path. Each client then handles it the right way:
    - Claude Desktop: calls copy_file_user_to_claude (Filesystem connector)
    - Local agent: reads the file itself and passes base64 to Ollama natively.
    
    Args:
        query: Natural language query — what to search for in your documents.
               Examples: 'quarterly revenue', 'machine learning', 'sunset beach'
        top_k: Number of results per modality (default 2, max 5)
        modalities: Comma-separated list — "text", "image", "audio", "video".
                    Default is all four. The agent's system prompt sets the
                    session scope; pass it through unchanged from there.
    
    Returns:
        Dict with separate lists for text, image, and audio results.
        Each result includes text snippet, score, file info, and metadata.
        Images and video keyframes include file paths — use view_image(file_path)
        to see the visual content. Video frame entries have "[video frame]" in the
        file_name so you know they came from a video.
        Audio includes transcript text (not actual audio playback).
    """
    top_k = min(top_k, 5)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{BACKEND_URL}/search",
            params={
                "q": query,
                "top_k": top_k,
                "modalities": modalities,
                # Visuals-only for video so every result is a real frame the model can see.
                "include_video_speech": "false",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", {})

        # Map video results to image results using the cached keyframe path.
        # The agent treats them identically — it calls view_image on the frame path.
        image_results = list(results.get("image", [])[:top_k])
        for hit in results.get("video", []):
            frame_path = (hit.get("metadata") or {}).get("frame_path")
            if frame_path:
                image_results.append({
                    **hit,
                    "file_path": frame_path,
                    "file_name": f"[video frame] {hit.get('file_name', '')}",
                })
        image_results = image_results[:top_k]

        return {
            "query": data.get("query", query),
            "text_results": results.get("text", [])[:top_k],
            "image_results": image_results,
            "audio_results": results.get("audio", [])[:top_k],
            "total_results": {
                "text": len(results.get("text", [])),
                "images": len(image_results),
                "audio": len(results.get("audio", [])),
            },
        }


# ── view_image ──────────────────────────────────────────────────────────────

@mcp.tool()
async def view_image(file_path: str, context: str = "") -> str:
    """
    Returns the file path of an image along with instructions for how to view it.
    
    WHY THIS DOESN'T RETURN IMAGE BYTES OR CALL OLLAMA:
    We used to try two approaches here that both failed:
    
    1. Returning base64 / MCP ImageContent:
       - Claude Desktop's UI doesn't reliably render MCP image blocks.
       - The openai-agents SDK strips image content before it reaches Ollama,
         so Ollama receives a text string of garbled base64, not an image.
    
    2. Calling Ollama from inside this tool to get a description:
       - This only works for the local agent, not Claude Desktop.
       - It couples the MCP server to Ollama's availability and model config.
       - Claude Desktop can see images natively and is better at it — making
         Ollama describe the image for Claude to then read is wasteful and wrong.
    
    The correct approach is to return the path and let each client handle it:
    
    FOR CLAUDE DESKTOP:
    Claude is told (via these instructions) to use the Filesystem connector's
    copy_file_user_to_claude tool. That tool has privileged access to Claude's
    sandbox (/mnt/user-data/uploads/) which is the only path Claude can see
    natively. Our MCP server cannot write to that path — it only exists inside
    Claude's cloud container, not on the user's local machine.
    
    If copy_file_user_to_claude is not available (Filesystem connector is off),
    Claude tells the user to enable it in Claude Desktop → Settings → Connectors.
    
    FOR THE LOCAL AGENT (agent_service.py):
    agent_service.py intercepts image paths from tool results, reads the file
    from disk, base64-encodes it, and posts it directly to Ollama's /api/chat
    with the "images": [base64] field. Ollama's native API handles this correctly.
    The openai-agents SDK is bypassed entirely for images.
    
    Args:
        file_path: Absolute path to the image file (from search_documents results).
        context:   Optional hint about what to look for, e.g. "screen time data".
    
    Returns:
        The file path + instructions for the client on how to load the image.
        The IMAGE_PATH: prefix is used by agent_service.py to detect image results.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found at {file_path}"
    
    ext = path.suffix.lower()
    supported = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
    if ext not in supported:
        return f"Error: Unsupported image format '{ext}' at {file_path}"
    
    # We return a structured string with a known prefix so agent_service.py
    # can reliably detect this is an image result and extract the path.
    result = (
        f"IMAGE_PATH: {file_path}\n"
        f"To view this image:\n"
        f"  - If you have the Filesystem connector: call copy_file_user_to_claude(path='{file_path}')\n"
        f"  - If the Filesystem connector is not enabled: tell the user to enable it in\n"
        f"    Claude Desktop → Settings → Connectors → Filesystem, then try again.\n"
    )
    
    if context:
        result += f"Context for analysis: {context}\n"
    
    return result


# ── list_indexed_folders ────────────────────────────────────────────────────

@mcp.tool()
async def list_indexed_folders() -> list[dict]:
    """
    List all folders currently tracked and indexed by LocalFind.
    
    Returns:
        List of folder dicts with path, file count, chunk count, and added_at.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BACKEND_URL}/folders")
        resp.raise_for_status()
        return resp.json()


# ── get_index_stats ─────────────────────────────────────────────────────────

@mcp.tool()
async def get_index_stats() -> dict:
    """
    Get global statistics about the LocalFind index.
    
    Returns:
        Dict with total_folders, total_files, total_chunks, last_sync.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BACKEND_URL}/stats")
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    mcp.run(transport="stdio")
