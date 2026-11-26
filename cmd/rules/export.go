package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"strings"

	"github.com/No-hym/DND-BofA-Rules-API/internal/content"
)

func exportData(args []string) error {
	fs := flag.NewFlagSet("export", flag.ContinueOnError)
	dir := fs.String("dir", "data/catalog", "catalog directory")
	out := fs.String("out", "", "output canonical JSON file (required)")
	edition := fs.String("edition", "", "filter by rules edition")
	category := fs.String("category", "", "filter by category")
	publisher := fs.String("publisher", "", "filter by publisher ID")
	book := fs.String("book", "", "filter by book ID")
	language := fs.String("lang", "", "optional single language export: en or ru")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if *out == "" {
		return errors.New("--out is required")
	}
	if *edition != "" && *edition != "2014" && *edition != "2024" {
		return errors.New("--edition must be 2014 or 2024")
	}
	if *language != "" && *language != "en" && *language != "ru" {
		return errors.New("--lang must be en or ru")
	}
	records, err := loadAndValidate(*dir)
	if err != nil {
		return err
	}
	selected := make([]content.Record, 0)
	for _, record := range records {
		if *edition != "" && record.Edition != *edition || *category != "" && record.Category != *category || *publisher != "" && record.PublisherID != *publisher || *book != "" && record.BookID != *book {
			continue
		}
		if *language != "" {
			translation, exists := record.Translations[*language]
			if !exists {
				continue
			}
			record.Translations = map[string]content.Translation{*language: translation}
		}
		selected = append(selected, record)
	}
	if len(selected) == 0 {
		return errors.New("no records matched the export filters")
	}
	encoded, err := json.MarshalIndent(selected, "", "  ")
	if err != nil {
		return err
	}
	encoded = append(encoded, '\n')
	if strings.TrimSpace(*out) == "-" {
		_, err = os.Stdout.Write(encoded)
		return err
	}
	if err = atomicWriteFile(*out, encoded, 0644); err != nil {
		return err
	}
	fmt.Printf("exported %d entities to %s\n", len(selected), *out)
	return nil
}
