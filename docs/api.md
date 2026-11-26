# REST API v1

Базовый URL: `/api/v1`; формат JSON. Неизвестные query-параметры игнорируются. `lang` принимает `en` или `ru` (default `en`). Если у сущности нет перевода на выбранном языке, возвращается EN fallback; поле `language` показывает язык реально выданного текста.

## Записи и поиск

`GET /entities` принимает:

| Параметр | Описание |
|---|---|
| `q` | Поиск FTS (`simple`) и trigram по переведённому имени/описанию, максимум 200 символов |
| `category` | Категория, например `monster`, `condition` |
| `edition` | `2014` или `2024` |
| `publisher` | ID издателя |
| `book` | ID книги |
| `lang` | `en` / `ru` |
| `sort` | `name` / `updated` |
| `limit` | 1–500, default 100 |
| `offset` | 0–1,000,000, default 0 |

Ответ: `{ "data": [...], "pagination": {"limit": 100, "offset": 0, "count": 2, "has_more": false} }`.

`GET /entities/{id}` возвращает одну запись или 404. `GET /export` принимает те же фильтры, лимит до 5000 и возвращает `data`, `truncated`, `limit`; для выгрузок больше 5000 нужно запросить следующую порцию с фильтрами через `/entities`.

Каждая запись возвращает неизменяемый `id`, `category`, `edition`, `publisher_id`, `book_id`, `source`, `license`, `version`, `language`, `translation_status`, полную `attribution`, `name`, `description` и структурированные `mechanics`.

## Справочные/системные маршруты

- `GET /categories`, `GET /editions` — только включённые книги.
- `GET /healthz` — процесс жив.
- `GET /readyz` — БД отвечает.
- `GET /openapi.yaml` — спецификация OpenAPI 3.1.

Контрактные Go-модели/Chi интерфейсы генерируются `oapi-codegen` (`make generate-openapi`) из `docs/openapi.yaml`.
