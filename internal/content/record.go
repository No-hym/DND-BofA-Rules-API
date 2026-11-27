package content

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type Translation struct {
	Name            string `json:"name"`
	Description     string `json:"description"`
	Status          string `json:"status,omitempty"`
	UpdatedAt       string `json:"updated_at,omitempty"`
	SourceVersion   string `json:"source_version,omitempty"`
	GlossaryVersion string `json:"glossary_version,omitempty"`
}

type Record struct {
	ID           string                 `json:"id"`
	Category     string                 `json:"category"`
	Edition      string                 `json:"edition"`
	PublisherID  string                 `json:"publisher_id"`
	BookID       string                 `json:"book_id"`
	Source       string                 `json:"source"`
	License      string                 `json:"license"`
	Version      string                 `json:"version"`
	ExternalID   string                 `json:"external_id"`
	Translations map[string]Translation `json:"translations"`
	Mechanics    map[string]any         `json:"mechanics"`
	Attribution  string                 `json:"attribution"`
}

func LoadDir(root string) ([]Record, error) {
	var records []Record
	err := filepath.WalkDir(root, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if entry.IsDir() || filepath.Ext(path) != ".json" || strings.HasSuffix(path, ".schema.json") {
			return nil
		}
		b, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		batch, err := decodeRecords(b)
		if err != nil {
			return fmt.Errorf("%s: %w", path, err)
		}
		for i := range batch {
			if err := batch[i].Validate(); err != nil {
				return fmt.Errorf("%s record %d: %w", path, i, err)
			}
		}
		records = append(records, batch...)
		return nil
	})
	if err != nil {
		return nil, err
	}
	return records, nil
}

// decodeRecords accepts either a JSON array of records (legacy aggregated
// catalog files) or a single record object (one file per record, a "card").
func decodeRecords(b []byte) ([]Record, error) {
	trimmed := bytes.TrimSpace(b)
	if len(trimmed) == 0 {
		return nil, fmt.Errorf("empty JSON document")
	}
	dec := json.NewDecoder(bytes.NewReader(b))
	dec.DisallowUnknownFields()
	var batch []Record
	if trimmed[0] == '{' {
		var single Record
		if err := dec.Decode(&single); err != nil {
			return nil, err
		}
		batch = []Record{single}
	} else {
		if err := dec.Decode(&batch); err != nil {
			return nil, err
		}
	}
	var trailing any
	if err := dec.Decode(&trailing); err != io.EOF {
		if err == nil {
			return nil, fmt.Errorf("unexpected trailing JSON value")
		}
		return nil, fmt.Errorf("trailing JSON: %w", err)
	}
	return batch, nil
}

func (r Record) Validate() error {
	for name, value := range map[string]string{"id": r.ID, "category": r.Category, "edition": r.Edition, "publisher_id": r.PublisherID, "book_id": r.BookID, "source": r.Source, "license": r.License, "version": r.Version, "external_id": r.ExternalID, "attribution": r.Attribution} {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%s is required", name)
		}
	}
	if r.Edition != "2014" && r.Edition != "2024" {
		return fmt.Errorf("edition must be 2014 or 2024")
	}
	if len(r.Translations) == 0 {
		return fmt.Errorf("at least one translation is required")
	}
	for lang, t := range r.Translations {
		if lang != "en" && lang != "ru" {
			return fmt.Errorf("unsupported language %q", lang)
		}
		if strings.TrimSpace(t.Name) == "" {
			return fmt.Errorf("translation %s has an empty name", lang)
		}
		if t.Status != "" && t.Status != "source" && t.Status != "machine" && t.Status != "reviewed" && t.Status != "outdated" {
			return fmt.Errorf("invalid translation status %q", t.Status)
		}
	}
	if r.Mechanics == nil {
		return fmt.Errorf("mechanics must be a JSON object")
	}
	return nil
}

func (r Record) Fingerprint() (string, error) {
	b, err := json.Marshal(r.Mechanics)
	if err != nil {
		return "", err
	}
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:]), nil
}

func TranslationDate(t Translation) *time.Time {
	if t.UpdatedAt == "" {
		return nil
	}
	v, err := time.Parse("2006-01-02", t.UpdatedAt)
	if err != nil {
		return nil
	}
	return &v
}
