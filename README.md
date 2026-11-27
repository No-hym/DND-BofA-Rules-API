# DND-BofA Rules API

Открытая двуязычная (EN/RU) база правил D&D 5e с REST API. Проект собирает правила из открытых лицензированных источников, нормализует их в единый каталог и переводит на русский язык. Код распространяется по MIT; лицензия каждого набора данных задаётся отдельно и возвращается в API вместе с записью.

## Откуда взята информация

Весь контент импортируется только из открытых источников с явными лицензиями; каждая запись в каталоге хранит книгу, издателя, автора, лицензию и атрибуцию. Источники зафиксированы по commit SHA в [`data/sources/sources.json`](data/sources/sources.json).

| Источник | Что берётся | Лицензия |
|---|---|---|
| [Open5e](https://github.com/open5e/open5e-api) (`open5e-api` @ `7d21c96`) | Основной структурированный контент: классы, подклассы, виды, черты, предыстории, заклинания, снаряжение, магические предметы, монстры, правила и справочники из 26 книг (SRD 5.2/2024, SRD 5.1/2014, книги Kobold Press, EN Publishing/A5E, Green Ronin, Somanyrobots и др.) | По книгам: CC BY 4.0, OGL 1.0a, CC0 (реестр лицензий Open5e) |
| [OmnisGM Rules](https://github.com/OmnisGM-App/OmnisGM-Rules) @ `1f7192b` | Русские тексты SRD 5.1 и SRD 5.2.1, глоссарии названий (перевод Petr Radilov) | CC BY 4.0 |
| [SRD 5.1 RU](https://github.com/palikhov/srd-dnd-5e-ru) @ `07425b6` | Дополнительные русские тексты SRD 5.1 (сообщество «Киборги и Чародеи») | CC BY-SA 4.0 |
| Ранее опубликованный каталог DND-BofA | Ранее опубликованные EN/RU тексты и стабильные ID записей | CC BY 4.0 |
| [5e SRD / Open Gaming Network](https://www.5esrd.com/) и [A5ESRD](https://a5esrd.com/a5esrd) | Только индексы разделов и ссылки на страницы/PDF; полный текст сайтов не копируется | OGL 1.0a / CC BY 4.0 + OGL + ORC |

Русские переводы, которых нет в лицензированных корпусах, выполняются как курируемые машинные переводы ([`data/translations/curated.json`](data/translations/curated.json), на каждую запись — книга, лицензия и атрибуция) и помечаются статусом `machine`: они требуют редакторской вычитки. Для записей без прозаического описания у источника русский текст строится только из их собственных структурированных механик. Английский текст никогда не выдаётся за перевод: если полного русского описания нет, RU-поле у записи отсутствует.

Подробно об источниках, книгах и лицензиях: [docs/data-sources.md](docs/data-sources.md), [docs/licensing.md](docs/licensing.md). Честные ограничения и причины оставшихся пропусков: [docs/limitations.md](docs/limitations.md).

## Покрытие перевода по разделам

Каталог `v20261128`: 12 703 записи, из них с русским текстом — 12 643 (99,5%). Редакции разделены: **2024** (SRD 5.2.1, основная) — 2 047 записей, переведено 100,0%; **2014** (SRD 5.1 и дополнительные книги) — 10 656 записей, переведено 99,4%. Каждая запись в каталоге и в ответах API помечена редакцией (`edition`), категорией (`category`) и краткой аббревиатурой книги или дополнения (`book_id`, например `toh`, `vom`, `tob2`), а также полным названием книги в `mechanics.source_document.title`.

### Редакция 2024 (SRD 5.2.1)

| Раздел (EN) | Раздел (RU) | На EN | На RU | Переведено |
|---|---|---:|---:|---:|
| ability | Характеристики | 6 | 6 | 100,0% |
| alignment | Мировоззрение | 9 | 9 | 100,0% |
| armor | Доспехи | 13 | 13 | 100,0% |
| attack | Атаки | 140 | 140 | 100,0% |
| background | Предыстории | 4 | 4 | 100,0% |
| class | Классы | 12 | 12 | 100,0% |
| condition | Состояния | 15 | 15 | 100,0% |
| creature-type | Типы существ | 4 | 4 | 100,0% |
| damage-type | Типы урона | 6 | 6 | 100,0% |
| equipment | Снаряжение | 203 | 203 | 100,0% |
| feat | Черты | 17 | 17 | 100,0% |
| item-category | Категории предметов | 2 | 2 | 100,0% |
| magic-item | Волшебные предметы | 760 | 760 | 100,0% |
| monster | Монстры | 331 | 331 | 100,0% |
| rule | Правила | 56 | 56 | 100,0% |
| ruleset | Наборы правил | 11 | 11 | 100,0% |
| service | Услуги | 30 | 30 | 100,0% |
| skill | Навыки | 13 | 13 | 100,0% |
| species | Виды (расы) | 9 | 9 | 100,0% |
| spell | Заклинания | 339 | 339 | 100,0% |
| subclass | Подклассы | 12 | 12 | 100,0% |
| weapon | Оружие | 38 | 38 | 100,0% |
| weapon-property | Свойства оружия | 17 | 17 | 100,0% |
| **Итого 2024** | | **2 047** | **2 047** | **100,0%** |

### Редакция 2014 (SRD 5.1 и дополнительные книги)

| Раздел (EN) | Раздел (RU) | На EN | На RU | Переведено |
|---|---|---:|---:|---:|
| ability | Характеристики | 18 | 18 | 100,0% |
| alignment | Мировоззрение | 18 | 18 | 100,0% |
| armor | Доспехи | 23 | 23 | 100,0% |
| attack | Атаки | 1 060 | 1 060 | 100,0% |
| background | Предыстории | 81 | 81 | 100,0% |
| class | Классы | 29 | 29 | 100,0% |
| condition | Состояния | 70 | 70 | 100,0% |
| creature-set | Наборы существ | 1 | 1 | 100,0% |
| creature-type | Типы существ | 22 | 22 | 100,0% |
| damage-type | Типы урона | 19 | 19 | 100,0% |
| environment | Окружение | 31 | 31 | 100,0% |
| equipment | Снаряжение | 237 | 237 | 100,0% |
| feat | Черты | 122 | 122 | 100,0% |
| image | Изображения (описания) | 32 | 32 | 100,0% |
| item-category | Категории предметов | 22 | 22 | 100,0% |
| item-rarity | Редкость предметов | 6 | 6 | 100,0% |
| item-set | Наборы предметов | 20 | 20 | 100,0% |
| language | Языки | 19 | 19 | 100,0% |
| magic-item | Волшебные предметы | 2 218 | 2 218 | 100,0% |
| monster | Монстры | 4 077 | 4 076 | 100,0% |
| plane | Планы существования | 8 | 8 | 100,0% |
| reference | Справочные ссылки | 108 | 108 | 100,0% |
| rule | Правила | 285 | 285 | 100,0% |
| ruleset | Наборы правил | 43 | 43 | 100,0% |
| size | Размеры | 7 | 7 | 100,0% |
| skill | Навыки | 48 | 48 | 100,0% |
| species | Виды (расы) | 36 | 36 | 100,0% |
| spell | Заклинания | 1 628 | 1 628 | 100,0% |
| spell-list | Списки заклинаний | 7 | 7 | 100,0% |
| spell-school | Школы магии | 9 | 9 | 100,0% |
| subclass | Подклассы | 235 | 179 | 76,2% |
| subspecies | Подвиды | 37 | 37 | 100,0% |
| weapon | Оружие | 68 | 65 | 95,6% |
| weapon-property | Свойства оружия | 12 | 12 | 100,0% |
| **Итого 2014** | | **10 656** | **10 596** | **99,4%** |

### По книгам и дополнениям

Вещи, монстры, заклинания и прочий контент из книг и дополнений помечены в каталоге аббревиатурой книги (`book_id`); ниже — покрытие по каждой книге.

| Аббревиатура | Книга / дополнение | Ред. | На EN | На RU | Переведено | Основное содержимое |
|---|---|---|---:|---:|---:|---|
| `srd-2024` | System Reference Document 5.2 | 2024 | 2 047 | 2 047 | 100,0% | magic-item (760), spell (339), monster (331) |
| `srd-2014` | System Reference Document 5.1 | 2014 | 1 596 | 1 596 | 100,0% | magic-item (499), spell (319), rule (240) |
| `vom` | Vault of Magic | 2014 | 1 114 | 1 114 | 100,0% | magic-item (1 114) |
| `tob2` | Tome of Beasts 2 | 2014 | 959 | 958 | 99,9% | monster (760), attack (199) |
| `tob` | Tome of Beasts | 2014 | 898 | 898 | 100,0% | monster (737), attack (159) |
| `a5e-mm` | Monstrous Menagerie (A5E) | 2014 | 790 | 790 | 100,0% | monster (586), attack (199) |
| `tob-2023` | Tome of Beasts 1 (2023 Edition) | 2014 | 618 | 618 | 100,0% | monster (479), attack (139) |
| `a5e` | Level Up Advanced 5e | 2014 | 610 | 610 | 100,0% | magic-item (546), feat (48) |
| `bfrd` | Black Flag SRD | 2014 | 563 | 563 | 100,0% | monster (360), attack (170), subclass (17) |
| `ccdx` | Creature Codex | 2014 | 528 | 528 | 100,0% | monster (356), attack (172) |
| `deepm` | Deep Magic for 5th Edition | 2014 | 515 | 515 | 100,0% | spell (515) |
| `a5e-ag` | Adventurer's Guide (A5E) | 2014 | 505 | 502 | 99,4% | spell (371), feat (59), condition (26) |
| `tob3` | Tome of Beasts 3 | 2014 | 397 | 397 | 100,0% | monster (397) |
| `toh` | Tome of Heroes | 2014 | 396 | 365 | 92,2% | subclass (151), spell (91), subspecies (32) |
| `menagerie` | Level Up Advanced 5e Monstrous Menagerie | 2014 | 283 | 283 | 100,0% | monster (283) |
| `wotc-srd` | 5e Core Rules | 2014 | 196 | 189 | 96,4% | monster (46), rule (45), magic-item (29) |
| `spells-that-dont-suck` | Spells That Don't Suck | 2014 | 180 | 180 | 100,0% | spell (180) |
| `core` | 5e Core Concepts | 2014 | 154 | 154 | 100,0% | item-category (22), environment (19), language (18) |
| `5esrd` | 5e SRD / Open Gaming Network (индекс) | 2014 | 77 | 77 | 100,0% | reference (77) |
| `deepmx` | Deep Magic Extended | 2014 | 64 | 64 | 100,0% | spell (64) |
| `wz` | Warlock Zine | 2014 | 43 | 43 | 100,0% | spell (43) |
| `open5e` | Open5e Originals | 2014 | 33 | 33 | 100,0% | subclass (17), image (12), spell (2) |
| `kp` | Kobold Press Compilation | 2014 | 32 | 32 | 100,0% | spell (32) |
| `a5esrd` | A5E System Reference Document (индекс) | 2014 | 31 | 31 | 100,0% | reference (31) |
| `elderberry-inn-icons` | Elderberry Inn Icons | 2014 | 20 | 20 | 100,0% | image (20) |
| `o5e` | Open5e Original Content | 2014 | 19 | 5 | 26,3% | subclass (15), spell-list (4) |
| `tdcs` | Tal'dorei Campaign Setting | 2014 | 16 | 16 | 100,0% | background (5), monster (4), subclass (4) |
| `taldorei` | Critical Role: Tal'Dorei Campaign Setting | 2014 | 13 | 9 | 69,2% | background (4), monster (4), subclass (4) |
| `a5e-ddg` | Dungeon Delver's Guide (A5E) | 2014 | 4 | 4 | 100,0% | background (4) |
| `a5e-gpg` | Gate Pass Gazette (A5E) | 2014 | 2 | 2 | 100,0% | background (2) |

Непереведённые 60 записей: 56 подклассов Open5e v1 с полным английским текстом (перевод продолжается; частичный перевод не публикуется), 1 монстр `Bloated Ghoul` (`tob2`; исходный текст обрезан у поставщика пометкой «Open Game License») и 3 оружия с пустым описанием у источника (Bolas, Hand Trebuchet, Wormsilk Net; `toh`). Автоматически обновляемая статистика по источникам, книгам и причинам пропусков: [docs/catalog-stats.md](docs/catalog-stats.md).

## Документация

- [API](docs/api.md) и [OpenAPI](docs/openapi.yaml) — маршруты и контракт.
- [Архитектура](docs/architecture.md) — как устроены каталог, API и база данных.
- [Источники данных](docs/data-sources.md), [лицензии](docs/licensing.md), [ограничения](docs/limitations.md).
- [Развёртывание](docs/deployment.md) — запуск в проде.
- [Contributing](docs/contributing.md) — вся техническая информация: быстрый старт, ETL и синхронизация источников, слои данных, разработка и проверки перед PR.

## Лицензия

Код — [MIT](LICENSE). Данные: лицензия и атрибуция каждой книги указаны в поле `attribution` каждой записи и в [docs/licensing.md](docs/licensing.md). Проект не аффилирован с Wizards of the Coast.
