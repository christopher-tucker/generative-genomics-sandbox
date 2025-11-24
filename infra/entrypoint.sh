#!/bin/sh
set -e

# Start FastAPI model server
echo "Starting FastAPI model server..."
cd /app/services/model_server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &
MODEL_PID=$!

# Start Go API Gateway
echo "Starting Go API Gateway..."
cd /app
./api-gateway
