# --- Stage 1: Go API Gateway build ---
    FROM golang:1.22 AS go-builder

    WORKDIR /app
    
    # Copy Go module file and download deps (go.sum not present for this module)
    COPY services/api_gateway/go.mod ./services/api_gateway/
    WORKDIR /app/services/api_gateway
    RUN go mod download
    
    # Copy the rest of the Go source
    COPY services/api_gateway /app/services/api_gateway
    
    # Build the gateway binary
    RUN go build -o /app/api-gateway ./cmd/gateway
    
    # --- Stage 2: Build React frontend ---
    FROM node:20 AS frontend-builder
    
    WORKDIR /app/web-client
    
    COPY web-client/package.json web-client/package-lock.json ./
    RUN npm install
    
    COPY web-client ./
    RUN npm run build
    
    # --- Stage 3: Python runtime (FastAPI + PyTorch + Gateway + Frontend) ---
    FROM python:3.10-slim
    
    # Needed for numpy, pandas, scikit-learn
    RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
     && rm -rf /var/lib/apt/lists/*
    
    WORKDIR /app
    
    # Copy model server code + models + preprocessed data
    COPY services/model_server /app/services/model_server
    COPY models /app/models
    COPY data /app/data
    
    # Install Python dependencies
    COPY services/model_server/requirements.txt /app/services/model_server/requirements.txt
    RUN pip install --no-cache-dir -r /app/services/model_server/requirements.txt
    
    # Copy Go gateway binary
    COPY --from=go-builder /app/api-gateway /app/api-gateway
    
    # Copy frontend build output
    COPY --from=frontend-builder /app/web-client/dist /app/web-client-dist
    
    # Add entrypoint
    COPY infra/entrypoint.sh /app/entrypoint.sh
    RUN chmod +x /app/entrypoint.sh
    
    # Internal FastAPI URL for gateway
    ENV MODEL_SERVER_URL=http://127.0.0.1:8001
    
    EXPOSE 8080
    
    ENTRYPOINT ["/app/entrypoint.sh"]
    