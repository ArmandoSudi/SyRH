<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchHealth, type Health } from '@/api/health'

const health = ref<Health | null>(null)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    health.value = await fetchHealth()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
})
</script>

<template>
  <main>
    <h1>SyRH</h1>
    <p class="subtitle">Système de gestion des ressources humaines de l'ARPTC</p>

    <section class="status" aria-live="polite">
      <h2>État du système</h2>
      <p v-if="error" class="ko" data-test="error">API injoignable : {{ error }}</p>
      <dl v-else-if="health" data-test="health">
        <dt>API</dt>
        <dd class="ok">{{ health.status }}</dd>
        <dt>Base de données</dt>
        <dd>{{ health.database.vendor }} {{ health.database.version }}</dd>
        <dt>Nom de la base</dt>
        <dd>{{ health.database.name }}</dd>
      </dl>
      <p v-else>Vérification en cours…</p>
    </section>
  </main>
</template>

<style scoped>
main {
  max-width: 40rem;
  margin: 4rem auto;
  padding: 0 1rem;
}

.subtitle {
  color: var(--muted);
}

.status {
  margin-top: 2rem;
  padding: 1rem 1.25rem;
  border: 1px solid var(--border);
  border-radius: 8px;
}

h2 {
  font-size: 1rem;
  margin: 0 0 0.75rem;
}

dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.4rem 1.5rem;
  margin: 0;
}

dt {
  color: var(--muted);
}

dd {
  margin: 0;
}

.ok {
  color: var(--ok);
  font-weight: 600;
}

.ko {
  color: var(--ko);
}
</style>
