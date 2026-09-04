"""Build mythic-suffix page + missing rainbow stubs from client MythicPAL files."""
from __future__ import annotations

import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_gc as gc

DUMP = gc.DDS_DIR
CONTENT = gc.CONTENT
SKIP_LABELS = {
    "of the",
    "NONE",
    "PREFIX",
    "SUFFIX",
    "NEEDS ENTRY",
    "",
}
# Split comments on `_` then strip trailing B/M. RangeDamageB → rangedamage.
COMMENT_TOKENS = {
    "strength": "STR",
    "agility": "AGI",
    "endurance": "END",
    "intellect": "INT",
    "attackrating": "Attack rating",
    "meleeattackrating": "Melee AR",
    "rangeattackrating": "Ranged AR",
    "defenserating": "Defense",
    "meleedamage": "+Melee damage",
    "rangedamage": "+Ranged",
    "rangeddamage": "+Ranged",
    "crushingdamage": "+Crushing",
    "piercingdamage": "+Piercing",
    "slashingdamage": "+Slashing",
    "firedamage": "+Fire",
    "icedamage": "+Ice",
    "divinedamage": "+Divine",
    "shadowdamage": "+Shadow",
    "poisondamage": "+Poison",
    "fireweapondamage": "+Fire",
    "iceweapondamage": "+Ice",
    "divineweapondamage": "+Divine",
    "shadowweapondamage": "+Shadow",
    "poisonweapondamage": "+Poison",
    "fireresist": "Fire resist",
    "iceresist": "Ice resist",
    "divineresist": "Divine resist",
    "shadowresist": "Shadow resist",
    "poisonresist": "Poison resist",
    "firedamageresist": "Fire resist",
    "icedamageresist": "Ice resist",
    "divinedamageresist": "Divine resist",
    "shadowdamageresist": "Shadow resist",
    "poisondamageresist": "Poison resist",
    "healthregen": "Health regen",
    "manaregen": "Mana regen",
    "hitpointregen": "Health regen",
    "speed": "Speed",
    "castspeed": "Cast speed",
    "size": "Character size",
    "damage": "Damage",
    "stun": "Stun",
    "stunresist": "Stun resist",
    "maxhitpoint": "Max health",
    "maxmana": "Max mana",
    "meleeattackspeed": "Melee attack speed",
    "rangeattackspeed": "Ranged attack speed",
    "meleecriticalchance": "Melee crit",
    "rangecriticalchance": "Ranged crit",
    "block": "Block",
    "hitpointsteal": "Health steal",
    "manasteal": "Mana steal",
    "meleedamagereflect": "Melee reflect",
    "rangedamagereflect": "Ranged reflect",
}
NEVER_LIVE_LEATHER_NINJA = {
    "Shadow Shozoko",
    "Tabi-lous",
    "Shadow Shawl",
    "Gauntlets of Silent Destruction",
    "Shaded Eyes",
}
CLOTH_NINJA = {
    "Shadow Shozoko",
    "Tabi-lous",
    "Shadow Shawl",
    "Gloves of Silent Destruction",
    "Shaded Eyes",
}
DESC_FLAVOR_RE = re.compile(
    r'Description\s*=\s*"((?:[^"\\]|\\.)*)"',
)
FILE_CLASS = {
    "PlateMythicPAL": ("Fighter", "Plate"),
    "ScaleMythicPAL": ("Fighter", "Scale"),
    "CrystalMythicPAL": ("Fighter", "Crystal"),
    "LeatherMythicPAL": ("Ranger", "Leather"),
    "ChainMythicPAL": ("Ranger", "Chain"),
    "SplintMythicPAL": ("Ranger", "Splint"),
    "RingMythicPAL": ("", "Ring"),
    "AmuletMythicPAL": ("", "Amulet"),
    "1HSwordMythicPAL": ("Fighter", "1H Sword"),
    "2HSwordMythicPAL": ("Fighter", "2H Sword"),
    "1HAxeMythicPAL": ("Fighter", "1H Axe"),
    "2HAxeMythicPAL": ("Fighter", "2H Axe"),
    "1HMaceMythicPAL": ("Fighter", "1H Mace"),
    "2HMaceMythicPAL": ("Fighter", "2H Mace"),
    "1HPickMythicPAL": ("Fighter", "1H Pick"),
    "2HPickMythicPAL": ("Fighter", "2H Pick"),
    "1HStaffMythicPAL": ("Mage", "1H Staff"),
    "2HStaffMythicPAL": ("Mage", "2H Staff"),
    "1HGunMythicPAL": ("Ranger", "1H Gun"),
    "2HGunMythicPAL": ("Ranger", "2H Gun"),
    "2HCrossbowMythicPAL": ("Ranger", "2H Crossbow"),
    "2HCannonMythicPAL": ("Ranger", "2H Cannon"),
}
WEAPON_CAT = {
    "1H Sword": "One-Handed-Fighter-Rainbows",
    "1H Axe": "One-Handed-Fighter-Rainbows",
    "1H Mace": "One-Handed-Fighter-Rainbows",
    "1H Pick": "One-Handed-Fighter-Rainbows",
    "2H Sword": "Two-Handed-Fighter-Rainbows",
    "2H Axe": "Two-Handed-Fighter-Rainbows",
    "2H Mace": "Two-Handed-Fighter-Rainbows",
    "2H Pick": "Two-Handed-Fighter-Rainbows",
    "1H Staff": "One-Handed-Mage-Rainbows",
    "2H Staff": "Two-Handed-Mage-Rainbows",
    "1H Gun": "One-Handed-Ranger-Rainbows",
    "2H Gun": "Two-Handed-Ranger-Rainbows",
    "2H Crossbow": "Two-Handed-Ranger-Rainbows",
    "2H Cannon": "Two-Handed-Ranger-Rainbows",
}
SLOT_CAT = {
    "Body": "Rainbow Body Armor",
    "Helm": "Rainbow Helms",
    "Gloves": "Rainbow Gloves",
    "Boots": "Rainbow Boots",
    "Shoulders": "Rainbow Shoulders",
    "Shield": "Rainbow Shields",
    "Ring": "Rainbow Rings",
    "Amulet": "Rainbow Amulets",
}
CLASS_ARMOR_CAT = {
    "Fighter": "Fighter Rainbow Armor",
    "Ranger": "Ranger Rainbow Armor",
    "Mage": "Mage Rainbow Armor",
}
ENTRY_RE = re.compile(
    r"(?P<name>[A-Za-z0-9_]+)\s+extends\s+(?P<ext>[\w.]+)\s*(?P<comment>//[^\n]*)?\s*\{(?P<body>[\s\S]*?)\n\t\}",
)
DESC_LABEL_RE = re.compile(
    r"Description\s*\{[\s\S]*?Label\s*=\s*\"((?:[^\"\\]|\\.)*)\"",
)
MOD_EXT_RE = re.compile(r"Mod\d+\s+extends\s+([\w.]+)(?:\s*//([^\n]*))?")
LABEL_TYPE_RE = re.compile(r"LabelType\s*=\s*(\w+)")
QUAL_RE = re.compile(r"Quality\s*=\s*(\w+)")
LABEL_RE = re.compile(r'Label\s*=\s*"((?:[^"\\]|\\.)*)"')


def stats_from_comment(comment: str) -> str:
    text = (comment or "").strip()
    if not text:
        return ""
    if "proc" in text.lower():
        return re.sub(r"\s+", " ", text)
    parts = []
    for raw in text.split("_"):
        token = raw.strip()
        if token.endswith(("B", "M")) and len(token) > 1:
            token = token[:-1]
        mapped = COMMENT_TOKENS.get(token.lower())
        if mapped and mapped not in parts:
            parts.append(mapped)
    return ", ".join(parts)


def stats_from_name(name: str) -> str:
    return stats_from_comment(name.split(".")[-1])


def slot_from_entry(entry: str, kind: str) -> str:
    low = entry.lower()
    for word, slot in (
        ("armor", "Body"),
        ("body", "Body"),
        ("helm", "Helm"),
        ("glove", "Gloves"),
        ("boot", "Boots"),
        ("shoulder", "Shoulders"),
        ("shield", "Shield"),
        ("ring", "Ring"),
        ("amulet", "Amulet"),
    ):
        if word in low:
            return slot
    if "Sword" in kind or "Axe" in kind or "Mace" in kind or "Pick" in kind or "Staff" in kind or "Gun" in kind or "Crossbow" in kind or "Cannon" in kind:
        return "Weapon"
    return ""


def wiki_index() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in CONTENT.rglob("*.json"):
        if "Category" in path.parts:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title") or ""
        if title.startswith("Category:"):
            continue
        out[gc.compact(title)] = title
        out[gc.compact(data.get("wikiTitle") or title)] = title
    for src, dest in gc.ALIASES.items():
        if dest in out:
            out[src] = out[dest]
        if src in out:
            out[dest] = out[src]
    return out


def extract_suffixes() -> dict[str, list[tuple[str, str, str]]]:
    """pool -> [(label, kind, stats)]"""
    files = {
        "Weapons": DUMP / "items" / "modpal" / "WeaponMythicModPAL.gc",
        "Fighter armor": DUMP / "items" / "modpal" / "FighterModPAL.gc",
        "Ranger armor": DUMP / "items" / "modpal" / "RangerModPAL.gc",
        "Mage armor": DUMP / "items" / "modpal" / "MageModPAL.gc",
        "Rings": DUMP / "RingCraftedModPAL.gc",
        "Amulets": DUMP / "AmuletCraftedModPAL.gc",
        "Jewelry prefixes": DUMP / "AmuletModPAL.gc",
        "Ring prefixes": DUMP / "RingModPAL.gc",
    }
    pools: dict[str, list[tuple[str, str, str]]] = {}
    for pool, path in files.items():
        text = path.read_text(encoding="utf-8", errors="ignore")
        rows = []
        for block in re.finditer(
            r"extends\s+([\w.]+)[^\n]*\n\s*\{([\s\S]*?)\n\s*\}",
            text,
        ):
            inner = block.group(2)
            label_m = LABEL_RE.search(inner)
            type_m = LABEL_TYPE_RE.search(inner)
            qual_m = QUAL_RE.search(inner)
            if not label_m or not type_m or not qual_m:
                continue
            if qual_m.group(1).upper() != "MYTHIC":
                continue
            if type_m.group(1) not in {"PREFIX", "POSTFIX"}:
                continue
            label = label_m.group(1)
            if label in SKIP_LABELS:
                continue
            rows.append((label, type_m.group(1), stats_from_name(block.group(1))))
        # keep first occurrence of each label
        seen = set()
        uniq = []
        for row in rows:
            key = row[0]
            if key in seen:
                continue
            seen.add(key)
            uniq.append(row)
        if uniq:
            pools[pool] = uniq
    return pools


def parse_mythic_pal(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    stem = path.stem
    klass, kind = FILE_CLASS.get(stem, ("", stem.replace("MythicPAL", "")))
    items = []
    for match in ENTRY_RE.finditer(text):
        body = match.group("body")
        label_m = DESC_LABEL_RE.search(body)
        if not label_m:
            continue
        label = label_m.group(1)
        if label in SKIP_LABELS:
            continue
        deprecated = "DEPRECATED" in (match.group("comment") or "")
        ahead = text[max(0, match.start() - 220) : match.start()]
        if "DEPRECATED" in ahead:
            deprecated = True
        never_live = "NEVER WENT LIVE" in ahead or "NEVER WENT LIVE" in (match.group("comment") or "")
        wishing = "WISHING WELL" in ahead.upper() or "WISHING WELL" in (match.group("comment") or "").upper()
        soulbound = bool(re.search(r"SoulBound\s*=\s*true", body, re.I))
        flavors = []
        for flav in DESC_FLAVOR_RE.finditer(body):
            raw = flav.group(1)
            raw = re.sub(r"<[^>]+>", "", raw)
            raw = raw.replace("&nbsp;", " ").strip()
            if raw:
                flavors.append(raw)
        mods = []
        for ext_m in MOD_EXT_RE.finditer(body):
            comment = (ext_m.group(2) or "").strip()
            stats = stats_from_comment(comment) or stats_from_name(ext_m.group(1))
            # skip visual-only mounted FX with no enhancement comment
            if not stats:
                continue
            mods.append(stats)
        items.append({
            "label": label,
            "file": path.name,
            "entry": match.group("name"),
            "class": klass,
            "kind": kind,
            "slot": slot_from_entry(match.group("name"), kind),
            "mods": mods,
            "deprecated": deprecated,
            "never_live": never_live,
            "wishing": wishing,
            "soulbound": soulbound,
            "flavors": flavors,
        })
    return items


PLAYER_STAT = {
    "STR": "+ Strength",
    "AGI": "+ Agility",
    "END": "+ Endurance",
    "INT": "+ Intellect",
    "+Melee damage": "+ Melee Damage",
    "+Ranged": "+ Ranged Damage",
    "+Crushing": "+ Crushing Damage",
    "+Piercing": "+ Piercing Damage",
    "+Slashing": "+ Slashing Damage",
    "+Fire": "+ Fire Damage",
    "+Ice": "+ Ice Damage",
    "+Divine": "+ Divine Damage",
    "+Shadow": "+ Shadow Damage",
    "+Poison": "+ Poison Damage",
    "Fire resist": "+ Fire Damage Resistance",
    "Ice resist": "+ Ice Damage Resistance",
    "Divine resist": "+ Divine Damage Resistance",
    "Shadow resist": "+ Shadow Damage Resistance",
    "Poison resist": "+ Poison Damage Resistance",
    "Health regen": "+ Health Regeneration",
    "Mana regen": "+ Mana Regeneration",
    "Speed": "+ % Movement Speed",
    "Cast speed": "+ % Casting Speed",
    "Character size": "+ % Character Size",
    "Damage": "+ Damage",
    "Stun": "+ % Enemy Stun Chance",
    "Stun resist": "+ % Stun Resistance",
    "Max health": "+ Total Health",
    "Max mana": "+ Total Mana",
    "Melee attack speed": "+ % Melee Attack Speed",
    "Ranged attack speed": "+ % Ranged Attack Speed",
    "Melee crit": "+ % Melee Critical Chance",
    "Ranged crit": "+ % Ranged Critical Chance",
    "Block": "+ Block",
    "Health steal": "+ Health Steal",
    "Mana steal": "+ Mana Steal",
    "Melee reflect": "+ Melee Damage Reflection",
    "Ranged reflect": "+ Ranged Damage Reflection",
    "Attack rating": "+ Attack Rating",
    "Melee AR": "+ Melee Attack Rating",
    "Ranged AR": "+ Ranged Attack Rating",
    "Defense": "+ Defense Rating",
}
KIND_PHRASE = {
    "1H Sword": "one-handed sword",
    "2H Sword": "two-handed sword",
    "1H Axe": "one-handed axe",
    "2H Axe": "two-handed axe",
    "1H Mace": "one-handed mace",
    "2H Mace": "two-handed mace",
    "1H Pick": "one-handed pick",
    "2H Pick": "two-handed pick",
    "1H Staff": "one-handed staff",
    "2H Staff": "two-handed staff",
    "1H Gun": "one-handed gun",
    "2H Gun": "two-handed gun",
    "2H Crossbow": "two-handed crossbow",
    "2H Cannon": "two-handed cannon",
    "Plate": "plate",
    "Scale": "scale",
    "Crystal": "crystal",
    "Leather": "leather",
    "Chain": "chain",
    "Splint": "splint",
    "Ring": "ring",
    "Amulet": "amulet",
}


def player_stat_lines(raw: str) -> list[str]:
    if not raw:
        return []
    lines = []
    for part in re.split(r"\s*,\s*", raw):
        part = part.strip()
        if not part:
            continue
        lines.append(PLAYER_STAT.get(part, part if part.startswith("+") else f"+ {part}"))
    return lines


def suffix_page_html(pools: dict[str, list[tuple[str, str, str]]]) -> str:
    parts = [
        "<p>Rainbow items keep a <b>fixed base name</b>. A rolled copy can also pick up "
        "one of these joke endings. The same ending always means the same bonus on that "
        "kind of gear. <i>Brilliance (Do Not Remove Label)</i> is just Brilliance plus "
        "the fighter-armor ending.</p>",
        "<p>See <a href=\"/wiki/Modifiers\" title=\"Modifiers\">Modifiers</a> for how "
        "ordinary green / blue / yellow / purple names are stacked, and "
        "<a href=\"/wiki/Name_Descriptors\" title=\"Name Descriptors\">Name Descriptors</a> "
        "for the Superior last word.</p>",
        '<table class="toc" id="toc" summary="Contents"><tr><td><div id="toctitle">'
        "<h2>Contents</h2></div><ul>",
    ]
    for pool in pools:
        anchor = re.sub(r"[^A-Za-z0-9]+", "_", pool)
        parts.append(
            f'<li class="toclevel-1"><a href="#{anchor}"><span class="toctext">'
            f"{html.escape(pool)}</span></a></li>"
        )
    parts.append("</ul></td></tr></table>")
    for pool, rows in pools.items():
        anchor = re.sub(r"[^A-Za-z0-9]+", "_", pool)
        parts.append(f'<a name="{anchor}"></a><h2> <span class="mw-headline">{html.escape(pool)}</span></h2>')
        parts.append('<table class="wiki-mod-table">')
        parts.append("<tr><th>Name ending</th><th>Where it sits</th><th>Bonus</th></tr>")
        for label, kind, stats in rows:
            where = "in front of the name" if kind.upper() == "PREFIX" else "after the name"
            bonus = ", ".join(player_stat_lines(stats)) or "—"
            parts.append(
                f"<tr><td>{html.escape(label)}</td>"
                f"<td>{where}</td><td>{html.escape(bonus)}</td></tr>"
            )
        parts.append("</table>")
    parts.append('<div class="visualClear"></div>')
    return "\n".join(parts)


def rainbow_html(item: dict) -> str:
    title = html.escape(item["label"])
    kind = item.get("kind") or ""
    klass = item.get("class") or ""
    slot = item.get("slot") or ""
    phrase = KIND_PHRASE.get(kind, kind.lower() if kind else "")
    if not phrase or phrase in {"cloth", "ghost", "padded", "rubber", "leather", "chain", "splint", "scale", "plate", "crystal"}:
        if slot and slot != "Weapon":
            phrase = slot.lower()
        elif not phrase:
            phrase = "rainbow item"
    who = f"{klass.lower()} " if klass else ""
    rows = []
    if slot and slot != "Weapon":
        rows.append(("Piece", slot))
    elif slot == "Weapon" or kind in KIND_PHRASE:
        rows.append(("Piece", "Weapon"))
        pretty_kind = " ".join(w.capitalize() if w.lower() not in {"of", "the"} else w for w in phrase.split())
        rows.append(("Type", pretty_kind.title() if pretty_kind == pretty_kind.lower() else pretty_kind))
    if klass:
        rows.append(("Class", klass))
    if slot and slot != "Weapon":
        rows.append(("Defense Rating", "varies with item level"))
    else:
        rows.append(("Damage", "varies with item level"))
    infobox = [
        '<table align="right" cellpadding="2" cellspacing="0" style="text-align:left; background:rgb(240,240,240); border:1px solid black; width:25%;">',
        f'<tr><td colspan="2" style="text-align:center; background:#9999FF; font-size:150%;"> {title}\n</td></tr>',
        "<tr><td colspan=\"2\"><hr/>\n</td></tr>",
    ]
    for key, val in rows:
        infobox.append(
            f'<tr><td style="width:50%;" valign="top"><b>{html.escape(key)}:&nbsp;</b>\n</td>'
            f'<td style="width:50%;" valign="top">{html.escape(val)}\n</td></tr>'
        )
    infobox.append("</table>")
    article = f"{who}{phrase}".strip()
    copula = "are" if phrase in {"gloves", "boots", "shoulders"} else "is a"
    body = [
        f"<p><b>{title}</b> {copula} {html.escape(article)}.</p>",
        "<p>It is unknown how many different varieties of this particular mythic item exist. "
        "Some of the Mythic items in this series may have the <b>same</b> name but "
        "<b>different</b> attributes.</p>",
    ]
    notes = []
    if item.get("wishing"):
        notes.append("This one came from the Wishing Well.")
    if item.get("soulbound"):
        notes.append("This item is soulbound.")
    if item.get("never_live"):
        notes.append("This name never dropped on the live servers.")
    if item.get("deprecated"):
        notes.append("This name was pulled from later loot tables.")
    for flav in item.get("flavors") or []:
        notes.append(html.escape(flav))
    if notes:
        body.append("<p>" + " ".join(notes) + "</p>")
    body.append('<a name="Attributes:"></a><h2> <span class="mw-headline"> Attributes: </span></h2>')
    if item["mods"]:
        body.append("<p>The base item always carries:</p>")
        body.append("<ul>")
        seen = set()
        for mod in item["mods"]:
            for line in player_stat_lines(mod):
                if line in seen:
                    continue
                seen.add(line)
                body.append(f"<li> {html.escape(line)}\n</li>")
        body.append("</ul>")
    else:
        body.append("<p>No fixed bonuses are known beyond the rainbow name itself.</p>")
    body.append(
        "<p>Rolled copies can also pick up an extra ending. Those endings and their "
        'bonuses are listed on <a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">'
        "Mythic Suffixes</a>.</p>"
    )
    body.append('<div class="visualClear"></div>')
    return "\n".join(infobox) + "\n" + "\n".join(body)


def categories_for(item: dict) -> list[str]:
    cats = ["Rainbow items"]
    slot_cat = SLOT_CAT.get(item["slot"])
    if slot_cat:
        cats.append(slot_cat)
    if item["slot"] in {"Body", "Helm", "Gloves", "Boots", "Shoulders", "Shield"}:
        armor_cat = CLASS_ARMOR_CAT.get(item["class"])
        if armor_cat:
            cats.append(armor_cat)
    weapon_cat = WEAPON_CAT.get(item["kind"])
    if weapon_cat:
        cats.append(weapon_cat)
    return cats


def wiki_slug(label: str) -> str:
    return label.replace(" ", "_").replace("/", "_").replace("\\", "_")


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    pools = extract_suffixes()
    write_json(CONTENT / "Mythic_Suffixes.json", {
        "title": "Mythic Suffixes",
        "wikiTitle": "Mythic_Suffixes",
        "path": "/wiki/Mythic_Suffixes",
        "description": "Mythic Suffixes — The Townstons wiki",
        "categories": ["Glossary", "Items", "Rainbow items", "Game Mechanics"],
        "images": [],
        "html": suffix_page_html(pools),
        "source": "dungeon-runners-client",
    })
    print("wrote Mythic_Suffixes")
    for pool, rows in pools.items():
        print(f"  {pool}: {len(rows)} labels")

    existing = wiki_index()
    created = []
    updated = []
    skipped = []
    for path in sorted(DUMP.glob("*MythicPAL.gc")):
        for item in parse_mythic_pal(path):
            label = item["label"].strip()
            if not label or label.endswith(" of") or label.endswith(" of "):
                skipped.append((item["label"], "", "incomplete label"))
                continue
            if item.get("never_live") and label in NEVER_LIVE_LEATHER_NINJA:
                skipped.append((label, "", "never-live leather ninja"))
                continue
            if label in CLOTH_NINJA:
                skipped.append((label, "", "cloth ninja already written from Mage PAL"))
                continue
            key = gc.compact(label)
            bare = gc.compact(re.sub(r"\s*\([^)]*\)\s*$", "", label))
            dest = CONTENT / f"{wiki_slug(item['label'])}.json"
            payload = {
                "title": item["label"],
                "wikiTitle": wiki_slug(item["label"]),
                "path": f"/wiki/{wiki_slug(item['label'])}",
                "description": f"{item['label']} — The Townstons wiki",
                "categories": categories_for(item),
                "images": [],
                "html": rainbow_html(item),
                "source": "dungeon-runners-client",
            }
            if dest.exists():
                old = json.loads(dest.read_text(encoding="utf-8"))
                if old.get("source") == "dungeon-runners-client":
                    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    updated.append(label)
                else:
                    skipped.append((label, dest.name, "exists richer page"))
                continue
            if key in existing or (bare and bare in existing):
                skipped.append((label, existing.get(key) or existing.get(bare, ""), "exists"))
                continue
            write_json(dest, payload)
            created.append(item["label"])
            existing[key] = item["label"]

    report = CONTENT.parent.parent / "archive" / "new-rainbows.txt"
    report.parent.mkdir(exist_ok=True)
    if created:
        report.write_text("\n".join(created) + "\n", encoding="utf-8")
    print(f"created {len(created)} rainbow pages")
    for title in created:
        print(f"  + {title}")
    print(f"updated {len(updated)} stubs")
    print(f"skipped {len(skipped)}")


if __name__ == "__main__":
    main()
