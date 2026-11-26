package api

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestCatalogMetadataIsServedWithoutDatabase(t *testing.T) {
	handler := New(nil, slog.Default())
	for _, path := range []string{"/api/v1/catalog", "/api/v1/sources"} {
		recorder := httptest.NewRecorder()
		handler.Routes().ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, path, nil))
		if recorder.Code != http.StatusOK {
			t.Fatalf("%s: status %d", path, recorder.Code)
		}
		var payload map[string]any
		if err := json.Unmarshal(recorder.Body.Bytes(), &payload); err != nil {
			t.Fatalf("%s: invalid JSON: %v", path, err)
		}
		if payload["primary_edition"] != "2024" {
			t.Fatalf("%s: unexpected primary edition %v", path, payload["primary_edition"])
		}
	}
}
