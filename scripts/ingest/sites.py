"""Website adapters.

5esrd and A5ESRD do not ship a machine-readable content dump. Their adapters
ingest the published section/PDF indexes as reference entities, attach those
references to matching Open5e records, and rely on the structured Open5e
snapshots for full mechanics. Sites are never contacted by the runtime API.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

from .model import Entity, Translation, slug

ANCHOR = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.current = ""
        self.href = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.current = ""
            self.href = dict(attrs).get("href") or ""

    def handle_data(self, data: str) -> None:
        if self.href:
            self.current += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.href:
            self.links.append((self.current.strip(), self.href))
            self.current, self.href = "", ""


def _reference_entity(source_id: str, title: str, url: str, section: str,
                      license_name: str, attribution: str, edition: str = "2014") -> Entity:
    key = slug(url)
    return Entity(
        id=f"{source_id}:reference:{key}",
        category="reference",
        edition=edition,
        publisher_id="open-gaming-network" if source_id == "5esrd" else "en-publishing",
        book_id=source_id,
        source=source_id,
        license=license_name,
        version="site-index",
        external_id=key,
        attribution=attribution,
        name=title,
        description="",
        mechanics={
            "source_data": {"title": title, "url": url, "section": section},
            "normalized": {"url": url, "section": section},
            "original_system": "a5e" if source_id == "a5esrd" else "5e-2014",
            "compatibility": {"editions": [edition], "systems": ["a5e" if source_id == "a5esrd" else "5e-2014"],
                              "adapted": True, "notes": "External section index; no full text is copied."},
            "requirements": [], "limitations": [], "choices": [], "relations": [],
            "resources": [], "formulas": [], "subentities": {},
        },
        translations={"en": Translation(name=title, description="", status="source", source_version="site-index")},
    )


def site_5esrd(config: dict[str, Any], root: Path) -> list[Entity]:
    attribution = config["license"] + "; " + config["url"] + "; " + config["license_url"]
    index_path = root.parent / "sources" / "5esrd-index.json"
    items: list[dict[str, str]] = []
    if index_path.exists():
        items.extend(json.loads(index_path.read_text(encoding="utf-8")).get("sections", []))
    html_dir = root / "5esrd"
    if html_dir.is_dir():
        for path in sorted(html_dir.glob("*.html")):
            parser = _Links()
            parser.feed(path.read_text(encoding="utf-8", errors="replace"))
            for title, url in parser.links:
                if "5esrd.com" in url and title:
                    items.append({"title": title, "url": url, "section": path.stem})
    seen: set[str] = set()
    result: list[Entity] = []
    for item in items:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        result.append(_reference_entity("5esrd", item["title"], item["url"],
                                        item.get("section", ""), config["license"], attribution))
    return result


def site_a5esrd(config: dict[str, Any], root: Path) -> list[Entity]:
    attribution = config["attribution"]
    index_path = root.parent / "sources" / "a5esrd-index.json"
    items: list[dict[str, str]] = []
    if index_path.exists():
        items.extend(json.loads(index_path.read_text(encoding="utf-8")).get("sections", []))
    html_dir = root / "a5esrd"
    if html_dir.is_dir():
        for path in sorted(html_dir.glob("*.html")):
            parser = _Links()
            parser.feed(path.read_text(encoding="utf-8", errors="replace"))
            for title, url in parser.links:
                if url.endswith((".pdf", ".zip")):
                    items.append({"title": title or slug(url), "url": url, "section": path.stem})
    seen: set[str] = set()
    result: list[Entity] = []
    for item in items:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        result.append(_reference_entity("a5esrd", item["title"], item["url"],
                                        item.get("section", ""), "CC-BY-4.0", attribution))
    return result


def attach_references(entities: list[Entity], references: Iterable[Entity]) -> int:
    """Attach source-site links by exact normalized name; never guess a match."""
    by_name: dict[tuple[str, str], list[str]] = {}
    for reference in references:
        info = reference.mechanics["source_data"]
        by_name.setdefault((reference.category, slug(info["title"].lower())), []).append(info["url"])
    attached = 0
    for entity in entities:
        urls = by_name.get((entity.category, slug(entity.name.lower())), [])
        if urls:
            entity.mechanics.setdefault("external_references", []).extend(
                {"source": reference.source, "url": url} for reference in references
                for url in urls if reference.mechanics["source_data"]["title"].lower() == entity.name.lower()
            )
            attached += 1
    return attached
