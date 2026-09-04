"""Enrich wiki quest pages with client .gc text, and create missing story-quest pages."""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_gc as gc

CLIENT_MARK = 'class="client-quest"'
FIELD = re.compile(
    r"(MinLevel|MaxLevel|Min_Level|Max_Level|UIZoneInfo|FollowupQuest|NPC|Label|"
    r"Summary|Description|RewardText|Repeatable|TokenReward|CashReward|ZoneName|"
    r"RequiredQuantity)\s*=\s*",
)
GIVER_COMMENT = re.compile(r"//\s*Quest [Gg]iver\s*=\s*(.+)")
OBSOLETE_COMMENT = re.compile(r"no longer in the game", re.I)
OBJ_HEAD = re.compile(r"\*\s*extends\s+([\w.]+)\s*\{")
CLASS_HEAD = re.compile(
    r"^([A-Za-z0-9_]+)\s+extends\s+([\w.]+)\s*\{",
    re.M,
)
TOKEN_SPLIT = gc.TOKEN_SPLIT
ZONE_CATEGORY = {
    "algernon": "Algernon Quests",
    "algorsterrordome": "Algor's Terror Dome Quests",
    "vergrimsvexation": "Vergrim's Quests",
    "thewidowersnest": "Widower's Nest Quests",
    "frumpsmisfortune": "Frump's Misfortune Quests",
    "dewvalleyforest": "Dew Valley Quests",
    "ratsputinsgulag": "Ratsputin's Gulag Quests",
    "themutanousmalaise": "Mutanous Malaise Quests",
    "mutantmania": "Mutant Mania Quests",
    "theembercorepath": "Embercore Path Quests",
    "theshadowsembrace": "Shadow's Embrace Quests",
    "balzacksburrow": "Balzack's Burrow Quests",
    "pwnston": "Pwnston Quests",
    "townston": "Townston Quests",
}
SKIP_PARTS = {"token", "uidesc", "debug"}


def compact(text: str) -> str:
    return TOKEN_SPLIT.sub("", (text or "").lower())


ZONE_CATEGORY[compact("Horrific Dungeon of Legend")] = "Horrific Dungeon of Legend Quests"


def dotted(path: Path) -> str:
    return ".".join(path.relative_to(gc.DDS_DIR).with_suffix("").parts)


def parse_quoted(text: str, start: int) -> tuple[str, int]:
    i = start
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    if i >= len(text) or text[i] != '"':
        end = text.find(";", i)
        if end < 0:
            return text[i:].strip(), len(text)
        return text[i:end].strip(), end + 1
    i += 1
    out: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            out.append(text[i + 1])
            i += 2
            continue
        if ch == '"':
            i += 1
            while i < len(text) and text[i] != ";":
                i += 1
            return "".join(out), min(i + 1, len(text))
        out.append(ch)
        i += 1
    return "".join(out), i


def parse_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in FIELD.finditer(block):
        value, _ = parse_quoted(block, match.end())
        fields[match.group(1)] = value
    return fields


def clean_text(value: str) -> str:
    value = (value or "").replace("\r\n", "\n")
    parts = re.split(r"(<br\s*/?>)", value, flags=re.I)
    out: list[str] = []
    for part in parts:
        if re.match(r"<br", part, re.I):
            out.append("<br/>")
        else:
            out.append(re.sub(r"\s+", " ", part).strip())
    text = "".join(out).strip()
    if text.upper() == "TEMP":
        return ""
    return re.sub(r"''(.+?)''", r"<i>\1</i>", text)


def boolish(value: str | None) -> bool | None:
    if value is None:
        return None
    low = value.strip().lower()
    if low == "true":
        return True
    if low == "false":
        return False
    return None


def numish(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_bases() -> dict[str, dict]:
    raw: dict[str, dict] = {}
    extends: dict[str, str] = {}
    root = gc.DDS_DIR / "quests" / "base"
    for path in root.glob("Quest*.gc"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        head = CLASS_HEAD.search(text)
        if not head:
            continue
        name = head.group(1)
        extends[name] = head.group(2).split(".")[-1]
        desc = gc.first_description(text[head.end() - 1 :])
        fields = parse_fields(gc.strip_comments(desc))
        raw[name] = {
            "token": numish(fields.get("TokenReward")),
            "cash": numish(fields.get("CashReward")),
            "repeatable": boolish(fields.get("Repeatable")),
        }
    resolved: dict[str, dict] = {}
    for name in raw:
        token = cash = None
        repeatable = None
        walk = name
        seen: set[str] = set()
        while walk and walk not in seen:
            seen.add(walk)
            row = raw.get(walk) or {}
            if token is None:
                token = row.get("token")
            if cash is None:
                cash = row.get("cash")
            if repeatable is None:
                repeatable = row.get("repeatable")
            walk = extends.get(walk, "")
        resolved[name] = {
            "token": token or 0,
            "cash": cash or 0,
            "repeatable": bool(repeatable),
        }
    return resolved


def load_zones() -> dict[str, dict]:
    zones: dict[str, dict] = {}
    for path in (gc.DDS_DIR / "quests" / "UIDesc").glob("*.gc"):
        text = gc.strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
        fields = parse_fields(text)
        name = fields.get("ZoneName") or path.stem.replace("_", " ")
        zones[path.stem.lower()] = {
            "name": name,
            "min": fields.get("Min_Level") or fields.get("MinLevel"),
            "max": fields.get("Max_Level") or fields.get("MaxLevel"),
        }
        zones[compact(path.stem)] = zones[path.stem.lower()]
    return zones


def load_npcs() -> dict[str, str]:
    labels: dict[str, str] = {}
    label_re = re.compile(r'Label\s*=\s*"((?:[^"\\]|\\.)*)"')
    for path in gc.DDS_DIR.rglob("*.gc"):
        parts = [p.lower() for p in path.parts]
        if "npc" not in parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        match = label_re.search(text)
        if not match:
            continue
        label = match.group(1)
        labels[dotted(path).lower()] = label
        labels[path.stem.lower()] = label
    return labels


def is_story_quest(path: Path) -> bool:
    parts = [p.lower() for p in path.parts]
    if "quest" not in parts:
        return False
    if any(part in SKIP_PARTS for part in parts):
        return False
    if "quests" in parts and "base" in parts:
        return False
    stem = path.stem.lower()
    if stem.startswith("debug") or "debug" in stem:
        return False
    return True


def parse_objectives(text: str, desc_end: int) -> list[dict]:
    out: list[dict] = []
    for match in OBJ_HEAD.finditer(text, desc_end):
        end = gc.matching_brace(text, match.end() - 1)
        inner = gc.strip_comments(text[match.end() : end])
        fields = parse_fields(inner)
        kind = match.group(1).split(".")[-1]
        if "Objective" not in kind:
            continue
        out.append({
            "kind": kind,
            "label": fields.get("Label") or "",
            "qty": fields.get("RequiredQuantity") or "",
        })
    return out


def quest_type(objectives: list[dict]) -> str:
    kinds = {obj["kind"] for obj in objectives}
    if kinds == {"GoToObjective"}:
        return "Discover"
    if kinds == {"KillObjective"}:
        return "Kill"
    if kinds == {"ItemObjective"}:
        return "Collect"
    if kinds == {"ActivateObjective"}:
        return "Activate"
    if "KillObjective" in kinds and "ItemObjective" in kinds:
        return "Hunt/Collect"
    if not kinds:
        return "Talk"
    return " / ".join(sorted(k.replace("Objective", "") for k in kinds))


def resolve_npc(raw: str | None, npcs: dict[str, str]) -> str:
    if not raw:
        return ""
    raw = raw.strip().strip('"').rstrip(";")
    if raw.lower().startswith("world.") or raw.lower().startswith("npc."):
        return npcs.get(raw.lower()) or npcs.get(raw.split(".")[-1].lower()) or ""
    return raw


def category_for(zone_name: str, path: Path) -> str:
    if "snowman" in [p.lower() for p in path.parts] or "holiday" in compact(zone_name):
        return "Holiday Quests"
    if "relic" in [p.lower() for p in path.parts]:
        return "Relic Quests"
    return ZONE_CATEGORY.get(compact(zone_name), f"{zone_name} Quests" if zone_name else "Quests")


def wiki_catalog() -> dict[str, tuple[Path, dict]]:
    out: dict[str, tuple[Path, dict]] = {}
    for path in gc.CONTENT.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title") or ""
        if title.startswith("Category:"):
            continue
        for key in match_keys(title) | match_keys(data.get("wikiTitle") or title):
            out.setdefault(key, (path, data))
    return out


def match_keys(name: str) -> set[str]:
    keys = {compact(name)}
    trimmed = re.sub(r"\((?:quest)\)", "", name, flags=re.I).strip()
    keys.add(compact(trimmed))
    c = compact(name)
    if c.endswith("quest"):
        keys.add(c[:-5])
    return {k for k in keys if k}


def is_quest_page(data: dict) -> bool:
    cats = [c.lower() for c in (data.get("categories") or [])]
    if "dungeons" in cats:
        return False
    body = data.get("html") or ""
    if "Quest Giver" in body:
        return True
    return "quests" in cats or any(c.endswith("quests") for c in cats)


def page_title(label: str) -> str:
    return (label or "").rstrip("!?").strip() or (label or "").strip()


def wiki_href(title: str) -> str:
    return "/wiki/" + title.replace(":", "/").replace(" ", "_")


def page_file(title: str) -> Path:
    rel = title.replace(":", "/").replace(" ", "_")
    rel = re.sub(r'[<>:"|?*]', "", rel)
    return gc.CONTENT / (rel + ".json")


def link_to(name: str, catalog: dict[str, tuple[Path, dict]]) -> str:
    if not name:
        return "—"
    hit = catalog.get(compact(name))
    if hit:
        title = hit[1].get("title") or name
        href = (hit[1].get("path") or wiki_href(title)).replace("'", "%27")
        return f'<a href="{html.escape(href, quote=True)}" title="{html.escape(title)}">{html.escape(title)}</a>'
    return html.escape(name)


def coin_link(n: int, catalog: dict) -> str:
    visible = "King's Coin" if n == 1 else "King's Coins"
    hit = (
        catalog.get(compact("King's Coins"))
        or catalog.get(compact("King's Coin"))
        or catalog.get(compact("Kings Coins"))
        or catalog.get(compact("Kings Coin"))
    )
    if not n:
        return ""
    if not hit:
        return f"{n} {html.escape(visible)}"
    href = (hit[1].get("path") or wiki_href(visible)).replace("'", "%27")
    title = hit[1].get("title") or visible
    return (
        f'{n} <a href="{html.escape(href, quote=True)}" '
        f'title="{html.escape(title)}">{html.escape(visible)}</a>'
    )


def reward_text(quest: dict, catalog: dict) -> str:
    parts: list[str] = []
    if (quest.get("cash") or 0) > 0:
        parts.append("Gold")
    tokens = int(quest.get("token") or 0)
    if tokens:
        parts.append(coin_link(tokens, catalog))
    return " and ".join(parts) if parts else "None listed"


def client_section(quest: dict) -> str:
    chunks = ['<div class="client-quest">']
    chunks.append("<h2>In-game text</h2>")
    chunks.append(
        "<p>Journal text, offer, and turn-in as they appeared in game.</p>"
    )
    if quest.get("obsolete"):
        chunks.append("<p><i>This quest was removed from the game.</i></p>")
    if quest.get("summary"):
        chunks.append(f"<p><b>Journal:</b> {quest['summary']}</p>")
    if quest.get("description"):
        chunks.append(f"<p><b>Offer:</b></p>\n<blockquote>{quest['description']}</blockquote>")
    if quest.get("reward_text"):
        chunks.append(f"<p><b>Turn-in:</b></p>\n<blockquote>{quest['reward_text']}</blockquote>")
    if quest.get("objectives"):
        items = "".join(
            "<li>"
            + html.escape(obj["label"] or obj["kind"])
            + (f" ×{html.escape(obj['qty'])}" if obj.get("qty") else "")
            + "</li>"
            for obj in quest["objectives"]
        )
        chunks.append(f"<p><b>Objectives:</b></p>\n<ul>{items}</ul>")
    if quest.get("min") or quest.get("max"):
        lo = quest.get("min") or "?"
        hi = quest.get("max") or "?"
        chunks.append(f"<p><b>Level range:</b> {html.escape(str(lo))}–{html.escape(str(hi))}</p>")
    chunks.append("</div>")
    return "\n".join(chunks)


def insert_client(body: str, section: str) -> str:
    if CLIENT_MARK in body:
        return re.sub(
            r'<div class="client-quest">.*?</div>',
            section,
            body,
            count=1,
            flags=re.S,
        )
    marker = '<div class="visualClear">'
    if marker in body:
        return body.replace(marker, section + "\n\n" + marker, 1)
    return body.rstrip() + "\n" + section + '\n<div class="visualClear"></div>'


def fill_unknowns(body: str, quest: dict) -> str:
    if quest.get("repeatable") is None:
        return body
    yes = "Yes" if quest["repeatable"] else "No"
    return re.sub(
        r"(<b>Repeatable:</b>\s*)Unknown",
        rf"\1{yes}",
        body,
        count=1,
        flags=re.I,
    )


def is_generated(data: dict) -> bool:
    if data.get("source") == "dungeon-runners-client":
        return True
    body = data.get("html") or ""
    if "<p><b>Zone:</b>" in body:
        return True
    if "Last Build Updated" in body or "\n</p><p>" in body:
        return False
    return body.startswith("<p><b>Quest Giver:</b>")


def render_new(quest: dict, catalog: dict) -> dict:
    title = quest.get("page_title") or page_title(quest["label"])
    giver = link_to(quest.get("giver") or "", catalog)
    if giver == "—":
        giver = "Unknown"
    zone = quest.get("zone") or ""
    follow = quest.get("follow_label") or ""
    rows = [
        f"<p><b>Quest Giver:</b> {giver}</p>",
        f"<p><b>Quest Type:</b> {html.escape(quest.get('qtype') or 'Unknown')}</p>",
        f"<p><b>Quest Description:</b> {quest.get('summary') or 'See in-game text below.'}</p>",
        f"<p><b>Quest Reward:</b> {reward_text(quest, catalog)}</p>",
        f"<p><b>Return to:</b> {giver}</p>",
        f"<p><b>Repeatable:</b> {'Yes' if quest.get('repeatable') else 'No'}</p>",
    ]
    if follow:
        rows.append(f"<p><b>Following Quest:</b> {link_to(page_title(follow), catalog)}</p>")
    if zone:
        rows.append(f"<p><b>Zone:</b> {link_to(zone, catalog)}</p>")
    cats = ["Quests"]
    zone_cat = quest.get("category")
    if zone_cat and zone_cat not in cats:
        cats.append(zone_cat)
    if quest.get("repeatable") and "Repeatable Quests" not in cats:
        cats.append("Repeatable Quests")
    body = "\n".join(rows) + "\n" + client_section(quest) + '\n<div class="visualClear"></div>'
    return {
        "title": title,
        "wikiTitle": title.replace(" ", "_"),
        "path": wiki_href(title),
        "description": f"{title} — The Townstons wiki",
        "categories": cats,
        "images": [],
        "html": body,
        "source": "dungeon-runners-client",
    }


def parse_quest(path: Path, bases: dict, zones: dict, npcs: dict) -> dict | None:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    desc_m = re.search(r"\bDescription\s*\{", raw)
    if not desc_m:
        return None
    desc_end = gc.matching_brace(raw, desc_m.end() - 1)
    desc_raw = raw[desc_m.end() : desc_end]
    giver_hits = GIVER_COMMENT.findall(desc_raw) or GIVER_COMMENT.findall(raw)
    giver_comment = giver_hits[-1].strip() if giver_hits else ""
    obsolete = bool(OBSOLETE_COMMENT.search(raw))
    fields = parse_fields(gc.strip_comments(desc_raw))
    label = fields.get("Label")
    if not label or label in {"NONE", "PREFIX", "SUFFIX"}:
        return None
    low = label.lower()
    if low.startswith("test ") or "test quest" in low or "activate objective test" in low:
        return None
    head = CLASS_HEAD.search(raw)
    base_name = head.group(2).split(".")[-1] if head else ""
    inherited = bases.get(base_name, {})
    zone_ref = (fields.get("UIZoneInfo") or "").split(".")[-1]
    zone = zones.get(zone_ref.lower()) or zones.get(compact(zone_ref)) or {}
    giver = resolve_npc(giver_comment, npcs) or resolve_npc(fields.get("NPC"), npcs)
    token = numish(fields.get("TokenReward"))
    cash = numish(fields.get("CashReward"))
    repeatable = boolish(fields.get("Repeatable"))
    if token is None:
        token = inherited.get("token") or 0
    if cash is None:
        cash = inherited.get("cash") or 0
    if repeatable is None:
        repeatable = inherited.get("repeatable") or False
    if "repeat" in base_name.lower() or "relic" in base_name.lower():
        repeatable = True
    summary = clean_text(fields.get("Summary") or "")
    description = clean_text(fields.get("Description") or "")
    category = category_for(zone.get("name") or "", path)
    blob = compact(summary + description + label + "/".join(path.parts))
    if "snowman" in blob or "shivery" in blob:
        category = "Holiday Quests"
        giver = giver or "Shivery the Incorrigible Snowman"
    return {
        "path": path,
        "dotted": dotted(path),
        "label": label,
        "summary": summary,
        "description": description,
        "reward_text": clean_text(fields.get("RewardText") or ""),
        "giver": giver,
        "follow": fields.get("FollowupQuest") or "",
        "follow_label": "",
        "zone": zone.get("name") or "",
        "category": category,
        "min": fields.get("MinLevel") or zone.get("min") or "",
        "max": fields.get("MaxLevel") or zone.get("max") or "",
        "token": token,
        "cash": cash,
        "repeatable": repeatable,
        "obsolete": obsolete,
        "objectives": parse_objectives(raw, desc_end),
        "qtype": "",
    }


def pick_wiki(quest: dict, catalog: dict) -> tuple[Path, dict] | None:
    keys = list(match_keys(quest["label"]) | match_keys(page_title(quest["label"])))
    c = compact(page_title(quest["label"]))
    keys.append(c + "quest")
    seen: list[tuple[Path, dict]] = []
    for key in keys:
        hit = catalog.get(key)
        if hit and hit not in seen:
            seen.append(hit)
    quest_hits = [h for h in seen if is_quest_page(h[1])]
    pool = quest_hits or []
    if not pool:
        return None
    exact = [h for h in pool if compact(h[1].get("title") or "") == c]
    if exact:
        return exact[0]
    return pool[0]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def ensure_townston_category() -> None:
    dest = gc.CONTENT / "Category" / "Townston_Quests.json"
    if dest.exists():
        return
    write_json(dest, {
        "title": "Category:Townston Quests",
        "wikiTitle": "Category:Townston_Quests",
        "path": "/wiki/Category/Townston_Quests",
        "description": "Category:Townston Quests — The Townstons wiki",
        "categories": ["Quests"],
        "images": [],
        "html": (
            "<p>Quests given in Townston, including commander/lieutenant turn-ins "
            "and town-only tasks such as the Wishing Well.</p>\n"
            '<div class="visualClear"></div>'
        ),
    })


def main() -> None:
    gc.log("Loading quest bases, zones, and NPC labels…")
    bases = load_bases()
    zones = load_zones()
    npcs = load_npcs()
    catalog = wiki_catalog()
    quests: list[dict] = []
    by_dot: dict[str, dict] = {}
    for path in gc.DDS_DIR.rglob("*.gc"):
        if not is_story_quest(path):
            continue
        try:
            quest = parse_quest(path, bases, zones, npcs)
        except OSError:
            continue
        if not quest:
            continue
        quest["qtype"] = quest_type(quest["objectives"])
        quests.append(quest)
        by_dot[quest["dotted"].lower()] = quest
    for quest in quests:
        follow = (quest.get("follow") or "").lower()
        if follow in by_dot:
            quest["follow_label"] = page_title(by_dot[follow]["label"])
    uniq: dict[str, dict] = {}
    for quest in quests:
        key = compact(page_title(quest["label"]))
        prev = uniq.get(key)
        if not prev:
            uniq[key] = quest
            continue
        winner = quest if len(quest.get("description") or "") > len(prev.get("description") or "") else prev
        other = prev if winner is quest else quest
        if other.get("category") == "Holiday Quests" or "snowman" in [p.lower() for p in other["path"].parts]:
            winner["category"] = "Holiday Quests"
        if not winner.get("giver"):
            winner["giver"] = other.get("giver") or ""
        if not winner.get("zone"):
            winner["zone"] = other.get("zone") or ""
        uniq[key] = winner
    quests = list(uniq.values())
    gc.log(f"{len(quests)} unique story/relic quest labels")

    jobs: list[tuple[str, dict, tuple[Path, dict]]] = []
    for quest in quests:
        existing = pick_wiki(quest, catalog)
        if existing and is_quest_page(existing[1]):
            jobs.append(("update", quest, existing))
            continue
        title = page_title(quest["label"])
        collision = catalog.get(compact(title))
        if collision and not is_quest_page(collision[1]) and not is_generated(collision[1]):
            title = f"{title} (Quest)"
            if catalog.get(compact(title)) and is_quest_page(catalog[compact(title)][1]):
                jobs.append(("update", quest, catalog[compact(title)]))
                continue
        dest = page_file(title)
        if dest.exists():
            on_disk = json.loads(dest.read_text(encoding="utf-8"))
            same = compact(on_disk.get("title") or "") == compact(title)
            if not same or not is_quest_page(on_disk):
                title = f"{page_title(quest['label'])} (Quest)"
                dest = page_file(title)
        stub = {
            "title": title,
            "path": wiki_href(title),
            "html": "<p><b>Zone:</b>",
            "categories": ["Quests"],
            "source": "dungeon-runners-client",
        }
        for key in match_keys(title) | match_keys(quest["label"]):
            catalog[key] = (dest, stub)
        jobs.append(("create", {**quest, "page_title": title}, (dest, stub)))

    created = enriched = rewritten = skipped = 0
    for action, quest, existing in jobs:
        dest, data = existing
        if action == "update" and is_generated(data):
            action = "create"
            quest = {**quest, "page_title": data.get("title") or page_title(quest["label"])}
        if action == "create":
            page = render_new(quest, catalog)
            dest = existing[0]
            old_bang = page_file(quest["label"])
            write_json(dest, page)
            if old_bang != dest and old_bang.exists() and is_generated(json.loads(old_bang.read_text(encoding="utf-8"))):
                old_bang.unlink()
            for key in match_keys(page["title"]) | match_keys(quest["label"]):
                catalog[key] = (dest, page)
            if data.get("source") == "dungeon-runners-client" or "<p><b>Zone:</b>" in (data.get("html") or ""):
                rewritten += 1
            else:
                created += 1
            continue
        if not is_quest_page(data):
            skipped += 1
            continue
        data["html"] = fill_unknowns(insert_client(data.get("html") or "", client_section(quest)), quest)
        cats = list(data.get("categories") or [])
        for extra in ("Quests", quest.get("category")):
            if extra and extra not in cats:
                cats.append(extra)
        data["categories"] = cats
        write_json(dest, data)
        for key in match_keys(data.get("title") or quest["label"]):
            catalog[key] = (dest, data)
        enriched += 1

    ensure_townston_category()
    gc.log(f"Quest pages: created {created}, rewritten {rewritten}, enriched {enriched}, skipped {skipped}")


if __name__ == "__main__":
    main()
