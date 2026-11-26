package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/No-hym/DND-BofA-Rules-API/internal/content"
)

type glossary struct {
	Version string            `json:"version"`
	Terms   map[string]string `json:"terms"`
}
type chatRequest struct {
	Model          string        `json:"model"`
	Messages       []chatMessage `json:"messages"`
	ResponseFormat any           `json:"response_format"`
}
type chatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}
type chatResponse struct {
	Choices []struct {
		Message chatMessage `json:"message"`
	} `json:"choices"`
}
type localizedText struct {
	Name        string `json:"name"`
	Description string `json:"description"`
}

func translateFile(args []string) error {
	fs := flag.NewFlagSet("translate", flag.ContinueOnError)
	file := fs.String("file", "", "canonical JSON batch file")
	endpoint := fs.String("endpoint", "", "OpenAI-compatible chat-completions URL")
	model := fs.String("model", "", "model identifier")
	source := fs.String("source", "en", "source language: en or ru")
	target := fs.String("target", "ru", "target language: en or ru")
	glossaryPath := fs.String("glossary", "data/glossary/en-ru.json", "terminology glossary JSON")
	apiKeyEnv := fs.String("api-key-env", "LLM_API_KEY", "environment variable holding optional provider key")
	maxRecords := fs.Int("max", 100, "maximum records to translate")
	force := fs.Bool("force", false, "replace existing translations, including reviewed ones")
	dryRun := fs.Bool("dry-run", false, "report work without calling the model or writing")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if *file == "" || *model == "" || *endpoint == "" {
		return errors.New("--file, --endpoint and --model are required")
	}
	if (*source != "en" && *source != "ru") || (*target != "en" && *target != "ru") || *source == *target {
		return errors.New("source and target must be different languages chosen from en/ru")
	}
	if *maxRecords < 1 || *maxRecords > 1000 {
		return errors.New("--max must be from 1 to 1000")
	}
	endpointURL, err := url.Parse(*endpoint)
	if err != nil || endpointURL.Host == "" || (endpointURL.Scheme != "https" && endpointURL.Hostname() != "localhost" && endpointURL.Hostname() != "127.0.0.1") {
		return errors.New("--endpoint must use HTTPS (localhost is allowed for local LLMs)")
	}
	var lexicon glossary
	glossaryData, err := os.ReadFile(*glossaryPath)
	if err != nil {
		return err
	}
	if err = json.Unmarshal(glossaryData, &lexicon); err != nil {
		return fmt.Errorf("read glossary: %w", err)
	}
	if lexicon.Version == "" {
		return errors.New("glossary must define a version")
	}
	encoded, err := os.ReadFile(*file)
	if err != nil {
		return err
	}
	var records []content.Record
	decoder := json.NewDecoder(bytes.NewReader(encoded))
	decoder.DisallowUnknownFields()
	if err = decoder.Decode(&records); err != nil {
		return err
	}
	for _, record := range records {
		if err = record.Validate(); err != nil {
			return fmt.Errorf("%s: %w", record.ID, err)
		}
	}
	if err = content.ValidateSchema(records, "data/schema/entity.schema.json"); err != nil {
		return err
	}
	work := make([]int, 0)
	for i, record := range records {
		if _, exists := record.Translations[*source]; !exists {
			continue
		}
		if old, exists := record.Translations[*target]; exists && !*force && old.Status == "reviewed" {
			continue
		}
		if _, exists := record.Translations[*target]; exists && !*force {
			continue
		}
		work = append(work, i)
		if len(work) == *maxRecords {
			break
		}
	}
	if *dryRun {
		fmt.Printf("would translate %d/%d records (%s -> %s)\n", len(work), len(records), *source, *target)
		return nil
	}
	if len(work) == 0 {
		fmt.Println("no untranslated records found")
		return nil
	}
	client := &http.Client{Timeout: 90 * time.Second, CheckRedirect: func(_ *http.Request, _ []*http.Request) error { return http.ErrUseLastResponse }}
	key := os.Getenv(*apiKeyEnv)
	for n, index := range work {
		record := &records[index]
		input := record.Translations[*source]
		prompt := "Translate D&D rules content faithfully from " + *source + " to " + *target + ". Preserve game mechanics, numbers, dice notation, markup, and names. Return only a JSON object with string fields name and description. Apply this glossary (source term to target term): "
		glossaryTerms := lexicon.Terms
		if *source == "ru" {
			glossaryTerms = make(map[string]string, len(lexicon.Terms))
			for english, russian := range lexicon.Terms {
				glossaryTerms[russian] = english
			}
		}
		terms, err := json.Marshal(glossaryTerms)
		if err != nil {
			return err
		}
		payload, err := json.Marshal(struct {
			Name        string `json:"name"`
			Description string `json:"description"`
		}{input.Name, input.Description})
		if err != nil {
			return err
		}
		requestBody := chatRequest{Model: *model, ResponseFormat: map[string]string{"type": "json_object"}, Messages: []chatMessage{{Role: "system", Content: prompt + string(terms)}, {Role: "user", Content: string(payload)}}}
		body, err := json.Marshal(requestBody)
		if err != nil {
			return err
		}
		req, err := http.NewRequest(http.MethodPost, endpointURL.String(), bytes.NewReader(body))
		if err != nil {
			return err
		}
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Accept", "application/json")
		if key != "" {
			req.Header.Set("Authorization", "Bearer "+key)
		}
		resp, err := client.Do(req)
		if err != nil {
			return fmt.Errorf("translate %s: %w", record.ID, err)
		}
		responseBody, readErr := io.ReadAll(io.LimitReader(resp.Body, 2<<20))
		if closeErr := resp.Body.Close(); readErr == nil {
			readErr = closeErr
		}
		if readErr != nil {
			return readErr
		}
		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			return fmt.Errorf("translation provider returned %s: %s", resp.Status, strings.TrimSpace(string(responseBody)))
		}
		var response chatResponse
		if err = json.Unmarshal(responseBody, &response); err != nil || len(response.Choices) == 0 {
			return fmt.Errorf("invalid chat-completions response for %s", record.ID)
		}
		var translated localizedText
		if err = json.Unmarshal([]byte(response.Choices[0].Message.Content), &translated); err != nil {
			return fmt.Errorf("model did not return JSON for %s: %w", record.ID, err)
		}
		if strings.TrimSpace(translated.Name) == "" {
			return fmt.Errorf("model returned an empty name for %s", record.ID)
		}
		record.Translations[*target] = content.Translation{Name: translated.Name, Description: translated.Description, Status: "machine", UpdatedAt: time.Now().UTC().Format("2006-01-02"), SourceVersion: record.Version, GlossaryVersion: lexicon.Version}
		fmt.Printf("translated %d/%d: %s\n", n+1, len(work), record.ID)
	}
	output, err := json.MarshalIndent(records, "", "  ")
	if err != nil {
		return err
	}
	output = append(output, '\n')
	if err = atomicWriteFile(*file, output, 0644); err != nil {
		return err
	}
	fmt.Printf("updated %s; machine translations must be reviewed before publication\n", filepath.Clean(*file))
	return nil
}
