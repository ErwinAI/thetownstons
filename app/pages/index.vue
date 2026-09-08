<script setup lang="ts">
useHead({ title: 'Main Page' })

const topics = [
  { to: '/wiki/Dungeons', label: 'Dungeons', blurb: 'Schematic maps, outlines and details of all dungeons' },
  { to: '/wiki/Guides', label: 'Guides', blurb: 'Useful information including Interface Guide, Boss Guides, Tips and other stuff.' },
  { to: '/wiki/Skills', label: 'Skills', blurb: 'Information on the effects and costs of all skills.' },
  { to: '/wiki/Category/Monsters', label: 'Monsters', blurb: 'Descriptions, often pictures, and sometimes tips for all monsters' },
  { to: '/wiki/Items', label: 'Items', blurb: 'Weapons, Armor, Jewelry and their uses, with a special section on Mythic (Rainbow) Items.' },
  { to: '/wiki/Category/Quests', label: 'Quests', blurb: 'The Quests that make the game interesting.' },
  { to: "/wiki/Category/NPC's", label: "NPC's", blurb: 'Non Player Characters and Objects you will encounter.' },
  { to: '/wiki/Towns/Outposts', label: 'Towns/Outposts', blurb: 'The places in the game that are NOT dungeons!' },
  { to: '/wiki/Builds', label: 'Builds', blurb: 'Share experience on how to create the perfect character.' },
  { to: '/wiki/Game_Mechanics', label: 'Game Mechanics', blurb: 'Those all important formulae and calculations, and a List of Equations.' },
  { to: '/wiki/Category/Guilds', label: 'Guilds (Posses)', blurb: 'Groups of players working together cooperatively.' },
  { to: '/wiki/Category/Glossary', label: 'Glossary', blurb: 'Definitions of game terms, many with links to more extensive articles.' },
]

const rainbowPages = [
  { to: '/wiki/Rainbow_Drops', label: 'Rainbow Drops', blurb: 'Boss, chest, HDoL, and Well 1-in-N. Five on Insane is 1250% loot.' },
  { to: '/wiki/Boss_Lair_Rainbows', label: 'Boss Lair Rainbows', blurb: 'The named chest lists. Sissirat through Manglefeet, with level floors.' },
  { to: '/wiki/Rainbow_Level_Bands', label: 'Rainbow Level Bands', blurb: 'Which shared-pile names can show at 15 / 35 / 55 / 75 / 95.' },
  { to: '/wiki/Boss_Exclusive_Rainbow_Farming', label: 'Boss-Exclusive Rainbow Farming', blurb: 'Loot percent, party split, and worked examples for those named chests.' },
  { to: '/wiki/Well-Only_Rainbows', label: 'Well-Only Rainbows', blurb: 'Pirate set, mouse ears, Charge!, NC Hammer. Not the shared pile.' },
  { to: '/wiki/Discontinued_Rainbows', label: 'Discontinued Rainbows', blurb: 'Names that still exist but no longer drop. Cooper, Milwaukee, and the rest.' },
  { to: '/wiki/Wishing_Well', label: 'Wishing Well', blurb: 'Two items per paid toss. Well-specific pile is 1 in 20. Cooldown is 30 minutes.' },
]

const news = [
  { date: '8 September 2026', text: 'Rainbow hubs are up: boss lair lists, level bands, Well-only names, discontinued names, and Well odds.' },
  { date: '6 September 2026', text: 'The wiki is live again. Editing is open. We are writing new pages and improving the old ones.' },
  { date: '26 September 2008', text: 'Chunk 4 UPDATE Progress' },
  { date: '12 July 2008', text: 'The new Chunk, loads of info!' },
  { date: '28 May 2008', text: 'The Townstons Forums are up!' },
  { date: '16 May 2008', text: 'Heave 121 Updates in Progress.' },
  { date: '8 May 2008', text: 'Upcoming Major Updates.' },
  { date: '5 March 2008', text: 'The Stiki Wiki Hot-Glue Gun' },
  { date: '4 March 2008', text: 'New Additions' },
  { date: '28 February 2008', text: 'Guides updated' },
]

const polls = [
  {
    q: 'What is the BEST BUILD for a player Levels 1-20?',
    votes: 94,
    answers: [
      { label: 'Fighters Rule!', pct: 32 },
      { label: 'Mages Forever!', pct: 50 },
      { label: 'Rangers Rock!', pct: 12 },
      { label: 'Hybrids are Multi-Talented!', pct: 6 },
    ],
  },
  {
    q: 'Then what is the BEST BUILD for a mid-level player 21-60?',
    votes: 32,
    answers: [
      { label: 'Fighters Kill!', pct: 19 },
      { label: 'Mages Toast Them!', pct: 34 },
      { label: 'Rangers Strike From Afar!', pct: 34 },
      { label: 'Hybrids Do It All!', pct: 13 },
    ],
  },
]
</script>

<template>
  <div>
    <h1 class="firstHeading">Main Page</h1>
    <div id="siteSub">From Townstons</div>

    <div class="home-intro">
      <p class="home-banner home-banner-title">The Townstons</p>
      <p>
        <b>The Townstons is a Fansite wiki. Here you can find information and opinions from lots of players of the popular game Dungeon Runners! You can start increasing your knowledge by clicking on one of the categories below or on the menu to the left. They all contain valuable information which has been contributed by players like YOU!</b>
      </p>
      <ul>
        <li><b>Here is the <NuxtLink to="/wiki/FAQ">FAQ</NuxtLink> which explains all about how this Wiki works.</b></li>
        <li><b>Here is the <NuxtLink to="/wiki/Crew">Crew</NuxtLink> Page which lists the moderators.</b></li>
        <li><b>The MOST important people in this Wiki are YOU, the players and contributors!</b></li>
      </ul>
    </div>

    <div class="home-grid">
      <div class="home-box home-box-wide" style="background:#fff6d6">
        <p class="home-banner">Rainbows</p>
        <ul>
          <li v-for="page in rainbowPages" :key="page.to">
            <b><NuxtLink :to="page.to">{{ page.label }}</NuxtLink>:</b>
            <i> {{ page.blurb }}</i>
          </li>
        </ul>
      </div>

      <div class="home-box" style="background:bisque">
        <p class="home-banner">Main Topics</p>
        <ul>
          <li v-for="topic in topics" :key="topic.to">
            <b><NuxtLink :to="topic.to">{{ topic.label }}</NuxtLink>:</b>
            <i> {{ topic.blurb }}</i>
          </li>
        </ul>
      </div>

      <div class="home-box" style="background:#f0f0ff">
        <p class="home-banner">Contributor</p>
        <p><b>Players like YOU made this wiki successful!</b></p>
        <p>Sign up, confirm your email, and hit Edit. We are writing new pages and cleaning up the old ones. Jump in.</p>
        <p>
          <b>Getting Started:</b>
          See the <NuxtLink to="/wiki/Help/Contents">Beginner's Guide</NuxtLink>
          or browse <NuxtLink to="/all">every article</NuxtLink>.
        </p>
      </div>

      <div class="home-box" style="background:bisque">
        <p class="home-banner">Wiki News</p>
        <p v-for="item in news" :key="item.date">
          <b>{{ item.date }}:
            <NuxtLink to="/wiki/Main_Page/news">News Message</NuxtLink>
          </b>
          {{ item.text }}
        </p>
      </div>

      <div class="home-box" style="background:#f0f0ff">
        <p class="home-banner">Poll</p>
        <div v-for="poll in polls" :key="poll.q" style="margin-bottom:1.2em">
          <p>
            <b>{{ poll.q }}</b>
            <span class="poll-meta"> ({{ poll.votes }} votes)</span>
          </p>
          <p v-for="answer in poll.answers" :key="answer.label">
            {{ answer.label }}
            <span style="display:inline-block;height:10px;background:#6b8cff;margin:0 6px 0 8px" :style="{ width: (answer.pct * 1.4) + 'px' }" />
            <span class="poll-meta">{{ answer.pct }}%</span>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
