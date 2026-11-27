# Составкаталог: покрытие источников

Версия каталога: `20261128`; собрано 2026-11-27T03:32:13+00:00. Основная редакция — D&D 5e 2024 (SRD 5.2.1); https://api.open5e.com/v2/ и дополнительные книги импортируются из зафиксированного репозитория open5e-api. Отчёт создаётся автоматически `python3 scripts/sync_sources.py build && python3 scripts/sync_sources.py verify`.

## Итого

- Записей в опубликованном каталоге: **12703** (2024: 2047, 2014: 10656).
- Записей с русским текстом: **11259**. Непереведённые записи не маскируются: RU-поле отсутствует, API отдает en с `language: en`.
- Адаптировано из других систем/редакций: **10656** (оригинальные механики сохранены в `mechanics.source_data`).
- Устранено дубликатов: **8908**, сохранено уникальных вариантов с разными механиками: **2771**.

## По источнику и категории

| Источник | Категория | Импортировано | Переведено | Адаптировано | Дубликатов | Пропущено |
|---|---|---|---|---|---|---|
| 5esrd | reference | 77 | 77 | 77 | 0 | 0 |
| a5esrd | reference | 31 | 31 | 31 | 0 | 0 |
| open5e | ability | 24 | 24 | 18 | 0 | 0 |
| open5e | alignment | 27 | 27 | 18 | 0 | 0 |
| open5e | armor | 36 | 36 | 23 | 12 | 0 |
| open5e | attack | 1200 | 1200 | 1060 | 4044 | 0 |
| open5e | background | 85 | 85 | 81 | 15 | 0 |
| open5e | class | 41 | 41 | 29 | 12 | 0 |
| open5e | condition | 85 | 85 | 70 | 1 | 0 |
| open5e | creature-set | 1 | 1 | 1 | 0 | 0 |
| open5e | creature-type | 26 | 26 | 22 | 0 | 0 |
| open5e | damage-type | 25 | 25 | 19 | 0 | 0 |
| open5e | environment | 31 | 31 | 31 | 0 | 0 |
| open5e | equipment | 440 | 440 | 237 | 0 | 0 |
| open5e | feat | 139 | 139 | 122 | 26 | 0 |
| open5e | image | 32 | 32 | 32 | 0 | 0 |
| open5e | item-category | 24 | 24 | 22 | 0 | 0 |
| open5e | item-rarity | 6 | 6 | 6 | 0 | 0 |
| open5e | item-set | 20 | 20 | 20 | 0 | 0 |
| open5e | language | 19 | 19 | 19 | 0 | 0 |
| open5e | magic-item | 2978 | 2281 | 2218 | 962 | 0 |
| open5e | monster | 4408 | 4041 | 4077 | 2340 | 0 |
| open5e | plane | 8 | 8 | 8 | 0 | 0 |
| open5e | rule | 341 | 341 | 285 | 0 | 0 |
| open5e | ruleset | 54 | 54 | 43 | 0 | 0 |
| open5e | service | 30 | 30 | 0 | 0 | 0 |
| open5e | size | 7 | 7 | 7 | 0 | 0 |
| open5e | skill | 61 | 61 | 48 | 0 | 0 |
| open5e | species | 45 | 45 | 36 | 4 | 0 |
| open5e | spell | 1967 | 1692 | 1628 | 1423 | 0 |
| open5e | spell-list | 7 | 7 | 7 | 0 | 0 |
| open5e | spell-school | 9 | 9 | 9 | 0 | 0 |
| open5e | subclass | 247 | 145 | 235 | 1 | 0 |
| open5e | subspecies | 37 | 37 | 37 | 31 | 0 |
| open5e | weapon | 106 | 103 | 68 | 37 | 0 |
| open5e | weapon-property | 29 | 29 | 12 | 0 | 0 |

## Подклассы

Всего записей подклассов: **247**, с русским текстом: **145**. Подклассы Open5e v2 хранятся как `CharacterClass` с `subclass_of` и публикуются категорией `subclass`; архетипы v1 сохранены как варианты с полным текстом. Непереведёнными остаются только v1-варианты, для которых русский текст был бы частичным, и подклассы с пустым описанием у источника.

| Редакция | Родительский класс (subclass_of) | Записей | С RU | Книги |
|---|---|---|---|---|
| 2024 | srd-2024_barbarian | 1 | 1 | srd-2024 |
| 2024 | srd-2024_bard | 1 | 1 | srd-2024 |
| 2024 | srd-2024_cleric | 1 | 1 | srd-2024 |
| 2024 | srd-2024_druid | 1 | 1 | srd-2024 |
| 2024 | srd-2024_fighter | 1 | 1 | srd-2024 |
| 2024 | srd-2024_monk | 1 | 1 | srd-2024 |
| 2024 | srd-2024_paladin | 1 | 1 | srd-2024 |
| 2024 | srd-2024_ranger | 1 | 1 | srd-2024 |
| 2024 | srd-2024_rogue | 1 | 1 | srd-2024 |
| 2024 | srd-2024_sorcerer | 1 | 1 | srd-2024 |
| 2024 | srd-2024_warlock | 1 | 1 | srd-2024 |
| 2024 | srd-2024_wizard | 1 | 1 | srd-2024 |
| 2014 | a5e_marshal | 3 | 0 | a5e-ag |
| 2014 | barbarian | 9 | 0 | taldorei, toh, wotc-srd |
| 2014 | bard | 8 | 1 | o5e, toh, wotc-srd |
| 2014 | bfrd_barbarian | 1 | 1 | bfrd |
| 2014 | bfrd_bard | 1 | 1 | bfrd |
| 2014 | bfrd_cleric | 2 | 2 | bfrd |
| 2014 | bfrd_druid | 1 | 1 | bfrd |
| 2014 | bfrd_fighter | 1 | 1 | bfrd |
| 2014 | bfrd_mechanist | 1 | 1 | bfrd |
| 2014 | bfrd_monk | 1 | 1 | bfrd |
| 2014 | bfrd_paladin | 1 | 1 | bfrd |
| 2014 | bfrd_ranger | 1 | 1 | bfrd |
| 2014 | bfrd_rogue | 1 | 1 | bfrd |
| 2014 | bfrd_sorcerer | 1 | 1 | bfrd |
| 2014 | bfrd_theurge | 1 | 1 | bfrd |
| 2014 | bfrd_vanguard | 1 | 1 | bfrd |
| 2014 | bfrd_warlock | 1 | 1 | bfrd |
| 2014 | bfrd_witch | 1 | 1 | bfrd |
| 2014 | bfrd_wizard | 1 | 1 | bfrd |
| 2014 | cleric | 12 | 2 | o5e, taldorei, toh, wotc-srd |
| 2014 | druid | 9 | 0 | o5e, toh, wotc-srd |
| 2014 | fighter | 8 | 0 | o5e, toh, wotc-srd |
| 2014 | monk | 10 | 0 | o5e, taldorei, toh, wotc-srd |
| 2014 | paladin | 8 | 0 | o5e, toh, wotc-srd |
| 2014 | ranger | 7 | 0 | toh, wotc-srd |
| 2014 | rogue | 8 | 1 | o5e, toh, wotc-srd |
| 2014 | sorcerer | 9 | 1 | o5e, taldorei, toh, wotc-srd |
| 2014 | srd-2024_wizard | 1 | 1 | open5e |
| 2014 | srd_barbarian | 9 | 9 | srd-2014, tdcs, toh |
| 2014 | srd_bard | 8 | 8 | open5e, srd-2014, toh |
| 2014 | srd_cleric | 12 | 12 | open5e, srd-2014, tdcs, toh |
| 2014 | srd_druid | 9 | 9 | open5e, srd-2014, toh |
| 2014 | srd_fighter | 8 | 8 | open5e, srd-2014, toh |
| 2014 | srd_monk | 10 | 10 | open5e, srd-2014, tdcs, toh |
| 2014 | srd_paladin | 8 | 8 | open5e, srd-2014, toh |
| 2014 | srd_ranger | 7 | 7 | srd-2014, toh |
| 2014 | srd_rogue | 8 | 8 | open5e, srd-2014, toh |
| 2014 | srd_sorcerer | 9 | 9 | open5e, srd-2014, tdcs, toh |
| 2014 | srd_warlock | 9 | 9 | open5e, srd-2014, toh |
| 2014 | srd_wizard | 11 | 11 | open5e, srd-2014, toh |
| 2014 | warlock | 8 | 1 | o5e, toh, wotc-srd |
| 2014 | wizard | 10 | 1 | o5e, toh, wotc-srd |

## По издательству и книге

| Издательство/книга | Записей |
|---|---|
| a5e/a5e | 610 |
| en-publishing/a5e-ag | 505 |
| en-publishing/a5e-ddg | 4 |
| en-publishing/a5e-gpg | 2 |
| en-publishing/a5e-mm | 790 |
| en-publishing/a5esrd | 31 |
| green-ronin/tdcs | 16 |
| kobold-press/bfrd | 563 |
| kobold-press/ccdx | 528 |
| kobold-press/deepm | 515 |
| kobold-press/deepmx | 64 |
| kobold-press/kp | 31 |
| kobold-press/tob | 552 |
| kobold-press/tob-2023 | 210 |
| kobold-press/tob2 | 581 |
| kobold-press/tob3 | 397 |
| kobold-press/toh | 239 |
| kobold-press/vom | 1063 |
| kobold-press/wz | 43 |
| kp/kp | 1 |
| menagerie/menagerie | 283 |
| o5e/o5e | 19 |
| open-gaming-network/5esrd | 77 |
| open5e/core | 154 |
| open5e/elderberry-inn-icons | 20 |
| open5e/open5e | 33 |
| somanyrobots/spells-that-dont-suck | 180 |
| taldorei/taldorei | 13 |
| tob-2023/tob-2023 | 408 |
| tob/tob | 346 |
| tob2/tob2 | 378 |
| toh/toh | 157 |
| vom/vom | 51 |
| wizards-of-the-coast/srd-2014 | 1596 |
| wizards-of-the-coast/srd-2024 | 2047 |
| wotc-srd/wotc-srd | 196 |

## Причины пропуска

| Источник | Причина | Записей |
|---|---|---|
| open5e:v2 | orphan nested object without a parent or name | 173 |

## Дубликаты и варианты

- Удалено точных дубликатов: 8908. Первые примеры: `o5e:wotc-srd:armor:breastplate` → `o5e:srd-2014:armor:srd-breastplate`, `o5e:wotc-srd:armor:chain-mail` → `o5e:srd-2014:armor:srd-chain-mail`, `o5e:wotc-srd:armor:chain-shirt` → `o5e:srd-2014:armor:srd-chain-shirt`, `o5e:wotc-srd:armor:half-plate` → `o5e:srd-2014:armor:srd-half-plate`, `o5e:wotc-srd:armor:hide` → `o5e:srd-2014:armor:srd-hide`, `o5e:wotc-srd:armor:leather` → `o5e:srd-2014:armor:srd-leather`, `o5e:wotc-srd:armor:padded` → `o5e:srd-2014:armor:srd-padded`, `o5e:wotc-srd:armor:plate` → `o5e:srd-2014:armor:srd-plate`.
- Сохранено вариантов: 2771. Первые примеры: `o5e:srd-2014:abilitydescription:srd-2014-cha-variant-2` (same name with materially different rules text or system), `o5e:srd-2014:abilitydescription:srd-2014-con-variant-2` (same name with materially different rules text or system), `o5e:srd-2014:abilitydescription:srd-2014-dex-variant-2` (same name with materially different rules text or system), `o5e:srd-2014:abilitydescription:srd-2014-int-variant-2` (same name with materially different rules text or system), `o5e:srd-2014:abilitydescription:srd-2014-str-variant-2` (same name with materially different rules text or system), `o5e:srd-2014:abilitydescription:srd-2014-wis-variant-2` (same name with materially different rules text or system), `o5e:srd-2014:alignmentdescription:srd-2014-chaotic-evil-variant-2` (same name with materially different rules text or system), `o5e:srd-2014:alignmentdescription:srd-2014-chaotic-good-variant-2` (same name with materially different rules text or system).

## Лимиты

- Русский текст принимается только при точном совпадении названия с лицензированным corpus; приблизительное сопоставление не применяется.
- Сайты 5esrd и a5esrd не публикуют structured dump: в каталог попадают их разделы/ PDF-индексы со ссылками и лицензией, а полные механики импортируются из Open5e.
- Машинный перевод через LLM не вызывается автоматически; для закрытых пробелов используйте `go run ./cmd/rules translate` с собственной моделью и последующей вычиткой.
