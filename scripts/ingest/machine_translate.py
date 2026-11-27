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
    # Card layout: one record per file under catalog/<edition>/<category>/.
    # Legacy aggregated files (a JSON array) are handled record by record too.
    paths = sorted(
        path for path in (root / "catalog" / edition).rglob("*.json")
        if not path.name.endswith(".schema.json")
    )
    for path in paths:
        if translated >= limit:
            break
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data if isinstance(data, list) else [data]
        changed = False
        for record in records:
            if "ru" in record["translations"] or translated >= limit:
                continue
            en = record["translations"]["en"]
            item = {"name": en["name"], "description": en.get("description", "")}
            translated += _flush(record, item, endpoint, model, glossary)
            changed = True
        if changed:
            payload = records if isinstance(data, list) else records[0]
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    return translated


def _flush(record: dict[str, Any], source: dict[str, str], endpoint: str, model: str,
           glossary: dict[str, str]) -> int:
    """Translate one record in place; the caller persists its card file."""
    (result,) = translate_batch([source], endpoint, model, glossary)
    name = str(result.get("name", "")).strip()
    description = str(result.get("description", "")).strip()
    if not CYRILLIC.search(name) or (source["description"] and not CYRILLIC.search(description)):
        return 0
    record["translations"]["ru"] = Translation(
        name=name, description=description, status="machine",
        source_version=record.get("version", ""), glossary_version="machine",
    ).to_json()
    record["mechanics"]["translation_provenance"] = {
        "source": f"machine-translation:{model}", "license": "derivative of source license",
        "attribution": "Machine translation; requires editorial review", "status": "machine",
    }
    return 1
