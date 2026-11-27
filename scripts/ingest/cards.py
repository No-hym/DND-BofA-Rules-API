"""One file per catalog record ("cards"), grouped by ruleset, book and category.

The published catalog stores every record as its own JSON file:

    data/catalog/<edition>/<book>/<category>/<record slug>.json

e.g. ``data/catalog/2024/srd-2024/weapon/srd-2024-longsword.json`` or
``data/catalog/2014/toh/subclass/<card>.json`` — each edition (2014/2024),
each book or supplement, and each category gets its own folder, and a single
item — e.g. one weapon — can be opened, reviewed and edited on its own
instead of inside a multi-megabyte aggregated array. The slug is the record
id after the last ``:``, sanitized for file names. Readers in this
repository (the Go loader, the layer validator, machine translation) accept
both card files (a single JSON object) and legacy aggregated files (a JSON
array), so older exports keep working.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def card_slug(record_id: str) -> str:
    slug = record_id.rsplit(":", 1)[-1] if ":" in record_id else record_id
    slug = _UNSAFE.sub("-", slug).strip("-._")
    return slug or "record"


def card_filename(record_id: str, used: set[str]) -> str:
    """Deterministic, collision-free card file name within one directory."""
    base = card_slug(record_id)
    name, counter = base, 2
    while name in used:
        name = f"{base}-{counter}"
        counter += 1
    used.add(name)
    return f"{name}.json"


def write_cards(directory: Path, records: Iterable[dict[str, Any]]) -> int:
    """Write one card file per record into ``directory``.

    Stale cards (records that no longer exist) and a legacy aggregated file
    named ``<directory>.json`` next to the directory are removed, so rebuilds
    never leave orphaned records behind.
    """
    records = list(records)
    directory.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    written: set[Path] = set()
    for record in records:
        target = directory / card_filename(str(record["id"]), used)
        target.write_text(
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.add(target)
    for stale in directory.glob("*.json"):
        if stale not in written and not stale.name.endswith(".schema.json"):
            stale.unlink()
    legacy = directory.with_suffix(".json")
    if legacy.is_file():
        legacy.unlink()
    return len(records)


def write_catalog_cards(edition_dir: Path, records: Iterable[dict[str, Any]]) -> int:
    """Write one edition of the catalog as book/category card folders.

    Records are grouped into ``<edition_dir>/<book_id>/<category>/`` (one
    folder per book or supplement). Any ``*.json`` file under ``edition_dir``
    that is not a card written here — stale cards from previous builds,
    legacy flat cards, legacy aggregated ``<category>.json`` files — is
    removed, and directories left empty are pruned. Non-JSON files (e.g.
    ``LICENSE``) and ``*.schema.json`` files are kept.
    """
    records = list(records)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault((str(record["book_id"]), str(record["category"])), []).append(record)
    expected: set[Path] = set()
    for (book_id, category), group in sorted(groups.items()):
        directory = edition_dir / book_id / category
        directory.mkdir(parents=True, exist_ok=True)
        used: set[str] = set()
        for record in group:
            target = directory / card_filename(str(record["id"]), used)
            target.write_text(
                json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            expected.add(target)
    if edition_dir.is_dir():
        for file in sorted(edition_dir.rglob("*.json")):
            if file not in expected and not file.name.endswith(".schema.json"):
                file.unlink()
        for directory in sorted(
            (path for path in edition_dir.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts), reverse=True,
        ):
            if not any(directory.iterdir()):
                directory.rmdir()
    return len(records)


def read_records(path: Path) -> list[dict[str, Any]]:
    """Read records from a card file, an aggregated file, or a directory of cards."""
    if path.is_dir():
        records: list[dict[str, Any]] = []
        for file in sorted(path.rglob("*.json")):
            if file.name.endswith(".schema.json"):
                continue
            records.extend(read_records(file))
        return records
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []
