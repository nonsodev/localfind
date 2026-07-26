# Agent Integration Guide

## Overview

LocalFind now includes an AI agent that can conversationally search through your indexed documents. The agent uses the **Model Context Protocol (MCP)** to communicate with the backend, making it reusable by other MCP clients like Claude Desktop.

## Architecture

```
┌─────────────────┐
│   Frontend UI   │
│  (Agent Chat)   │
└────────┬────────┘
         │ HTTP POST /agent/chat
         ▼
┌─────────────────┐
│  Backend API    │
│ (agent_service) │
└────────┬────────┘
         │ stdio
         ▼
┌─────────────────┐
│   MCP Server    │
│  (server.py)    │
└────────┬────────┘
         │ HTTP GET /search
         ▼
┌─────────────────┐
│  Backend API    │
│ (multimodal)    │
└─────────────────┘
```

## Components

### 1. Agent Service (`backend/agent_service.py`)
- Manages the AI agent lifecycle
- Uses `openai-agents` SDK with Ollama
- Spawns MCP server as subprocess
- Handles conversation state

### 2. MCP Server (`mcp_server/server.py`)
- Exposes document search as MCP tools
- Communicates with backend via HTTP
- Can be used by other MCP clients
- Tools:
  - `search_documents(query, top_k)` - Search across text, images, audio
  - `list_indexed_folders()` - List tracked folders
  - `get_index_stats()` - Get index statistics

### 3. Frontend (`frontend/src/components/AgentChat.jsx`)
- Chat UI with message history
- Toggle between Search and Agent modes
- Displays sources from agent responses

## Setup

### Prerequisites

1. **Ollama** with `gemma4:e4b` model:
   ```bash
   ollama pull gemma4:e4b
   ```

2. **Backend dependencies**:
   ```bash
   cd backend
   uv pip install -r requirements.txt
   ```

3. **MCP server dependencies** (optional, for standalone use):
   ```bash
   cd mcp_server
   uv pip install -r requirements.txt
   ```

4. **Windows build tools**:
   - Install Microsoft C++ Build Tools if dependency installation fails on Windows.

## Usage

### In LocalFind UI

1. Start the backend:
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Open http://localhost:5173

4. Toggle to **Agent** mode in the Search section

5. Ask questions like:
   - "What is machine learning?"
   - "Show me information about neural networks"
   - "Summarize the Q3 policy update"

### With Claude Desktop (or other MCP clients)

Add to your MCP client config:

```json
{
  "mcpServers": {
    "localagento": {
      "command": "python",
      "args": ["/path/to/localfind/mcp_server/server.py"],
      "env": {}
    }
  }
}
```

Make sure the backend is running at `http://localhost:8000`.

## API Endpoints

### POST `/agent/chat`

Chat with the agent.

**Request:**
```json
{
  "message": "What is machine learning?",
  "conversation_history": [
    {"role": "user", "content": "Previous message"},
    {"role": "assistant", "content": "Previous response"}
  ]
}
```

**Response:**
```json
{
  "response": "Machine learning is...",
  "sources": ["ml_basics.pdf", "neural_networks.pdf"],
  "success": true
}
```

### GET `/agent/stream?q=<query>`

Stream agent responses (Server-Sent Events).

## Configuration

### Change Agent Model

Edit `backend/agent_service.py`:

```python
AGENT_MODEL = "gemma4:e4b"  # Change to your preferred model
```

Supported models:
- `gemma4:e4b` (recommended)
- `llama3.1:8b`
- `mistral:7b`
- Any Ollama-compatible model

### Change Results Per Modality

Edit `mcp_server/server.py`:

```python
@mcp.tool()
async def search_documents(query: str, top_k: int = 2) -> dict:
    """
    top_k: Number of results per modality (default 2, max 5)
    """
```

### Change Backend URL

Edit `mcp_server/server.py`:

```python
BACKEND_URL = "http://localhost:8000"  # Change if backend runs elsewhere
```

## Troubleshooting

### Agent not responding

1. Check Ollama is running:
   ```bash
   ollama list
   ```

2. Check backend logs for errors

3. Verify MCP server can reach backend:
   ```bash
   curl http://localhost:8000/health
   ```

### MCP server errors

1. Check Python path in agent_service.py
2. Verify mcp_server/server.py exists
3. Check backend is running

### "Model not found" error

Pull the model:
```bash
ollama pull gemma4:e4b
```

### Slow responses

- Use a smaller model (e.g., `llama3.1:8b`)
- Reduce `top_k` in search_documents
- Ensure GPU acceleration is enabled in Ollama

## Development

### Testing Agent Service

```python
import asyncio
from backend import agent_service

async def test():
    result = await agent_service.chat_with_agent("What is AI?")
    print(result)

asyncio.run(test())
```

### Testing MCP Server

```bash
cd mcp_server
python server.py
# In another terminal:
# Use MCP inspector or client to test tools
```

### Adding New MCP Tools

Edit `mcp_server/server.py`:

```python
@mcp.tool()
async def your_new_tool(param: str) -> dict:
    """Tool description for the agent."""
    # Implementation
    return {"result": "..."}
```

## Performance

- **Agent response time**: 2-5 seconds (depends on model)
- **Search latency**: ~50ms per modality
- **Memory usage**: ~4GB (Gemma 4) to ~16GB (larger models)

## Security

- Agent runs locally, no data leaves your machine
- MCP server only accessible via localhost by default
- No API keys or external services required

## Future Enhancements

- [ ] Streaming responses in UI
- [ ] Conversation persistence
- [ ] Multi-turn context awareness
- [ ] Image viewing in agent responses
- [ ] Audio playback in agent responses
- [ ] Custom agent instructions per folder
- [ ] Agent memory/RAG over conversation history

## References

- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Ollama](https://ollama.ai/)
- [FastMCP](https://github.com/jlowin/fastmcp)
