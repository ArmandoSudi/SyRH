<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchHealth, type Health } from '@/features/systeme/api/health'

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
  <section class="sy-card status" aria-live="polite">
    <div class="sy-card-header">
      <h2 class="sy-card-title">
        <span class="sy-icon"><i class="pi pi-database" aria-hidden="true" /></span>
        État du système
      </h2>
    </div>
    <p v-if="error" class="ko" data-test="error">API injoignable : {{ error }}</p>
    <dl v-else-if="health" data-test="health">
      <dt>API</dt>
      <dd class="ok">{{ health.status }}</dd>
      <dt>Base de données</dt>
      <dd>{{ health.database.vendor }} {{ health.database.version }}</dd>
      <dt>Nom de la base</dt>
      <dd>{{ health.database.name }}</dd>
    </dl>
    <p v-else class="sy-muted">Vérification en cours…</p>
  </section>
</template>

<style scoped>
.status {
  max-width: 36rem;
}

dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.5rem 1.5rem;
  margin: 0;
}

dt {
  color: var(--sy-muted);
}

dd {
  margin: 0;
}

.ok {
  color: var(--sy-success);
  font-weight: 600;
}

.ko {
  color: var(--sy-danger);
}
</style>
