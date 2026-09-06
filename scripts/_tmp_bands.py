from pathlib import Path
import json
import re

ROOT = Path(r"C:\Users\me\Dungeon_Runners_Client_666\dravex_v1.0.0.0_by_atom0s")
WIKI = Path(r"C:\Users\me\Projects\thetownstons\content\wiki")


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*?$", "", text, flags=re.M)
    return text


LABEL_Q = re.compile(r'Label\s*=\s*"((?:[^"\\]|\\.)*)"')
LABEL_U = re.compile(r"Label\s*=\s*([^;\n]+);")
HEAD = re.compile(r"^(\s*)([A-Za-z0-9_.'*]+)\s+extends\s+([A-Za-z0-9_.']+)", re.M)


def balanced(text: str, brace_at: int) -> str:
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


labels: dict[str, str] = {}
for pal in list(ROOT.rglob("*PAL.gc")) + list((ROOT / "items" / "pal").rglob("*.gc")):
    try:
        text = pal.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    text_nc = strip_comments(text)
    for m in HEAD.finditer(text_nc):
        name = m.group(2)
        brace = text_nc.find("{", m.end())
        if brace < 0 or brace - m.end() > 80:
            continue
        body = balanced(text_nc, brace)
        if not body:
            continue
        lq = LABEL_Q.search(body)
        lab = ""
        if lq:
            lab = lq.group(1)
        else:
            lu = LABEL_U.search(body)
            if lu:
                lab = lu.group(1).strip().strip('"')
        if lab and lab not in {"NONE", "PREFIX", "SUFFIX"}:
            labels[name] = lab
            labels[f"{pal.stem}.{name}"] = lab

print("labels", len(labels))

wiki_titles: dict[str, str] = {}
for p in WIKI.rglob("*.json"):
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    title = data.get("title") or ""
    if title.startswith("Category") or title.startswith("Talk"):
        continue
    wiki_titles[title.lower()] = title

block_start = re.compile(
    r"^(\s*)([A-Za-z0-9_.'*]+)\s+extends\s+(ItemTimeline\.MythicPhase\d+(?:Link)?|ItemTimeline\.MythicSingleItemStart|SingleItemGenerator|RandomItemGenerator)",
    re.M,
)
item_re = re.compile(r"Item\s*=\s*([A-Za-z0-9_.']+)")

rows = []
for ig in ROOT.rglob("*IG.gc"):
    path = str(ig).replace("/", "\\")
    low = path.lower()
    if any(s in low for s in ["wishingwell", "tokenreward", "world\\test", "customboss"]):
        continue
    if "mythic" not in ig.name.lower() and "items\\ig" not in low:
        continue
    try:
        text = strip_comments(ig.read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        continue
    for m in block_start.finditer(text):
        timeline = m.group(3)
        chunk = text[m.end() : m.end() + 600]
        im = item_re.search(chunk)
        if not im:
            continue
        item = im.group(1)
        short = item.split(".")[-1]
        file_stem = Path(item.replace(".", "/") ).name if "." in item else ""
        lab = (
            labels.get(item)
            or labels.get(short)
            or labels.get(f"{item.split('.')[-2]}.{short}" if item.count(".") else "")
            or ""
        )
        if "Phase" in timeline:
            phase = int(re.search(r"(\d+)", timeline).group(1))
            kind = "phase"
        elif "SingleItemStart" in timeline:
            phase = 1
            kind = "start"
        else:
            phase = 1
            kind = "unbanded"
        fighter = "fighter" in low
        rows.append((phase, kind, lab or short, item, str(ig.relative_to(ROOT)), fighter))


def skip_label(lab: str, item: str) -> bool:
    if not lab or lab in {"DIVINE", "FIRE", "ICE", "POISON", "SHADOW"}:
        return True
    last = item.split(".")[-1]
    if "GeneratedMythic" in last and "_" in last:
        return True
    return False


mins = {1: 15, 2: 35, 3: 55, 4: 75, 5: 95, 6: 100}
for phase in range(1, 6):
    print(f"\n===== BAND {mins[phase]}+  (phase {phase}) =====")
    seen: set[str] = set()
    items = []
    for ph, kind, lab, item, rel, fighter in rows:
        if ph != phase or kind == "unbanded":
            continue
        if skip_label(lab, item):
            continue
        key = lab.lower()
        if key in seen:
            continue
        seen.add(key)
        wiki = wiki_titles.get(key)
        mark = " [fighter set]" if fighter else ""
        items.append((lab, wiki, mark))
    for lab, wiki, mark in sorted(items, key=lambda x: x[0].lower()):
        w = f"  wiki={wiki}" if wiki else "  NO WIKI"
        print(f"  {lab}{mark}{w}")

print("\n===== UNBANDED named (shared pool from 15) =====")
seen2: set[str] = set()
for ph, kind, lab, item, rel, fighter in rows:
    if kind != "unbanded" or skip_label(lab, item):
        continue
    if lab.lower() in seen2:
        continue
    seen2.add(lab.lower())
    wiki = wiki_titles.get(lab.lower())
    w = f"wiki={wiki}" if wiki else "NO WIKI"
    print(f"  {lab}  {w}  ({rel})")
