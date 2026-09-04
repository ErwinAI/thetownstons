"""Create wiki stubs for weapon-list names using client .gc stats + recovered icons."""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_gc as gc
import match_gc_rest as rest

CONTENT = gc.CONTENT
LISTS = [
    "Category/One-Handed-fighter.json",
    "Category/Two-Handed-fighter.json",
    "Category/One-Handed-mage.json",
    "Category/Two-Handed-mage.json",
    "Category/Two-Handed-ranger.json",
]
STAT_ASSIGN = re.compile(
    r"(Label|InventoryIcon|WeaponSpeed|Damage|SoulBound|Quality)\s*=\s*("
    r'"(?:[^"\\]|\\.)*"'
    r"|[A-Za-z0-9_.\-'][\w.\-']*)\s*;",
)
NAME_ALIASES = {
    "axotic": "axiotic",
}
ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
SRC_RE = re.compile(r'src="(/images/[^"]+)"')


def is_stub(data: dict) -> bool:
    body = data.get("html") or ""
    if "noarticletext" in body:
        return True
    text = re.sub(r"<[^>]+>", "", body)
    return len(re.sub(r"\s+", " ", text).strip()) < 40


def wiki_catalog() -> dict[str, tuple[Path, dict]]:
    out: dict[str, tuple[Path, dict]] = {}
    for path in CONTENT.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title") or ""
        if title.startswith("Category:"):
            continue
        out[gc.compact(title)] = (path, data)
        out[gc.compact(data.get("wikiTitle") or title)] = (path, data)
    return out


def index_stats() -> dict[str, dict]:
    stats: dict[str, dict] = {}
    for path in gc.DDS_DIR.rglob("*.gc"):
        if any(part.lower() in gc.SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "Label" not in text:
            continue
        text = gc.strip_comments(text)
        current: dict = {}
        for kind, raw in STAT_ASSIGN.findall(text):
            val = gc.unquote_val(raw)
            if kind == "Label" and val not in {"NONE", "PREFIX", "SUFFIX"}:
                if current.get("label"):
                    key = gc.compact(current["label"])
                    if key and (key not in stats or current.get("speed")):
                        stats[key] = current
                current = {"label": val}
            elif kind == "InventoryIcon":
                current["icon"] = val
            elif kind == "WeaponSpeed":
                current["speed"] = val
            elif kind == "Damage":
                current["damage"] = val
            elif kind == "SoulBound":
                current["soulbound"] = val.lower() == "true"
            elif kind == "Quality":
                current["quality"] = val
        if current.get("label"):
            key = gc.compact(current["label"])
            if key and (key not in stats or current.get("speed")):
                stats[key] = current
    return stats


def materials_for(base: str, stats: dict[str, dict]) -> list[str]:
    hits = []
    for key, row in stats.items():
        if rest.base_item_key(row["label"]) == base and key != base:
            hits.append(row["label"])
    # keep material-looking prefixes only
    out = []
    for label in hits:
        compact = gc.compact(label)
        if compact.startswith(base) is False and rest.base_item_key(label) == base:
            out.append(label)
    return sorted(set(out), key=str.lower)[:16]


def parse_rows(html_text: str) -> list[dict]:
    rows = []
    for raw in ROW_RE.findall(html_text):
        if "<th" in raw:
            continue
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip() for c in CELL_RE.findall(raw)]
        if len(cells) < 5:
            continue
        name = cells[1]
        if not name or name.lower() in {"name", "icon"}:
            continue
        srcs = SRC_RE.findall(raw)
        rows.append({
            "raw": raw,
            "name": name,
            "hand": cells[2],
            "dtype": cells[3],
            "speed": cells[4],
            "note": cells[5] if len(cells) > 5 else "",
            "icon": srcs[0] if srcs else "",
        })
    return rows


def page_path(title: str) -> str:
    return "/wiki/" + title.replace(" ", "_")


def page_file(title: str) -> Path:
    return CONTENT / (title.replace(" ", "_") + ".json")


def render_page(row: dict, gc_row: dict | None, category: str, materials: list[str]) -> dict:
    title = row["name"]
    icon = row["icon"]
    img = ""
    if icon:
        img = (
            f'<a class="image" href="{html.escape(icon, quote=True)}" title="{html.escape(title)}">'
            f'<img alt="{html.escape(title)}" border="0" src="{html.escape(icon, quote=True)}"/></a>'
        )
    rows_html = [
        ("Damage Type:", row["dtype"]),
        ("Wielding:", row["hand"]),
        ("Attack Speed:", row["speed"]),
    ]
    if row["note"]:
        rows_html.append(("Notes:", row["note"]))
    if gc_row:
        if gc_row.get("speed"):
            rows_html.append(("Client weapon speed:", gc_row["speed"]))
        if gc_row.get("damage"):
            rows_html.append(("Client damage coeff:", gc_row["damage"]))
        if gc_row.get("soulbound"):
            rows_html.append(("Soulbound:", "Yes"))
    stat_trs = "".join(
        f'<tr>\n<td style="width:50%;"><b>{html.escape(k)}&nbsp;</b>\n'
        f'</td><td style="width:50%;">{html.escape(v)}\n</td></tr>\n'
        for k, v in rows_html
    )
    extra = ""
    if materials:
        extra = (
            "<p>The client also has material-tier versions of this weapon "
            f"({html.escape(', '.join(materials[:8]))}"
            f"{', …' if len(materials) > 8 else ''}).</p>\n"
        )
    body = (
        f'<table align="right" cellpadding="2" cellspacing="0" '
        f'style="text-align:left; background:rgb(240,240,240); border:1px solid black; width:25%;">\n'
        f'<tr>\n<td colspan="2" style="text-align:center; background:#9999FF; font-size:150%;"> '
        f'{html.escape(title)}\n</td></tr>\n'
        f'<tr>\n<td colspan="2" style="text-align:center;">{img}\n</td></tr>\n'
        f'<tr>\n<td colspan="2"><hr/>\n</td></tr>\n{stat_trs}</table>\n'
        f"<p><b>{html.escape(title)}</b> is listed on the "
        f'<a href="/wiki/Category/{html.escape(category)}" title="Category:{html.escape(category)}">'
        f"{html.escape(category)}</a> weapon list. "
        f"Stats on this page come from that list and the Dungeon Runners client files.</p>\n"
        f"{extra}"
        f'<div class="visualClear"></div>'
    )
    return {
        "title": title,
        "wikiTitle": title.replace(" ", "_"),
        "path": page_path(title),
        "description": f"{title} — The Townstons wiki",
        "categories": [category, "Weapons"],
        "images": [icon] if icon else [],
        "html": body,
    }


def link_name(raw_row: str, title: str) -> str:
    href = page_path(title).replace("'", "%27")
    linked = f'<a href="{href}" title="{html.escape(title)}">{html.escape(title)}</a>'
    # Replace the name cell text once, only if not already linked.
    if f'title="{title}"' in raw_row or f"title='{title}'" in raw_row:
        return raw_row
    return raw_row.replace(f">{title}", f">{linked}", 1)


def pick_gc(name: str, stats: dict[str, dict]) -> dict | None:
    keys = [gc.compact(name), NAME_ALIASES.get(gc.compact(name), "")]
    keys.append(rest.base_item_key(name))
    for key in keys:
        if key and key in stats:
            return stats[key]
    return None


def main() -> None:
    catalog = wiki_catalog()
    gc.log("Indexing weapon stats…")
    stats = index_stats()
    gc.log(f"{len(stats)} labeled items with stats")
    created = updated = linked = 0

    for rel in LISTS:
        path = CONTENT / rel
        data = json.loads(path.read_text(encoding="utf-8"))
        html_text = data.get("html") or ""
        category = (data.get("title") or path.stem).replace("Category:", "")
        new_html = html_text
        for row in parse_rows(html_text):
            name = row["name"]
            key = gc.compact(name)
            existing = catalog.get(key)
            gc_row = pick_gc(name, stats)
            materials = materials_for(rest.base_item_key(name), stats) if gc_row else []
            dest = existing[0] if existing else page_file(name)
            current = existing[1] if existing else None
            if current and not is_stub(current):
                page = current
            else:
                page = render_page(row, gc_row, category, materials)
                dest.write_text(json.dumps(page, indent=2) + "\n", encoding="utf-8")
                catalog[key] = (dest, page)
                if existing:
                    updated += 1
                else:
                    created += 1
            replaced = link_name(row["raw"], name)
            if replaced != row["raw"]:
                new_html = new_html.replace(row["raw"], replaced, 1)
                linked += 1
        if new_html != html_text:
            data["html"] = new_html
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        gc.log(f"{rel}: linked names")

    gc.log(f"Weapon stubs: created {created}, filled {updated}, linked {linked}")


if __name__ == "__main__":
    main()
