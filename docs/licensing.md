# Лицензии и атрибуция

1. **Код:** MIT, см. корневой `LICENSE`. Утилиты ETL — часть кода и распространяются на тех же условиях.
2. **Структурированные данные Open5e:** лицензия определяется per-document в `data/v2/License.json` upstream: CC BY 4.0, OGL 1.0a или CC0. `sync_sources.py` пропускает документы без лицензии. Для каждой записи сохраняются автор, издатель, название книги, permalink, редакция правил и идентификатор лицензии (`license`) + URL (`mechanics.license_url`) + полный TASL (`attribution`).
3. **Содержимое Wotc SRD 5.2:** CC BY 4.0, © Wizards of the Coast LLC. Атрибуция: «This work includes material from the System Reference Document 5.2.1 ("SRD 5.2.1") by Wizards of the Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the Creative Commons Attribution 4.0 International License, available at https://creativecommons.org/licenses/by/4.0/legalcode».
4. **Русские переводы OmnisGM:** CC BY 4.0, Petr Radilov (https://github.com/OmnisGM-App/OmnisGM-Rules). Являются производным материалом SRD и сохраняют атрибуцию оригинала.
5. **Русские тексты SRD 5.1 RU:** CC BY-SA 4.0, сообщество «Киборги и Чародеи», Антон Палихов (Palant), Featona, Damir, Mongo, xattttta (https://github.com/palikhov/srd-dnd-5e-ru). Производные от этих RU-текстов материалы должны распространяться на условиях CC BY-SA 4.0; исходный SRD остаётся CC BY 4.0. Источник перевода фиксируется в `mechanics.translation_provenance` каждой записи.
6. **5esrd:** OGL 1.0a с большим списком per-product copyright notices. В каталог попадают только ссылки/названия разделов; полная копия контента сайта не распространяется. Полный текст уведомлений: https://www.5esrd.com/legal-information/.
7. **A5ESRD:** CC BY 4.0 + OGL 1.0a + ORC. Обязательная атрибуция: «A5E System Reference Document (A5ESRD), © EN Publishing, www.a5esrd.com; based on Level Up: Advanced 5th Edition, www.levelup5e.com». См. https://a5esrd.com/a5esrd.
8. **Машинный перевод:** при явном вызове `sync_sources.py translate` результат помечается `status: machine`; он не считается вычитанным и не должен публиковаться без ревью. originating English всегда сохраняется в `translations.en`.
9. **A5E/сторонние системы:** в каталоге хранится как данные с `mechanics.original_system` и `compatibility`;DND-BofA не заявляет совместимость с коммерческими книгами, не входящими в SRD/OGL/CC набора.

Перед публичным выпуском нового источника или книги требуется человеческая юридическая проверка. Эта документация не является юридической консультацией.
