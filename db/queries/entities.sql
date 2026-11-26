-- name: GetEntity :one
SELECT e.id, e.category, e.edition, e.publisher_id, e.book_id, e.source, e.license_id,
       e.source_version, e.mechanics, t.language, t.name, t.description, t.translation_status, t.translated_at
FROM entities e
JOIN books b ON b.id = e.book_id AND b.enabled
JOIN entity_translations t ON t.entity_id = e.id
WHERE e.id = $1 AND t.language = $2;

-- name: ListEntities :many
SELECT e.id, e.category, e.edition, e.publisher_id, e.book_id, e.source, e.license_id,
       e.source_version, e.mechanics, t.language, t.name, t.description, t.translation_status, t.translated_at
FROM entities e
JOIN books b ON b.id = e.book_id AND b.enabled
JOIN entity_translations t ON t.entity_id = e.id
WHERE ($1::text = '' OR e.category = $1)
  AND ($2::text = '' OR e.edition = $2)
  AND ($3::text = '' OR e.publisher_id = $3)
  AND ($4::text = '' OR e.book_id = $4)
  AND t.language = $5
  AND ($6::text = '' OR to_tsvector('simple', t.name || ' ' || t.description) @@ plainto_tsquery('simple', $6))
ORDER BY t.name ASC, e.id ASC
LIMIT $7 OFFSET $8;
