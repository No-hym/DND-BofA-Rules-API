"""Validation of the three separated catalog layers and the published merge."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CYRILLIC = re.compile(r"[\u0400-\u04ff]")
ENGLISH_RUN = re.compile(r"\b(?:the|and|you|with|that|this|of|in|for|when|from)\b", re.I)
STATUSES = {"source", "machine", "reviewed", "outdated"}
REQUIRED = {"id", "category", "edition", "publisher_id", "book_id", "source", "license",
            "version", "external_id", "translations", "mechanics", "attribution"}


def _records(path: Path) -> list[tuple[str, list[dict[str, Any]]]]:
    result: list[tuple[str, list[dict[str, Any]]]] = []
    if not path.is_dir():
        return result
    for file in sorted(path.rglob("*.json")):
        if file.name.endswith(".schema.json"):
            continue
        data = json.loads(file.read_text(encoding="utf-8"))
        if isinstance(data, list):
            result.append((str(file), data))
    return result


def validate_dirs(root: Path) -> list[str]:
    problems: list[str] = []
    seen: dict[str, str] = {}
    translated_ids: set[str] = set()
    for layer in ("normalized", "translated", "catalog"):
        for path, records in _records(root / layer):
            for index, record in enumerate(records):
                label = f"{path}#{index}"
                if layer == "translated":
                    if not record.get("id") or not CYRILLIC.search(record.get("translation", {}).get("name", "")):
                        problems.append(f"{label}: translated entry needs an id and Cyrillic name")
                    translated_ids.add(record["id"])
                    continue
                missing = REQUIRED - set(record)
                if missing:
                    problems.append(f"{label}: missing fields {sorted(missing)}")
                    continue
                if record["edition"] not in ("2014", "2024"):
                    problems.append(f"{label}: unsupported edition {record['edition']}")
                if layer == "normalized" and set(record["translations"]) != {"en"}:
                    problems.append(f"{label}: normalized layer must contain English only")
                for code, translation in record["translations"].items():
                    if code not in ("en", "ru"):
                        problems.append(f"{label}: unsupported language {code}")
                    if not translation.get("name"):
                        problems.append(f"{label}: empty {code} name")
                    if translation.get("status") and translation["status"] not in STATUSES:
                        problems.append(f"{label}: invalid status {translation['status']}")
                    if code == "ru":
                        if not CYRILLIC.search(translation["name"]):
                            problems.append(f"{label}: RU name is not translated")
                        words = re.findall(r"[A-Za-zА-Яа-яЁё]+", translation.get("description", ""))
                        english = len(ENGLISH_RUN.findall(translation.get("description", "")))
                        if words and english >= 3 and english > len(words) * 0.12:
                            problems.append(f"{label}: RU description contains untranslated English rules")
                if not isinstance(record["mechanics"], dict):
                    problems.append(f"{label}: mechanics must be an object")
                if not record["attribution"]:
                    problems.append(f"{label}: attribution is empty")
                if layer == "catalog":
                    if record["id"] in seen:
                        problems.append(f"{label}: duplicate id {record['id']} (also {seen[record['id']]})")
                    seen[record["id"]] = label
    missing_translations = translated_ids - set(seen)
    if missing_translations:
        problems.append(f"translated ids missing in catalog: {len(missing_translations)}")
    return problems
