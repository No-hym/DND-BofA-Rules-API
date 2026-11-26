package api

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/pressly/goose/v3"
	"github.com/testcontainers/testcontainers-go"
	"github.com/testcontainers/testcontainers-go/wait"
)

func TestPostgresAPIIntegration(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()
	ctr, err := testcontainers.Run(ctx, "postgres:18-alpine", testcontainers.WithEnv(map[string]string{"POSTGRES_DB": "rules", "POSTGRES_USER": "rules", "POSTGRES_PASSWORD": "rules"}), testcontainers.WithExposedPorts("5432/tcp"), testcontainers.WithWaitStrategy(wait.ForLog("database system is ready to accept connections").WithOccurrence(2).WithStartupTimeout(60*time.Second)))
	if err != nil {
		t.Skipf("Docker/Testcontainers unavailable: %v", err)
	}
	t.Cleanup(func() { _ = ctr.Terminate(context.Background()) })
	host, err := ctr.Host(ctx)
	if err != nil {
		t.Fatal(err)
	}
	port, err := ctr.MappedPort(ctx, "5432/tcp")
	if err != nil {
		t.Fatal(err)
	}
	dsn := fmt.Sprintf("postgres://rules:rules@%s/%s?sslmode=disable", host, port.Port())
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	if err = goose.SetDialect("postgres"); err != nil {
		t.Fatal(err)
	}
	if err = goose.Up(db, "../../db/migrations"); err != nil {
		t.Fatalf("migration failed: %v", err)
	}
	statements := []string{
		`INSERT INTO books(id,publisher_id,title,edition,license_id) VALUES('test-srd','wotc','Test SRD','2024','CC-BY-4.0')`,
		`INSERT INTO entities(id,category,edition,publisher_id,book_id,source,license_id,source_version,external_id,mechanics,attribution,fingerprint) VALUES('test:blind','condition','2024','wotc','test-srd','test:source','CC-BY-4.0','1','blind','{"key":"blinded"}','test attribution','fingerprint')`,
		`INSERT INTO entity_translations(entity_id,language,name,description,translation_status,source_version) VALUES('test:blind','en','Blinded','A blinded creature cannot see.','source','1'),('test:blind','ru','Ослеплённый','Существо не видит.','machine','1')`,
		`INSERT INTO entities(id,category,edition,publisher_id,book_id,source,license_id,source_version,external_id,mechanics,attribution,fingerprint) VALUES('test:shrub','monster','2024','wotc','test-srd','test:source','CC-BY-4.0','1','shrub','{}','test attribution','fingerprint')`,
		`INSERT INTO entity_translations(entity_id,language,name,description,translation_status,source_version) VALUES('test:shrub','en','Awakened Shrub','Small plant creature.','source','1')`,
	}
	for _, statement := range statements {
		if _, err = db.Exec(statement); err != nil {
			t.Fatal(err)
		}
	}
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		t.Fatal(err)
	}
	defer pool.Close()
	h := New(pool, slog.New(slog.NewTextHandler(httptest.NewRecorder(), nil))).Routes()
	for _, tc := range []struct{ path, contains string }{{"/api/v1/entities/test:blind?lang=ru", "Ослеплённый"}, {"/api/v1/entities?lang=ru&q=Ослеплённый", "Ослеплённый"}, {"/api/v1/entities?lang=ru&category=condition", "test:blind"}, {"/api/v1/entities/test:shrub?lang=ru", "\"language\":\"en\""}} {
		req := httptest.NewRequest("GET", tc.path, nil)
		res := httptest.NewRecorder()
		h.ServeHTTP(res, req)
		if res.Code != 200 {
			t.Fatalf("GET %s: status %d body=%s", tc.path, res.Code, res.Body.String())
		}
		if !strings.Contains(res.Body.String(), tc.contains) {
			t.Fatalf("GET %s body does not contain %q: %s", tc.path, tc.contains, res.Body.String())
		}
	}
}
