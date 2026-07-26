# Multimodal RAG System — Complete Guide

## Overview

This system implements a **fully local multimodal RAG** that can semantically search across:
- **Text documents** (PDF, DOCX, TXT, MD, CSV, RST)
- **Images** (JPG, PNG, GIF, BMP, WEBP)
- **Audio transcripts** (MP3, WAV, FLAC, M4A, OGG, AAC, MP4)

All processing happens locally — no external APIs required.

## Architecture

### Retrieval Models (All Local)

| Modality | Model | Purpose |
|----------|-------|---------|
| **Text** | `nomic-embed-text` (via Ollama) | Embeds text chunks from documents |
| **Images** | OpenCLIP (ViT-B-32) | Connects images and text in shared embedding space |
| **Audio transcripts** | `nomic-embed-text` (via Ollama) | Embeds transcript chunks produced by Whisper |

### How It Works

```
┌─────────────────────────────────────────────────────────┐
│              ChromaDB (Local Vector Store)              │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   text       │  │   images     │  │   audio      │ │
│  │  collection  │  │  collection  │  │  collection  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
         ↑                  ↑                  ↑
         │                  │                  │
    nomic-embed         OpenCLIP         nomic-embed
    (Ollama)         (ViT-B-32)         (Ollama)
```

### Query Flow

When you search with text like **"machine learning"**:

1. **Text embedding** → Query text collection → Returns matching PDF/doc chunks
2. **CLIP text embedding** → Query image collection → Returns matching images
3. **Text embedding** → Query audio transcript collection → Returns matching spoken content
4. **Merge results** → Return all three types ranked by similarity

## Installation

### 1. Install Python Dependencies

```bash
cd backend
uv pip install -r requirements.txt
```

This installs:
- `open-clip-torch` — Local CLIP for images
- `faster-whisper` — Local Whisper transcription
- `librosa` — Audio processing
- `pillow` — Image processing
- `torch` & `torchvision` — Deep learning framework

### 2. Install Ollama (for text embeddings)

```bash
# macOS
brew install ollama

# Start Ollama
ollama serve

# Pull the text embedding model
ollama pull nomic-embed-text
```

### 3. Download Model Checkpoints

**OpenCLIP** downloads automatically on first use.

**Whisper** downloads automatically on first transcription.

## Usage

### Start the Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Add a Folder

```bash
curl -X POST http://localhost:8000/folders \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/your/media/folder"}'
```

### Sync/Index the Folder

```bash
curl -X POST http://localhost:8000/sync/{folder_id}
```

This will:
- Walk the folder recursively
- Detect file types (text/image/audio)
- Extract content and embed with appropriate model
- Store in corresponding ChromaDB collection

### Search Across All Modalities

```bash
# Search everything
curl "http://localhost:8000/search?q=sunset%20beach&top_k=5"

# Search only images
curl "http://localhost:8000/search?q=sunset%20beach&modalities=image"

# Search images and audio transcripts
curl "http://localhost:8000/search?q=meeting%20summary&modalities=image,audio"

# Search within a specific folder
curl "http://localhost:8000/search?q=jazz&folder_id=1"
```

### Response Format

```json
{
  "query": "melancholic rainy evening",
  "results": {
    "text": [
      {
        "text": "...chunk content...",
        "score": 0.8234,
        "file_name": "poetry.pdf",
        "file_path": "/path/to/poetry.pdf",
        "file_type": "pdf",
        "modality": "text",
        "chunk_index": 3
      }
    ],
    "image": [
      {
        "text": "Image: rainy_street.jpg",
        "score": 0.7891,
        "file_name": "rainy_street.jpg",
        "file_path": "/path/to/rainy_street.jpg",
        "file_type": "image",
        "modality": "image",
        "metadata": {
          "width": 1920,
          "height": 1080,
          "format": "JPEG"
        }
      }
    ],
    "audio": [
      {
        "text": "...transcript chunk...",
        "score": 0.8567,
        "file_name": "nocturne.mp3",
        "file_path": "/path/to/nocturne.mp3",
        "file_type": "audio",
        "modality": "audio",
        "metadata": {
          "start_time": 45.2,
          "end_time": 120.5,
          "language": "en",
          "duration": 245.3
        }
      }
    ]
  }
}
```

## How Each Modality Works

### Text (PDFs, Documents)

1. **Parse** → Extract text from PDF/DOCX/TXT
2. **Chunk** → Split into 500-char chunks with 80-char overlap
3. **Embed** → Use Ollama's `nomic-embed-text`
4. **Store** → ChromaDB `localfind_text` collection

### Images

1. **Parse** → Load with PIL, convert to RGB
2. **Embed** → OpenCLIP image encoder
3. **Store** → ChromaDB `localfind_images` collection with file path as metadata

**Key insight**: CLIP learns a shared embedding space for images and text, so a text query like "sunset beach" can retrieve matching images.

### Audio

1. **Transcribe** → Whisper creates transcript segments with timestamps
2. **Chunk** → Transcript text is chunked like document text
3. **Embed** → Ollama `nomic-embed-text`
4. **Store** → ChromaDB `localfind_audio_transcripts` collection with timing metadata

**Key insight**: audio search is speech- and transcript-oriented, so text queries retrieve spoken content rather than raw sound similarity.

## Preventing Chunking Bias

The system limits results per modality to prevent text chunks from drowning out images/audio:

```python
MAX_RESULTS_PER_MODALITY = 10
```

This ensures balanced results across all three modalities.

## File Type Support

### Text Documents
- `.pdf` — PDFs
- `.docx`, `.doc` — Word documents
- `.txt` — Plain text
- `.md` — Markdown
- `.csv` — CSV files
- `.rst` — reStructuredText

### Images
- `.jpg`, `.jpeg` — JPEG images
- `.png` — PNG images
- `.gif` — GIF images
- `.bmp` — Bitmap images
- `.webp` — WebP images

### Audio
- `.mp3` — MP3 audio
- `.wav` — WAV audio
- `.flac` — FLAC lossless
- `.m4a` — M4A/AAC
- `.ogg` — Ogg Vorbis
- `.aac` — AAC audio

## Performance Considerations

### Model Loading
- Models load lazily on first use
- Subsequent queries reuse loaded models
- CLIP stays in memory for image inference
- Whisper is used during indexing, not search-time retrieval

### GPU Acceleration
- Automatically uses CUDA if available
- Falls back to CPU if no GPU
- For best performance, use a GPU

### Storage
- Text chunks: ~1KB per chunk
- Images: ~512 floats per embedding (~2KB)
- Audio transcripts: same embedding size as text chunks
- ChromaDB uses HNSW index for fast similarity search

## API Endpoints

### `GET /folders`
List all tracked folders with file counts.

### `POST /folders`
Add a new folder to track.
```json
{"path": "/path/to/folder"}
```

### `DELETE /folders/{id}`
Remove a folder and all its indexed content.

### `POST /sync/{folder_id}`
Trigger indexing for a folder (runs in background).

### `GET /sync/{folder_id}/status`
Check sync status.

### `GET /search`
Multimodal semantic search.

Query params:
- `q` — Search query (required)
- `top_k` — Results per modality (default: 5)
- `folder_id` — Filter by folder (optional)
- `modalities` — Comma-separated: `text,image,audio` (optional)

### `GET /stats`
Global statistics (total folders, files, chunks).

### `GET /health`
Health check.

## Troubleshooting

### "Ollama connection refused"
Make sure Ollama is running:
```bash
ollama serve
```

### "Whisper model not found"
Whisper downloads automatically on first transcription. Check your internet connection and backend logs.

### "Out of memory"
- Reduce batch size in embedding functions
- Use CPU instead of GPU
- Process fewer files at once

### "No results for images/audio"
- Make sure you've synced folders containing those file types
- Check that models loaded successfully (look for "✓ CLIP loaded" in logs)
- Try more descriptive queries

## Advanced: Custom Models

### Use a Different CLIP Model

Edit `multimodal_indexer.py`:
```python
_clip_model, _, _clip_preprocess = open_clip.create_model_and_transforms(
    "ViT-L-14",  # Larger, more accurate
    pretrained="laion2b_s32b_b82k",
    device=device,
)
```

### Use a Different Text Model

Edit `multimodal_indexer.py`:
```python
TEXT_EMBED_MODEL = "mxbai-embed-large"  # Or any Ollama model
```

Then pull it:
```bash
ollama pull mxbai-embed-large
```

## Example Use Cases

### 1. Personal Media Library
Index your entire photo/music/document collection and search semantically:
- "family vacation photos 2023"
- "upbeat workout music"
- "tax documents"

### 2. Content Creation
Find assets for projects:
- "minimalist logo designs"
- "ambient background music"
- "technical documentation about APIs"

### 3. Research
Search across papers, diagrams, and audio recordings:
- "neural network architectures"
- "climate change graphs"
- "interview transcripts about AI"

## Next Steps

1. **Frontend Integration**: Update the React frontend to display images/audio
2. **Thumbnail Generation**: Generate thumbnails for images
3. **Audio Playback**: Add audio player to frontend
4. **Metadata Extraction**: Extract EXIF from images, ID3 tags from audio
5. **Hybrid Search**: Combine semantic + keyword search
6. **Relevance Tuning**: Weight modalities differently based on query

## References

- [OpenCLIP](https://github.com/mlfoundations/open_clip) — Open source CLIP implementation
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — Fast local Whisper inference
- [ChromaDB](https://www.trychroma.com/) — Vector database
- [Ollama](https://ollama.ai/) — Local LLM/embedding server

---

**Built with ❤️ for fully local, privacy-first multimodal search.**
