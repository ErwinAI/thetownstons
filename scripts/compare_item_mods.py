"""Extract item prefix/postfix labels from client ModPAL files and compare to Name Descriptors."""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_gc as gc

MOD_DIRS = [
    gc.DDS_DIR,
    gc.DDS_DIR / "items" / "modpal",
]
SKIP = {"deprecated", "crafted", "levelprefix", "binder", "sharedarmor", "weaponmodpal"}
LABEL_RE = re.compile(r'Label\s*=\s*"((?:[^"\\]|\\.)*)"')
TYPE_RE = re.compile(r"LabelType\s*=\s*(\w+)")
QUAL_RE = re.compile(r"Quality\s*=\s*(\w+)")
EXTENDS_RE = re.compile(r"extends\s+([\w.]+)")
STAT_MAP = {
    "strength": "STR",
    "agility": "AGI",
    "endurance": "END",
    "intellect": "INT",
    "meleeattackrating": "Melee AR",
    "rangedattackrating": "Ranged AR",
    "defenserating": "Defense",
    "meleedamage": "+Melee dmg",
    "rangeddamage": "+Ranged dmg",
    "crushingdamage": "+Crushing",
    "piercingdamage": "+Piercing",
    "slashingdamage": "+Slashing",
    "firedamage": "+Fire",
    "icedamage": "+Ice",
    "divinedamage": "+Divine",
    "shadowdamage": "+Shadow",
    "poisondamage": "+Poison",
    "fireresist": "Fire resist",
    "iceresist": "Ice resist",
    "divineresist": "Divine resist",
    "shadowresist": "Shadow resist",
    "poisonresist": "Poison resist",
    "healthregen": "Health regen",
    "manaregen": "Mana regen",
    "speed": "Speed",
}
WIKI_POSTFIX = {
    "beetle": "END",
    "hippo": "STR",
    "penguin": "STR, END",
    "ant": "STR, END",
    "liger": "STR, END",
    "tigon": "STR, AGI",
    "panda": "STR, AGI",
    "tarantula": "STR, AGI",
    "manatee": "AGI, END",
    "newt": "AGI, END",
    "bonobo": "AGI, END",
    "dragonfly": "AGI, INT",
    "squid": "AGI, INT",
    "blowfish": "AGI, INT",
    "greyhound": "END",
    "hawk": "AGI",
    "starfish": "END, INT",
    "armadillo": "END, INT",
    "unicorn": "END, INT",
    "wallaby": "END, INT",
    "noggin": "INT",
    "turtle": "END",
    "beaver": "STR, END, INT",
    "buckaroo": "AGI, END, INT",
    "bunny": "AGI, END",
    "hog": "STR, END",
    "platypus": "INT",
    "snapper": "END",
    "wombat": "END, INT",
    "battle": "STR, END, INT",
    "hysteria": "AGI, END",
    "rage": "STR, END",
    "bovine": "AGI",
    "flipside": "STR, AGI, INT",
    "ghetto": "STR, END",
    "monkey": "AGI, END, INT",
    "muskrat": "AGI, INT",
    "nutria": "STR, INT",
    "party": "AGI, END",
    "reactor": "STR",
    "rendezvouspoint": "AGI",
    "gerbil": "END, INT",
    "ladybug": "AGI, INT",
    "sugarglider": "AGI",
    "wasp": "AGI, END, INT",
    "roadkill": "END, INT",
    "spammer": "AGI, END, INT",
    "termite": "END, INT",
    "yeti": "AGI",
    "crocodile": "END",
    "sasquatch": "STR",
    "jackalope": "AGI",
    "dodo": "INT",
    "clam": "STR, END",
    "rhino": "STR, INT",
    "donkey": "AGI, INT",
    "llama": "AGI, END",
    "rooster": "END, INT",
    "lobster": "STR, END, INT",
    "butterfly": "AGI, END, INT",
    "chinchilla": "STR, AGI, END",
}
WIKI_PREFIX = {
    "stitching": "+Piercing",
    "carving": "+Slashing",
    "slugging": "+Melee dmg",
    "molten": "+Fire",
    "revived": "Health regen",
}


def compact(text: str) -> str:
    return gc.TOKEN_SPLIT.sub("", (text or "").lower())


def stats_from_extends(name: str) -> str:
    leaf = name.split(".")[-1]
    parts = []
    for chunk in re.findall(r"[A-Za-z]+", leaf):
        key = chunk.lower().rstrip("bms")
        if key in STAT_MAP:
            parts.append(STAT_MAP[key])
        elif chunk.lower() in STAT_MAP:
            parts.append(STAT_MAP[chunk.lower()])
    # rstrip('bms') is too aggressive (e.g. EnduranceB -> endurance). Use explicit B suffix.
    return ""


def stats_from_extends2(name: str) -> str:
    leaf = name.split(".")[-1]
    tokens = re.findall(r"[A-Z][a-z]+(?:[A-Z][a-z]+)*B?", leaf)
    if not tokens:
        tokens = re.findall(r"[A-Za-z]+", leaf)
    parts = []
    for token in tokens:
        raw = token[:-1] if token.endswith("B") or token.endswith("M") else token
        key = raw.lower()
        if key in STAT_MAP:
            parts.append(STAT_MAP[key])
    return ", ".join(parts)


def parse_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    rows = []
    for block in re.finditer(
        r"extends\s+([\w.]+)\s*\{([\s\S]*?)\n\s*\}",
        text,
    ):
        inner = block.group(2)
        label_m = LABEL_RE.search(inner)
        type_m = TYPE_RE.search(inner)
        if not label_m or not type_m:
            continue
        label = label_m.group(1)
        if label in {"of the", "NONE", "PREFIX", "SUFFIX"}:
            continue
        qual = QUAL_RE.search(inner)
        rows.append({
            "file": path.stem,
            "label": label,
            "kind": type_m.group(1),
            "quality": (qual.group(1) if qual else "").upper(),
            "stats": stats_from_extends2(block.group(1)),
            "extends": block.group(1).split(".")[-1],
        })
    return rows


def main() -> None:
    files: list[Path] = []
    for folder in MOD_DIRS:
        if not folder.exists():
            continue
        for path in folder.glob("*ModPAL.gc"):
            stem = path.stem.lower()
            if any(skip in stem for skip in SKIP):
                continue
            if "crafted" in stem:
                continue
            files.append(path)
    rows: list[dict] = []
    for path in files:
        rows.extend(parse_file(path))
    print(f"{len(files)} ModPAL files, {len(rows)} labeled mods")

    post = [r for r in rows if r["kind"] == "POSTFIX"]
    pre = [r for r in rows if r["kind"] == "PREFIX"]
    by_label: dict[str, dict] = {}
    for row in post:
        key = compact(row["label"])
        prev = by_label.get(key)
        if not prev or (row["stats"] and not prev["stats"]):
            by_label[key] = row

    print("\n=== POSTFIX vs Name Descriptors ===")
    missing_wiki = []
    mismatch = []
    for key, row in sorted(by_label.items(), key=lambda kv: kv[1]["label"].lower()):
        wiki = WIKI_POSTFIX.get(key)
        if wiki is None:
            # noggin' apostrophe
            wiki = WIKI_POSTFIX.get(key.rstrip("'"))
        if wiki is None:
            missing_wiki.append(row)
            continue
        dump = row["stats"] or "?"
        wiki_set = {p.strip() for p in wiki.split(",")}
        dump_set = {p.strip() for p in dump.split(",") if p.strip()}
        if wiki_set != dump_set and dump != "?":
            mismatch.append((row["label"], wiki, dump, row["file"]))

    print(f"wiki postfix names: {len(WIKI_POSTFIX)}")
    print(f"dump unique postfix: {len(by_label)}")
    print(f"on wiki, missing from this parse: {len(WIKI_POSTFIX) - (len(by_label) - len(missing_wiki))}")
    print(f"in dump, not on wiki: {len(missing_wiki)}")
    print(f"stat mismatches: {len(mismatch)}")
    print("\nNot on wiki:")
    for row in missing_wiki:
        print(f"  {row['label']:24} {row['stats'] or row['extends']:28} [{row['file']} {row['quality']}]")
    if mismatch:
        print("\nStat mismatches (wiki -> dump):")
        for label, wiki, dump, src in mismatch:
            print(f"  {label:24} wiki={wiki:20} dump={dump:20} [{src}]")

    wiki_pre_missing = []
    pre_by = {}
    for row in pre:
        key = compact(row["label"])
        pre_by.setdefault(key, row)
    print(f"\n=== PREFIX ===")
    print(f"dump unique prefixes: {len(pre_by)}")
    for key, meaning in WIKI_PREFIX.items():
        if key not in pre_by:
            wiki_pre_missing.append(key)
    print(f"wiki prefixes missing in dump: {wiki_pre_missing}")
    print("wiki prefixes found:")
    for key, meaning in WIKI_PREFIX.items():
        row = pre_by.get(key)
        if row:
            print(f"  {row['label']:24} wiki={meaning:16} dump={row['stats'] or row['extends']}")

    # group prefixes by quality for a short sample
    by_q = defaultdict(list)
    for row in pre_by.values():
        by_q[row["quality"]].append(row)
    for quality, items in sorted(by_q.items()):
        print(f"\n{quality or '?'} prefixes ({len(items)}):")
        for row in sorted(items, key=lambda r: r["label"].lower())[:12]:
            print(f"  {row['label']:24} {row['stats'] or row['extends']}")
        if len(items) > 12:
            print(f"  … +{len(items) - 12} more")


if __name__ == "__main__":
    main()
