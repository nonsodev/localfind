# LocalFind Quick Reference

One-page reference for the current repo layout and day-to-day commands.

## Start Services

```bash
# Terminal 1
ollama serve

# Terminal 2
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3
cd frontend
npm run dev
```

Optional convenience scripts:

```bash
./start.sh
./stop.sh
```

## Default URLs

| Service | URL |
|---------|-----|
| Frontend | `http://localhost:5173` |
| Backend API | `http://localhost:8000` |
| Ollama | `http://localhost:11434` |

## Useful Paths

| Path | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app entrypoint |
| `backend/config.py` | `.env` loading and backend settings |
| `backend/multimodal_indexer.py` | Indexing and search logic |
| `backend/audio_transcriber.py` | Whisper transcription |
| `frontend/src/pages/ModernHome.jsx` | Main UI page |
| `frontend/src/components/AgentChat.jsx` | Built-in agent chat UI |
| `mcp_server/server.py` | MCP server for Claude Desktop and other clients |

## Useful Commands

```bash
# Health
curl http://localhost:8000/health

# Stats
curl http://localhost:8000/stats

# List folders
curl http://localhost:8000/folders

# Search
curl "http://localhost:8000/search?q=machine+learning&top_k=5"

# Add folder
curl -X POST http://localhost:8000/folders \
  -H "Content-Type: application/json" \
  -d '{"path": "/absolute/path/to/folder"}'
```

## Claude Desktop MCP Config

```json
{
  "mcpServers": {
    "localfind": {
      "command": "python",
      "args": ["/absolute/path/to/localfind/mcp_server/server.py"],
      "env": {
        "BACKEND_URL": "http://localhost:8000"
      }
    }
  }
}
```

## Image Support Rules

- Built-in LocalFind agent: full image understanding
- Claude Desktop: full image understanding with Filesystem connector enabled
- Other MCP clients: usually text and audio only, with images returned as paths

## Environment Setup

```bash
uv venv
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```

Install Python dependencies:
```bash
cd backend
uv pip install -r requirements.txt

cd ../mcp_server
uv pip install -r requirements.txt
```

Windows note:
- Install Microsoft C++ Build Tools if native package builds fail.
