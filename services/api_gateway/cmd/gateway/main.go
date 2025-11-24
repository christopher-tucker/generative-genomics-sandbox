package main

import (
	"bytes"
	"io"
	"log"
	"net/http"
	"os"
	"time"
)

const (
	defaultListenAddr     = ":8080"
	defaultModelServerURL = "http://localhost:8001" // override in Docker/ECS
	modelServerURLEnvVar  = "MODEL_SERVER_URL"

	readHeaderTimeout      = 5 * time.Second
	upstreamRequestTimeout = 15 * time.Second
)

func main() {
	// Where the model server lives
	modelServerURL := os.Getenv(modelServerURLEnvVar)
	if modelServerURL == "" {
		modelServerURL = defaultModelServerURL
	}
	log.Printf("Using model server at %s", modelServerURL)

	mux := http.NewServeMux()

	// Simple health check for the gateway itself
	mux.HandleFunc("/api/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ok","source":"go_gateway"}`))
	})

	// Main generate endpoint -> proxies to FastAPI /generate
	mux.HandleFunc("/api/generate", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		proxyGenerate(w, r, modelServerURL)
	})

	// Temporary root handler (later: serve React build here)
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		_, _ = w.Write([]byte("Generative Genomics API Gateway\n\nTry POST /api/generate"))
	})

	server := &http.Server{
		Addr:              defaultListenAddr,
		Handler:           loggingMiddleware(mux),
		ReadHeaderTimeout: readHeaderTimeout,
	}

	log.Printf("API Gateway listening on %s", defaultListenAddr)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server error: %v", err)
	}
}

// proxyGenerate forwards the JSON body to the FastAPI /generate endpoint
// and streams the JSON response back unchanged.
func proxyGenerate(w http.ResponseWriter, r *http.Request, modelServerURL string) {
	upstreamURL := modelServerURL + "/generate"

	// Read incoming body
	bodyBytes, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "failed to read request body", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	log.Printf("Proxying /api/generate -> %s", upstreamURL)

	client := &http.Client{Timeout: upstreamRequestTimeout}
	upReq, err := http.NewRequestWithContext(
		r.Context(),
		http.MethodPost,
		upstreamURL,
		bytes.NewReader(bodyBytes),
	)
	if err != nil {
		http.Error(w, "failed to create upstream request", http.StatusInternalServerError)
		return
	}
	upReq.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(upReq)
	if err != nil {
		log.Printf("error calling model server: %v", err)
		http.Error(w, "failed to reach model server", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	if _, err := io.Copy(w, resp.Body); err != nil {
		log.Printf("error copying upstream response: %v", err)
	}
}

// loggingMiddleware logs basic request info.
func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s from %s", r.Method, r.URL.Path, r.RemoteAddr)
		next.ServeHTTP(w, r)
	})
}
