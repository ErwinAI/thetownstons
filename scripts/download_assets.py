"""Download key branding images that the homepage needs immediately."""
from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "images"
UA = "thetownstons-restore/1.0 (personal Dungeon Runners wiki restore)"
BASE = "https://web.archive.org/web/2009id_/http://www.thetownstons.com"

ASSETS = [
    "/thetownstons/thetownstons.png",
    "/thetownstons/images/DRLogoLayeredScaled.gif",
    "/thetownstons/images/Maintitle.png",
    "/thetownstons/images/Maintopics.png",
    "/thetownstons/images/Contributor.png",
    "/thetownstons/images/Wikinews.png",
    "/thetownstons/images/Poll.png",
    "/favicon.ico",
]


def fetch(path: str) -> bytes | None:
    url = urljoin(BASE + "/", path.lstrip("/"))
    r = requests.get(url, headers={"User-Agent": UA}, timeout=45, allow_redirects=True)
    if r.status_code != 200:
        print(f"FAIL {r.status_code} {path}")
        return None
    ctype = r.headers.get("content-type", "")
    if "text/html" in ctype and len(r.content) < 8000:
        print(f"SKIP html interstitial {path}")
        return None
    return r.content


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (ROOT / "public").mkdir(parents=True, exist_ok=True)
    for path in ASSETS:
        name = Path(path).name
        dest = ROOT / "public" / name if name == "favicon.ico" else OUT / name
        if dest.exists() and dest.stat().st_size > 100:
            print(f"HAVE {dest.relative_to(ROOT)}")
            continue
        data = fetch(path)
        time.sleep(0.4)
        if not data:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        print(f"OK {dest.relative_to(ROOT)} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
