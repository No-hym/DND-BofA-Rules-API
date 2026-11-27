"""Russian translation memory built from licensed corpora and the legacy catalog.

Only exact-name matches are accepted. English fallback names are never counted
as translations, and text that fails the Cyrillic check is not published as RU.
"""

from __future__ import annotations

import gzip
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .model import Entity, Translation, slug

CYRILLIC = re.compile(r"[\u0400-\u04ff]")
# Corpus headings name SRD subclasses as "<Class> Subclass: <Name>" in English
# and "Подкласс <родит. класса>: <Имя>" in Russian. Catalog entities use the
# bare subclass name, so both forms are indexed as aliases of each other.
SUBCLASS_EN = re.compile(r"^.+?\s+Subclass:?\s+(.+)$", re.I)
SUBCLASS_RU = re.compile(r"^Подкласс\s+[^:]+:\s*(.+)$")
PAREN_EN = re.compile(r"\(([A-Za-z][A-Za-z0-9'’\- ,\.]+)\)\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
EN_SENTENCE = re.compile(r"\b(?:the|and|you|with|that|this|of|in|for|when|from|creature|damage)\b", re.I)


@dataclass
class MemoryEntry:
    name: str
    description: str = ""
    attribution: str = ""
    license: str = ""
    source: str = ""
    status: str = "source"
    edition: str = ""


class TranslationMemory:
    def __init__(self) -> None:
        self.by_key: dict[tuple[str, str, str], list[MemoryEntry]] = defaultdict(list)
        self.names: dict[tuple[str, str], MemoryEntry] = {}
        self.descriptions: dict[tuple[str, str], MemoryEntry] = {}
        self.glossary: dict[str, dict[str, str]] = {"2014": {}, "2024": {}}

    def add(self, edition: str, category: str, name_en: str, entry: MemoryEntry) -> None:
        # Index "<Class> Subclass: <Name>" corpus headings under the bare
        # subclass name as well (skipping "[...]" change-note entries).
        subclass_match = SUBCLASS_EN.match(name_en.strip())
        if subclass_match and "[" not in entry.name:
            ru_match = SUBCLASS_RU.match(entry.name.strip())
            if ru_match:
                self.add(edition, category, subclass_match.group(1).strip(), MemoryEntry(
                    name=ru_match.group(1).strip(), description=entry.description,
                    attribution=entry.attribution, license=entry.license,
                    source=entry.source, status=entry.status, edition=entry.edition))
        name_key = (edition, slug(name_en.lower()))
        if CYRILLIC.search(entry.name):
            key = (edition, category, slug(name_en.lower()))
            marker = (entry.name, entry.source, entry.description[:160])
            if not any((existing.name, existing.source, existing.description[:160]) == marker
                       for existing in self.by_key[key]):
                self.by_key[key].append(entry)
            current = self.names.get(name_key)
            if current is None or len(entry.description) > len(current.description):
                self.names[name_key] = entry
        if CYRILLIC.search(entry.description):
            current = self.descriptions.get(name_key)
            if current is None or len(entry.description) > len(current.description):
                self.descriptions[name_key] = entry

    def _find(self, field: dict[tuple[str, str], MemoryEntry], edition: str, name_en: str) -> MemoryEntry | None:
        key = slug(name_en.lower())
        # Exact edition first, then the other edition: an SRD name translated
        # for 2014 remains the established RU term for 2024 and vice versa.
        for candidate in (edition, "2024", "2014", ""):
            found = field.get((candidate, key))
            if found is not None:
                return found
        return None

    def feature_entry(self, edition: str, level: int | None, feature_name: str) -> MemoryEntry | None:
        """Licensed RU text of a class feature gained at an exact level."""
        if level is None:
            return None
        return self._find(self.descriptions, edition, f"Level {level}: {feature_name}")

    def lookup(self, edition: str, category: str, name_en: str) -> MemoryEntry | None:
        named: MemoryEntry | None = None
        other = "2014" if edition == "2024" else "2024"
        for key in ((edition, category, slug(name_en.lower())),
                    (edition, "", slug(name_en.lower())),
                    (other, category, slug(name_en.lower())),
                    (other, "", slug(name_en.lower())),
                    ("", category, slug(name_en.lower())),
                    ("", "", slug(name_en.lower()))):
            entries = self.by_key.get(key, [])
            if entries:
                named = max(entries, key=lambda item: (bool(item.description), len(item.description)))
                break
        if named is None:
            named = self.names.get((edition, slug(name_en.lower()))) or self.names.get(("", slug(name_en.lower())))
        described = self._find(self.descriptions, edition, name_en)
        if named is None and described is None:
            return None
        if named is None:
            return described
        if described and described.description and (not named.description or len(described.description) > len(named.description)):
            return MemoryEntry(name=named.name, description=described.description,
                               attribution=described.attribution, license=described.license,
                               source=described.source + "+" + named.source, status="source",
                               edition=named.edition or described.edition)
        return named

    def to_json(self) -> dict[str, Any]:
        return {
            "version": 1,
            "entries": {
                f"{edition}|{category}|{name}": [asdict(item) for item in items]
                for (edition, category, name), items in sorted(self.by_key.items())
            },
            "descriptions": {f"{edition}|{name}": asdict(item)
                             for (edition, name), item in sorted(self.descriptions.items())},
            "glossary": self.glossary,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "TranslationMemory":
        memory = cls()
        for key, items in data.get("entries", {}).items():
            edition, category, name = key.split("|", 2)
            seen: set[str] = set()
            for raw in items:
                marker = json.dumps(raw, sort_keys=True, ensure_ascii=False)
                if marker not in seen:
                    seen.add(marker)
                    memory.by_key[(edition, category, name)].append(MemoryEntry(**raw))
        for items in memory.by_key.values():
            for item in items:
                key = (item.edition, slug(item.name.lower()))
                current = memory.names.get(key)
                if current is None or len(item.description) > len(current.description):
                    memory.names[key] = item
        for key, raw in data.get("descriptions", {}).items():
            edition, name = key.split("|", 1)
            memory.descriptions[(edition, name)] = MemoryEntry(**raw)
        memory.glossary = data.get("glossary", {"2014": {}, "2024": {}})
        return memory


def _load_json(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def from_curated_file(path: Path, memory: TranslationMemory) -> int:
    """Load hand/machine-reviewed translations kept in the repository.

    Entries live in ``data/translations/curated.json`` so a catalog rebuild
    never loses them; their status (``machine`` until independently reviewed)
    and attribution are preserved on every record they translate.
    """
    if not path.is_file():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for raw in data.get("entries", []):
        if not raw.get("name_en") or not raw.get("name_ru"):
            continue
        memory.add(raw.get("edition", ""), raw.get("category", ""), raw["name_en"], MemoryEntry(
            name=raw["name_ru"], description=raw.get("description_ru", ""),
            attribution=raw.get("attribution", "DND-BofA curated translation"),
            license=raw.get("license", ""), source=raw.get("source", "dnd-bofa-curated"),
            status=raw.get("status", "machine"), edition=raw.get("edition", "")))
        count += 1
    return count


def from_legacy_catalog(root: Path, memory: TranslationMemory) -> int:
    count = 0
    if not root.is_dir():
        return 0
    paths = sorted(list(root.rglob("*.json")) + list(root.rglob("*.json.gz")))
    for path in paths:
        if path.name.endswith(".schema.json"):
            continue
        if path.name.endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                data = json.load(handle)
        else:
            data = _load_json(path)
        for record in data if isinstance(data, list) else []:
            en = record.get("translations", {}).get("en") or {}
            ru = record.get("translations", {}).get("ru") or {}
            if not ru or not CYRILLIC.search(ru.get("name", "")):
                continue
            entry = MemoryEntry(
                name=ru["name"], description=ru.get("description", ""),
                attribution=record.get("attribution", ""), license="CC-BY-4.0",
                source="dnd-bofa-legacy", status=ru.get("status") or "source",
                edition=record.get("edition", ""),
            )
            memory.add(record.get("edition", ""), record.get("category", ""), en.get("name", ""), entry)
            count += 1
    return count


def _parse_sections(text: str) -> list[tuple[int, str, str]]:
    sections: list[tuple[int, str, str]] = []
    level = 0
    title = ""
    lines: list[str] = []
    for line in text.splitlines():
        match = HEADING.match(line)
        if match:
            if title:
                sections.append((level, title, "\n".join(lines).strip()))
            level, title, lines = len(match.group(1)), match.group(2).strip(), []
        elif title:
            lines.append(line)
    if title:
        sections.append((level, title, "\n".join(lines).strip()))
    return sections


def _clean_heading(title: str) -> tuple[str, str]:
    """Return (ru_name, en_name); en_name is extracted from 'Русский (English)'."""
    match = PAREN_EN.search(title)
    if match:
        return title[:match.start()].strip(), match.group(1).strip()
    return title, ""


def _safe_description(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > 5000:
        cut = text.rfind("\n\n", 0, 5000)
        text = text[:cut if cut > 3000 else 5000].rstrip() + " …"
    if not text or not CYRILLIC.search(text):
        return ""
    # Reject output that is mostly English: never publish a mixed-language description.
    words = re.findall(r"[A-Za-zА-Яа-яЁё]+", text)
    if words:
        english = sum(1 for word in words if word.isascii() and EN_SENTENCE.fullmatch(word))
        if english > 3 and english > len(words) * 0.12:
            return ""
    return text



def from_russian_only_corpus(root: Path, edition: str, source: str, attribution: str,
                             license_name: str, memory: TranslationMemory) -> int:
    """SRD 5.1 RU files keep English names in frontmatter/headings and RU prose."""
    count = 0
    if not root.is_dir():
        return 0
    for path in sorted(root.rglob("*.md")):
        if "/translate/" in path.as_posix() or "/ru/" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        name_match = re.search(r"^name:\s*(.+?)\s*$", text, re.M)
        sections = _parse_sections(text)
        heading = sections[0][1] if sections else ""
        name = name_match.group(1).strip() if name_match else heading
        if not name or not name.isascii() or len(name) > 120:
            continue
        body = sections[0][2] if sections else ""
        if len(sections) > 1:
            body += "\n\n" + "\n\n".join(part[2] for part in sections[1:] if part[2])
        description = _safe_description(body)
        if not description:
            continue
        memory.add(edition, "", name, MemoryEntry(
            name="", description=description, attribution=attribution,
            license=license_name, source=source, edition=edition))
        count += 1
    return count

def from_markdown_corpus(root: Path, edition: str, source: str, attribution: str,
                         license_name: str, memory: TranslationMemory) -> int:
    count = 0
    if not root.is_dir():
        return 0
    for en_dir in sorted(path for path in root.rglob("en")
                         if path.is_dir() and (path.parent / "ru").is_dir() and "dnd" in path.parts):
        for en_path in sorted(en_dir.rglob("*.md")):
            relative = en_path.relative_to(en_dir)
            ru_path = en_dir.parent / "ru" / relative
            if not ru_path.exists():
                continue
            en_text = en_path.read_text(encoding="utf-8", errors="replace")
            ru_text = ru_path.read_text(encoding="utf-8", errors="replace")
            en_sections, ru_sections = _parse_sections(en_text), _parse_sections(ru_text)
            if len(en_sections) == len(ru_sections) and all(a[0] == b[0] for a, b in zip(en_sections, ru_sections)):
                for (_, en_title, _), (_, ru_title, ru_body) in zip(en_sections, ru_sections):
                    ru_name, embedded_en = _clean_heading(ru_title)
                    en_name = embedded_en or en_title
                    if not en_name or en_name == ru_name:
                        continue
                    memory.add(edition, "", en_name, MemoryEntry(
                        name=ru_name, description=_safe_description(ru_body),
                        attribution=attribution, license=license_name, source=source, edition=edition))
                    count += 1
            # Bilingual glossary tables: 'Оригинал (EN)' column gives exact EN names.
            en_rows = [line for line in en_text.splitlines() if line.startswith("|")]
            ru_rows = [line for line in ru_text.splitlines() if line.startswith("|")]
            if "Оригинал (EN)" in ru_text and len(en_rows) == len(ru_rows):
                for en_line, ru_line in zip(en_rows, ru_rows):
                    en_cells = [cell.strip() for cell in en_line.strip("|").split("|")]
                    ru_cells = [cell.strip() for cell in ru_line.strip("|").split("|")]
                    if len(ru_cells) < 3 or len(en_cells) < 2:
                        continue
                    ru_name, en_name = ru_cells[0], ru_cells[1]
                    if not en_name or not CYRILLIC.search(ru_name):
                        continue
                    memory.add(edition, "", en_name, MemoryEntry(
                        name=ru_name, description="", attribution=attribution,
                        license=license_name, source=source, edition=edition))
                    memory.glossary.setdefault(edition, {}).setdefault(en_name.lower(), ru_name)
                    count += 1
    return count


def apply(memory: TranslationMemory, entity: Entity, glossary_version: str) -> bool:
    """Attach a RU translation when an exact licensed match exists."""
    entry = memory.lookup(entity.edition, entity.category, entity.name)
    if not entry:
        return False
    description = entry.description
    assembled_features = 0
    complete_curated = False
    if entity.category == "subclass" and entity.description:
        # A curated entry may hold a complete translation of a long full-text
        # record (e.g. an Open5e v1 archetype) next to a short intro entry for
        # its v2 variant. Pick the shortest curated text that is still a
        # complete translation of *this* record, so the short intro keeps
        # serving the v2 variant and the full text serves the v1 record.
        other = "2014" if entity.edition == "2024" else "2024"
        name_slug = slug(entity.name.lower())
        candidates = [
            candidate
            for key in ((entity.edition, entity.category, name_slug),
                        (entity.edition, "", name_slug),
                        (other, entity.category, name_slug),
                        (other, "", name_slug),
                        ("", entity.category, name_slug),
                        ("", "", name_slug))
            for candidate in memory.by_key.get(key, [])
            if candidate.source == "dnd-bofa-curated" and candidate.description
        ]
        complete = [candidate for candidate in candidates
                    if len(candidate.description) >= 0.4 * len(entity.description)]
        if complete:
            entry = min(complete, key=lambda candidate: len(candidate.description))
            description = entry.description
            complete_curated = len(description) >= 0.4 * len(entity.description)
    if entity.category == "subclass" and not complete_curated:
        # The subclass description in the corpora is the intro section only;
        # the feature texts live in separate "Level N: <Feature>" sections.
        # Assemble the complete RU subclass text from those licensed sections,
        # matched by the exact level at which the feature is gained.
        parts = [description] if description else []
        features = entity.mechanics.get("subentities", {}).get("features", [])
        for feature in sorted(features, key=lambda item: (item.get("level") or 0, str(item.get("name", "")))):
            feature_text = memory.feature_entry(entity.edition, feature.get("level"),
                                                str(feature.get("name", "")))
            if feature_text and feature_text.description:
                parts.append(f"### {feature_text.name}\n\n{feature_text.description}")
                assembled_features += 1
        if assembled_features:
            description = "\n\n".join(parts)
        elif description and len(description) < 0.4 * len(entity.description):
            # A short intro must not masquerade as the translation of a long
            # full-text subclass record (e.g. an Open5e v1 archetype whose
            # feature texts are not available as licensed RU sections).
            return False
    # Prefer the upstream EN description when the corpus section is only a
    # heading/table, but never invent text: an empty RU description is explicit.
    entity.translations["ru"] = Translation(
        name=entry.name,
        description=description,
        status=entry.status if entry.status in ("source", "machine", "reviewed") else "source",
        source_version=entity.version,
        glossary_version=glossary_version,
    )
    entity.mechanics["translation_provenance"] = {
        "source": entry.source,
        "license": entry.license,
        "attribution": entry.attribution,
        "edition": entry.edition,
        "exact_match": entity.name,
        **({"assembled_features": assembled_features} if assembled_features else {}),
    }
    entity.attribution += f"; RU translation: {entry.attribution} ({entry.license})"
    return True
