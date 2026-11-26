# DND-BofA Rules API

Открытая двуязычная база правил D&D с REST API, PostgreSQL и инструментами управления контентом. Код проекта распространяется по MIT; лицензия каждого набора данных задаётся отдельно и возвращается в API.

> **Текущий объём и пробелы:** каталог содержит SRD 5.2.1: 336 существ, 15 состояний, 456 предметов, 94 базовых записи снаряжения/оружия, 339 заклинаний, 17 черт, 4 предыстории и 9 видов. У всех 1270 записей есть EN/RU поля, но это не означает полный перевод: атрибутированные русские тексты из OmnisGM присутствуют у 1100 записей; у 170 записей категорий предметов/снаряжения RU описание пока пустое, а название оставлено на английском как явный fallback. Переводы со статусом `source` не прошли независимую вычитку здесь. Структурированные механики сохранены в английском `mechanics.source_data`. См. [объём покрытия и ограничения](docs/limitations.md).

## Быстрый старт (Docker)

Требуются Docker Engine/Desktop и Docker Compose v2.

```sh
cp .env.example .env        # Windows: copy .env.example .env
# задайте POSTGRES_PASSWORD в .env
docker compose up -d --build
docker compose --profile tools run --rm seed
```

API доступен на `http://localhost:8080`, OpenAPI: `http://localhost:8080/openapi.yaml`.

Windows BAT-файлы: `start.bat`, `stop.bat`, `restart.bat`, `import-data.bat`. Для обновления каталога сначала обновите JSON, затем повторите импорт. Остановка не удаляет volume PostgreSQL; для полного удаления данных используйте `docker compose down -v`.

## Примеры API

```sh
curl 'http://localhost:8080/api/v1/entities?category=monster&edition=2024&lang=en&limit=10'
curl 'http://localhost:8080/api/v1/entities/srd:awakened-shrub?lang=ru' # fallback на en помечен language=en
curl 'http://localhost:8080/api/v1/entities?category=condition&lang=ru&q=Ослеплённый'
curl 'http://localhost:8080/api/v1/export?edition=2024&lang=en&limit=5000'
```

Основные маршруты: `GET /api/v1/entities`, `GET /api/v1/entities/{id}`, `GET /api/v1/export`, `/api/v1/categories`, `/api/v1/editions`, `/healthz`, `/readyz`, `/openapi.yaml`. Полный список параметров и ответов — в [OpenAPI](docs/openapi.yaml) и [документации API](docs/api.md).

## Инструменты данных

Требуется Go 1.27.4+.

```sh
go run ./cmd/rules validate --dir data/catalog
go run ./cmd/rules stats --dir data/catalog
go run ./cmd/rules export --edition 2024 --category monster --out /tmp/monsters.json
DATABASE_URL='postgres://rules:password@localhost:5432/dnd_rules?sslmode=disable' go run ./cmd/rules import --dir data/catalog
```

Обновление из Open5e выполняется **вручную/в CI-ETL**, а не API-сервером во время обработки запросов. Например, для SRD 2014:

```sh
go run ./cmd/rules sync-open5e \
  --url 'https://api.open5e.com/v2/monsters/?document__slug=srd-2014' \
  --category monster --edition 2014 --publisher-id wizards-of-the-coast \
  --book-id srd-2014 --license CC-BY-4.0 --version 5.1 \
  --source-id open5e:srd-2014 \
  --attribution 'D&D System Reference Document 5.1, Wizards of the Coast; CC BY 4.0; https://creativecommons.org/licenses/by/4.0/' \
  --out data/imports/2014/monsters.json

go run ./cmd/rules validate --dir data/imports/2014
go run ./cmd/rules import --dir data/imports/2014
```

Проверьте действующий slug документа и условия лицензии у источника до синхронизации: CLI требует явно указать лицензию и полную атрибуцию, не объявляет сторонний контент открытым автоматически. API не делает сетевых запросов к Open5e или LLM.

Для локальной/облачной LLM с OpenAI-compatible Chat Completions:

```sh
# Отдельный файл-каталог; исходные тексты и лицензии не меняются.
go run ./cmd/rules translate --file data/imports/2014/monsters.json \
  --endpoint http://localhost:1234/v1/chat/completions --model local-model \
  --source en --target ru --glossary data/glossary/en-ru.json --dry-run
```

Уберите `--dry-run` для перевода. Для облачной модели укажите HTTPS URL и ключ через переменную `LLM_API_KEY`. Результат автоматически помечается `machine`; перед публикацией нужен редакторский review. Переводчик не вызывается без явного запуска команды.

Включение/отключение книг:

```sh
DATABASE_URL=... go run ./cmd/rules book disable srd-5.2.1
DATABASE_URL=... go run ./cmd/rules book enable srd-5.2.1
```

## Архитектура и права

- [Архитектура](docs/architecture.md), [источники и лицензии](docs/data-sources.md), [развёртывание](docs/deployment.md), [вклад в проект](docs/contributing.md).
- Git — источник истины для версионируемых JSON-файлов. PostgreSQL — поисковая/прикладная проекция, восстанавливаемая импортом.
- Игровые механики хранятся в JSONB, тексты и состояния перевода — отдельно. Идентификаторы не зависят от перевода.
- Официальные книги вне SRD, платные сторонние книги и пользовательские данные без разрешения не копируются в публичный каталог. Пользовательские и Homebrew-наборы импортируются отдельно и не меняют оригинальные строки.
- Лицензия кода: [MIT](LICENSE). Данные SRD 5.2.1 и включённый RU-перевод: CC BY 4.0, с раздельной атрибуцией в `data/catalog/2024/LICENSE` и в каждой сущности. См. [правила лицензирования](docs/licensing.md).

## Разработка

```sh
make validate
make test                 # интеграционный тест требует Docker; при недоступном Docker пропускается
make build
make generate-openapi     # требует oapi-codegen
```

CI выполняет проверку JSON, Go-тесты, `go vet`, генерацию типов из OpenAPI и сборку контейнера. Подробный текущий объём и незакрытые требования: [docs/limitations.md](docs/limitations.md).
