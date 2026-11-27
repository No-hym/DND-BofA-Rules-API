"""Russian rendering of structured sub-entities (class features, monster
traits and actions, species traits, background benefits, ...).

Entity-level translations (``translations.ru``) never covered the nested
payloads in ``mechanics.subentities``: the normalizers copy those verbatim
from upstream, so any client rendering them as separate blocks (class
features on a character sheet, a monster's traits/actions) always showed
English. This module fills ``name_ru``/``desc_ru`` on every nested item
from layered, honest sources, strongest first:

1. curated-by-text translations (``data/translations/curated-features.json``),
   keyed by the sha256 of the English text, so one translation serves every
   book/edition that reuses the same text (status ``machine``, editorial
   review required);
2. the licensed translation memory: exact ``Level N: <feature>`` corpus
   sections for class/subclass features, and exact-name corpus sections
   for species traits (length-guarded);
3. full-match formula templates for formulaic statblock lines (monster
   attack lines, multiattacks, common standard traits). A template fires
   only when it accounts for the *entire* English text;
4. a derived stub rendered from the item's own structured fields (kind,
   level, action type), explicitly marked ``derived`` so clients can tell
   it apart from a real translation. No prose is invented.

Every item records where its Russian text came from in ``ru_source``
(``curated``/``memory``/``template``/``derived``). Items whose payload has
no English text at all are left untouched.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .derived import russian_name
from .translations import CYRILLIC, TranslationMemory

KIND_LABEL_RU = {
    "features": "Классовое умение",
    "traits": "Особенность",
    "actions": "Действие",
    "benefits": "Преимущество",
    "casting_options": "Вариант сотворения",
    "descriptions": "Описание",
    "reactions": "Реакция",
    "legendary_actions": "Легендарное действие",
}

_DAMAGE_GENITIVE = {
    "acid": "кислотного", "bludgeoning": "дробящего", "cold": "холодного",
    "fire": "огненного", "force": "силового", "lightning": "электрического",
    "necrotic": "некротического", "piercing": "колющего", "poison": "ядовитого",
    "psychic": "психического", "radiant": "светлого", "slashing": "рубящего",
    "thunder": "звукового",
}
_CONDITION_RU = {
    "grappled": "схвачено", "restrained": "сдержано", "prone": "сбито с ног",
    "poisoned": "отравлено", "stunned": "ошеломлено", "paralyzed": "парализовано",
    "frightened": "напугано", "charmed": "очаровано", "blinded": "ослеплено",
    "deafened": "оглушено", "incapacitated": "выведено из строя",
}
_ABILITY_RU = {
    "strength": "Силы", "dexterity": "Ловкости", "constitution": "Телосложения",
    "intelligence": "Интеллекта", "wisdom": "Мудрости", "charisma": "Харизмы",
}
_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
_NUM_RU = {1: "одну", 2: "две", 3: "три", 4: "четыре", 5: "пять", 6: "шесть"}


def text_key(description_en: str) -> str:
    """Stable key of an English payload text (whitespace-normalized)."""
    normalized = re.sub(r"\s+", " ", description_en).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_curated_features(path: Path) -> dict[str, dict[str, str]]:
    """Load curated sub-entity translations keyed by English text hash."""
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    entries: dict[str, dict[str, str]] = {}
    for raw in data.get("entries", []):
        key = raw.get("key") or (text_key(raw["description_en"]) if raw.get("description_en") else "")
        if key and raw.get("description_ru"):
            entries[key] = {
                "name_ru": raw.get("name_ru", ""),
                "description_ru": raw["description_ru"],
            }
    return entries


def _dice(expression: str) -> str:
    return re.sub(r"(\d+)\s*d\s*(\d+)", r"\1к\2", expression).replace(" ", "")


_ATTACK_RE = re.compile(
    r"^(?P<melee>Melee or Ranged|Melee|Ranged) (?P<spell>Weapon|Spell) Attack: "
    r"(?P<tohit>[+-]\d+) to hit, "
    r"(?:reach (?P<reach>\d+) ft\.(?: or range (?P<reachrange>[\d/]+) ft\.)?"
    r"|range (?P<range>[\d/]+) ft\.), "
    r"(?P<target>one target|one creature)(?P<swarm> in the swarm's space)?\. "
    r"Hit: (?P<rest>.+)$", re.S)
_DAMAGE_SEGMENT = re.compile(
    r"(?P<avg>\d+) \((?P<dice>[^)]+)\) (?P<type>[a-z]+) damage")
_TAIL_CONDITION = re.compile(
    r", and the target is (?P<cond>[a-z]+)(?: \(escape DC (?P<dc>\d+)\))?")
_TAIL_VERSATILE = re.compile(
    r", or (?P<avg>\d+) \((?P<dice>[^)]+)\) (?P<type>[a-z]+) damage "
    r"if used (?:with )?(?:two hands|two-handed)\.?")


def _translate_attack(text: str) -> str | None:
    cleaned = re.sub(r"_+", "", text.strip())
    match = _ATTACK_RE.match(cleaned)
    if not match:
        return None
    rest = match.group("rest").strip()
    parts: list[str] = []
    position = 0
    segments = 0
    for seg in _DAMAGE_SEGMENT.finditer(rest):
        between = rest[position:seg.start()].strip()
        if segments == 0 and between:
            return None
        if segments and between in (", or", "or"):
            break  # versatile alternative: handled as the tail below
        if segments and between not in ("plus", ", plus", "and", ", and"):
            return None
        dtype = _DAMAGE_GENITIVE.get(seg.group("type"))
        if dtype is None:
            return None
        parts.append(f"{seg.group('avg')} ({_dice(seg.group('dice'))}) {dtype} урона")
        position = seg.end()
        segments += 1
    if not segments:
        return None
    tail = rest[position:].strip()
    if tail == ".":
        tail = ""
    tail_ru = ""
    if tail:
        versatile = _TAIL_VERSATILE.fullmatch(tail)
        cond = _TAIL_CONDITION.fullmatch(tail.rstrip("."))
        if versatile and versatile.group("type") in _DAMAGE_GENITIVE:
            tail_ru = (f", или {versatile.group('avg')} ({_dice(versatile.group('dice'))}) "
                       f"{_DAMAGE_GENITIVE[versatile.group('type')]} урона при использовании двумя руками.")
        elif cond and cond.group("cond") in _CONDITION_RU:
            tail_ru = f", и цель {_CONDITION_RU[cond.group('cond')]}"
            if cond.group("dc"):
                tail_ru += f" (Сл освобождения {cond.group('dc')})"
            tail_ru += "."
        else:
            return None
    kind_ru = "Атака оружием" if match.group("spell") == "Weapon" else "Атака заклинанием"
    mode_ru = {"Melee": "ближнего боя", "Ranged": "дальнего боя"}.get(
        match.group("melee"), "ближнего или дальнего боя")
    zones = []
    if match.group("reach"):
        zones.append(f"досягаемость {match.group('reach')} фт.")
    if match.group("reachrange"):
        zones.append(f"дистанция {match.group('reachrange')} фт.")
    if match.group("range"):
        zones.append(f"дистанция {match.group('range')} фт.")
    zone = " или ".join(zones)
    target = "одна цель" if match.group("target") == "one target" else "одно существо"
    if match.group("swarm"):
        target += " в пространстве роя"
    hit = ("Попадание: " + " плюс ".join(parts) + tail_ru).rstrip(".") + "."
    return (f"{kind_ru} {mode_ru}: {match.group('tohit')} к попаданию, {zone}, {target}. {hit}")


_MULTIATTACK_RE = re.compile(
    r"^The .+? makes (?P<total>one|two|three|four|five|\d+) attacks?: (?P<list>.+)\.$", re.S)
_MULTIATTACK_FLAT_RE = re.compile(
    r"^The .+? makes (?P<list>(?:one|two|three|four|five|\d+) attacks? with its .+)\.$", re.S)
_MULTIATTACK_SEGMENT = re.compile(
    r"(one|two|three|four|five|\d+) (?:attacks? )?with its "
    r"([a-z][a-z' -]*?)(?=, | and (?:one|two|three|four|five|\d+) with its|\.|$)")


def _translate_multiattack(text: str) -> str | None:
    stripped = text.strip()
    match = _MULTIATTACK_RE.match(stripped)
    total = None
    if match:
        listing = match.group("list")
        total = match.group("total")
    else:
        flat = _MULTIATTACK_FLAT_RE.match(stripped)
        if not flat:
            return None
        listing = flat.group("list")
    segments = _MULTIATTACK_SEGMENT.findall(listing)
    if not segments:
        return None
    # The whole list must consist of "N with its X" segments.
    residue = _MULTIATTACK_SEGMENT.sub("", listing)
    if residue.replace("attacks", "").replace("attack", "").replace("and", "").replace(",", "").strip():
        return None
    rendered = []
    for number, weapon in segments:
        count = _NUM_WORDS.get(number, None)
        count_ru = _NUM_RU.get(count, number) if count else number
        rendered.append(f"{count_ru} — атака «{russian_name(weapon.strip())}»")
    if total is None:
        total_n = sum(_NUM_WORDS.get(n, int(n) if n.isdigit() else 0) for n, _ in segments)
    else:
        total_n = _NUM_WORDS.get(total, total)
    return (f"Мультиатака. Существо совершает {total_n} атаки: "
            + "; ".join(rendered) + ".")


_TRAIT_PATTERNS: list[tuple[re.Pattern[str], Any]] = [
    (re.compile(r"^The .+ can breathe air and water\.$"),
     lambda m: "Может дышать как воздухом, так и водой."),
    (re.compile(r"^The .+ can hold its breath for ([\d,]+) (minute|minutes|hour|hours)\.$"),
     lambda m: f"Может задерживать дыхание на {m.group(1)} "
               + ("минуту." if m.group(2) == "minute" else
                  "минут." if m.group(2) in ("minutes",) else
                  "час." if m.group(2) == "hour" else "часов.")),
    (re.compile(r"^The .+ has advantage on saving throws against spells and other magical effects\.$"),
     lambda m: "Совершает спасброски от заклинаний и прочих магических эффектов с преимуществом."),
    (re.compile(r"^The .+ has advantage on Wisdom \(Perception\) checks that rely on (?P<sense>smell|hearing|sight)\.$"),
     lambda m: "Совершает проверки Мудрости (Восприятие) с преимуществом, если они полагаются на "
               + {"smell": "обоняние.", "hearing": "слух.", "sight": "зрение."}[m.group("sense")]),
    (re.compile(r"^The .+ has advantage on attack rolls against a creature if at least one of the .+? allies is within 5 feet of the creature and the ally isn't incapacitated\.$"),
     lambda m: "Совершает броски атаки по существу с преимуществом, если хотя бы один его союзник "
               "находится в пределах 5 футов от существа и этот союзник не выведен из строя."),
    (re.compile(r"^The .+ can climb difficult surfaces, including upside down on ceilings, without needing to make an ability check\.$"),
     lambda m: "Может карабкаться по трудным поверхностям, включая потолки вниз головой, "
               "без проверки характеристик."),
    (re.compile(r"^The .+ is immune to any spell or effect that would alter its form\.$"),
     lambda m: "Иммунитет к любым заклинаниям и эффектам, которые изменили бы его форму."),
    (re.compile(r"^The .+? weapon attacks are magical\.$"),
     lambda m: "Его атаки оружием являются магическими."),
    (re.compile(r"^The .+ can move through a space as narrow as 1 inch wide without squeezing\.$"),
     lambda m: "Может перемещаться через пространство шириной от 1 дюйма, не протискиваясь."),
    (re.compile(r"^If the .+ fails a saving throw, it can choose to succeed instead\.$"),
     lambda m: "Если проваливает спасбросок, может вместо этого выбрать успех."),
    (re.compile(r"^The .+ has disadvantage on attack rolls and on Wisdom \(Perception\) checks that rely on sight when the .+?, the target of its attack, or whatever it is trying to perceive is in direct sunlight\.$"),
     lambda m: "Совершает броски атаки и проверки Мудрости (Восприятие), полагающиеся на зрение, "
               "с помехой, когда само существо, цель его атаки или то, что оно пытается воспринять, "
               "находится под прямым солнечным светом."),
]


def template_description(kind: str, text: str) -> str | None:
    """Translate a formulaic statblock line; None unless it fully matches."""
    stripped = text.strip()
    if kind in ("actions", "legendary_actions", "reactions"):
        for translator in (_translate_attack, _translate_multiattack):
            rendered = translator(stripped)
            if rendered:
                return rendered
    if kind == "traits":
        for pattern, render in _TRAIT_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return render(match)
    return None


def _stub_description(kind: str, item: dict[str, Any], name_ru: str) -> str:
    label = KIND_LABEL_RU.get(kind, "Элемент")
    details = [label + (f" «{name_ru}»" if name_ru else "")]
    if item.get("level") is not None:
        details.append(f"уровень {item['level']}")
    if item.get("action_type"):
        details.append(f"тип: {str(item['action_type']).lower()}")
    # A derived rendering of the item's own structured fields only; the full
    # English prose stays in `desc` and is never paraphrased or invented.
    return ("; ".join(details)
            + ". Производный машинный текст из структурированных полей записи; "
              "полный исходный текст — в поле desc (требуется перевод и редакторская вычитка).")


def _memory_description(memory: TranslationMemory, entity: Any, kind: str,
                        item: dict[str, Any], en_desc: str) -> tuple[str, str] | None:
    name = str(item.get("name") or "")
    if not name:
        return None
    if kind == "features":
        entry = memory.feature_entry(entity.edition, item.get("level"), name)
        if entry and entry.description and CYRILLIC.search(entry.description):
            name_ru = re.sub(r"^(Уровень|Level)\s+\d+:\s*", "", entry.name).strip()
            return name_ru, entry.description
    if kind == "traits" and entity.category in ("species", "subspecies"):
        entry = memory.lookup(entity.edition, "", name)
        if (entry and entry.description and CYRILLIC.search(entry.description)
                and 0.4 * len(en_desc) <= len(entry.description) <= 2.5 * len(en_desc)):
            return entry.name, entry.description
    return None


def translate_subentities(memory: TranslationMemory, entity: Any,
                          curated: dict[str, dict[str, str]]) -> dict[str, int]:
    """Fill name_ru/desc_ru on every nested payload of one entity.

    Returns per-source counters. Items that already carry a translation
    (e.g. subclass features written by the description assembly in
    translations.apply) are kept as-is.
    """
    stats: dict[str, int] = {}
    subentities = entity.mechanics.get("subentities") or {}
    for kind, items in subentities.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            en_desc = str(item.get("desc") or item.get("description") or "")
            en_name = str(item.get("name") or "")
            if not en_desc.strip() and not en_name.strip():
                continue
            if item.get("desc_ru"):
                stats["already"] = stats.get("already", 0) + 1
                continue
            name_ru = ""
            desc_ru = ""
            source = ""
            curated_hit = curated.get(text_key(en_desc)) if en_desc.strip() else None
            if curated_hit:
                name_ru = curated_hit.get("name_ru", "")
                desc_ru = curated_hit.get("description_ru", "")
                source = "curated"
            if not desc_ru and en_desc.strip():
                memory_hit = _memory_description(memory, entity, kind, item, en_desc)
                if memory_hit:
                    name_ru, desc_ru = memory_hit
                    source = "memory"
            if not desc_ru and en_desc.strip():
                templated = template_description(kind, en_desc)
                if templated:
                    desc_ru = templated
                    source = "template"
            if not name_ru and en_name:
                name_ru = russian_name(en_name)
            if not desc_ru:
                desc_ru = _stub_description(kind, item, name_ru)
                source = "derived"
            if name_ru:
                item["name_ru"] = name_ru
            item["desc_ru"] = desc_ru
            item["ru_source"] = source
            stats[source] = stats.get(source, 0) + 1
    return stats
