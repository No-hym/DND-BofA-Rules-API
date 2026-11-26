package content

import (
	"os"
	"path/filepath"
	"testing"
)

func TestBundledCatalogSchemaAndCoverage(t *testing.T) {
	root := filepath.Join("..", "..")
	records, err := LoadDir(filepath.Join(root, "data", "catalog"))
	if err != nil {
		t.Fatal(err)
	}
	if err = ValidateSchema(records, filepath.Join(root, "data", "schema", "entity.schema.json")); err != nil {
		t.Fatal(err)
	}
	if len(records) != 336 {
		t.Fatalf("expected 336 bundled entities, got %d", len(records))
	}
	english, russianNames, russianFull := 0, 0, 0
	for _, record := range records {
		if _, ok := record.Translations["en"]; ok {
			english++
		}
		if russian, ok := record.Translations["ru"]; ok {
			russianNames++
			if russian.Description != "" {
				russianFull++
			}
		}
	}
	if english != 336 || russianNames != 64 || russianFull != 14 {
		t.Fatalf("unexpected translations: en=%d ru names=%d full text=%d", english, russianNames, russianFull)
	}
}

func TestLoadDirRejectsTrailingJSON(t *testing.T) {
	dir := t.TempDir()
	data := `[] []`
	if err := os.WriteFile(filepath.Join(dir, "records.json"), []byte(data), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := LoadDir(dir); err == nil {
		t.Fatal("trailing JSON was accepted")
	}
}
