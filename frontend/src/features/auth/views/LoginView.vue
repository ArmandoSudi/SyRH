<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'

import { ApiError } from '@/shared/utils/http'
import ThemeToggle from '@/shared/ui/ThemeToggle.vue'
import { safeRedirect } from '@/router/guards'
import { useAuthStore } from '@/features/auth/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

async function submit() {
  if (loading.value) return
  loading.value = true
  error.value = null
  try {
    await auth.login(username.value, password.value)
    await router.replace(safeRedirect(route.query.redirect))
  } catch (e) {
    password.value = ''
    error.value =
      e instanceof ApiError && e.status === 400
        ? e.message
        : 'Connexion impossible pour le moment. Réessayez dans un instant.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="page">
    <div class="theme"><ThemeToggle /></div>

    <section class="sy-card panel">
      <div class="brand">
        <span class="mark" aria-hidden="true">S</span>
        <span class="wordmark">SyRH</span>
      </div>
      <h1>Connexion</h1>
      <p class="sy-muted intro">Système de gestion des ressources humaines de l'ARPTC.</p>

      <form novalidate @submit.prevent="submit">
        <Message v-if="error" severity="error" :closable="false" data-test="error">
          {{ error }}
        </Message>

        <div class="field">
          <label for="username">Identifiant</label>
          <InputText
            id="username"
            v-model="username"
            name="username"
            autocomplete="username"
            autocapitalize="none"
            spellcheck="false"
            autofocus
            fluid
            required
          />
        </div>

        <div class="field">
          <label for="password">Mot de passe</label>
          <Password
            v-model="password"
            input-id="password"
            name="password"
            :input-props="{ autocomplete: 'current-password', required: true }"
            :feedback="false"
            toggle-mask
            fluid
          />
        </div>

        <Button
          type="submit"
          label="Se connecter"
          severity="contrast"
          :loading="loading"
          :disabled="loading || !username || !password"
          fluid
        />
      </form>

      <p class="sy-muted help">
        Mot de passe oublié ? Adressez-vous à l'administrateur du système.
      </p>
    </section>
  </main>
</template>

<style scoped>
.page {
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: var(--sy-space-6) var(--sy-space-4);
}

.theme {
  position: absolute;
  top: var(--sy-space-4);
  right: var(--sy-space-4);
}

.panel {
  width: 100%;
  max-width: 25rem;
  padding: var(--sy-space-6);
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--sy-space-3);
  margin-bottom: var(--sy-space-5);
}

.mark {
  display: grid;
  place-items: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: var(--sy-radius-sm);
  background: var(--sy-lime);
  color: var(--sy-on-lime);
  font-weight: 800;
}

.wordmark {
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

h1 {
  font-size: 1.6rem;
}

.intro {
  margin-top: var(--sy-space-1);
}

form {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-4);
  margin-top: var(--sy-space-5);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-2);
}

label {
  font-size: 0.9rem;
  font-weight: 600;
}

.help {
  margin-top: var(--sy-space-5);
  font-size: 0.85rem;
  text-align: center;
}

@media (max-width: 420px) {
  .panel {
    padding: var(--sy-space-5);
  }
}
</style>
