"""Create wiki stubs for named GeneratedMythic templates in items/pal."""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_gc as gc
from build_item_systems import categories_for, rainbow_html, wiki_slug

PAL = gc.DDS_DIR / "items" / "pal"
ENTRY_RE = re.compile(
    r"(?P<name>GeneratedMythic\w*)\s+extends\s+(?P<ext>[\w.]+)\s*(?://[^\n]*)?\s*"
    r"\{(?P<body>[\s\S]*?)\n[ \t]+\}",
)
LABEL_RE = re.compile(r'Label\s*=\s*"((?:[^"\\]|\\.)*)"')
FLAVOR_RE = re.compile(r'Description\s*=\s*"((?:[^"\\]|\\.)*)"')
MATERIAL = {
    "XXXLight": "Ghost (XXXLight)",
    "XXLight": "Cloth (XXLight)",
    "XLight": "Padded / Rubber (XLight)",
}
SLOT_FROM_FILE = {
    "Body": "Body",
    "Boots": "Boots",
    "Gloves": "Gloves",
    "Helm": "Helm",
    "Shoulders": "Shoulders",
    "Shield": "Shield",
}
KIND_FROM_EXT = {
    "Base1HSword": "1H Sword",
    "Base1HAxe": "1H Axe",
    "Base1HMace": "1H Mace",
    "Base1HPick": "1H Pick",
    "Base1HStaff": "1H Staff",
    "Base1HGun": "1H Gun",
}


def wiki_index() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in gc.CONTENT.rglob("*.json"):
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
    return out


def class_from_file(name: str) -> str:
    if name.startswith("Mage"):
        return "Mage"
    if name.startswith("Fighter"):
        return "Fighter"
    if name.startswith("Ranger"):
        return "Ranger"
    if "Sword" in name or "Axe" in name or "Mace" in name or "Pick" in name:
        return "Fighter"
    if "Staff" in name:
        return "Mage"
    if "Gun" in name or "Crossbow" in name or "Cannon" in name:
        return "Ranger"
    return ""


def slot_from_file(name: str) -> str:
    for key, slot in SLOT_FROM_FILE.items():
        if key in name:
            return slot
    return "Weapon"


def kind_from(file_name: str, ext: str) -> str:
    leaf = ext.split(".")[-1]
    if leaf in KIND_FROM_EXT:
        return KIND_FROM_EXT[leaf]
    for token, label in MATERIAL.items():
        if token in ext:
            return label
    stem = file_name.replace("PAL.gc", "")
    return stem


def parse() -> list[dict]:
    items = []
    for path in sorted(PAL.rglob("*.gc")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in ENTRY_RE.finditer(text):
            body = match.group("body")
            lab = LABEL_RE.search(body)
            if not lab:
                continue
            label = lab.group(1).strip()
            if not label:
                continue
            flavors = []
            for flav in FLAVOR_RE.finditer(body):
                raw = re.sub(r"<[^>]+>", "", flav.group(1)).strip()
                if raw:
                    flavors.append(raw)
            slot = slot_from_file(path.name)
            items.append({
                "label": label,
                "file": f"items/pal/{path.name}",
                "entry": match.group("name"),
                "class": class_from_file(path.name),
                "kind": kind_from(path.name, match.group("ext")),
                "slot": slot,
                "mods": [],
                "deprecated": False,
                "never_live": False,
                "wishing": False,
                "soulbound": bool(re.search(r"SoulBound\s*=\s*true", body, re.I)),
                "flavors": flavors,
            })
    return items


def write_set_page(pieces: list[dict]) -> None:
    links = []
    for item in pieces:
        slug = wiki_slug(item["label"])
        links.append(
            f'<li> <a href="/wiki/{html.escape(slug)}" title="{html.escape(item["label"])}">'
            f'{html.escape(item["label"])}</a> — {html.escape(item["slot"])}\n</li>'
        )
    html_body = (
        "<p><b>Azza Zin</b> is a named cloth mage mythic set. "
        "Each piece is <code>GeneratedMythic004</code> in the Mage PAL files "
        "(<code>Base*Classes.XXLight</code>). The item generators point at those "
        "templates in <code>items/ig/mage/MythicMage*IG.gc</code>.</p>"
        "<p>The templates set <code>SoulBound = true</code> and a fixed base name. "
        "They do not declare their own enhancement Mod blocks. Rolled endings: "
        '<a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">Mythic Suffixes</a> '
        "(Mage armor pool).</p>"
        "<p>Pieces:</p><ul>\n" + "".join(links) + "</ul>"
        '<div class="visualClear"></div>'
    )
    dest = gc.CONTENT / "Azza_Zin.json"
    dest.write_text(json.dumps({
        "title": "Azza Zin",
        "wikiTitle": "Azza_Zin",
        "path": "/wiki/Azza_Zin",
        "description": "Azza Zin — The Townstons wiki",
        "categories": ["Rainbow items", "Mage Rainbow Armor"],
        "images": [],
        "html": html_body,
        "source": "dungeon-runners-client",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote Azza_Zin set page")


def main() -> None:
    existing = wiki_index()
    created = []
    azza = []
    for item in parse():
        label = item["label"]
        if label.startswith("Azza Zin"):
            azza.append(item)
        key = gc.compact(label)
        bare = gc.compact(re.sub(r"\s*\([^)]*\)\s*$", "", label))
        if key in existing or (bare and bare in existing):
            continue
        slug = wiki_slug(label)
        dest = gc.CONTENT / f"{slug}.json"
        if dest.exists():
            continue
        extra = ""
        if label.startswith("Azza Zin"):
            extra = (
                '<p>Part of the <a href="/wiki/Azza_Zin" title="Azza Zin">Azza Zin</a> '
                "cloth set.</p>"
            )
        page_html = rainbow_html(item)
        if extra:
            page_html = page_html.replace(
                '<div class="visualClear"></div>',
                extra + '<div class="visualClear"></div>',
            )
        dest.write_text(json.dumps({
            "title": label,
            "wikiTitle": slug,
            "path": f"/wiki/{slug}",
            "description": f"{label} — The Townstons wiki",
            "categories": categories_for(item),
            "images": [],
            "html": page_html,
            "source": "dungeon-runners-client",
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        created.append(label)
        existing[key] = label
    if azza:
        order = {"Body": 0, "Shoulders": 1, "Helm": 2, "Gloves": 3, "Boots": 4, "Shield": 5}
        write_set_page(sorted(azza, key=lambda x: order.get(x["slot"], 9)))
    print(f"created {len(created)}")
    for title in created:
        print(f"  + {title}")


if __name__ == "__main__":
    main()
