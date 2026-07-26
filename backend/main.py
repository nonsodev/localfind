"""
main.py — FastAPI backend for LocalFind.

Routes:
  GET  /folders                    List all tracked folders
  POST /folders                    Add a folder by path
  DELETE /folders/{id}             Remove a folder and its index entries
  POST /sync/{folder_id}           Trigger on-demand sync for a folder
  GET  /search?q=&top_k=&folder_id= Semantic search
  GET  /stats                      Global index stats
  GET  /health                     Health check
"""
import logging
import time

# Configure logging before anything else imports/logs.
from logging_config import setup_logging, get_logger
setup_logging()
log = get_logger("api")

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List
import os
import shutil
from pathlib import Path

import db
import multimodal_indexer
import agent_service
from config import BACKEND_HOST, BACKEND_PORT, CHROMA_PATH, DB_PATH, UPLOADS_DIR

# ── App setup ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="LocalFind API",
    description="Local document AI Agent & RAG — index folders, search semantically.",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging ────────────────────────────────────────────────────────
# Log every request with its status and how long it took. Frequent health/stats
# polls are logged at DEBUG so they don't bury the interesting lines; everything
# else is INFO, and 4xx/5xx responses are WARNING.

_QUIET_PATHS = {"/health", "/stats"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    path = request.url.path
    is_quiet = path in _QUIET_PATHS
    log.log(logging.DEBUG if is_quiet else logging.INFO, "→ %s %s", request.method, path)
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        log.exception("✗ %s %s raised after %.0fms", request.method, path, elapsed)
        raise
    elapsed = (time.perf_counter() - start) * 1000
    if response.status_code >= 400:
        level = logging.WARNING
    elif is_quiet:
        level = logging.DEBUG
    else:
        level = logging.INFO
    log.log(level, "← %s %s %d (%.0fms)", request.method, path, response.status_code, elapsed)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Last-resort handler: log the full traceback and return a clean JSON error."""
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "path": request.url.path},
    )


db.init_db()

# ── Startup integrity check ────────────────────────────────────────────────
# If chroma_db was manually deleted from the filesystem, SQLite will still
# have stale records. Detect this and wipe SQLite so they stay in sync.

if not CHROMA_PATH.exists():
    log.warning("chroma_db not found on disk — clearing SQLite metadata to stay in sync")
    db.clear_all_metadata()
else:
    log.info("Backend starting — chroma_db at %s", CHROMA_PATH)


# ── Models ─────────────────────────────────────────────────────────────────

class AddFolderRequest(BaseModel):
    path: str


# ── Sync state tracker (in-memory for per-folder sync status) ──────────────

_sync_status: dict[int, dict] = {}


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok"}


@app.get("/folders")
def list_folders():
    folders = db.get_folders()
    # Enrich with per-folder file counts
    enriched = []
    for f in folders:
        files = db.get_folder_files(f["id"])
        sync_entry = _sync_status.get(f["id"], {})
        enriched.append({
            **f,
            "file_count": len(files),
            "chunk_count": sum(x["chunk_count"] for x in files),
            "sync_status": sync_entry.get("status", "idle"),
            "sync_progress": sync_entry.get("progress") if sync_entry.get("status") == "syncing" else None,
        })
    return enriched


@app.post("/folders", status_code=201)
def add_folder(req: AddFolderRequest):
    path = req.path.strip()
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"Path does not exist or is not a directory: {path}")
    folder = db.add_folder(path)
    return folder


@app.delete("/folders/{folder_id}", status_code=204)
def remove_folder(folder_id: int):
    folder = db.get_folder_by_id(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Remove all ChromaDB chunks for files in this folder across all modalities
    try:
        files = db.get_folder_files(folder_id)
        if files:
            file_paths = [f["file_path"] for f in files]
            for col_name in [multimodal_indexer.TEXT_COLLECTION,
                             multimodal_indexer.IMAGE_COLLECTION,
                             multimodal_indexer.IMAGE_CAPTIONS_COLLECTION,
                             multimodal_indexer.AUDIO_COLLECTION,
                             multimodal_indexer.VIDEO_FRAMES_COLLECTION]:
                collection = multimodal_indexer.get_collection(col_name)
                # ChromaDB supports filtering by metadata
                for path in file_paths:
                    existing = collection.get(where={"source": path})
                    if existing and existing["ids"]:
                        collection.delete(ids=existing["ids"])
        log.info("Removed folder %d (%s) and its index entries", folder_id, folder.get("path", "?"))
    except Exception:
        log.exception("Cleanup error during removal of folder %d", folder_id)
        # Best-effort cleanup — keep going so the folder record is still removed.

    db.remove_folder(folder_id)
    _sync_status.pop(folder_id, None)
    return None


def _do_sync(folder_id: int, folder_path: str, enable_captioning: bool):
    """Background sync task — updates _sync_status in place."""
    _sync_status[folder_id] = {
        "status": "syncing", "result": None,
        "progress": {"done": 0, "total": 0, "current_file": ""},
    }
    log.info("Sync started — folder %d (%s), captioning=%s",
             folder_id, folder_path, enable_captioning)
    started = time.perf_counter()

    def _on_progress(done: int, total: int, current_file: str):
        _sync_status[folder_id]["progress"] = {
            "done": done, "total": total, "current_file": current_file,
        }

    try:
        result = multimodal_indexer.sync_folder(folder_id, folder_path,
                                                enable_captioning=enable_captioning,
                                                on_progress=_on_progress)
        _sync_status[folder_id] = {"status": "done", "result": result, "progress": None}
        log.info("Sync finished — folder %d in %.1fs: %s",
                 folder_id, time.perf_counter() - started, result.get("by_modality", result))
    except Exception as e:
        _sync_status[folder_id] = {"status": "error", "result": {"error": str(e)}, "progress": None}
        log.exception("Sync FAILED — folder %d (%s)", folder_id, folder_path)


@app.post("/sync/{folder_id}")
def sync_folder(folder_id: int, background_tasks: BackgroundTasks,
                enable_captioning: bool = True):
    """
    Trigger a sync for a folder.

    enable_captioning (default: true) — the vision model generates a natural-language
    caption for each new image at index time, enabling semantic text search over image
    contents. Pass ?enable_captioning=false to skip captioning (faster, CLIP only).
    """
    folder = db.get_folder_by_id(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    current = _sync_status.get(folder_id, {})
    if current.get("status") == "syncing":
        raise HTTPException(status_code=409, detail="Sync already in progress for this folder")

    background_tasks.add_task(_do_sync, folder_id, folder["path"], enable_captioning)
    _sync_status[folder_id] = {"status": "syncing", "result": None}
    return {"message": "Sync started", "folder_id": folder_id,
            "enable_captioning": enable_captioning}


@app.get("/sync/{folder_id}/status")
def sync_status(folder_id: int):
    status = _sync_status.get(folder_id, {"status": "idle", "result": None})
    return status


ACCEPTED_UPLOAD_EXTENSIONS = {
    ".pdf", ".docx", ".txt", ".md", ".csv",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    ".mp3", ".wav", ".flac", ".m4a",
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v",
}

@app.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
):
    """
    Upload one or more files directly. Files are saved to the uploads/ directory
    and indexed immediately. Supports all file types: documents, images, audio, video.
    """
    UPLOADS_DIR.mkdir(exist_ok=True)

    # Get or create the virtual "uploads" folder in the DB
    uploads_folder = db.add_folder(str(UPLOADS_DIR))
    folder_id = uploads_folder["id"]

    saved = []
    rejected = []

    for file in files:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in ACCEPTED_UPLOAD_EXTENSIONS:
            rejected.append(file.filename)
            continue

        dest = UPLOADS_DIR / file.filename
        # Avoid overwriting — append _1, _2, etc. if name already exists
        if dest.exists():
            stem = Path(file.filename).stem
            i = 1
            while dest.exists():
                dest = UPLOADS_DIR / f"{stem}_{i}{suffix}"
                i += 1

        content = await file.read()
        dest.write_bytes(content)
        saved.append(dest.name)

    if saved:
        background_tasks.add_task(_do_sync, folder_id, str(UPLOADS_DIR), True)
        _sync_status[folder_id] = {"status": "syncing", "result": None}

    return {
        "saved": saved,
        "rejected": rejected,
        "folder_id": folder_id,
        "message": f"{len(saved)} file(s) uploaded, indexing started"
            if saved else "No valid files to upload",
    }


@app.get("/search")
def search(q: str, top_k: int = 5, folder_id: int | None = None,
           modalities: str | None = None, group_by_source: bool = False,
           include_video_speech: bool = False):
    """
    Multimodal semantic search.

    Query params:
        q: Search query
        top_k: Results per modality (default: 5)
        folder_id: Optional folder filter
        modalities: Comma-separated list (e.g., "text,image,audio")
        group_by_source: If true, collapse each file to its best match
            ("one result per file" filter — text/audio/video). Default false.
        include_video_speech: If true, video search also matches the spoken
            transcript, not just the visual frames. Default false (visuals only).
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Parse modalities filter
    modality_list = None
    if modalities:
        modality_list = [m.strip() for m in modalities.split(",")]
        valid = {"text", "image", "audio", "video"}
        if not all(m in valid for m in modality_list):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid modality. Must be one of: {valid}"
            )
    
    try:
        results = multimodal_indexer.search(
            q,
            top_k=top_k,
            folder_id=folder_id,
            modalities=modality_list,
            group_by_source=group_by_source,
            include_video_speech=include_video_speech,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
    return results


# ── Agent Chat Endpoint ────────────────────────────────────────────────────

class AgentChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] | None = None
    search_modalities: str = "text,image,audio"


@app.post("/agent/chat")
async def agent_chat(request: AgentChatRequest):
    """
    Chat with the AI agent that can search your documents.

    Body:
        message:             User message/question.
        conversation_history: Optional prior messages.
        search_modalities:   Comma-separated list of modalities the agent may search.
                             Default "text,image,audio". Add "video" to enable
                             video-frame search (slower with local models).
                             Example: "text,image,audio,video"

    Returns:
        response: Agent's response
        sources: List of files mentioned
        success: Whether the request succeeded
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        result = await agent_service.chat_with_agent(
            request.message,
            request.conversation_history,
            search_modalities=request.search_modalities,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.get("/agent/stream")
async def agent_chat_stream(q: str):
    """
    Stream agent responses (SSE).
    
    Query params:
        q: User message/question
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    return StreamingResponse(
        agent_service.chat_with_agent_stream(q),
        media_type="text/event-stream"
    )


@app.get("/stats")
def stats():
    return db.get_stats()


@app.get("/files/{file_path:path}")
def serve_file(file_path: str):
    """
    Serve indexed files (images, audio, video, extracted keyframes) for preview
    in the frontend. Decodes URL-encoded file paths and returns the file.

    The media type is inferred from the extension so audio/video elements can
    play and seek (FileResponse handles HTTP range requests for them).
    """
    from urllib.parse import unquote
    import mimetypes

    # Decode the URL-encoded path
    decoded_path = unquote(file_path)

    # Security check: ensure file exists and is accessible
    if not os.path.exists(decoded_path):
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.isfile(decoded_path):
        raise HTTPException(status_code=400, detail="Path is not a file")

    media_type = mimetypes.guess_type(decoded_path)[0] or "application/octet-stream"

    # Return the file
    return FileResponse(
        decoded_path,
        media_type=media_type,
        filename=os.path.basename(decoded_path)
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=BACKEND_HOST, port=BACKEND_PORT, reload=True)
