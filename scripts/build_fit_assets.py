"""Build the Fit character-viewer catalog and convert client UI/icons to PNG."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_gc as gc

ROOT = gc.ROOT
DUMP = gc.DDS_DIR
PUBLIC = ROOT / "public" / "fit"
SERVER_DATA = ROOT / "server" / "data"
CONTENT = gc.CONTENT
SKIP_DIRS = gc.SKIP_DIRS | {"migrators", "admin", "terrain", "tiles", "creatures", "npc", "pvp", "quests"}

FIELD_ASSIGN = re.compile(
    r"(Label|InventoryIcon|Icon|ActiveIcon|IconName|Quality|LabelType|Description|"
    r"WeaponSpeed|Damage|DefenseRating|CoolDown|ManaCostMod|MaxSkillLevel|RequiredLevel|"
    r"Duration|DurationInc|Attribute|Name)\s*=\s*("
    r'"(?:[^"\\]|\\.)*"'
    r"|[A-Za-z0-9_.\-'][\w.\-']*)\s*;",
)
CURVE_ENTRY = re.compile(
    r"\*\s*extends\s+CurveTableEntry\s*\{([^}]*)\}",
    re.S,
)
NAME_BEFORE = re.compile(r'Name\s*=\s*"((?:[^"\\]|\\.)*)"\s*;', re.S)
MOD_CHILD = re.compile(r"^Mod\d+$", re.I)

ATTR_LABEL = {
    "STRENGTH": "+ Strength",
    "AGILITY": "+ Agility",
    "ENDURANCE": "+ Endurance",
    "INTELLECT": "+ Intellect",
    "SPEEDMOD": "+ % Movement Speed",
    "SIZEMOD": "+ % Character Size",
    "BLOCK": "+ % Block",
    "DODGE": "+ Dodge",
    "ATTACK_RATING": "+ Attack Rating",
    "ATTACK_RATING_MOD": "+ % Attack Rating",
    "MELEE_ATTACK_RATING": "+ Melee Attack Rating",
    "MELEE_ATTACK_RATING_MOD": "+ % Melee Attack Rating",
    "RANGE_ATTACK_RATING": "+ Ranged Attack Rating",
    "RANGE_ATTACK_RATING_MOD": "+ % Ranged Attack Rating",
    "DEFENSE_RATING": "+ Defense Rating",
    "DEFENSE_RATING_MOD": "+ % Defense Rating",
    "DAMAGE": "+ Damage",
    "MELEE_DAMAGE": "+ Melee Damage",
    "RANGE_DAMAGE": "+ Ranged Damage",
    "CRUSHING_DAMAGE": "+ Crushing Damage",
    "PIERCING_DAMAGE": "+ Piercing Damage",
    "SLASHING_DAMAGE": "+ Slashing Damage",
    "FIRE_DAMAGE": "+ Fire Damage",
    "ICE_DAMAGE": "+ Ice Damage",
    "POISON_DAMAGE": "+ Poison Damage",
    "SHADOW_DAMAGE": "+ Shadow Damage",
    "DIVINE_DAMAGE": "+ Divine Damage",
    "FIRE_DAMAGE_BONUS": "+ Fire Damage",
    "ICE_DAMAGE_BONUS": "+ Ice Damage",
    "POISON_DAMAGE_BONUS": "+ Poison Damage",
    "SHADOW_DAMAGE_BONUS": "+ Shadow Damage",
    "DIVINE_DAMAGE_BONUS": "+ Divine Damage",
    "FIRE_RESIST": "+ Fire Resistance",
    "ICE_RESIST": "+ Ice Resistance",
    "POISON_RESIST": "+ Poison Resistance",
    "SHADOW_RESIST": "+ Shadow Resistance",
    "DIVINE_RESIST": "+ Divine Resistance",
    "FIRE_DAMAGE_RESIST": "+ Fire Resistance",
    "ICE_DAMAGE_RESIST": "+ Ice Resistance",
    "POISON_DAMAGE_RESIST": "+ Poison Resistance",
    "SHADOW_DAMAGE_RESIST": "+ Shadow Resistance",
    "DIVINE_DAMAGE_RESIST": "+ Divine Resistance",
    "MAX_HIT_POINTS": "+ Total Health",
    "MAX_HIT_POINT": "+ Total Health",
    "MAX_MANA": "+ Total Mana",
    "HIT_POINT_REGEN": "+ Health Regen",
    "MANA_REGEN": "+ Mana Regen",
    "MELEE_ATTACK_SPEED_MOD": "+ % Melee Attack Speed",
    "RANGE_ATTACK_SPEED_MOD": "+ % Ranged Attack Speed",
    "CAST_SPEED_MOD": "+ % Casting Speed",
    "MELEE_CRITICAL_CHANCE": "+ Melee Crit",
    "RANGE_CRITICAL_CHANCE": "+ Ranged Crit",
    "HIT_POINT_STEAL": "+ Health Steal",
    "MANA_STEAL": "+ Mana Steal",
    "MELEE_DAMAGE_REFLECT": "+ Melee Damage Reflection",
    "RANGE_DAMAGE_REFLECT": "+ Ranged Damage Reflection",
    "STUN_RESIST": "+ Stun Resist",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_classes(text: str) -> list[dict]:
    text = gc.strip_comments(text)
    classes: list[dict] = []

    def walk(body: str, prefix: str) -> None:
        pos = 0
        while True:
            m = gc.HEADER.search(body, pos)
            if not m:
                return
            name, parent = m.group(1), m.group(2)
            end = gc.matching_brace(body, m.end() - 1)
            inner = body[m.end() : end]
            pos = end + 1
            dotted = f"{prefix}.{name}" if prefix else name
            fields: dict[str, str] = {}
            curves: dict[str, dict[int, float]] = {}
            duration = None
            for kind, raw in FIELD_ASSIGN.findall(inner):
                val = gc.unquote_val(raw)
                if kind == "Name" and val:
                    fields.setdefault("_attr_name", val)
                elif kind == "Attribute":
                    fields["attribute"] = val
                elif kind == "Duration" and duration is None:
                    try:
                        duration = float(val)
                    except ValueError:
                        pass
                elif kind not in {"Name", "Attribute", "Duration", "DurationInc"}:
                    if kind not in fields or kind in {"Label", "InventoryIcon", "Icon", "ActiveIcon"}:
                        fields[kind] = val
            for match in CURVE_ENTRY.finditer(inner):
                block = match.group(1)
                lm = re.search(r"Level\s*=\s*(\d+)\s*;", block)
                vm = re.search(r"Value\s*=\s*(-?[\d.]+)\s*;", block)
                if not lm or not vm:
                    continue
                names = NAME_BEFORE.findall(inner[: match.start()])
                attr_name = names[-1] if names else (fields.get("_attr_name") or "Value")
                curves.setdefault(attr_name, {})[int(lm.group(1))] = float(vm.group(1))
            if duration is not None:
                fields["Duration"] = str(duration)
            mods = []
            child_pos = 0
            while True:
                cm = gc.HEADER.search(inner, child_pos)
                if not cm:
                    break
                cend = gc.matching_brace(inner, cm.end() - 1)
                child_pos = cend + 1
                child = cm.group(1)
                if MOD_CHILD.match(child):
                    mods.append(f"{dotted}.{child}")
            classes.append({
                "name": dotted,
                "short": name,
                "parent": parent,
                "fields": fields,
                "curves": curves,
                "mods": mods,
            })
            walk(inner, dotted)

    walk(text, "")
    return classes


def index_gc() -> dict[str, dict]:
    by_name: dict[str, dict] = {}
    parsed = 0
    for path in DUMP.rglob("*.gc"):
        if any(part.lower() in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "Label" not in text and "InventoryIcon" not in text and "Icon" not in text and "Attribute" not in text:
            continue
        parsed += 1
        rel = path.relative_to(DUMP).with_suffix("")
        file_key = str(rel).replace("\\", "/")
        file_prefix = ".".join(rel.parts)
        for cls in parse_classes(text):
            cls["file"] = file_key
            cls["file_prefix"] = file_prefix
            by_name[cls["name"]] = cls
            by_name.setdefault(cls["short"], cls)
            if cls["name"] == path.stem or cls["short"] == path.stem:
                by_name.setdefault(file_prefix, cls)
                if file_key.startswith("skills/"):
                    by_name[f"skills.{'.'.join(rel.parts[1:])}"] = cls
                    by_name[file_prefix] = cls
    log(f"Parsed {parsed} .gc files, {len(by_name)} keys")
    return by_name


def lookup(by_name: dict[str, dict], name: str | None) -> dict | None:
    if not name:
        return None
    hit = by_name.get(name)
    if hit:
        return hit
    return by_name.get(name.split(".")[-1])


def field(by_name: dict[str, dict], cls: dict | None, key: str) -> str | None:
    seen: set[str] = set()
    cur = cls
    while cur and cur["name"] not in seen:
        seen.add(cur["name"])
        val = cur["fields"].get(key)
        if val:
            return val
        cur = lookup(by_name, cur.get("parent"))
    return None


TOKEN_STATS = {
    "StrengthB": "+ Strength",
    "AgilityB": "+ Agility",
    "EnduranceB": "+ Endurance",
    "IntellectB": "+ Intellect",
    "SpeedM": "+ % Movement Speed",
    "SizeM": "+ % Character Size",
    "BlockM": "+ % Block",
    "MaxHitPointB": "+ Total Health",
    "MaxManaB": "+ Total Mana",
    "AttackRatingB": "+ Attack Rating",
    "AttackRatingM": "+ % Attack Rating",
    "MeleeAttackRatingB": "+ Melee Attack Rating",
    "MeleeAttackRatingM": "+ % Melee Attack Rating",
    "RangeAttackRatingB": "+ Ranged Attack Rating",
    "RangeAttackRatingM": "+ % Ranged Attack Rating",
    "DefenseRatingB": "+ Defense Rating",
    "DefenseRatingM": "+ % Defense Rating",
    "DamageB": "+ Damage",
    "MeleeDamageB": "+ Melee Damage",
    "RangeDamageB": "+ Ranged Damage",
    "FireDamageB": "+ Fire Damage",
    "IceDamageB": "+ Ice Damage",
    "PoisonDamageB": "+ Poison Damage",
    "ShadowDamageB": "+ Shadow Damage",
    "DivineDamageB": "+ Divine Damage",
    "FireResistB": "+ Fire Resistance",
    "IceResistB": "+ Ice Resistance",
    "PoisonResistB": "+ Poison Resistance",
    "ShadowResistB": "+ Shadow Resistance",
    "DivineResistB": "+ Divine Resistance",
    "MeleeDamageReflectB": "+ Melee Damage Reflection",
    "RangeDamageReflectB": "+ Ranged Damage Reflection",
    "MeleeAttackSpeedM": "+ % Melee Attack Speed",
    "RangeAttackSpeedM": "+ % Ranged Attack Speed",
    "CastSpeedM": "+ % Casting Speed",
    "StunResistM": "+ Stun Resist",
    "HitPointRegenB": "+ Health Regen",
    "ManaRegenB": "+ Mana Regen",
}


def stats_from_token(name: str | None) -> list[str]:
    if not name:
        return []
    short = name.split(".")[-1]
    out: list[str] = []
    for part in short.split("_"):
        label = TOKEN_STATS.get(part)
        if label and label not in out:
            out.append(label)
    return out


def collect_attributes(by_name: dict[str, dict], cls: dict | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    cur = cls
    hops = 0
    while cur and cur["name"] not in seen and hops < 12:
        seen.add(cur["name"])
        hops += 1
        attr = cur["fields"].get("attribute")
        if attr:
            label = ATTR_LABEL.get(attr.upper()) or ATTR_LABEL.get(attr)
            if not label:
                pretty = attr.replace("_", " ").title()
                if cur["name"].endswith("M") or attr.upper().endswith("MOD"):
                    label = f"+ % {pretty}"
                else:
                    label = f"+ {pretty}"
            if label not in out:
                out.append(label)
        for label in stats_from_token(cur.get("parent")) + stats_from_token(cur.get("name")):
            if label not in out:
                out.append(label)
        cur = lookup(by_name, cur.get("parent"))
    return out


def wiki_by_label() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in CONTENT.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        title = data.get("title") or ""
        if not title or title.startswith("Category:") or title.startswith("Talk:"):
            continue
        wiki_path = data.get("path") or f"/wiki/{path.stem}"
        out[gc.compact(title)] = wiki_path
        wt = data.get("wikiTitle") or ""
        if wt:
            out[gc.compact(wt.replace("_", " "))] = wiki_path
    return out


def icon_stem(raw: str | None) -> str | None:
    if not raw:
        return None
    stem = Path(str(raw).replace("\\", "/")).stem.strip()
    return stem or None


def convert_icon(src: Path, dest: Path, size: int = 64) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(src) as im:
            rgba = im.convert("RGBA")
            if max(rgba.size) > size:
                rgba.thumbnail((size, size), Image.Resampling.LANCZOS)
            rgba.save(dest, format="PNG", optimize=True)
        return dest.exists() and dest.stat().st_size > 24
    except OSError as exc:
        log(f"icon fail {src.name}: {exc}")
        return False


def save_png(im: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, format="PNG", optimize=True)


def crop_ui() -> None:
    ui_dir = PUBLIC / "ui"
    ui_dir.mkdir(parents=True, exist_ok=True)

    def open_dds(name: str) -> Image.Image:
        with Image.open(DUMP / name) as im:
            return im.convert("RGBA")

    ui2 = open_dds("InGameUI2.dds")
    ui3 = open_dds("InGameUI3.dds")
    ui4 = open_dds("InGameUI4.dds")
    ui5 = open_dds("IngameUI5.dds")
    plate = open_dds("Character_Nameplate.dds")

    save_png(ui2.crop((422, 29, 787, 297)), ui_dir / "equip.png")
    save_png(ui2.crop((26, 29, 393, 621)), ui_dir / "stats.png")
    save_png(ui3.crop((2, 954, 452, 1024)), ui_dir / "hotbar.png")
    save_png(ui5.crop((24, 24, 1000, 1000)), ui_dir / "frame.png")
    save_png(plate, ui_dir / "nameplate.png")
    # Dungeon Runners wordmark, bottom-left of UI4
    save_png(ui4.crop((18, 780, 430, 1010)), ui_dir / "logo.png")
    log(f"Wrote UI crops to {ui_dir}")


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    SERVER_DATA.mkdir(parents=True, exist_ok=True)
    crop_ui()

    by_name = index_gc()
    dds = gc.index_dds()
    wiki = wiki_by_label()
    icons_needed: set[str] = set()

    items: dict[str, dict] = {}
    skills: dict[str, dict] = {}
    mods: dict[str, dict] = {}

    seen_ids: set[int] = set()
    for cls in by_name.values():
        if id(cls) in seen_ids:
            continue
        seen_ids.add(id(cls))
        name = cls["name"]
        label = field(by_name, cls, "Label")
        icon = (
            field(by_name, cls, "InventoryIcon")
            or field(by_name, cls, "ActiveIcon")
            or field(by_name, cls, "Icon")
            or field(by_name, cls, "IconName")
        )
        quality = (field(by_name, cls, "Quality") or "").upper() or None
        label_type = (field(by_name, cls, "LabelType") or "").upper() or None
        desc = field(by_name, cls, "Description")
        stats = collect_attributes(by_name, cls)

        file_key = str(cls.get("file") or "")
        is_skill = file_key.startswith("skills/") and cls.get("short") == Path(file_key).stem
        is_mod = ".Mod" in name and re.search(r"\.Mod\d+$", name)
        has_item_icon = bool(field(by_name, cls, "InventoryIcon") or (label and icon and not is_skill))

        if is_mod:
            mods[name] = {
                "label": label if label and label not in {"NONE", "PREFIX", "SUFFIX"} else None,
                "labelType": label_type,
                "quality": quality,
                "stats": stats,
            }
            parent_stats = stats
            if not parent_stats:
                parent = lookup(by_name, cls.get("parent"))
                parent_stats = collect_attributes(by_name, parent)
                if parent_stats:
                    mods[name]["stats"] = parent_stats
            continue

        if is_skill and (label or icon):
            curves = dict(cls.get("curves") or {})
            cur = cls
            hops = 0
            seen = set()
            while cur and cur["name"] not in seen and hops < 8:
                seen.add(cur["name"])
                hops += 1
                for k, v in (cur.get("curves") or {}).items():
                    curves.setdefault(k, v)
                cur = lookup(by_name, cur.get("parent"))
            duration = field(by_name, cls, "Duration")
            values = {k: {str(lvl): val for lvl, val in table.items()} for k, table in curves.items()}
            if duration:
                values.setdefault("Duration", {"1": float(duration)})
            stem = icon_stem(field(by_name, cls, "ActiveIcon") or field(by_name, cls, "Icon") or icon)
            if stem:
                icons_needed.add(stem)
            skill_def = f"skills.{'.'.join(Path(file_key).parts[1:])}".replace("/", ".")
            row = {
                "label": label or Path(file_key).stem,
                "description": desc,
                "icon": stem,
                "cooldown": _num(field(by_name, cls, "CoolDown")),
                "mana": _num(field(by_name, cls, "ManaCostMod")),
                "maxLevel": _int(field(by_name, cls, "MaxSkillLevel")),
                "values": values,
            }
            skills[skill_def] = row
            skills[f"skills.generic.{Path(file_key).stem}"] = row
            continue

        if label and label not in {"NONE", "PREFIX", "SUFFIX"} and has_item_icon:
            stem = icon_stem(icon)
            if stem:
                icons_needed.add(stem)
            baked = []
            for mod_name in cls.get("mods") or []:
                baked.append(mod_name)
            wiki_path = wiki.get(gc.compact(label))
            items[name] = {
                "label": label,
                "icon": stem,
                "quality": quality,
                "damage": field(by_name, cls, "Damage"),
                "speed": field(by_name, cls, "WeaponSpeed"),
                "defense": field(by_name, cls, "DefenseRating"),
                "wiki": wiki_path,
                "bakedMods": baked,
            }

    icon_dir = PUBLIC / "icons"
    icon_dir.mkdir(parents=True, exist_ok=True)
    converted = 0
    missing = 0
    for stem in sorted(icons_needed):
        dest = icon_dir / f"{stem}.png"
        dds_name = gc.find_dds(stem, dds)
        if not dds_name:
            for alt in (f"{stem}_on", f"{stem}_On", stem.replace("_On", "_on"), stem.replace("_on", "_On")):
                dds_name = gc.find_dds(alt, dds)
                if dds_name:
                    break
        if not dds_name:
            missing += 1
            continue
        if dest.exists() and dest.stat().st_size > 24:
            converted += 1
            continue
        if convert_icon(DUMP / dds_name, dest):
            converted += 1
        else:
            missing += 1

    catalog = {"items": items, "skills": skills, "mods": mods}
    payload = json.dumps(catalog, separators=(",", ":"), ensure_ascii=False)
    (SERVER_DATA / "fit-catalog.json").write_text(payload, encoding="utf-8")
    log(
        f"Catalog: {len(items)} items, {len(skills)} skills, {len(mods)} mods, "
        f"{converted} icons, {missing} missing, {len(payload)} bytes"
    )


def _num(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _int(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


if __name__ == "__main__":
    main()
