"""Adapters for the Open5e v1/v2 fixture snapshots and the paginated v2 API."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .model import (CATEGORY_MAP, CHILD_MODELS, Entity, Translation, compact,
                    content_hash, slug)

V1_SUPPLEMENTAL = {
    "Archetype": "subclass",
    "Subrace": "subspecies",
    "Plane": "plane",
    "Section": "rule",
    "SpellList": "spell-list",
}
V2_META_MODELS = {"document", "license", "gamesystem", "publisher"}
CATEGORY_MAP_LOWER = {key.lower(): value for key, value in CATEGORY_MAP.items()}
CHILD_MODELS_LOWER = {key.lower(): value for key, value in CHILD_MODELS.items()}

NORMALIZE_KEYS: dict[str, tuple[str, ...]] = {
    "spell": ("level", "school", "ritual", "casting_time", "verbal", "somatic", "material",
              "material_specified", "material_cost", "material_consumed", "range", "range_unit",
              "range_text", "duration", "concentration", "target_type", "target_count",
              "shape_type", "shape_size", "shape_size_unit", "attack_roll", "saving_throw_ability",
              "damage_roll", "damage_types", "classes"),
    "monster": ("size", "category", "alignment", "challenge_rating", "armor_class", "armor_detail",
                "hit_points", "hit_dice", "initiative_bonus", "proficiency_bonus", "passive_perception",
                "speed", "walk", "fly", "swim", "climb", "burrow", "normal_sight_range",
                "darkvision_range", "blindsight_range", "languages", "languages_desc",
                "damage_vulnerabilities", "damage_resistances", "damage_immunities",
                "condition_immunities", "environments", "skill_bonus_acrobatics",
                "saving_throw_strength", "saving_throw_dexterity", "saving_throw_constitution",
                "saving_throw_intelligence", "saving_throw_wisdom", "saving_throw_charisma",
                "ability_score_strength", "ability_score_dexterity", "ability_score_constitution",
                "ability_score_intelligence", "ability_score_wisdom", "ability_score_charisma"),
    "class": ("hit_dice", "primary_abilities", "saving_throws", "caster_type", "subclass_of"),
    "subclass": ("subclass_of", "caster_type"),
    "species": ("subspecies_of",),
    "subspecies": ("subspecies_of",),
    "magic-item": ("category", "rarity", "requires_attunement", "cost", "weight", "size"),
    "equipment": ("category", "cost", "weight", "size", "weapon", "armor", "damage_immunities",
                  "damage_resistances", "damage_vulnerabilities"),
    "weapon": ("damage_dice", "damage_type", "range", "long_range", "is_simple", "is_improvised",
               "distance_unit"),
    "armor": ("ac_base", "ac_add_dexmod", "ac_cap_dexmod", "grants_stealth_disadvantage",
              "strength_score_required"),
    "feat": ("type", "prerequisite"),
    "trait": ("type", "order"),
    "benefit": ("type",),
    "action": ("action_type", "order_in_statblock", "legendary_action_cost", "uses_type",
               "uses_param", "limited_to_form"),
    "attack": ("attack_type", "to_hit_mod", "reach", "range", "long_range", "damage_die_count",
               "damage_die_type", "damage_bonus", "damage_type", "extra_damage_die_count",
               "extra_damage_die_type", "extra_damage_bonus", "extra_damage_type"),
    "rule": ("index", "initialHeaderLevel", "ruleset"),
    "spell-list": ("spells",),
}

REQUIREMENT_KEYS = ("prerequisite", "requires_attunement", "strength_score_required", "minimum_level")
LIMITATION_KEYS = ("concentration", "ritual", "legendary_action_cost", "uses_param", "uses_type",
                   "limited_to_form", "grants_stealth_disadvantage")


def iter_fixture_files(root: Path, version: str) -> Iterable[tuple[str, Path]]:
    directory = root / ("v2" if version == "v2" else "v1")
    if not directory.is_dir():
        return
    pattern = "*/*/*.json" if version == "v2" else "*/*.json"
    for path in sorted(directory.glob(pattern)):
        yield path.parent.name, path


def load_fixtures(root: Path, version: str = "v2") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for book, path in iter_fixture_files(root, version):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, list):
            continue
        for row in data:
            if isinstance(row, dict) and "model" in row and "fields" in row:
                item = dict(row)
                item["_book_dir"] = book
                item["_file"] = path.name
                rows.append(item)
    return rows


class Open5eAdapter:
    """Normalizes Open5e fixtures into source-agnostic catalog entities."""

    def __init__(self, config: dict[str, Any], snapshot: Path | None) -> None:
        self.config = config
        self.snapshot = snapshot
        self.license_map = config["license_map"]
        self.edition_map = config["editions"]
        self.documents: dict[str, dict[str, Any]] = {}
        self.doc_aliases: dict[str, str] = {}
        self.publishers: dict[str, dict[str, Any]] = {}
        self.stats = defaultdict(int)
        self.skipped: list[dict[str, str]] = []

    def _skip(self, reason: str, source: str, name: str) -> None:
        self.skipped.append({"source": source, "name": str(name), "reason": reason})
        self.stats["skipped"] += 1

    def _load_metadata(self, rows: list[dict[str, Any]], version: str) -> None:
        for row in rows:
            model = row["model"].rsplit(".", 1)[-1].lower()
            fields = row["fields"] or {}
            if model == "document":
                key = str(fields.get("slug") or row["pk"]) if version == "v1" else str(row["pk"])
                if version == "v1":
                    self.doc_aliases[str(row["pk"])] = key
                licenses = fields.get("licenses") or ([fields["license"]] if fields.get("license") else [])
                mapped = [self.license_map.get(str(lic).lower(), "") for lic in licenses]
                self.documents[key] = {
                    "key": key,
                    "title": fields.get("name") or fields.get("title") or key,
                    "display_name": fields.get("display_name") or "",
                    "author": fields.get("author") or "",
                    "copyright": fields.get("copyright") or "",
                    "permalink": fields.get("permalink") or fields.get("url") or "",
                    "publisher": fields.get("publisher") or row.get("_book_dir", ""),
                    "organization": fields.get("organization") or "",
                    "gamesystem": fields.get("gamesystem", ""),
                    "licenses": [lic for lic in mapped if lic],
                    "raw_license": licenses,
                    "version": fields.get("version") or "",
                    "publication_date": fields.get("publication_date") or "",
                    "desc": fields.get("desc") or "",
                    "version_tag": version,
                }
            elif model == "publisher":
                self.publishers[str(row["pk"])] = fields

    def _license(self, document: dict[str, Any] | None) -> tuple[str, str]:
        if not document:
            return "", ""
        licenses = document["licenses"]
        if not licenses:
            return "", ""
        # Prefer an explicit Creative Commons license over OGL where both apply.
        chosen = next((lic for lic in licenses if lic.startswith("CC")), licenses[0])
        urls = {
            "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/legalcode",
            "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/legalcode",
            "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
            "OGL-1.0a": "https://open5e.com/legal",
            "ORC-1.0": "https://a5esrd.com/a5esrd",
        }
        return chosen, urls.get(chosen, "")

    def _attribution(self, document: dict[str, Any] | None, license_name: str, license_url: str) -> str:
        if not document:
            return "Upstream: Open5e (https://api.open5e.com/); license: " + license_name
        author = document.get("author") or document.get("organization") or "Various authors"
        publisher = self.publishers.get(document.get("publisher", ""), {}).get("name") or document.get("publisher", "")
        parts = [
            f"Title: {document['title']}",
            f"Author: {author}",
            f"Publisher: {publisher}",
            f"Source: {document.get('permalink') or 'https://api.open5e.com/'}",
            f"License: {license_name}" + (f" ({license_url})" if license_url else ""),
        ]
        if document.get("copyright"):
            parts.append(document["copyright"])
        return "; ".join(parts)

    def _make_entity(self, row: dict[str, Any], category: str, version: str,
                     document_key: str | None = None) -> Entity | None:
        fields = row["fields"] or {}
        name = str(fields.get("name") or "").strip()
        if not name and fields.get("describes"):
            name = str(fields["describes"]).replace("-", " ").title()
        if not name:
            self._skip("missing name", f"open5e:{version}", str(row.get("pk")))
            return None
        doc_key = document_key or fields.get("document") or row.get("_book_dir")
        doc_key = self.doc_aliases.get(str(doc_key), str(doc_key))
        document = self.documents.get(str(doc_key))
        if not document:
            self._skip("unknown document", f"open5e:{version}", name)
            return None
        license_name, license_url = self._license(document)
        if not license_name:
            self._skip("license not declared by source", document["title"], name)
            return None
        system = document.get("gamesystem") or ("a5e" if str(doc_key).startswith("a5e") else "5e-2014")
        if system not in self.edition_map:
            self._skip(f"unsupported game system {system}", document["title"], name)
            return None
        edition = self.edition_map[system]
        pk = str(row["pk"])
        book_id = str(doc_key)
        external_id = slug(pk)
        model_slug = slug(row["model"].rsplit(".", 1)[-1])
        entity_id = f"o5e:{book_id}:{model_slug}:{external_id}"
        source = f"open5e:{version}:{book_id}"
        description = str(fields.get("desc") or fields.get("description") or "").strip()
        attribution = self._attribution(document, license_name, license_url)
        normalized = {key: compact(fields[key]) for key in NORMALIZE_KEYS.get(category, ()) if key in fields}
        mechanics: dict[str, Any] = {
            "source_data": compact(fields),
            "normalized": normalized,
            "original_system": system,
            "compatibility": {
                "editions": [edition, "2024"] if system == "5e-2014" else [edition],
                "systems": [system],
                "adapted": system != "5e-2024",
                "primary_edition": "2024",
                "adapted_for_primary": system != "5e-2024",
                "notes": (
                    "Original 5e 2014 mechanics preserved in source_data; usable with the 2024 "
                    "primary edition subject to the rules difference notes."
                    if system == "5e-2014" else
                    "Advanced 5e material kept with its original mechanics; mapped to the closest "
                    "primary edition for catalog filtering."
                ),
            },
            "content_hash": content_hash(compact(fields)),
            "source_document": {k: document[k] for k in ("key", "title", "author", "publisher",
                                                         "permalink", "publication_date", "licenses")},
            "license_url": license_url,
            "requirements": [],
            "limitations": [],
            "choices": [],
            "relations": [],
            "resources": [],
            "formulas": [],
            "subentities": defaultdict(list),
        }
        for key in REQUIREMENT_KEYS:
            if key in fields and fields[key] not in (None, "", False, []):
                mechanics["requirements"].append({"type": key, "value": compact(fields[key])})
        for key in LIMITATION_KEYS:
            if key in fields and fields[key] not in (None, "", False, []):
                mechanics["limitations"].append({"type": key, "value": compact(fields[key])})
        for key in ("classes", "parent", "subclass_of", "subspecies_of", "ruleset", "documents"):
            if key in fields and fields[key] not in (None, "", []):
                value = compact(fields[key])
                mechanics["relations"].append({
                    "type": key,
                    "target_id": value[0] if isinstance(value, list) and value else str(value),
                    "required": False,
                    "value": value,
                })
        for key in ("damage_roll", "hit_dice", "cost", "weight", "range", "long_range"):
            if isinstance(fields.get(key), str) and any(c.isdigit() for c in fields[key]):
                mechanics["formulas"].append({"type": key, "expression": fields[key]})
        return Entity(
            id=entity_id, category=category, edition=edition, publisher_id=str(document.get("publisher") or "unknown"),
            book_id=book_id, source=source, license=license_name,
            version=document.get("version") or str(row.get("_sha", "snapshot")), external_id=pk,
            attribution=attribution, name=name, description=description, mechanics=mechanics,
            translations={"en": Translation(name=name, description=description, status="source",
                                            source_version=document.get("version") or "snapshot")},
        )

    def build(self, version: str = "v2") -> list[Entity]:
        if not self.snapshot or not self.snapshot.is_dir():
            return []
        rows = load_fixtures(self.snapshot, version)
        self._load_metadata(rows, version)
        primary: dict[tuple[str, str], Entity] = {}
        by_pk: dict[tuple[str, str], tuple[Entity, dict[str, Any]]] = {}
        children: list[tuple[dict[str, Any], str, str]] = []

        # ClassFeatureItem rows carry the level at which a class/subclass
        # feature is gained. They are consumed here to annotate the folded
        # feature payloads instead of being reported as orphan children.
        feature_levels: dict[str, int] = {}
        for row in rows:
            if row["model"].rsplit(".", 1)[-1].lower() != "classfeatureitem":
                continue
            fields = row["fields"] or {}
            parent_pk, level = str(fields.get("parent") or ""), fields.get("level")
            if parent_pk and isinstance(level, int):
                feature_levels[parent_pk] = min(level, feature_levels.get(parent_pk, level))

        for row in rows:
            model = row["model"].rsplit(".", 1)[-1]
            model_key = model.lower()
            if model_key in V2_META_MODELS or model_key in ("license", "gamesystem", "publisher"):
                continue
            if model_key in ("crossreference", "monsterspell", "classfeatureitem"):
                continue  # folded into relations/feature levels
            category = CATEGORY_MAP_LOWER.get(model_key)
            if not category:
                self._skip(f"unmapped model {model}", f"open5e:{version}", str(row.get("pk")))
                continue
            if category == "source-document":
                continue
            # Open5e v2 models subclasses as CharacterClass rows whose
            # `subclass_of` points at the parent class, and subspecies as
            # Species rows with `subspecies_of`. Publish them under their real
            # categories so clients can query subclasses directly.
            row_fields = row["fields"] or {}
            if model_key == "characterclass" and row_fields.get("subclass_of"):
                category = "subclass"
            elif model_key == "species" and row_fields.get("subspecies_of"):
                category = "subspecies"
            if model_key in CHILD_MODELS_LOWER:
                children.append((row, model, category))
                continue
            entity = self._make_entity(row, category, version)
            if entity is None:
                continue
            key = (model, str(row["pk"]))
            primary[key] = entity
            by_pk[key] = (entity, row["fields"] or {})
            self.stats["imported"] += 1

        # Children are attached to their parents; nested payloads stay intact.
        allowed_parents = {"characterclass", "species", "spell", "creature", "feat",
                           "background", "classfeature", "creatureaction"}
        pk_index: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for model_name, pk in by_pk:
            if model_name.lower() in allowed_parents:
                pk_index[pk].append((model_name, pk))
        for row, model, category in children:
            fields = row["fields"] or {}
            target_field = CHILD_MODELS_LOWER[model.lower()][1]
            parent_value = fields.get(target_field)
            parent_key = None
            if parent_value is not None:
                candidates = pk_index.get(str(parent_value), [])
                if candidates:
                    parent_key = candidates[0]
                elif target_field == "describes":
                    suffix = "-" + str(parent_value)
                    for key, options in pk_index.items():
                        if key == str(parent_value) or key.endswith(suffix):
                            parent_key = options[0]
                            break
            if parent_key is None:
                # Orphan child: keep it as a standalone entity with a relation.
                if not fields.get("name") and not fields.get("describes"):
                    self._skip("orphan nested object without a parent or name", f"open5e:{version}", str(row.get("pk")))
                    continue
                entity = self._make_entity(row, category, version,
                                           document_key=fields.get("document") or row.get("_book_dir"))
                if entity:
                    primary[(model, str(row["pk"]))] = entity
                    by_pk[(model, str(row["pk"]))] = (entity, fields)
                    self.stats["imported"] += 1
                continue
            parent, _ = by_pk[parent_key]
            bucket, _ = CHILD_MODELS_LOWER[model.lower()]
            payload = {"external_id": str(row["pk"]), **compact(fields)}
            if bucket == "features" and str(row["pk"]) in feature_levels:
                payload["level"] = feature_levels[str(row["pk"])]
            parent.mechanics["subentities"][bucket].append(payload)
            self.stats["folded"] += 1

        for entity in primary.values():
            subentities = entity.mechanics["subentities"]
            if subentities.get("features"):
                subentities["features"].sort(
                    key=lambda item: (item.get("level") is None, item.get("level") or 0,
                                      str(item.get("name", ""))))
            entity.mechanics["subentities"] = dict(subentities)

        # Cross references become typed relations on the source entity.
        for row in rows:
            model_key = row["model"].rsplit(".", 1)[-1].lower()
            if model_key == "monsterspell":
                fields = row["fields"] or {}
                monster_pk = str(fields.get("monster") or "")
                spell_pk = str(fields.get("spell") or "")
                for (model_name, pk), (entity, _) in by_pk.items():
                    if pk == monster_pk and model_name.lower() == "creature":
                        entity.mechanics["relations"].append({
                            "type": "knows_spell", "target_id": spell_pk, "required": False,
                        })
                        break
                continue
            if model_key != "crossreference":
                continue
            fields = row["fields"] or {}
            source_key = str(fields.get("source_object_key") or "")
            target_key = str(fields.get("reference_object_key") or "")
            for (model, pk), (entity, _) in by_pk.items():
                if pk == source_key:
                    entity.mechanics["relations"].append({
                        "type": "cross-reference", "target_id": target_key,
                        "anchor": fields.get("anchor", ""), "required": False,
                    })
                    break
        return list(primary.values())
