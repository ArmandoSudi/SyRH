<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Menu from 'primevue/menu'
import type { MenuItem } from 'primevue/menuitem'

import { LOGIN_PATH } from '@/router/guards'
import { useAuthStore } from '@/features/auth/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const menu = ref<InstanceType<typeof Menu> | null>(null)

async function signOut() {
  try {
    await auth.logout()
  } catch {
    // Session already gone, or server unreachable: leave the screen either way.
    auth.clear()
  }
  await router.push(LOGIN_PATH)
}

const items: MenuItem[] = [
  {
    label: 'Changer le mot de passe',
    icon: 'pi pi-lock',
    command: () => void router.push({ name: 'password' }),
  },
  { separator: true },
  { label: 'Se déconnecter', icon: 'pi pi-sign-out', command: () => void signOut() },
]
</script>

<template>
  <button
    type="button"
    class="user"
    aria-haspopup="true"
    aria-controls="user-menu"
    :aria-label="`Compte de ${auth.displayName}`"
    @click="menu?.toggle($event)"
  >
    <span class="avatar" aria-hidden="true" data-test="initials">{{ auth.initials }}</span>
    <span class="name" data-test="name">{{ auth.displayName }}</span>
    <i class="pi pi-chevron-down" aria-hidden="true" />
  </button>
  <Menu id="user-menu" ref="menu" :model="items" popup />
</template>

<style scoped>
.user {
  display: flex;
  align-items: center;
  gap: var(--sy-space-2);
  flex: none;
  padding: 3px 0.85rem 3px 3px;
  border: 1px solid var(--sy-border);
  border-radius: var(--sy-radius-pill);
  background: var(--sy-surface);
  color: var(--sy-text);
  font: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
}

.user:hover {
  background: var(--sy-surface-2);
}

.avatar {
  display: grid;
  place-items: center;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  background: var(--sy-violet);
  color: var(--sy-on-violet);
  font-size: 0.8rem;
  font-weight: 700;
}

.name {
  max-width: 11rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pi {
  font-size: 0.7rem;
  color: var(--sy-muted);
}

/* Below this width the page title needs the room more than the name does. */
@media (max-width: 1200px) {
  .user {
    padding-right: 3px;
  }

  .name,
  .pi {
    display: none;
  }
}
</style>
