"""Turn downloaded Wayback MediaWiki HTML into Nuxt Content markdown."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "archive" / "raw"
CONTENT = ROOT / "content" / "wiki"
MANIFEST = ROOT / "archive" / "parse-manifest.json"
SKIP_PREFIXES = (
    "special:",
    "special%3a",
    "image:",
    "image%3a",
    "mediawiki:",
    "template:",
    "user:",
    "user_talk:",
)
SKIP_QUERY_BITS = (
    "action=edit",
    "action=history",
    "action=submit",
    "action=raw",
    "action=info",
    "printable=yes",
    "oldid=",
    "diff=",
    "redlink=1",
)


def slug_from_path(path: Path) -> str | None:
    text = path.as_posix()
    marker = "/index.php/"
    if marker not in text:
        return None
    raw = text.split(marker, 1)[1]
    if raw.endswith("/index.html"):
        raw = raw[: -len("/index.html")]
    raw = unquote(raw)
    if any(bit in raw.lower() for bit in SKIP_QUERY_BITS):
        return None
    if "?" in raw:
        return None
    title = raw.replace("%3A", ":").replace("%3a", ":")
    lower = title.lower()
    if any(lower.startswith(p) for p in SKIP_PREFIXES):
        return None
    return title


def route_path(slug: str) -> str:
    """Parentheses are regex groups to Nitro/rou3. Encode those titles."""
    if re.search(r"[()[\]?*]", slug):
        return "/wiki/" + quote(slug, safe="_-,'!:")
    return "/wiki/" + slug


def file_slug(slug: str) -> str:
    if slug.startswith("Category:"):
        return "Category/" + slug[len("Category:") :].replace("/", "-")
    return slug.replace("/", "-").replace("(", "").replace(")", "")


def wiki_href(href: str) -> str:
    if not href:
        return href
    href = href.strip()
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    path = unquote(parsed.path or "")
    if "web.archive.org" in (parsed.netloc or "") and "/http" in path:
        path = path.split("/http", 1)[-1]
        if "://" in path:
            path = "/" + path.split("://", 1)[-1].split("/", 1)[-1]
    if path.startswith("/thetownstons/images/"):
        return "/images/" + path.split("/thetownstons/images/", 1)[1]
    if path.startswith("/thetownstons/index.php/"):
        page = path.split("/thetownstons/index.php/", 1)[1]
        if page.startswith("Image:") or page.startswith("File:"):
            filename = page.split(":", 1)[1]
            return "/images/" + filename
        return route_path(page)
    if path.endswith("/index.php") and parsed.query:
        m = re.search(r"(?:^|&)title=([^&]+)", parsed.query)
        if m:
            return route_path(unquote(m.group(1)).replace(" ", "_"))
    if href.startswith("/thetownstons/images/"):
        return "/images/" + href.split("/thetownstons/images/", 1)[1]
    if href.startswith("/thetownstons/index.php/"):
        page = href.split("/thetownstons/index.php/", 1)[1]
        if page.startswith("Image:") or page.startswith("File:"):
            return "/images/" + page.split(":", 1)[1]
        return route_path(page)
    return href


def clean_body(soup: BeautifulSoup) -> tuple[str, list[str], list[str]]:
    body = soup.find(id="bodyContent") or soup.find(id="mw-content-text")
    if not body:
        return "", [], []
    for sel in (
        "#siteSub",
        "#contentSub",
        "#jump-to-nav",
        ".printfooter",
        "#catlinks",
        "script",
        "style",
        "noscript",
    ):
        for el in body.select(sel):
            el.decompose()
    for comment in body.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    categories: list[str] = []
    catlinks = soup.find(id="catlinks")
    if catlinks:
        for a in catlinks.select("a"):
            title = a.get("title") or a.get_text(strip=True)
            if title and not title.startswith("Special:"):
                categories.append(title.replace("Category:", ""))

    images: list[str] = []
    for img in body.find_all("img"):
        src = img.get("src") or ""
        rewritten = wiki_href(src)
        img["src"] = rewritten
        if rewritten.startswith("/images/"):
            images.append(rewritten)
        img.attrs.pop("srcset", None)

    for a in body.find_all("a"):
        href = a.get("href")
        if href:
            a["href"] = wiki_href(href)
        if a.get("class") and "new" in a.get("class", []):
            a["class"] = [c for c in a["class"] if c != "new"] + ["missing"]

    html = body.decode_contents().strip()
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html, categories, images


def write_page(slug: str, title: str, html: str, categories: list[str], images: list[str]) -> Path:
    dest = CONTENT / f"{file_slug(slug)}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "title": title,
                "wikiTitle": slug,
                "path": route_path(slug),
                "description": title + " — The Townstons wiki",
                "categories": categories,
                "images": images,
                "html": html,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def main() -> None:
    CONTENT.mkdir(parents=True, exist_ok=True)
    written: list[dict] = []
    skipped = 0
    for html_path in RAW.rglob("index.html"):
        slug = slug_from_path(html_path)
        if not slug:
            skipped += 1
            continue
        raw = html_path.read_text(encoding="utf-8", errors="replace")
        if "<html" not in raw.lower():
            skipped += 1
            continue
        soup = BeautifulSoup(raw, "html.parser")
        heading = soup.select_one("h1.firstHeading")
        title = heading.get_text(" ", strip=True) if heading else slug.replace("_", " ")
        html, categories, images = clean_body(soup)
        if not html or len(html) < 40:
            skipped += 1
            continue
        dest = write_page(slug, title, html, categories, images)
        written.append({"slug": slug, "title": title, "file": str(dest.relative_to(ROOT))})
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({"pages": written, "skipped": skipped}, indent=2), encoding="utf-8")
    print(f"Wrote {len(written)} wiki pages, skipped {skipped}")


if __name__ == "__main__":
    main()
