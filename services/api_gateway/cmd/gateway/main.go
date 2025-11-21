package main

import (
	"io"
	"log"
	"net/http"
	"os"
)

func proxyModel(w http.ResponseWriter, r *http.Request) {
	// Simple proxy to model server
	resp, err := http.Post("http://model_server:8001/generate", "application/json", r.Body)
	if err != nil {
		http.Error(w, "model server error", 502)
		return
	}
	defer resp.Body.Close()
	w.Header().Set("Content-Type", "application/json")
	io.Copy(w, resp.Body)
}

func main() {
	http.HandleFunc("/generate", proxyModel)
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Println("API Gateway listening on:", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
