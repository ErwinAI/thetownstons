"""Recover leftover gear, unique, skill/effect, and quest icons from client .gc/DDS."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_gc as gc
import match_gc_skills as skills

ROOT = gc.ROOT
CONTENT = gc.CONTENT
RECOVERED = gc.RECOVERED
DDS_DIR = gc.DDS_DIR
REPORT = ROOT / "archive" / "gc-rest-matches.json"

SKIP_NAMES = {
    "magnify-clip.png",
    "exclamation.png",
    "image_missing_rt_64px.jpg",
    "image_missing.jpg",
}
SCREENSHOT = re.compile(
    r"(screenshot|guide-|guild-|maintitle|maintopic|contributor|wikinews|"
    r"^new\d|boss[-_]|monster[-_]|mobknight|orok_|dungeonrunners|"
    r"algernon\d|vv\d|wn\d|mm\d|fm\d|hdol|both\.jpg|pool\.jpg|mask\.jpg)",
    re.I,
)
WIKI_PREFIX = re.compile(
    r"^(image:|file:|effect[_-]?icon[-_]?|skill[-_]|item[-_]|"
    r"1h[-_]?weapon[-_]|2h[-_]?weapon[-_]|2h[-_]?ranged[-_]|"
    r"1h[-_]|2h[-_]|amulet[-_]|ring[-_]|body[-_]|boots[-_]|"
    r"gloves[-_]|helm[-_]?s?[-_]|shoulder[-_]?s?[-_]|shield[-_]|weapon[-_])",
    re.I,
)
NEAR_TD = re.compile(
    r'src="(/images/[^"]+)"[^>]*>.*?</td>\s*<td>(?:<a[^>]*>)?([^<]{2,80})',
    re.S,
)
PX = re.compile(r"(_?64px|_?43px|_on|_off|_display.*|_top.*|_side.*|_bottom.*)$", re.I)
SET_RE = re.compile(r"(ghost|leather|chain|cloth|scale|splint|padded)[-_]?(\d+)", re.I)
SLOT_RE = re.compile(
    r"^(body|helm|helms|boots|boot|gloves|glove|shoulder|shoulders|shield|amulet|ring)[-_]",
    re.I,
)
MATERIALS = (
    "default", "cardboard", "wooden", "stone", "tin", "iron", "titanium",
    "obsidian", "diamond", "celestial", "uber", "rusty", "aluminum", "aluminium",
    "steel", "bronze", "silver", "gold", "mithril", "scrapmetal", "bicycle",
)
ALIASES = {
    **gc.ALIASES,
    **skills.SKILL_ALIASES,
    "goldenticket": "ticket54000601",
    "fizzdrink": "fizzwater",
    "namebrandbracelet": "namebrandbraceletrelic",
    "cheerycupofjo": "cheerycupofjorelic",
    "burglarizednecklace": "burglarizednecklacerelic",
    "certificateofincompletion": "certificateofincompletionrelic",
    "selfmadecrown": "selfmadecrownrelic",
    "spicedwristband": "spikedwristbandrelic",
    "triplechinchoker": "triplechinchokercommonrelic",
    "hotrodkey": "hotrodkeyrelic",
    "damagecurse": "meleedamagedebuff",
    "damagecursedebuff": "meleedamagedebuff",
    "damagecursedebuffon": "meleedamagedebuff",
    "bravery": "banneroffoolishbravery",
    "questreward": "moarcowbell",
    "widowersprison": "widowerprison",
    "widowsprison": "widowerprison",
    "widowscurse": "widowscurse",
    "scalemail": "scalemail",
    "ricketylid": "ricketyplate",
    "leather0hood": "leatherhoody",
    "leatherhood": "leatherhoody",
    "enfeeble": "enfeeble",
    "ghost1threads": "ghostplate",
    "ghost1mask": "ghostmask",
    "namebrandbracelet": "sissiratscommonnamebrandbraceletrelic",
    "cheerycupofjo": "sissiratsamazingcheerycupofjorelic",
    "drainbamagedebuff": "drainbamage",
    "questreward": "moarcowbell",
    "zonespawninvulnerability": "invulnerable",
    "graypaint": "greypaint",
    "wolfpeltsbrown": "wolfpelt",
    "wolfpelts": "wolfpelt",
    "goldedpumpkin": "goldpumpkin",
    "goldedearocorn": "goldearocorn",
    "serpentinering": "serpentinehoop",
    "spiderbandring": "spiderband",
    "widowmakerscommonspicedwristband": "widowmakerscommonspikedwristbandrelic",
    "spicedwristband": "spikedwristbandrelic",
    "sawedoffshotgunn": "sawedoffshotgun",
}
FORCE_DDS = {
    "questreward": "MOAR_Cowbell",
    "moarcowbell": "MOAR_Cowbell",
    "zonespawninvulnerability": "Invulnerable",
    "goldedpumpkin": "QuestItem_GoldPumpkin",
    "mixer": "QuestItem_Mixer_icon",
    "resurrectionsickness": "RessurectionSickness",
    "candies": "YummyYums",
    "audits": "QuestItem_AuditScroll",
}
TAIL_STRIP = ("debuff", "buff", "relic", "ring", "64px", "43px")
ICON_ASSIGN = re.compile(
    r"(Label|InventoryIcon|Icon|ActiveIcon|IconName)\s*=\s*("
    r'"(?:[^"\\]|\\.)*"'
    r"|[A-Za-z0-9_][\w']*)\s*;",
)
SLOT_TOKEN = {
    "body": "body",
    "helm": "helm",
    "helms": "helm",
    "boot": "boot",
    "boots": "boot",
    "glove": "glove",
    "gloves": "glove",
    "shoulder": "shoulder",
    "shoulders": "shoulder",
    "shield": "shield",
}


def norm_key(name: str) -> str:
    stem = Path(unquote(name)).stem
    stem = WIKI_PREFIX.sub("", stem)
    while True:
        nxt = PX.sub("", stem)
        if nxt == stem:
            break
        stem = nxt
    return gc.compact(stem)


def base_item_key(label: str) -> str:
    key = gc.compact(label)
    for mat in MATERIALS:
        if key.startswith(mat) and len(key) > len(mat) + 2:
            return key[len(mat) :]
    if key.endswith("relic") and len(key) > 8:
        return key[: -len("relic")]
    return key


def parse_skill_icon_names() -> dict[str, str]:
    labels: dict[str, str] = {}
    roots = [DDS_DIR / "skills", DDS_DIR / "creatures", DDS_DIR / "avatar"]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.gc"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "Label" not in text or "Icon" not in text:
                continue
            text = gc.strip_comments(text)
            last_label = None
            for kind, raw in ICON_ASSIGN.findall(text):
                val = gc.unquote_val(raw)
                if kind == "Label" and val not in {"NONE", "PREFIX", "SUFFIX"}:
                    last_label = val
                elif kind in {"Icon", "ActiveIcon", "IconName", "InventoryIcon"} and val and last_label:
                    labels.setdefault(last_label, val)
    return labels


def index_dds() -> dict[str, str]:
    out = {}
    for name in os.listdir(DDS_DIR):
        if name.lower().endswith(".dds"):
            out[name.lower()] = name
            out[gc.compact(Path(name).stem)] = name
    return out


def find_dds(icon: str, dds: dict[str, str]) -> str | None:
    if not icon:
        return None
    stem = Path(icon).stem
    hits: list[str] = []
    for cand in (
        f"{stem}_on.dds",
        f"{stem}_On.dds",
        f"{stem}.dds",
        f"{icon}.dds",
        icon,
    ):
        name = dds.get(cand.lower()) or dds.get(gc.compact(Path(cand).stem))
        if name:
            hits.append(name)
    if not hits:
        fallback = gc.find_dds(icon, {k: v for k, v in dds.items() if k.endswith(".dds")})
        if fallback:
            hits.append(fallback)
    if not hits:
        return None
    preferred = [h for h in hits if "icon" in h.lower()]
    return preferred[0] if preferred else hits[0]


def set_slot_icon(wiki_name: str, dds: dict[str, str]) -> str | None:
    raw = Path(unquote(wiki_name)).stem
    slot_m = SLOT_RE.match(raw)
    set_m = SET_RE.search(raw)
    if not slot_m or not set_m:
        return None
    slot = SLOT_TOKEN.get(slot_m.group(1).lower())
    family, num = set_m.group(1), set_m.group(2)
    if not slot:
        return None
    n = int(num)
    family_title = family[:1].upper() + family[1:].lower()
    guesses = [
        f"{family_title}_{n}_{slot}_icon",
        f"{family_title}_{n}_{slot}s_icon",
        f"{family.title()}_{n:02d}_{slot}_icon",
        f"{slot}_icon_{family}{n:02d}",
        f"{slot}_icon_{family}0{n}",
        f"Body_Icon_{family_title}{n:02d}" if slot == "body" else "",
        f"Helmet_Icon_{family_title}{n:02d}" if slot == "helm" else "",
        f"Boots_Icon_{family_title}{n:02d}" if slot == "boot" else "",
        f"Gloves_Icon_{family_title}{n:02d}" if slot == "glove" else "",
    ]
    if family.lower() == "chain":
        guesses += [
            f"Body_Icon_Chainmail{n:02d}" if slot == "body" else "",
            f"Chain_{n}_{slot}_icon",
        ]
    if family.lower() == "leather":
        guesses += [
            f"Body_Icon_Leather{n:02d}" if slot == "body" else "",
            f"Body_Icon_Leather0{n}" if slot == "body" else "",
            f"Leather_{n:02d}_{slot}_icon",
        ]
        if n == 0:
            guesses += [
                f"starting_ranger_{slot}_icon",
                f"starting_ranger_{slot}s_icon",
                "starting_ranger_helm_icon" if slot == "helm" else "",
                "starting_ranger_body_icon" if slot == "body" else "",
                "starting_ranger_boots_icon" if slot == "boot" else "",
                "starting_ranger_glove_icon" if slot == "glove" else "",
            ]
    if family.lower() == "ghost" and n == 1:
        token = {"glove": "Glove", "boot": "Boot"}.get(slot, slot.title())
        guesses.append(f"Unique_Cloth_Armor_Set_2_{token}_icon")
    if family.lower() == "scale" and n == 0:
        guesses += [f"Body_Icon_Scale04" if slot == "body" else f"{slot.title()}_Icon_Scale01"]
    for guess in guesses:
        if not guess:
            continue
        hit = find_dds(guess, dds)
        if hit:
            return hit
    # compact contains ghost3body
    want = gc.compact(f"{family}{n}{slot}")
    for key, name in dds.items():
        if "icon" in name.lower() and want in gc.compact(Path(name).stem):
            return name
    return None


def broaden(keys: set[str]) -> set[str]:
    out = set(keys)
    for key in list(keys):
        cur = key
        for tail in TAIL_STRIP:
            if cur.endswith(tail) and len(cur) > len(tail) + 3:
                cur = cur[: -len(tail)]
                out.add(cur)
        swapped = key.replace("spiced", "spiked").replace("gray", "grey").replace("golded", "gold")
        if swapped != key:
            out.add(swapped)
            out.add(base_item_key(swapped))
        if key.endswith("relic") is False:
            out.add(key + "relic")
    out |= {ALIASES.get(k, k) for k in out}
    out.discard("")
    return out


def pick_from_maps(keys: set[str], by_compact: dict[str, tuple[str, str]], dds: dict[str, str]) -> tuple[str, str, str] | None:
    for key in broaden(keys):
        if key in by_compact:
            label, icon = by_compact[key]
            dds_name = find_dds(icon, dds)
            if dds_name:
                return label, icon, dds_name
    return None


def apply_replacements(pairs: list[tuple[str, str]]) -> int:
    pairs = [(a, b) for a, b in dict.fromkeys(pairs) if a != b]
    changed = 0
    for path in CONTENT.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in pairs:
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def recovered_map() -> dict[str, str]:
    out: dict[str, str] = {}
    if not RECOVERED.exists():
        return out
    for path in RECOVERED.iterdir():
        if not path.is_file():
            continue
        dest = f"/images/recovered/{path.name}"
        for key in {norm_key(path.name), gc.compact(path.stem)}:
            if key and key not in out:
                out[key] = dest
    return out


def main() -> None:
    gc.log("Indexing items…")
    labels, rows = gc.index_gc()
    gc.LABELS.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    gc.log(f"{len(labels)} item labels")

    gc.log("Indexing skill/effect IconName…")
    skill_labels = skills.skill_labels()
    skill_labels.update(parse_skill_icon_names())
    gc.log(f"{len(skill_labels)} skill/effect labels")

    dds = index_dds()
    gc.log(f"{len(dds)} DDS keys")

    by_compact: dict[str, tuple[str, str]] = {}
    for source in (skill_labels, labels):
        for label, icon in source.items():
            if icon and "skillbook" in icon.lower():
                continue
            extra = {gc.compact(Path(icon).stem), norm_key(icon)} if icon else set()
            for key in gc.label_keys(label) | {base_item_key(label), norm_key(label)} | extra:
                if len(key) >= 4:
                    by_compact.setdefault(key, (label, icon))

    rec = recovered_map()
    report = []
    replacements: list[tuple[str, str]] = []
    wrote = 0

    src_re = re.compile(r'src="(/images/[^"]+)"')
    needed: dict[str, set[str]] = {}
    hints: dict[str, set[str]] = {}
    for path in CONTENT.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title") or ""
        html = data.get("html") or ""
        for src in src_re.findall(html):
            needed.setdefault(unquote(src), set()).add(title)
        for src, nearby in NEAR_TD.findall(html):
            text = re.sub(r"\s+", " ", nearby).strip(" \t\r\n.|")
            if text:
                hints.setdefault(unquote(src), set()).add(text)

    def title_fits(title: str, name: str) -> bool:
        if title.startswith("Category:"):
            return False
        t = gc.compact(title)
        n = norm_key(name)
        if len(t) < 6 or len(n) < 4:
            return False
        return t in n or n in t

    for src, titles in needed.items():
        name = src.replace("\\", "/").split("/")[-1]
        if name.lower() in SKIP_NAMES or "image_missing" in name.lower():
            continue
        disk = ROOT / "public" / src.lstrip("/")
        if disk.is_file():
            continue
        if SCREENSHOT.search(name):
            report.append({"wiki": name, "skip": "screenshot"})
            continue

        keys = {norm_key(name), gc.compact(Path(name).stem)}
        for hint in hints.get(src, set()):
            keys |= gc.wiki_keys(hint)
            keys.add(norm_key(hint))
            keys.add(base_item_key(hint))
        for title in titles:
            if title_fits(title, name):
                keys |= gc.wiki_keys(title)
                keys.add(norm_key(title))
                keys.add(base_item_key(title))
        keys = broaden(keys)

        rec_hit = next((rec[k] for k in keys if k in rec), None)
        if rec_hit:
            replacements.append((src, rec_hit))
            replacements.append((f"/images/{name}", rec_hit))
            report.append({"wiki": name, "reused": rec_hit, "pages": sorted(titles)[:6]})
            continue

        set_dds = set_slot_icon(name, dds)
        if set_dds:
            safe = re.sub(r'[<>:"/\\|?*\']', "", Path(name).stem).strip(" ._")
            dest = RECOVERED / (safe + ".png")
            if gc.convert(DDS_DIR / set_dds, dest):
                new = f"/images/recovered/{dest.name}"
                replacements.append((src, new))
                replacements.append((f"/images/{name}", new))
                wrote += 1
                report.append({"wiki": name, "dds": set_dds, "via": "set-slot", "pages": sorted(titles)[:6]})
                rec[norm_key(name)] = new
                continue

        picked = pick_from_maps(keys, by_compact, dds)
        if not picked:
            forced = next((FORCE_DDS[k] for k in keys if k in FORCE_DDS), None)
            if forced:
                dds_name = find_dds(forced, dds)
                if dds_name:
                    picked = (forced, forced, dds_name)
        if not picked:
            report.append({"wiki": name, "dds": None, "pages": sorted(titles)[:6]})
            continue
        label, icon, dds_name = picked
        safe = re.sub(r'[<>:"/\\|?*\']', "", Path(name).stem).strip(" ._")
        dest = RECOVERED / (safe + ".png")
        if not gc.convert(DDS_DIR / dds_name, dest):
            report.append({"wiki": name, "icon": icon, "dds": dds_name, "failed": True})
            continue
        new = f"/images/recovered/{dest.name}"
        replacements.append((src, new))
        replacements.append((f"/images/{name}", new))
        wrote += 1
        rec[norm_key(name)] = new
        report.append({
            "wiki": name,
            "gc_label": label,
            "icon": icon,
            "dds": dds_name,
            "pages": sorted(titles)[:6],
        })

    gc.log(f"Rewriting {len(set(replacements))} srcs across wiki…")
    files = apply_replacements(replacements)
    hits = sum(1 for r in report if r.get("dds") or r.get("reused"))
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    gc.log(f"Rest leftovers: {hits}/{len(report)} matched, wrote {wrote} icons, touched {files} pages")


if __name__ == "__main__":
    main()
