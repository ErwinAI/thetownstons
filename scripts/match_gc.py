"""Map wiki rainbow items to inventory icons using client .gc Label/InventoryIcon."""
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
REPORT = ROOT / "archive" / "gc-rainbow-matches.json"
LABELS = ROOT / "archive" / "gc-labels.json"
TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")
COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.S)
HEADER = re.compile(
    r"([A-Za-z0-9_][\w]*)\s*(?:extends\s+([\w.]+))?\s*\{",
    re.S,
)
ASSIGN = re.compile(
    r"(Label|InventoryIcon)\s*=\s*(" r'"(?:[^"\\]|\\.)*"' r"|[A-Za-z_][\w']*)\s*;",
)
# Wiki title compact → GC label compact when the client spelling differs.
ALIASES = {
    "abaddonshandycandybroomstick": "abaddonshandycandyboomstick",
    "docwyverns": "docwyvernsboots",
    "sissiratsbrotherscousinsroomatesstaffofsomethingreallyawesome": (
        "sissiratsbrotherscousinsroommatesstaffofsomethingreallyawesome"
    ),
    "fuzzytrimmedluvcuffs": "fuzztrimmedluvcuffs",
    "kingscoins": "kingscoinsx20",
    "najsflakjacket": "naisflakjacket",
    "najasflakjacket": "naisflakjacket",
    "doppelgangersmeathooks": "dopplegangersmeathooks",
    "superiorwandofsuperiority": "superiorwandofstupendoussuperiority",
    "murdaksmonstermainers": "murdaksmonstermaimers",
}

SKIP_DIRS = {"effects", "misc", "world", "ncs", "sound", "sounds", "music"}


def log(msg: str) -> None:
    print(msg, flush=True)


def compact(text: str) -> str:
    return TOKEN_SPLIT.sub("", text.lower())


def strip_comments(text: str) -> str:
    text = COMMENT_BLOCK.sub("", text)
    out: list[str] = []
    i = 0
    in_str = False
    while i < len(text):
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def unquote_val(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1].replace('\\"', '"')
    return raw


def matching_brace(text: str, start: int) -> int:
    """Index of the `}` that closes text[start] == `{`, ignoring braces in strings."""
    depth = 0
    i = start
    in_str = False
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\" and i + 1 < len(text):
                i += 2
                continue
            if ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(text)


def first_description(inner: str) -> str:
    pos = 0
    while True:
        m = HEADER.search(inner, pos)
        if not m:
            return ""
        end = matching_brace(inner, m.end() - 1)
        if m.group(1) == "Description":
            return inner[m.end() : end]
        pos = end + 1


def parse_gc(text: str) -> list[dict]:
    text = strip_comments(text)
    classes: list[dict] = []

    def walk(body: str, prefix: str) -> None:
        pos = 0
        while True:
            m = HEADER.search(body, pos)
            if not m:
                return
            name, parent = m.group(1), m.group(2)
            end = matching_brace(body, m.end() - 1)
            inner = body[m.end() : end]
            pos = end + 1
            if name == "Description":
                continue
            dotted = f"{prefix}.{name}" if prefix else name
            label = icon = None
            for kind, raw in ASSIGN.findall(first_description(inner)):
                val = unquote_val(raw)
                if kind == "Label" and val not in {"NONE", "PREFIX", "SUFFIX"}:
                    label = val
                elif kind == "InventoryIcon":
                    icon = val
            classes.append({
                "name": dotted,
                "short": name,
                "parent": parent,
                "label": label,
                "icon": icon,
            })
            walk(inner, dotted)

    walk(text, "")
    return classes


def index_gc() -> tuple[dict[str, str], list[dict]]:
    by_name: dict[str, dict] = {}
    parsed = 0
    for path in DDS_DIR.rglob("*.gc"):
        if any(part.lower() in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "Label" not in text and "InventoryIcon" not in text:
            continue
        parsed += 1
        for cls in parse_gc(text):
            by_name[cls["name"]] = cls
            by_name.setdefault(cls["short"], cls)
    log(f"Parsed {parsed} .gc files, {len(by_name)} class keys")

    def lookup(name: str | None) -> dict | None:
        if not name:
            return None
        if name in by_name:
            return by_name[name]
        short = name.split(".")[-1]
        return by_name.get(short)

    def resolve_icon(cls: dict) -> str | None:
        seen: set[str] = set()
        cur: dict | None = cls
        while cur and cur["name"] not in seen:
            seen.add(cur["name"])
            if cur.get("icon"):
                return cur["icon"]
            cur = lookup(cur.get("parent"))
        return None

    labels: dict[str, str] = {}
    label_src: dict[str, str] = {}
    rows = []
    seen_ids: set[int] = set()
    for cls in by_name.values():
        if id(cls) in seen_ids:
            continue
        seen_ids.add(id(cls))
        if not cls.get("label"):
            continue
        icon = resolve_icon(cls)
        if not icon:
            continue
        label = cls["label"]
        prev = label_src.get(label, "")
        mythic = "mythic" in cls["name"].lower()
        prev_mythic = "mythic" in prev.lower()
        if label not in labels or (mythic and not prev_mythic):
            labels[label] = icon
            label_src[label] = cls["name"]
        rows.append({"label": label, "icon": icon, "cls": cls["name"]})
    return labels, rows


def index_dds() -> dict[str, str]:
    out = {}
    for p in DDS_DIR.iterdir():
        if p.suffix.lower() == ".dds":
            out[p.name.lower()] = p.name
    return out


def find_dds(icon: str, dds: dict[str, str]) -> str | None:
    stem = Path(icon).stem
    for cand in (f"{icon}.dds", f"{stem}.dds", icon):
        hit = dds.get(cand.lower())
        if hit:
            return hit
    return None


def wiki_keys(title: str) -> set[str]:
    keys = {compact(title)}
    keys.add(compact(re.sub(r"\s*\(.*?\)\s*", "", title)))
    keys.discard("")
    return keys


def label_keys(label: str) -> set[str]:
    keys = {compact(label)}
    keys.add(compact(re.sub(r"\s*\(.*?\)\s*", "", label)))
    keys.discard("")
    return keys


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


def is_keep_local(src: str) -> bool:
    rel = unquote(src).lstrip("/").replace("\\", "/")
    if rel.startswith("images/recovered/"):
        return False
    if not rel.startswith("images/"):
        return False
    return (PUBLIC_IMAGES / rel[len("images/") :]).is_file()


def original_wiki_name(src: str, images: list[str]) -> str:
    name = unquote(src).replace("\\", "/").split("/")[-1]
    if name.startswith("recovered/"):
        name = name.split("/", 1)[1]
    for listed in images:
        listed_name = unquote(listed).replace("\\", "/").split("/")[-1]
        if compact(listed_name) == compact(name) or Path(listed_name).stem == Path(name).stem:
            return listed_name
    return name


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
    labels, rows = index_gc()
    LABELS.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    log(f"Resolved {len(labels)} labeled items")

    by_compact: dict[str, tuple[str, str]] = {}
    for label, icon in labels.items():
        for key in label_keys(label):
            by_compact.setdefault(key, (label, icon))

    dds = index_dds()
    log(f"{len(dds)} DDS files")

    report = []
    replacements: list[tuple[str, str]] = []
    recovered = 0
    for item in rainbow_pages():
        data = item["data"]
        title = data.get("title") or ""
        html = data.get("html") or ""
        listed = [unquote(s) for s in (data.get("images") or [])]
        srcs = re.findall(r'src="(/images/[^"]+)"', html)
        hit = None
        for key in wiki_keys(title):
            key = ALIASES.get(key, key)
            if key in by_compact:
                hit = by_compact[key]
                break
        if not hit:
            for key in wiki_keys(title):
                key = ALIASES.get(key, key)
                if len(key) < 10:
                    continue
                cands = [v for k, v in by_compact.items() if k.startswith(key)]
                if len(cands) == 1:
                    hit = cands[0]
                    break
        icon_name = None
        dds_name = None
        gc_label = None
        if hit:
            gc_label, icon_name = hit
            dds_name = find_dds(icon_name, dds)

        seen = set()
        for src in srcs:
            name = original_wiki_name(src, listed)
            if name.lower() in {"magnify-clip.png", "exclamation.png"} or name in seen:
                continue
            if "image_missing" in name.lower():
                continue
            seen.add(name)
            if is_keep_local(src):
                report.append({"page": title, "wiki": name, "kept": src})
                continue
            if not dds_name:
                original = f"/images/{name}"
                if src != original:
                    replacements.append((src, original))
                report.append({
                    "page": title,
                    "wiki": name,
                    "gc_label": gc_label,
                    "icon": icon_name,
                    "dds": None,
                })
                continue
            safe = re.sub(r'[<>:"/\\|?*\']', "", Path(name).stem).strip(" ._")
            dest = RECOVERED / (safe + ".png")
            ok = convert(DDS_DIR / dds_name, dest)
            report.append({
                "page": title,
                "wiki": name,
                "gc_label": gc_label,
                "icon": icon_name,
                "dds": dds_name,
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
    hits = sum(1 for r in report if r.get("dds"))
    log(f"Rainbow via .gc: {hits}/{len(report)} matches, wrote {recovered} icons")


if __name__ == "__main__":
    main()
