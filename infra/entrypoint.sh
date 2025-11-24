#!/bin/bash
set -e

MODEL_PID=""

# Cleanup function to kill model server
cleanup() {
    if [ -n "$MODEL_PID" ]; then
        echo "Shutting down model server (PID: $MODEL_PID)..."
        kill -TERM "$MODEL_PID" 2>/dev/null || true
        # Wait up to 5 seconds for graceful shutdown
        wait "$MODEL_PID" 2>/dev/null || sleep 1
        # Force kill if still running
        kill -KILL "$MODEL_PID" 2>/dev/null || true
    fi
}

# Set up signal handlers to cleanup on container shutdown
trap cleanup SIGTERM SIGINT EXIT

# Start FastAPI model server in background
echo "Starting FastAPI model server..."
cd /app/services/model_server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &
MODEL_PID=$!

# Start Go API Gateway in foreground (container exits when gateway exits)
echo "Starting Go API Gateway..."
cd /app
exec ./api-gateway
