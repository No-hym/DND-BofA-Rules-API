"""Optional OpenAI-compatible machine translation for catalog gaps.

Never called by the API or by an unattended sync: an operator must supply an
endpoint and model explicitly. Results are marked `machine` and remain subject
to editorial review; the English source text is never overwritten.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

from .model import Translation, from_record
from .translations import CYRILLIC

SYSTEM_PROMPT = (
    "You are a professional D&D 5e Russian localizer. Translate the supplied JSON object "
    "into Russian using established Russian D&D terminology. Return only valid JSON with "
    "the same keys: name, description. Keep game mechanics terms consistent, do not use "
    "machine-like word-for-word calques, and do not leave English sentences."
)


def translate_batch(items: list[dict[str, str]], endpoint: str, model: str,
                    glossary: dict[str, str], timeout: int = 120) -> list[dict[str, str]]:
    glossary_hint = "; ".join(f"{key}=>.{value}" for key, value in list(glossary.items())[:60])
    user = json.dumps({"glossary": glossary_hint, "items": items}, ensure_ascii=False)
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if os.environ.get("LLM_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["LLM_API_KEY"]
    request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    text = payload["choices"][0]["message"]["content"].strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("translation endpoint returned no JSON object")
    decoded = json.loads(match.group(0))
    if isinstance(decoded, dict) and "items" in decoded:
        decoded = decoded["items"]
    if not isinstance(decoded, list) or len(decoded) != len(items):
        raise ValueError("translation endpoint returned an unexpected number of items")
    return decoded


def translate_catalog(root: Path, endpoint: str, model: str, edition: str,
                      limit: int, glossary: dict[str, str]) -> int:
    """Fill missing RU translations in the published layer; English remains untouched."""
    translated = 0
    for path in sorted((root / "catalog" / edition).glob("*.json")):
        if path.name.endswith(".schema.json"):
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        batch: list[tuple[dict[str, Any], dict[str, str]]] = []
        for record in records:
            if "ru" in record["translations"] or translated >= limit:
                continue
            en = record["translations"]["en"]
            batch.append((record, {"name": en["name"], "description": en.get("description", "")}))
            if len(batch) >= 20:
                translated += _flush(path, records, batch, endpoint, model, glossary)
                batch = []
            if translated >= limit:
                break
        if batch:
            translated += _flush(path, records, batch, endpoint, model, glossary)
        if translated >= limit:
            break
    return translated


def _flush(path: Path, records: list[dict[str, Any]],
           batch: list[tuple[dict[str, Any], dict[str, str]]],
           endpoint: str, model: str, glossary: dict[str, str]) -> int:
    results = translate_batch([item for _, item in batch], endpoint, model, glossary)
    count = 0
    for (record, source), result in zip(batch, results):
        name = str(result.get("name", "")).strip()
        description = str(result.get("description", "")).strip()
        if not CYRILLIC.search(name) or (source["description"] and not CYRILLIC.search(description)):
            continue
        record["translations"]["ru"] = Translation(
            name=name, description=description, status="machine",
            source_version=record.get("version", ""), glossary_version="machine",
        ).to_json()
        record["mechanics"]["translation_provenance"] = {
            "source": f"machine-translation:{model}", "license": "derivative of source license",
            "attribution": "Machine translation; requires editorial review", "status": "machine",
        }
        count += 1
    path.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return count
