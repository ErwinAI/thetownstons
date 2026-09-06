<script setup lang="ts">
const { user, profile, refresh } = useAuth()
const { isAdmin, canEdit } = useWikiAccess()

async function logout() {
  await useSupabase().auth.signOut()
  await refresh()
}

const sections = [
  { title: 'Navigation', links: [
    { to: '/', label: 'Main Page' },
    { to: '/wiki/Crew', label: 'Crew Page' },
    { to: '/wiki/FAQ', label: 'FAQ' },
    { to: '/wiki/Help/Contents', label: 'Help' },
    { to: '/all', label: 'All pages' },
    { to: '/random', label: 'Random page' },
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
    <NuxtLink to="/" class="wiki-logo" title="Main Page">
      <img class="wiki-logo-img" src="/wiki-logo.png" alt="The Townstons" width="512" height="512">
      <span class="wiki-logo-name">The Townstons</span>
    </NuxtLink>

    <div class="portlet">
      <h5>Search</h5>
      <div class="pBody">
        <form class="wiki-search" action="/search" method="get">
          <input type="search" name="q" aria-label="Search">
          <button type="submit">Go</button>
        </form>
      </div>
    </div>

    <div class="portlet">
      <h5>Account</h5>
      <div class="pBody">
        <ul>
          <template v-if="user">
            <li><span class="wiki-account-email">{{ profile?.username || 'Account' }}</span></li>
            <li v-if="canEdit"><NuxtLink to="/new">New page</NuxtLink></li>
            <li><a href="#" @click.prevent="logout">Log out</a></li>
          </template>
          <template v-else>
            <li><NuxtLink to="/login">Log in</NuxtLink></li>
            <li><NuxtLink to="/signup">Sign up</NuxtLink></li>
          </template>
        </ul>
      </div>
    </div>

    <div v-if="isAdmin" class="portlet">
      <h5>Admin</h5>
      <div class="pBody">
        <ul>
          <li><NuxtLink to="/changes">All changes</NuxtLink></li>
          <li><NuxtLink to="/admin/images">Approve images</NuxtLink></li>
        </ul>
      </div>
    </div>

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
