import os
from pathlib import Path
from dotenv import load_dotenv

# Base Paths
BACKEND_DIR = Path(__file__).parent.absolute()
ROOT_DIR = BACKEND_DIR.parent

# Prefer a repo-root .env so backend, frontend, and helper scripts share one config.
# Fall back to backend/.env for people who run the backend in isolation.
ROOT_ENV_PATH = ROOT_DIR / ".env"
BACKEND_ENV_PATH = BACKEND_DIR / ".env"

if ROOT_ENV_PATH.exists():
    load_dotenv(ROOT_ENV_PATH)
elif BACKEND_ENV_PATH.exists():
    load_dotenv(BACKEND_ENV_PATH)
else:
    load_dotenv()

CHROMA_PATH = BACKEND_DIR / "chroma_db"
DB_PATH = BACKEND_DIR / "localfind_meta.db"
UPLOADS_DIR = BACKEND_DIR / "uploads"
# Extracted video keyframes are cached here so the UI can show thumbnails and
# the agent can re-read a frame. One subdirectory per indexed video.
VIDEO_FRAMES_DIR = BACKEND_DIR / "video_frames"

# Ollama Settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemma4:e4b")

# Image/video-frame indexing backend. Determines how images and video keyframes
# are turned into something searchable.
# Three tiers (set IMAGE_CAPTIONING_BACKEND in .env), move up only for better results:
#   clip          — OpenCLIP visual-similarity embeddings, ~400 MB pkg, no Ollama  (default)
#                   Lightest. No captions/OCR/agent image-reading — visual match only.
#   qwen2.5vl:3b  — captions + strong OCR/text-in-image, ~3.2 GB. Recommended upgrade.
#   gemma4:e2b    — top-quality captions, ~7 GB, heavier.
# For maximum quality, gemma4:e4b (~9.6 GB) is the top end; other Ollama vision tags work too.
#
# Changing this after indexing requires deleting chroma_db/ and re-syncing
# (clip and the caption backends use different collections).
IMAGE_CAPTIONING_BACKEND = os.getenv("IMAGE_CAPTIONING_BACKEND", "clip")

# Multilingual MoE text embedding model — supports ~100 languages, 958 MB.
TEXT_EMBED_MODEL = os.getenv("TEXT_EMBED_MODEL", "nomic-embed-text-v2-moe")

# Backend Settings
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
BACKEND_URL = os.getenv("BACKEND_URL", f"http://localhost:{BACKEND_PORT}")

# Whisper Settings
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "medium")

# ── Video indexing ────────────────────────────────────────────────────────────
# Videos are indexed as keyframes (each captioned like an image) plus a Whisper
# transcript of the audio track. Frames are chosen by scene-change detection so
# static footage doesn't produce hundreds of near-identical captions.
#
# VIDEO_SCENE_THRESHOLD: ffmpeg scene score (0-1) above which a frame is kept.
#   Lower = more frames/sensitive (0.2), higher = only big cuts (0.6). 0.4 is balanced.
# VIDEO_MAX_FRAMES: hard cap on captioned frames per video (evenly downsampled if exceeded).
# VIDEO_MIN_FRAME_GAP: minimum seconds between kept frames (dedups rapid cuts).
VIDEO_SCENE_THRESHOLD = float(os.getenv("VIDEO_SCENE_THRESHOLD", "0.4"))
VIDEO_MAX_FRAMES = int(os.getenv("VIDEO_MAX_FRAMES", "40"))
VIDEO_MIN_FRAME_GAP = float(os.getenv("VIDEO_MIN_FRAME_GAP", "1.5"))

# UI Settings
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Logging: INFO (default) for normal use, DEBUG to trace every step.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
