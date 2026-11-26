package content

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestBundledCatalogSchemaAndCoverage(t *testing.T) {
	//translate: The canonical source_data and normalized mechanics remain in English; use the full
	// Russian stat-block text in translations.ru.description until localized machine-readable mechanics exist.
	//translate: Avatar of Death uses special HP (half the summoner's maximum), not a fixed HP number;
	// consumers must read mechanics.stat_block.stat_block_json.source_data.hp.special.
	//translate: These creatures have formula-based AC, so armor_class may be a string, not an integer:
	// srd:draconic-spirit, srd:giant-insect, srd:otherworldly-steed.
	root := filepath.Join("..", "..")
	records, err := LoadDir(filepath.Join(root, "data", "catalog"))
	if err != nil {
		t.Fatal(err)
	}
	if err = ValidateSchema(records, filepath.Join(root, "data", "schema", "entity.schema.json")); err != nil {
		t.Fatal(err)
	}
	expectedCategories := map[string]int{"monster": 336, "condition": 15, "item": 456, "equipment": 94, "spell": 339, "feat": 17, "background": 4, "species": 9}
	if len(records) != 1270 {
		t.Fatalf("expected 1270 bundled entities, got %d", len(records))
	}
	english, russianNames, russianFull, sourcedMonsterBlocks, sourcedConditions, sourcedOther := 0, 0, 0, 0, 0, 0
	categoryCounts := map[string]int{}
	for _, record := range records {
		categoryCounts[record.Category]++
		if _, ok := record.Translations["en"]; ok {
			english++
		}
		if russian, ok := record.Translations["ru"]; ok {
			russianNames++
			if russian.Description != "" {
				russianFull++
			}
			if russian.Status == "source" && russian.Description != "" {
				if record.Category == "monster" {
					sourcedMonsterBlocks++
				} else if record.Category == "condition" {
					sourcedConditions++
				} else {
					sourcedOther++
				}
				if !strings.Contains(record.Attribution, "Petr Radilov") || !strings.Contains(record.Attribution, "CC BY 4.0") {
					t.Errorf("sourced Russian translation %s is missing attribution", record.ID)
				}
			}
		}
	}
	for category, expected := range expectedCategories {
		if categoryCounts[category] != expected {
			t.Errorf("expected %d %s records, got %d", expected, category, categoryCounts[category])
		}
	}
	if english != 1270 || russianNames != 1270 || russianFull != 1100 || sourcedMonsterBlocks != 336 || sourcedConditions != 15 || sourcedOther != 749 {
		t.Fatalf("unexpected translations: en=%d ru names=%d full RU text=%d sourced monsters=%d sourced conditions=%d sourced other=%d", english, russianNames, russianFull, sourcedMonsterBlocks, sourcedConditions, sourcedOther)
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
