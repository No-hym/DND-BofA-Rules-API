# Разработка и внесение данных

Вся техническая информация проекта собрана здесь. Пользовательское описание, источники и покрытие перевода — в [README](../README.md).

## Быстрый старт (Docker)

Требуются Docker Engine/Desktop и Docker Compose v2.

```sh
cp .env.example .env        # Windows: copy .env.example .env
# задайте POSTGRES_PASSWORD в .env
docker compose up -d --build
docker compose --profile tools run --rm seed
```

API доступен на `http://localhost:8080`, OpenAPI: `http://localhost:8080/openapi.yaml`.

Windows BAT-файлы: `start.bat`, `stop.bat`, `restart.bat`, `import-data.bat`. Для обновления каталога сначала обновите JSON (см. «Синхронизация источников»), затем повторите импорт. Остановка не удаляет volume PostgreSQL; для полного удаления данных используйте `docker compose down -v`.

## Примеры API

```sh
curl 'http://localhost:8080/api/v1/entities?category=monster&edition=2024&lang=en&limit=10'
curl 'http://localhost:8080/api/v1/entities/o5e:srd-2024:conditiondescription:srd-2024-blinded?lang=ru'
# прежние ID (например srd:blinded) сопоставляются через data/releases/aliases.json
curl 'http://localhost:8080/api/v1/entities?category=condition&lang=ru&q=Ослеплённый'
curl 'http://localhost:8080/api/v1/export?edition=2024&lang=en&limit=5000'
curl 'http://localhost:8080/api/v1/catalog' # версия, покрытие, источники; без БД и без сети
```

Основные маршруты: `GET /api/v1/entities`, `GET /api/v1/entities/{id}`, `GET /api/v1/export`, `/api/v1/categories`, `/api/v1/editions`, `/api/v1/catalog`, `/api/v1/sources`, `/healthz`, `/readyz`, `/openapi.yaml`. Полный список — в [OpenAPI](openapi.yaml) и [документации API](api.md).

## Слои данных

| Слой | Путь | Содержимое |
|---|---|---|
| Оригинал | `data/sources/sources.json` + зафиксированные snapshot-ы в `data/original/` (`.gitignore`) | исходные Fixture/`data/v1`,`data/v2`, markdown-корпуса, страницы сайтов; контрольные суммы в манифесте релиза |
| Нормализованный | `data/normalized/<edition>/normalized.jsonl.gz` | EN-записи с типизированными механиками, связями, требованиями, ограничениями и формулами |
| Переведённый | `data/translated/<edition>/translated.jsonl.gz` | отдельные RU-записи с атрибуцией, лицензией перевода и статусом |
| Публикация | `data/catalog/<edition>/<book>/<category>/<card>.json` | двуязычный каталог для Go-импортера/API; папка на редакцию, книгу/дополнение и категорию, одна запись — один файл-карточка |
| Релиз | `data/releases/v<version>.json`, `aliases.json`, `latest.json` | версия, статистика, дубликаты, причины пропусков, алиасы legacy ID |

`data/legacy/2024/` сохраняет прежний каталог SRD 5.2.1 как источник переводов и стабильных ID. Старые ID доступны через `data/releases/aliases.json`.

## Синхронизация источников

ETL написан на Python (стандартная библиотека) по образцу существующего `scripts/sync_srd521.py`; API и импортер остаются на Go.

```sh
python3 scripts/sync_sources.py fetch                    # только ETL: загрузка зафиксированных snapshot-ов
python3 scripts/sync_sources.py build --version 20261128 # сборка слоёв и отчёта
python3 scripts/sync_sources.py verify                   # валидация слоёв
python3 -m unittest discover -s scripts/tests
python3 scripts/package_release.py --version 20261128 --out /tmp/catalog.tar.gz
cp data/api/catalog-meta.json internal/api/catalog_meta.json   # метаданные для /api/v1/catalog
go run ./cmd/rules validate --dir data/catalog
```

`fetch` разрешает только `codeload.github.com`, `api.github.com`, `www.5esrd.com`, `a5esrd.com`. Исходники зафиксированы по commit SHA в `data/sources/sources.json`; неизвестная лицензия = пропуск записи. GitHub Actions (`sync-sources.yml`) запускает конвейер по расписанию и вручную (`workflow_dispatch`), проверяет каталог, публикует версионированный `.tar.gz` и открывает PR на ревью. Подробности: [docs/sync.md](sync.md) (при наличии) и [data-sources.md](data-sources.md).

Проверенный релиз доступен как ассет `catalog-v<version>.tar.gz` (создаётся workflow с опцией `publish_release`) и содержит `catalog/`, `releases/v<version>.json`, `releases/aliases.json`, `catalog-release.json`. Основной сайт DND-BofA подключается к ассету, а не к внешним API.

## Переводы

Русские тексты берутся из лицензированных корпусов с точным совпадением английского названия: OmnisGM SRD 5.1/5.2 (CC BY 4.0, Petr Radilov), SRD 5.1 RU (CC BY-SA 4.0, сообщество «Киборги и Чародеи») и ранее опубликованный каталог DND-BofA. Дополнительно: курируемые машинные переводы (`data/translations/curated.json`, на запись — книга, лицензия и атрибуция) и производные тексты из собственных структурированных механик записи (`derived-from-structured-mechanics`) для записей, у которых у источника нет прозаического описания; оба слоя имеют статус `machine`. Английский fallback не считается переводом: если нет полного RU-описания, RU-поле в каталоге отсутствует, а API отдаёт en с `language: en`.

Для подклассов действуют дополнительные правила в `scripts/ingest/translations.py`: короткий вводный текст не публикуется как перевод длинной записи с полным текстом (порог 0,4 длины оригинала); если для одного имени есть и вводный, и полный курируемый перевод, каждой записи (варианты Open5e v2 и v1) подбирается текст, соответствующий длине её английского описания.

Для закрытия пробелов предусмотрен явный LLM-перевод (не вызывается автоматически):

```sh
python3 scripts/sync_sources.py translate --endpoint https://.../v1/chat/completions --model MODEL --limit 100
```

Результат помечается `status: machine` и требует редакторской вычитки; исходный английский текст не изменяется. Альтернативный Go-переводчик: `go run ./cmd/rules translate --help`.

## Архитектура и права

- [Архитектура](architecture.md), [источники](data-sources.md), [лицензии](licensing.md), [развёртывание](deployment.md).
- Git — источник истины для версионируемых JSON; PostgreSQL — восстанавливаемая проекция.
- Игровые механики и их исходная форма хранятся раздельно; ID не зависят от языка.
- Дополнительные книги подключаются профилями в `data/sources/sources.json` и новым адаптером — без изменений API/БД.
- Код: [MIT](../LICENSE). Данные: лицензия и атрибуция каждой книги — в `attribution` записи и в [licensing.md](licensing.md).

## Разработка

```sh
make validate
make test                 # интеграционный тест требует Docker; при недоступном Docker пропускается
make build
make generate-openapi     # требует oapi-codegen
```

CI проверяет JSON, Go-тесты, `go vet`, генерацию типов, сборку контейнера; workflow синхронизации дополнительно собирает и проверяет каталог.

## Правила внесения изменений

1. Установите Go 1.27.4+, Docker Compose, Python 3.11+, `oapi-codegen` v2 (для генерации контракта).
2. Изменяйте каталог через ETL (`python3 scripts/sync_sources.py ...`) либо точечными правками JSON в `data/catalog`; не редактируйте PostgreSQL как источник истины.
3. Каждая запись обязана содержать постоянный ID, категорию, редакцию, источник, книгу, издателя, лицензию, версию, атрибуцию, EN-текст и машинно-читаемые mechanics. RU-поле публикуется только с реальным переводом и атрибуцией.
4. Проверки перед PR: `python3 scripts/sync_sources.py verify`, `python3 -m unittest discover -s scripts/tests`, `make validate`, `make test`, `go vet ./...`, `make generate-openapi`, Docker build.
5. В PR указывайте источник, commit/версию, лицензии, количество записей по категории/языку, diff ID, статусы переводов и известные несовпадения с upstream. Тексты закрытых книг не принимаются без подтверждённых прав.

Механики должны хранить числа/структуру/варианты, а не только прозу; используйте `requirements`, `limitations`, `choices`, `relations`, `resources`, `formulas` и `compatibility`. Для новой категории добавьте ключи в `NORMALIZE_KEYS` адаптера и, при необходимости, категорийные правила валидации. ID при переименовании/переводе не меняется; при смене upstream ID сохраняйте alias в `mechanics.aliases` и `data/releases/aliases.json`.

Новый источник: добавьте профиль в `data/sources/sources.json`, адаптер в `scripts/ingest/`, тест и явно укажите лицензию/атрибуцию. Изменения в API/БД не требуются.
