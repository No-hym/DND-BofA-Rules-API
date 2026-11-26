"""Canonical record model shared by all DND-BofA ingest adapters.

The published catalog intentionally keeps the Go ``content.Record`` JSON shape.
Everything specific to a source (original payload, normalized mechanics,
adaptation notes, provenance) lives under ``mechanics`` so the existing Go API,
importer, JSON schema and PostgreSQL projection keep working unchanged.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

CATEGORY_MAP = {
    "CharClass": "class",
    "Race": "species",
    "Monster": "monster",
    "MonsterSpell": "spell-link",
    "Section": "rule",
    "Archetype": "subclass",
    "Subrace": "subspecies",
    "Plane": "plane",
    "SpellList": "spell-list",
    "CharacterClass": "class",
    "Species": "species",
    "Background": "background",
    "Feat": "feat",
    "Spell": "spell",
    "Creature": "monster",
    "MagicItem": "magic-item",
    "Item": "equipment",
    "Weapon": "weapon",
    "Armor": "armor",
    "Rule": "rule",
    "RuleSet": "ruleset",
    "Condition": "condition",
    "Ability": "ability",
    "Skill": "skill",
    "DamageType": "damage-type",
    "CreatureType": "creature-type",
    "Language": "language",
    "Alignment": "alignment",
    "AlignmentDescription": "alignment",
    "ItemCategory": "item-category",
    "ItemRarity": "item-rarity",
    "SpellSchool": "spell-school",
    "Size": "size",
    "Environment": "environment",
    "WeaponProperty": "weapon-property",
    "Service": "service",
    "Image": "image",
    "CrossReference": "cross-reference",
    "ClassFeature": "feature",
    "SpeciesTrait": "trait",
    "FeatBenefit": "benefit",
    "BackgroundBenefit": "benefit",
    "ConditionDescription": "condition",
    "AbilityDescription": "ability",
    "SkillDescription": "skill",
    "DamageTypeDescription": "damage-type",
    "CreatureTypeDescription": "creature-type",
    "AlignmentDescription": "alignment",
    "CreatureAction": "action",
    "CreatureTrait": "trait",
    "CreatureActionAttack": "attack",
    "SpellCastingOption": "spell-option",
    "ClassFeatureItem": "feature-level",
    "WeaponPropertyAssignment": "weapon-property-assignment",
    "ItemSet": "item-set",
    "CreatureSet": "creature-set",
    "Document": "source-document",
}

# Nested models that are folded into their parent entity instead of becoming
# standalone catalog records. Folded data is still preserved verbatim.
CHILD_MODELS = {
    "ClassFeature": ("features", "parent"),
    "ClassFeatureItem": ("levels", "parent"),
    "SpellCastingOption": ("casting_options", "parent"),
    "CreatureAction": ("actions", "parent"),
    "CreatureActionAttack": ("attacks", "parent"),
    "CreatureTrait": ("traits", "parent"),
    "FeatBenefit": ("benefits", "parent"),
    "BackgroundBenefit": ("benefits", "parent"),
    "SpeciesTrait": ("traits", "parent"),
    "ConditionDescription": ("descriptions", "describes"),
    "AbilityDescription": ("descriptions", "describes"),
    "SkillDescription": ("descriptions", "describes"),
    "DamageTypeDescription": ("descriptions", "describes"),
    "CreatureTypeDescription": ("descriptions", "describes"),
    "WeaponPropertyAssignment": ("weapon_properties", "weapon"),
}

SLUG_SAFE = re.compile(r"[^a-z0-9]+")


def slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return SLUG_SAFE.sub("-", value.lower()).strip("-")


def compact(value: Any) -> Any:
    """Drop empty values from upstream payloads without changing real data."""
    if isinstance(value, dict):
        return {k: compact(v) for k, v in value.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        return [compact(v) for v in value]
    return value


def content_hash(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass
class Translation:
    name: str
    description: str = ""
    status: str = "source"
    source_version: str = ""
    glossary_version: str = ""
    updated_at: str = ""
    attribution: str = ""

    def to_json(self) -> dict[str, str]:
        result: dict[str, str] = {"name": self.name, "description": self.description}
        if self.status:
            result["status"] = self.status
        if self.source_version:
            result["source_version"] = self.source_version
        if self.glossary_version:
            result["glossary_version"] = self.glossary_version
        if self.updated_at:
            result["updated_at"] = self.updated_at
        return result


@dataclass
class Entity:
    id: str
    category: str
    edition: str
    publisher_id: str
    book_id: str
    source: str
    license: str
    version: str
    external_id: str
    attribution: str
    name: str
    description: str = ""
    mechanics: dict[str, Any] = field(default_factory=dict)
    translations: dict[str, Translation] = field(default_factory=dict)
    aliases: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if "en" not in self.translations:
            self.translations["en"] = Translation(name=self.name, description=self.description,
                                                    status="source", source_version=self.version)
        self.name = self.translations["en"].name
        self.description = self.translations["en"].description

    def fingerprint(self) -> str:
        return content_hash({
            "name": self.name.lower(),
            "category": self.category,
            "normalized": self.mechanics.get("normalized", {}),
        })

    def to_record(self) -> dict[str, Any]:
        mechanics = dict(self.mechanics)
        if self.aliases:
            mechanics["aliases"] = sorted(self.aliases)
        return {
            "id": self.id,
            "category": self.category,
            "edition": self.edition,
            "publisher_id": self.publisher_id,
            "book_id": self.book_id,
            "source": self.source,
            "license": self.license,
            "version": self.version,
            "external_id": self.external_id,
            "translations": {lang: value.to_json() for lang, value in sorted(self.translations.items())},
            "mechanics": mechanics,
            "attribution": self.attribution,
        }


def from_record(record: dict[str, Any]) -> Entity:
    translations: dict[str, Translation] = {}
    for lang, raw in record.get("translations", {}).items():
        translations[lang] = Translation(
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            status=raw.get("status", "source"),
            source_version=raw.get("source_version", ""),
            glossary_version=raw.get("glossary_version", ""),
            updated_at=raw.get("updated_at", ""),
        )
    mechanics = record.get("mechanics", {})
    en = translations.get("en", Translation(name=record.get("id", "")))
    entity = Entity(
        id=record["id"],
        category=record["category"],
        edition=record["edition"],
        publisher_id=record["publisher_id"],
        book_id=record["book_id"],
        source=record["source"],
        license=record["license"],
        version=record.get("version", ""),
        external_id=record.get("external_id", ""),
        attribution=record.get("attribution", ""),
        name=en.name,
        description=en.description,
        mechanics=mechanics,
        translations=translations,
    )
    entity.aliases.update(mechanics.get("aliases", []))
    return entity
