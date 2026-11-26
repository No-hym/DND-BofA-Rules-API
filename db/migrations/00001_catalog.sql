-- +goose Up
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS books (
    id text PRIMARY KEY,
    publisher_id text NOT NULL,
    title text NOT NULL,
    edition text NOT NULL CHECK (edition IN ('2014', '2024')),
    license_id text NOT NULL,
    source_url text NOT NULL DEFAULT '',
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS entities (
    id text PRIMARY KEY,
    category text NOT NULL,
    edition text NOT NULL CHECK (edition IN ('2014', '2024')),
    publisher_id text NOT NULL,
    book_id text NOT NULL REFERENCES books(id),
    source text NOT NULL,
    license_id text NOT NULL,
    source_version text NOT NULL,
    external_id text NOT NULL,
    mechanics jsonb NOT NULL DEFAULT '{}'::jsonb,
    attribution text NOT NULL,
    fingerprint text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source, edition, category, external_id)
);

CREATE TABLE IF NOT EXISTS entity_translations (
    entity_id text NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    language text NOT NULL CHECK (language IN ('en', 'ru')),
    name text NOT NULL,
    description text NOT NULL DEFAULT '',
    translation_status text NOT NULL DEFAULT 'machine' CHECK (translation_status IN ('source', 'machine', 'reviewed', 'outdated')),
    translated_at timestamptz,
    source_version text NOT NULL,
    glossary_version text NOT NULL DEFAULT '',
    PRIMARY KEY (entity_id, language)
);

CREATE TABLE IF NOT EXISTS import_runs (
    id bigserial PRIMARY KEY,
    source text NOT NULL,
    source_version text NOT NULL,
    imported_count integer NOT NULL DEFAULT 0,
    skipped_count integer NOT NULL DEFAULT 0,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS entities_category_edition_idx ON entities(category, edition);
CREATE INDEX IF NOT EXISTS entities_publisher_book_idx ON entities(publisher_id, book_id);
CREATE INDEX IF NOT EXISTS entities_mechanics_gin_idx ON entities USING gin(mechanics);
CREATE INDEX IF NOT EXISTS translations_name_trgm_idx ON entity_translations USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS translations_description_trgm_idx ON entity_translations USING gin(description gin_trgm_ops);
CREATE INDEX IF NOT EXISTS translations_search_fts_idx ON entity_translations USING gin(to_tsvector('simple', name || ' ' || description));

-- +goose Down
DROP TABLE IF EXISTS import_runs;
DROP TABLE IF EXISTS entity_translations;
DROP TABLE IF EXISTS entities;
DROP TABLE IF EXISTS books;
DROP EXTENSION IF EXISTS pg_trgm;
