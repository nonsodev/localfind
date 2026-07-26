"""
multimodal_indexer.py — Multimodal RAG indexing pipeline.

Handles three modalities:
  1. TEXT (PDFs, DOCX, TXT, MD) → nomic-embed-text via Ollama
  2. IMAGES (JPG, PNG, etc.) → OpenCLIP (local)
  3. AUDIO (MP3, WAV, FLAC, etc.) → Whisper transcription → text embeddings

Each modality gets its own ChromaDB collection, but they're all queried
together at search time with a unified text query.

Architecture:
  - Text query → embed with text model (Ollama)
  - Query text collection with text embedding
  - Query image collection with CLIP text embedding
  - Query audio collection with text embedding (from transcripts)
  - Merge and rank results from all three
"""
import os
import re
import shutil
from pathlib import Path
from typing import Generator, Any
import numpy as np

import chromadb
from openai import OpenAI

# open_clip and torch are only loaded when IMAGE_CAPTIONING_BACKEND == "clip".
# Lazy-imported in get_clip_model() so caption-backend users don't pay the
# PyTorch startup cost or need those packages installed.
open_clip = None
torch = None

import base64
import httpx

import db
import audio_transcriber
import video_processor
from logging_config import get_logger
from config import (
    OLLAMA_BASE_URL, OLLAMA_CHAT_URL, TEXT_EMBED_MODEL, CHROMA_PATH,
    IMAGE_CAPTIONING_BACKEND, VIDEO_FRAMES_DIR,
    VIDEO_SCENE_THRESHOLD, VIDEO_MAX_FRAMES, VIDEO_MIN_FRAME_GAP,
)
from parsers import (
    parse_pdf, parse_docx, parse_text,
    parse_image, get_image_metadata,
    get_audio_metadata
)

log = get_logger("indexer")

# Collection names for each modality
TEXT_COLLECTION = "localfind_text"
IMAGE_COLLECTION = "localfind_images"
IMAGE_CAPTIONS_COLLECTION = "localfind_image_captions"  # text embeddings of vision-model captions
AUDIO_COLLECTION = "localfind_audio_transcripts"  # also holds video speech transcripts (modality="video_transcript")
VIDEO_FRAMES_COLLECTION = "localfind_video_frames"  # captioned keyframes, one entry per frame

# Supported file extensions by modality
TEXT_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".txt": "text",
    ".md": "text",
    ".rst": "text",
    ".csv": "text",
}

IMAGE_EXTENSIONS = {
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".bmp": "image",
    ".webp": "image",
}

AUDIO_EXTENSIONS = {
    ".mp3": "audio",
    ".wav": "audio",
    ".flac": "audio",
    ".m4a": "audio",
    ".ogg": "audio",
    ".aac": "audio",
}

# Video files are indexed as keyframes + a Whisper transcript of the audio track.
VIDEO_EXTENSIONS = dict(video_processor.VIDEO_EXTENSIONS)

ALL_EXTENSIONS = {**TEXT_EXTENSIONS, **IMAGE_EXTENSIONS, **AUDIO_EXTENSIONS, **VIDEO_EXTENSIONS}

# Text chunking config
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80

# Per-modality result limits (prevents text from drowning out images/audio)
MAX_RESULTS_PER_MODALITY = 10

# When the "one result per file" grouping filter is on, how many results a single
# source file may contribute. 1 = each file appears once, at its best match — so a
# video full of matching frames (or a long podcast/PDF) can't crowd out other files.
GROUPED_RESULTS_PER_SOURCE = 1


# ── Model singletons ───────────────────────────────────────────────────────

_openai_client: Any = None
_clip_model: Any = None
_clip_preprocess: Any = None
_clip_tokenizer: Any = None
_chroma_client: Any = None
_collections: dict[str, Any] = {}


def get_openai_client() -> OpenAI:
    """OpenAI SDK → Ollama for text embeddings."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",
        )
    return _openai_client


def get_clip_model():
    """Load OpenCLIP model (ViT-B-32). Lazy-imports torch and open_clip."""
    global _clip_model, _clip_preprocess, _clip_tokenizer, open_clip, torch
    if _clip_model is None:
        import open_clip as _oc
        import torch as _torch
        open_clip = _oc
        torch = _torch

        log.info("🔄 Loading OpenCLIP model (ViT-B-32)...")
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

        _clip_model, _, _clip_preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained="laion2b_s34b_b79k",
            device=device,
        )
        _clip_tokenizer = open_clip.get_tokenizer("ViT-B-32")
        _clip_model.eval()
        log.info(f"✓ CLIP loaded on {device}")
    return _clip_model, _clip_preprocess, _clip_tokenizer


def get_chroma_client():
    """Get ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        # Disable telemetry to clean up logs
        from chromadb.config import Settings
        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False)
        )
    return _chroma_client


def get_collection(name: str):
    """Get or create a ChromaDB collection by name."""
    global _collections
    if name not in _collections:
        client = get_chroma_client()
        _collections[name] = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
    return _collections[name]


# ── Embedding functions ────────────────────────────────────────────────────

def embed_texts_ollama(texts: list[str]) -> list[list[float]]:
    """Embed text using Ollama (nomic-embed-text)."""
    client = get_openai_client()
    response = client.embeddings.create(
        model=TEXT_EMBED_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def embed_images_clip(images: list) -> list[list[float]]:
    """
    Embed images using OpenCLIP.
    
    Args:
        images: List of PIL Image objects
    
    Returns:
        List of embedding vectors
    """
    model, preprocess, _ = get_clip_model()
    device = next(model.parameters()).device
    
    embeddings = []
    with torch.no_grad():
        for img in images:
            img_tensor = preprocess(img).unsqueeze(0).to(device)
            embedding = model.encode_image(img_tensor)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)  # Normalize
            embeddings.append(embedding.cpu().numpy()[0].tolist())
    
    return embeddings


def embed_text_clip(texts: list[str]) -> list[list[float]]:
    """
    Embed text using OpenCLIP (for querying image collection).
    
    Args:
        texts: List of text strings
    
    Returns:
        List of embedding vectors
    """
    model, _, tokenizer = get_clip_model()
    device = next(model.parameters()).device
    
    embeddings = []
    with torch.no_grad():
        for text in texts:
            text_tokens = tokenizer([text]).to(device)
            embedding = model.encode_text(text_tokens)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)  # Normalize
            embeddings.append(embedding.cpu().numpy()[0].tolist())
    
    return embeddings


# ── Text chunking (same as before) ─────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Recursive character-level chunker with overlap."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", ". ", " ", ""]

    def _split(t: str, sep_idx: int = 0) -> list[str]:
        if len(t) <= chunk_size:
            return [t]
        sep = separators[sep_idx] if sep_idx < len(separators) else ""
        parts = t.split(sep) if sep else list(t)
        result, current = [], ""
        for part in parts:
            piece = (current + sep + part) if current else part
            if len(piece) <= chunk_size:
                current = piece
            else:
                if current:
                    result.append(current)
                if len(part) > chunk_size and sep_idx + 1 < len(separators):
                    result.extend(_split(part, sep_idx + 1))
                    current = ""
                else:
                    current = part
        if current:
            result.append(current)
        return result

    raw_chunks = _split(text)

    chunks = []
    for i, chunk in enumerate(raw_chunks):
        if i == 0:
            chunks.append(chunk)
        else:
            tail = raw_chunks[i - 1][-overlap:]
            chunks.append((tail + " " + chunk) if tail else chunk)

    return [c.strip() for c in chunks if c.strip()]


# ── File walking ───────────────────────────────────────────────────────────

def walk_supported_files(folder_path: str) -> Generator[tuple[str, str, str], None, None]:
    """
    Yield (absolute_path, file_type, modality) for all supported files.
    
    modality is one of: "text", "image", "audio"
    """
    log.info(f"🔍 Scanning: {folder_path}")
    found_any = False
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext in ALL_EXTENSIONS:
                found_any = True
                file_path = os.path.join(root, fname)
                file_type = ALL_EXTENSIONS[ext]
                
                # Determine modality
                if ext in TEXT_EXTENSIONS:
                    modality = "text"
                elif ext in IMAGE_EXTENSIONS:
                    modality = "image"
                elif ext in VIDEO_EXTENSIONS:
                    modality = "video"
                else:
                    modality = "audio"

                yield file_path, file_type, modality
    
    if not found_any:
        log.warning("No supported files found")


# ── Parsing dispatch ───────────────────────────────────────────────────────

def parse_file(file_path: str, file_type: str, modality: str):
    """Parse file based on modality."""
    if modality == "text":
        if file_type == "pdf":
            return parse_pdf(file_path)
        elif file_type == "docx":
            return parse_docx(file_path)
        else:
            return parse_text(file_path)
    elif modality == "image":
        return parse_image(file_path)
    elif modality == "audio":
        # For audio, we transcribe instead of parsing waveform
        return audio_transcriber.transcribe_and_save(file_path)
    else:
        raise ValueError(f"Unknown modality: {modality}")


# ── ChromaDB upsert ────────────────────────────────────────────────────────

def _chunk_id(file_path: str, idx: int) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", file_path)
    return f"{safe}__chunk{idx}"


def _file_id(file_path: str) -> str:
    """For images/audio, we store one embedding per file."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", file_path)
    return f"{safe}__file"


def upsert_text_chunks(file_path: str, file_type: str, chunks: list[str],
                       folder_id: int, content_hash: str):
    """Embed and store text chunks in text collection."""
    collection = get_collection(TEXT_COLLECTION)
    
    # Remove old chunks
    existing = collection.get(where={"source": file_path})
    if existing and existing["ids"]:
        collection.delete(ids=existing["ids"])
    
    if not chunks:
        return
    
    log.info(f"  → Embedding {len(chunks)} text chunks via Ollama...")
    embeddings = embed_texts_ollama(chunks)
    
    ids = [_chunk_id(file_path, i) for i in range(len(chunks))]
    metadatas = [
        {
            "source": file_path,
            "file_name": Path(file_path).name,
            "file_type": file_type,
            "modality": "text",
            "folder_id": folder_id,
            "chunk_index": i,
            "content_hash": content_hash,
        }
        for i in range(len(chunks))
    ]
    
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas,
    )


def generate_image_caption(file_path: str) -> str | None:
    """
    Ask the configured vision model (e.g. Qwen2.5-VL or Gemma) to describe an image.
    Returns None on any failure — captioning is best-effort, never blocks indexing.
    Uses a synchronous httpx.Client because sync_folder runs in a thread.
    """
    try:
        with open(file_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        log.warning(f"Could not read image for captioning: {e}")
        return None

    payload = {
        "model": IMAGE_CAPTIONING_BACKEND,
        "messages": [{
            "role": "user",
            "content": (
                "Describe this image in one to three sentences. "
                "Be specific about people, objects, text, settings, colors, and activities. "
                "Focus on details that would help someone find this image through a search engine."
            ),
            "images": [image_b64],
        }],
        "stream": False,
    }

    for attempt in range(1, 3):  # up to 2 attempts — a model can occasionally return empty
        try:
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(OLLAMA_CHAT_URL, json=payload)
                resp.raise_for_status()
                caption = resp.json()["message"]["content"].strip()
                if caption:
                    return caption
                if attempt < 2:
                    log.warning(f"Empty response from {IMAGE_CAPTIONING_BACKEND}, retrying...")
        except Exception as e:
            log.warning(f"Caption failed ({IMAGE_CAPTIONING_BACKEND}): {e}")
            return None
    return None


def upsert_image(file_path: str, image, folder_id: int, content_hash: str,
                 enable_captioning: bool = True):
    """
    Embed and store an image. Routing depends on IMAGE_CAPTIONING_BACKEND:

    clip backend:
        CLIP visual embedding → IMAGE_COLLECTION.
        Fast. No Ollama call. Visual similarity only.

    captioning backend (qwen2.5vl:*, gemma4:*, any non-clip vision tag):
        If enable_captioning=True:  Ollama vision caption → nomic text embedding → IMAGE_CAPTIONS_COLLECTION.
        If enable_captioning=False: filename text → nomic text embedding → IMAGE_CAPTIONS_COLLECTION.
        Caption quality varies by model (see IMAGE_CAPTIONING_BACKEND in config).
    """
    shared_meta = get_image_metadata(file_path)
    shared_meta.update({
        "source": file_path,
        "file_name": Path(file_path).name,
        "file_type": "image",
        "modality": "image",
        "folder_id": folder_id,
        "content_hash": content_hash,
    })

    if IMAGE_CAPTIONING_BACKEND == "clip":
        # ── CLIP path ────────────────────────────────────────────────────────
        collection = get_collection(IMAGE_COLLECTION)
        existing = collection.get(where={"source": file_path})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])

        log.info(f"  → Embedding image via OpenCLIP...")
        clip_embeddings = embed_images_clip([image])
        collection.add(
            documents=[f"Image: {Path(file_path).name}"],
            embeddings=clip_embeddings,
            ids=[_file_id(file_path)],
            metadatas=[{**shared_meta, "has_caption": False}],
        )

    else:
        # ── Caption path (qwen2.5vl:3b / gemma4:* — any non-clip backend) ────
        captions_col = get_collection(IMAGE_CAPTIONS_COLLECTION)
        existing = captions_col.get(where={"source": file_path})
        if existing and existing["ids"]:
            captions_col.delete(ids=existing["ids"])

        caption = None
        if enable_captioning:
            log.info(f"  → Generating caption with {IMAGE_CAPTIONING_BACKEND}...")
            caption = generate_image_caption(file_path)
            if caption:
                log.info(f"  → Caption ({len(caption)} chars): {caption[:120]}{'...' if len(caption) > 120 else ''}")
            else:
                log.warning("Caption unavailable, using filename fallback")
        else:
            log.info(f"  → Captioning skipped (quick sync)")

        document_text = caption if caption else f"Image: {Path(file_path).name}"
        log.info(f"  → Indexing via nomic text embedding...")
        embeddings = embed_texts_ollama([document_text])
        captions_col.add(
            documents=[document_text],
            embeddings=embeddings,
            ids=[_file_id(file_path)],
            metadatas=[{**shared_meta, "has_caption": bool(caption)}],
        )


def upsert_audio_transcript(file_path: str, transcript: dict, folder_id: int, content_hash: str,
                            file_type: str = "audio", modality: str = "audio_transcript"):
    """
    Embed and store transcript chunks in the audio collection.

    Used for both standalone audio files (file_type="audio") and the speech track
    of videos (file_type="video", modality="video_transcript"). The modality tag
    lets search keep audio results and video results separate even though both
    live in the same collection.

    Args:
        file_path: Path to the source audio/video file
        transcript: Transcript dict from audio_transcriber
        folder_id: Folder ID
        content_hash: File hash
        file_type: "audio" or "video"
        modality: "audio_transcript" or "video_transcript"
    """
    collection = get_collection(AUDIO_COLLECTION)
    
    # Remove old entries
    existing = collection.get(where={"source": file_path})
    if existing and existing["ids"]:
        collection.delete(ids=existing["ids"])
    
    full_text = transcript["text"]
    if not full_text.strip():
        log.warning("Empty transcript, skipping")
        return 0

    segments = transcript.get("segments") or []
    duration = transcript.get("duration")

    # Build chunks directly from the timed segments so each chunk's (start, end)
    # is exact. The old approach chunked the flat transcript and tried to match
    # the text back to segments afterward; that frequently failed and fell back
    # to the whole-file span, making every result look like it covered the
    # entire audio/video.
    if segments:
        timed_chunks = _chunk_transcript_segments(segments)
    else:
        # No timing available — index plain text chunks spanning the whole file.
        timed_chunks = [{"text": c, "start": 0.0, "end": duration or 0.0}
                        for c in chunk_text(full_text)]

    if not timed_chunks:
        log.warning("No transcript chunks produced, skipping")
        return 0

    documents = [c["text"] for c in timed_chunks]
    log.info(f"  → Embedding {len(documents)} transcript chunks via Ollama...")
    embeddings = embed_texts_ollama(documents)

    ids, metadatas = [], []
    for i, c in enumerate(timed_chunks):
        ids.append(_chunk_id(file_path, i))
        metadatas.append({
            "source": file_path,
            "file_name": Path(file_path).name,
            "file_type": file_type,
            "modality": modality,
            "folder_id": folder_id,
            "chunk_index": i,
            "content_hash": content_hash,
            "start_time": round(c["start"], 2) if c["start"] is not None else 0.0,
            "end_time": round(c["end"], 2) if c["end"] is not None else 0.0,
            "language": transcript.get("language", "unknown"),
            "duration": duration,
        })

    collection.add(
        documents=documents,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas,
    )
    return len(documents)


def _chunk_transcript_segments(segments: list[dict], chunk_size: int = CHUNK_SIZE) -> list[dict]:
    """
    Group Whisper segments into ~chunk_size-character chunks, carrying the exact
    (start, end) time covered by the segments in each chunk.

    Building chunks FROM the timed segments (rather than chunking the flat
    transcript and guessing the range) means every chunk's timestamps are exact —
    so a search result highlights the moment it actually matched, not the whole file.
    """
    chunks: list[dict] = []
    cur_text = ""
    cur_start = None
    cur_end = None

    for seg in segments:
        seg_text = (seg.get("text") or "").strip()
        if not seg_text:
            continue
        # Flush the current chunk before adding this segment would overflow it.
        if cur_text and len(cur_text) + 1 + len(seg_text) > chunk_size:
            chunks.append({"text": cur_text, "start": cur_start, "end": cur_end})
            cur_text = ""
            cur_start = None
        if cur_start is None:
            cur_start = seg.get("start")
        cur_text = f"{cur_text} {seg_text}".strip() if cur_text else seg_text
        cur_end = seg.get("end")

    if cur_text:
        chunks.append({"text": cur_text, "start": cur_start, "end": cur_end})

    return chunks


def _video_frames_dir(file_path: str) -> str:
    """Cache directory for one video's extracted keyframes."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", file_path)
    return str(VIDEO_FRAMES_DIR / safe)


def upsert_video(file_path: str, folder_id: int, content_hash: str,
                 enable_captioning: bool = True) -> int:
    """
    Index a video as keyframes + a speech transcript.

    Frames: scene-change keyframes are extracted with ffmpeg and captioned with
    the same vision pipeline as images. Each frame becomes one entry in
    VIDEO_FRAMES_COLLECTION tagged with its timestamp and cached JPEG path.

    Speech: the audio track is transcribed by Whisper and stored in the audio
    collection tagged modality="video_transcript", with per-chunk time ranges.

    With enable_captioning=False (quick sync) frame extraction is skipped and only
    the transcript is indexed — frame captioning is the expensive part.

    Returns the number of keyframes indexed.
    """
    frames_col = get_collection(VIDEO_FRAMES_COLLECTION)

    # Clear previous frame entries + cached images for this video (re-index path).
    existing = frames_col.get(where={"source": file_path})
    if existing and existing["ids"]:
        frames_col.delete(ids=existing["ids"])
    frames_dir = _video_frames_dir(file_path)

    frame_count = 0
    if enable_captioning:
        log.info(f"  → Extracting keyframes (scene threshold {VIDEO_SCENE_THRESHOLD})...")
        keyframes = video_processor.extract_keyframes(
            file_path, frames_dir,
            scene_threshold=VIDEO_SCENE_THRESHOLD,
            max_frames=VIDEO_MAX_FRAMES,
            min_gap=VIDEO_MIN_FRAME_GAP,
        )
        log.info(f"  → {len(keyframes)} keyframes; captioning each...")

        documents, embeddings, ids, metadatas = [], [], [], []
        use_clip = IMAGE_CAPTIONING_BACKEND == "clip"
        clip_images = []

        for idx, (timestamp, frame_path) in enumerate(keyframes):
            has_caption = False
            if use_clip:
                from PIL import Image
                clip_images.append(Image.open(frame_path).convert("RGB"))
                document = f"{Path(file_path).name} — frame at {timestamp}s"
            else:
                caption = generate_image_caption(frame_path)
                has_caption = bool(caption)
                document = caption if caption else f"{Path(file_path).name} — frame at {timestamp}s"

            documents.append(document)
            ids.append(f"{_file_id(file_path)}__frame{idx}")
            metadatas.append({
                "source": file_path,
                "file_name": Path(file_path).name,
                "file_type": "video",
                "modality": "video_frame",
                "folder_id": folder_id,
                "content_hash": content_hash,
                "timestamp": timestamp,
                "frame_path": frame_path,
                "frame_index": idx,
                "has_caption": has_caption,
            })

        if documents:
            if use_clip:
                embeddings = embed_images_clip(clip_images)
            else:
                embeddings = embed_texts_ollama(documents)
            frames_col.add(
                documents=documents,
                embeddings=embeddings,
                ids=ids,
                metadatas=metadatas,
            )
        frame_count = len(documents)
    else:
        log.info(f"  → Frame extraction skipped (quick sync); transcribing audio only")
        shutil.rmtree(frames_dir, ignore_errors=True)

    # Speech track → reuse the Whisper pipeline (it accepts video containers).
    log.info(f"  → Transcribing audio track via Whisper...")
    transcript = audio_transcriber.transcribe_and_save(file_path)
    upsert_audio_transcript(
        file_path, transcript, folder_id, content_hash,
        file_type="video", modality="video_transcript",
    )

    return frame_count


# ── Main sync entry point ──────────────────────────────────────────────────

def sync_folder(folder_id: int, folder_path: str, enable_captioning: bool = True,
                on_progress=None) -> dict:
    """
    Index all supported files (text, images, audio) in folder_path.
    Skips files whose SHA256 hash hasn't changed since last sync.

    on_progress: optional callable(done, total, current_filename) called before each file.
    """
    if not os.path.isdir(folder_path):
        raise ValueError(f"Not a directory: {folder_path}")

    db.init_db()

    stats = {
        "total_scanned": 0,
        "indexed_new": 0,
        "indexed_updated": 0,
        "skipped_unchanged": 0,
        "failed": 0,
        "errors": [],
        "by_modality": {
            "text": 0,
            "image": 0,
            "audio": 0,
            "video": 0,
        }
    }

    all_files = list(walk_supported_files(folder_path))
    total = len(all_files)

    for i, (file_path, file_type, modality) in enumerate(all_files):
        fname = Path(file_path).name
        if on_progress:
            on_progress(i, total, fname)
        stats["total_scanned"] += 1
        log.info(f"📄 [{i+1}/{total}] {fname} ({modality}/{file_type})")
        
        try:
            content_hash = db.get_file_hash(file_path)
            existing = db.get_indexed_file(file_path)
            
            if existing and existing["content_hash"] == content_hash:
                log.info(f"  → Unchanged, skipping")
                stats["skipped_unchanged"] += 1
                continue
            
            is_update = existing is not None
            
            # Parse based on modality.
            # Images skip parse_file when using a caption backend — the caption
            # path reads the file directly as bytes. parse_image (PIL) is only
            # needed for the CLIP backend which requires a PIL Image object.
            if modality == "video":
                # Video has its own pipeline (frames + transcript); no parse step.
                parsed = None
            elif modality == "image" and IMAGE_CAPTIONING_BACKEND != "clip":
                parsed = None
            else:
                parsed = parse_file(file_path, file_type, modality)

            # Process based on modality
            if modality == "text":
                if not parsed.strip():
                    log.warning(f"No text extracted from {fname}")
                    db.upsert_indexed_file(folder_id, file_path, content_hash, file_type, 0)
                    continue

                chunks = chunk_text(parsed)
                log.info(f"  → {len(chunks)} chunks")
                upsert_text_chunks(file_path, file_type, chunks, folder_id, content_hash)
                db.upsert_indexed_file(folder_id, file_path, content_hash, file_type, len(chunks))

            elif modality == "image":
                upsert_image(file_path, parsed, folder_id, content_hash,
                             enable_captioning=enable_captioning)
                db.upsert_indexed_file(folder_id, file_path, content_hash, file_type, 1)
            
            elif modality == "audio":
                # parsed is the transcript dict
                transcript = parsed
                chunk_count = upsert_audio_transcript(file_path, transcript, folder_id, content_hash)
                db.upsert_indexed_file(folder_id, file_path, content_hash, file_type, chunk_count)

            elif modality == "video":
                frame_count = upsert_video(file_path, folder_id, content_hash,
                                           enable_captioning=enable_captioning)
                db.upsert_indexed_file(folder_id, file_path, content_hash, file_type, frame_count)

            stats["by_modality"][modality] += 1
            
            if is_update:
                stats["indexed_updated"] += 1
                log.info(f"  ✓ Updated")
            else:
                stats["indexed_new"] += 1
                log.info(f"  ✓ Indexed")
        
        except Exception as e:
            log.exception(f"Error indexing {fname}")
            stats["failed"] += 1
            stats["errors"].append({"file": file_path, "error": str(e)})
    
    if on_progress:
        on_progress(total, total, "")

    n_indexed = stats["indexed_new"] + stats["indexed_updated"]
    log.info(f"✅ Done: {n_indexed} indexed ({stats['by_modality']}), "
             f"{stats['skipped_unchanged']} skipped, {stats['failed']} failed")
    return stats


# ── Multimodal search ──────────────────────────────────────────────────────

def _build_where(folder_id: int | None, modality: str | None = None) -> dict | None:
    """Compose a ChromaDB where filter from an optional folder and modality."""
    clauses = []
    if folder_id is not None:
        clauses.append({"folder_id": folder_id})
    if modality is not None:
        clauses.append({"modality": modality})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _take_top(hits: list[dict], limit: int, per_source: int | None) -> list[dict]:
    """
    Rank hits by score (desc) and return up to `limit`.

    If per_source is set, keep at most that many results per source file — so one
    file with many matching chunks/frames can't fill every slot. This is the
    "one result per file" grouping filter (per_source=1); per_source=None keeps
    the raw ranked list.
    """
    ranked = sorted(hits, key=lambda r: r.get("score", 0), reverse=True)
    if per_source is None:
        return ranked[:limit]
    seen: dict[str, int] = {}
    out: list[dict] = []
    for hit in ranked:
        src = hit.get("file_path", "")
        if seen.get(src, 0) >= per_source:
            continue
        seen[src] = seen.get(src, 0) + 1
        out.append(hit)
        if len(out) >= limit:
            break
    return out


def search(query: str, top_k: int = 5, folder_id: int | None = None,
           modalities: list[str] | None = None,
           group_by_source: bool = False,
           include_video_speech: bool = False) -> dict:
    """
    Unified multimodal search.
    
    Embeds the query and searches all collections,
    then merges and ranks results.
    
    Args:
        query: Text query
        top_k: Number of results per modality
        folder_id: Optional folder filter
        modalities: List of modalities to search (default: all)
        group_by_source: If True, collapse each source file to its best match
            (the "one result per file" filter). Applies to text, audio, and
            video; images are already one entry per file. Off by default.
        include_video_speech: For the "video" modality, whether to also search the
            spoken transcript (what was said) in addition to the visual frames
            (what's shown). Off by default — video search is visuals-only unless
            this is set. Speech matches are tagged with their nearest keyframe so
            they still show a real frame.

    Returns:
        Dict with results grouped by modality
    """
    if modalities is None:
        modalities = ["text", "image", "audio", "video"]

    where = {"folder_id": folder_id} if folder_id is not None else None
    results = {"query": query, "results": {}}

    per_modality = min(top_k, MAX_RESULTS_PER_MODALITY)
    per_source = GROUPED_RESULTS_PER_SOURCE if group_by_source else None
    # When grouping, pull a wider candidate pool so collapsing per file still
    # leaves enough distinct files to fill the results.
    fetch_n = max(per_modality * 10, 50) if group_by_source else per_modality

    # Search text collection
    if "text" in modalities:
        try:
            text_collection = get_collection(TEXT_COLLECTION)
            count = text_collection.count()
            if count > 0:
                query_embedding = embed_texts_ollama([query])[0]
                text_results = text_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(fetch_n, count),
                    where=where,
                    include=["documents", "metadatas", "distances"],
                )
                results["results"]["text"] = _take_top(
                    _format_results(text_results), per_modality, per_source)
            else:
                results["results"]["text"] = []
        except Exception as e:
            results["results"]["text"] = {"error": str(e)}
    
    # Search image collection — backend determines which collection and embedding to use
    if "image" in modalities:
        try:
            if IMAGE_CAPTIONING_BACKEND == "clip":
                # Visual similarity: CLIP text → image embedding space
                collection = get_collection(IMAGE_COLLECTION)
                query_embedding = embed_text_clip([query])[0]
            else:
                # Semantic caption search: nomic text → same space as captions
                collection = get_collection(IMAGE_CAPTIONS_COLLECTION)
                query_embedding = embed_texts_ollama([query])[0]

            if collection.count() > 0:
                raw = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, MAX_RESULTS_PER_MODALITY),
                    where=where,
                    include=["documents", "metadatas", "distances"],
                )
                results["results"]["image"] = _format_results(raw)
            else:
                results["results"]["image"] = []
        except Exception as e:
            results["results"]["image"] = {"error": str(e)}
    
    # Search audio transcript collection (audio files only — video speech is
    # filtered out here and surfaced under the "video" modality instead).
    if "audio" in modalities:
        try:
            audio_collection = get_collection(AUDIO_COLLECTION)
            count = audio_collection.count()
            if count > 0:
                query_embedding = embed_texts_ollama([query])[0]
                audio_results = audio_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(fetch_n, count),
                    where=_build_where(folder_id, "audio_transcript"),
                    include=["documents", "metadatas", "distances"],
                )
                results["results"]["audio"] = _take_top(
                    _format_results(audio_results), per_modality, per_source)
            else:
                results["results"]["audio"] = []
        except Exception as e:
            results["results"]["audio"] = {"error": str(e)}

    # Search video. Two channels: the visual frames (what's shown) and, only when
    # include_video_speech is set, the spoken transcript (what was said). Visuals
    # are the default so every result is a real frame; speech is opt-in, and each
    # speech match is tagged with its nearest keyframe so it still shows a frame.
    if "video" in modalities:
        try:
            candidates: list[dict] = []

            # Visual: keyframe captions (nomic) or frame embeddings (clip backend).
            frames_col = get_collection(VIDEO_FRAMES_COLLECTION)
            frame_count = frames_col.count()
            if frame_count > 0:
                if IMAGE_CAPTIONING_BACKEND == "clip":
                    frame_query_embedding = embed_text_clip([query])[0]
                else:
                    frame_query_embedding = embed_texts_ollama([query])[0]
                frame_results = frames_col.query(
                    query_embeddings=[frame_query_embedding],
                    n_results=min(fetch_n, frame_count),
                    where=where,
                    include=["documents", "metadatas", "distances"],
                )
                candidates.extend(_format_results(frame_results))

            # Spoken: video transcripts (opt-in). Stored in the audio collection.
            if include_video_speech:
                audio_collection = get_collection(AUDIO_COLLECTION)
                audio_count = audio_collection.count()
                if audio_count > 0:
                    transcript_results = audio_collection.query(
                        query_embeddings=[embed_texts_ollama([query])[0]],
                        n_results=min(fetch_n, audio_count),
                        where=_build_where(folder_id, "video_transcript"),
                        include=["documents", "metadatas", "distances"],
                    )
                    candidates.extend(_format_results(transcript_results))

            video_hits = _take_top(candidates, per_modality, per_source)
            # Give every speech match a real frame: the keyframe nearest its moment.
            for hit in video_hits:
                md = hit.get("metadata") or {}
                if not md.get("frame_path"):
                    fp, fts = _nearest_keyframe(hit.get("file_path", ""),
                                                md.get("start_time") or 0)
                    if fp:
                        md["frame_path"] = fp
                        md["frame_timestamp"] = fts
                        hit["metadata"] = md
            results["results"]["video"] = video_hits
        except Exception as e:
            results["results"]["video"] = {"error": str(e)}

    return results


def _nearest_keyframe(video_path: str, t: float) -> tuple[str | None, float | None]:
    """Return (frame_path, timestamp) of the keyframe closest in time to t for a
    video, or (None, None) if it has no stored keyframes."""
    if not video_path:
        return (None, None)
    try:
        got = get_collection(VIDEO_FRAMES_COLLECTION).get(
            where={"source": video_path}, include=["metadatas"])
    except Exception:
        return (None, None)
    best = None  # (distance, frame_path, timestamp)
    for m in (got.get("metadatas") or []):
        ts = m.get("timestamp")
        fp = m.get("frame_path")
        if ts is None or not fp:
            continue
        dist = abs(ts - t)
        if best is None or dist < best[0]:
            best = (dist, fp, ts)
    return (best[1], best[2]) if best else (None, None)


def _format_results(chroma_results: dict) -> list[dict]:
    """Format ChromaDB results into a clean list."""
    output = []
    
    if not chroma_results["documents"] or not chroma_results["documents"][0]:
        return output
    
    for doc, meta, dist in zip(
        chroma_results["documents"][0],
        chroma_results["metadatas"][0],
        chroma_results["distances"][0],
    ):
        output.append({
            "text": doc,
            "score": round(1 - dist, 4),  # cosine distance → similarity
            "file_name": meta.get("file_name", ""),
            "file_path": meta.get("source", ""),
            "file_type": meta.get("file_type", ""),
            "modality": meta.get("modality", ""),
            "chunk_index": meta.get("chunk_index"),
            "metadata": {k: v for k, v in meta.items() 
                        if k not in ["source", "file_name", "file_type", 
                                    "modality", "folder_id", "chunk_index", "content_hash"]},
        })
    
    return output
