FROM golang:1.21-alpine
WORKDIR /app
COPY . /app
RUN go build -o /api_gateway ./cmd/gateway
CMD ["/api_gateway"]
