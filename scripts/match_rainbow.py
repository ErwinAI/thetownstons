"""Match rainbow-item wiki images to client inventory icons.

Only apply a hit when the wiki image/title encodes a real set token
(Ghost3, Cloth3, …) or a uniquely named DDS. No fuzzy joke-title scoring.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "wiki"
PUBLIC_IMAGES = ROOT / "public" / "images"
RECOVERED = PUBLIC_IMAGES / "recovered"
DDS_DIR = Path(r"C:\Users\me\Dungeon_Runners_Client_666\dravex_v1.0.0.0_by_atom0s")
REPORT = ROOT / "archive" / "rainbow-matches.json"
TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")

# Unique item → DDS. Keys are compacted title or image-stem fragments.
NAMED = {
    "tentonhammer": "Icon_Weapon_2H_TenTonHammer.dds",
    "myprettypuncturer": "icon_Weapon_Pick_1H_MyPrettyPuncture.dds",
    "myprettypuncture": "icon_Weapon_Pick_1H_MyPrettyPuncture.dds",
    "skulliosis": "icon_Weapon_Pick_1H_Skulliosis.dds",
    "skeetor": "icon_Weapon_Pick_1H_Skeeter.dds",
    "skeeter": "icon_Weapon_Pick_1H_Skeeter.dds",
    "duncesgeniuscap": "Fantasiahat_01_icon.dds",
    "wizardhat": "Fantasiahat_01_icon.dds",
    "seabirdprojectileprotectorofthescallywag": "Cloth_Pirate_01_Helm_Icon.dds",
    "imagepiratehat": "Cloth_Pirate_01_Helm_Icon.dds",
    "piratehat": "Cloth_Pirate_01_Helm_Icon.dds",
    "portablepoopdecks": "Cloth_Pirate_01_Shoulder_Icon.dds",
    "saltytoesofthelowtide": "Cloth_Pirate_01_Boots_Icon.dds",
    "billysggoat": "Helmet_Icon_Mask.dds",
    "skullmask": "Helmet_Icon_Mask.dds",
    "uberwand": "Weapon_Wand_Blue_Pearls_icon.dds",
    "superiorwandofsuperiority": "Weapon_Wand_Blue_Pearls_icon.dds",
    "staffofrarrr": "Weapon_Staff_Gnarly_icon.dds",
    "staffofrarr": "Weapon_Staff_Gnarly_icon.dds",
    "sissistaff": "Weapon_Claweye_Staff_weapon_icon.dds",
    "sissiratsbrotherscousinsroomatesstaffofsomethingreallyawesome": "Weapon_Claweye_Staff_weapon_icon.dds",
    "sissiratssupersissysmasherofstench": "Weapon_Runed_Club_poison_weapon_icon.dds",
    "weaponrunedclubpoisonweaponicon": "Weapon_Runed_Club_poison_weapon_icon.dds",
    "kingscoins": "Voucher_King's_Coins_Icon.dds",
    "deathshabit": "Ghost_3_Body_icon.dds",
    "thehorror": "Ghost_3_Body_icon.dds",
    "deathshead": "Ghost_3_Helm_icon.dds",
    "deathsgrip": "Ghost_3_Gloves_Icon.dds",
    "deathstwolegs": "Ghost_3_Boot_icon.dds",
    "deathsdisdain": "Ghost_3_Shoulder_icon.dds",
    "thecondemned": "Ghost_3_Helm_icon.dds",
    "themanipulators": "Ghost_3_Gloves_Icon.dds",
    "themerciless": "Ghost_3_Shoulder_icon.dds",
    "thenadir": "Ghost_3_Boot_icon.dds",
    "manesmiter": "Ghost_4_Helm_icon.dds",
    "manesribcage": "Ghost_4_Body_icon.dds",
    "manesscapulae": "Ghost_4_Shoulder_icon.dds",
    "manesphalanges": "Ghost_4_Gloves_Icon.dds",
    "manesmetatarsals": "Ghost_4_Boot_icon.dds",
    "threadzwrap": "Mythic_Cloth_01_Body_Icon.dds",
    "threadzhat": "Mythic_Cloth_01_Helm_Icon.dds",
    "threadztoeticklers": "Mythic_Cloth_01_Boots_Icon.dds",
    "threadzfingerwarmers": "Mythic_Cloth_01_Gloves_Icon.dds",
    "threadzearprotectors": "Mythic_Cloth_01_Shoulders_Icon.dds",
    "thelateknightscap": "Plate_05_Helm_Dark_icon.dds",
    "thelateknightsgrievances": "Plate_05_Boots_Dark_icon.dds",
    "thelateknightsstacks": "Plate_05_Shoulder_Dark_icon.dds",
    "thelateknightsgauntlets": "Plate_05_Gloves_Dark_icon.dds",
    "darkplategauntlets": "Plate_05_Gloves_Dark_icon.dds",
    "kingsjumpsuit": "Body_Icon_Cloth03.dds",
    "horrifictaint": "Body_Icon_Cloth03.dds",
    "emeraldclothsuit": "Body_Icon_Cloth03.dds",
    "cloth3killerthreads": "Body_Icon_Cloth03.dds",
    "foldingchairofthemangledfoot": "Weapon_Icon_Folding_Chair.dds",
    "viskarsbilespitter": "Weapon_Icon_VenomSpitter.dds",
    "manesaegis": "Weapon_Icon_Shield_Skull.dds",
    "yeoldmanholecover": "Weapon_Icon_Shield_Round.dds",
    "bucklerofthedreadedbrowneye": "Weapon_Icon_Shield_Round_Small.dds",
    "theelectricfence": "Weapon_Icon_Shield_Spiked.dds",
    "stikiwikihotgluegun": "Weapon_Icon_2H_Stiki_Wiki.dds",
    "stikiwikihotgluegunmadeintownston128px": "Weapon_Icon_2H_Stiki_Wiki.dds",
    "badmutha": "Weapon_Icon_2h_Gun_09_Rainbow.dds",
    "badmuthabfg9001": "Weapon_Icon_2h_Gun_09_Rainbow.dds",
    "bfg9001": "Weapon_Icon_2h_Gun_09_Rainbow.dds",
    "dukeblaster": "Weapon_Icon_Shotgun.dds",
    "dukeblasterpopper": "Weapon_Icon_Shotgun.dds",
    "demonsniper": "Weapon_Icon_LaserRifle.dds",
    "mastercheftoxicfloodgun": "Weapon_Icon_2h_Gun_09_Green.dds",
    "masterchefstoxicfloodgun": "Weapon_Icon_2h_Gun_09_Green.dds",
    "jimisburningdesire": "Weapon_Icon_FlameTongue.dds",
    "thegavel": "Weapon_Icon_Hammer_Mallet.dds",
    "skullopener": "Weapon_Hammer_Skull_icon.dds",
    "weaponicon2hgun18": "Weapon_Icon_2h_Gun_18.dds",
    "abaddonshandycandybroomstick": "Weapon_Icon_2h_Gun_18.dds",
    "doesntsqueak": "Mouse_Ears_01_Helm_icon.dds",
    "squeaks": "Mouse_Ears_02_Helm_icon.dds",
    "mouseears01helmicon": "Mouse_Ears_01_Helm_icon.dds",
    "mouseears02helmicon": "Mouse_Ears_02_Helm_icon.dds",
    "alibubbasphantasmalshoulderpads": "Padded_1_Shoulder_icon.dds",
    "paddedshoulders": "Padded_1_Shoulder_icon.dds",
    "cooperscoolersplint": "Splint_3_Body_Icon.dds",
    "cortezscrushers": "Splint_3_Boots_Icon.dds",
    "militarysplintgreaves": "Splint_3_Boots_Icon.dds",
    "creepyfeet": "Splint_3_Boots_Icon.dds",
    "bonesplintboots": "Splint_3_Boots_Icon.dds",
    "foilcoveredthinkbox": "Plate_3_Helm_icon.dds",
    "royalplatehelm": "Plate_3_Helm_icon.dds",
    "seabasshelmofmulekicking": "Plate_3_Helm_icon.dds",
    "skewedbrassringlets": "Chain_2_Helm_icon.dds",
    "chain2coif": "Chain_2_Helm_icon.dds",
    "rippermcgeesrippermcteerex": "Weapon_2H_Axe_Rex_Normal_Icon.dds",
}

SLOT_FROM_PREFIX = (
    ("helm", "helm"),
    ("helms", "helm"),
    ("hat", "helm"),
    ("body", "body"),
    ("boots", "boots"),
    ("boot", "boots"),
    ("gloves", "gloves"),
    ("glove", "gloves"),
    ("shoulders", "shoulder"),
    ("shoulder", "shoulder"),
    ("shield", "shield"),
    ("amulet", "amulet"),
    ("ring", "ring"),
    ("2h-ranged", "ranged"),
    ("2h-weapon", "weapon"),
    ("1h-weapon", "weapon"),
    ("2h", "weapon"),
    ("1h", "weapon"),
    ("weapon", "weapon"),
)

CAT_SLOT = (
    ("rainbow helms", "helm"),
    ("rainbow body", "body"),
    ("rainbow boots", "boots"),
    ("rainbow gloves", "gloves"),
    ("rainbow shoulders", "shoulder"),
    ("rainbow shields", "shield"),
    ("rainbow amulets", "amulet"),
    ("rainbow rings", "ring"),
    ("one-handed", "weapon"),
    ("two-handed", "weapon"),
)

# Image-name set token → slot → DDS. Only when the filename itself says so.
SET_SLOTS = {
    "ghost3": {
        "helm": "Ghost_3_Helm_icon.dds",
        "body": "Ghost_3_Body_icon.dds",
        "boots": "Ghost_3_Boot_icon.dds",
        "gloves": "Ghost_3_Gloves_Icon.dds",
        "shoulder": "Ghost_3_Shoulder_icon.dds",
    },
    "ghost4": {
        "helm": "Ghost_4_Helm_icon.dds",
        "body": "Ghost_4_Body_icon.dds",
        "boots": "Ghost_4_Boot_icon.dds",
        "gloves": "Ghost_4_Gloves_Icon.dds",
        "shoulder": "Ghost_4_Shoulder_icon.dds",
    },
    "pirate": {
        "helm": "Cloth_Pirate_01_Helm_Icon.dds",
        "body": "Cloth_Pirate_01_Body_Icon.dds",
        "boots": "Cloth_Pirate_01_Boots_Icon.dds",
        "gloves": "Cloth_Pirate_01_Gloves_Icon.dds",
        "shoulder": "Cloth_Pirate_01_Shoulder_Icon.dds",
        "shield": "Weapon_Icon_Shield_Pirate_01.dds",
    },
    "threadz": {
        "helm": "Mythic_Cloth_01_Helm_Icon.dds",
        "body": "Mythic_Cloth_01_Body_Icon.dds",
        "boots": "Mythic_Cloth_01_Boots_Icon.dds",
        "gloves": "Mythic_Cloth_01_Gloves_Icon.dds",
        "shoulder": "Mythic_Cloth_01_Shoulders_Icon.dds",
    },
    "lateknight": {
        "helm": "Plate_05_Helm_Dark_icon.dds",
        "body": "Plate_05_Body_Dark_icon.dds",
        "boots": "Plate_05_Boots_Dark_icon.dds",
        "gloves": "Plate_05_Gloves_Dark_icon.dds",
        "shoulder": "Plate_05_Shoulder_Dark_icon.dds",
        "shield": "Weapon_Icon_Shield_Plate_05_Dark.dds",
    },
    "splint3": {
        "helm": "Splint_3_Helm_icon.dds",
        "body": "Splint_3_Body_Icon.dds",
        "boots": "Splint_3_Boots_Icon.dds",
        "gloves": "Splint_3_Gloves_Icon.dds",
        "shoulder": "Splint_3_Shoulder_icon.dds",
    },
    "chain2": {
        "helm": "Chain_2_Helm_icon.dds",
        "body": "Chain_2_Body_icon.dds",
        "boots": "Chain_2_Boot_icon.dds",
        "gloves": "Chain_2_Gloves_Icon.dds",
        "shoulder": "Chain_2_Shoulder_icon.dds",
    },
    "plate3": {
        "helm": "Plate_3_Helm_icon.dds",
        "body": "Plate_3_Body_Icon.dds",
        "boots": "Plate_3_Boots_Icon.dds",
        "gloves": "Plate_3_Gloves_Icon.dds",
        "shoulder": "Plate_3_Shoulder_icon.dds",
    },
    "cloth3": {
        "body": "Body_Icon_Cloth03.dds",
    },
    "padded1": {
        "helm": "Padded_1_Helm_icon.dds",
        "body": "Padded_1_Body_icon.dds",
        "boots": "Padded_1_Boot_icon.dds",
        "gloves": "Padded_1_Gloves_icon.dds",
        "shoulder": "Padded_1_Shoulder_icon.dds",
    },
}

SET_PATTERNS = (
    (re.compile(r"ghost[_ ]?3|ghost3"), "ghost3"),
    (re.compile(r"ghost[_ ]?4|ghost4"), "ghost4"),
    (re.compile(r"cloth[_ ]?pirate|pirate[_ ]?0?1|piratehat"), "pirate"),
    (re.compile(r"threadz"), "threadz"),
    (re.compile(r"late[_ ]?knight|dark[_ ]?plate"), "lateknight"),
    (re.compile(r"military[_ ]?splint|bone[_ ]?splint|cooler[_ ]?splint|splint[_ ]?3"), "splint3"),
    (re.compile(r"chain[_ ]?2|chain2"), "chain2"),
    (re.compile(r"royal[_ ]?plate"), "plate3"),
    (re.compile(r"cloth[_ ]?3|killer[_ ]?threads"), "cloth3"),
    (re.compile(r"padded[_ ]?shoulder"), "padded1"),
)


def compact(text: str) -> str:
    return TOKEN_SPLIT.sub("", Path(text).stem.lower())


def log(msg: str) -> None:
    print(msg, flush=True)


def slot_from_wiki(image: str, cats: list[str]) -> str | None:
    stem = Path(image).stem.lower()
    for prefix, slot in SLOT_FROM_PREFIX:
        if stem.startswith(prefix) or f"{prefix}-" in stem[:24] or f"{prefix}_" in stem[:24]:
            return slot
    joined = " ".join(cats).lower()
    for needle, slot in CAT_SLOT:
        if needle in joined:
            return slot
    return None


def wiki_base(image: str) -> str:
    stem = Path(unquote(image)).stem
    stem = re.sub(r"^(image[_:]?)", "", stem, flags=re.I)
    stem = re.sub(
        r"^(1h-?weapon[-_]|2h-?ranged[-_]|2h-?weapon[-_]|1h[-_]|2h[-_]|"
        r"amulet[-_]|ring[-_]|body[-_]|boots[-_]|boot[-_]|gloves[-_]|"
        r"helm[-_]|helms[-_]|shoulder[-_]|shoulders[-_]|shield[-_]|weapon[-_])",
        "",
        stem,
        flags=re.I,
    )
    stem = re.sub(r"_?64px$", "", stem, flags=re.I)
    stem = re.sub(r"_?128px$", "", stem, flags=re.I)
    return stem.strip("-_ ")


def convert(src: Path, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(src) as im:
            rgba = im.convert("RGBA")
            if max(im.size) > 256:
                rgba.thumbnail((256, 256), Image.Resampling.LANCZOS)
            rgba.save(dest, format="PNG")
        return dest.exists() and dest.stat().st_size > 32
    except OSError as exc:
        log(f"fail {src.name}: {exc}")
        return False


def named_hit(image: str, title: str) -> str | None:
    keys = {compact(wiki_base(image)), compact(title), compact(image)}
    keys.discard("")
    for key in keys:
        if key in NAMED:
            return NAMED[key]
    return None


def set_hit(image: str, title: str, cats: list[str]) -> str | None:
    blob = f"{unquote(image)} {title}".lower()
    slot = slot_from_wiki(image, cats)
    for pattern, set_key in SET_PATTERNS:
        if pattern.search(blob):
            mapping = SET_SLOTS[set_key]
            if slot and slot in mapping:
                return mapping[slot]
            if len(mapping) == 1:
                return next(iter(mapping.values()))
    return None


def pick(image: str, title: str, cats: list[str]) -> str | None:
    return named_hit(image, title) or set_hit(image, title, cats)


def original_wiki_name(src: str, images: list[str]) -> str:
    name = unquote(src).replace("\\", "/").split("/")[-1]
    if name.startswith("recovered/"):
        name = name.split("/", 1)[1]
    for listed in images:
        listed_name = unquote(listed).replace("\\", "/").split("/")[-1]
        if compact(listed_name) == compact(name) or Path(listed_name).stem == Path(name).stem:
            return listed_name
    return name


def is_keep_local(src: str) -> bool:
    """Real screenshot already on disk (not a previous recovered guess)."""
    rel = unquote(src).lstrip("/").replace("\\", "/")
    if rel.startswith("images/recovered/"):
        return False
    if not rel.startswith("images/"):
        return False
    return (PUBLIC_IMAGES / rel[len("images/") :]).is_file()


def rainbow_pages() -> list[dict]:
    pages = []
    for path in CONTENT.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title") or ""
        if title.startswith("Category:"):
            continue
        cats = data.get("categories") or []
        if not any("rainbow" in c.lower() for c in cats):
            continue
        pages.append({"path": path, "data": data})
    return pages


def main() -> None:
    log("Matching rainbow pages from image names / unique DDS…")

    report = []
    replacements: list[tuple[str, str]] = []
    recovered = 0
    for item in rainbow_pages():
        data = item["data"]
        html = data.get("html") or ""
        listed = [unquote(s) for s in (data.get("images") or [])]
        srcs = re.findall(r'src="(/images/[^"]+)"', html)
        seen = set()
        for src in srcs:
            name = original_wiki_name(src, listed)
            key = name.lower()
            if key in {"magnify-clip.png", "exclamation.png"} or name in seen:
                continue
            if "image_missing" in key:
                continue
            seen.add(name)
            if is_keep_local(src):
                report.append({"page": data.get("title"), "wiki": name, "dds": None, "kept": src})
                continue
            dds = pick(name, data.get("title") or "", data.get("categories") or [])
            if not dds:
                original = f"/images/{name}"
                if src != original:
                    replacements.append((src, original))
                report.append({"page": data.get("title"), "wiki": name, "dds": None})
                continue
            safe = re.sub(r'[<>:"/\\|?*\']', "", Path(name).stem)
            dest = RECOVERED / (safe + ".png")
            ok = convert(DDS_DIR / dds, dest)
            report.append({
                "page": data.get("title"),
                "wiki": name,
                "dds": dds,
                "recovered": str(dest.relative_to(ROOT)) if ok else None,
            })
            if not ok:
                continue
            recovered += 1
            new = f"/images/recovered/{dest.name}"
            replacements.append((src, new))
            replacements.append((f"/images/{name}", new))

    replacements = list(dict.fromkeys(replacements))
    log(f"Rewriting {len(replacements)} srcs…")
    for item in rainbow_pages():
        path = item["path"]
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in replacements:
            if old != new:
                updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    hit = sum(1 for r in report if r.get("dds"))
    kept = sum(1 for r in report if r.get("kept"))
    log(f"Rainbow: {hit}/{len(report)} named matches, kept {kept} local shots, wrote {recovered} icons")


if __name__ == "__main__":
    main()
