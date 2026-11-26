package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"reflect"
	"strconv"
	"strings"
	"time"

	"github.com/No-hym/DND-BofA-Rules-API/internal/content"
)

type open5ePage struct {
	Next    *string          `json:"next"`
	Results []map[string]any `json:"results"`
}

func syncOpen5e(args []string) error {
	fs := flag.NewFlagSet("sync-open5e", flag.ContinueOnError)
	endpoint := fs.String("url", "", "Open5e v2 paginated endpoint URL")
	category := fs.String("category", "", "local category identifier, e.g. monster or spell")
	edition := fs.String("edition", "", "rules edition: 2014 or 2024")
	publisher := fs.String("publisher-id", "wizards-of-the-coast", "publisher identifier")
	book := fs.String("book-id", "", "stable book identifier")
	license := fs.String("license", "", "SPDX/license identifier; verify this document's rights before import")
	version := fs.String("version", "", "upstream document version")
	source := fs.String("source-id", "", "source identifier, e.g. open5e:srd-2014")
	attribution := fs.String("attribution", "", "complete attribution notice required by source license")
	out := fs.String("out", "", "output canonical JSON file")
	if err := fs.Parse(args); err != nil {
		return err
	}
	for key, value := range map[string]string{"url": *endpoint, "category": *category, "edition": *edition, "book-id": *book, "license": *license, "version": *version, "source-id": *source, "attribution": *attribution, "out": *out} {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("--%s is required", key)
		}
	}
	if *edition != "2014" && *edition != "2024" {
		return errors.New("--edition must be 2014 or 2024")
	}
	start, err := url.Parse(*endpoint)
	if err != nil || (start.Scheme != "https" && start.Hostname() != "localhost" && start.Hostname() != "127.0.0.1") || (start.Hostname() != "api.open5e.com" && start.Hostname() != "localhost" && start.Hostname() != "127.0.0.1") {
		return errors.New("--url must use HTTPS (localhost is allowed for development)")
	}
	client := &http.Client{Timeout: 60 * time.Second}
	client.CheckRedirect = func(req *http.Request, via []*http.Request) error {
		if len(via) >= 5 || req.URL.Scheme != start.Scheme || !strings.EqualFold(req.URL.Host, start.Host) {
			return http.ErrUseLastResponse
		}
		return nil
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()
	current := start
	records := make([]content.Record, 0, 1024)
	seen := map[string]map[string]any{}
	pages := 0
	for current != nil {
		pages++
		if pages > 10000 {
			return errors.New("pagination safety limit exceeded")
		}
		if current.Scheme != start.Scheme || !strings.EqualFold(current.Host, start.Host) {
			return errors.New("Open5e pagination next URL changed origin; refusing to follow")
		}
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, current.String(), nil)
		if err != nil {
			return err
		}
		req.Header.Set("Accept", "application/json")
		req.Header.Set("User-Agent", "DND-BofA-Rules-Importer/1.0")
		resp, err := client.Do(req)
		if err != nil {
			return fmt.Errorf("fetch page %d: %w", pages, err)
		}
		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			body, _ := io.ReadAll(io.LimitReader(resp.Body, 2048))
			_ = resp.Body.Close()
			return fmt.Errorf("Open5e returned %s: %s", resp.Status, strings.TrimSpace(string(body)))
		}
		var page open5ePage
		dec := json.NewDecoder(io.LimitReader(resp.Body, 32<<20))
		err = dec.Decode(&page)
		_ = resp.Body.Close()
		if err != nil {
			return fmt.Errorf("decode page %d: %w", pages, err)
		}
		for _, raw := range page.Results {
			name := stringField(raw, "name")
			if name == "" {
				return fmt.Errorf("page %d has a record without name", pages)
			}
			external := stringField(raw, "slug")
			if external == "" {
				external = stringField(raw, "key")
			}
			if external == "" {
				external = stringField(raw, "id")
			}
			if external == "" {
				external = slugify(name)
			}
			id := slugify(*source + ":" + *edition + ":" + *category + ":" + external)
			if id == "" {
				return fmt.Errorf("cannot generate stable ID for %q", name)
			}
			if previous, exists := seen[id]; exists {
				if !reflect.DeepEqual(previous, raw) {
					return fmt.Errorf("conflicting duplicate source ID %q; refusing to choose silently", external)
				}
				continue
			}
			seen[id] = raw
			desc := stringField(raw, "desc")
			if desc == "" {
				desc = stringField(raw, "description")
			}
			records = append(records, content.Record{ID: id, Category: *category, Edition: *edition, PublisherID: *publisher, BookID: *book, Source: *source, License: *license, Version: *version, ExternalID: external, Translations: map[string]content.Translation{"en": {Name: name, Description: desc, Status: "source"}}, Mechanics: raw, Attribution: *attribution})
			if len(records) > 100000 {
				return errors.New("catalog exceeds 100000-record safety limit")
			}
		}
		if page.Next == nil || strings.TrimSpace(*page.Next) == "" {
			current = nil
		} else {
			next, err := url.Parse(*page.Next)
			if err != nil {
				return fmt.Errorf("invalid pagination URL: %w", err)
			}
			if !next.IsAbs() {
				next = start.ResolveReference(next)
			}
			current = next
		}
	}
	if len(records) == 0 {
		return errors.New("Open5e returned no records; refusing to write an empty snapshot")
	}
	for _, r := range records {
		if err := r.Validate(); err != nil {
			return err
		}
	}
	encoded, err := json.MarshalIndent(records, "", "  ")
	if err != nil {
		return err
	}
	encoded = append(encoded, '\n')
	if err = atomicWriteFile(*out, encoded, 0644); err != nil {
		return err
	}
	fmt.Printf("fetched %d unique records across %d pages; wrote %s\n", len(records), pages, *out)
	return nil
}
func stringField(record map[string]any, key string) string {
	v, ok := record[key]
	if !ok || v == nil {
		return ""
	}
	switch x := v.(type) {
	case string:
		return strings.TrimSpace(x)
	case float64:
		return strconv.FormatFloat(x, 'f', -1, 64)
	default:
		return ""
	}
}
func slugify(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	var b strings.Builder
	dash := false
	for _, r := range value {
		if r >= 'a' && r <= 'z' || r >= '0' && r <= '9' {
			b.WriteRune(r)
			dash = false
		} else if r == '-' || r == '_' || r == ':' {
			b.WriteRune(r)
			dash = false
		} else if !dash && b.Len() > 0 {
			b.WriteByte('-')
			dash = true
		}
	}
	return strings.Trim(b.String(), "-:")
}
