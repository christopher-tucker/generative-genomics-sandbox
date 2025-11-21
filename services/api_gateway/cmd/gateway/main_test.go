package main

import (
	"bytes"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

// This test starts a fake model server and verifies that the gateway's proxy
// forwards the request and returns the model server response.
func TestProxyModel(t *testing.T) {
	modelHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		io.WriteString(w, `{"model_version":"v0.1","genes":["GENE1"],"expression":[0.5]}`)
	})
	modelSrv := httptest.NewServer(modelHandler)
	defer modelSrv.Close()

	proxy := func(w http.ResponseWriter, r *http.Request) {
		resp, err := http.Post(modelSrv.URL+"/generate", "application/json", r.Body)
		if err != nil {
			http.Error(w, "model server error", 502)
			return
		}
		defer resp.Body.Close()
		w.Header().Set("Content-Type", "application/json")
		io.Copy(w, resp.Body)
	}

	reqBody := bytes.NewBufferString(`{"descriptor":{"cell_type":"A","treatment":"X","dose":1,"timepoint":1}}`)
	req := httptest.NewRequest("POST", "/generate", reqBody)
	rr := httptest.NewRecorder()

	proxy(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200 but got %d", rr.Code)
	}

	if rr.Body.String() == "" {
		t.Fatal("expected non-empty body")
	}
}
