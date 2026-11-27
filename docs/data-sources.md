# Источники данных, книги и лицензии

Все источники зафиксированы по commit SHA в [`data/sources/sources.json`](../data/sources/sources.json). ETL отказывается импортировать документ без явно указанной лицензии; атрибуция (автор, издатель, книга, permalink, лицензия) копируется в каждую запись и в PostgreSQL.

| Источник | Что импортируется | Лицензия контента | Роль |
|---|---|---|---|
| [Open5e API v2](https://api.open5e.com/v2/) + [Open5e schema](https://api.open5e.com/schema/) + [open5e-api](https://github.com/open5e/open5e-api) @ `7d21c96` | `data/v2` и дополнительные `data/v1` модели: классы, подклассы, виды/подвиды, черты, предыстории, заклинания, оружие, снаряжение, магические предметы, монстры, способности, правила, справочники | per-document registry `data/v2/License.json`: CC BY 4.0, OGL 1.0a, CC0 | Основной структурированный контент, все категории и книги |
| [5esrd / Open Gaming Network](https://www.5esrd.com/) | индексы разделов и страниц, ссылки на OGC других издателей | OGL 1.0a, постраничные copyright notices в [legal-information](https://www.5esrd.com/legal-information/) | Перекрёстные ссылки и описание разделов; полный текст не копируется |
| [A5ESRD](https://a5esrd.com/a5esrd) | индекс PDF глав Adventurer's Guide, Trials & Treasures, Monstrous Menagerie, Dungeon Delver's Guide, Voidrunner's Codex;structured A5E-контент из Open5e | CC BY 4.0 + OGL 1.0a + ORC; атрибуция EN Publishing | Адаптация Advanced 5e с сохранением оригинальных механик |
| [OmnisGM Rules](https://github.com/OmnisGM-App/OmnisGM-Rules) @ `1f7192b` | RU markdown SRD 5.1/5.2, глоссарии названий | CC BY 4.0, перевод Petr Radilov | Русская translation memory |
| [SRD 5.1 RU](https://github.com/palikhov/srd-dnd-5e-ru) @ `07425b6` | RU тексты глав и правил SRD 5.1 | CC BY-SA 4.0, «Киборги и Чародеи», Антон Палихов и др. | Дополнительная translation memory |
| Pre-existing DND-BofA catalog | ранее опубликованные EN/RU тексты и стабильные ID | CC BY 4.0, см. `data/catalog/2024/LICENSE` в истории репозитория | Сохранение переводов и legacy alias при пересборке |

## Книги и издательства в каталоге

- **Wizards of the Coast**: `srd-2024` (SRD 5.2 / 5e 2024, CC BY 4.0), `srd-2014` (SRD 5.1, OGL/CC BY), `core`, `open5e-2024`.
- **EN Publishing**: `a5e-ag`, `a5e-ddg`, `a5e-gpg`, `a5e-mm` (A5ESRD, CC BY 4.0 / OGL / ORC), плюс PDF-индексы A5ESRD.
- **Kobold Press**: `bfrd`, `ccdx`, `deepm`, `deepmx`, `kp`, `tob`, `tob-2023`, `tob2`, `tob3`, `toh`, `vom`, `wz` (CC BY 4.0 в реестре лицензий Open5e).
- **Green Ronin**: `tdcs`; **Open5e**: `open5e`, `elderberry-inn-icons`; **Somanyrobots**: `spells-that-dont-suck`.
- **5esrd/A5ESRD**: справочные записи `reference` со ссылками на разделы/PDF.

Точные названия, авторы, даты публикации и URL находятся в `mechanics.source_document` каждой записи и в полной атрибуции `attribution`. Статистика по каждой книге — в [docs/catalog-stats.md](catalog-stats.md).

## Что намеренно не копируется

- Тексты закрытых книг и Product Identity, даже если страница доступна онлайн.
- Полные HTML-страницы 5esrd/A5ESRD: импортируются только индексы разделов и ссылки, а механики берутся из структурированных открытых наборов.
- Изображения (отдельная лицензия CC BY-NC 4.0 в open5e-api) в публичный каталог не входят.
- Электронные таблицы с несовместимыми лицензиями и нечётным происхождением.

Этот проект не аффилирован с Wizards of the Coast и не заменяет юридическую проверку прав перед публикацией стороннего набора.
