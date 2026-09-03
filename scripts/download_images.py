"""Pull wiki images referenced in the raw archive from Wayback."""
from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "archive" / "raw"
OUT = ROOT / "public" / "images"
UA = "thetownstons-restore/1.0 (personal Dungeon Runners wiki restore)"
WAYBACK = "https://web.archive.org/web/2009id_/http://www.thetownstons.com"
IMG_RE = re.compile(r"/thetownstons/images/([^\"')\s]+)")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    names: set[str] = set()
    for html in RAW.rglob("*.html"):
        text = html.read_text(encoding="utf-8", errors="replace")
        for match in IMG_RE.findall(text):
            if "thumb/" in match:
                continue
            names.add(unquote(match).split("?")[0])
    print(f"Found {len(names)} image paths")
    ok = 0
    for rel in sorted(names):
        dest = OUT / Path(rel).name
        if dest.exists() and dest.stat().st_size > 80:
            continue
        url = urljoin(WAYBACK + "/", "thetownstons/images/" + rel)
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=40, allow_redirects=True)
        except requests.RequestException as exc:
            print(f"ERR {rel}: {exc}")
            time.sleep(0.5)
            continue
        time.sleep(0.35)
        if r.status_code != 200 or "text/html" in r.headers.get("content-type", ""):
            print(f"MISS {rel} ({r.status_code})")
            continue
        dest.write_bytes(r.content)
        ok += 1
        print(f"OK {dest.name} ({len(r.content)})")
    print(f"Downloaded {ok} images")


if __name__ == "__main__":
    main()
