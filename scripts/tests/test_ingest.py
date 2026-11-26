import json
import tempfile
import unittest
from pathlib import Path

from scripts.ingest.dedupe import deduplicate
from scripts.ingest.model import Entity, Translation
from scripts.ingest.open5e import Open5eAdapter
from scripts.ingest.pipeline import load_config
from scripts.ingest.translations import MemoryEntry, TranslationMemory, apply
from scripts.ingest.validate import validate_dirs

ROOT = Path(__file__).resolve().parents[2]


def entity(identifier: str, name: str, category: str = "spell", edition: str = "2024",
           normalized: dict | None = None) -> Entity:
    return Entity(
        id=identifier, category=category, edition=edition, publisher_id="wizards-of-the-coast",
        book_id="srd-2024", source="open5e:v2:srd-2024", license="CC-BY-4.0", version="5.2",
        external_id=identifier, attribution="TASL", name=name, description="English text",
        mechanics={"normalized": normalized or {"level": 1}, "source_data": {"name": name},
                   "compatibility": {"adapted": False}},
        translations={"en": Translation(name=name, description="English text")},
    )


class Open5eAdapterTests(unittest.TestCase):
    def test_fixture_normalization_keeps_license_and_mechanics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc_dir = root / "data" / "v2" / "wizards-of-the-coast" / "srd-test"
            doc_dir.mkdir(parents=True)
            (doc_dir / "Document.json").write_text(json.dumps([{
                "model": "api_v2.document", "pk": "srd-test",
                "fields": {"name": "Test SRD", "author": "Wizards of the Coast",
                           "publisher": "wizards-of-the-coast", "gamesystem": "5e-2024",
                           "licenses": ["cc-by-40"], "permalink": "https://example.invalid/srd"},
            }]), encoding="utf-8")
            (doc_dir / "Spell.json").write_text(json.dumps([{
                "model": "api_v2.spell", "pk": "srd-test_fire",
                "fields": {"name": "Fire", "document": "srd-test", "desc": "Deal damage.",
                           "level": 1, "school": "evocation", "verbal": True,
                           "damage_roll": "1d6", "damage_types": ["fire"],
                           "casting_time": "action"},
            }]), encoding="utf-8")
            adapter = Open5eAdapter(load_config(), root / "data")
            records = adapter.build("v2")
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record.license, "CC-BY-4.0")
            self.assertEqual(record.edition, "2024")
            self.assertEqual(record.mechanics["normalized"]["damage_roll"], "1d6")
            self.assertIn("Wizards of the Coast", record.attribution)
            self.assertEqual(record.translations["en"].description, "Deal damage.")

    def test_unlicensed_document_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc_dir = root / "data" / "v2" / "unknown" / "book"
            doc_dir.mkdir(parents=True)
            (doc_dir / "Document.json").write_text(json.dumps([{
                "model": "api_v2.document", "pk": "book",
                "fields": {"name": "Closed", "gamesystem": "5e-2024", "publisher": "unknown", "licenses": []},
            }]), encoding="utf-8")
            (doc_dir / "Spell.json").write_text(json.dumps([{
                "model": "api_v2.spell", "pk": "book_x",
                "fields": {"name": "X", "document": "book"},
            }]), encoding="utf-8")
            adapter = Open5eAdapter(load_config(), root / "data")
            self.assertEqual(adapter.build("v2"), [])
            self.assertTrue(any("license" in item["reason"] for item in adapter.skipped))


class TranslationTests(unittest.TestCase):
    def test_exact_match_and_english_fallback_rejection(self) -> None:
        memory = TranslationMemory()
        memory.add("2024", "spell", "Fireball", MemoryEntry(name="Огненный шар", description="Огненный шар поражает цель."))
        memory.add("2024", "spell", "No Name", MemoryEntry(name="No Name", description="English only"))
        item = entity("spell:fireball", "Fireball")
        self.assertTrue(apply(memory, item, "v1"))
        self.assertEqual(item.translations["ru"].name, "Огненный шар")
        other = entity("spell:none", "No Name")
        self.assertFalse(apply(memory, other, "v1"))
        self.assertNotIn("ru", other.translations)

    def test_description_from_second_corpus_is_merged(self) -> None:
        memory = TranslationMemory()
        memory.add("2024", "", "Fireball", MemoryEntry(name="Шар огня", attribution="A", source="A"))
        memory.add("2024", "", "Fireball", MemoryEntry(name="", description="Описание на русском.", attribution="B", source="B"))
        item = entity("spell:fireball", "Fireball")
        self.assertTrue(apply(memory, item, "v1"))
        self.assertEqual(item.translations["ru"].name, "Шар огня")
        self.assertEqual(item.translations["ru"].description, "Описание на русском.")
        self.assertEqual({"A", "B"}, set(item.mechanics["translation_provenance"]["source"].split("+")))


class DedupeTests(unittest.TestCase):
    def test_identical_records_are_merged_and_variants_kept(self) -> None:
        first = entity("a", "Fireball")
        same = entity("b", "Fireball")
        different = entity("c", "Fireball", normalized={"level": 9})
        different.description = "A different, much larger explosion."
        different.translations["en"].description = different.description
        kept, report = deduplicate([first, same, different])
        self.assertEqual(len(kept), 2)
        self.assertEqual(report["counts"]["duplicate"], 1)
        self.assertEqual(report["counts"]["variant"], 1)
        self.assertTrue(any("variant" in item["kept"] for item in report["variants"]))


class ValidationTests(unittest.TestCase):
    def test_validator_rejects_duplicate_ids_and_untranslated_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = entity("a", "Fireball").to_record()
            record["translations"]["ru"] = {"name": "Fireball", "description": ""}
            (root / "catalog" / "2024").mkdir(parents=True)
            (root / "catalog" / "2024" / "spell.json").write_text(json.dumps([record, record]), encoding="utf-8")
            problems = validate_dirs(root)
            self.assertTrue(any("duplicate id" in problem for problem in problems))
            self.assertTrue(any("RU name is not translated" in problem for problem in problems))


class ManifestTests(unittest.TestCase):
    def test_every_source_declares_license_or_registry(self) -> None:
        config = load_config()
        for source in config["sources"]:
            self.assertTrue(source.get("license") or source.get("content_license_registry"), source["id"])
            self.assertTrue(source.get("role"), source["id"])

    def test_runtime_handler_does_not_call_external_services(self) -> None:
        handler = (ROOT / "internal" / "api" / "handler.go").read_text(encoding="utf-8")
        self.assertNotIn("http.Get", handler)
        self.assertNotIn("api.open5e.com", handler)


if __name__ == "__main__":
    unittest.main()
