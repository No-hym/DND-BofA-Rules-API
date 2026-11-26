# Источники данных и лицензии

## Английский SRD

Материал SRD 5.2.1 (Wizards of the Coast LLC) используется по CC BY 4.0: https://creativecommons.org/licenses/by/4.0/legalcode. Официальная страница: https://www.dndbeyond.com/srd.

Структурированный набор: [bankenichi/5etools-srd, commit `3b26955ea5394fde43a1e33b2a878b42cebbe51c`](https://github.com/bankenichi/5etools-srd/tree/3b26955ea5394fde43a1e33b2a878b42cebbe51c), опубликован под CC BY 4.0 с атрибуцией Wizards of the Coast. Импортёр сохраняет исходные структуры под `mechanics.source_data`.

## Русские переводы

Русские тексты разделов существ, состояний, происхождений/видов, черт, снаряжения, заклинаний и магических предметов взяты из [OmnisGM-App/OmnisGM-Rules, commit `1f7192be159e84f2db7212565866747094e3b9de`](https://github.com/OmnisGM-App/OmnisGM-Rules/tree/1f7192be159e84f2db7212565866747094e3b9de/src/dnd/srd-5.2/ru), автор перевода Petr Radilov; CC BY 4.0 в соответствии с лицензией источника. Для существ также используется ранее импортированный источник [my-git-store/nastolka-dnd-reference, commit `547fc77f31649f69ff67c97699125d491f2f9209`](https://github.com/my-git-store/nastolka-dnd-reference/tree/547fc77f31649f69ff67c97699125d491f2f9209).

В новых категориях importer засчитывает русский текст только при точном совпадении английского названия в заголовке перевода или точном совпадении заголовка семейства. Пробелы не маскируются придуманным переводом: у 170 записей (137 `item`, 33 `equipment`) русское описание пустое, имя — английский fallback, статус `source` не выставлен. Переводы с `source` атрибутированы, но не проходили независимую вычитку в этом проекте. Атрибуция включена в каждую запись и `data/catalog/2024/LICENSE`.

## Воспроизведение дополнительных категорий

Скачайте архивы закреплённых коммитов из GitHub, распакуйте их вне репозитория, затем выполните:

```sh
python3 scripts/sync_srd521.py \
  --srd-data /path/to/5etools-srd/data \
  --ru-rules /path/to/OmnisGM-Rules/src/dnd/srd-5.2/ru
```

Для пересборки существующих монстров/состояний дополнительно передайте соответствующие аргументы `--monsters-source`, `--conditions-source`, `--ru-monsters` и `--ru-glossary`; см. `python3 scripts/sync_srd521.py --help`.

Этот проект не аффилирован с Wizards of the Coast LLC и не одобрен ею.
