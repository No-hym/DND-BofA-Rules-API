# Синхронизация и публикация каталога

Конвейер полностью отделён от рантайм API: сервер на Go не делает сетевых запросов к источникам и не вызывает LLM. Синхронизацию запускает только ETL/CLI или GitHub Actions.

## Этапы

1. **`fetch`** — загрузка snapshot-ов по зафиксированным commit SHA (open5e-api, OmnisGM, SRD 5.1 RU) и HTML-индексов 5esrd/A5ESRD. Разрешены только хосты из allowlist в `scripts/sync_sources.py`. Snapshot-ы попадают в `data/original/` (игнорируется Git).
2. **Адаптеры** — `scripts/ingest/open5e.py` нормализует все модели v1/v2, сворачивает вложенные объекты (действия монстров, атаки, черты, варианты заклинаний, уровни умений, бонусы черт/предысторий) в родительские записи, сохраняя исходный payload в `mechanics.source_data` и `mechanics.subentities`. Адаптеры сайтов создают записи `reference` с ссылками и лицензией.
3. **`build`** — определяет ID, edition, publisher/book/license из upstream-документа, строит `requirements`, `limitations`, `choices`, `relations`, `resources`, `formulas` и `compatibility`, применяет translation memory по точному названию, дедуплицирует по (edition, category, normalized name) + hash механик, пишет три раздельных слоя и двуязычный каталог.
4. **`verify`** — проверка JSON, Homebrew-совместимой JSON Schema, обязательной атрибуции, уникальности ID, отсутствия английских RU-описаний и наличия RU-записей в итоговом каталоге.
5. **`package_release`** — детерминированный `tar.gz` с каталогом, манифестом, алиасами и `catalog-release.json`.

## GitHub Actions

`.github/workflows/sync-sources.yml`:

- `schedule` — еженедельно;
- `workflow_dispatch` — ручной запуск с параметрами `version` и `publish_release`;
- после сборки выполняются `verify`, Python unit-тесты, `go run ./cmd/rules validate`, `stats`, packaging;
- артефакт с каталогом и отчётом загружается в run;
- PR с изменениями каталога создаётся через `peter-evans/create-pull-request` и требует обычного ревью;
- при `publish_release=true` создаётся/обновляется GitHub Release `catalog-v<version>` с ассетом `catalog-v<version>.tar.gz`.

## Подключение основного сайта DND-BofA

1. Скачать ассет_release: `https://github.com/No-hym/DND-BofA-Rules-API/releases/download/catalog-v<version>/catalog-v<version>.tar.gz`.
2. Прочитать `catalog-release.json` (версия, основная редакция, точка входа).
3. Загрузить `catalog/<edition>/<category>.json` в поисковую проекцию/БД сайта; `releases/v<version>.json` использовать для статистики и аудита, `releases/aliases.json` — для миграции старых ID.
4. Никаких обращений к Open5e/5esrd/A5ESRD с сайта не требуется.

## Обнаружение изменений и безопасное обновление

- `mechanics.content_hash` — SHA-256 нормализованных исходных полей; изменение upstream меняет hash записи.
- `fingerprint` в Go-импортере по-прежнему вычисляется от `mechanics` и используется для transакционного upsert.
- Translation memory хранится отдельно и никогда не перезаписывается английским текстом: при повторной сборке RU-записи поднимаются из `data/translations/memory.json` и `data/legacy/2024/`, даже если upstream изменил описание. Если исходник изменился, нужно явно обновить запись памяти/перевод.
- Точные дубликаты свертываются, но все источники сохраняются в `mechanics.provenance`; уникальные варианты получают suffix `-variant-N` и `variant_of`.

## Добавление нового источника/издательства

1. Добавить запись в `data/sources/sources.json` (id, URL, license или license registry, role, commit, adapter).
2. Реализовать адаптер в `scripts/ingest/`, возвращающий `Entity` с теми же полями; метод `_make_entity` в Open5e-адаптере — пример гарантий лицензирования и атрибуции.
3. Добавить тест в `scripts/tests/`, при необходимости категорийный key-набор в `NORMALIZE_KEYS`.
4. Запустить `build`/`verify`. Изменений в Go API, PostgreSQL и JSON Schema не требуется: `category` и `mechanics` открытые.
