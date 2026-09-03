<script setup lang="ts">
const sections = [
  { title: 'Navigation', links: [
    { to: '/', label: 'Main Page' },
    { to: '/wiki/Crew', label: 'Crew Page' },
    { to: '/wiki/Current_events', label: 'Current events' },
    { to: '/wiki/Townstons/Projects', label: 'Projects' },
    { to: '/all', label: 'All pages' },
    { to: '/random', label: 'Random page' },
    { to: '/wiki/Help/Contents', label: 'Help' },
  ]},
  { title: 'Contact', links: [
    { to: '/wiki/Contact', label: 'Contact Info' },
    { to: '/wiki/FAQ', label: 'FAQ' },
    { to: '/wiki/Donations', label: 'Donate' },
  ]},
  { title: 'Sections', links: [
    { to: '/wiki/Category/Quests', label: 'Quests' },
    { to: '/wiki/Category/Monsters', label: 'Monsters' },
    { to: '/wiki/Items', label: 'Items' },
    { to: '/wiki/Skills', label: 'Skills' },
    { to: '/wiki/Towns/Outposts', label: 'Towns/Outposts' },
    { to: '/wiki/Dungeons', label: 'Dungeons' },
    { to: "/wiki/Category/NPC's", label: "NPC's" },
    { to: '/wiki/Guides', label: 'Guides' },
    { to: '/wiki/Builds', label: 'Builds' },
    { to: '/wiki/Category/Guilds', label: 'Guilds (Posses)' },
    { to: '/wiki/Category/Game_Mechanics', label: 'Game Mechanics' },
  ]},
  { title: 'Special', links: [
    { to: '/wiki/Category/Rainbow_Items', label: 'Rainbow List' },
    { to: '/wiki/List_of_Equations', label: 'List of Equations' },
    { to: '/wiki/Category/Glossary', label: 'Glossary' },
    { to: '/wiki/The_Townstons', label: 'The Townstons' },
  ]},
]
</script>

<template>
  <aside class="wiki-sidebar" id="column-one">
    <NuxtLink to="/" class="wiki-logo is-text" title="Main Page">
      <span class="wiki-logo-the">The</span>
      <span class="wiki-logo-name">Townstons</span>
    </NuxtLink>

    <div v-for="group in sections" :key="group.title" class="portlet">
      <h5>{{ group.title }}</h5>
      <div class="pBody">
        <ul>
          <li v-for="link in group.links" :key="link.to">
            <NuxtLink :to="link.to">{{ link.label }}</NuxtLink>
          </li>
        </ul>
      </div>
    </div>
  </aside>
</template>
