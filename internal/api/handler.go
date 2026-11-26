package api

import (
	"context"
	"embed"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

//go:embed openapi.yaml
var docs embed.FS

type Handler struct {
	pool *pgxpool.Pool
	log  *slog.Logger
}

func New(pool *pgxpool.Pool, log *slog.Logger) *Handler { return &Handler{pool: pool, log: log} }

type Entity struct {
	ID                string          `json:"id"`
	Category          string          `json:"category"`
	Edition           string          `json:"edition"`
	PublisherID       string          `json:"publisher_id"`
	BookID            string          `json:"book_id"`
	Source            string          `json:"source"`
	License           string          `json:"license"`
	Version           string          `json:"version"`
	Language          string          `json:"language"`
	Name              string          `json:"name"`
	Description       string          `json:"description"`
	TranslationStatus string          `json:"translation_status"`
	Attribution       string          `json:"attribution"`
	Mechanics         json.RawMessage `json:"mechanics"`
}
type listResponse struct {
	Data       []Entity   `json:"data"`
	Pagination pagination `json:"pagination"`
}
type pagination struct {
	Limit   int  `json:"limit"`
	Offset  int  `json:"offset"`
	Count   int  `json:"count"`
	HasMore bool `json:"has_more"`
}
type apiError struct {
	Error   string `json:"error"`
	Message string `json:"message"`
}

func (h *Handler) Routes() http.Handler {
	r := chi.NewRouter()
	r.Get("/healthz", func(w http.ResponseWriter, _ *http.Request) { writeJSON(w, 200, map[string]string{"status": "ok"}) })
	r.Get("/readyz", h.ready)
	r.Get("/openapi.yaml", func(w http.ResponseWriter, _ *http.Request) {
		b, err := fs.ReadFile(docs, "openapi.yaml")
		if err != nil {
			writeError(w, 500, "internal_error", "OpenAPI document unavailable")
			return
		}
		w.Header().Set("Content-Type", "application/yaml; charset=utf-8")
		_, _ = w.Write(b)
	})
	r.Route("/api/v1", func(r chi.Router) {
		r.Get("/entities", h.list)
		r.Get("/entities/{id}", h.get)
		r.Get("/export", h.export)
		r.Get("/editions", h.editions)
		r.Get("/categories", h.categories)
		r.Get("/catalog", h.catalogMetadata)
		r.Get("/sources", h.catalogMetadata)
	})
	return r
}
func (h *Handler) ready(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := h.pool.Ping(ctx); err != nil {
		writeError(w, 503, "not_ready", "Database is unavailable")
		return
	}
	writeJSON(w, 200, map[string]string{"status": "ready"})
}

const selectEntity = `SELECT e.id,e.category,e.edition,e.publisher_id,e.book_id,e.source,e.license_id,e.source_version,t.language,t.name,t.description,t.translation_status,e.attribution,e.mechanics FROM entities e JOIN books b ON b.id=e.book_id AND b.enabled JOIN LATERAL (SELECT x.language,x.name,x.description,x.translation_status FROM entity_translations x WHERE x.entity_id=e.id AND x.language IN ($1,'en') ORDER BY CASE WHEN x.language=$1 THEN 0 ELSE 1 END LIMIT 1) t ON true`

func (h *Handler) get(w http.ResponseWriter, r *http.Request) {
	lang, err := language(r)
	if err != nil {
		writeError(w, 400, "invalid_language", err.Error())
		return
	}
	id := chi.URLParam(r, "id")
	ctx, cancel := context.WithTimeout(r.Context(), 4*time.Second)
	defer cancel()
	row, err := scanEntity(h.pool.QueryRow(ctx, selectEntity+` WHERE e.id=$2`, lang, id))
	if errors.Is(err, pgx.ErrNoRows) && lang != "en" {
		row, err = scanEntity(h.pool.QueryRow(ctx, selectEntity+` WHERE e.id=$2`, "en", id))
	}
	if errors.Is(err, pgx.ErrNoRows) {
		writeError(w, 404, "not_found", "Entity not found")
		return
	}
	if err != nil {
		h.internalError(w, r, err)
		return
	}
	writeJSON(w, 200, row)
}
func (h *Handler) list(w http.ResponseWriter, r *http.Request)   { h.query(w, r, false) }
func (h *Handler) export(w http.ResponseWriter, r *http.Request) { h.query(w, r, true) }
func (h *Handler) query(w http.ResponseWriter, r *http.Request, export bool) {
	q := r.URL.Query()
	lang, err := language(r)
	if err != nil {
		writeError(w, 400, "invalid_language", err.Error())
		return
	}
	limit := 100
	offset := 0
	if export {
		limit = 5000
	}
	if v := q.Get("limit"); v != "" {
		limit, err = strconv.Atoi(v)
		maxLimit := 500
		if export {
			maxLimit = 5000
		}
		if err != nil || limit < 1 || limit > maxLimit {
			writeError(w, 400, "invalid_limit", fmt.Sprintf("limit must be an integer from 1 to %d", maxLimit))
			return
		}
	}
	if v := q.Get("offset"); v != "" {
		offset, err = strconv.Atoi(v)
		if err != nil || offset < 0 || offset > 1000000 {
			writeError(w, 400, "invalid_offset", "offset must be a non-negative integer")
			return
		}
	}
	if export {
		offset = 0
	}
	category, edition, publisher, book, search := q.Get("category"), q.Get("edition"), q.Get("publisher"), q.Get("book"), strings.TrimSpace(q.Get("q"))
	if edition != "" && edition != "2014" && edition != "2024" {
		writeError(w, 400, "invalid_edition", "edition must be 2014 or 2024")
		return
	}
	if len(search) > 200 {
		writeError(w, 400, "query_too_long", "q may contain at most 200 characters")
		return
	}
	sortBy := q.Get("sort")
	if sortBy == "" {
		sortBy = "name"
	}
	order := "t.name"
	if sortBy == "updated" {
		order = "e.updated_at"
	} else if sortBy != "name" {
		writeError(w, 400, "invalid_sort", "sort must be name or updated")
		return
	}
	// ORDER BY is selected from a strict allowlist; values remain parameterized.
	where := ` WHERE ($2='' OR e.category=$2) AND ($3='' OR e.edition=$3) AND ($4='' OR e.publisher_id=$4) AND ($5='' OR e.book_id=$5) AND ($6='' OR to_tsvector('simple',t.name||' '||t.description) @@ plainto_tsquery('simple',$6) OR t.name % $6 OR t.description % $6)`
	ctx, cancel := context.WithTimeout(r.Context(), 8*time.Second)
	defer cancel()
	rows, err := h.pool.Query(ctx, selectEntity+where+` ORDER BY `+order+`,e.id LIMIT $7 OFFSET $8`, lang, category, edition, publisher, book, search, limit+1, offset)
	if err != nil {
		h.internalError(w, r, err)
		return
	}
	defer rows.Close()
	items := make([]Entity, 0)
	for rows.Next() {
		item, e := scanRow(rows)
		if e != nil {
			h.internalError(w, r, e)
			return
		}
		items = append(items, item)
	}
	if err = rows.Err(); err != nil {
		h.internalError(w, r, err)
		return
	}
	hasMore := len(items) > limit
	if hasMore {
		items = items[:limit]
	}
	if export {
		writeJSON(w, 200, map[string]any{"data": items, "truncated": hasMore, "limit": limit})
		return
	}
	writeJSON(w, 200, listResponse{Data: items, Pagination: pagination{Limit: limit, Offset: offset, Count: len(items), HasMore: hasMore}})
}
func (h *Handler) editions(w http.ResponseWriter, r *http.Request)   { h.distinct(w, r, "edition") }
func (h *Handler) categories(w http.ResponseWriter, r *http.Request) { h.distinct(w, r, "category") }
func (h *Handler) distinct(w http.ResponseWriter, r *http.Request, column string) {
	ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()
	var sql string
	if column == "edition" {
		sql = `SELECT DISTINCT edition FROM books WHERE enabled ORDER BY edition`
	} else {
		sql = `SELECT DISTINCT e.category FROM entities e JOIN books b ON b.id=e.book_id WHERE b.enabled ORDER BY e.category`
	}
	rows, err := h.pool.Query(ctx, sql)
	if err != nil {
		h.internalError(w, r, err)
		return
	}
	defer rows.Close()
	values := make([]string, 0)
	for rows.Next() {
		var value string
		if err = rows.Scan(&value); err != nil {
			h.internalError(w, r, err)
			return
		}
		values = append(values, value)
	}
	if err = rows.Err(); err != nil {
		h.internalError(w, r, err)
		return
	}
	writeJSON(w, 200, map[string]any{"data": values})
}
func language(r *http.Request) (string, error) {
	v := r.URL.Query().Get("lang")
	if v == "" {
		v = "en"
	}
	if v != "en" && v != "ru" {
		return "", errors.New("lang must be en or ru")
	}
	return v, nil
}

func scanEntity(row pgx.Row) (Entity, error) {
	var e Entity
	err := row.Scan(&e.ID, &e.Category, &e.Edition, &e.PublisherID, &e.BookID, &e.Source, &e.License, &e.Version, &e.Language, &e.Name, &e.Description, &e.TranslationStatus, &e.Attribution, &e.Mechanics)
	return e, err
}
func scanRow(row pgx.Rows) (Entity, error) {
	var e Entity
	err := row.Scan(&e.ID, &e.Category, &e.Edition, &e.PublisherID, &e.BookID, &e.Source, &e.License, &e.Version, &e.Language, &e.Name, &e.Description, &e.TranslationStatus, &e.Attribution, &e.Mechanics)
	return e, err
}
func (h *Handler) internalError(w http.ResponseWriter, r *http.Request, err error) {
	h.log.Error("request failed", "method", r.Method, "path", r.URL.Path, "error", err)
	writeError(w, 500, "internal_error", "An internal error occurred")
}
func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
func writeError(w http.ResponseWriter, status int, code, message string) {
	writeJSON(w, status, apiError{Error: code, Message: message})
}
