"""Generate the human-readable catalog coverage report."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    def fmt(value: Any) -> str:
        return str(value).replace("|", "\\|")
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(fmt(cell) for cell in row) + " |" for row in rows]
    return lines


def write_report(manifest: dict[str, Any]) -> Path:
    counts = manifest["counts"]
    lines = [
        "# Составкаталог: покрытие источников",
        "",
        f"Версия каталога: `{manifest['version']}`; собрано {manifest['generated_at']}. "
        "Основная редакция — D&D 5e 2024 (SRD 5.2.1); https://api.open5e.com/v2/ и дополнительные книги "
        "импортируются из зафиксированного репозитория open5e-api. Отчёт создаётся автоматически "
        "`python3 scripts/sync_sources.py build && python3 scripts/sync_sources.py verify`.",
        "",
        "## Итого",
        "",
        f"- Записей в опубликованном каталоге: **{counts['entities']}** "
        f"(2024: {counts['by_edition'].get('2024', 0)}, 2014: {counts['by_edition'].get('2014', 0)}).",
        f"- Записей с русским текстом: **{counts['translated']}**. "
        "Непереведённые записи не маскируются: RU-поле отсутствует, API отдает en с `language: en`.",
        f"- Адаптировано из других систем/редакций: "
        f"**{sum(row['adapted'] for row in manifest.get('matrix', []))}** "
        "(оригинальные механики сохранены в `mechanics.source_data`).",
        f"- Устранено дубликатов: **{counts.get('dedupe', {}).get('duplicate', 0)}**, "
        "сохранено уникальных вариантов с разными механиками: "
        f"**{counts.get('dedupe', {}).get('variant', 0)}**.",
        "",
        "## По источнику и категории",
        "",
    ]
    matrix = sorted(manifest.get("matrix", []), key=lambda row: (row["source"], row["category"]))
    lines += _table(
        ["Источник", "Категория", "Импортировано", "Переведено", "Адаптировано", "Дубликатов", "Пропущено"],
        [[row["source"], row["category"], row["imported"], row["translated"],
          row["adapted"], row["duplicates"], row["skipped"]] for row in matrix],
    )
    lines += ["", "## Подклассы", ""]
    subclass_rows: list[list[Any]] = []
    subclass_total = subclass_ru = 0
    for edition in ("2024", "2014"):
        path = REPO / "data" / "catalog" / edition / "subclass.json"
        if not path.is_file():
            continue
        import json as _json
        records = _json.loads(path.read_text(encoding="utf-8"))
        by_parent: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            parent = str(record.get("mechanics", {}).get("normalized", {}).get("subclass_of")
                         or record.get("mechanics", {}).get("source_data", {}).get("char_class") or "—")
            by_parent.setdefault(parent, []).append(record)
        for parent, subset in sorted(by_parent.items()):
            translated_count = sum(1 for record in subset
                                   if record.get("translations", {}).get("ru", {}).get("description", "").strip())
            subclass_total += len(subset)
            subclass_ru += translated_count
            subclass_rows.append([edition, parent, len(subset), translated_count,
                                  ", ".join(sorted({record.get("book_id", "") for record in subset}))])
    if subclass_rows:
        lines.append(f"Всего записей подклассов: **{subclass_total}**, с русским текстом: **{subclass_ru}**. "
                     "Подклассы Open5e v2 хранятся как `CharacterClass` с `subclass_of` и публикуются "
                     "категорией `subclass`; архетипы v1 сохранены как варианты с полным текстом. "
                     "Непереведёнными остаются только v1-варианты, для которых русский текст был бы частичным, "
                     "и подклассы с пустым описанием у источника.")
        lines.append("")
        lines += _table(["Редакция", "Родительский класс (subclass_of)", "Записей", "С RU", "Книги"],
                        subclass_rows)
    lines += ["", "## По издательству и книге", ""]
    lines += _table(["Издательство/книга", "Записей"],
                    [[key, value] for key, value in sorted(counts.get("by_book", {}).items())])
    lines += ["", "## Причины пропуска", ""]
    reasons = defaultdict(int)
    for item in manifest.get("skipped", []):
        reasons[(item.get("source", ""), item.get("reason", ""))] += 1
    lines += _table(["Источник", "Причина", "Записей"],
                    [[source, reason, count] for (source, reason), count in sorted(reasons.items())])
    lines += ["", "## Дубликаты и варианты", ""]
    duplicates = manifest.get("duplicates", [])
    variants = manifest.get("variants", [])
    duplicate_total = counts.get("dedupe", {}).get("duplicate", len(duplicates))
    variant_total = counts.get("dedupe", {}).get("variant", len(variants))
    lines += [
        f"- Удалено точных дубликатов: {duplicate_total}. Первые примеры: " +
        ", ".join(f"`{item['id']}` → `{item['duplicate_of']}`" for item in duplicates[:8]) + ".",
        f"- Сохранено вариантов: {variant_total}. Первые примеры: " +
        ", ".join(f"`{item['kept']}` ({item['reason']})" for item in variants[:8]) + ".",
        "",
        "## Лимиты",
        "",
        "- Русский текст принимается только при точном совпадении названия с лицензированным corpus; "
        "приблизительное сопоставление не применяется.",
        "- Сайты 5esrd и a5esrd не публикуют structured dump: в каталог попадают их разделы/ PDF-индексы "
        "со ссылками и лицензией, а полные механики импортируются из Open5e.",
        "- Машинный перевод через LLM не вызывается автоматически; для закрытых пробелов используйте "
        "`go run ./cmd/rules translate` с собственной моделью и последующей вычиткой.",
        "",
    ]
    target = REPO / "docs" / "catalog-stats.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target
