import json
import tempfile
import unittest
from pathlib import Path

from scripts.ingest.cards import read_records, write_cards, write_catalog_cards
from scripts.ingest.dedupe import deduplicate
from scripts.ingest.derived import apply_derived
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


class CardLayoutTests(unittest.TestCase):
    def test_one_file_per_record_and_backwards_compatible_reads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "catalog" / "2024" / "weapon"
            legacy = directory.with_suffix(".json")
            legacy.parent.mkdir(parents=True)
            legacy.write_text("[]", encoding="utf-8")
            records = [
                {"id": "srd-2024:weapon:longsword", "category": "weapon"},
                {"id": "srd-2024:weapon:shortsword", "category": "weapon"},
            ]
            self.assertEqual(write_cards(directory, records), 2)
            # A single weapon is a single self-contained card file.
            card = json.loads((directory / "longsword.json").read_text(encoding="utf-8"))
            self.assertEqual(card["id"], "srd-2024:weapon:longsword")
            self.assertFalse(legacy.exists())
            self.assertEqual(
                [record["id"] for record in read_records(directory)],
                ["srd-2024:weapon:longsword", "srd-2024:weapon:shortsword"],
            )
            # Rebuilding without a record removes its stale card.
            write_cards(directory, records[:1])
            self.assertFalse((directory / "shortsword.json").exists())
            # Legacy aggregated arrays are still readable.
            aggregated = root / "legacy.json"
            aggregated.write_text(json.dumps(records), encoding="utf-8")
            self.assertEqual(len(read_records(aggregated)), 2)

    def test_catalog_cards_group_by_book_and_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            edition_dir = Path(tmp) / "catalog" / "2024"
            # A stale flat card from the previous layout must be pruned.
            stale = edition_dir / "weapon" / "old-card.json"
            stale.parent.mkdir(parents=True)
            stale.write_text("{}", encoding="utf-8")
            records = [
                {"id": "srd-2024:weapon:longsword", "book_id": "srd-2024", "category": "weapon"},
                {"id": "srd-2024:spell:fireball", "book_id": "srd-2024", "category": "spell"},
                {"id": "toh:spell:some-spell", "book_id": "toh", "category": "spell"},
            ]
            self.assertEqual(write_catalog_cards(edition_dir, records), 3)
            self.assertTrue((edition_dir / "srd-2024" / "weapon" / "longsword.json").exists())
            self.assertTrue((edition_dir / "srd-2024" / "spell" / "fireball.json").exists())
            self.assertTrue((edition_dir / "toh" / "spell" / "some-spell.json").exists())
            self.assertFalse(stale.exists())
            self.assertFalse((edition_dir / "weapon").exists())
            self.assertEqual(len(read_records(edition_dir)), 3)


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


class SubclassTests(unittest.TestCase):
    def test_v2_subclass_of_rows_become_subclass_category(self) -> None:
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
            (doc_dir / "CharacterClass.json").write_text(json.dumps([
                {"model": "api_v2.characterclass", "pk": "srd-test_fighter",
                 "fields": {"name": "Fighter", "document": "srd-test", "hit_dice": "1d10"}},
                {"model": "api_v2.characterclass", "pk": "srd-test_champion",
                 "fields": {"name": "Champion", "document": "srd-test",
                            "subclass_of": "srd-test_fighter", "desc": "Intro."}},
            ]), encoding="utf-8")
            adapter = Open5eAdapter(load_config(), root / "data")
            records = {record.name: record for record in adapter.build("v2")}
            self.assertEqual(records["Fighter"].category, "class")
            self.assertEqual(records["Champion"].category, "subclass")
            relations = records["Champion"].mechanics["relations"]
            self.assertTrue(any(item["type"] == "subclass_of"
                                and item["target_id"] == "srd-test_fighter" for item in relations))

    def test_subclass_alias_and_cross_edition_lookup(self) -> None:
        memory = TranslationMemory()
        memory.add("2024", "", "Fighter Subclass: Champion",
                   MemoryEntry(name="Подкласс воина: Чемпион",
                               description="Архетипичный Чемпион сосредоточен на физической мощи."))
        found = memory.lookup("2014", "subclass", "Champion")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Чемпион")

    def test_complete_curated_subclass_translation_is_published(self) -> None:
        memory = TranslationMemory()
        memory.add("2014", "subclass", "Ancient Dragons",
                   MemoryEntry(name="Древние драконы", description="Короткое вступление.",
                               source="dnd-bofa-curated", status="machine"))
        memory.add("2014", "subclass", "Ancient Dragons",
                   MemoryEntry(name="Древние драконы",
                               description="Полный перевод текста подкласса. " * 200,
                               source="dnd-bofa-curated", status="machine"))
        long_item = entity("subclass:dragons-v1", "Ancient Dragons", category="subclass", edition="2014")
        long_item.description = "Full text. " * 500
        long_item.translations["en"].description = long_item.description
        self.assertTrue(apply(memory, long_item, "v1"))
        self.assertTrue(long_item.translations["ru"].description.startswith("Полный перевод"))
        short_item = entity("subclass:dragons-v2", "Ancient Dragons", category="subclass", edition="2014")
        short_item.description = "Intro."
        short_item.translations["en"].description = short_item.description
        self.assertTrue(apply(memory, short_item, "v1"))
        self.assertEqual(short_item.translations["ru"].description, "Короткое вступление.")

    def test_partial_subclass_translation_is_not_published(self) -> None:
        memory = TranslationMemory()
        memory.add("2014", "subclass", "Ancient Dragons",
                   MemoryEntry(name="Древние драконы", description="Короткое вступление."))
        item = entity("subclass:dragons", "Ancient Dragons", category="subclass", edition="2014")
        item.description = "Full text. " * 500
        item.translations["en"].description = item.description
        self.assertFalse(apply(memory, item, "v1"))
        self.assertNotIn("ru", item.translations)


class DerivedTests(unittest.TestCase):
    def test_name_only_match_still_gets_derived_description(self) -> None:
        item = entity("monster:dragon", "Adult Black Dragon", category="monster", edition="2014",
                      normalized={"size": "huge", "type": "dragon", "alignment": "chaotic evil",
                                  "challenge_rating": 14, "hit_points": 195, "armor_class": 19,
                                  "damage_resistances": ["necrotic"],
                                  "condition_immunities": ["charmed"]})
        item.description = ""
        item.translations["en"].description = ""
        item.translations["ru"] = Translation(name="Взрослый чёрный дракон", description="")
        self.assertTrue(apply_derived(item))
        ru = item.translations["ru"]
        self.assertEqual(ru.name, "Взрослый чёрный дракон")
        self.assertIn("Огромный дракон", ru.description)
        self.assertIn("очарование", ru.description)
        self.assertNotIn("from nonmagical", ru.description)

    def test_false_description_counts_as_empty_prose(self) -> None:
        item = entity("monster:spirit", "Chernomoi", category="monster", edition="2014",
                      normalized={"size": "medium", "type": "fiend", "challenge_rating": 3, "hit_points": 45, "armor_class": 13})
        item.description = "False"
        item.translations["en"].description = "False"
        self.assertTrue(apply_derived(item))
        self.assertIn("Среднее исчадие", item.translations["ru"].description)


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


class SubentityTranslationTests(unittest.TestCase):
    def _entity_with(self, category: str, subentities: dict) -> Entity:
        ent = entity(f"test:{category}", "Test", category=category, edition="2014")
        ent.mechanics["subentities"] = subentities
        return ent

    def test_curated_feature_translation_by_text_hash(self) -> None:
        from scripts.ingest.subtranslate import text_key, translate_subentities
        desc = "You can use your rage as a bonus action."
        curated = {text_key(desc): {"name_ru": "Ярость", "description_ru": "Вы можете войти в ярость бонусным действием."}}
        ent = self._entity_with("class", {"features": [
            {"name": "Rage", "level": 1, "desc": desc}]})
        stats = translate_subentities(TranslationMemory(), ent, curated)
        item = ent.mechanics["subentities"]["features"][0]
        self.assertEqual(item["desc_ru"], "Вы можете войти в ярость бонусным действием.")
        self.assertEqual(item["name_ru"], "Ярость")
        self.assertEqual(item["ru_source"], "curated")
        self.assertEqual(stats.get("curated"), 1)

    def test_memory_feature_entry_translates_payload(self) -> None:
        from scripts.ingest.subtranslate import translate_subentities
        memory = TranslationMemory()
        memory.add("2014", "", "Level 1: Rage", MemoryEntry(
            name="Ярость", description="На 1-м уровне вы можете войти в ярость.",
            attribution="test", license="CC-BY-4.0", source="test", edition="2014"))
        ent = self._entity_with("subclass", {"features": [
            {"name": "Rage", "level": 1, "desc": "Starting at 1st level you can rage."}]})
        translate_subentities(memory, ent, {})
        item = ent.mechanics["subentities"]["features"][0]
        self.assertEqual(item["ru_source"], "memory")
        self.assertIn("ярость", item["desc_ru"])

    def test_attack_line_template(self) -> None:
        from scripts.ingest.subtranslate import translate_subentities
        ent = self._entity_with("monster", {"actions": [
            {"name": "Bite", "action_type": "ACTION",
             "desc": "Melee Weapon Attack: +8 to hit, reach 5 ft., one target. "
                     "Hit: 12 (2d6 + 5) piercing damage."}]})
        translate_subentities(TranslationMemory(), ent, {})
        item = ent.mechanics["subentities"]["actions"][0]
        self.assertEqual(item["ru_source"], "template")
        self.assertIn("+8 к попаданию", item["desc_ru"])
        self.assertIn("2к6+5", item["desc_ru"])
        self.assertIn("колющего урона", item["desc_ru"])

    def test_unmatched_prose_gets_marked_derived_stub(self) -> None:
        from scripts.ingest.subtranslate import translate_subentities
        ent = self._entity_with("subclass", {"features": [
            {"name": "Arcane Aegis", "level": 2,
             "desc": "You can use the power of your school's spells to ward yourself."}]})
        translate_subentities(TranslationMemory(), ent, {})
        item = ent.mechanics["subentities"]["features"][0]
        self.assertEqual(item["ru_source"], "derived")
        self.assertTrue(item["desc_ru"])
        self.assertTrue(item["name_ru"])


if __name__ == "__main__":
    unittest.main()
