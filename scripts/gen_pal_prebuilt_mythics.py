"""Create wiki stubs for MythicPreBuilt / MythicPartialBuilt / PartialBuiltMythic."""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_gc as gc
from build_item_systems import (
    MOD_EXT_RE,
    categories_for,
    rainbow_html,
    stats_from_comment,
    stats_from_name,
    wiki_slug,
)
from gen_pal_generated_mythics import (
    class_from_file,
    slot_from_file,
    wiki_index,
)

PAL = gc.DDS_DIR / "items" / "pal"
HEAD_RE = re.compile(
    r"(?P<name>(?:MythicPreBuilt|MythicPartialBuilt|PartialBuiltMythic)\w*)"
    r"\s+extends\s+(?P<ext>[\w.]+)",
)
LABEL_RE = re.compile(r'Label\s*=\s*"((?:[^"\\]|\\.)*)"')
FLAVOR_RE = re.compile(r'Description\s*=\s*"((?:[^"\\]|\\.)*)"')
LONG_SLUGS = {
    "Burning Axe of Complete Fiery Devastation Over Your Foe Who Deserve What's Coming to Them for Doing Unspeakable and Heinous Acts Such As, But Not Limited to, Passing Gas in the Company of Others, Namely You":
        "Burning_Axe_of_Complete_Fiery_Devastation",
}


def balanced_body(text: str, brace_at: int) -> str:
    depth = 0
    i = brace_at
    while i < len(text):
        ch = text[i]
        if ch == '"':
            i += 1
            while i < len(text):
                if text[i] == "\\" and i + 1 < len(text):
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[brace_at + 1 : i]
        i += 1
    return ""
MATERIAL = {
    "XXXHeavy": "Crystal (XXXHeavy)",
    "XXHeavy": "Plate (XXHeavy)",
    "XHeavy": "Scale (XHeavy)",
    "XXXLight": "Ghost (XXXLight)",
    "XXLight": "Cloth (XXLight)",
    "XLight": "Padded / Rubber (XLight)",
    "Heavy": "Splint (Heavy)",
    "Medium": "Chain (Medium)",
    "Light": "Leather (Light)",
}
KIND_FROM_EXT = {
    "Base1HSword": "1H Sword",
    "Base1HAxe": "1H Axe",
    "Base1HMace": "1H Mace",
    "Base1HPick": "1H Pick",
    "Base1HStaff": "1H Staff",
    "Base1HGun": "1H Gun",
}
SET_RULES = (
    ("The Uber Knight's Most Extreme", "The Uber Knight's Most Extreme"),
    ("The Dark Order's Ceremonial", "The Dark Order's Ceremonial"),
)
SLOT_ORDER = {"Body": 0, "Shoulders": 1, "Helm": 2, "Gloves": 3, "Boots": 4, "Shield": 5}


def kind_from(file_name: str, ext: str) -> str:
    leaf = ext.split(".")[-1]
    if leaf in KIND_FROM_EXT:
        return KIND_FROM_EXT[leaf]
    for token, label in MATERIAL.items():
        if token in ext:
            return label
    return file_name.replace("PAL.gc", "")


def parse() -> list[dict]:
    items = []
    for path in sorted(PAL.rglob("*.gc")):
        raw = path.read_text(encoding="utf-8", errors="ignore")
        text = gc.COMMENT_BLOCK.sub("", raw)
        for match in HEAD_RE.finditer(text):
            brace = text.find("{", match.end())
            if brace < 0:
                continue
            body = balanced_body(text, brace)
            if not body:
                continue
            lab = LABEL_RE.search(body)
            if not lab:
                continue
            label = lab.group(1).strip()
            if not label or label.endswith(" of") or label.endswith(" of "):
                continue
            flavors = []
            for flav in FLAVOR_RE.finditer(body):
                # skip commented-out Description = lines
                line_start = body.rfind("\n", 0, flav.start()) + 1
                if body[line_start:flav.start()].lstrip().startswith("//"):
                    continue
                raw_flav = re.sub(r"<[^>]+>", "", flav.group(1)).strip()
                if raw_flav:
                    flavors.append(raw_flav)
            mods = []
            for ext_m in MOD_EXT_RE.finditer(body):
                comment = (ext_m.group(2) or "").strip()
                stats = stats_from_comment(comment) or stats_from_name(ext_m.group(1))
                if stats:
                    mods.append(stats)
            name = match.group("name")
            items.append({
                "label": label,
                "file": f"items/pal/{path.name}",
                "entry": name,
                "class": class_from_file(path.name),
                "kind": kind_from(path.name, match.group("ext")),
                "slot": slot_from_file(path.name),
                "mods": mods,
                "deprecated": False,
                "never_live": False,
                "wishing": "WishingWell" in name or "WISHING WELL" in name.upper(),
                "soulbound": bool(re.search(r"SoulBound\s*=\s*true", body, re.I)),
                "flavors": flavors,
            })
    return items


def write_set_page(title: str, pieces: list[dict]) -> None:
    slug = wiki_slug(title)
    links = []
    for item in sorted(pieces, key=lambda x: SLOT_ORDER.get(x["slot"], 9)):
        piece_slug = wiki_slug(item["label"])
        links.append(
            f'<li> <a href="/wiki/{piece_slug}" title="{html.escape(item["label"])}">'
            f"{html.escape(item['label'])}</a> — {html.escape(item['slot'])}\n</li>"
        )
    klass = pieces[0]["class"] if pieces else ""
    html_body = (
        f"<p><b>{html.escape(title)}</b> is a named mythic set in the "
        f"<code>PartialBuiltMythic</code> / seasonal PAL templates"
        f"{f' ({html.escape(klass)} palette)' if klass else ''}.</p>"
        "<p>Each piece sets <code>SoulBound = true</code> and a fixed base name. "
        "Rolled extra endings, if any: "
        '<a href="/wiki/Mythic_Suffixes" title="Mythic Suffixes">Mythic Suffixes</a>.</p>'
        "<p>Pieces:</p><ul>\n" + "".join(links) + "</ul>"
        '<div class="visualClear"></div>'
    )
    dest = gc.CONTENT / f"{slug}.json"
    dest.write_text(json.dumps({
        "title": title,
        "wikiTitle": slug,
        "path": f"/wiki/{slug}",
        "description": f"{title} — The Townstons wiki",
        "categories": ["Rainbow items"] + ([f"{klass} Rainbow Armor"] if klass else []),
        "images": [],
        "html": html_body,
        "source": "dungeon-runners-client",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote set", title)


def safe_write(dest: Path, payload: dict) -> bool:
    try:
        dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return True
    except OSError:
        short = wiki_slug(payload["title"])[:80].rstrip("_")
        dest = gc.CONTENT / f"{short}.json"
        payload["wikiTitle"] = short
        payload["path"] = f"/wiki/{short}"
        dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("shortened path for", payload["title"])
        return True


def main() -> None:
    existing = wiki_index()
    created = []
    sets: dict[str, list[dict]] = {title: [] for _, title in SET_RULES}
    for item in parse():
        label = item["label"]
        for prefix, set_title in SET_RULES:
            if label.startswith(prefix):
                sets[set_title].append(item)
        key = gc.compact(label)
        bare = gc.compact(re.sub(r"\s*\([^)]*\)\s*$", "", label))
        slug = LONG_SLUGS.get(label) or wiki_slug(label)
        dest = gc.CONTENT / f"{slug}.json"
        extra = ""
        for prefix, set_title in SET_RULES:
            if label.startswith(prefix):
                extra = (
                    f'<p>Part of <a href="/wiki/{wiki_slug(set_title)}" '
                    f'title="{html.escape(set_title)}">{html.escape(set_title)}</a>.</p>'
                )
        page_html = rainbow_html(item)
        if extra:
            page_html = page_html.replace(
                '<div class="visualClear"></div>',
                extra + '<div class="visualClear"></div>',
            )
        payload = {
            "title": label,
            "wikiTitle": slug,
            "path": f"/wiki/{slug}",
            "description": f"{label} — The Townstons wiki",
            "categories": categories_for(item),
            "images": [],
            "html": page_html,
            "source": "dungeon-runners-client",
        }
        if dest.exists():
            old = json.loads(dest.read_text(encoding="utf-8"))
            if old.get("source") == "dungeon-runners-client":
                safe_write(dest, payload)
            continue
        if key in existing or (bare and bare in existing):
            continue
        if safe_write(dest, payload):
            created.append(label)
            existing[key] = label
    for title, pieces in sets.items():
        if len(pieces) >= 3:
            write_set_page(title, pieces)
    print(f"created {len(created)}")
    for title in created:
        print(f"  + {title}")


if __name__ == "__main__":
    main()
