# Архитектура

## Версии стека

Зафиксированные стабильные версии (2026-11-26): Go 1.27.4, PostgreSQL 18, Chi 5.5.0, pgx 5.11.0, Goose 3.30.2, JSON Schema validator 6.0.3, sqlc 1.31.1, oapi-codegen 2.9.0/runtime 1.9.1, Testcontainers Go 0.45.0, golangci-lint 2.15.0. ETL использует Python 3.11+ без внешних зависимостей.

## Слои и ответственность

- `scripts/sync_sources.py`, `scripts/ingest/*`: source-agnostic ETL (fetch → normalize → translate → dedupe → validate → publish). Не является частью API-процесса.
- `data/original/`: непреобразованные snapshot-ы источников (Git-игнорируются); контрольные суммы и commit SHA — в манифесте релиза.
- `data/normalized/`, `data/translated/`: раздельные gzip JSONL-слои нормализованных EN-записей и RU-переводов с атрибуцией.
- `data/catalog/<edition>/<category>/<card>.json`: проверенный двуязычный каталог, единственный вход для Go-импортера. Каждая запись — отдельная карточка: один JSON-файл на запись (например, одно оружие — `data/catalog/2024/weapon/srd-2024-longsword.json`); имя файла — слаг из `id` после последнего `:`. Загрузчики читают и карточки, и легаси-массивы.
- `data/releases/`: версия, статистика, дубликаты, причины пропусков, legacy aliases, `catalog-meta.json`.
- `cmd/rules-api` / `internal/api`: HTTP-сервер, Chi-роуты, read-only REST поверх PostgreSQL. `/api/v1/catalog` и `/api/v1/sources` отдают встроенный манифест без БД и без сети.
- `cmd/rules`: validate/import/export/stats/book/translate; транзакционный upsert, fingerprint, переключение книг.
- `internal/content`: каноническая JSON-модель `content.Record` — контракт между ETL и Go.
- `db/migrations`, `db/queries`: PostgreSQL-проекция; sqlc/generated store подключается по мере необходимости.

Приложение не вызывает внешние сервисы на пути API-запроса. Это проверяется unit-тестом `TestRuntimeHandlerDoesNotCallExternalServices`.

## Каноническая модель и идентификаторы

ID формируется детерминированно: `o5e:<doc>:<model>:<slug(pk)>`, для сайтов — `<source>:reference:<slug(url)>`. ID не зависит от языка и перевода. Legacy ID прежнего каталога (`srd:*`) сохраняются в `mechanics.aliases` и в `data/releases/aliases.json`. Стабильный `external_id` — исходный ключ upstream.

`edition` (`2014` / `2024`) отражает исходную редакцию; `mechanics.compatibility.primary_edition = "2024"`, `adapted_for_primary` и `original_system` описывают адаптацию. Оригинальные механики доступны в `mechanics.source_data`, нормализованные — в `mechanics.normalized` и категорийных ключах.

## Механики для автоматизации

Общие машиночитаемые ключи JSON Schema: `requirements`, `limitations`, `choices`, `relations`, `resources`, `formulas`, `compatibility`, `subentities`, `provenance`, `translation_provenance`. Категории добавляют свои поля через `normalized`:

- class — `hit_dice`, `saving_throws`, `primary_abilities`, `caster_type`, submodel `features` с уровнями из `ClassFeatureItem`;
- species/background/feat — `traits`/`benefits` с типами и связями;
- spell — уровень, школа, компоненты, дистанция, длительность, концентрация, DC/атака, урон, `casting_options` для высших уровней;
- monster — AC/HP/initiative/CR/спасы/навыки/иммунитеты, `actions`, `attacks`, `traits` с формулами урона;
- weapon/armor/item/magic-item — урон, диапазон, свойства, AC-формулы, цена/вес, редкость и настройка;
- rule/ability/skill/condition/damage-type — descriptions и связи `cross-reference`.

Связи хранятся как `relations[{type,target_id,required,value}]`, целевые ID — стабильные ID каталога или внешние ключи исходника.

## Дедупликация и переводы

Ключ дедупликации — `(edition, category, slug(EN name))`. Записи с одинаковым `content_hash` сливаются, источники сохраняются в `provenance`; записи с разными механиками получают `-variant-N` и `variant_of` — уникальные варианты редакций/книг не теряются. Переводы присваиваются только при точном названии из лицензированного корпуса; RU-описание без перевода не публикуется, чтобы избежать смешения языков.

## PostgreSQL и расширение

Сущности/переводы нормализованы в `entities` / `entity_translations`; механики — JSONB. `books.enabled` управляет публикацией книги. Индексы: GIN JSONB, `pg_trgm`, FTS `simple`. API делает fallback на EN и возвращает фактический `language`.

Новый источник подключается адаптером ETL и записью в `data/sources/sources.json`; категория — строковый идентификатор, поэтому изменения API/БД/JSON Schema не нужны. Версионированный релиз для DND-BofA публикуется как GitHub Release asset, без зависимости от доступности upstream.
