<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import InputText from 'primevue/inputtext'

import ThemeToggle from '@/components/ui/ThemeToggle.vue'

interface NavItem {
  to: string
  label: string
  icon: string
}

const mainNav: NavItem[] = [
  { to: '/', label: 'Tableau de bord', icon: 'pi pi-home' },
  { to: '/agents', label: 'Agents', icon: 'pi pi-users' },
  { to: '/carriere', label: 'Carrière', icon: 'pi pi-briefcase' },
  { to: '/personnel', label: 'Présences', icon: 'pi pi-calendar' },
  { to: '/paie', label: 'Paie', icon: 'pi pi-wallet' },
  { to: '/social', label: 'Social', icon: 'pi pi-heart' },
  { to: '/formation', label: 'Formation', icon: 'pi pi-graduation-cap' },
]

const adminNav: NavItem[] = [
  { to: '/referentiels', label: 'Référentiels', icon: 'pi pi-sliders-h' },
  { to: '/systeme', label: 'Système', icon: 'pi pi-server' },
  { to: '/design', label: 'Design', icon: 'pi pi-palette' },
]

const route = useRoute()
const title = computed(() => (route.meta.title as string | undefined) ?? 'SyRH')
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <RouterLink to="/" class="brand" aria-label="SyRH, accueil">
        <span class="mark" aria-hidden="true">S</span>
        <span class="wordmark">SyRH</span>
      </RouterLink>

      <nav aria-label="Navigation principale">
        <RouterLink v-for="item in mainNav" :key="item.to" :to="item.to" :title="item.label">
          <i :class="item.icon" aria-hidden="true" />
          <span>{{ item.label }}</span>
        </RouterLink>

        <p class="group">Administration</p>
        <RouterLink v-for="item in adminNav" :key="item.to" :to="item.to" :title="item.label">
          <i :class="item.icon" aria-hidden="true" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
    </aside>

    <div class="main">
      <header class="topbar">
        <h1>{{ title }}</h1>
        <label class="search">
          <i class="pi pi-search" aria-hidden="true" />
          <InputText placeholder="Rechercher un agent…" aria-label="Rechercher un agent" />
        </label>
        <ThemeToggle />
        <button type="button" class="round" aria-label="Notifications" title="Notifications">
          <i class="pi pi-bell" aria-hidden="true" />
        </button>
        <span class="avatar" title="Utilisateur" aria-label="Utilisateur">RH</span>
      </header>

      <RouterView />
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 15.5rem minmax(0, 1fr);
  min-height: 100vh;
}

/* --- Sidebar ---------------------------------------------------------- */

.sidebar {
  position: sticky;
  top: 0;
  align-self: start;
  height: 100vh;
  overflow-y: auto;
  padding: var(--sy-space-5) var(--sy-space-4);
  background: var(--sy-surface);
  border-right: 1px solid var(--sy-border);
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--sy-space-3);
  padding: 0 var(--sy-space-2);
  margin-bottom: var(--sy-space-5);
  text-decoration: none;
}

.mark {
  display: grid;
  place-items: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: var(--sy-radius-sm);
  background: var(--sy-lime);
  color: var(--sy-on-lime);
  font-weight: 800;
}

.wordmark {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

nav a {
  display: flex;
  align-items: center;
  gap: var(--sy-space-3);
  padding: 0.6rem 0.85rem;
  border-radius: var(--sy-radius-pill);
  color: var(--sy-muted);
  font-size: 0.93rem;
  font-weight: 500;
  text-decoration: none;
}

nav a:hover {
  background: var(--sy-surface-2);
  color: var(--sy-text);
}

nav a.router-link-exact-active {
  background: var(--sy-inverse);
  color: var(--sy-on-inverse);
}

.group {
  margin: var(--sy-space-5) 0 var(--sy-space-2);
  padding: 0 0.85rem;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--sy-muted);
}

/* --- Main column ------------------------------------------------------ */

.main {
  padding: var(--sy-space-5) var(--sy-space-6) var(--sy-space-6);
  min-width: 0;
}

.topbar {
  display: flex;
  align-items: center;
  gap: var(--sy-space-3);
  margin-bottom: var(--sy-space-5);
}

.topbar h1 {
  flex: 1;
  font-size: 1.6rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.search {
  position: relative;
  display: flex;
  align-items: center;
}

.search i {
  position: absolute;
  left: 0.9rem;
  color: var(--sy-muted);
  font-size: 0.85rem;
  pointer-events: none;
}

.search :deep(input) {
  width: 16rem;
  padding-left: 2.4rem;
  border-radius: var(--sy-radius-pill);
}

.round,
.avatar {
  display: grid;
  place-items: center;
  flex: none;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
}

.round {
  border: 1px solid var(--sy-border);
  background: var(--sy-surface);
  color: var(--sy-text);
  cursor: pointer;
}

.round:hover {
  background: var(--sy-surface-2);
}

.avatar {
  background: var(--sy-violet);
  color: var(--sy-on-violet);
  font-size: 0.8rem;
  font-weight: 700;
}

/* --- Narrow screens: the sidebar becomes an icon rail ------------------ */

@media (max-width: 1000px) {
  .shell {
    grid-template-columns: 4.5rem minmax(0, 1fr);
  }

  .sidebar {
    padding-inline: var(--sy-space-3);
  }

  .brand {
    justify-content: center;
    padding: 0;
  }

  .wordmark,
  nav a span,
  .group {
    display: none;
  }

  nav a {
    justify-content: center;
    padding: 0.75rem 0;
  }

  .main {
    padding-inline: var(--sy-space-4);
  }

  .search {
    display: none;
  }
}
</style>
