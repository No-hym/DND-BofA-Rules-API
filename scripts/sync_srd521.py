#!/usr/bin/env python3
"""Rebuild SRD 5.2.1 catalogs from pinned CC BY English and Russian sources.

Inputs are deliberately kept outside this repository: the official-SRD-derived
5etools JSON export, the Russian SRD translation reference JSON, and OmnisGM's
Russian rules chapters. Translation matching uses exact names/headings and does
not invent localized content where a reliable match is unavailable.
"""

from __future__ import annotations

import argparse
import json
import re
from fractions import Fraction
from pathlib import Path
from typing import Any

SRD_SOURCE = "5etools-srd:SRD521"
VERSION = "5.2.1"
UPDATED_AT = "2026-11-26"
MONSTER_REFERENCE_COMMIT = "547fc77f31649f69ff67c97699125d491f2f9209"
TRANSLATION_COMMIT = "1f7192be159e84f2db7212565866747094e3b9de"
DATA_COMMIT = "3b26955ea5394fde43a1e33b2a878b42cebbe51c"

RU_CONDITION_NAMES = {
    "Blinded": "Ослеплённый",
    "Charmed": "Очарованный",
    "Deafened": "Оглохший",
    "Exhaustion": "Истощение",
    "Frightened": "Испуганный",
    "Grappled": "Схваченный",
    "Incapacitated": "Недееспособный",
    "Invisible": "Невидимый",
    "Paralyzed": "Парализованный",
    "Petrified": "Окаменевший",
    "Poisoned": "Отравленный",
    "Prone": "Лежащий",
    "Restrained": "Опутанный",
    "Stunned": "Ошеломлённый",
    "Unconscious": "Без сознания",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def render_entries(value: Any) -> str:
    """Render 5etools entry nodes to readable English text; raw nodes are retained too."""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return "" if value is None else str(value)
    if isinstance(value, list):
        return "\n\n".join(part for item in value if (part := render_entries(item)))
    if isinstance(value, dict):
        name = value.get("name")
        if "entries" in value:
            body = render_entries(value["entries"])
        elif "items" in value:
            body = render_entries(value["items"])
        elif "entry" in value:
            body = render_entries(value["entry"])
        else:
            body = ""
        if name and body:
            return f"{name}. {body}"
        if name:
            return str(name)
        return body
    return str(value)


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    if not slug:
        raise ValueError(f"cannot make stable id from {name!r}")
    return slug


def challenge_parts(value: Any) -> tuple[str | None, float | None, Any]:
    if isinstance(value, dict):
        rating = value.get("cr")
        xp = value.get("xp")
    else:
        rating, xp = value, None
    if rating is None:
        return None, None, xp
    text = str(rating)
    try:
        numeric = float(Fraction(text))
    except (ValueError, ZeroDivisionError):
        numeric = None
    return text, numeric, xp


def ac_value(value: Any) -> Any:
    if not isinstance(value, list) or not value:
        return None
    first = value[0]
    if isinstance(first, dict):
        return first.get("ac", first.get("special"))
    return first


def size_label(sizes: Any) -> str:
    labels = {"T": "Tiny", "S": "Small", "M": "Medium", "L": "Large", "H": "Huge", "G": "Gargantuan", "V": "Varies"}
    if not isinstance(sizes, list):
        return str(sizes)
    return " or ".join(labels.get(str(size), str(size)) for size in sizes)


def section_entries(source: dict[str, Any], key: str) -> list[dict[str, Any]]:
    result = []
    for entry in source.get(key, []) or []:
        if isinstance(entry, dict):
            normalized = dict(entry)
            normalized["description"] = render_entries(entry.get("entries", []))
            result.append(normalized)
        else:
            result.append({"description": render_entries(entry)})
    return result


def make_mechanics(source: dict[str, Any]) -> dict[str, Any]:
    cr, cr_numeric, xp = challenge_parts(source.get("cr"))
    hp = source.get("hp") or {}
    scores = {key: source[key] for key in ("str", "dex", "con", "int", "wis", "cha") if key in source}
    stats: dict[str, Any] = {
        "schema_version": 2,
        "ability_scores": scores,
        "speed": source.get("speed", {}),
        "senses": source.get("senses", []),
        "passive_perception": source.get("passive"),
        "saving_throws": source.get("save", {}),
        "skills": source.get("skill", {}),
        "damage_immunities": source.get("immune", []),
        "damage_resistances": source.get("resist", []),
        "damage_vulnerabilities": source.get("vulnerable", []),
        "condition_immunities": source.get("conditionImmune", []),
        "languages": source.get("languages", []),
        "traits": section_entries(source, "trait"),
        "actions": section_entries(source, "action"),
        "bonus_actions": section_entries(source, "bonus"),
        "reactions": section_entries(source, "reaction"),
        "legendary_actions": section_entries(source, "legendary"),
        "spellcasting": source.get("spellcasting", []),
        "source_data": source,
    }
    for key in ("gear", "initiative", "group", "dragonAge", "familiar", "summonedBySpell", "summonedBySpellLevel", "legendaryHeader", "legendaryActionsLair", "pbNote"):
        if key in source:
            stats[key] = source[key]
    for key in ("passive_perception", "saving_throws", "skills", "damage_immunities", "damage_resistances", "damage_vulnerabilities", "condition_immunities", "languages", "traits", "actions", "bonus_actions", "reactions", "legendary_actions", "spellcasting"):
        if stats[key] in (None, {}, []):
            stats.pop(key)
    mechanics: dict[str, Any] = {
        "type": source.get("type"),
        "size": size_label(source.get("size")),
        "size_codes": source.get("size", []),
        "alignment": source.get("alignment", []),
        "armor_class": ac_value(source.get("ac")),
        "armor_class_details": source.get("ac", []),
        "speed": source.get("speed", {}),
        "stat_block": {"stat_block_json": stats},
        "source_page": source.get("page"),
    }
    if cr is not None:
        mechanics["challenge_rating"] = cr
    if cr_numeric is not None:
        mechanics["challenge_rating_numeric"] = cr_numeric
    if xp is not None:
        mechanics["challenge_rating_xp"] = xp
    if isinstance(hp.get("average"), (int, float)):
        mechanics["hit_points"] = hp["average"]
    if hp.get("formula"):
        mechanics["hit_points_formula"] = hp["formula"]
    if hp.get("special"):
        mechanics["hit_points_special"] = hp["special"]
    if source.get("initiative") is not None:
        mechanics["initiative"] = source["initiative"]
    return mechanics


def attribution(translation_kind: str) -> str:
    text = (
        'This work includes material from the System Reference Document 5.2.1 '
        '("SRD 5.2.1") by Wizards of the Coast LLC, available at https://www.dndbeyond.com/srd. '
        'The SRD 5.2.1 is licensed under CC BY 4.0: https://creativecommons.org/licenses/by/4.0/legalcode. '
        f'Structured SRD data adapted from https://github.com/bankenichi/5etools-srd/tree/{DATA_COMMIT}, '
        'which republishes SRD 5.2.1 under CC BY 4.0. '
    )
    if translation_kind == "monster":
        text += (
            'Russian name and stat-block translation: Petr Radilov (OmnisGM), CC BY 4.0; '
            f'imported from https://github.com/my-git-store/nastolka-dnd-reference/tree/{MONSTER_REFERENCE_COMMIT}. '
        )
    else:
        text += (
            'Russian condition translation: Petr Radilov (OmnisGM), CC BY 4.0; '
            f'source https://github.com/OmnisGM-App/OmnisGM-Rules/tree/{TRANSLATION_COMMIT}/'
            'src/dnd/srd-5.2/ru/08_RulesGlossary.md. '
        )
    text += 'Russian translation license: https://creativecommons.org/licenses/by/4.0/legalcode. '
    return text + 'Adaptation: structured fields and catalog IDs were normalized for this API; RU text is source-attributed and has not been independently proofread here.'


def validate_monster_summary(source: dict[str, Any], reference: dict[str, Any]) -> None:
    """Cross-check key English mechanics against the independently structured RU reference."""
    armor = ac_value(source.get("ac"))
    if isinstance(armor, (int, float)) and reference.get("armorClass") != armor:
        raise ValueError(f"armor class mismatch for {source['name']}: {armor} vs {reference.get('armorClass')}")
    if isinstance(armor, str) and not str(reference.get("armorClass", "")).strip():
        raise ValueError(f"missing translated special armor class for {source['name']}")

    hp = source.get("hp") or {}
    if isinstance(hp.get("average"), (int, float)) and reference.get("hitPoints") != hp["average"]:
        raise ValueError(f"hit points mismatch for {source['name']}: {hp['average']} vs {reference.get('hitPoints')}")
    if hp.get("special") and not isinstance(reference.get("hitPoints"), str):
        raise ValueError(f"missing translated special hit points for {source['name']}")

    rating, _, _ = challenge_parts(source.get("cr"))
    reference_rating = reference.get("challenge")
    if rating is None:
        if reference_rating not in (None, "", "Нет"):
            raise ValueError(f"unexpected challenge rating for {source['name']}: {reference_rating}")
    elif str(rating) != str(reference_rating):
        raise ValueError(f"challenge rating mismatch for {source['name']}: {rating} vs {reference_rating}")


def build_monsters(args: argparse.Namespace) -> list[dict[str, Any]]:
    source_data = read_json(args.monsters_source)["monster"]
    reference = read_json(args.ru_monsters)
    old = read_json(args.previous_monsters)
    old_ids = {row["translations"]["en"]["name"].casefold(): row["id"] for row in old}
    source_names = {row["name"].casefold() for row in source_data}
    ru_names = {row["englishName"].casefold() for row in reference}
    if any(row.get("source") != "SRD521" or row.get("srd52") is not True for row in source_data):
        raise ValueError("monster source contains records outside SRD521")
    if source_names != ru_names or len(source_data) != 336 or len(reference) != 336:
        raise ValueError(f"monster source/translation name sets differ: source={len(source_names)} RU={len(ru_names)}")
    translated = {row["englishName"].casefold(): row for row in reference}
    used_ids: set[str] = set()
    result = []
    for source in source_data:
        name = source["name"]
        ref = translated[name.casefold()]
        validate_monster_summary(source, ref)
        entity_id = old_ids.get(name.casefold(), "srd:" + slugify(name))
        if entity_id in used_ids:
            raise ValueError(f"duplicate stable id {entity_id}")
        used_ids.add(entity_id)
        mechanics = make_mechanics(source)
        result.append({
            "id": entity_id,
            "category": "monster",
            "edition": "2024",
            "publisher_id": "wizards-of-the-coast",
            "book_id": "srd-5.2.1",
            "source": SRD_SOURCE,
            "license": "CC-BY-4.0",
            "version": VERSION,
            "external_id": entity_id,
            "translations": {
                "en": {"name": name, "description": "", "source_version": VERSION},
                "ru": {
                    "name": ref["name"],
                    "description": ref["body"].strip(),
                    "status": "source",
                    "updated_at": UPDATED_AT,
                    "source_version": VERSION,
                },
            },
            "mechanics": mechanics,
            "attribution": attribution("monster"),
        })
    return sorted(result, key=lambda row: row["translations"]["en"]["name"].casefold())


def parse_ru_condition_sections(markdown: str) -> dict[str, str]:
    lines = markdown.splitlines()
    sections: dict[str, str] = {}
    for index, line in enumerate(lines):
        match = re.match(r"^#### (.+?) \[Состояние\]\s*$", line)
        if not match:
            continue
        name = match.group(1).strip()
        end = index + 1
        while end < len(lines) and not lines[end].startswith("#### "):
            end += 1
        body = "\n".join(lines[index + 1:end]).strip()
        sections[name] = body
    return sections


def build_conditions(args: argparse.Namespace) -> list[dict[str, Any]]:
    source_data = read_json(args.conditions_source)["condition"]
    old = read_json(args.previous_conditions)
    old_ids = {row["translations"]["en"]["name"].casefold(): row["id"] for row in old}
    if any(row.get("source") != "SRD521" or row.get("srd52") is not True for row in source_data):
        raise ValueError("condition source contains records outside SRD521")
    ru_sections = parse_ru_condition_sections(args.ru_glossary.read_text(encoding="utf-8"))
    english_names = {row["name"] for row in source_data}
    if english_names != set(RU_CONDITION_NAMES):
        raise ValueError(f"condition list mismatch: source={sorted(english_names)} expected={sorted(RU_CONDITION_NAMES)}")
    if set(ru_sections) != set(RU_CONDITION_NAMES.values()):
        raise ValueError(f"Russian condition sections mismatch: {sorted(set(RU_CONDITION_NAMES.values()) - set(ru_sections))}")
    result = []
    for source in source_data:
        name = source["name"]
        ru_name = RU_CONDITION_NAMES[name]
        entity_id = old_ids.get(name.casefold(), "srd:" + slugify(name))
        result.append({
            "id": entity_id,
            "category": "condition",
            "edition": "2024",
            "publisher_id": "wizards-of-the-coast",
            "book_id": "srd-5.2.1",
            "source": SRD_SOURCE,
            "license": "CC-BY-4.0",
            "version": VERSION,
            "external_id": entity_id,
            "translations": {
                "en": {"name": name, "description": render_entries(source.get("entries", [])), "source_version": VERSION},
                "ru": {
                    "name": ru_name,
                    "description": ru_sections[ru_name],
                    "status": "source",
                    "updated_at": UPDATED_AT,
                    "source_version": VERSION,
                },
            },
            "mechanics": {"key": slugify(name), "source_page": source.get("page"), "source_data": source},
            "attribution": attribution("condition"),
        })
    return sorted(result, key=lambda row: row["translations"]["en"]["name"].casefold())



def parse_ru_named_sections(paths: list[Path], heading_level: int = 4) -> dict[str, tuple[str, str]]:
    """Map exact upstream English labels in RU Markdown headings to Russian body/name."""
    result: dict[str, tuple[str, str]] = {}
    pattern = re.compile(rf"^{'#' * heading_level} (.*?)\s*\(([^()]*)\)\s*$")
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            match = pattern.match(line)
            if not match:
                continue
            ru_name, en_name = match.group(1).strip(), match.group(2).strip()
            end = index + 1
            while end < len(lines):
                next_heading = re.match(r"^(#{1,6}) ", lines[end])
                if next_heading and len(next_heading.group(1)) <= heading_level:
                    break
                end += 1
            body = "\n".join(lines[index + 1:end]).strip()
            result.setdefault(en_name.casefold(), (ru_name, body))
    return result


def source_attribution() -> str:
    return (
        'This work includes material from the System Reference Document 5.2.1 '
        '("SRD 5.2.1") by Wizards of the Coast LLC, https://www.dndbeyond.com/srd, '
        'licensed under CC BY 4.0: https://creativecommons.org/licenses/by/4.0/legalcode. '
        f'Structured data adapted from https://github.com/bankenichi/5etools-srd/tree/{DATA_COMMIT} (CC BY 4.0). '
        f'Russian translation source: OmnisGM Rules, Petr Radilov, CC BY 4.0, '
        f'https://github.com/OmnisGM-App/OmnisGM-Rules/tree/{TRANSLATION_COMMIT}/src/dnd/srd-5.2/ru. '
        'Russian text is source-attributed and has not been independently proofread in this project.'
    )


def build_srd_records(rows: list[dict[str, Any]], category: str, sections: dict[str, tuple[str, str]],
                      *, level: int | None = None) -> list[dict[str, Any]]:
    """Keep complete upstream JSON in mechanics and attach only exact-label RU sections."""
    result = []
    for source in rows:
        #translate: Upstream 5etools-srd marks some legacy item entries with srd52 equal to their name; source=SRD521 is still the inclusion boundary.
        if source.get("source") != "SRD521" or source.get("srd52") not in (True, source.get("name")):
            raise ValueError(f"{category} contains a record outside SRD521: {source.get('name')}")
        en_name = source["name"]
        localized = sections.get(en_name.casefold())
        # For family variants, the source-family heading is an exact, auditable match.
        if localized is None:
            family = source.get("_srd521", {}).get("heading")
            localized = sections.get(str(family).casefold()) if family else None
        ru_name, ru_body = localized if localized else (en_name, "")
        entity_id = "srd:" + category + ":" + slugify(en_name)
        english_description = render_entries(source.get("entries", []))
        if source.get("entriesHigherLevel"):
            english_description += "\n\n" + render_entries(source["entriesHigherLevel"])
        mechanics: dict[str, Any] = {"source_page": source.get("page"), "source_data": source}
        if level is not None:
            mechanics["level"] = level
        ru_translation: dict[str, Any] = {"name": ru_name, "description": ru_body, "updated_at": UPDATED_AT,
                                          "source_version": VERSION}
        if localized:
            ru_translation["status"] = "source"
        result.append({
            "id": entity_id,
            "category": category,
            "edition": "2024",
            "publisher_id": "wizards-of-the-coast",
            "book_id": "srd-5.2.1",
            "source": SRD_SOURCE,
            "license": "CC-BY-4.0",
            "version": VERSION,
            "external_id": entity_id,
            "translations": {
                "en": {"name": en_name, "description": english_description, "source_version": VERSION},
                "ru": ru_translation,
            },
            "mechanics": mechanics,
            "attribution": source_attribution(),
        })
    return result


def build_requested_categories(args: argparse.Namespace) -> dict[str, list[dict[str, Any]]]:
    ru = args.ru_rules
    sections4 = parse_ru_named_sections([
        ru / "04_CharacterOrigins.md", ru / "05_Feats.md", ru / "06_Equipment.md", ru / "10_MagicItems.md"
    ])
    #translate: These aliases connect SRD base-item names to exact rows in OmnisGM's 2024 equipment tables.
    ru_base_item_names = {
        "Arrow": "Стрелы", "Arrows (20)": "Стрелы", "Bolt": "Болты", "Bolts (20)": "Болты",
        "Firearm Bullet": "Пули огнестрельные", "Firearm Bullets (10)": "Пули огнестрельные",
        "Needle": "Иглы", "Needles (50)": "Иглы", "Sling Bullet": "Снаряды для пращи", "Sling Bullets (20)": "Снаряды для пращи",
        "Club": "Дубинка", "Dagger": "Кинжал", "Greatclub": "Палица", "Handaxe": "Ручной топор",
        "Javelin": "Метательное копьё", "Light Hammer": "Лёгкий молот", "Mace": "Булава",
        "Quarterstaff": "Боевой посох", "Sickle": "Серп", "Spear": "Копьё", "Dart": "Дротик",
        "Light Crossbow": "Лёгкий арбалет", "Shortbow": "Короткий лук", "Sling": "Праща",
        "Battleaxe": "Боевой топор", "Flail": "Цеп", "Glaive": "Глефа", "Greataxe": "Секира",
        "Greatsword": "Двуручный меч", "Halberd": "Алебарда", "Lance": "Копьё для турнира",
        "Longsword": "Длинный меч", "Maul": "Молот", "Morningstar": "Моргенштерн", "Pike": "Пика",
        "Rapier": "Рапира", "Scimitar": "Скимитар", "Shortsword": "Короткий меч", "Trident": "Трезубец",
        "Warhammer": "Боевой молот", "War Pick": "Боевая кирка", "Whip": "Кнут",
        "Blowgun": "Духовая трубка", "Hand Crossbow": "Ручной арбалет", "Heavy Crossbow": "Тяжёлый арбалет",
        "Longbow": "Длинный лук", "Musket": "Мушкет", "Pistol": "Пистолет",
        "Padded Armor": "Стёганый доспех", "Leather Armor": "Кожаный доспех",
        "Studded Leather Armor": "Проклёпанный кожаный доспех", "Hide Armor": "Шкурный доспех",
        "Chain Shirt": "Кольчужная рубаха", "Scale Mail": "Чешуйчатый доспех", "Breastplate": "Кираса",
        "Half Plate Armor": "Полулаты", "Ring Mail": "Колечный доспех", "Chain Mail": "Кольчуга",
        "Splint Armor": "Наборный доспех", "Plate Armor": "Латы", "Shield": "Щит",
    }
    equipment_lines = (ru / "06_Equipment.md").read_text(encoding="utf-8").splitlines()
    table_rows: dict[str, str] = {}
    for line in equipment_lines:
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if cells:
                table_rows.setdefault(cells[0].casefold(), line.strip())
    for en_name, ru_label in ru_base_item_names.items():
        row = table_rows.get(ru_label.casefold())
        if row:
            sections4[en_name.casefold()] = (ru_label, row)
    spell_sections = parse_ru_named_sections([ru / "07_Spells.md"], heading_level=3)
    base = args.srd_data
    json_items = read_json(base / "items.json")["item"]
    # Distinct baseitem records carry the 2024 weapon/armor stat blocks and are retained separately.
    json_baseitems = read_json(base / "items-base.json")["baseitem"]
    spells = read_json(base / "spells" / "spells-xphb.json")["spell"]
    feats = read_json(base / "feats.json")["feat"]
    backgrounds = read_json(base / "backgrounds.json")["background"]
    races = read_json(base / "races.json")["race"]
    all_items = build_srd_records(json_items, "item", sections4)
    all_items.extend(build_srd_records(json_baseitems, "equipment", sections4))
    return {
        "items": sorted(all_items, key=lambda r: r["translations"]["en"]["name"].casefold()),
        "spells": build_srd_records(spells, "spell", spell_sections),
        "feats": build_srd_records(feats, "feat", sections4),
        "backgrounds": build_srd_records(backgrounds, "background", sections4),
        "species": build_srd_records(races, "species", sections4),
    }

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monsters-source", type=Path, help="5etools data/bestiary/bestiary-srd521.json")
    parser.add_argument("--conditions-source", type=Path, help="5etools data/conditionsdiseases.json")
    parser.add_argument("--ru-monsters", type=Path, help="Nastolka reference monsters.json")
    parser.add_argument("--ru-glossary", type=Path, help="OmnisGM SRD 5.2.1 Russian RulesGlossary.md")
    parser.add_argument("--previous-monsters", type=Path, default=Path("data/catalog/2024/monsters.json"))
    parser.add_argument("--previous-conditions", type=Path, default=Path("data/catalog/2024/conditions.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/catalog/2024"))
    parser.add_argument("--srd-data", type=Path, help="pinned 5etools data directory; enables additional SRD categories")
    parser.add_argument("--ru-rules", type=Path, help="OmnisGM pinned Russian SRD rules directory")
    args = parser.parse_args()

    if bool(args.monsters_source) != bool(args.ru_monsters):
        parser.error("--monsters-source and --ru-monsters must be supplied together")
    if bool(args.conditions_source) != bool(args.ru_glossary):
        parser.error("--conditions-source and --ru-glossary must be supplied together")
    if not any((args.monsters_source, args.conditions_source, args.srd_data)):
        parser.error("provide at least one source set to build")
    monsters = build_monsters(args) if args.monsters_source else None
    conditions = build_conditions(args) if args.conditions_source else None
    additional = build_requested_categories(args) if args.srd_data and args.ru_rules else {}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if monsters is not None:
        (args.out_dir / "monsters.json").write_text(json.dumps(monsters, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if conditions is not None:
        (args.out_dir / "conditions.json").write_text(json.dumps(conditions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for filename, records in additional.items():
        (args.out_dir / f"{filename}.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    extra_count = sum(map(len, additional.values()))
    print(f"Wrote {len(monsters or [])} monsters, {len(conditions or [])} conditions, and {extra_count} additional SRD records to {args.out_dir}")


if __name__ == "__main__":
    main()
