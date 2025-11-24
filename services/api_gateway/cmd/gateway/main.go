package main

import (
	"bytes"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
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

	// ---- Static frontend serving ----
	distDir := "/app/web-client-dist"
	fileServer := http.FileServer(http.Dir(distDir))

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		// Don't hijack API routes (they're handled above)
		if strings.HasPrefix(r.URL.Path, "/api/") {
			http.NotFound(w, r)
			return
		}

		// Root path: serve index.html
		if r.URL.Path == "/" || r.URL.Path == "" {
			http.ServeFile(w, r, filepath.Join(distDir, "index.html"))
			return
		}

		// Try to serve an actual file from dist (e.g. /main.[hash].js, /179...js, /assets/...)
		relPath := strings.TrimPrefix(r.URL.Path, "/")
		candidate := filepath.Join(distDir, relPath)

		if info, err := os.Stat(candidate); err == nil && !info.IsDir() {
			fileServer.ServeHTTP(w, r)
			return
		}

		// Fallback: SPA route → index.html
		http.ServeFile(w, r, filepath.Join(distDir, "index.html"))
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
