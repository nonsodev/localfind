# Agent Quick Start

Use this when you want the fastest path to conversational search in LocalFind.

## What This Supports

- Text document search
- Audio transcript search
- Image understanding through the built-in LocalFind agent
- Image understanding through Claude Desktop when the Filesystem connector is enabled

## 1. Install Dependencies

```bash
cd backend
uv pip install -r requirements.txt

cd ../mcp_server
uv pip install -r requirements.txt
```

Windows note:
- Install Microsoft C++ Build Tools before installing Python dependencies.

## 2. Pull Ollama Models

```bash
ollama pull nomic-embed-text
ollama pull gemma4:e4b
```

## 3. Start LocalFind

Backend:

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

## 4. Use the Built-In Agent

1. Open `http://localhost:5173`
2. Go to the Search area
3. Switch from `Search` to `Agent`
4. Ask questions about your indexed content

Example prompts:
- `What is machine learning?`
- `Summarize the Q3 policy update`
- `Show me neural network diagrams`

## 5. Use Claude Desktop Instead

Add this to your Claude Desktop MCP config:

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

Notes:
- Claude Desktop can use text, audio, and image results.
- For image inspection, enable the Filesystem connector in Claude Desktop.
- If your backend is on another host or port, change `BACKEND_URL`.

## Limitations

- Generic MCP clients can connect to the LocalFind MCP server.
- In most non-Claude clients, images will only be returned as file paths.
- For reliable image understanding, use either the LocalFind agent or Claude Desktop.
