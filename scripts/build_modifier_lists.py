"""Full player-facing prefix / postfix lists from ModPAL files."""
from __future__ import annotations

import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_gc as gc
from build_item_systems import PLAYER_STAT, player_stat_lines

DUMP = gc.DDS_DIR
CONTENT = gc.CONTENT
SKIP = {"of the", "NONE", "PREFIX", "SUFFIX", "NEEDS ENTRY", ""}
LABEL_RE = re.compile(r'Label\s*=\s*"((?:[^"\\]|\\.)*)"')
TYPE_RE = re.compile(r"LabelType\s*=\s*(\w+)")
QUAL_RE = re.compile(r"Quality\s*=\s*(\w+)")
EXT_RE = re.compile(
    r"extends\s+([\w.]+)[^\n]*\n\s*\{([\s\S]*?)\n\s*\}",
)
LEVEL_BLOCK = re.compile(
    r"^\t([A-Za-z0-9]+)\s*(?://\s*([^\n]*))?\s*\n\t\{",
    re.M,
)
FILE_POOL = {
    "WeaponMagicModPAL": "Weapons",
    "WeaponRareModPAL": "Weapons",
    "WeaponUniqueModPAL": "Weapons",
    "WeaponSuperiorModPAL": "Weapons",
    "WeaponMythicModPAL": "Weapons",
    "WeaponModPAL": "Weapons",
    "FighterModPAL": "Fighter armor",
    "RangerModPAL": "Ranger armor",
    "MageModPAL": "Mage armor",
    "SharedArmorModPAL": "Armor",
    "FighterShieldModPAL": "Fighter shields",
    "MageShieldModPAL": "Mage shields",
    "LevelPrefixModPAL": "Grey names",
    "PlateModPAL": "Plate",
    "ScaleModPAL": "Scale",
    "CrystalModPAL": "Crystal",
    "LeatherModPAL": "Leather",
    "ChainModPAL": "Chain",
    "SplintModPAL": "Splint",
    "SwordModPAL": "Swords",
    "AxeModPAL": "Axes",
    "MaceModPAL": "Maces",
    "PickModPAL": "Picks",
    "StaffModPAL": "Staves",
    "GunModPAL": "Guns",
    "CrossbowModPAL": "Crossbows",
    "CannonModPAL": "Cannons",
    "2HCannonModPAL": "Cannons",
    "RingModPAL": "Rings",
    "AmuletModPAL": "Amulets",
    "RingCraftedModPAL": "Rings",
    "AmuletCraftedModPAL": "Amulets",
    "SwordCraftedModPAL": "Swords",
    "AxeCraftedModPAL": "Axes",
    "StaffCraftedModPAL": "Staves",
    "PickCraftedModPAL": "Picks",
    "GunCraftedModPAL": "Guns",
    "CrystalCraftedModPAL": "Crystal",
    "SplintCraftedModPAL": "Splint",
}
LEVEL_MAT = {
    "XXXLight01": "Ghost",
    "XXLight01": "Cloth",
    "XLight01": "Padded",
    "Light01": "Leather",
    "Medium01": "Chain",
    "Heavy01": "Splint",
    "XHeavy01": "Scale",
    "XXHeavy01": "Plate",
    "XXXHeavy01": "Crystal",
    "Weapon01": "Weapons",
}
QUALITY_PAGE = {
    ("MAGICAL", "PREFIX"): ("Magic Prefixes", "Magic_Prefixes", "blue Magic", "in front of the item name"),
    ("RARE", "POSTFIX"): ("Rare Postfixes", "Rare_Postfixes", "yellow Rare", "after the item name, before the last word"),
    ("UNIQUE", "PREFIX"): ("Unique Prefixes", "Unique_Prefixes", "purple Unique", "in front of the item name"),
    ("SUPERIOR", "POSTFIX"): None,
    ("NORMAL", "PREFIX"): ("Level Prefixes", "Level_Prefixes", "grey", "in front of the item name on ordinary drops"),
    ("MYTHIC", "PREFIX"): None,
    ("MYTHIC", "POSTFIX"): None,
}


def stats_from_ext(ext: str) -> str:
    from build_item_systems import stats_from_name
    return stats_from_name(ext)


def pool_name(path: Path) -> str:
    return FILE_POOL.get(path.stem, path.stem.replace("ModPAL", "").replace("Crafted", ""))


def iter_modpal() -> list[Path]:
    files = []
    for path in DUMP.rglob("*ModPAL.gc"):
        low = str(path).lower()
        if "deprecated" in low or "skillbook" in low or "procmod" in low:
            continue
        files.append(path)
    return sorted(files)


def extract() -> dict[tuple[str, str], dict[str, dict]]:
    """(quality, labeltype) -> label -> {stats, pools}"""
    bags: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for path in iter_modpal():
        text = path.read_text(encoding="utf-8", errors="ignore")
        pool = pool_name(path)
        level_owner = ""
        if path.stem == "LevelPrefixModPAL":
            for block in LEVEL_BLOCK.finditer(text):
                raw = (block.group(2) or "").split("(")[0].strip()
                level_owner = LEVEL_MAT.get(block.group(1), raw or block.group(1))
                chunk_end = text.find("\n\t}", block.end())
                chunk = text[block.end(): chunk_end if chunk_end > 0 else None]
                for inner in EXT_RE.finditer(chunk):
                    body = inner.group(2)
                    label_m = LABEL_RE.search(body)
                    type_m = TYPE_RE.search(body)
                    qual_m = QUAL_RE.search(body)
                    if not (label_m and type_m and qual_m):
                        continue
                    label = label_m.group(1).strip()
                    if label in SKIP:
                        continue
                    key = (qual_m.group(1).upper(), type_m.group(1).upper())
                    row = bags[key].setdefault(label, {"stats": "", "pools": set()})
                    row["pools"].add(level_owner or pool)
            continue
        for block in EXT_RE.finditer(text):
            body = block.group(2)
            label_m = LABEL_RE.search(body)
            type_m = TYPE_RE.search(body)
            qual_m = QUAL_RE.search(body)
            if not (label_m and type_m and qual_m):
                continue
            label = label_m.group(1).strip()
            if label in SKIP:
                continue
            key = (qual_m.group(1).upper(), type_m.group(1).upper())
            stats = stats_from_ext(block.group(1))
            row = bags[key].setdefault(label, {"stats": stats, "pools": set()})
            if stats and not row["stats"]:
                row["stats"] = stats
            row["pools"].add(pool)
    return bags


def table_html(rows: list[tuple[str, str, str]]) -> str:
    parts = ['<table class="wiki-mod-table">', "<tr><th>Word</th><th>Bonus</th><th>On</th></tr>"]
    for label, stats, pools in rows:
        bonus = ", ".join(player_stat_lines(stats)) or "—"
        parts.append(
            f"<tr><td>{html.escape(label)}</td>"
            f"<td>{html.escape(bonus)}</td>"
            f"<td>{html.escape(pools)}</td></tr>"
        )
    parts.append("</table>")
    return "\n".join(parts)


def grouped_rows(bag: dict[str, dict]) -> dict[str, list[tuple[str, str, str]]]:
    groups: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for label, info in sorted(bag.items(), key=lambda kv: kv[0].lower()):
        pools = sorted(info["pools"])
        primary = pools[0] if pools else "General"
        groups[primary].append((label, info["stats"], ", ".join(pools)))
    return dict(sorted(groups.items()))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def page_html(title: str, lead: str, groups: dict[str, list[tuple[str, str, str]]]) -> str:
    parts = [f"<p>{lead}</p>"]
    parts.append(
        '<p>Also see <a href="/wiki/Modifiers" title="Modifiers">Modifiers</a>, '
        '<a href="/wiki/Name_Descriptors" title="Name Descriptors">Name Descriptors</a>, '
        '<a href="/wiki/Item_Prefixes" title="Item Prefixes">Item Prefixes</a>, and '
        '<a href="/wiki/Item_Suffixes" title="Item Suffixes">Item Suffixes</a>.</p>'
    )
    if len(groups) > 1:
        parts.append('<table class="toc" id="toc" summary="Contents"><tr><td><div id="toctitle"><h2>Contents</h2></div><ul>')
        for pool in groups:
            anchor = re.sub(r"[^A-Za-z0-9]+", "_", pool)
            parts.append(f'<li><a href="#{anchor}">{html.escape(pool)}</a></li>')
        parts.append("</ul></td></tr></table>")
    for pool, rows in groups.items():
        anchor = re.sub(r"[^A-Za-z0-9]+", "_", pool)
        parts.append(f'<a name="{anchor}"></a><h2> <span class="mw-headline">{html.escape(pool)}</span></h2>')
        parts.append(f"<p>{len(rows)} names.</p>")
        parts.append(table_html(rows))
    parts.append('<div class="visualClear"></div>')
    return "\n".join(parts)


def cat_page(name: str, parent: list[str], blurb: str) -> None:
    dest = CONTENT / "Category" / f"{name.replace(' ', '_')}.json"
    write_json(dest, {
        "title": f"Category:{name}",
        "wikiTitle": f"Category:{name.replace(' ', '_')}",
        "path": f"/wiki/Category/{name.replace(' ', '_')}",
        "description": f"Category:{name} — The Townstons wiki",
        "categories": parent,
        "images": [],
        "html": f"<p>{blurb}</p>\n<div class=\"visualClear\"></div>",
    })


def modifiers_html() -> str:
    return """<p>Item names are not random flavor. Each extra word is a modifier you can read.</p>
<p>A typical yellow sword looks like:</p>
<blockquote>Molten Iron Sword of the Beetle</blockquote>
<ul>
<li><b>Molten</b> — Magic prefix (blue word in front)</li>
<li><b>Iron Sword</b> — the base item</li>
<li><b>of the</b> — the glue word</li>
<li><b>Beetle</b> — Superior last word (green+). Beetle on fighter armor is always Endurance.</li>
</ul>
<p>Yellow adds another word before that last word. Purple swaps the front word for a Unique prefix. Grey junk can also wear a cosmetic level word (<i>Opaque</i>, <i>Acid-Wash</i>) that does not change stats. Rainbows keep a fixed name and can roll a joke ending instead.</p>
<a name="Quality"></a><h2> <span class="mw-headline">When the words show up</span></h2>
<ul>
<li>Grey (Normal) — cosmetic level prefix only</li>
<li>Green (Superior, level 1+) — last word</li>
<li>Blue (Magic, level 3+) — prefix + last word</li>
<li>Yellow (Rare, level 6+) — prefix + rare postfix + last word</li>
<li>Purple (Unique, level 10+) — unique prefix + rare postfix + last word</li>
<li>Rainbow (Mythic, level 15+) — fixed name, optional <a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">mythic ending</a></li>
</ul>
<a name="Lists"></a><h2> <span class="mw-headline">Full word lists</span></h2>
<ul>
<li><a href="/wiki/Name_Descriptors" title="Name Descriptors">Name Descriptors</a> — Superior last words by class and weapon</li>
<li><a href="/wiki/Level_Prefixes" title="Level Prefixes">Level Prefixes</a> — grey cosmetic words</li>
<li><a href="/wiki/Magic_Prefixes" title="Magic Prefixes">Magic Prefixes</a> — blue words in front</li>
<li><a href="/wiki/Rare_Postfixes" title="Rare Postfixes">Rare Postfixes</a> — yellow words after the name</li>
<li><a href="/wiki/Unique_Prefixes" title="Unique Prefixes">Unique Prefixes</a> — purple words in front</li>
<li><a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">Mythic Suffixes</a> — rainbow joke endings</li>
<li><a href="/wiki/Item_Prefixes" title="Item Prefixes">Item Prefixes</a> — every front-of-name list</li>
<li><a href="/wiki/Item_Suffixes" title="Item Suffixes">Item Suffixes</a> — every after-the-name list</li>
</ul>
<p>Fighter loot uses Scale / Plate / Crystal. Ranger uses Leather / Chain / Splint. Mage uses Ghost / Cloth / Padded. Anyone can wear any piece that meets the level.</p>
<div class="visualClear"></div>"""


def name_descriptors_html() -> str:
    return """<p>The last word on green and better gear is the <b>Superior postfix</b>. That word is how you read Strength, Agility, Endurance, and Intellect at a glance. A fighter tank looking for Endurance hunts <i>Beetle</i> plate. The same word on a different weapon family can mean something else — armor <i>Hippo</i> is not mace <i>Hippopotamus</i>.</p>
<p>Blue and purple add a word in front. Yellow can add another word before this last word. Those lists are on <a href="/wiki/Magic_Prefixes" title="Magic Prefixes">Magic Prefixes</a>, <a href="/wiki/Unique_Prefixes" title="Unique Prefixes">Unique Prefixes</a>, and <a href="/wiki/Rare_Postfixes" title="Rare Postfixes">Rare Postfixes</a>. Rainbow endings are on <a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">Mythic Suffixes</a>.</p>
<a name="Armor"></a><h2> <span class="mw-headline">Armor</span></h2>
<p>Any class can wear any armor that meets the level. The last word still comes from that armor's class list.</p>
<a name="Fighter"></a><h3> <span class="mw-headline">Fighter</span></h3>
<ul><li> Beetle — + Endurance</li>
<li> Hippo — + Strength</li>
<li> Penguin, Ant, Liger — + Strength, + Endurance</li>
<li> Tigon, Panda, Tarantula — + Strength, + Agility</li></ul>
<a name="Ranger"></a><h3> <span class="mw-headline">Ranger</span></h3>
<ul><li> Hawk — + Agility</li>
<li> Greyhound — + Endurance</li>
<li> Manatee, Newt, Bonobo — + Agility, + Endurance</li>
<li> Dragonfly, Squid, Blowfish — + Agility, + Intellect</li></ul>
<a name="Mage"></a><h3> <span class="mw-headline">Mage</span></h3>
<ul><li> Noggin' — + Intellect</li>
<li> Turtle — + Endurance</li>
<li> Starfish, Armadillo, Unicorn, Wallaby — + Endurance, + Intellect</li>
<li> Narwhal — + Agility, + Intellect <i>(ninja mage body only, not random drops)</i></li></ul>
<a name="Weapons"></a><h2> <span class="mw-headline">Weapons</span></h2>
<a name="Melee"></a><h3> <span class="mw-headline">Melee</span></h3>
<p><b>Maces</b></p>
<ul><li> Snapper — + Endurance</li>
<li> Bunny — + Agility, + Endurance</li>
<li> Hog — + Strength, + Endurance</li>
<li> Buckaroo — + Agility, + Endurance, + Intellect</li>
<li> Hippopotamus — + Agility, + Strength</li></ul>
<p><b>Staves</b></p>
<ul><li> Platypus — + Intellect</li>
<li> Wombat — + Endurance, + Intellect</li>
<li> Beaver — + Strength, + Endurance, + Intellect</li></ul>
<p><b>Picks</b></p>
<ul><li> Taint — + Strength</li>
<li> Hysteria — + Agility, + Endurance</li>
<li> Rage — + Strength, + Endurance</li>
<li> Battle — + Strength, + Endurance, + Intellect</li></ul>
<p><b>Swords</b></p>
<ul><li> Bovine — + Agility</li>
<li> Muskrat — + Agility, + Intellect</li>
<li> Nutria — + Strength, + Intellect</li>
<li> Monkey — + Agility, + Endurance, + Intellect</li></ul>
<p><b>Axes</b></p>
<ul><li> Rendezvous Point — + Agility</li>
<li> Reactor — + Strength</li>
<li> Party — + Agility, + Endurance</li>
<li> Ghetto — + Strength, + Endurance</li>
<li> Nether Region — + Agility, + Strength</li>
<li> Flipside — + Strength, + Agility, + Intellect</li></ul>
<a name="Ranged"></a><h3> <span class="mw-headline">Ranged</span></h3>
<p><b>Crossbows</b></p>
<ul><li> Sugar Glider — + Agility</li>
<li> Roadkill — + Endurance</li>
<li> Ladybug — + Agility, + Intellect</li>
<li> Gerbil — + Endurance, + Intellect</li>
<li> Wasp — + Agility, + Endurance, + Intellect</li></ul>
<p><b>Guns</b></p>
<ul><li> Yeti — + Agility</li>
<li> Termite — + Endurance, + Intellect</li>
<li> Spammer — + Agility, + Endurance, + Intellect</li></ul>
<p><b>Cannons</b></p>
<ul><li> Jumbo Shrimp — + Agility</li>
<li> Elephant — + Endurance</li>
<li> Brontosaurus — + Strength</li>
<li> Whale — + Agility, + Endurance</li>
<li> Rhino — + Endurance, + Intellect <i>(same word as jewelry Rhino, different stats)</i></li>
<li> Kraken — + Agility, + Intellect</li>
<li> Python — + Agility, + Endurance, + Intellect</li></ul>
<a name="Jewelry"></a><h2> <span class="mw-headline">Jewelry</span></h2>
<p>Rings and amulets share this list, except Chicken, which is amulet-only.</p>
<ul><li> Crocodile — + Endurance</li>
<li> Sasquatch — + Strength</li>
<li> Jackalope — + Agility</li>
<li> Dodo — + Intellect</li>
<li> Clam — + Strength, + Endurance</li>
<li> Llama — + Agility, + Endurance</li>
<li> Chicken — + Agility, + Endurance <i>(amulets only)</i></li>
<li> Amoeba — + Agility, + Strength</li>
<li> Donkey — + Agility, + Intellect</li>
<li> Rooster — + Endurance, + Intellect</li>
<li> Rhino — + Strength, + Intellect</li>
<li> Chinchilla — + Strength, + Agility, + Endurance</li>
<li> Butterfly — + Agility, + Endurance, + Intellect</li>
<li> Lobster — + Strength, + Endurance, + Intellect</li>
<li> Goat — + Agility, + Intellect, + Strength</li>
<li> Algae — + Strength, + Agility, + Endurance, + Intellect</li></ul>
<p>The full dump of every other name word is on the category pages linked from <a href="/wiki/Modifiers" title="Modifiers">Modifiers</a>.</p>
<div class="visualClear"></div>"""


def main() -> None:
    bags = extract()
    for key, spec in QUALITY_PAGE.items():
        if spec is None:
            continue
        title, slug, color, where = spec
        bag = bags.get(key, {})
        groups = grouped_rows(bag)
        lead = (
            f"<b>{html.escape(title)}</b> are the {color} words that sit {where}. "
            f"This is the full list ({sum(len(v) for v in groups.values())} names)."
        )
        write_json(CONTENT / f"{slug}.json", {
            "title": title,
            "wikiTitle": slug,
            "path": f"/wiki/{slug}",
            "description": f"{title} — The Townstons wiki",
            "categories": ["Glossary", "Items", "Game Mechanics", title],
            "images": [],
            "html": page_html(title, lead, groups),
        })
        cat_page(title, ["Item Prefixes" if "Prefix" in title else "Item Suffixes", "Glossary"],
                 f"The full list is on <a href=\"/wiki/{slug}\" title=\"{title}\">{title}</a>.")
        print(f"wrote {title}: {sum(len(v) for v in groups.values())}")

    write_json(CONTENT / "Modifiers.json", {
        "title": "Modifiers",
        "wikiTitle": "Modifiers",
        "path": "/wiki/Modifiers",
        "description": "Modifiers — The Townstons wiki",
        "categories": ["Glossary", "Items", "Game Mechanics"],
        "images": [],
        "html": modifiers_html(),
    })
    write_json(CONTENT / "Name_Descriptors.json", {
        "title": "Name Descriptors",
        "wikiTitle": "Name_Descriptors",
        "path": "/wiki/Name_Descriptors",
        "description": "Name Descriptors — The Townstons wiki",
        "categories": ["Glossary", "Items", "Superior Postfixes"],
        "images": [],
        "html": name_descriptors_html(),
    })
    write_json(CONTENT / "Item_Prefixes.json", {
        "title": "Item Prefixes",
        "wikiTitle": "Item_Prefixes",
        "path": "/wiki/Item_Prefixes",
        "description": "Item Prefixes — The Townstons wiki",
        "categories": ["Glossary", "Items", "Item Prefixes"],
        "images": [],
        "html": (
            "<p>Words that sit <b>in front</b> of the item name.</p>"
            "<ul>"
            '<li><a href="/wiki/Level_Prefixes" title="Level Prefixes">Level Prefixes</a> — grey cosmetic</li>'
            '<li><a href="/wiki/Magic_Prefixes" title="Magic Prefixes">Magic Prefixes</a> — blue</li>'
            '<li><a href="/wiki/Unique_Prefixes" title="Unique Prefixes">Unique Prefixes</a> — purple</li>'
            '<li>Rainbow jewelry can also roll <i>Up-Sized</i>, <i>Steam Rolling</i>, or <i>Bloodlusting</i> '
            '(see <a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">Mythic Suffixes</a>)</li>'
            "</ul><div class=\"visualClear\"></div>"
        ),
    })
    write_json(CONTENT / "Item_Suffixes.json", {
        "title": "Item Suffixes",
        "wikiTitle": "Item_Suffixes",
        "path": "/wiki/Item_Suffixes",
        "description": "Item Suffixes — The Townstons wiki",
        "categories": ["Glossary", "Items", "Item Suffixes"],
        "images": [],
        "html": (
            "<p>Words that sit <b>after</b> the item name.</p>"
            "<ul>"
            '<li><a href="/wiki/Name_Descriptors" title="Name Descriptors">Name Descriptors</a> — Superior last word (green+)</li>'
            '<li><a href="/wiki/Rare_Postfixes" title="Rare Postfixes">Rare Postfixes</a> — yellow extra word</li>'
            '<li><a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">Mythic Suffixes</a> — rainbow joke endings</li>'
            "</ul><div class=\"visualClear\"></div>"
        ),
    })
    growth = json.loads((CONTENT / "Growth_Items.json").read_text(encoding="utf-8"))
    listed = re.search(r"<ul>[\s\S]*?</ul>", growth.get("html") or "")
    growth["html"] = (
        "<p>Growth Items are rainbow rings and amulets with a <b>+ % Character Size</b> bonus. "
        "Size does nothing in a fight. Players stacked two rings and one amulet; the old listed "
        "maximum is 56% (13% + 13% + 26%). The jewelry prefix for that bonus is <i>Up-Sized</i>.</p>"
        "<p>Known pages in "
        '<a href="/wiki/Category/Growth_Items" title="Category:Growth Items">Category:Growth Items</a>:</p>'
        + (listed.group(0) if listed else "")
        + '\n<div class="visualClear"></div>'
    )
    write_json(CONTENT / "Growth_Items.json", growth)
    for name, parent, blurb in (
        ("Item Prefixes", ["Glossary"], "Every list of words that sit in front of an item name."),
        ("Item Suffixes", ["Glossary"], "Every list of words that sit after an item name."),
        ("Superior Postfixes", ["Item Suffixes", "Glossary"],
         'The last-word list is on <a href="/wiki/Name_Descriptors" title="Name Descriptors">Name Descriptors</a>.'),
        ("Name Modifiers", ["Glossary", "Items"],
         'Start at <a href="/wiki/Modifiers" title="Modifiers">Modifiers</a>.'),
    ):
        cat_page(name, parent, blurb)
    print("hubs written")


if __name__ == "__main__":
    main()
