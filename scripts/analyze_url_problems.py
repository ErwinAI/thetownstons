"""Inventory wiki URL problems: special chars, link 404s, file/path mismatches."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "wiki"
# Apostrophes are legal in MediaWiki hrefs; don't stop the match at '.
HREF_RE = re.compile(r'''href=["'](/wiki/[^"#]+)''', re.I)
SPECIAL = re.compile(r"""[^\w/\-]""")
RESERVED = set(":/?#[]@!$&'()*+,;=%")


def fold(value: str) -> str:
    text = value.replace("/wiki/", "", 1) if value.startswith("/wiki/") else value
    try:
        text = unquote(text)
    except Exception:
        pass
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip().lower()
    if text.startswith("category/"):
        text = "category:" + text[len("category/") :]
    return text


def walk() -> list[dict]:
    pages = []
    for path in CONTENT.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data.get("path") or not data.get("title"):
            continue
        rel = path.relative_to(CONTENT).as_posix()
        data["_file"] = rel
        data["_file_slug"] = rel[: -len(".json")]
        pages.append(data)
    return pages


def char_class(slug: str) -> list[str]:
    labels = []
    if "," in slug:
        labels.append("comma")
    if "'" in slug or "%27" in slug:
        labels.append("apostrophe")
    if "(" in slug or ")" in slug or "%28" in slug or "%29" in slug:
        labels.append("paren")
    if "&" in slug or "%26" in slug:
        labels.append("ampersand")
    if "!" in slug:
        labels.append("bang")
    if "?" in slug or "%3F" in slug:
        labels.append("question")
    if ":" in slug and not slug.startswith("Category:"):
        labels.append("colon")
    if slug.startswith("Category:"):
        labels.append("category-colon")
    if slug.startswith("Category/"):
        labels.append("category-slash")
    if "/" in slug and not slug.startswith("Category/"):
        labels.append("nested-slash")
    if "..." in slug or slug.count(".") >= 2:
        labels.append("ellipsis")
    if '"' in slug or "%22" in slug:
        labels.append("quote")
    if any(ch in slug for ch in "*[]"):
        labels.append("glob-char")
    if not labels and SPECIAL.search(unquote(slug)):
        labels.append("other-special")
    if not labels:
        labels.append("plain")
    return labels


def classify_broken(href: str, folded: str, keys: set[str], cat_members: set[str]) -> str:
    slug = href.replace("/wiki/", "", 1)
    if re.match(r"^(Special|Talk|User|Category_talk|File|Image|MediaWiki|Help_talk|Template|Guild)/", slug, re.I):
        return "old-wiki-namespace"
    if slug.startswith("Category:") or slug.startswith("Category/"):
        name = re.sub(r"^Category[:/]", "", slug).replace("_", " ").lower()
        if name in cat_members:
            return "category-should-resolve"
        return "empty-or-missing-category"
    if folded in keys:
        return "exists-lookup-should-work"
    if "%" in slug:
        try:
            if fold(unquote(slug)) in keys:
                return "encoding-mismatch"
        except Exception:
            return "bad-encoding"
    return "genuinely-missing"


def main() -> None:
    pages = walk()
    keys: set[str] = set()
    for page in pages:
        for value in (page.get("path"), page.get("wikiTitle"), page.get("title")):
            keys.add(fold(str(value or "")))
            if fold(str(value or "")).startswith("category:"):
                keys.add(fold(str(value or ""))[len("category:") :].strip())

    cat_members: set[str] = set()
    for page in pages:
        for cat in page.get("categories") or []:
            cat_members.add(cat.replace("_", " ").lower())

    path_classes: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    encoded_in_path = 0
    file_mismatch = []
    for page in pages:
        slug = page["path"].replace("/wiki/", "", 1)
        decoded = unquote(slug)
        if slug != decoded:
            encoded_in_path += 1
        if page["_file_slug"] != slug and page["_file_slug"] != decoded:
            file_mismatch.append(
                {"file": page["_file"], "path": page["path"], "file_slug": page["_file_slug"]}
            )
        for label in char_class(slug):
            path_classes[label] += 1
            if len(examples[label]) < 8:
                examples[label].append(page["path"])

    links: dict[str, dict] = {}
    total_hrefs = 0
    for page in pages:
        for match in HREF_RE.finditer(page.get("html") or ""):
            href = match.group(1)
            total_hrefs += 1
            entry = links.setdefault(href, {"count": 0, "sources": []})
            entry["count"] += 1
            if len(entry["sources"]) < 3:
                entry["sources"].append(page["path"])

    broken_groups: dict[str, list] = defaultdict(list)
    for href, meta in links.items():
        folded = fold(href)
        if folded in keys or (
            href.replace("/wiki/", "", 1).startswith("Category/")
            and href.replace("/wiki/", "", 1)[len("Category/") :].replace("_", " ").lower() in cat_members
        ) or (
            href.replace("/wiki/", "", 1).startswith("Category:")
            and href.replace("/wiki/", "", 1)[len("Category:") :].replace("_", " ").lower() in cat_members
        ):
            continue
        kind = classify_broken(href, folded, keys, cat_members)
        if kind in {"exists-lookup-should-work", "category-should-resolve"}:
            continue
        broken_groups[kind].append({"href": href, "count": meta["count"], "sources": meta["sources"]})

    for items in broken_groups.values():
        items.sort(key=lambda x: -x["count"])

    prerender_encode = set("()[]?*")
    would_encode = []
    need_comma_encode = []
    for page in pages:
        slug = unquote(page["path"].replace("/wiki/", "", 1))
        chars = sorted({ch for ch in slug if ch in RESERVED and ch not in "/:"})
        extra = [ch for ch in chars if ch not in prerender_encode]
        if extra:
            would_encode.append({"path": page["path"], "chars": extra})
        if "," in slug:
            need_comma_encode.append(page["path"])

    report = {
        "pages": len(pages),
        "unique_hrefs": len(links),
        "total_hrefs": total_hrefs,
        "encoded_stored_paths": encoded_in_path,
        "file_vs_path_mismatches": len(file_mismatch),
        "file_mismatch_samples": file_mismatch[:25],
        "path_character_classes": dict(path_classes),
        "path_examples": {k: v for k, v in examples.items()},
        "broken": {k: {"unique": len(v), "refs": sum(x["count"] for x in v), "top": v[:15]} for k, v in broken_groups.items()},
        "prerender_encodes_only": "()[]?*",
        "pages_with_unencoded_reserved": len(would_encode),
        "unencoded_reserved_samples": would_encode[:40],
        "comma_pages": need_comma_encode,
        "comma_page_count": len(need_comma_encode),
    }
    out = ROOT / "archive" / "url-problems.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "pages", "unique_hrefs", "total_hrefs", "encoded_stored_paths",
        "file_vs_path_mismatches", "path_character_classes",
        "prerender_encodes_only", "pages_with_unencoded_reserved",
        "comma_page_count",
    )}, indent=2))
    print("\nBROKEN")
    for kind, info in sorted(report["broken"].items(), key=lambda kv: -kv[1]["refs"]):
        print(f"  {kind}: {info['unique']} unique / {info['refs']} refs")
        for item in info["top"][:5]:
            print(f"    {item['count']}x {item['href']}")


if __name__ == "__main__":
    main()
