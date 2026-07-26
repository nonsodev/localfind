#!/bin/bash

# LocalFind Stop Script
# This script stops both backend and frontend

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

echo "Stopping LocalFind..."

# Read PIDs from files
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    kill "$BACKEND_PID" 2>/dev/null && echo "✓ Backend stopped (PID: $BACKEND_PID)"
    rm -f .backend.pid
fi

if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    kill "$FRONTEND_PID" 2>/dev/null && echo "✓ Frontend stopped (PID: $FRONTEND_PID)"
    rm -f .frontend.pid
fi

kill_port_processes() {
    local port="$1"
    local label="$2"
    local pids

    pids=$(lsof -ti:"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill 2>/dev/null || true
        echo "✓ Stopped remaining ${label} process(es) on port ${port}"
    fi
}

kill_port_processes "$BACKEND_PORT" "backend"
kill_port_processes "$FRONTEND_PORT" "frontend"

echo "LocalFind stopped."
