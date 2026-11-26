GO ?= go

.PHONY: fmt test lint build validate generate-openapi dev-up dev-down sync-fetch sync-build sync-verify
fmt:
	gofmt -w $$(find cmd internal -name '*.go' -type f)

test:
	$(GO) test ./...

lint:
	golangci-lint run ./...

build:
	mkdir -p bin
	$(GO) build -o bin/rules-api ./cmd/rules-api
	$(GO) build -o bin/rules ./cmd/rules

validate:
	$(GO) run ./cmd/rules validate --dir data/catalog

sync-fetch:
	python3 scripts/sync_sources.py fetch

sync-build:
	python3 scripts/sync_sources.py build
	python3 scripts/sync_sources.py verify
	python3 -m unittest discover -s scripts/tests
	cp data/api/catalog-meta.json internal/api/catalog_meta.json

sync-verify:
	python3 scripts/sync_sources.py verify
	python3 -m unittest discover -s scripts/tests

# Generate contract models and Chi server interfaces from the OpenAPI source.
generate-openapi:
	cp docs/openapi.yaml internal/api/openapi.yaml
	oapi-codegen --config oapi-codegen.yaml docs/openapi.yaml

dev-up:
	docker compose up -d --build

dev-down:
	docker compose down
