"""Derived Russian text for records whose structured mechanics are complete
but whose prose description is empty upstream (most Open5e v2 monsters and
creature attacks).

Nothing here invents lore: the Russian description is a faithful rendering of
the record's own normalized mechanics (size, type, armor class, hit points,
damage dice, ...), and the Russian name is a dictionary translation of common
D&D terms with transliteration of proper names. Everything produced here is
marked ``status: machine`` with provenance ``derived-from-structured-mechanics``
so editors can prioritize it for review.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .model import Entity, Translation

WORDS: dict[str, str] = {
    "tiny": "Крошечный", "small": "Маленький", "medium": "Средний", "large": "Крупный",
    "huge": "Огромный", "gargantuan": "Гигантский",
    "aberration": "аберрация", "beast": "зверь", "celestial": "небожитель",
    "construct": "конструкт", "dragon": "дракон", "elemental": "элементаль",
    "fey": "фея", "fiend": "исчадие", "giant": "великан", "humanoid": "гуманоид",
    "monstrosity": "чудовище", "ooze": "слизь", "plant": "растение", "undead": "нежить",
    "angel": "ангел", "demon": "демон", "devil": "дьявол", "goblinoid": "гоблиноид",
    "swarm": "рой", "shapechanger": "оборотень",
    "acid": "кислотный", "bludgeoning": "дробящий", "cold": "холодный",
    "fire": "огненный", "force": "силовой", "lightning": "электрический",
    "necrotic": "некротический", "piercing": "колющий", "poison": "ядовитый",
    "psychic": "психический", "radiant": "светлый", "slashing": "рубящий",
    "thunder": "звуковой",
    "bite": "Укус", "claw": "Коготь", "claws": "Когти", "tail": "Хвост",
    "sting": "Жало", "slam": "Удар", "fist": "Кулак", "hoof": "Копыто",
    "tentacle": "Щупальце", "horn": "Рог", "horns": "Рога", "beak": "Клюв",
    "attack": "атака", "longbow": "длинный лук", "shortbow": "короткий лук",
    "longsword": "длинный меч", "shortsword": "короткий меч", "dagger": "кинжал",
    "spear": "копьё", "axe": "топор", "greataxe": "секира", "greatsword": "двуручный меч",
    "mace": "булава", "club": "дубинка", "staff": "посох", "bow": "лук",
    "crossbow": "арбалет", "sword": "меч", "hammer": "молот", "warhammer": "боевой молот",
    "scimitar": "скимитар", "rapier": "рапира", "whip": "кнут", "trident": "трезубец",
    "glaive": "глефа", "halberd": "алебарда", "pike": "пика", "lance": "рыцарское копьё",
    "net": "сеть", "dart": "дротик", "sling": "праща", "blowgun": "духовая трубка",
    "javelin": "метательное копьё", "handaxe": "ручной топор", "sickle": "серп",
    "quarterstaff": "боевой посох", "morningstar": "моргенштерн", "flail": "цеп",
    "maul": "кувалда", "greatclub": "большая дубинка",
    "young": "молодой", "adult": "взрослый", "ancient": "древний", "elder": "старший",
    "greater": "большой", "lesser": "малый", "king": "король", "queen": "королева",
    "lord": "владыка", "knight": "рыцарь", "warrior": "воин", "mage": "маг",
    "priest": "жрец", "acolyte": "прислужник", "cultist": "культист",
    "bandit": "бандит", "guard": "страж", "scout": "разведчик", "spy": "шпион",
    "veteran": "ветеран", "archmage": "архимаг", "assassin": "убийца",
    "berserker": "берсерк", "champion": "чемпион", "gladiator": "гладиатор",
    "druid": "друид", "shaman": "шаман", "witch": "ведьма", "warlock": "колдун",
    "wizard": "волшебник", "sorcerer": "чародей", "cleric": "жрец",
    "paladin": "паладин", "ranger": "следопыт", "rogue": "плут", "bard": "бард",
    "monk": "монах", "fighter": "воин", "barbarian": "варвар",
    "rat": "крыса", "wolf": "волк", "bear": "медведь", "boar": "кабан",
    "snake": "змея", "spider": "паук", "bat": "летучая мышь", "cat": "кошка",
    "dog": "собака", "horse": "лошадь", "eagle": "орёл", "hawk": "ястреб",
    "owl": "сова", "raven": "ворон", "lion": "лев", "tiger": "тигр",
    "shark": "акула", "octopus": "осьминог", "crab": "краб", "frog": "лягушка",
    "toad": "жаба", "lizard": "ящерица", "ape": "обезьяна", "beetle": "жук",
    "crocodile": "крокодил", "elephant": "слон", "elk": "лось", "fox": "лиса",
    "hyena": "гиена", "leopard": "леопард", "panther": "пантера",
    "scorpion": "скорпион", "wasp": "оса", "whale": "кит",
    "skeleton": "скелет", "zombie": "зомби", "ghost": "призрак",
    "vampire": "вампир", "mummy": "мумия", "ghoul": "упырь", "golem": "голем",
    "red": "красный", "black": "чёрный", "white": "белый", "green": "зелёный",
    "blue": "синий", "gold": "золотой", "silver": "серебряный", "iron": "железный",
    "stone": "каменный", "fire": "огненный", "ice": "ледяной", "shadow": "теневой",
    "night": "ночной", "death": "смерти", "blood": "крови", "storm": "бури",
    "of": "", "the": "", "and": "и",
    "mortal": "смертной", "form": "форме", "only": "только", "or": "или",
}
DAMAGE_RU = {
    "acid": "кислотой", "bludgeoning": "дробящего", "cold": "холодом",
    "fire": "огнём", "force": "силового поля", "lightning": "электричеством",
    "necrotic": "некротической энергией", "piercing": "колющего",
    "poison": "ядом", "psychic": "психической энергией", "radiant": "излучением",
    "slashing": "рубящего", "thunder": "звуком",
}
ALIGN_RU = {
    "lawful good": "законно-доброе", "neutral good": "нейтрально-доброе",
    "chaotic good": "хаотично-доброе", "lawful neutral": "законно-нейтральное",
    "neutral": "нейтральное", "true neutral": "нейтральное",
    "chaotic neutral": "хаотично-нейтральное", "lawful evil": "законно-злое",
    "neutral evil": "нейтрально-злое", "chaotic evil": "хаотично-злое",
    "unaligned": "без мировоззрения", "any alignment": "любое мировоззрение",
}
ABILITY = [("strength", "СИЛ"), ("dexterity", "ЛОВ"), ("constitution", "ТЕЛ"),
           ("intelligence", "ИНТ"), ("wisdom", "МУД"), ("charisma", "ХАР")]
SIZE_RU = {
    "tiny": ("Крошечный", "Крошечная", "Крошечное"),
    "small": ("Маленький", "Маленькая", "Маленькое"),
    "medium": ("Средний", "Средняя", "Среднее"),
    "large": ("Крупный", "Крупная", "Крупное"),
    "huge": ("Огромный", "Огромная", "Огромное"),
    "gargantuan": ("Гигантский", "Гигантская", "Гигантское"),
}
TYPE_GENDER = {
    "aberration": "f", "beast": "m", "celestial": "m", "construct": "m",
    "dragon": "m", "elemental": "m", "fey": "f", "fiend": "n", "giant": "m",
    "humanoid": "m", "monstrosity": "n", "ooze": "f", "plant": "n", "undead": "f",
}
WEAPON_CATEGORY_RU = {
    "simple melee weapons": "простое оружие ближнего боя",
    "simple ranged weapons": "простое оружие дальнего боя",
    "martial melee weapons": "боевое оружие ближнего боя",
    "martial ranged weapons": "боевое оружие дальнего боя",
}
WEAPON_PROPERTY_RU = {
    "ammunition": "боеприпас", "finesse": "фехтовальное", "heavy": "тяжёлое",
    "light": "лёгкое", "loading": "заряжаемое", "range": "дальнобойное",
    "reach": "досягаемое", "special": "особое", "thrown": "бросковое",
    "two-handed": "двуручное", "versatile": "универсальное",
}
COND_RU = {
    "blinded": "ослепление", "charmed": "очарование", "deafened": "глухота",
    "exhaustion": "истощение", "frightened": "испуг", "grappled": "захват",
    "incapacitated": "недееспособность", "invisible": "невидимость",
    "paralyzed": "паралич", "petrified": "окаменение", "poisoned": "отравление",
    "prone": "положение ничком", "restrained": "удержание", "stunned": "оглушение",
    "unconscious": "бессознательное состояние",
}

_TRANS = [
    ("sch", "ш"), ("shch", "щ"), ("ch", "ч"), ("sh", "ш"), ("zh", "ж"),
    ("kh", "х"), ("ts", "ц"), ("yu", "ю"), ("ya", "я"), ("ye", "е"),
    ("ph", "ф"), ("th", "т"), ("ck", "к"), ("qu", "кв"), ("x", "кс"),
    ("a", "а"), ("b", "б"), ("c", "к"), ("d", "д"), ("e", "е"), ("f", "ф"),
    ("g", "г"), ("h", "х"), ("i", "и"), ("j", "дж"), ("k", "к"), ("l", "л"),
    ("m", "м"), ("n", "н"), ("o", "о"), ("p", "п"), ("q", "к"), ("r", "р"),
    ("s", "с"), ("t", "т"), ("u", "у"), ("v", "в"), ("w", "в"), ("y", "й"),
    ("z", "з"),
]


def transliterate(word: str) -> str:
    out, i, lower = [], 0, word.lower()
    while i < len(lower):
        for src, dst in _TRANS:
            if lower.startswith(src, i):
                out.append(dst)
                i += len(src)
                break
        else:
            out.append(lower[i])
            i += 1
    text = "".join(out)
    return text[:1].upper() + text[1:] if text else text


def russian_name(name_en: str) -> str:
    alignment = ALIGN_RU.get(name_en.strip().lower())
    if alignment:
        return alignment[:1].upper() + alignment[1:]
    name = re.sub(r"\s+attack$", "", name_en.strip(), flags=re.I)
    tokens = re.findall(r"\+?\d+|[A-Za-z][A-Za-z'\-]*|\([^)]*\)", name)
    result: list[str] = []
    for token in tokens:
        if token.startswith("("):
            inner = token[1:-1]
            translated = " ".join(WORDS.get(w.lower(), "") or transliterate(w)
                                  for w in inner.split())
            result.append(f"({translated.lower()})")
        elif token[0].isdigit() or token.startswith("+"):
            result.append(token)
        elif "-" in token and not token[0].isupper():
            result.append(transliterate(token))
        else:
            known = WORDS.get(token.lower())
            result.append(known if known is not None else transliterate(token))
    text = " ".join(part for part in result if part).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:1].upper() + text[1:] if text else name_en


def _dice(expression: Any) -> str:
    return re.sub(r"(\d+)d(\d+)", r"\1к\2", str(expression))


def _num(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number == int(number) else str(number)


def _join(values: list[str]) -> str:
    return ", ".join(values)


_EMPTY_DESCRIPTIONS = {"", "false", "none", "null", "n/a", "no description", "[no description provided]"}


def _damage_value(value) -> str:
    """Translate a damage type, including qualified resistance strings."""
    s = str(value).lower().strip()
    if s in DAMAGE_RU:
        return DAMAGE_RU[s]
    suffix = ""
    for en_suffix, ru_suffix in (
        (" from nonmagical attacks not made with silvered weapons",
         " от немагических атак, совершённых не посеребрённым оружием"),
        (" from attacks not made with silvered weapons",
         " от атак, совершённых не посеребрённым оружием"),
        (" from nonmagical attacks", " от немагических атак"),
    ):
        if s.endswith(en_suffix):
            s = s[: -len(en_suffix)]
            suffix = ru_suffix
            break
    parts = [part.strip() for part in s.replace(" and ", ",").split(",") if part.strip()]
    translated = [DAMAGE_RU.get(part, part) for part in parts]
    return ", ".join(translated) + suffix


def _list_values(value) -> list:
    """Normalize a list-or-string mechanics field; drop upstream 'False' junk."""
    if not value:
        return []
    if isinstance(value, str):
        if value.strip().lower() in _EMPTY_DESCRIPTIONS:
            return []
        return [v.strip() for v in value.replace(";", ",").split(",") if v.strip()]
    return [v for v in value if str(v).strip().lower() not in _EMPTY_DESCRIPTIONS]


def _prose_empty(entity: Entity) -> bool:
    return entity.description.strip().lower() in _EMPTY_DESCRIPTIONS


def derived_description(entity: Entity) -> str | None:
    if not _prose_empty(entity):
        return None
    normalized = entity.mechanics.get("normalized") or {}
    source = entity.mechanics.get("source_data") or {}
    data = {**source, **{k: v for k, v in normalized.items() if v not in (None, "", [])}}
    category = entity.category

    if category == "monster":
        parts: list[str] = []
        raw_type = str(data.get("type") or data.get("category") or "").lower()
        gender_idx = {"m": 0, "f": 1, "n": 2}[TYPE_GENDER.get(raw_type, "m")]
        size_forms = SIZE_RU.get(str(data.get("size", "")).lower())
        size = size_forms[gender_idx] if size_forms else ""
        creature_type = WORDS.get(raw_type, str(data.get("type") or data.get("category") or ""))
        alignment = ALIGN_RU.get(str(data.get("alignment", "")).lower(), "")
        head = " ".join(part for part in [size, creature_type] if part)
        if head:
            parts.append(head[:1].upper() + head[1:] + (f", мировоззрение: {alignment}." if alignment else "."))
        if data.get("armor_class") is not None:
            detail = {"natural armor": "природный доспех"}.get(str(data.get("armor_detail", "")).lower(), "")
            parts.append(f"Класс доспеха: {_num(data['armor_class'])}" + (f" ({detail})" if detail else "") + ".")
        if data.get("hit_points") is not None:
            parts.append(f"Хиты: {_num(data['hit_points'])}"
                         + (f" ({_dice(data['hit_dice'])})" if data.get("hit_dice") else "") + ".")
        speeds = [("walk", "ходьба"), ("fly", "полёт"), ("swim", "плавание"),
                  ("climb", "лазание"), ("burrow", "рытьё")]
        speed_text = [f"{label} {_num(data[key])} фт." for key, label in speeds if data.get(key)]
        if speed_text:
            parts.append("Скорость: " + _join(speed_text) + ".")
        scores = [f"{abbr} {_num(data[f'ability_score_{key}'])}" for key, abbr in ABILITY
                  if data.get(f"ability_score_{key}") is not None]
        if scores:
            parts.append("Характеристики: " + _join(scores) + ".")
        for key, label in (("damage_vulnerabilities", "Уязвимость к урону"),
                           ("damage_resistances", "Сопротивление урону"),
                           ("damage_immunities", "Иммунитет к урону")):
            values = _list_values(data.get(key))
            if values:
                parts.append(f"{label}: " + _join([_damage_value(v) for v in values]) + ".")
        conditions = _list_values(data.get("condition_immunities"))
        if conditions:
            parts.append("Иммунитет к состояниям: " + _join([COND_RU.get(str(v).lower(), str(v)) for v in conditions]) + ".")
        senses: list[str] = []
        if data.get("darkvision_range"):
            senses.append(f"тёмное зрение {_num(data['darkvision_range'])} фт.")
        if data.get("blindsight_range"):
            senses.append(f"слепое зрение {_num(data['blindsight_range'])} фт.")
        if data.get("passive_perception") is not None:
            senses.append(f"пассивное Восприятие {_num(data['passive_perception'])}")
        if senses:
            parts.append("Чувства: " + _join(senses) + ".")
        if data.get("challenge_rating") is not None:
            parts.append(f"Показатель опасности: {_num(data['challenge_rating'])}.")
        subentities = entity.mechanics.get("subentities") or {}
        counts = [f"{label}: {len(subentities[key])}" for key, label in
                  (("traits", "особенностей"), ("actions", "действий"), ("attacks", "атак"))
                  if subentities.get(key)]
        if counts:
            parts.append("Структурированные механики записи: " + _join(counts) + ".")
        return " ".join(parts) if len(parts) >= 2 else None

    if category == "attack":
        kind = "Атака заклинанием" if str(data.get("attack_type", "")).upper() == "SPELL" else "Атака оружием"
        parts = [kind + (f": +{_num(data['to_hit_mod'])} к попаданию" if data.get("to_hit_mod") is not None else "") + "."]
        reach: list[str] = []
        if data.get("reach") is not None:
            reach.append(f"досягаемость {_num(data['reach'])} фт.")
        if data.get("range") is not None:
            reach.append(f"дистанция {_num(data['range'])}"
                           + (f"/{_num(data['long_range'])}" if data.get("long_range") else "") + " фт.")
        if reach:
            parts.append("Зона: " + _join(reach) + ", одна цель.")
        if data.get("damage_die_count") is not None and data.get("damage_die_type"):
            die = str(data["damage_die_type"]).lower().replace("d", "к")
            bonus = data.get("damage_bonus")
            bonus_text = f" + {_num(bonus)}" if bonus else ""
            damage = DAMAGE_RU.get(str(data.get("damage_type", "")).lower(), str(data.get("damage_type", "")))
            parts.append(f"Попадание: {_num(data['damage_die_count'])}{die}{bonus_text} {damage} урона.")
        if data.get("extra_damage_die_count") is not None and data.get("extra_damage_die_type"):
            die = str(data["extra_damage_die_type"]).lower().replace("d", "к")
            damage = DAMAGE_RU.get(str(data.get("extra_damage_type", "")).lower(), str(data.get("extra_damage_type", "")))
            parts.append(f"Дополнительный урон: {_num(data['extra_damage_die_count'])}{die} {damage}.")
        return " ".join(parts)

    if category == "weapon":
        parts = ["Оружие."]
        if data.get("damage_dice"):
            damage = DAMAGE_RU.get(str(data.get("damage_type", "")).lower(), str(data.get("damage_type", "")))
            parts.append(f"Урон: {_dice(data['damage_dice'])} {damage}.")
        if data.get("range") is not None:
            parts.append(f"Дистанция: {_num(data['range'])}"
                         + (f"/{_num(data['long_range'])}" if data.get("long_range") else "") + " фт.")
        weapon_category = WEAPON_CATEGORY_RU.get(str(data.get("category", "")).strip().lower())
        if weapon_category:
            parts.append(f"Категория: {weapon_category}.")
        properties = _list_values(data.get("properties"))
        if not properties and data.get("properties_json"):
            try:
                properties = _list_values(json.loads(str(data["properties_json"])))
            except (ValueError, TypeError):
                properties = []
        if properties:
            rendered = []
            for prop in properties:
                text = str(prop).strip()
                match = re.match(r"^(.+?)\s*\((.+)\)$", text)
                base = (match.group(1) if match else text).lower()
                label = WEAPON_PROPERTY_RU.get(base, base)
                if match:
                    detail = re.sub(r"^range\s+", "дистанция ", match.group(2))
                    rendered.append(f"{label} ({detail})")
                else:
                    rendered.append(label)
            parts.append("Свойства: " + _join(rendered) + ".")
        if data.get("cost"):
            parts.append(f"Стоимость: {str(data['cost']).replace(' gp', ' зм').replace(' sp', ' см').replace(' cp', ' мм')}.")
        if data.get("weight"):
            parts.append(f"Вес: {str(data['weight']).replace(' lb.', ' фнт').replace(' lb', ' фнт')}.")
        return " ".join(parts) if len(parts) > 1 else None

    if category == "armor":
        if data.get("ac_base") is not None:
            return f"Доспех. Базовый класс доспеха: {_num(data['ac_base'])}."
        return "Доспех (параметры приведены в структурированных механиках записи)."

    templates = {
        "size": "Обозначение размера существ в правилах 5e.",
        "item-rarity": "Редкость магических предметов в правилах 5e.",
        "item-category": "Категория предметов в правилах 5e.",
        "creature-set": "Набор существ в правилах 5e.",
        "reference": "Внешний раздел источника. Полный текст не копируется; ссылка и лицензия приведены в механиках записи.",
        "image": "Графический ресурс источника; описание приведено в механиках записи.",
        "feat": "Черта. Структурированные особенности и требования приведены в механиках записи.",
        "background": "Предыстория. Структурированные особенности приведены в механиках записи.",
        "skill": "Навык. Описание и связанная характеристика приведены в механиках записи.",
        "alignment": "Мировоззрение персонажей и существ в правилах 5e.",
        "creature-type": "Тип существ в правилах 5e.",
        "damage-type": "Тип урона в правилах 5e.",
        "condition": "Состояние в правилах 5e; полный текст приведён в связанных описаниях записи.",
        "class": "Класс персонажа. Структурированные механики, умения и подклассы приведены в механиках записи.",
    }
    if category in templates:
        return templates[category]
    return None


def apply_derived(entity: Entity) -> bool:
    """Attach a derived RU rendering for a record with no prose description."""
    if not _prose_empty(entity):
        return False
    existing = entity.translations.get("ru")
    if existing is not None and existing.description.strip():
        return False
    description = derived_description(entity)
    if not description:
        return False
    # A name-only memory match (empty RU description) must not block the
    # derived rendering; keep its RU name when it provides one.
    name = existing.name if existing is not None and existing.name.strip() else russian_name(entity.name)
    entity.translations["ru"] = Translation(
        name=name, description=description, status="machine",
        source_version=entity.version, glossary_version="derived-v1")
    entity.mechanics["translation_provenance"] = {
        "source": "derived-from-structured-mechanics",
        "license": entity.license,
        "attribution": "Derived from the record's own structured mechanics; machine rendering, review required",
        "edition": entity.edition,
        "exact_match": entity.name,
    }
    return True

