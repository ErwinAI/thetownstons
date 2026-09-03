"""Match wiki skill/item/NPC images to Dungeon Runners DDS icons."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import unquote

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "wiki"
PUBLIC_IMG = ROOT / "public" / "images"
RECOVERED = PUBLIC_IMG / "recovered"
DDS_DIR = Path(r"C:\Users\me\Dungeon_Runners_Client_666\dravex_v1.0.0.0_by_atom0s")
REPORT = ROOT / "archive" / "dds-matches.json"
TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")

# Wiki joke names / screenshots -> client icon files
ALIASES = {
    "triggerhappy": "rapidFire_on.dds",
    "triggerfinger": "Frenzy_on.dds",
    "triggerfingerfrenzy": "Frenzy_on.dds",
    "monsterbait": "Bait_on.dds",
    "extracrispymonsterbait": "BaitHealthModPassive_on.dds",
    "gaseousblast": "noxiousCloud_on.dds",
    "spiritofhehare": "MovementSpeed_Buff_on.dds",
    "spiritofthehare": "MovementSpeed_Buff_on.dds",
    "averagebmi": "LesserHealthNut_on.dds",
    "gymfreak": "HealthNut_on.dds",
    "bookworm": "Mental_Prowess_on.dds",
    "divineward": "DivineResist_Buff_on.dds",
    "fireward": "FireResist_Buff_on.dds",
    "iceward": "IceResist_Buff_on.dds",
    "shadowward": "ShadowResist_Buff_on.dds",
    "poisonward": "PoisonResist_Buff_on.dds",
    "divineresistance": "DivineResist_Buff_on.dds",
    "fireresistance": "FireResist_Buff_on.dds",
    "iceresistance": "IceResist_Buff_on.dds",
    "shadowresistance": "ShadowResist_Buff_on.dds",
    "poisonresistance": "PoisonResist_Buff_on.dds",
    "buildsnowman": "SummonSnowman_on.dds",
    "nippytwigs": "NippyTwigs_on.dds",
    "ontherocks": "OnTheRocks_on.dds",
    "snowglobe": "SnowGlobe_on.dds",
    "wayoftheroo": "Haste_on.dds",
    "1hswivelarmaction": "1HMeleeMastery_on.dds",
    "2hswivelarmaction": "2HMeleeMastery_on.dds",
    "awesomecleavage": "GreaterCleave_on.dds",
    "fearofgosh": "RayOfGosh_on.dds",
    "improvedshadowlightning": "ShadowLightningGreater_on.dds",
    "shivershot": "IceShot_on.dds",
    "icebolt": "Iceball_on.dds",
    "firebolt": "FireBolt_On.dds",
    "shadowbolt": "ShadowBolt_on.dds",
    "ringoffire": "Fire_Cone_on.dds",
    "pyromania": "firemastery_on.dds",
    "crispycritters": "Immolation_on.dds",
    "holyroller": "Smite_On.dds",
    "thickheadedness": "ThickSkin_on.dds",
    "spontaneousregeneration": "TrollBlood_on.dds",
    "spontaneousrengeration": "TrollBlood_on.dds",
    "banneroffoolishbravery": "Leadership_on.dds",
    "bannerofthefoolishbravery": "Leadership_on.dds",
    "bluescreenoflife": "heal_on.dds",
    "soulrend": "ShadowWordSmackdown_on.dds",
    "putridpenetration": "NoxiousShot_On.dds",
    "darkconniption": "Berserk_on.dds",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def compact(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = re.sub(r"^(image:|file:)", "", stem)
    stem = re.sub(r"^(skill-_|skill-|item-_|item-|monster-_|monster-|npc-_|npc-|effect_icon-_|effect_icon-)", "", stem)
    stem = stem.replace("_on", "").replace("-on", "")
    return TOKEN_SPLIT.sub("", stem)


def tokens(name: str) -> set[str]:
    stem = Path(name).stem.lower()
    stem = re.sub(r"^(image:|file:|skill-_|skill-|item-_|monster-_|npc-_|effect_icon-_)", "", stem)
    return {p for p in TOKEN_SPLIT.split(stem) if len(p) > 2}


def collect_needed() -> dict[str, set[str]]:
    """image filename -> wiki titles that use it"""
    needed: dict[str, set[str]] = {}
    for path in CONTENT.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title") or ""
        text = data.get("html") or ""
        for match in re.findall(r"/images/(?:recovered/)?([^\"')\s]+)", text):
            name = unquote(match).replace("\\", "/").split("/")[-1]
            if name in {"magnify-clip.png", "Exclamation.png"}:
                continue
            needed.setdefault(name, set()).add(title)
        for match in data.get("images") or []:
            name = unquote(match).replace("\\", "/").split("/")[-1]
            needed.setdefault(name, set()).add(title)
    return needed


def icon_score(dds_name: str) -> int:
    low = dds_name.lower()
    score = 0
    if low.endswith("_on.dds"):
        score += 8
    if "icon" in low:
        score += 6
    if low.startswith("ncs_"):
        score -= 4
    if any(bad in low for bad in ("tileset", "groundobject", "_spec", "emissive", "overlay")):
        score -= 6
    return score


def pick_dds(need: str, titles: set[str], by_compact: dict[str, list[str]]) -> str | None:
    keys = {compact(need)}
    for title in titles:
        keys.add(compact(title))
    keys.discard("")

    for key in list(keys):
        if key in ALIASES:
            return ALIASES[key]
        if key.endswith("ward"):
            keys.add(key[:-4] + "resistbuff")
        if key.endswith("resistance"):
            keys.add(key[:-10] + "resistbuff")

    candidates: list[str] = []
    for key in keys:
        candidates.extend(by_compact.get(key, []))
        for norm, names in by_compact.items():
            if key and (key == norm or (len(key) > 6 and (key in norm or norm in key))):
                candidates.extend(names)

    # token overlap for remaining skill-like names
    need_tokens = tokens(need)
    for title in titles:
        need_tokens |= tokens(title)
    if need_tokens and not candidates:
        for norm, names in by_compact.items():
            dt = tokens(names[0])
            if need_tokens and dt and need_tokens <= dt or (need_tokens & dt and len(need_tokens & dt) >= 2):
                candidates.extend(names)

    if not candidates:
        return None
    uniq = list(dict.fromkeys(candidates))
    uniq.sort(key=lambda n: (-icon_score(n), len(n)))
    return uniq[0]


def convert_dds(src: Path, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(src) as im:
            w, h = im.size
            if w > 256 or h > 256:
                log(f"skip large {src.name} {im.size}")
                return False
            im.convert("RGBA").save(dest, format="PNG")
        return dest.exists() and dest.stat().st_size > 32
    except Exception as exc:
        log(f"DDS fail {src.name}: {exc}")
        return False


def main() -> None:
    if not DDS_DIR.exists():
        raise SystemExit(f"DDS folder missing: {DDS_DIR}")
    log("Indexing DDS names…")
    by_compact: dict[str, list[str]] = {}
    for name in os.listdir(DDS_DIR):
        if not name.lower().endswith(".dds"):
            continue
        by_compact.setdefault(compact(name), []).append(name)
    needed = collect_needed()
    log(f"{len(needed)} wiki image names, {sum(len(v) for v in by_compact.values())} DDS files")

    matches = []
    replacements: list[tuple[str, str]] = []
    recovered = 0
    for name in sorted(needed):
        dds_name = pick_dds(name, needed[name], by_compact)
        if not dds_name:
            matches.append({"wiki": name, "dds": None, "pages": sorted(needed[name])[:5]})
            continue
        dest = RECOVERED / (Path(name).stem + ".png")
        ok = convert_dds(DDS_DIR / dds_name, dest)
        matches.append({
            "wiki": name,
            "dds": dds_name,
            "recovered": str(dest.relative_to(ROOT)) if ok else None,
            "pages": sorted(needed[name])[:5],
        })
        if not ok:
            continue
        recovered += 1
        stem = Path(name).stem
        replacements.append((f"/images/{name}", f"/images/recovered/{dest.name}"))
        replacements.append((f"/images/recovered/{stem}.png", f"/images/recovered/{dest.name}"))

    log(f"Rewriting {len(replacements)} srcs in content…")
    replacements = list(dict.fromkeys(replacements))
    for json_path in CONTENT.rglob("*.json"):
        text = json_path.read_text(encoding="utf-8")
        updated = text
        for old, new in replacements:
            if old != new:
                updated = updated.replace(old, new)
        if updated != text:
            json_path.write_text(updated, encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(matches, indent=2), encoding="utf-8")
    log(f"Recovered {recovered} icons -> {RECOVERED}")


if __name__ == "__main__":
    main()
