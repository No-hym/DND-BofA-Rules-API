"""Deterministic de-duplication that never discards distinct rules text.

Two records are duplicates only when category, edition, normalized English
name, normalized description and original rules system all match. Records with
the same name but different text (different editions, books or homebrew
variants) are kept and linked with ``variant_of``.
"""

from __future__ import annotations

import copy
import re
from collections import defaultdict
from typing import Any

from .model import Entity, slug

_WS = re.compile(r"\s+")


def _key(entity: Entity) -> tuple[str, str, str]:
    return entity.edition, entity.category, slug(entity.name.lower())


def _description(entity: Entity) -> str:
    return _WS.sub(" ", entity.description).strip().casefold()[:2000]


def _system(entity: Entity) -> str:
    return str(entity.mechanics.get("original_system", ""))


def _preferred(entity: Entity) -> tuple[bool, bool, int, str]:
    return (entity.edition != "2024", "v1" in entity.source, len(entity.id), entity.id)


def deduplicate(entities: list[Entity]) -> tuple[list[Entity], dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[Entity]] = defaultdict(list)
    for entity in entities:
        groups[_key(entity)].append(entity)

    report: dict[str, Any] = {
        "duplicates": [],
        "variants": [],
        "counts": {"duplicate": 0, "variant": 0, "kept": 0},
    }
    result: list[Entity] = []
    for key, items in sorted(groups.items(), key=lambda pair: str(pair[0])):
        if len(items) == 1:
            result.append(items[0])
            report["counts"]["kept"] += 1
            continue
        by_content: dict[tuple[str, str], list[Entity]] = defaultdict(list)
        for entity in items:
            by_content[(_description(entity), _system(entity))].append(entity)
        ordered = sorted(by_content.values(), key=lambda group: (-len(group), _description(group[0])))
        group_primary_id = ""
        for index, twins in enumerate(ordered):
            twins = sorted(twins, key=_preferred)
            primary = copy.deepcopy(twins[0])
            if index == 0:
                group_primary_id = primary.id
            else:
                primary.id = f"{primary.id}-variant-{index + 1}"
                primary.mechanics["variant_of"] = group_primary_id
                report["variants"].append({
                    "kept": primary.id, "name": primary.name,
                    "reason": "same name with materially different rules text or system",
                })
                report["counts"]["variant"] += 1
            provenance = []
            for twin in twins:
                provenance.append({
                    "id": twin.id, "source": twin.source, "book": twin.book_id,
                    "edition": twin.edition, "license": twin.license,
                    "content_hash": twin.mechanics.get("content_hash", ""),
                })
                primary.aliases.add(twin.id)
                if twin is not twins[0]:
                    report["duplicates"].append({
                        "id": twin.id, "duplicate_of": primary.id, "name": twin.name,
                        "category": twin.category, "source": twin.source,
                        "reason": "same name, rules text and system",
                    })
                    report["counts"]["duplicate"] += 1
            primary.mechanics["provenance"] = provenance
            result.append(primary)
    return result, report
