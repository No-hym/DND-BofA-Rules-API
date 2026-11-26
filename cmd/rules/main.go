package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log"
	"os"
	"sort"
	"strings"
	"time"

	"github.com/No-hym/DND-BofA-Rules-API/internal/content"
	_ "github.com/jackc/pgx/v5/stdlib"
)

func main() {
	if err := run(os.Args[1:]); err != nil {
		log.Printf("error: %v", err)
		os.Exit(1)
	}
}

func run(args []string) error {
	if len(args) == 0 {
		usage()
		return errors.New("missing command")
	}
	switch args[0] {
	case "validate":
		return validate(args[1:])
	case "import":
		return importData(args[1:])
	case "book":
		return book(args[1:])
	case "stats":
		return stats(args[1:])
	case "export":
		return exportData(args[1:])
	case "sync-open5e":
		return syncOpen5e(args[1:])
	case "translate":
		return translateFile(args[1:])
	default:
		usage()
		return fmt.Errorf("unknown command %q", args[0])
	}
}

func usage() {
	fmt.Fprintln(os.Stderr, `rules <validate|import|export|book|stats|sync-open5e|translate> [options]
  validate --dir data/catalog
  import --dir data/catalog [--dry-run]
  export --dir data/catalog --edition 2024 --category monster --out monsters.json
  book enable|disable <book-id>
  stats --dir data/catalog
  sync-open5e --url URL --category monster --edition 2014 --book-id srd-2014 --license CC-BY-4.0 --version 1 --source-id open5e:srd-2014 --attribution NOTICE --out data/imports/2014/monsters.json
  translate --file data/imports/2024/monsters.json --endpoint http://localhost:1234/v1/chat/completions --model local-model --source en --target ru`)
}

func rootFlag(command string, args []string) (string, bool, error) {
	fs := flag.NewFlagSet(command, flag.ContinueOnError)
	dir := fs.String("dir", "data/catalog", "catalog directory")
	dry := fs.Bool("dry-run", false, "validate without writing")
	err := fs.Parse(args)
	return *dir, *dry, err
}

func loadAndValidate(dir string) ([]content.Record, error) {
	records, err := content.LoadDir(dir)
	if err != nil {
		return nil, err
	}
	if err = content.ValidateSchema(records, "data/schema/entity.schema.json"); err != nil {
		return nil, err
	}
	seen := make(map[string]bool, len(records))
	for _, record := range records {
		if seen[record.ID] {
			return nil, fmt.Errorf("duplicate stable id %q", record.ID)
		}
		seen[record.ID] = true
	}
	return records, nil
}

func validate(args []string) error {
	dir, _, err := rootFlag("validate", args)
	if err != nil {
		return err
	}
	records, err := loadAndValidate(dir)
	if err != nil {
		return err
	}
	fmt.Printf("valid: %d entities in %s\n", len(records), dir)
	return nil
}

func importData(args []string) error {
	dir, dryRun, err := rootFlag("import", args)
	if err != nil {
		return err
	}
	records, err := loadAndValidate(dir)
	if err != nil {
		return err
	}
	if dryRun {
		fmt.Printf("dry run: %d valid records\n", len(records))
		return nil
	}
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		return errors.New("DATABASE_URL is required")
	}
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		return err
	}
	defer func() {
		if closeErr := db.Close(); closeErr != nil {
			log.Printf("close database: %v", closeErr)
		}
	}()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()
	if err = db.PingContext(ctx); err != nil {
		return fmt.Errorf("database not reachable (run migrations first): %w", err)
	}
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer func() {
		if rollbackErr := tx.Rollback(); rollbackErr != nil && !errors.Is(rollbackErr, sql.ErrTxDone) {
			log.Printf("rollback import transaction: %v", rollbackErr)
		}
	}()

	books := make(map[string]content.Record)
	for _, record := range records {
		books[record.BookID] = record
	}
	bookIDs := make([]string, 0, len(books))
	for id := range books {
		bookIDs = append(bookIDs, id)
	}
	sort.Strings(bookIDs)
	for _, id := range bookIDs {
		record := books[id]
		title := strings.ReplaceAll(id, "-", " ")
		sourceURL := "https://api.open5e.com/"
		if document, ok := record.Mechanics["source_document"].(map[string]any); ok {
			if value, ok := document["title"].(string); ok && strings.TrimSpace(value) != "" {
				title = value
			}
			if value, ok := document["permalink"].(string); ok && strings.TrimSpace(value) != "" {
				sourceURL = value
			}
		}
		if id == "srd-5.2.1" {
			title = "System Reference Document 5.2.1"
		}
		_, err = tx.ExecContext(ctx, `INSERT INTO books(id,publisher_id,title,edition,license_id,source_url)
			VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(id) DO UPDATE SET publisher_id=EXCLUDED.publisher_id,
			title=EXCLUDED.title,edition=EXCLUDED.edition,license_id=EXCLUDED.license_id,source_url=EXCLUDED.source_url,updated_at=now()`,
			id, record.PublisherID, title, record.Edition, record.License, sourceURL)
		if err != nil {
			return fmt.Errorf("upsert book %s: %w", id, err)
		}
	}

	for _, record := range records {
		fingerprint, err := record.Fingerprint()
		if err != nil {
			return err
		}
		mechanics, err := json.Marshal(record.Mechanics)
		if err != nil {
			return err
		}
		_, err = tx.ExecContext(ctx, `INSERT INTO entities(id,category,edition,publisher_id,book_id,source,license_id,source_version,external_id,mechanics,attribution,fingerprint)
			VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) ON CONFLICT(id) DO UPDATE SET category=EXCLUDED.category,
			edition=EXCLUDED.edition,publisher_id=EXCLUDED.publisher_id,book_id=EXCLUDED.book_id,source=EXCLUDED.source,
			license_id=EXCLUDED.license_id,source_version=EXCLUDED.source_version,external_id=EXCLUDED.external_id,
			mechanics=EXCLUDED.mechanics,attribution=EXCLUDED.attribution,fingerprint=EXCLUDED.fingerprint,updated_at=now()`,
			record.ID, record.Category, record.Edition, record.PublisherID, record.BookID, record.Source, record.License,
			record.Version, record.ExternalID, mechanics, record.Attribution, fingerprint)
		if err != nil {
			return fmt.Errorf("upsert %s: %w", record.ID, err)
		}
		for language, translation := range record.Translations {
			status := translation.Status
			if status == "" {
				status = "source"
			}
			translationVersion := translation.SourceVersion
			if translationVersion == "" {
				translationVersion = record.Version
			}
			if language != "en" && translationVersion != record.Version {
				status = "outdated"
			}
			_, err = tx.ExecContext(ctx, `INSERT INTO entity_translations(entity_id,language,name,description,translation_status,translated_at,source_version,glossary_version)
				VALUES($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT(entity_id,language) DO UPDATE SET name=EXCLUDED.name,
				description=EXCLUDED.description,translation_status=EXCLUDED.translation_status,translated_at=EXCLUDED.translated_at,
				source_version=EXCLUDED.source_version,glossary_version=EXCLUDED.glossary_version`,
				record.ID, language, translation.Name, translation.Description, status, content.TranslationDate(translation), translationVersion, translation.GlossaryVersion)
			if err != nil {
				return fmt.Errorf("upsert translation %s/%s: %w", record.ID, language, err)
			}
		}
	}
	if _, err = tx.ExecContext(ctx, `INSERT INTO import_runs(source,source_version,imported_count,skipped_count) VALUES('catalog','mixed',$1,0)`, len(records)); err != nil {
		return err
	}
	if err = tx.Commit(); err != nil {
		return err
	}
	fmt.Printf("imported/upserted %d entities\n", len(records))
	return nil
}

func book(args []string) error {
	if len(args) != 2 || (args[0] != "enable" && args[0] != "disable") {
		return errors.New("usage: rules book enable|disable <book-id>")
	}
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		return errors.New("DATABASE_URL is required")
	}
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		return err
	}
	defer func() {
		if closeErr := db.Close(); closeErr != nil {
			log.Printf("close database: %v", closeErr)
		}
	}()
	enabled := args[0] == "enable"
	result, err := db.Exec(`UPDATE books SET enabled=$1,updated_at=now() WHERE id=$2`, enabled, args[1])
	if err != nil {
		return err
	}
	count, _ := result.RowsAffected()
	if count == 0 {
		return fmt.Errorf("book %q not found", args[1])
	}
	fmt.Printf("book %s %s\n", args[1], args[0])
	return nil
}

func stats(args []string) error {
	dir, _, err := rootFlag("stats", args)
	if err != nil {
		return err
	}
	records, err := loadAndValidate(dir)
	if err != nil {
		return err
	}
	type aggregate struct {
		Count               int `json:"count"`
		EnglishRecords      int `json:"en_records"`
		RussianRecords      int `json:"ru_records"`
		RussianNames        int `json:"ru_names"`
		RussianDescriptions int `json:"ru_descriptions"`
		RussianFullText     int `json:"ru_name_and_description"`
		RussianReviewed     int `json:"ru_reviewed"`
	}
	result := map[string]aggregate{}
	for _, record := range records {
		key := record.Edition + "/" + record.Category
		value := result[key]
		value.Count++
		if _, ok := record.Translations["en"]; ok {
			value.EnglishRecords++
		}
		if translation, ok := record.Translations["ru"]; ok {
			value.RussianRecords++
			if strings.TrimSpace(translation.Name) != "" {
				value.RussianNames++
			}
			if strings.TrimSpace(translation.Description) != "" {
				value.RussianDescriptions++
			}
			if strings.TrimSpace(translation.Name) != "" && strings.TrimSpace(translation.Description) != "" {
				value.RussianFullText++
			}
			if translation.Status == "reviewed" {
				value.RussianReviewed++
			}
		}
		result[key] = value
	}
	encoded, err := json.MarshalIndent(result, "", "  ")
	if err == nil {
		fmt.Println(string(encoded))
	}
	return err
}
