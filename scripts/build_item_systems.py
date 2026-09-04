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


def suffix_page_html(pools: dict[str, list[tuple[str, str, str]]]) -> str:
    parts = [
        "<p>Rainbow (mythic) items have a <b>fixed base name</b>. "
        "When the client rolls a mythic, it can also attach one of these "
        "<b>name endings</b>. The ending is a real modifier: the same word always "
        "comes from the same stat bonus in that pool.</p>",
        "<p>Existing wiki pages that list “Brilliance (Do Not Remove Label)” are "
        "the base name plus one of these endings. This page is the full client list, "
        "grouped by the ModPAL that owns it. Placeholders labeled NEEDS ENTRY in the "
        "dump are omitted.</p>",
        "<p>See <a href=\"/wiki/Modifiers\" title=\"Modifiers\">Modifiers</a> for how "
        "names are stacked, and a rainbow item page for that item’s fixed base mods.</p>",
    ]
    for pool, rows in pools.items():
        anchor = re.sub(r"[^A-Za-z0-9]+", "_", pool)
        parts.append(f'<a name="{anchor}"></a><h2> <span class="mw-headline">{html.escape(pool)}</span></h2>')
        parts.append("<ul>")
        for label, kind, stats in rows:
            extra = f" — {html.escape(stats)}" if stats else ""
            parts.append(f"<li> {html.escape(label)} <i>({kind.lower()})</i>{extra}\n</li>")
        parts.append("</ul>")
    parts.append("<p><i>Labels and stats come from the client ModPAL files listed above.</i></p>")
    parts.append('<div class="visualClear"></div>')
    return "\n".join(parts)


def rainbow_html(item: dict) -> str:
    title = html.escape(item["label"])
    rows = []
    if item["slot"] and item["slot"] != "Weapon":
        rows.append(("Piece", item["slot"]))
    if item["kind"]:
        rows.append(("Client type", item["kind"]))
    if item["class"]:
        rows.append(("Class palette", item["class"]))
    rows.append(("Quality", "Mythic (rainbow)"))
    infobox = [
        '<table align="right" cellpadding="2" cellspacing="0" style="text-align:left; background:rgb(240,240,240); border:1px solid black; width:25%;">',
        f'<tr><td colspan="2" style="text-align:center; background:#9999FF; font-size:150%;"> {title}\n</td></tr>',
        "<tr><td colspan=\"2\"><hr/>\n</td></tr>",
    ]
    for key, val in rows:
        infobox.append(
            f'<tr><td style="width:50%;"><b>{html.escape(key)}:&nbsp;</b>\n</td>'
            f'<td style="width:50%;">{html.escape(val)}\n</td></tr>'
        )
    infobox.append("</table>")
    body = [
        f"<p><b>{title}</b> is a named mythic item from the client file "
        f"<code>{html.escape(item['file'])}</code> ({html.escape(item['entry'])}).</p>",
        "<p>This is the <b>base name</b>. Rolled mythics can also append a suffix "
        'from <a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">Mythic Suffixes</a>. '
        "Those endings change the last part of the name and add the bonus listed on that page. "
        "This page does not invent extra roll combinations.</p>",
    ]
    notes = []
    if item.get("wishing"):
        notes.append("The client marks this entry as wishing-well only.")
    if item.get("soulbound"):
        notes.append("The template sets <code>SoulBound = true</code>.")
    if item.get("never_live"):
        notes.append("The client file marks this entry <i>never went live</i>.")
    if item.get("deprecated"):
        notes.append("The client file marks this entry deprecated / removed from generators.")
    for flav in item.get("flavors") or []:
        notes.append(html.escape(flav))
    if notes:
        body.append("<p>" + " ".join(notes) + "</p>")
    if item["mods"]:
        body.append("<p><b>Fixed mods on this template</b> (client <code>LabelType = NONE</code>, always on the item):</p>")
        body.append("<ul>")
        for mod in item["mods"]:
            body.append(f"<li> {html.escape(mod)}\n</li>")
        body.append("</ul>")
    else:
        body.append("<p>This mythic entry does not declare enhancement Mod blocks of its own. It only sets the name and the flags above.</p>")
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
