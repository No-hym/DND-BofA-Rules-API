# Разработка и внесение данных

1. Установите Go 1.27.4+, Docker Compose, Python 3.11+, `oapi-codegen` v2 (для генерации контракта).
2. Изменяйте каталог через ETL (`python3 scripts/sync_sources.py ...`) либо точечными правками JSON в `data/catalog`; не редактируйте PostgreSQL как источник истины.
3. Каждая запись обязана содержать постоянный ID, категорию, редакцию, источник, книгу, издателя, лицензию, версию, атрибуцию, EN-текст и машинно-читаемые mechanics. RU-поле публикуется только с реальным переводом и атрибуцией.
4. Проверки перед PR: `python3 scripts/sync_sources.py verify`, `python3 -m unittest discover -s scripts/tests`, `make validate`, `make test`, `go vet ./...`, `make generate-openapi`, Docker build.
5. В PR указывайте источник, commit/версию, лицензии, количество записей по категории/языку, diff ID, статусы переводов иизвестные несовпадения с upstream. Тексты закрытых книг не принимаются без подтверждённых прав.

Механики должны хранить числа/структуру/варианты, а не только прозу; используйте `requirements`, `limitations`, `choices`, `relations`, `resources`, `formulas` и `compatibility`. Для новой категории добавьте ключи в `NORMALIZE_KEYS` адаптера и, при необходимости, категорийные правила валидации. ID при переименовании/переводе не меняется; при смене upstream ID сохраняйте alias в `mechanics.aliases` и `data/releases/aliases.json`.

Новый источник: добавьте профиль в `data/sources/sources.json`, адаптер в `scripts/ingest/`, тест и явно укажите лицензию/атрибуцию. Изменения в API/БД не требуются.
