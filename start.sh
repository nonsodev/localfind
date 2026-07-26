#!/bin/bash

# LocalFind Startup Script
# This script starts both backend and frontend as a convenience entrypoint.

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
AGENT_MODEL="${AGENT_MODEL:-gemma4:e4b}"
TEXT_EMBED_MODEL="${TEXT_EMBED_MODEL:-nomic-embed-text-v2-moe}"

echo "================================================"
echo "  LocalFind - Local Multimodal RAG System"
echo "================================================"
echo ""

# Check if Ollama is running
echo "Checking Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama is not running!"
    echo "   Please start Ollama first:"
    echo "   $ ollama serve"
    echo ""
    exit 1
fi
echo "✓ Ollama is running"

# Check if the configured embedding model is available
echo "Checking for embedding model (${TEXT_EMBED_MODEL})..."
if ! ollama list | grep -q "${TEXT_EMBED_MODEL%%:*}"; then
    echo "⚠️  ${TEXT_EMBED_MODEL} model not found!"
    echo "   Pulling model (this may take a few minutes)..."
    ollama pull "${TEXT_EMBED_MODEL}"
fi
echo "✓ embedding model available"

# Check if the configured agent model is available (for agent)
echo "Checking for agent model (${AGENT_MODEL})..."
if ! ollama list | grep -q "${AGENT_MODEL}"; then
    echo "⚠️  ${AGENT_MODEL} model not found!"
    echo "   The agent feature will not work without this model."
    echo "   To enable agent, run: ollama pull ${AGENT_MODEL}"
    echo ""
else
    echo "✓ agent model available"
fi

# Check if backend dependencies are installed
echo "Checking backend dependencies..."
if ! python -c "import fastapi, chromadb, faster_whisper" 2>/dev/null; then
    echo "⚠️  Backend dependencies not installed!"
    echo "   Installing dependencies..."
    cd backend
    pip install -r requirements.txt
    cd ..
fi
echo "✓ Backend dependencies installed"

# Check if frontend dependencies are installed
echo "Checking frontend dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    echo "⚠️  Frontend dependencies not installed!"
    echo "   Installing dependencies..."
    cd frontend
    npm install
    cd ..
fi
echo "✓ Frontend dependencies installed"

echo ""
echo "================================================"
echo "  Starting LocalFind..."
echo "================================================"
echo ""

# Start backend in background
echo "Starting backend on http://localhost:${BACKEND_PORT}..."
cd backend
python main.py > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; then
        echo "✓ Backend started successfully"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ Backend failed to start. Check backend.log for errors."
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Start frontend in background
echo "Starting frontend on http://localhost:${FRONTEND_PORT}..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "Waiting for frontend to start..."
sleep 3

echo ""
echo "================================================"
echo "  ✓ LocalFind is running!"
echo "================================================"
echo ""
echo "  Backend:  http://localhost:${BACKEND_PORT}"
echo "  Frontend: http://localhost:${FRONTEND_PORT}"
echo ""
echo "  Backend logs:  tail -f backend.log"
echo "  Frontend logs: tail -f frontend.log"
echo ""
echo "  To stop: Press Ctrl+C or run: ./stop.sh"
echo ""
echo "================================================"
echo ""

# Save PIDs for stop script
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

cleanup() {
    echo ""
    echo "Stopping LocalFind..."
    ./stop.sh
    echo "Stopped."
    exit 0
}

# Wait for user interrupt
trap cleanup INT TERM

# Keep script running
wait
