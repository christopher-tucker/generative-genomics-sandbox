# --- Stage 1: Go API Gateway build ---
FROM golang:1.22 AS go-builder

WORKDIR /app/services/api_gateway

# Download Go deps (go.sum may not exist yet; go mod download will no-op if none)
COPY services/api_gateway/go.mod .
RUN go mod download

# Copy source and build
COPY services/api_gateway .
RUN go build -o /app/api-gateway ./cmd/gateway

# --- Stage 2: Build React frontend ---
FROM node:20 AS frontend-builder

WORKDIR /app/web-client

COPY web-client/package.json web-client/package-lock.json ./
RUN npm ci

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

# Install Python dependencies (cached separately from source)
COPY services/model_server/requirements.txt /app/services/model_server/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r /app/services/model_server/requirements.txt

# Copy model server code + models + preprocessed data
COPY services/model_server /app/services/model_server
COPY models /app/models
COPY data /app/data

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
