#!/bin/sh
set -eu
: "${DATABASE_URL:?DATABASE_URL is required}"
goose -dir /app/db/migrations postgres "$DATABASE_URL" up
exec "$@"
