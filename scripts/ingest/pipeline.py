"""Build layered, versioned catalogs from pinned open data snapshots."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dedupe import deduplicate
from .model import Entity, Translation, from_record, slug
from .open5e import Open5eAdapter
from .sites import attach_references, site_5esrd, site_a5esrd
from .translations import (TranslationMemory, apply, from_legacy_catalog,
                           from_markdown_corpus, from_russian_only_corpus)

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"


def _write_json(path: Path, value: Any, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    options = {"separators": (",", ":")} if compact else {"indent": 2}
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, **options) + "\n", encoding="utf-8")


def _write_jsonl_gz(path: Path, records: list[dict[str, Any]]) -> None:
    import gzip
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config() -> dict[str, Any]:
    return json.loads((DATA / "sources" / "sources.json").read_text(encoding="utf-8"))


def build_memory(config: dict[str, Any], snapshot_root: Path, legacy_root: Path) -> tuple[TranslationMemory, dict[str, int]]:
    memory_path = DATA / "translations" / "memory.json"
    memory = TranslationMemory()
    if memory_path.exists():
        memory = TranslationMemory.from_json(json.loads(memory_path.read_text(encoding="utf-8")))
    counts: dict[str, int] = {}
    counts["legacy_catalog"] = from_legacy_catalog(legacy_root, memory)
    for source in config["sources"]:
        if source["kind"] != "translation" or source["id"] == "dnd-bofa-legacy":
            continue
        root = snapshot_root / source["id"]
        if not root.is_dir():
            continue
        edition = "2024" if "5.2" in source["id"] or source["id"] == "omnigm" else "2014"
        attribution = f"{source.get('translator', 'Various')} ({source['url']})"
        if source["id"] == "srd-ru":
            count = from_russian_only_corpus(root, edition, source["id"], attribution, source["license"], memory)
        else:
            count = from_markdown_corpus(
                root, edition, source["id"], attribution, source["license"], memory,
            )
        counts[source["id"]] = count
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(
        json.dumps(memory.to_json(), ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return memory, counts


def build(snapshot_root: Path, legacy_root: Path | None = None,
          release_version: str | None = None) -> dict[str, Any]:
    config = load_config()
    legacy_root = legacy_root or (DATA / "legacy" / "2024")
    if not legacy_root.is_dir():
        legacy_root = DATA / "catalog" / "2024"

    entities: list[Entity] = []
    adapter_stats: dict[str, Any] = {}
    skipped: list[dict[str, str]] = []

    for version in ("v2", "v1"):
        source_root = snapshot_root / "open5e-api" / "data"
        adapter = Open5eAdapter(config, source_root)
        batch = adapter.build(version)
        entities.extend(batch)
        adapter_stats[f"open5e:{version}"] = dict(adapter.stats)
        skipped.extend({"source": "open5e:" + version, **item} for item in adapter.skipped)

    source_conf = {source["id"]: source for source in config["sources"]}
    references = site_5esrd(source_conf["5esrd"], DATA / "original")
    references += site_a5esrd(source_conf["a5esrd"], DATA / "original")
    adapter_stats["5esrd"] = {"imported": len([r for r in references if r.source == "5esrd"])}
    adapter_stats["a5esrd"] = {"imported": len([r for r in references if r.source == "a5esrd"])}
    attached = attach_references(entities, references)
    adapter_stats["references_attached"] = attached
    entities.extend(references)

    # Preserve every previously published stable ID as an alias and every RU text.
    legacy_ids: dict[tuple[str, str, str], str] = {}
    for path in sorted(legacy_root.rglob("*.json")):
        if path.name.endswith(".schema.json"):
            continue
        for record in json.loads(path.read_text(encoding="utf-8")):
            en = (record.get("translations", {}).get("en") or {}).get("name", "")
            legacy_ids[(record.get("edition", ""), record.get("category", ""), slug(en.lower()))] = record["id"]

    memory, memory_counts = build_memory(config, snapshot_root, legacy_root)
    adapter_stats["translation_memory"] = memory_counts
    translated = 0
    for entity in entities:
        legacy_id = legacy_ids.get((entity.edition, entity.category, slug(entity.name.lower())))
        if legacy_id and legacy_id != entity.id:
            entity.aliases.add(legacy_id)
        if apply(memory, entity, "v1") and entity.translations["ru"].description.strip():
            translated += 1

    entities, dedupe_report = deduplicate(entities)
    adapter_stats["dedupe"] = dedupe_report["counts"]

    # Layer 1: normalized English records (no translations applied).
    for edition in ("2014", "2024"):
        normalized: dict[str, list[dict[str, Any]]] = defaultdict(list)
        translated_layer: dict[str, list[dict[str, Any]]] = defaultdict(list)
        catalog: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entity in entities:
            if entity.edition != edition:
                continue
            record = entity.to_record()
            if "ru" in record["translations"] and not record["translations"]["ru"]["description"].strip():
                # A translated name alone is kept in the translation layer, not in the
                # bilingual catalog: clients must never see an empty RU description.
                del record["translations"]["ru"]
                entity.translations.pop("ru", None)
            normalized[entity.category].append({
                **{key: value for key, value in record.items() if key != "translations"},
                "translations": {"en": record["translations"]["en"]},
            })
            if "ru" in entity.translations:
                translated_layer[entity.category].append({
                    "id": entity.id,
                    "language": "ru",
                    "translation": record["translations"]["ru"],
                    "provenance": entity.mechanics.get("translation_provenance", {}),
                    "partial": not entity.translations.get("ru", Translation("", "")).description.strip(),
                })
            catalog[entity.category].append(record)
        for category, records in catalog.items():
            _write_json(DATA / "catalog" / edition / f"{category}.json", records, compact=True)
        for layer, data in (("normalized", normalized), ("translated", translated_layer)):
            _write_jsonl_gz(DATA / layer / edition / f"{layer}.jsonl.gz",
                            [record for records in data.values() for record in records])

    catalog_license = DATA / "catalog" / "2024" / "LICENSE"
    catalog_license.parent.mkdir(parents=True, exist_ok=True)
    if not catalog_license.exists():
        catalog_license.write_text(
            "Content in this directory is attributed per record in the `attribution` field. "
            "SRD content: CC BY 4.0, © Wizards of the Coast. See docs/licensing.md.\n",
            encoding="utf-8",
        )

    version = release_version or datetime.now(timezone.utc).strftime("%Y%m%d")
    manifest = {
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "primary_edition": config["primary_edition"],
        "sources": config["sources"],
        "snapshot_files": [],
        "counts": {
            "entities": len(entities),
            "translated": translated,
            "by_edition": dict(Counter(entity.edition for entity in entities)),
            "by_category": dict(Counter(entity.category for entity in entities)),
            "by_source": dict(Counter(entity.source.split(":")[0] for entity in entities)),
            "dedupe": dedupe_report["counts"],
        },
        "adapter_stats": adapter_stats,
        "skipped": skipped[:5000],
        "duplicates": dedupe_report["duplicates"][:5000],
        "variants": dedupe_report["variants"][:5000],
    }
    manifest["counts"]["by_book"] = {
        f"{publisher}/{book}": count for (publisher, book), count in
        Counter((entity.publisher_id, entity.book_id) for entity in entities).items()
    }
    matrix: list[dict[str, Any]] = []
    source_names = sorted({entity.source.split(":")[0] for entity in entities})
    for source_name in source_names:
        for category in sorted({entity.category for entity in entities}):
            subset = [entity for entity in entities if entity.source.split(":")[0] == source_name
                      and entity.category == category]
            if not subset:
                continue
            duplicates = sum(1 for item in dedupe_report["duplicates"]
                             if item.get("source", "").startswith(source_name) and item.get("category") == category)
            matrix.append({
                "source": source_name,
                "category": category,
                "imported": len(subset),
                "translated": sum(1 for entity in subset if "ru" in entity.translations),
                "adapted": sum(1 for entity in subset if entity.mechanics.get("compatibility", {}).get("adapted")),
                "duplicates": duplicates,
                "skipped": 0,
            })
    manifest["matrix"] = matrix
    original_dir = DATA / "original"
    if original_dir.is_dir():
        for path in sorted(original_dir.rglob("*")):
            if path.is_file() and path.stat().st_size < 100_000_000:
                manifest["snapshot_files"].append({
                    "path": str(path.relative_to(REPO)), "sha256": _sha256(path),
                    "size": path.stat().st_size,
                })
    _write_json(DATA / "releases" / f"v{version}.json", manifest, compact=True)
    (DATA / "releases" / "latest.json").write_text(
        json.dumps({"version": version, "catalog": "data/catalog", "manifest": f"data/releases/v{version}.json"},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    aliases = {
        alias: entity.id for entity in entities for alias in entity.aliases
    }
    _write_json(DATA / "releases" / "aliases.json", aliases, compact=True)
    _write_json(DATA / "api" / "catalog-meta.json", {
        "version": version,
        "primary_edition": config["primary_edition"],
        "entities": len(entities),
        "by_edition": manifest["counts"]["by_edition"],
        "by_category": manifest["counts"]["by_category"],
        "by_source": manifest["counts"]["by_source"],
        "by_book": manifest["counts"]["by_book"],
        "translated": translated,
        "dedupe": dedupe_report["counts"],
        "sources": [{
            "id": source["id"], "title": source["title"], "url": source["url"],
            "license": source.get("license", ""), "role": source.get("role", ""),
            "commit": source.get("commit", ""),
        } for source in config["sources"]],
    }, compact=True)
    return manifest
