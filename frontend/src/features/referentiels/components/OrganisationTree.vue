<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DatePicker from 'primevue/datepicker'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import TreeTable from 'primevue/treetable'

import { fetchUnites, type Unite } from '@/features/referentiels/api/referentiels'
import {
  buildTree,
  expandedKeys,
  filterTree,
  TYPE_SEVERITY,
} from '@/features/referentiels/components/tree'
import { useReferentielsStore } from '@/features/referentiels/stores/referentiels'
import { formatDate, localDate } from '@/shared/utils/dates'

const store = useReferentielsStore()

const unites = ref<Unite[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

let latest = 0

async function load() {
  const call = ++latest
  loading.value = true
  error.value = null
  try {
    const rows = await fetchUnites({ date: localDate(store.date) })
    if (call !== latest) return // a newer request superseded this one
    unites.value = rows
  } catch (e) {
    if (call !== latest) return
    error.value = e instanceof Error ? e.message : String(e)
    unites.value = []
  } finally {
    if (call === latest) loading.value = false
  }
}

const tree = computed(() => buildTree(unites.value))
const visible = computed(() => filterTree(tree.value, store.texte))
const filtering = computed(() => store.texte.trim() !== '')

// While filtering, every match is shown with its ancestors opened.
const expanded = computed({
  get: () => (filtering.value ? expandedKeys(visible.value) : store.expanded),
  set: (keys: Record<string, boolean>) => {
    if (!filtering.value) store.expanded = keys
  },
})

function expandAll() {
  store.texte = ''
  store.expanded = expandedKeys(tree.value)
}

function collapseAll() {
  store.texte = ''
  store.expanded = {}
}

watch(
  () => store.date,
  () => void load(),
)
onMounted(load)
</script>

<template>
  <div class="toolbar" role="search" aria-label="Filtrer l'organisation">
    <label class="field">
      <span class="sy-muted">Organisation au</span>
      <DatePicker
        v-model="store.date"
        :manual-input="false"
        date-format="dd/mm/yy"
        show-icon
        icon-display="input"
        aria-label="Organisation au"
        data-test="date"
      />
    </label>
    <IconField class="search">
      <InputIcon class="pi pi-search" />
      <InputText
        v-model="store.texte"
        placeholder="Code ou nom"
        aria-label="Rechercher une unité"
        data-test="search"
      />
    </IconField>
    <div class="actions">
      <Button
        type="button"
        label="Tout déplier"
        icon="pi pi-angle-double-down"
        text
        severity="secondary"
        data-test="expand-all"
        @click="expandAll"
      />
      <Button
        type="button"
        label="Tout replier"
        icon="pi pi-angle-double-up"
        text
        severity="secondary"
        data-test="collapse-all"
        @click="collapseAll"
      />
    </div>
  </div>

  <Message v-if="error" severity="error" :closable="false" data-test="error">
    L'organisation n'a pas pu être chargée : {{ error }}
  </Message>

  <TreeTable
    v-model:expanded-keys="expanded"
    :value="visible"
    :loading="loading"
    class="tree"
    data-test="tree"
  >
    <template #empty>
      <p class="sy-muted empty">
        {{ filtering ? 'Aucune unité ne correspond à cette recherche.' : 'Aucune unité à cette date.' }}
      </p>
    </template>
    <Column field="nom" header="Nom" expander header-class="name-col" body-class="name-col">
      <template #body="{ node }">
        <span class="name">{{ node.data.nom }}</span>
      </template>
    </Column>
    <Column header="Code">
      <template #body="{ node }">
        <span class="sy-num nowrap">{{ node.data.code }}</span>
      </template>
    </Column>
    <Column header="Type">
      <template #body="{ node }">
        <Tag :value="node.data.type_libelle" :severity="TYPE_SEVERITY[node.data.type as Unite['type']]" />
      </template>
    </Column>
    <Column header="Site">
      <template #body="{ node }">{{ node.data.site.nom }}</template>
    </Column>
    <Column header="Ouverture">
      <template #body="{ node }">
        <span class="sy-num nowrap">{{ formatDate(node.data.date_ouverture) }}</span>
      </template>
    </Column>
    <Column header="Fermeture">
      <template #body="{ node }">
        <span class="sy-num nowrap">{{ formatDate(node.data.date_fermeture) }}</span>
      </template>
    </Column>
  </TreeTable>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: var(--sy-space-3);
  margin-bottom: var(--sy-space-4);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-1);
  font-size: 0.85rem;
}

.search {
  min-width: 16rem;
}

.search :deep(input) {
  width: 100%;
}

.actions {
  display: flex;
  gap: var(--sy-space-1);
  margin-left: auto;
  white-space: nowrap;
}

/* Narrow screens: the tree scrolls inside the card instead of being cut. */
.tree :deep(.p-treetable-table-container) {
  overflow-x: auto;
}

.name {
  font-weight: 500;
}

/* Names stay readable; the table scrolls sideways before squeezing them. */
.tree :deep(.name-col) {
  min-width: 18rem;
}

.nowrap {
  white-space: nowrap;
}

.empty {
  padding: var(--sy-space-4) 0;
  text-align: center;
}

@media (max-width: 640px) {
  .field,
  .search {
    flex: 1 1 100%;
    min-width: 0;
  }

  .actions {
    margin-left: 0;
  }
}
</style>
