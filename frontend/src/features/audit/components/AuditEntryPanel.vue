<script setup lang="ts">
import Tag from 'primevue/tag'

import type { AuditEntryDetail } from '@/features/audit/api/audit'
import { ACTION_SEVERITY, formatDateTime, formatValue } from '@/features/audit/components/format'

defineProps<{ entry: AuditEntryDetail }>()
</script>

<template>
  <article class="panel" data-test="audit-panel">
    <header>
      <Tag :value="entry.action_libelle" :severity="ACTION_SEVERITY[entry.action]" />
      <h3>{{ entry.objet_libelle }}</h3>
      <p class="sy-muted">
        {{ entry.table.libelle }} · {{ entry.module_libelle }}<br />
        {{ formatDateTime(entry.date) }} · {{ entry.auteur.nom }}
      </p>
    </header>

    <p v-if="!entry.changements.length" class="sy-muted" data-test="no-change">
      Aucun champ enregistré.
    </p>
    <table v-else>
      <thead>
        <tr>
          <th scope="col">Champ</th>
          <th scope="col">Avant</th>
          <th scope="col">Après</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="change in entry.changements" :key="change.champ" data-test="change">
          <th scope="row">{{ change.libelle }}</th>
          <template v-if="change.ajoutes || change.retires">
            <td>
              <span v-if="change.retires?.length" class="removed">
                Retirés : {{ change.retires.join(', ') }}
              </span>
              <span v-else>—</span>
            </td>
            <td>
              <span v-if="change.ajoutes?.length" class="added">
                Ajoutés : {{ change.ajoutes.join(', ') }}
              </span>
              <span v-else>—</span>
            </td>
          </template>
          <template v-else>
            <td>{{ formatValue(change.avant) }}</td>
            <td>{{ formatValue(change.apres) }}</td>
          </template>
        </tr>
      </tbody>
    </table>
  </article>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-4);
}

header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--sy-space-2);
}

h3 {
  font-size: 1.15rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

th,
td {
  padding: 0.55rem 0.5rem;
  border-bottom: 1px solid var(--sy-border);
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}

thead th {
  color: var(--sy-muted);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

tbody th {
  font-weight: 600;
  width: 30%;
}

.added {
  color: var(--sy-success);
}

.removed {
  color: var(--sy-danger);
}
</style>
