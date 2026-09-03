"""Match leftover skill (and a few NPC) wiki images using .gc Icon/ActiveIcon."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_gc as gc

ROOT = gc.ROOT
CONTENT = gc.CONTENT
PUBLIC_IMAGES = gc.PUBLIC_IMAGES
RECOVERED = gc.RECOVERED
DDS_DIR = gc.DDS_DIR
SKILLS_DIR = DDS_DIR / "skills"
NPC_DIR = DDS_DIR / "world"
REPORT = ROOT / "archive" / "gc-skill-npc-matches.json"

ASSIGN = re.compile(
    r"(Label|InventoryIcon|Icon|ActiveIcon)\s*=\s*("
    r'"(?:[^"\\]|\\.)*"'
    r"|[A-Za-z0-9_][\w']*)\s*;",
)

SKILL_ALIASES = {
    "showerofgold": "goshsgloriousshowerofgold",
    "flamingbuddy": "myflamingbuddy",
    "healselfnotother": "healselfnotother",
    "imrubberyourescrewed": "imrubberyourescrewed",
}

# Only NPCs that have a real named client graphic — not UV skins or generic merchant pips.
NPC_ICONS = {
    "wishingwell": "Mystery_Wishing_Well_Icon.dds",
}


def parse_fields(text: str) -> list[dict]:
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
            if name == "Description":
                continue
            dotted = f"{prefix}.{name}" if prefix else name
            label = icon = active = None
            for kind, raw in ASSIGN.findall(gc.first_description(inner)):
                val = gc.unquote_val(raw)
                if kind == "Label" and val not in {"NONE", "PREFIX", "SUFFIX"}:
                    label = val
                elif kind == "ActiveIcon":
                    active = val
                elif kind in {"Icon", "InventoryIcon"}:
                    icon = val
            classes.append({
                "name": dotted,
                "parent": parent,
                "label": label,
                "icon": active or icon,
            })
            walk(inner, dotted)

    walk(text, "")
    return classes


def skill_labels() -> dict[str, str]:
    labels: dict[str, str] = {}
    for path in SKILLS_DIR.rglob("*.gc"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "Label" not in text or "Icon" not in text:
            continue
        for cls in parse_fields(text):
            if cls.get("label") and cls.get("icon"):
                labels[cls["label"]] = cls["icon"]
    return labels


def wiki_pages(kinds: set[str]) -> list[dict]:
    pages = []
    for path in CONTENT.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title") or ""
        cats = " ".join(data.get("categories") or []).lower()
        is_skill = "skill" in cats
        is_npc = any(k in cats for k in ("npc", "merchant", "banker", "skill trainer"))
        if title.startswith("Category:"):
            if "skill" in title.lower() and "skill" in kinds:
                pages.append({"path": path, "data": data, "kind": "skill"})
            continue
        if is_skill and "skill" in kinds:
            pages.append({"path": path, "data": data, "kind": "skill"})
        elif is_npc and "npc" in kinds:
            pages.append({"path": path, "data": data, "kind": "npc"})
    return pages


def pick_skill(title: str, labels: dict[str, tuple[str, str]]) -> tuple[str, str] | None:
    keys = gc.wiki_keys(title)
    for key in list(keys):
        keys.add(SKILL_ALIASES.get(key, key))
    for key in keys:
        if key in labels:
            return labels[key]
    if len(gc.compact(title)) >= 10:
        cands = [v for k, v in labels.items() if k.startswith(gc.compact(title)) or gc.compact(title) in k]
        if len(cands) == 1:
            return cands[0]
    return None


def apply(pages: list[dict], choose, dds: dict[str, str]) -> list[dict]:
    report = []
    replacements: list[tuple[str, str]] = []
    for item in pages:
        data = item["data"]
        title = data.get("title") or ""
        html = data.get("html") or ""
        listed = [unquote(s) for s in (data.get("images") or [])]
        srcs = re.findall(r'src="(/images/[^"]+)"', html)
        hit = choose(title)
        seen = set()
        for src in srcs:
            name = gc.original_wiki_name(src, listed)
            if name.lower() in {"magnify-clip.png", "exclamation.png"} or name in seen:
                continue
            if "image_missing" in name.lower():
                continue
            seen.add(name)
            if gc.is_keep_local(src) and "/recovered/" not in src:
                report.append({"page": title, "wiki": name, "kept": src})
                continue
            if not hit:
                report.append({"page": title, "wiki": name, "dds": None})
                continue
            label, icon = hit
            dds_name = gc.find_dds(icon, dds)
            if not dds_name:
                # try _on / no _on
                for extra in (f"{icon}_on", icon.replace("_on", "").replace("_On", "")):
                    dds_name = gc.find_dds(extra, dds)
                    if dds_name:
                        break
            if not dds_name:
                report.append({"page": title, "wiki": name, "icon": icon, "dds": None})
                continue
            safe = re.sub(r'[<>:"/\\|?*\']', "", Path(name).stem).strip(" ._")
            dest = RECOVERED / (safe + ".png")
            ok = gc.convert(DDS_DIR / dds_name, dest)
            report.append({
                "page": title,
                "wiki": name,
                "gc_label": label,
                "icon": icon,
                "dds": dds_name,
                "recovered": str(dest.relative_to(ROOT)) if ok else None,
            })
            if not ok:
                continue
            new = f"/images/recovered/{dest.name}"
            replacements.append((src, new))
            replacements.append((f"/images/{name}", new))

    replacements = list(dict.fromkeys(replacements))
    gc.log(f"Rewriting {len(replacements)} srcs…")
    # Rewrite every wiki page so category lists pick up the new icons too.
    for path in CONTENT.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in replacements:
            if old != new:
                updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
    return report


def main() -> None:
    dds = gc.index_dds()
    raw = skill_labels()
    by_compact: dict[str, tuple[str, str]] = {}
    for label, icon in raw.items():
        for key in gc.label_keys(label):
            by_compact.setdefault(key, (label, icon))
    gc.log(f"{len(raw)} skill labels with icons")

    def choose_skill(title: str):
        return pick_skill(title, by_compact)

    skill_pages = wiki_pages({"skill"})
    report = apply(skill_pages, choose_skill, dds)

    def choose_npc(title: str):
        for key in gc.wiki_keys(title):
            if key in NPC_ICONS:
                return title, Path(NPC_ICONS[key]).stem
        return None

    npc_pages = wiki_pages({"npc"})
    report += apply(npc_pages, choose_npc, dds)

    # Build/category pages reuse skill screenshots without a matching page title.
    leftover = [
        "Heal_self_not_Other.jpg",
        "I'm_Rubber_You're_Screwed.jpg",
        "Mad_Melee_Mastery.jpg",
        "Light_in_the_Loafers.jpg",
        "Ice-shards.jpg",
        "Cold_snap.jpg",
        "Shower_of_gold.jpg",
        "Flaming_buddy.PNG",
        "1h-swivel-arm-action.png",
        "2h-swivel-arm-action.png",
    ]
    stem_alias = {
        "healselfnotother": "healselfnotother",
        "imrubberyourescrewed": "imrubberyourescrewed",
        "madmeleemastery": "madmeleemastery",
        "lightintheloafers": "lightintheloafers",
        "iceshards": "iceshards",
        "coldsnap": "coldsnap",
        "showerofgold": "goshsgloriousshowerofgold",
        "flamingbuddy": "myflamingbuddy",
        "1hswivelarmaction": "1hswivelarmaction",
        "2hswivelarmaction": "2hswivelarmaction",
    }
    extra: list[tuple[str, str]] = []
    for name in leftover:
        key = stem_alias.get(gc.compact(name))
        hit = by_compact.get(key) if key else None
        if not hit:
            hit = pick_skill(Path(name).stem, by_compact)
        if not hit:
            continue
        label, icon = hit
        dds_name = gc.find_dds(icon, dds) or gc.find_dds(f"{icon}_on", dds)
        if not dds_name:
            continue
        safe = re.sub(r'[<>:"/\\|?*\']', "", Path(name).stem).strip(" ._")
        dest = RECOVERED / (safe + ".png")
        if not gc.convert(DDS_DIR / dds_name, dest):
            continue
        new = f"/images/recovered/{dest.name}"
        extra.append((f"/images/{name}", new))
        extra.append((f"/images/recovered/{Path(name).stem}.png", new))
        report.append({"page": "(image)", "wiki": name, "gc_label": label, "icon": icon, "dds": dds_name})
    if extra:
        gc.log(f"Rewriting {len(extra)} leftover skill srcs…")
        extra = list(dict.fromkeys(extra))
        for path in CONTENT.rglob("*.json"):
            text = path.read_text(encoding="utf-8")
            updated = text
            for old, new in extra:
                if old != new:
                    updated = updated.replace(old, new)
            if updated != text:
                path.write_text(updated, encoding="utf-8")

    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    hits = sum(1 for r in report if r.get("dds"))
    gc.log(f"Skills/NPCs via .gc: {hits}/{len(report)} matches")


if __name__ == "__main__":
    main()
