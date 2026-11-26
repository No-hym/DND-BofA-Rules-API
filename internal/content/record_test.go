package content

import (
	"os"
	"path/filepath"
	"testing"
)

func TestValidateRequiresStableProvenanceAndTranslations(t *testing.T) {
	r := Record{ID: "srd:rule-1", Category: "rule", Edition: "2024", PublisherID: "wotc", BookID: "srd-5.2.1", Source: "open5e:srd-5.2.1", License: "CC-BY-4.0", Version: "5.2.1", ExternalID: "rule-1", Translations: map[string]Translation{"en": {Name: "A rule"}}, Mechanics: map[string]any{}, Attribution: "Wizards of the Coast, CC BY 4.0"}
	if err := r.Validate(); err != nil {
		t.Fatalf("valid record rejected: %v", err)
	}
	r.Edition = "2025"
	if err := r.Validate(); err == nil {
		t.Fatal("unsupported edition accepted")
	}
}

func TestFingerprintIsDeterministic(t *testing.T) {
	r := Record{Mechanics: map[string]any{"challenge_rating": "1/4", "hp": 10}}
	a, err := r.Fingerprint()
	if err != nil {
		t.Fatal(err)
	}
	b, err := r.Fingerprint()
	if err != nil {
		t.Fatal(err)
	}
	if a != b || len(a) != 64 {
		t.Fatalf("unexpected fingerprint %q / %q", a, b)
	}
}
