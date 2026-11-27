"""One file per catalog record ("cards").

The published catalog stores every record as its own JSON file:

    data/catalog/<edition>/<category>/<record slug>.json

so a single item — e.g. one weapon — can be opened, reviewed and edited on
its own instead of inside a multi-megabyte aggregated array. The slug is the
record id after the last ``:``, sanitized for file names. Readers in this
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
