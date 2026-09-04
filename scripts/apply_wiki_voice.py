"""Sweep wiki HTML to player voice and fix rainbow categories."""
from __future__ import annotations

import json
import re
from pathlib import Path

import match_gc as gc
from build_item_systems import KIND_PHRASE, PLAYER_STAT, player_stat_lines, rainbow_html

CONTENT = gc.CONTENT
FROZEN_RAINBOW = CONTENT / "Category" / "Rainbow_Items.json"
QUESTGIVER_RE = re.compile(r"QuestGiver_[A-Za-z0-9]+")
RETURN_TO = re.compile(
    r"return to (?:the )?([A-Z][^.<]{1,70}?)(?:\s+in\s|\.|$)",
    re.I,
)
SLOT_FROM_CAT = {
    "rainbow helms": "Helm",
    "rainbow body armor": "Body",
    "rainbow gloves": "Gloves",
    "rainbow boots": "Boots",
    "rainbow shoulders": "Shoulders",
    "rainbow shields": "Shield",
    "rainbow rings": "Ring",
    "rainbow amulets": "Amulet",
}
CLASS_FROM_CAT = {
    "fighter rainbow armor": "Fighter",
    "ranger rainbow armor": "Ranger",
    "mage rainbow armor": "Mage",
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
KIND_FROM_TEXT = {
    "2h axe": "2H Axe",
    "1h axe": "1H Axe",
    "2h sword": "2H Sword",
    "1h sword": "1H Sword",
    "2h mace": "2H Mace",
    "1h mace": "1H Mace",
    "2h pick": "2H Pick",
    "1h pick": "1H Pick",
    "2h staff": "2H Staff",
    "1h staff": "1H Staff",
    "2h gun": "2H Gun",
    "1h gun": "1H Gun",
    "2h crossbow": "2H Crossbow",
    "2h cannon": "2H Cannon",
}
SKIP_RAINBOW_MEMBER = {
    "Mythic Suffixes",
    "Growth Items",
    "Modifiers",
    "Name Descriptors",
    "Kings Coins",
    "King's Coins",
    "Soulbound",
    "Loot",
    "Items",
}
VOICE_SWAPS = (
    (
        "Recovered from the Dungeon Runners client files. The notes above are from the old wiki when they exist.",
        "Journal text, offer, and turn-in as they appeared in game.",
    ),
    (
        "This quest was removed from the game; the client still has the text.",
        "This quest was removed from the game.",
    ),
    ("Client level range:", "Level range:"),
    ("None listed in the client files", "None listed"),
    ("Stats on this page come from that list and the Dungeon Runners client files.", "Stats on this page come from the old weapon lists."),
    ("The client also has material-tier versions of this weapon", "This weapon also exists in other materials"),
    ("The nine client materials are Ghost, Cloth, Padded (Rubber), Leather, Chain, Splint, Scale, Plate, and Crystal (<code>BaseArmorClasses.gc</code>). Ninja is a cloth mesh, not a material.",
     "The nine armor materials are Ghost, Cloth, Padded (Rubber), Leather, Chain, Splint, Scale, Plate, and Crystal. Ninja is a cloth look, not a tenth material."),
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def field(html: str, label: str) -> str:
    pat = rf"<b>{re.escape(label)}:?\s*(?:&nbsp;)?\s*</b>\s*</td>\s*<td[^>]*>\s*([^<]+)"
    match = re.search(pat, html, re.I)
    return (match.group(1).strip() if match else "").replace("&nbsp;", "").strip()


def is_quest(data: dict) -> bool:
    html = data.get("html") or ""
    return "Quest Giver:" in html or "client-quest" in html


def is_category(data: dict) -> bool:
    return str(data.get("title") or "").startswith("Category:")


def scrape_mods(html: str) -> list[str]:
    mods = []
    for raw in re.findall(r"<li>\s*([^<]+)", html):
        text = raw.strip()
        if not text:
            continue
        mods.extend(player_stat_lines(text) or [text])
    # player_stat_lines already expands; rainbow_html will expand again.
    # Keep raw tokens so rainbow_html can map them.
    raw_mods = []
    for raw in re.findall(r"<li>\s*([^<]+)", html):
        raw_mods.append(raw.strip())
    return raw_mods


NINJA_CLOTH = {
    "Shadow Shozoko",
    "Tabi-lous",
    "Shadow Shawl",
    "Gloves of Silent Destruction",
    "Shaded Eyes",
}


def infer_slot_class(data: dict) -> tuple[str, str]:
    slot = ""
    klass = ""
    for cat in data.get("categories") or []:
        key = cat.lower()
        if key in SLOT_FROM_CAT:
            slot = SLOT_FROM_CAT[key]
        if key in CLASS_FROM_CAT:
            klass = CLASS_FROM_CAT[key]
        if key == "one-handed-fighter-rainbows":
            klass = klass or "Fighter"
            slot = slot or "Weapon"
        if key == "two-handed-fighter-rainbows":
            klass = klass or "Fighter"
            slot = slot or "Weapon"
        if key == "one-handed-mage-rainbows":
            klass = klass or "Mage"
            slot = slot or "Weapon"
        if key == "two-handed-mage-rainbows":
            klass = klass or "Mage"
            slot = slot or "Weapon"
        if "ranger-rainbows" in key:
            klass = klass or "Ranger"
            slot = slot or "Weapon"
    return slot, klass


def rewrite_scraped_item(data: dict) -> str | None:
    html = data.get("html") or ""
    scraped = (
        "from the client file" in html
        or "Class palette" in html
        or "Client type" in html
        or "PreBuiltWishingWell" in html
        or "SoulBound = true" in html
        or "is a rainbow item." in html
        or "is a fighter rainbow item." in html
        or "is a mage rainbow item." in html
        or "is a ranger rainbow item." in html
        or " is a mage gloves." in html
        or " is a fighter gloves." in html
        or " is a ranger gloves." in html
        or " is a mage boots." in html
        or " is a fighter boots." in html
        or " is a ranger boots." in html
        or " is a mage shoulders." in html
        or " is a fighter shoulders." in html
        or " is a ranger shoulders." in html
    )
    if not scraped or "Quest Giver" in html:
        return None
    if is_quest(data) or is_category(data):
        return None
    title = data.get("title") or ""
    slot = field(html, "Piece")
    klass = field(html, "Class") or field(html, "Class palette")
    if not slot or not klass or slot == "Weapon" and not field(html, "Type"):
        inferred_slot, inferred_class = infer_slot_class(data)
        slot = slot or inferred_slot
        klass = klass or inferred_class
    raw_kind = field(html, "Type") or field(html, "Client type")
    kind = KIND_FROM_TEXT.get(raw_kind.lower(), "")
    if not kind and raw_kind:
        # Cloth (XXLight) etc — material, not weapon
        if slot in SLOT_CAT or slot in {"Body", "Helm", "Gloves", "Boots", "Shoulders", "Shield", "Ring", "Amulet"}:
            kind = raw_kind.split("(")[0].strip()
        else:
            kind = raw_kind
    wishing = "wishing" in html.lower()
    soulbound = "SoulBound" in html or "soulbound" in html.lower()
    mods = []
    for raw in re.findall(r"<li>\s*([^<]+)", html):
        mods.append(raw.strip())
    flavors = []
    for flav in re.findall(r"1st Edition[^<]*", html):
        flavors.append(flav.strip())
    item = {
        "label": title,
        "kind": kind,
        "class": klass,
        "slot": slot if slot != "Weapon" else "Weapon",
        "mods": mods,
        "wishing": wishing,
        "soulbound": soulbound,
        "never_live": title not in NINJA_CLOTH and ("never-live" in html or "never went live" in html.lower()),
        "deprecated": False,
        "flavors": flavors,
        "file": "",
        "entry": "",
    }
    return rainbow_html(item)


def clean_npc_paths(html: str) -> str:
    html = re.sub(
        r"(Soldier Hogarth|Townston Commander)\s+world\.[A-Za-z0-9_.]+",
        r"\1",
        html,
    )
    html = QUESTGIVER_RE.sub("Unknown", html)
    return html


def apply_voice(html: str) -> str:
    out = html
    for old, new in VOICE_SWAPS:
        out = out.replace(old, new)
    return out


def fix_quest_giver(html: str) -> str:
    if "QuestGiver_" not in html:
        return html
    journal = ""
    jm = re.search(r"<b>Journal:</b>\s*([^<]+)", html)
    if jm:
        journal = jm.group(1)
    name = ""
    hit = RETURN_TO.search(journal)
    if hit:
        name = hit.group(1).strip().rstrip(",")
    if not name:
        return html
    escaped = (
        name.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return QUESTGIVER_RE.sub(escaped, html)


def cats_for_rainbow(data: dict) -> list[str]:
    html = data.get("html") or ""
    cats = list(data.get("categories") or [])
    low = {c.lower() for c in cats}
    slot = ""
    klass = ""
    kind = ""
    for cat, mapped in SLOT_FROM_CAT.items():
        if cat in low:
            slot = mapped
    for cat, mapped in CLASS_FROM_CAT.items():
        if cat in low:
            klass = mapped
    piece = field(html, "Piece")
    if piece in SLOT_CAT:
        slot = piece
    klass = field(html, "Class") or field(html, "Class palette") or klass
    raw_kind = field(html, "Type") or field(html, "Client type")
    kind = KIND_FROM_TEXT.get(raw_kind.lower(), raw_kind if raw_kind in WEAPON_CAT else kind)
    if "Rainbow items" not in cats and "Rainbow Items" not in cats:
        cats.append("Rainbow items")
    if slot and SLOT_CAT.get(slot) not in cats:
        cats.append(SLOT_CAT[slot])
    if slot in {"Body", "Helm", "Gloves", "Boots", "Shoulders", "Shield"} and klass in CLASS_ARMOR_CAT:
        if CLASS_ARMOR_CAT[klass] not in cats:
            cats.append(CLASS_ARMOR_CAT[klass])
    if kind in WEAPON_CAT and WEAPON_CAT[kind] not in cats:
        cats.append(WEAPON_CAT[kind])
    seen = set()
    out = []
    for cat in cats:
        key = cat.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cat)
    return out


def frozen_rainbow_titles() -> set[str]:
    if not FROZEN_RAINBOW.exists():
        return set()
    html = load(FROZEN_RAINBOW).get("html") or ""
    return set(re.findall(r'title="([^"]+)"', html))


def ensure_category_page(name: str, parent: str, blurb: str) -> None:
    dest = CONTENT / "Category" / f"{name.replace(' ', '_')}.json"
    if dest.exists():
        return
    save(dest, {
        "title": f"Category:{name}",
        "wikiTitle": f"Category:{name.replace(' ', '_')}",
        "path": f"/wiki/Category/{name.replace(' ', '_')}",
        "description": f"Category:{name} — The Townstons wiki",
        "categories": [parent],
        "images": [],
        "html": f"<p>{blurb}</p>\n<div class=\"visualClear\"></div>",
    })


def copy_love_hate_alias() -> None:
    src = CONTENT / "Love_Hate_(mostly_Hate).json"
    dest = CONTENT / "Love_Hate_mostly_Hate.json"
    if not src.exists():
        return
    data = load(src)
    data["wikiTitle"] = "Love_Hate_mostly_Hate"
    data["path"] = "/wiki/Love_Hate_mostly_Hate"
    save(dest, data)


def main() -> None:
    frozen = frozen_rainbow_titles()
    changed = 0
    rainbows = 0
    quests = 0
    for path in CONTENT.rglob("*.json"):
        data = load(path)
        html = data.get("html") or ""
        rewritten = rewrite_scraped_item(data)
        new_html = rewritten if rewritten else apply_voice(html)
        if is_quest(data):
            new_html = fix_quest_giver(new_html)
            new_html = clean_npc_paths(new_html)
            if new_html != html:
                quests += 1
        cats = list(data.get("categories") or [])
        title = data.get("title") or ""
        looks_rainbow = (
            any("rainbow" in c.lower() for c in cats)
            or title in frozen
            or (data.get("source") == "dungeon-runners-client" and not is_quest(data) and not is_category(data))
        )
        if looks_rainbow and not is_quest(data) and not is_category(data) and title not in SKIP_RAINBOW_MEMBER:
            new_cats = cats_for_rainbow({**data, "html": new_html})
            if new_cats != cats:
                data["categories"] = new_cats
                rainbows += 1
        if new_html != html:
            data["html"] = new_html
        if new_html != html or data.get("categories") != cats:
            save(path, data)
            changed += 1
    ensure_category_page(
        "One-Handed-Ranger-Rainbows",
        "Rainbow items",
        "One-handed ranger rainbow weapons.",
    )
    rainbow_cat = CONTENT / "Category" / "Rainbow_Items.json"
    if rainbow_cat.exists():
        data = load(rainbow_cat)
        html = data.get("html") or ""
        needle = "One-Handed-Mage-Rainbows</a></li>"
        extra = (
            needle
            + '<li><a href="/wiki/Category/One-Handed-Ranger-Rainbows" '
            'title="Category:One-Handed-Ranger-Rainbows">One-Handed-Ranger-Rainbows</a></li>'
        )
        if "One-Handed-Ranger-Rainbows" not in html and needle in html:
            data["html"] = html.replace(needle, extra, 1).replace(
                "There are 17 subcategories",
                "There are 18 subcategories",
                1,
            )
            save(rainbow_cat, data)
    copy_love_hate_alias()
    print(f"updated {changed} pages ({quests} quests rewritten, {rainbows} rainbow category fixes)")


if __name__ == "__main__":
    main()
