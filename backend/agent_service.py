"""
agent_service.py — Agent service using openai-agents SDK with MCP tools.

DESIGN PHILOSOPHY:
The agent (an Ollama chat/vision model, Gemma by default) decides when to search using MCP tools.
For text and audio results, tool output flows through normally.
For image results, we intercept and handle them ourselves — because the
openai-agents SDK has an unfixed bug where MCP image content never reaches
Ollama in a usable form. See _handle_image_results() for full explanation.
"""
import asyncio
import sys
import os
import re
import base64
import json
import httpx
import logging
from pathlib import Path
from typing import AsyncGenerator

from agents import Agent, Runner, OpenAIChatCompletionsModel
from agents.mcp import MCPServerStdio
from openai import AsyncOpenAI

# ── Logging ──────────────────────────────────────────────────────────────────
# Shared config (see logging_config.py): consistent format, stdout + rotating
# file, noisy libraries capped at WARNING. setup_logging() is idempotent, so
# calling it here keeps the agent loggable even when imported on its own.
from logging_config import setup_logging, get_logger

setup_logging()
log = get_logger("agent")

from config import OLLAMA_BASE_URL, OLLAMA_CHAT_URL, AGENT_MODEL
from parsers import get_image_metadata, get_audio_metadata

MCP_SERVER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "mcp_server", "server.py"
)

# The prefix our server.py puts on image results so we can detect them reliably.
# Using a prefix instead of regex on file extensions because the agent might
# mention image paths in other contexts (e.g. "I searched for /photos/...").
IMAGE_PATH_PREFIX = "IMAGE_PATH: "

# ── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are DocSearch, a friendly conversational assistant with document search capabilities.

CRITICAL RULE - When NOT to Search:
- If the user just says "hi", "hello", "hey", "sup", or any greeting → JUST GREET THEM BACK, DO NOT USE TOOLS
- If the user asks "how are you?" or "what's up?" → JUST RESPOND NORMALLY, DO NOT USE TOOLS
- If the user asks "what can you do?" → EXPLAIN YOUR CAPABILITIES, DO NOT USE TOOLS
- For general conversation or small talk → JUST CHAT, DO NOT USE TOOLS

ONLY Use search_documents When:
- User explicitly asks to "find", "search", "show me", "look for" documents
- User asks "what's in my files about X?"
- User asks "do I have any documents about Y?"
- User clearly wants information FROM their indexed documents

You have access to these tools:
search_documents  — searches text, images, audio, and video in your indexed files
view_image        — MUST be called for every image or video frame path found in search results

Video results appear as image entries with "[video frame]" in the file name.
Treat them exactly like images — call view_image on the frame path to see what's on screen.

MANDATORY IMAGE/FRAME RULE — This is non-negotiable:
If search_documents returns ANY image results (files ending in .jpg, .jpeg, .png, .gif etc.),
including video keyframes, you MUST call view_image(file_path) for EACH one before writing
your final response.

Do NOT skip this step. Do NOT say you "cannot see" the image or frame. Do NOT say it
is "queued for viewing". The system handles the actual image analysis automatically
when you call view_image — your job is just to call it. Always call it.

When you DO search:
1. Call search_documents(query, top_k=2)
2. For EVERY image or video frame path in the results → call view_image(file_path) immediately
3. After all view_image calls are done → write your final summary
4. Cite file names (and for video frames, mention which video they came from) where you found information

Default Behavior:
- Be friendly and conversational
- Answer general questions directly without tools
- Only search when the user is CLEARLY asking about their files
- When in doubt, DON'T search — just chat normally"""


# ── Backend singletons (MCP subprocess + Ollama model wrapper) ──────────────
# The Agent object itself is cheap and created per-request so the system prompt
# (which carries the per-session modalities scope) can vary without restarting
# the expensive MCP subprocess.

_mcp_server = None
_model      = None


async def _ensure_backend_started():
    """Start MCP subprocess and Ollama model wrapper (idempotent singleton)."""
    global _mcp_server, _model
    if _mcp_server is not None:
        return

    log.info("_ensure_backend_started: starting up — model=%s", AGENT_MODEL)
    log.debug("_ensure_backend_started: MCP server path = %s", os.path.abspath(MCP_SERVER_PATH))

    ollama_client = AsyncOpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
    )
    _model = OpenAIChatCompletionsModel(
        model=AGENT_MODEL,
        openai_client=ollama_client,
    )

    # MCP server runs as a subprocess communicating over stdio.
    _mcp_server = MCPServerStdio(
        params={
            "command": sys.executable,
            "args": [os.path.abspath(MCP_SERVER_PATH)],
        },
        client_session_timeout_seconds=60,
    )
    log.info("_ensure_backend_started: starting MCP server subprocess...")
    await _mcp_server.__aenter__()
    log.info("_ensure_backend_started: ✅ ready")


def _build_agent(search_modalities: str) -> "Agent":
    """Create a lightweight Agent with the given search scope baked into its instructions."""
    instructions = (
        SYSTEM_PROMPT
        + f"\n\nSEARCH SCOPE FOR THIS SESSION: When calling search_documents, "
        f"ALWAYS pass modalities='{search_modalities}'. Never deviate from this value."
    )
    return Agent(
        name="DocSearch",
        instructions=instructions,
        model=_model,
        mcp_servers=[_mcp_server],
    )


# Keep the old name as a shim so any external callers still work.
async def initialize_agent():
    await _ensure_backend_started()
    return _build_agent("text,image,audio")


# ── Image handling ───────────────────────────────────────────────────────────

async def _send_image_to_ollama(file_path: str, user_query: str) -> str:
    """
    Send an image directly to Ollama's native /api/chat and get a description.
    
    WHY WE BYPASS THE openai-agents SDK FOR IMAGES:
    The SDK wraps Ollama via the OpenAI-compatible endpoint (/v1/chat/completions).
    When an MCP tool returns image content, the SDK is supposed to convert it into
    an OpenAI vision message (type: "image_url" with a data: URI). It doesn't.
    Instead it passes the image block as a plain text string, so Ollama receives
    garbled text and never sees any pixels. This is a known open bug in the SDK.
    
    WHY WE USE /api/chat AND NOT /v1/chat/completions:
    Ollama's native /api/chat accepts an "images" field directly on the message
    object — a list of raw base64 strings. This is simpler and more reliable than
    the OpenAI-compat format which wraps the base64 in a data: URI inside
    image_url. Both work in theory, but the native API is what Ollama was built
    around and is less likely to have edge-case parsing issues.
    
    WHY WE READ THE FILE HERE INSTEAD OF IN server.py:
    server.py is environment-agnostic. It doesn't know if it's running under
    Claude Desktop or the local agent. Reading the file and calling Ollama from
    inside server.py would couple the MCP server to Ollama's availability, which
    breaks Claude Desktop usage where Ollama is irrelevant.
    
    Instead, server.py returns the path and this function does the file reading.
    
    Args:
        file_path:  Absolute path to the image on disk.
        user_query: The original user question, used as context so Ollama knows
                    what aspect of the image to focus on.
    
    Returns:
        Plain text description of the image from Ollama, or an error string.
    """
    path = Path(file_path)
    log.info("_send_image_to_ollama: processing image — %s", path.name)
    
    if not path.exists():
        log.error("_send_image_to_ollama: file not found — %s", file_path)
        return f"[Image not found: {file_path}]"
    
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
            image_b64 = base64.b64encode(raw).decode("utf-8")
        
        log.debug(
            "_send_image_to_ollama: read %d bytes from %s, base64 length = %d",
            len(raw), path.name, len(image_b64),
        )
    except Exception as e:
        log.error("_send_image_to_ollama: could not read file %s — %s", file_path, e)
        return f"[Could not read image {path.name}: {e}]"
    
    payload = {
        "model": AGENT_MODEL,
        "messages": [{
            "role": "user",
            # We include the user's query so Ollama focuses on what matters.
            # "Describe this image" alone would give generic output.
            "content": (
                f"The user asked: '{user_query}'\n"
                f"Describe what you see in this image and how it relates to their question."
            ),
            "images": [image_b64],  # Ollama native format — raw base64 list
        }],
        "stream": False,
    }
    
    log.info(
        "_send_image_to_ollama: posting to %s — model=%s image=%s",
        OLLAMA_CHAT_URL, AGENT_MODEL, path.name,
    )
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(OLLAMA_CHAT_URL, json=payload)
            log.debug(
                "_send_image_to_ollama: response status=%d for %s",
                resp.status_code, path.name,
            )
            resp.raise_for_status()
            description = resp.json()["message"]["content"]
            log.info(
                "_send_image_to_ollama: ✅ got description for %s (%d chars)",
                path.name, len(description),
            )
            return description
    except httpx.HTTPStatusError as e:
        log.error(
            "_send_image_to_ollama: HTTP %d from Ollama for %s — response body: %s",
            e.response.status_code, path.name, e.response.text[:500],
        )
        return (
            f"[Ollama vision error for {path.name}: HTTP {e.response.status_code}. "
            f"Make sure {AGENT_MODEL} supports vision — run: ollama show {AGENT_MODEL}]"
        )
    except Exception as e:
        log.error("_send_image_to_ollama: unexpected error for %s — %s", path.name, e)
        return f"[Ollama vision error for {path.name}: {e}]"


# Image file extensions we recognise for the search_documents fallback
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

PATH_EXTENSION_PATTERN = r"(?:jpg|jpeg|png|gif|bmp|webp|pdf|docx|txt|md|mp3|wav|flac|m4a|ogg|aac|mp4)"
ABSOLUTE_PATH_PATTERN = re.compile(
    rf'((?:[A-Za-z]:[\\/]|/)[^\s\'"<>\]\)\r\n]+\.{PATH_EXTENSION_PATTERN})',
    re.IGNORECASE
)


def _texts_from_tool_output(output) -> list[str]:
    """
    Flatten a tool output (string, list of blocks, or nested structure)
    into a list of plain text strings.
    
    WHY THIS IS A SEPARATE HELPER:
    The openai-agents SDK doesn't guarantee a single output shape. Depending
    on the Ollama model and SDK version, tool outputs arrive as:
    - A plain string
    - A list of {"type": "text", "text": "..."} dicts
    - A list of plain strings
    - Occasionally nested lists
    
    Centralising the flattening logic means we don't repeat it in two places.
    """
    if isinstance(output, str):
        return [output]
    
    if isinstance(output, list):
        texts = []
        for block in output:
            if isinstance(block, str):
                texts.append(block)
            elif isinstance(block, dict):
                texts.append(block.get("text", ""))
        return texts
    
    log.debug("_texts_from_tool_output: unrecognised output type %s", type(output))
    return []


def _normalise_tool_path(raw_path: str) -> str:
    """Clean up absolute paths extracted from tool output across Unix and Windows."""
    path = raw_path.strip().strip("\"'").rstrip(".,;:")
    path = path.replace("\\\\", "\\")
    return os.path.normpath(path)


def _find_paths_in_text(text: str, allowed_exts: set[str] | None = None) -> list[str]:
    """Extract absolute file paths from tool text, supporting Unix and Windows paths."""
    paths = []
    seen = set()

    for match in ABSOLUTE_PATH_PATTERN.finditer(text):
        candidate = _normalise_tool_path(match.group(1))
        ext = Path(candidate).suffix.lower()
        if allowed_exts and ext not in allowed_exts:
            continue
        if candidate not in seen:
            seen.add(candidate)
            paths.append(candidate)

    return paths


def _extract_image_paths_from_tool_results(result) -> list[str]:
    """
    Pull image file paths out of MCP tool results.
    
    TWO-PASS STRATEGY — WHY:
    The ideal flow is: agent calls search_documents → sees image paths →
    calls view_image for each one → we read IMAGE_PATH: lines from those results.
    
    But the agent model (and LLMs in general) sometimes skip the view_image call,
    deciding on their own that they "can't view images". When that happens,
    the IMAGE_PATH: lines never appear and we get nothing.
    
    So we do two passes:
    
    Pass 1 — IMAGE_PATH: prefix (from view_image results):
    server.py's view_image tool prefixes its output with "IMAGE_PATH: <path>".
    This is the clean, intended path. We scan all tool outputs for this prefix.
    
    Pass 2 — search_documents fallback:
    If pass 1 finds nothing, we scan search_documents outputs for file paths
    with image extensions. This catches the case where the agent found images
    but skipped calling view_image. We still run the vision analysis ourselves
    — we just get the paths from search results instead of view_image results.
    
    WHY WE LOOK AT TOOL RESULTS AND NOT THE AGENT'S FINAL TEXT:
    The agent's final text often formats paths as markdown links:
    [/Users/.../photo.jpg](/Users/.../photo.jpg)
    A naive regex on that text captures the ]( and produces a broken path.
    Tool result outputs are raw strings from the MCP server, so they're clean.
    
    WHY THE IMAGE_PATH: PREFIX OVER A FILE EXTENSION REGEX ON view_image RESULTS:
    We could detect view_image results by the tool name, but the SDK doesn't
    always expose which tool produced which output item reliably across versions.
    The prefix is explicit and always present regardless of SDK internals.
    """
    seen  = set()
    paths = []
    
    # ── Log every tool call the agent made so we can see what it actually did ─
    all_outputs = []
    for item in result.new_items:
        item_type = type(item).__name__
        
        # Log tool calls (what the agent decided to call)
        if hasattr(item, "name") and hasattr(item, "arguments"):
            log.info(
                "agent tool call: %s(%s)",
                item.name,
                str(item.arguments)[:200],  # truncate huge search payloads
            )
        
        # Log tool outputs (what the MCP server returned)
        if hasattr(item, "output"):
            texts = _texts_from_tool_output(item.output)
            tool_name = getattr(item, "name", "unknown")
            for i, text in enumerate(texts):
                log.debug(
                    "tool output [%s] block %d/%d: %s",
                    tool_name, i + 1, len(texts),
                    text[:300] + ("..." if len(text) > 300 else ""),
                )
            all_outputs.append((item, texts))
        else:
            log.debug("agent item type=%s (no output field)", item_type)
    
    if not all_outputs:
        log.warning("_extract_image_paths: no tool outputs found in result.new_items")
    
    # ── Pass 1: IMAGE_PATH: prefix from view_image ───────────────────────────
    log.debug("_extract_image_paths: starting pass 1 (IMAGE_PATH: prefix scan)")
    
    for item, texts in all_outputs:
        for text in texts:
            for line in text.splitlines():
                if line.startswith(IMAGE_PATH_PREFIX):
                    path = line[len(IMAGE_PATH_PREFIX):].strip()
                    if path and path not in seen:
                        log.info("_extract_image_paths: pass 1 found — %s", path)
                        seen.add(path)
                        paths.append(path)
    
    if paths:
        log.info(
            "_extract_image_paths: pass 1 succeeded — %d image(s) found via view_image",
            len(paths),
        )
        return paths
    
    log.warning(
        "_extract_image_paths: pass 1 found nothing — "
        "agent did NOT call view_image (skipped the mandatory step). "
        "Falling back to pass 2 (scraping search_documents output)."
    )
    
    # ── Pass 2: fallback — scrape image paths from search_documents output ───
    # WHY WE ONLY DO THIS IF PASS 1 IS EMPTY:
    #   If the agent did call view_image, we'd double-count the same images.
    #   Pass 2 is only a safety net for when the agent skips view_image entirely.
    
    log.debug("_extract_image_paths: starting pass 2 (extension regex fallback)")
    
    for item, texts in all_outputs:
        for text in texts:
            for path in _find_paths_in_text(text, IMAGE_EXTENSIONS):
                exists = Path(path).exists()
                log.debug(
                    "_extract_image_paths: pass 2 regex match — %s (exists=%s)",
                    path, exists,
                )
                if path and path not in seen and exists:
                    log.info("_extract_image_paths: pass 2 found — %s", path)
                    seen.add(path)
                    paths.append(path)
    
    if paths:
        log.info(
            "_extract_image_paths: pass 2 succeeded — %d image(s) found via fallback",
            len(paths),
        )
    else:
        log.error(
            "_extract_image_paths: both passes found nothing — "
            "no image paths in tool outputs at all. "
            "Check that search_documents is returning image results and that the paths exist on disk."
        )
    
    return paths


def _extract_all_references_from_result(result) -> list[str]:
    """
    Scrape all absolute file paths from all tool outputs in the result.
    This catches paths from search_documents, view_image, etc.
    """
    seen = set()
    paths = []
    
    for item in result.new_items:
        if hasattr(item, "output"):
            texts = _texts_from_tool_output(item.output)
            for text in texts:
                for path in _find_paths_in_text(text):
                    if path and path not in seen and os.path.exists(path):
                        seen.add(path)
                        paths.append(path)
    
    return paths


async def _synthesise_image_aware_answer(
    user_query: str,
    agent_response: str,
    image_analyses: list[dict],
) -> str:
    """
    Turn raw image analyses into one clean final answer.

    This avoids dumping "Image 1 says..." blocks back to the user and lets the
    same chat model answer naturally using both search/tool context and the
    vision observations gathered out-of-band.
    """
    if not image_analyses:
        return agent_response

    successful_analyses = []
    for item in image_analyses:
        description = item.get("description", "")
        if description and not description.startswith("["):
            successful_analyses.append({
                "file_name": Path(item["path"]).name,
                "analysis": description,
            })

    if not successful_analyses:
        return agent_response

    synthesis_prompt = (
        "You are refining a final answer for a user.\n"
        "Use the draft answer plus the image analyses below to answer the user's question directly.\n"
        "Do not say you cannot see the images.\n"
        "Do not narrate tool use.\n"
        "Do not list every image unless needed.\n"
        "Give a clean, natural answer and cite filenames only if helpful.\n"
    )

    payload = {
        "model": AGENT_MODEL,
        "messages": [
            {"role": "system", "content": synthesis_prompt},
            {
                "role": "user",
                "content": (
                    f"User question:\n{user_query}\n\n"
                    f"Draft answer:\n{agent_response}\n\n"
                    f"Image analyses:\n{json.dumps(successful_analyses, indent=2)}"
                ),
            },
        ],
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(OLLAMA_CHAT_URL, json=payload)
            resp.raise_for_status()
            refined = resp.json()["message"]["content"].strip()
            return refined or agent_response
    except Exception as e:
        log.warning("_synthesise_image_aware_answer: failed — %s", e)
        return agent_response


# ── Main chat function ───────────────────────────────────────────────────────

async def chat_with_agent(message: str, conversation_history: list = None,
                         search_modalities: str = "text,image,audio") -> dict:
    """
    Chat with the agent. The agent uses MCP tools to search documents.
    Images and video keyframes are handled separately via Ollama's native vision API.

    Args:
        message:              The user's message.
        conversation_history: Unused for now — the openai-agents SDK manages
                              context internally within a run.
        search_modalities:    Comma-separated modalities the agent may search.
                              Default "text,image,audio" (no video) — add "video"
                              to let the agent find and describe video keyframes.
                              Example: "text,image,audio,video"

    Returns:
        Dict with response text, success flag, sources, file references,
        and image_analyses (list of {path, description} dicts).
    """
    try:
        await _ensure_backend_started()
        agent = _build_agent(search_modalities)
        log.info("chat_with_agent: running agent — message=%s modalities=%s",
                 message[:100], search_modalities)
        
        result = await Runner.run(agent, message)
        agent_response = result.final_output
        
        log.info(
            "chat_with_agent: agent finished — response length=%d chars",
            len(agent_response),
        )
        
        # ── Handle images ────────────────────────────────────────────────────
        image_paths = _extract_image_paths_from_tool_results(result)
        image_analyses = []
        
        for path in image_paths:
            log.info("chat_with_agent: sending image to Ollama — %s", Path(path).name)
            description = await _send_image_to_ollama(path, message)
            image_analyses.append({
                "path": path,
                "description": description,
            })

        if image_analyses:
            agent_response = await _synthesise_image_aware_answer(
                message,
                agent_response,
                image_analyses,
            )
        
        # ── Extract full paths for the UI ────────────────────────────────────
        # IMPORTANT: We extract from tool results directly, NOT just the agent's text.
        # This fixes the issue where agent only uses filenames in its summary.
        all_paths = _extract_all_references_from_result(result)
        log.info("chat_with_agent: found %d total file references in tools", len(all_paths))
        
        file_references = []
        for path in all_paths:
            ext = Path(path).suffix.lower()
            file_type = (
                "image"    if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"} else
                "audio"    if ext in {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".mp4"} else
                "document"
            )
            
            # Get rich metadata
            metadata = {}
            if file_type == "image":
                metadata = get_image_metadata(path)
            elif file_type == "audio":
                metadata = get_audio_metadata(path)
                
            file_references.append({
                "path":      path,
                "type":      file_type,
                "extension": ext[1:], # remove leading dot
                "metadata":  metadata
            })
        
        # Sources are just the filenames for a clean list
        sources = list(set([Path(p).name for p in all_paths]))
        
        return {
            "response":        agent_response,
            "success":         True,
            "sources":         sources,
            "file_references": file_references,
            "image_analyses":  image_analyses,
        }
        
    except Exception as e:
        import traceback
        log.error("chat_with_agent: unhandled exception — %s", e, exc_info=True)
        traceback.print_exc()
        return {
            "response": f"Error: {str(e)}",
            "success":  False,
            "error":    str(e),
        }


# ── Streaming ────────────────────────────────────────────────────────────────

async def chat_with_agent_stream(message: str) -> AsyncGenerator[str, None]:
    """
    Stream agent responses token by token.
    
    Currently yields the full response in chunks — true streaming is a TODO
    once the openai-agents SDK stabilises its streaming support.
    """
    try:
        result = await chat_with_agent(message)
        
        if result["success"]:
            response   = result["response"]
            chunk_size = 50
            for i in range(0, len(response), chunk_size):
                yield f"data: {response[i:i + chunk_size]}\n\n"
                await asyncio.sleep(0.05)
        else:
            yield f"data: {result.get('error', 'Unknown error')}\n\n"
        
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: Error: {str(e)}\n\n"
        yield "data: [DONE]\n\n"


# ── Source / reference extraction ────────────────────────────────────────────

def extract_sources(response: str) -> list[str]:
    """
    Extract file names or full paths mentioned in the agent's response.
    Returns a deduplicated list of strings.
    """
    # Matches filenames or absolute paths
    pattern = r'(/[^\s\'"<>\]\)]+\.[\w]{2,4}|[\w\-]+\.[\w]{2,4})'
    matches = re.findall(pattern, response, re.IGNORECASE)
    
    # Clean matches (remove trailing punctuation that might be caught)
    cleaned = []
    for m in matches:
        # Remove trailing dots or commas if they aren't part of the extension
        cleaned.append(m.rstrip('.,'))
        
    return list(set(cleaned))


def extract_file_references(response: str, sources: list[str]) -> list[dict]:
    """
    Extract full file paths from the agent's response for UI preview.
    """
    file_refs = []
    
    # Improved pattern to catch absolute paths even if wrapped in quotes or followed by punctuation
    # Group 1: The path
    # Group 2: The extension
    path_pattern = r'[\'"]?(/[^\s\'"<>\]\)]+\.(pdf|docx|txt|md|jpg|jpeg|png|gif|bmp|webp|mp3|wav|flac|m4a|ogg|aac|mp4))[\'"]?'
    matches = re.findall(path_pattern, response, re.IGNORECASE)
    
    seen = set()
    for path, ext in matches:
        # Clean path from any trailing punctuation that regex might have missed
        path = path.rstrip('.,')
        
        if path in seen:
            continue
        seen.add(path)
        
        ext_lower = ext.lower()
        file_type = (
            "image"    if ext_lower in {"jpg", "jpeg", "png", "gif", "bmp", "webp"} else
            "audio"    if ext_lower in {"mp3", "wav", "flac", "m4a", "ogg", "aac", "mp4"} else
            "document"
        )
        
        metadata = {}
        # Only try to get metadata if the file actually exists
        if os.path.exists(path):
            if file_type == "image":
                metadata = get_image_metadata(path)
            elif file_type == "audio":
                metadata = get_audio_metadata(path)
            
            file_refs.append({
                "path":      path,
                "type":      file_type,
                "extension": ext_lower,
                "metadata":  metadata
            })
        else:
            log.warning("extract_file_references: file does not exist: %s", path)
    
    return file_refs


# ── Cleanup ──────────────────────────────────────────────────────────────────

async def cleanup_agent():
    """Shut down the MCP server subprocess cleanly."""
    global _agent, _mcp_server
    
    log.info("cleanup_agent: shutting down MCP server...")
    
    if _mcp_server is not None:
        try:
            await _mcp_server.__aexit__(None, None, None)
            log.info("cleanup_agent: MCP server stopped")
        except Exception as e:
            log.warning("cleanup_agent: error stopping MCP server — %s", e)
    
    _agent      = None
    _mcp_server = None
    log.info("cleanup_agent: done")
