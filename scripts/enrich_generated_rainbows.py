"""Add player-voice roll pools to generated rainbows and refresh rainbow category intros."""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_gc as gc

DUMP = gc.DDS_DIR
CONTENT = gc.CONTENT

ITEM_RE = re.compile(
    r"^\s*Item\s*=\s*[^;\n]+;(?:\s*//(?P<comment>[^\n]*))?",
    re.M,
)
GEN_RE = re.compile(r"ItemModGenerator\d+\s*=\s*([^;]+);")
ALREADY_RE = re.compile(r"This item already has a (\w+)", re.I)
ROLL_BLOCK_RE = re.compile(r'\s*<div class="wiki-roll-pool">[\s\S]*?</div>', re.I)
STUB_FIXED_RE = re.compile(
    r"<p>No fixed bonuses are known beyond the rainbow name itself\.</p>\s*"
    r"<p>Rolled copies can also pick up an extra ending\.[\s\S]*?</p>",
    re.I,
)
ATTR_RE = re.compile(
    r'<a name="Attributes:"></a>\s*<h2[^>]*>[\s\S]*?</h2>',
    re.I,
)

SKIP_TABLES = {
    "mythicbinder",
    "binder",
    "questbinder",
    "uniquebinder",
    "snowhelmvisual",
}

ALWAYS_ON = {
    "firedamageresistb": "+ Fire Damage Resistance",
    "icedamageresistb": "+ Ice Damage Resistance",
    "shadowdamageresistb": "+ Shadow Damage Resistance",
    "divinedamageresistb": "+ Divine Damage Resistance",
    "poisondamageresistb": "+ Poison Damage Resistance",
    "fireweapondamageb": "+ Fire Damage to Weapon Attacks",
    "iceweapondamageb": "+ Ice Damage to Weapon Attacks",
    "shadowweapondamageb": "+ Shadow Damage to Weapon Attacks",
    "divineweapondamageb": "+ Divine Damage to Weapon Attacks",
    "poisonweapondamageb": "+ Poison Damage to Weapon Attacks",
}

LABEL_ALIASES = {
    "Ripper McGee's Ripper McGee": "Ripper McGee's Ripper McTee... Rex (External Use Only!)",
    "Billy's Goat Skull Mask": "Billy's Goat",
}

AZZA = {
    "Azza Zin's Credence": ("Body", "Mage", "Rainbow Body Armor"),
    "Azza Zin's Credo": ("Helm", "Mage", "Rainbow Helms"),
    "Azza Zin's Credentials": ("Gloves", "Mage", "Rainbow Gloves"),
    "Azza Zin's Creepers": ("Boots", "Mage", "Rainbow Boots"),
    "Azza Zin's Credenzas": ("Shoulders", "Mage", "Rainbow Shoulders"),
}

CAT_INTROS = {
    "Mage Rainbow Armor": (
        "<p>Mage rainbow armor. Some of these are just a name and a look. "
        "The mage armor ending sets Endurance / Intellect. Extra stats roll "
        "and do not change the name. Named pieces can also have baked bonuses "
        "that every copy shares.</p>"
    ),
    "Fighter Rainbow Armor": (
        "<p>Fighter rainbow armor. Some of these are just a name and a look. "
        "The fighter armor ending sets Strength / Agility / Endurance. Extra "
        "stats roll and do not change the name. Named pieces can also have "
        "baked bonuses that every copy shares.</p>"
    ),
    "Ranger Rainbow Armor": (
        "<p>Ranger rainbow armor. Some of these are just a name and a look. "
        "The ranger armor ending sets Agility / Endurance. Extra stats roll "
        "and do not change the name. Named pieces can also have baked bonuses "
        "that every copy shares.</p>"
    ),
    "Rainbow Helms": "<p>Rainbow helms for every class.</p>",
    "Rainbow Body Armor": "<p>Rainbow body armor for every class.</p>",
    "Rainbow Gloves": "<p>Rainbow gloves for every class.</p>",
    "Rainbow Boots": "<p>Rainbow boots for every class.</p>",
    "Rainbow Shoulders": "<p>Rainbow shoulders for every class.</p>",
    "Rainbow Shields": "<p>Rainbow shields for every class.</p>",
    "Rainbow Rings": (
        "<p>Rainbow rings. Generated rings keep a fixed name and look. The "
        "jewelry ending sets the primaries. Extra stats roll and do not "
        "change the name. Size is one of those unnamed rolls on some of them.</p>"
    ),
    "Rainbow Amulets": (
        "<p>Rainbow amulets. Generated amulets keep a fixed name and look. "
        "The jewelry ending sets the primaries. Extra stats roll and do not "
        "change the name. Size is one of those unnamed rolls on some of them.</p>"
    ),
    "One-Handed-Fighter-Rainbows": "<p>One-handed fighter rainbows.</p>",
    "One-Handed-Mage-Rainbows": "<p>One-handed mage rainbows.</p>",
    "One-Handed-Ranger-Rainbows": "<p>One-handed ranger rainbows.</p>",
    "Two-Handed-Fighter-Rainbows": "<p>Two-handed fighter rainbows.</p>",
    "Two-Handed-Mage-Rainbows": "<p>Two-handed mage rainbows.</p>",
    "Two-Handed-Ranger-Rainbows": "<p>Two-handed ranger rainbows.</p>",
}

RAINBOW_ITEMS_EXTRA = (
    "<p>A lot of later rainbows work that way: fixed name and look, a joke "
    "ending for the primaries, and unnamed rolls for the rest. Named pieces "
    "can also have baked bonuses that every copy shares. The item pages say "
    "which rolls that piece actually has.</p>"
)
GROWTH_EXTRA = (
    "<p>On generated rings and amulets, size is one of those unnamed rolls. "
    "It does not change the item's name.</p>"
)


def family_of(ref: str) -> str:
    low = ref.lower()
    if "mageshield" in low or "magemg" in low or "ringmage" in low or "amuletmage" in low or "staff" in low:
        return "mage"
    if "fighter" in low or "plate" in low or "scale" in low or "crystal" in low:
        return "fighter"
    if any(w in low for w in ("axe", "sword", "mace", "pick")):
        return "fighter"
    if "ranger" in low or "leather" in low or "chain" in low or "splint" in low or "gun" in low or "crossbow" in low or "cannon" in low:
        return "ranger"
    if "ring" in low or "amulet" in low:
        return "jewelry"
    if "weapon" in low:
        return "weapon"
    return "other"


def is_weapon_ref(ref: str) -> bool:
    low = ref.lower()
    return "weaponmythic" in low or any(
        token in low
        for token in (
            "2haxe", "1haxe", "2hsword", "1hsword", "2hmace", "1hmace",
            "2hpick", "1hpick", "2hstaff", "1hstaff", "2hgun", "1hgun",
            "crossbow", "cannon",
        )
    )


def table_name(ref: str) -> str:
    return ref.strip().split(".")[-1]


def suffix_blurb(ref: str, table: str) -> str | None:
    fam = family_of(ref)
    key = table.lower()
    if key in {"mythicrequired", "required"}:
        if is_weapon_ref(ref) or fam == "weapon":
            return (
                "The joke ending is one of the "
                '<a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">weapon suffixes</a>. '
                "That ending is what sets the primaries."
            )
        if fam == "mage":
            return (
                "The joke ending is one of the six "
                '<a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">mage armor suffixes</a>. '
                "That ending is what sets Endurance / Intellect."
            )
        if fam == "fighter":
            return (
                "The joke ending is one of the "
                '<a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">fighter armor suffixes</a>. '
                "That ending is what sets Strength / Agility / Endurance."
            )
        if fam == "ranger":
            return (
                "The joke ending is one of the "
                '<a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">ranger armor suffixes</a>. '
                "That ending is what sets Agility / Endurance."
            )
        if fam == "jewelry":
            return (
                "The joke ending is one of the "
                '<a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">jewelry suffixes</a>. '
                "That ending is what sets the primaries."
            )
        return (
            "The joke ending is listed on "
            '<a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">Mythic Suffixes</a>. '
            "That ending is what sets the primaries."
        )
    if key in {"fighter", "mage", "ranger"} and "weaponmythicmg" in ref.lower():
        if key == "mage":
            who = "Endurance / Intellect"
        elif key == "ranger":
            who = "Agility / Endurance"
        else:
            who = "Strength / Agility / Endurance"
        return (
            f"Primaries roll as a {who} mix. That roll is the joke ending on "
            '<a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">Mythic Suffixes</a>.'
        )
    return None


def roll_line(ref: str, table: str) -> str | None:
    fam = family_of(ref)
    key = table.lower()
    if key in SKIP_TABLES or suffix_blurb(ref, table):
        return None
    lines = {
        "damagebonus": {
            "mage": "Element: fire, ice, shadow, or a combo of those. Random.",
            "fighter": "Element / damage type: fire, ice, shadow, divine, poison, crushing, or a mix. Random.",
            "ranger": "Element / damage type: fire, ice, shadow, divine, poison, or a mix. Random.",
            "jewelry": "Element: a % bonus to fire, ice, shadow, divine, or poison damage. Random.",
            "weapon": "Element / damage type: a random elemental or physical mix.",
            "other": "Element: a random elemental bonus.",
        },
        "damageresistbonus": "Resists: a random pair or triple from divine, fire, ice, poison, and shadow.",
        "maxpointbonus": "Health / mana: health, mana, or both. Random.",
        "criticalhitmod": "Crit: crit chance or crit damage. Random.",
        "speedmod": {
            "mage": "Speed: movement speed, casting speed, or both. Random.",
            "fighter": "Speed: movement speed, melee attack speed, or both. Random.",
            "ranger": "Speed: movement speed, ranged attack speed, or both. Random.",
            "jewelry": "Speed: movement speed and/or attack or cast speed. Random.",
            "other": "Speed: movement speed and/or attack or cast speed. Random.",
        },
        "stealbonus": "Steal: health steal, mana steal, or both. Random.",
        "stunbonus": "Stun: enemy stun chance, stun resistance, or both. Random.",
        "stunmod": "Stun: enemy stun chance, stun resistance, or both. Random.",
        "attackdefenseratingbonus": "Rating: attack rating, defense rating, or both. Random.",
        "attackdefenseratingmod": "Rating: attack rating, defense rating, or both. Random.",
        "damagemod": "Melee / ranged damage: a % bonus to melee, ranged, or both. Random.",
        "damagereflectbonus": "Reflect: melee reflection, ranged reflection, or both. Random.",
        "damagereflection": "Reflect: melee reflection, ranged reflection, or both. Random.",
        "sizemod": "Size: + % Character Size. Random.",
        "regenmod": "Regen: health regen, mana regen, or both. Random.",
        "meleecriticalchancemod": "Crit: melee crit chance. Random.",
        "rangecriticalchancemod": "Crit: ranged crit chance. Random.",
        "castcriticalchancemod": "Crit: spell crit chance. Random.",
        "meleespeedmod": "Speed: melee attack speed. Random.",
        "rangespeedmod": "Speed: ranged attack speed. Random.",
        "castspeedmod": "Speed: casting speed. Random.",
        "meleeattackdefenseratingbonus": "Rating: melee attack rating and/or defense rating. Random.",
        "rangeattackdefenseratingbonus": "Rating: ranged attack rating and/or defense rating. Random.",
        "castattackdefenseratingbonus": "Rating: spell attack rating and/or defense rating. Random.",
        "meleeattackdefenseratingmod": "Rating: melee attack rating and/or defense rating. Random.",
        "rangeattackdefenseratingmod": "Rating: ranged attack rating and/or defense rating. Random.",
        "castattackdefenseratingmod": "Rating: spell attack rating and/or defense rating. Random.",
        "nofiredamageresistbonus": "Resists: a pair or triple that is not fire.",
        "noicedamageresistbonus": "Resists: a pair or triple that is not ice.",
        "noshadowdamageresistbonus": "Resists: a pair or triple that is not shadow.",
        "nodivinedamageresistbonus": "Resists: a pair or triple that is not divine.",
        "nopoisondamageresistbonus": "Resists: a pair or triple that is not poison.",
        "firedamagemod": "Damage: fire damage %. Random.",
        "icedamagemod": "Damage: ice damage %. Random.",
        "shadowdamagemod": "Damage: shadow damage %. Random.",
        "divinedamagemod": "Damage: divine damage %. Random.",
        "poisondamagemod": "Damage: poison damage %. Random.",
        "slashingfireweapondamagebonus": "Weapon damage: slashing and fire.",
        "slashingiceweapondamagebonus": "Weapon damage: slashing and ice.",
        "slashingshadowweapondamagebonus": "Weapon damage: slashing and shadow.",
        "slashingdivineweapondamagebonus": "Weapon damage: slashing and divine.",
        "slashingpoisonweapondamagebonus": "Weapon damage: slashing and poison.",
        "crushingweapondamagebonus": "Weapon damage: crushing, or crushing plus an element.",
        "piercingweapondamagebonus": "Weapon damage: piercing, or piercing plus an element.",
        "slashingweapondamagebonus": "Weapon damage: slashing, or slashing plus an element.",
        "crushingdamagemod": "Damage: crushing damage %. Random.",
        "piercingdamagemod": "Damage: piercing damage %. Random.",
        "slashingdamagemod": "Damage: slashing damage %. Random.",
    }
    mapped = lines.get(key)
    if mapped is None:
        return None
    if isinstance(mapped, dict):
        return mapped.get(fam) or mapped.get("other")
    return mapped


def label_candidates(comment: str) -> list[str]:
    text = (comment or "").strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return []
    out = [text]
    bare = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()
    if bare and bare not in out:
        out.append(bare)
    return out


def wiki_index() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for path in CONTENT.rglob("*.json"):
        if "Category" in path.parts:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title") or ""
        if title.startswith("Category:"):
            continue
        out[gc.compact(title)] = path
        out[gc.compact(data.get("wikiTitle") or title)] = path
    return out


def parse_generated() -> list[dict]:
    files = list(DUMP.glob("Mythic*IG.gc"))
    files += list((DUMP / "items" / "ig").rglob("Mythic*IG.gc"))
    files += list((DUMP / "items" / "ig").rglob("MythicIG.gc"))
    seen_files: set[Path] = set()
    items: dict[str, dict] = {}
    for path in files:
        if path in seen_files:
            continue
        seen_files.add(path)
        text = path.read_text(encoding="utf-8", errors="ignore")
        matches = list(ITEM_RE.finditer(text))
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[match.start() : end]
            gens = [g.strip() for g in GEN_RE.findall(body)]
            if not gens:
                continue
            labels = label_candidates(match.group("comment") or "")
            if not labels or labels[0].startswith("Has "):
                continue
            already = [
                ALWAYS_ON[m.lower()]
                for m in ALREADY_RE.findall(body)
                if m.lower() in ALWAYS_ON
            ]
            key = gc.compact(labels[-1])
            rec = items.setdefault(
                key,
                {
                    "labels": labels,
                    "gens": [],
                    "already": [],
                    "file": path.name,
                },
            )
            for gen in gens:
                if gen not in rec["gens"]:
                    rec["gens"].append(gen)
            for line in already:
                if line not in rec["already"]:
                    rec["already"].append(line)
    return list(items.values())


def roll_html(item: dict, title: str) -> str:
    suffix = ""
    bullets: list[str] = []
    seen = set()
    for ref in item["gens"]:
        table = table_name(ref)
        blurb = suffix_blurb(ref, table)
        if blurb and not suffix:
            suffix = blurb
        line = roll_line(ref, table)
        if line and line not in seen:
            seen.add(line)
            bullets.append(line)
    parts = [
        '<div class="wiki-roll-pool">',
        f"<p>The name and the look are fixed. {suffix}</p>" if suffix else
        "<p>The name and the look are fixed. Extra stats roll and do not show up in the name.</p>",
    ]
    if item.get("already"):
        parts.append("<p>Every copy also carries:</p><ul>")
        for line in item["already"]:
            parts.append(f"<li> {html.escape(line)}</li>")
        parts.append("</ul>")
    if bullets:
        parts.append("<p>The rest of the stats roll and do not show up in the name.</p>")
        parts.append("<ul>")
        for line in bullets:
            parts.append(f"<li> {html.escape(line)}</li>")
        parts.append("</ul>")
    if title.startswith("Azza Zin"):
        parts.append(
            "<p>This piece does not roll casting speed. Casting speed shows up on "
            "Threadz and Ma'nes instead.</p>"
        )
    parts.append(
        "<p>It is unknown how many different varieties exist. The same ending can "
        "still drop with different rolls underneath.</p>"
    )
    parts.append("</div>")
    return "\n".join(parts)


def inject_roll(page_html: str, block: str) -> str:
    page_html = ROLL_BLOCK_RE.sub("", page_html)
    page_html = STUB_FIXED_RE.sub("", page_html)
    attr = ATTR_RE.search(page_html)
    if attr:
        return page_html[: attr.end()] + "\n" + block + page_html[attr.end() :]
    close = page_html.find("</table>")
    if close != -1:
        end = close + len("</table>")
        return page_html[:end] + "\n" + block + page_html[end:]
    return block + page_html


def wiki_slug(label: str) -> str:
    return label.replace(" ", "_").replace("/", "_").replace("\\", "_")


def missing_stub(title: str, item: dict, block: str) -> dict:
    gens = " ".join(item.get("gens") or []).lower()
    if "weaponmythicmg.mage" in gens:
        klass, piece, extra = "Mage", "Weapon", "One-Handed-Mage-Rainbows"
    elif "weaponmythicmg.ranger" in gens:
        klass, piece, extra = "Ranger", "Weapon", "One-Handed-Ranger-Rainbows"
    else:
        klass, piece, extra = "Fighter", "Weapon", "One-Handed-Fighter-Rainbows"
    cats = ["Rainbow items", extra]
    return {
        "title": title,
        "wikiTitle": wiki_slug(title),
        "path": f"/wiki/{wiki_slug(title)}",
        "description": f"{title} — The Townstons wiki",
        "categories": cats,
        "images": [],
        "html": (
            '<table align="right" cellpadding="2" cellspacing="0" '
            'style="text-align:left; background:rgb(240,240,240); border:1px solid black; width:25%;">\n'
            f'<tr><td colspan="2" style="text-align:center; background:#9999FF; font-size:150%;"> '
            f"{html.escape(title)}\n</td></tr>\n"
            '<tr><td colspan="2"><hr/>\n</td></tr>\n'
            f'<tr><td style="width:50%;" valign="top"><b>Piece:&nbsp;</b>\n</td>'
            f'<td style="width:50%;" valign="top">{piece}\n</td></tr>\n'
            f'<tr><td style="width:50%;" valign="top"><b>Class:&nbsp;</b>\n</td>'
            f'<td style="width:50%;" valign="top">{klass}\n</td></tr>\n'
            f'<tr><td style="width:50%;" valign="top"><b>Damage:&nbsp;</b>\n</td>'
            f'<td style="width:50%;" valign="top">varies with item level\n</td></tr>\n'
            "</table>\n"
            f"<p><b>{html.escape(title)}</b> is a {klass.lower()} rainbow weapon.</p>\n"
            '<a name="Attributes:"></a><h2> <span class="mw-headline"> Attributes: </span></h2>\n'
            f"{block}\n"
            '<div class="visualClear"></div>'
        ),
        "source": "dungeon-runners-client",
    }


def azza_page(title: str, block: str) -> dict:
    piece, klass, slot_cat = AZZA[title]
    copula = "are" if piece in {"Gloves", "Boots", "Shoulders"} else "is a"
    return {
        "title": title,
        "wikiTitle": wiki_slug(title),
        "path": f"/wiki/{wiki_slug(title)}",
        "description": f"{title} — The Townstons wiki",
        "categories": ["Rainbow items", slot_cat, "Mage Rainbow Armor"],
        "images": [],
        "html": (
            '<table align="right" cellpadding="2" cellspacing="0" '
            'style="text-align:left; background:rgb(240,240,240); border:1px solid black; width:25%;">\n'
            f'<tr><td colspan="2" style="text-align:center; background:#9999FF; font-size:150%;"> '
            f"{html.escape(title)}\n</td></tr>\n"
            '<tr><td colspan="2"><hr/>\n</td></tr>\n'
            f'<tr><td style="width:50%;" valign="top"><b>Piece:&nbsp;</b>\n</td>'
            f'<td style="width:50%;" valign="top">{piece}\n</td></tr>\n'
            f'<tr><td style="width:50%;" valign="top"><b>Class:&nbsp;</b>\n</td>'
            f'<td style="width:50%;" valign="top">{klass}\n</td></tr>\n'
            f'<tr><td style="width:50%;" valign="top"><b>Defense Rating:&nbsp;</b>\n</td>'
            f'<td style="width:50%;" valign="top">varies with item level\n</td></tr>\n'
            "</table>\n"
            f"<p><b>{html.escape(title)}</b> {copula} mage {piece.lower()}.</p>\n"
            "<p>This item is soulbound.</p>\n"
            '<a name="Attributes:"></a><h2> <span class="mw-headline"> Attributes: </span></h2>\n'
            f"{block}\n"
            '<div class="visualClear"></div>'
        ),
        "source": "dungeon-runners-client",
    }


def strip_frozen_lists(html_text: str) -> str:
    html_text = re.sub(r'<div id="mw-pages">[\s\S]*?</div>', "", html_text, flags=re.I)
    html_text = re.sub(r'<div id="mw-subcategories">[\s\S]*?</div>', "", html_text, flags=re.I)
    return html_text.strip()


def ensure_intro(html_text: str, intro: str) -> str:
    body = strip_frozen_lists(html_text)
    body = re.sub(r'<div class="wiki-cat-intro">[\s\S]*?</div>', "", body, flags=re.I)
    body = re.sub(r"<p>Here (is|are) (all |a listing of all ).*?</p>", "", body, flags=re.I | re.S)
    body = body.strip()
    extra = f"\n{body}" if body else ""
    return f'<div class="wiki-cat-intro">\n{intro}\n</div>{extra}\n'


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_categories() -> None:
    rainbow = CONTENT / "Category" / "Rainbow_items.json"
    if rainbow.exists():
        data = json.loads(rainbow.read_text(encoding="utf-8"))
        html_text = data.get("html") or ""
        if "unnamed rolls" not in html_text:
            html_text = html_text.replace(
                "The Rainbow Body armor will show all bodies for all classes.\n</p>",
                "The Rainbow Body armor will show all bodies for all classes.\n</p>\n"
                + RAINBOW_ITEMS_EXTRA,
                1,
            )
        data["html"] = html_text
        write_json(rainbow, data)

    growth = CONTENT / "Category" / "Growth_Items.json"
    if growth.exists():
        data = json.loads(growth.read_text(encoding="utf-8"))
        html_text = data.get("html") or ""
        if "unnamed rolls" not in html_text:
            html_text = html_text.replace("</p>", "</p>\n" + GROWTH_EXTRA, 1)
        data["html"] = html_text
        write_json(growth, data)

    for name, intro in CAT_INTROS.items():
        slug = name.replace(" ", "_")
        path = CONTENT / "Category" / f"{slug}.json"
        if not path.exists():
            write_json(path, {
                "title": f"Category:{name}",
                "wikiTitle": f"Category:{slug}",
                "path": f"/wiki/Category/{slug}",
                "description": f"Category:{name} — The Townstons wiki",
                "categories": ["Rainbow items"],
                "images": [],
                "html": f'<div class="wiki-cat-intro">\n{intro}\n</div>\n',
            })
            print(f"created category {name}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        cats = list(data.get("categories") or [])
        if "Rainbow items" not in cats:
            cats.append("Rainbow items")
            data["categories"] = cats
        data["html"] = ensure_intro(data.get("html") or "", intro)
        write_json(path, data)


def main() -> None:
    index = wiki_index()
    generated = parse_generated()
    updated = 0
    created = 0
    missed: list[str] = []
    for item in generated:
        path = None
        title = item["labels"][-1]
        lookup = list(item["labels"])
        for label in list(lookup):
            alias = LABEL_ALIASES.get(label)
            if alias:
                lookup.append(alias)
        for label in lookup:
            hit = index.get(gc.compact(label))
            if hit:
                path = hit
                title = json.loads(hit.read_text(encoding="utf-8")).get("title") or label
                break
        block = roll_html(item, title)
        if path is None:
            dest = CONTENT / f"{wiki_slug(title)}.json"
            if title in AZZA:
                write_json(dest, azza_page(title, block))
            else:
                write_json(dest, missing_stub(title, item, block))
            index[gc.compact(title)] = dest
            created += 1
            print(f"created {title}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        data["html"] = inject_roll(data.get("html") or "", block)
        cats = list(data.get("categories") or [])
        if any(table_name(g).lower() == "sizemod" for g in item["gens"]):
            if "Growth Items" not in cats:
                cats.append("Growth Items")
                data["categories"] = cats
        write_json(path, data)
        updated += 1

    update_categories()
    print(f"updated {updated} generated rainbows")
    print(f"created {created} missing pages")
    print(f"no wiki page for {len(missed)}")
    for title in missed[:40]:
        print(f"  ? {title}")


if __name__ == "__main__":
    main()
