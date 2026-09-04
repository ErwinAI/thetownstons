"""Rewrite quest field markup to the clean one-field-per-line layout."""
from __future__ import annotations

import json
import re
from pathlib import Path

import match_gc as gc

CONTENT = gc.CONTENT
FIELD_ORDER = {
    "quest giver": "Quest Giver",
    "quest type": "Quest Type",
    "quest description": "Quest Description",
    "quest reward": "Quest Reward",
    "return to": "Return to",
    "repeatable": "Repeatable",
    "following quest": "Following Quest",
    "followed by": "Following Quest",
    "zone": "Zone",
}
SKIP_LABELS = {
    "last build updated",
    "contents",
}
LEAVE_LABELS = {
    "journal",
    "offer",
    "turn-in",
    "objectives",
    "level range",
}
P_TAG_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.I | re.S)
FIELD_INNER_RE = re.compile(
    r"^\s*<(?:b|strong|i)>\s*([^<:]+?)\s*:?\s*</(?:b|strong|i)>\s*:?\s*(.*)\s*$",
    re.I | re.S,
)
CLIENT_RE = re.compile(r'<div class="client-quest">.*?</div>', re.I | re.S)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def is_quest(data: dict) -> bool:
    if str(data.get("title") or "").startswith("Category:"):
        return False
    html = data.get("html") or ""
    if "Quest Giver" not in html:
        return False
    cats = [c.lower() for c in (data.get("categories") or [])]
    if "dungeons" in cats:
        return False
    if any("quest" in c for c in cats):
        return True
    return "Quest Type:" in html or "Quest Type:" in html.replace(" ", "")


def tidy_inner(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"\s*\n\s*", " ", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    value = value.replace("&nbsp;", " ").strip()
    value = re.sub(r"\s+</", "</", value)
    return value


def normalize_repeatable(value: str) -> str:
    text = tidy_inner(re.sub(r"<[^>]+>", "", value)).rstrip(".")
    if text in {"?", "??", ""}:
        return "Unknown"
    return tidy_inner(value).rstrip(".")


def rewrite_paragraph(inner: str) -> str | None:
    match = FIELD_INNER_RE.match(inner.strip())
    if not match:
        return None
    label = re.sub(r"<[^>]+>", "", match.group(1)).strip().rstrip(":")
    lowered = label.lower()
    if lowered in SKIP_LABELS:
        return ""
    if lowered in LEAVE_LABELS:
        return None
    value = tidy_inner(match.group(2))
    key = FIELD_ORDER.get(lowered, label)
    if key == "Repeatable":
        value = normalize_repeatable(value)
    if key == "Following Quest" and (not value or re.fullmatch(r"(none|—|-|\?)", value, re.I)):
        return ""
    if key in FIELD_ORDER.values() and not value:
        return ""
    if not value:
        return None
    return f"<p><b>{key}:</b> {value}</p>"


def rewrite_html(html: str) -> str:
    client = CLIENT_RE.search(html)
    head = html[: client.start()] if client else html
    tail = html[client.start() :] if client else ""

    def repl(match: re.Match[str]) -> str:
        new = rewrite_paragraph(match.group(1))
        return match.group(0) if new is None else new

    new_head = P_TAG_RE.sub(repl, head)
    new_head = re.sub(r"</p>\s*<p>", "</p>\n<p>", new_head)
    new_head = re.sub(r"[ \t]+\n", "\n", new_head)
    new_head = re.sub(r"\n{3,}", "\n\n", new_head)
    new_head = new_head.strip()
    if tail:
        return f"{new_head}\n{tail.strip()}"
    if '<div class="visualClear">' not in new_head:
        new_head += '\n<div class="visualClear"></div>'
    return new_head


def main() -> None:
    changed = skipped = already = 0
    for path in sorted(CONTENT.rglob("*.json")):
        data = load(path)
        if not is_quest(data):
            continue
        html = data.get("html") or ""
        new_html = rewrite_html(html)
        if "Quest Giver" not in new_html:
            skipped += 1
            continue
        if new_html == html:
            already += 1
            continue
        data["html"] = new_html
        save(path, data)
        changed += 1
    print(f"rewrote {changed}, already clean {already}, skipped {skipped}")


if __name__ == "__main__":
    main()
