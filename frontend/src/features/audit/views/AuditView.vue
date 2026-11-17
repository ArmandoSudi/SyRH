<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable, { type DataTablePageEvent, type DataTableRowClickEvent } from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import {
  fetchEntries,
  fetchEntry,
  type AuditEntry,
  type AuditEntryDetail,
} from '@/features/audit/api/audit'
import AuditEntryPanel from '@/features/audit/components/AuditEntryPanel.vue'
import {
  ACTION_OPTIONS,
  ACTION_SEVERITY,
  formatDateTime,
} from '@/features/audit/components/format'
import { useAuditStore } from '@/features/audit/stores/audit'
import { useAuthStore } from '@/features/auth/stores/auth'
import { MODULE_PERMISSIONS, type ModuleKey } from '@/shared/utils/modules'

const PAGE_SIZE = 50

// Modules that hold business tables, with their labels. Système and the audit
// log itself have none.
const SCOPE_LABELS: [ModuleKey | 'comptes', string][] = [
  ['agents', 'Agents'],
  ['carriere', 'Carrière'],
  ['personnel', 'Présences'],
  ['paie', 'Paie'],
  ['social', 'Social'],
  ['formation', 'Formation'],
  ['referentiels', 'Référentiels'],
  ['comptes', 'Comptes'],
]

const store = useAuditStore()
const auth = useAuthStore()

// The reader's own modules, plus account administration (D21). The API
// filters on its own; this only avoids offering empty choices.
const moduleOptions = computed(() =>
  SCOPE_LABELS.filter(([key]) => key === 'comptes' || auth.can(MODULE_PERMISSIONS[key])).map(
    ([value, label]) => ({ value, label }),
  ),
)

const entries = ref<AuditEntry[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const selected = ref<AuditEntryDetail | null>(null)
const panelOpen = ref(false)
const panelError = ref<string | null>(null)

let latest = 0

async function load() {
  const call = ++latest
  loading.value = true
  error.value = null
  try {
    const page = await fetchEntries(store.query)
    if (call !== latest) return // a newer request superseded this one
    entries.value = page.results
    total.value = page.count
  } catch (e) {
    if (call !== latest) return
    error.value = e instanceof Error ? e.message : String(e)
    entries.value = []
    total.value = 0
  } finally {
    if (call === latest) loading.value = false
  }
}

function onPage(event: DataTablePageEvent) {
  store.page = event.page + 1
}

async function onRowClick(event: DataTableRowClickEvent) {
  const row = event.data as AuditEntry
  panelError.value = null
  selected.value = null
  panelOpen.value = true
  try {
    selected.value = await fetchEntry(row.id)
  } catch (e) {
    panelError.value = e instanceof Error ? e.message : String(e)
  }
}

// Any filter change goes back to page 1; typing in the author field waits a
// moment so each keystroke does not hit the API.
let typing: ReturnType<typeof setTimeout> | undefined
watch(
  () => [store.periode, store.module, store.action],
  () => {
    store.page = 1
    void load()
  },
  { deep: true },
)
watch(
  () => store.auteur,
  () => {
    clearTimeout(typing)
    typing = setTimeout(() => {
      store.page = 1
      void load()
    }, 300)
  },
)
watch(
  () => store.page,
  () => void load(),
)

onMounted(load)

const first = computed(() => (store.page - 1) * PAGE_SIZE)
</script>

<template>
  <section class="sy-card">
    <div class="sy-card-header">
      <h2 class="sy-card-title">
        <span class="sy-icon"><i class="pi pi-history" aria-hidden="true" /></span>
        Journal d'audit
      </h2>
      <span class="sy-muted sy-num" data-test="total">
        {{ total }} entrée{{ total > 1 ? 's' : '' }}
      </span>
    </div>

    <form class="filters" role="search" aria-label="Filtrer le journal" @submit.prevent>
      <DatePicker
        v-model="store.periode"
        selection-mode="range"
        :manual-input="false"
        date-format="dd/mm/yy"
        placeholder="Période"
        show-button-bar
        aria-label="Période"
      />
      <InputText v-model="store.auteur" placeholder="Auteur" aria-label="Auteur" />
      <Select
        v-model="store.module"
        :options="moduleOptions"
        option-label="label"
        option-value="value"
        placeholder="Module"
        show-clear
        aria-label="Module"
        data-test="module-filter"
      />
      <Select
        v-model="store.action"
        :options="ACTION_OPTIONS"
        option-label="label"
        option-value="value"
        placeholder="Action"
        show-clear
        aria-label="Action"
      />
      <Button
        v-if="store.hasFilters"
        type="button"
        label="Effacer les filtres"
        icon="pi pi-filter-slash"
        text
        @click="store.reset()"
      />
    </form>

    <Message v-if="error" severity="error" :closable="false" data-test="error">
      Le journal n'a pas pu être chargé : {{ error }}
    </Message>

    <DataTable
      :value="entries"
      lazy
      paginator
      :rows="PAGE_SIZE"
      :first="first"
      :total-records="total"
      :loading="loading"
      data-key="id"
      row-hover
      class="entries"
      @page="onPage"
      @row-click="onRowClick"
    >
      <template #empty>
        <p class="sy-muted empty">Aucune entrée ne correspond à ces critères.</p>
      </template>
      <Column header="Date et heure">
        <template #body="{ data }">
          <span class="sy-num nowrap">{{ formatDateTime(data.date) }}</span>
        </template>
      </Column>
      <Column header="Auteur" field="auteur.nom" />
      <Column header="Action">
        <template #body="{ data }">
          <Tag :value="data.action_libelle" :severity="ACTION_SEVERITY[data.action as keyof typeof ACTION_SEVERITY]" />
        </template>
      </Column>
      <Column header="Module" field="module_libelle" />
      <Column header="Table" field="table.libelle" />
      <Column header="Objet" field="objet_libelle" />
    </DataTable>

    <Drawer
      v-model:visible="panelOpen"
      position="right"
      header="Détail de l'entrée"
      class="audit-drawer"
    >
      <Message v-if="panelError" severity="error" :closable="false">{{ panelError }}</Message>
      <AuditEntryPanel v-else-if="selected" :entry="selected" />
      <p v-else class="sy-muted">Chargement…</p>
    </Drawer>
  </section>
</template>

<style scoped>
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sy-space-3);
  margin-bottom: var(--sy-space-4);
}

.filters > * {
  min-width: 12rem;
}

.entries :deep(tbody tr) {
  cursor: pointer;
}

/* Narrow screens: the table scrolls inside the card instead of being cut. */
.entries :deep(.p-datatable-table-container) {
  overflow-x: auto;
}

@media (max-width: 640px) {
  .filters > * {
    flex: 1 1 100%;
    min-width: 0;
  }
}

.nowrap {
  white-space: nowrap;
}

.empty {
  padding: var(--sy-space-4) 0;
  text-align: center;
}
</style>

<style>
/* The drawer is teleported to <body>, outside this component's scope. */
.audit-drawer.p-drawer {
  width: min(34rem, 100vw);
}
</style>
