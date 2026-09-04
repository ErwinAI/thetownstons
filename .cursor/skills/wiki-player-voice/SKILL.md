---
name: wiki-player-voice
description: >-
  Writes Townstons wiki copy from a player perspective. Use when creating or
  editing wiki pages, rainbow stubs, quest pages, modifiers, Name Descriptors,
  Mythic Suffixes, prefixes, postfixes, category lists, or any article HTML in
  content/wiki. Also use when generating pages from the Dungeon Runners client
  dump.
---

# Wiki player voice

IT HAS TO ALWAYS BE WRITTEN FROM A PLAYER PERSPECTIVE.

analyse existing pages. Write like that. Always.

## Before writing

Read recovered pages that already sound like the old wiki. Match them.

- Items: `content/wiki/Brilliance.json`, `content/wiki/The_Horror.json`, `content/wiki/Threadz_Wrap.json`
- Mechanics: `content/wiki/Items.json` (loot colors, soulbound, name descriptions)
- Quests: recovered pages with Quest Giver / Quest Type / Last Build Updated

Do not invent observed roll tables. If the old page listed varieties, keep them. If you only know the base item, say so the way Brilliance does: unknown how many varieties exist, then list only what is known.

## Never put this in article HTML

- `.gc` filenames, ModPAL, templates, `LabelType`, `SoulBound = true`
- “client file”, “client dump”, “scraped”, “parsed”, “NEEDS ENTRY”
- Internal IDs (`2HAxeMythic7`, `QuestGiver_A`, `PreBuiltWishingWell001`)
- “this page does not invent extra roll combinations”
- “Checked against the client”

Facts can come from the dump. The page must read like a player wrote it.

## Item pages

Infobox like Brilliance / The Horror:

- Piece, Class, Movement Speed or Defense Rating / Damage
- Weapons: Piece or Type players used (Two-Handed Axe), not “Client type”
- Quality stays “Mythic (rainbow)” only if the old pages said it; prefer the infobox fields above

Body:

- “X is a two-handed fighter rainbow axe.”
- Soulbound as a player fact: “This item is soulbound.”
- Flavor text the player saw on the item is fine
- Attributes as `+ Strength`, `+ Endurance`, `+ % Movement Speed`, `+ Fire Damage Resistance`
- Not `STR`, `END`, `+Shadow`, `Melee AR`

Rainbow extras: link [Mythic Suffixes](/wiki/Mythic_Suffixes). Do not dump every possible ending onto the item page.

## Mechanic pages

Write like `Items.json`. Colors, levels, and “of the Beetle” are how players read gear.

- Last word on green+ = Superior postfix (not “animals” as a system name; many are not animals)
- Blue = Magic prefix in front
- Yellow keeps the last word and adds a Rare postfix
- Purple uses a Unique prefix instead of the Magic one
- Grey cosmetic words are level prefixes (Opaque Ghost, Acid-Wash Cloth)
- Rainbows keep a fixed base name and can roll a joke ending

List every real prefix/postfix when the user wants the full category list. Do not hide pools behind “about 240 prefixes.”

## Quest pages

Keep the old field labels: Quest Giver, Quest Type, Quest Description, Quest Reward, Return to, Repeatable, Following Quest, Zone.

In-game text block:

- Heading: “In-game text”
- Journal / Offer / Turn-in / Objectives
- “Level range”, never “Client level range”
- No “Recovered from the Dungeon Runners client files”
- Real NPC names, never `QuestGiver_A`
- “This quest was removed from the game.” if it was pulled

## Categories

One article list per category page. Frozen `#mw-pages` HTML plus a live “Pages in this category” dump is wrong.

Rainbow items belong in:

- `Rainbow items`
- Slot: Rainbow Helms, Body Armor, Gloves, Boots, Shoulders, Shields, Rings, Amulets
- Class armor: Fighter / Ranger / Mage Rainbow Armor
- Weapon family: One-Handed-Fighter-Rainbows, Two-Handed-Fighter-Rainbows, One-Handed-Mage-Rainbows, Two-Handed-Mage-Rainbows, Two-Handed-Ranger-Rainbows, One-Handed-Ranger-Rainbows

## More

See [examples.md](examples.md).
