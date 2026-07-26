# LocalFind - Project Structure

Complete overview of the LocalFind project structure and components.

## 📁 Directory Structure

```
localagento/
├── .env.example               # Shared root env template for backend/frontend/scripts
├── backend/                    # Main LocalFind server
│   ├── main.py                # FastAPI server (port 8000)
│   ├── multimodal_indexer.py  # Multimodal indexing logic
│   ├── audio_transcriber.py   # Whisper audio transcription
│   ├── db.py                  # SQLite metadata database
│   ├── config.py              # Shared backend config + .env loading
│   ├── requirements.txt       # Python dependencies
│   ├── parsers/               # File parsers
│   │   ├── text_parser.py     # PDF, DOCX, TXT, MD
│   │   ├── image_parser.py    # JPG, PNG, GIF
│   │   └── audio_parser.py    # MP3, WAV, FLAC
│   └── chroma_db/             # ChromaDB vector storage
│
├── frontend/                   # Main LocalFind UI
│   ├── src/
│   │   ├── App.jsx            # Main app
│   │   ├── pages/
│   │   │   └── ModernHome.jsx # Search interface
│   │   └── components/
│   │       ├── MultimodalSearchBar.jsx
│   │       ├── MultimodalResultCard.jsx
│   │       ├── AudioPlayer.jsx
│   │       ├── FolderManager.jsx
│   │       └── StatsPanel.jsx
│   ├── package.json
│   └── vite.config.js         # Runs on port 5173
│
├── mcp_server/                # MCP bridge for external tool clients
│   ├── server.py              # MCP server entrypoint
│   └── requirements.txt       # MCP server dependencies
│
├── docs/                      # Project documentation
│   ├── ARCHITECTURE.md
│   ├── MULTIMODAL_RAG_GUIDE.md
│   ├── WHISPER_AUDIO_GUIDE.md
│   └── ...
├── start.sh                   # Convenience script to run backend + frontend
├── stop.sh                    # Convenience script to stop both processes
├── README.md                  # Main documentation
├── CONTRIBUTING.md            # Contribution guide
├── LICENSE                    # MIT License
└── .gitignore                 # Git ignore rules
```

## 🏗️ Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         LocalFind System                         │
│                                                                  │
│  ┌────────────────────┐              ┌────────────────────┐    │
│  │   Main Frontend    │              │  LocalFind Agent   │    │
│  │   (Port 5173)      │              │   (Port 3001)      │    │
│  │                    │              │                    │    │
│  │  - Search UI       │              │  - Chat UI         │    │
│  │  - Folder Manager  │              │  - Settings UI     │    │
│  │  - Stats Dashboard │              │                    │    │
│  └─────────┬──────────┘              └─────────┬──────────┘    │
│            │                                   │                │
│            │                                   │                │
│            ▼                                   ▼                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              LocalFind Server (Port 8000)               │   │
│  │                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │   │
│  │  │   Indexer    │  │   Search     │  │   API        │ │   │
│  │  │              │  │   Engine     │  │   Routes     │ │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────────┘ │   │
│  │         │                 │                            │   │
│  │         ▼                 ▼                            │   │
│  │  ┌──────────────────────────────────────────────┐     │   │
│  │  │           ChromaDB Vector Store              │     │   │
│  │  │                                              │     │   │
│  │  │  - localfind_text (text embeddings)            │     │   │
│  │  │  - localfind_images (image embeddings)         │     │   │
│  │  │  - localfind_audio_transcripts (audio text)    │     │   │
│  │  └──────────────────────────────────────────────┘     │   │
│  │                                                        │   │
│  │  ┌──────────────────────────────────────────────┐     │   │
│  │  │         SQLite Metadata Database             │     │   │
│  │  │  - folders, files, sync status               │     │   │
│  │  └──────────────────────────────────────────────┘     │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Ollama Server   │
                    │  (Port 11434)    │
                    │                  │
                    │  - Text Embed    │
                    │  - LLaVA (Agent) │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Whisper Model   │
                    │  (faster-whisper)│
                    │                  │
                    │  - Audio → Text  │
                    └──────────────────┘
```

## 🔄 Data Flow

### Indexing Flow

```
1. User adds folder in UI
   ↓
2. Backend scans folder for files
   ↓
3. For each file:
   ├─ Text files → Parse → Chunk → Embed (Ollama) → ChromaDB (text)
   ├─ Images → Parse → Embed (OpenCLIP) → ChromaDB (images)
   └─ Audio → Transcribe (Whisper) → Chunk → Embed (Ollama) → ChromaDB (audio)
   ↓
4. Metadata saved to SQLite
   ↓
5. UI shows updated stats
```

### Search Flow (Main UI)

```
1. User enters query in search bar
   ↓
2. Query embedded using Ollama
   ↓
3. Search all 3 ChromaDB collections in parallel:
   ├─ localfind_text
   ├─ localfind_images
   └─ localfind_audio_transcripts
   ↓
4. Results merged and ranked by similarity
   ↓
5. UI displays results with:
   ├─ Text: chunks with highlighting
   ├─ Images: thumbnails + metadata
   └─ Audio: waveform player + timestamps
```

### Agent Chat Flow

```
1. User sends message in chat
   ↓
2. Agent analyzes message
   ↓
3. If search needed:
   ├─ Query LocalFind server /search endpoint
   ├─ Receive top 2 results per modality
   └─ Format as context
   ↓
4. Agent generates response using:
   ├─ System prompt
   ├─ Conversation history
   ├─ User message
   └─ Search results (if any)
   ↓
5. Response sent to UI
   ↓
6. UI displays with markdown formatting
```

## 🔌 API Endpoints

### LocalFind Server (Port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/folders` | List tracked folders |
| POST | `/folders` | Add folder |
| DELETE | `/folders/{id}` | Remove folder |
| POST | `/sync/{folder_id}` | Sync folder |
| GET | `/sync/{folder_id}/status` | Sync status |
| GET | `/search` | Multimodal search |
| GET | `/stats` | Index statistics |
| GET | `/files/{path}` | Serve file |

### Agent And MCP Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agent/chat` | Built-in agent chat |
| GET | `/agent/stream` | Stream agent responses |
| stdio | `mcp_server/server.py` | MCP server transport for Claude Desktop |

## 📦 Dependencies

### Backend (LocalFind Server)

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
chromadb==0.5.5
ollama==0.3.3
pypdf==4.3.1
python-docx==1.1.2
pillow==10.4.0
faster-whisper==1.0.3
openai-clip==1.0.1
torch==2.4.1
torchvision==0.19.1
```

### MCP Server

```
fastmcp>=0.2.0
httpx==0.27.0
```

### Frontend

```
react==18.3.1
react-dom==18.3.1
vite==5.4.2
react-markdown==9.0.1
wavesurfer.js==7.8.2
```

## 🗄️ Database Schema

### SQLite (localfind_meta.db)

**folders table:**
```sql
CREATE TABLE folders (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**indexed_files table:**
```sql
CREATE TABLE indexed_files (
    id INTEGER PRIMARY KEY,
    folder_id INTEGER NOT NULL,
    file_path TEXT UNIQUE NOT NULL,
    content_hash TEXT NOT NULL,
    file_type TEXT NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (folder_id) REFERENCES folders(id)
);
```

### ChromaDB Collections

**localfind_text:**
- Embeddings: Ollama (nomic-embed-text)
- Metadata: source, chunk_index, file_name, folder_id

**localfind_images:**
- Embeddings: OpenCLIP (ViT-B-32)
- Metadata: source, file_name, width, height, format, folder_id

**localfind_audio_transcripts:**
- Embeddings: Ollama (nomic-embed-text)
- Metadata: source, chunk_index, file_name, start_time, end_time, folder_id

## 🚀 Startup Sequence

### Full System Startup

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start LocalFind Server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Start Main UI (optional)
cd frontend
npm run dev

# Terminal 4: Optional Claude Desktop / MCP setup
cd mcp_server
uv pip install -r requirements.txt
```

### Built-In Agent Usage

```bash
# Make sure LocalFind server, frontend, and Ollama are running
# Then open the UI and switch from Search to Agent
```

## 🔧 Configuration Files

### Backend Config

**backend/main.py:**
- API routes
- CORS settings
- Port: 8000

**backend/multimodal_indexer.py:**
- Chunk size: 500 chars
- Chunk overlap: 80 chars
- ChromaDB path: `./chroma_db`

**backend/audio_transcriber.py:**
- Whisper model: medium
- Compute type: auto (GPU/CPU)
- Chunk duration: 30s

### Frontend Config

**frontend/vite.config.js:**
- Port: 5173
- Proxy: `/api` → `http://localhost:8000`

**backend/config.py:**
- Root `.env` loading
- Backend host and port
- Ollama and frontend URLs

**mcp_server/server.py:**
- MCP tool definitions
- Uses `BACKEND_URL` to reach the backend
- Designed for Claude Desktop and compatible MCP clients

## 📊 Performance Characteristics

### Indexing Speed

- **Text**: ~100 pages/minute
- **Images**: ~50 images/minute
- **Audio**: ~1-2x realtime (CPU), ~10-20x (GPU)

### Search Speed

- **Text**: ~30-50ms
- **Images**: ~50-80ms
- **Audio**: ~50ms

### Storage

- **Text**: ~2KB per chunk
- **Images**: ~2KB per image
- **Audio**: ~1-2KB per minute + transcript JSON

### Memory Usage

- **Backend**: ~500MB-1GB
- **Frontend**: ~100-200MB
- **Ollama (nomic-embed-text)**: ~500MB
- **Ollama agent model**: depends on selected model

## 🔐 Security Considerations

- **100% Local**: No external API calls
- **No Telemetry**: No usage tracking
- **File Access**: Backend can only access indexed folders
- **CORS**: Configured for localhost only
- **No Authentication**: Designed for single-user local use

## 🧪 Testing

### Manual Testing

**Test LocalFind Server:**
```bash
curl http://localhost:8000/health
curl "http://localhost:8000/search?q=test&top_k=5"
```

**Test Built-In Agent:**
```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","conversation_history":[]}'
```

**Test Ollama:**
```bash
curl http://localhost:11434/api/tags
```

## 📝 Development Notes

### Adding New File Types

1. Create parser in `backend/parsers/`
2. Add to `multimodal_indexer.py`
3. Update UI to display new type
4. Update documentation

### Changing Embedding Models

**Text:**
- Edit `multimodal_indexer.py`
- Change `OLLAMA_MODEL`
- Re-index all documents

**Images:**
- Edit `multimodal_indexer.py`
- Change `CLIP_MODEL`
- Re-index all images

**Audio:**
- Edit `audio_transcriber.py`
- Change `WHISPER_MODEL_SIZE`
- Re-transcribe all audio

### Customizing Agent

**Backend agent behavior:**
- Edit `backend/agent_service.py`
- Adjust prompt, search behavior, or model usage there

---

**Last Updated**: May 2026  
**Version**: 2.0
