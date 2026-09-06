from pathlib import Path
import json

WIKI = Path(r"C:\Users\me\Projects\thetownstons\content\wiki")

NOTE = (
    '<p>This rainbow is specific to {who} lair chest. '
    "It is not in the shared mythic pool every boss rolls. The "
    '<a href="/wiki/Wishing_Well" title="Wishing Well">Wishing Well</a> can also spit it out '
    "once you are high enough for that dungeon. The full list is on "
    '<a href="/wiki/Boss_Lair_Rainbows" title="Boss Lair Rainbows">Boss Lair Rainbows</a>.</p>\n'
)

NACHO = (
    "<p>Manglefeet&#x27;s lair chest is also wired to roll this helm. It is better known as a "
    '<a href="/wiki/Wishing_Well" title="Wishing Well">Wishing Well</a> piece, and it always felt half-finished. '
    'See <a href="/wiki/Boss_Lair_Rainbows" title="Boss Lair Rainbows">Boss Lair Rainbows</a>.</p>\n'
)

def who(href: str, title: str, poss: str) -> str:
    return f'<a href="{href}" title="{title}">{title}</a>{poss}'


ITEMS = {
    "Sissirat's_Super_Sissy_Stick_of_Stench.json": who("/wiki/Sissirat", "Sissirat", "&#x27;s"),
    "Sissirat's_Super_Sissy_Smasher_of_Stench.json": who("/wiki/Sissirat", "Sissirat", "&#x27;s"),
    "Sissirat's_Sissy_Spitter.json": who("/wiki/Sissirat", "Sissirat", "&#x27;s"),
    "Algor's_Axe_of_Global_Warming_Protection.json": who("/wiki/Algor_the_Cold", "Algor the Cold", "&#x27;s"),
    "Icicle_Pop_Ring.json": who("/wiki/Algor_the_Cold", "Algor the Cold", "&#x27;s"),
    "Algor's_Freeze_Popper.json": who("/wiki/Algor_the_Cold", "Algor the Cold", "&#x27;s"),
    "Vergrim's_Protective_Headgear_of_the_Goshly_Wisker.json": who("/wiki/Vergrim", "Vergrim", "&#x27;s"),
    "Vergrim's_Fancy_Gloves.json": who("/wiki/Vergrim", "Vergrim", "&#x27;s"),
    "I_Got_Next_Game.json": who("/wiki/Widow_Maker", "Widow Maker", "&#x27;s"),
    "I_Won_the_Game_and_All_I_Got_Was_This_Stupid_Ring.json": who("/wiki/Widow_Maker", "Widow Maker", "&#x27;s"),
    "Doesn't_Suck_Charm.json": who("/wiki/Frump", "Frump", "&#x27;s"),
    "Rotgut's_Drool_Covered_Microphone.json": who("/wiki/Rotgut_the_Bloated", "Rotgut the Bloated", "&#x27;s"),
    "Sound_Blaster.json": who("/wiki/Rotgut_the_Bloated", "Rotgut the Bloated", "&#x27;s"),
    "Abaddon's_Handy_Candy_Cane.json": who("/wiki/Abaddon", "Abaddon", "&#x27;s"),
    "Abaddon's_Handy_Candy_Broomstick.json": who("/wiki/Abaddon", "Abaddon", "&#x27;s"),
    "Abaddon's_Hardened_Candy_Corn_Cowl.json": who("/wiki/Abaddon", "Abaddon", "&#x27;s"),
    "Shadow_Queen's_Ring_of_Brilliant_Light!.json": who("/wiki/Queen_of_Shadows", "Queen of Shadows", "'"),
    "Dance_Shoes_of_the_Burrow.json": who("/wiki/Balzack", "Balzack", "&#x27;s"),
    "Balzack's_Dance_Decoder_Ring_of_The_Mutant_Samba.json": who("/wiki/Balzack", "Balzack", "&#x27;s"),
    "Long_Stem_Rose_of_Balzack's_Everlasting_Tango.json": who("/wiki/Balzack", "Balzack", "&#x27;s"),
    "Ratsputin's_Icy_Sword_of_Whisker_Power.json": who("/wiki/Ratsputin", "Ratsputin", "&#x27;s"),
    "Ratsputin's_Frosted_Forest_Snow_Globe_Ring.json": who("/wiki/Ratsputin", "Ratsputin", "&#x27;s"),
    "Folding_Chair_of_the_Mangled_Foot.json": who("/wiki/Manglefeet", "Manglefeet", "&#x27;s"),
    "Manglefeet's_Championship_Ring.json": who("/wiki/Manglefeet", "Manglefeet", "&#x27;s"),
}

BOSS_BLURB = (
    '<p>The chest in this lair can roll a short list of named rainbows. Those pieces are on '
    '<a href="/wiki/Boss_Lair_Rainbows" title="Boss Lair Rainbows">Boss Lair Rainbows</a>.</p>\n'
)

BOSSES = [
    "Sissirat.json",
    "Algor_the_Cold.json",
    "Vergrim.json",
    "Widow_Maker.json",
    "Frump.json",
    "Rotgut_the_Bloated.json",
    "Abaddon.json",
    "Queen_of_Shadows.json",
    "Balzack.json",
    "Ratsputin.json",
    "Manglefeet.json",
]


def insert_before_attributes(html: str, note: str) -> str:
    if "Boss_Lair_Rainbows" in html:
        return html
    marker = '<a name="Attributes:"'
    idx = html.find(marker)
    if idx == -1:
        marker = "<a name=\"Attributes:\""
        idx = html.find(marker)
    if idx == -1:
        marker = '<div class="visualClear">'
        idx = html.find(marker)
    if idx == -1:
        raise SystemExit("no insert point")
    return html[:idx] + note + html[idx:]


def patch_item(name: str, note: str) -> None:
    path = WIKI / name
    data = json.loads(path.read_text(encoding="utf-8"))
    data["html"] = insert_before_attributes(data["html"], note)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("item", name)


for fname, who_html in ITEMS.items():
    patch_item(fname, NOTE.format(who=who_html))

patch_item("Nacho_Supreme.json", NACHO)

for fname in BOSSES:
    path = WIKI / fname
    data = json.loads(path.read_text(encoding="utf-8"))
    html = data["html"]
    if "Boss_Lair_Rainbows" in html:
        print("skip boss", fname)
        continue
    marker = '<div class="visualClear">'
    idx = html.rfind(marker)
    if idx == -1:
        raise SystemExit(f"no clear {fname}")
    data["html"] = html[:idx] + BOSS_BLURB + html[idx:]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("boss", fname)
