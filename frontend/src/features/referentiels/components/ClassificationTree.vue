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

import {
  fetchCategories,
  fetchEchelons,
  fetchGrades,
  type Categorie,
  type Echelon,
  type Grade,
} from '@/features/referentiels/api/referentiels'
import {
  buildClassification,
  NIVEAU_LIBELLE,
  NIVEAU_SEVERITY,
  searchText,
  type Niveau,
} from '@/features/referentiels/components/classification'
import { expandedKeys, filterTree } from '@/features/referentiels/components/tree'
import { useReferentielsStore } from '@/features/referentiels/stores/referentiels'
import { formatDate, localDate } from '@/shared/utils/dates'

// Read-only: the grid is edited in Django admin until roadmap 1.9 (classification D30).
const store = useReferentielsStore()
const state = store.classification

const lists = ref<{ categories: Categorie[]; grades: Grade[]; echelons: Echelon[] }>({
  categories: [],
  grades: [],
  echelons: [],
})
const loading = ref(false)
const error = ref<string | null>(null)

let latest = 0

async function load() {
  const call = ++latest
  loading.value = true
  error.value = null
  try {
    const options = { date: localDate(state.date) }
    const [categories, grades, echelons] = await Promise.all([
      fetchCategories(options),
      fetchGrades(options),
      fetchEchelons(options),
    ])
    if (call !== latest) return // a newer request superseded this one
    lists.value = { categories, grades, echelons }
  } catch (e) {
    if (call !== latest) return
    error.value = e instanceof Error ? e.message : String(e)
    lists.value = { categories: [], grades: [], echelons: [] }
  } finally {
    if (call === latest) loading.value = false
  }
}

const tree = computed(() =>
  buildClassification(lists.value.categories, lists.value.grades, lists.value.echelons),
)
const visible = computed(() => filterTree(tree.value, state.texte, searchText))
const filtering = computed(() => state.texte.trim() !== '')

// While filtering, every match is shown with its ancestors opened.
const expanded = computed({
  get: () => (filtering.value ? expandedKeys(visible.value) : state.expanded),
  set: (keys: Record<string, boolean>) => {
    if (!filtering.value) state.expanded = keys
  },
})

function expandAll() {
  state.texte = ''
  state.expanded = expandedKeys(tree.value)
}

function collapseAll() {
  state.texte = ''
  state.expanded = {}
}

watch(
  () => state.date,
  () => void load(),
)
onMounted(load)
</script>

<template>
  <div class="toolbar" role="search" aria-label="Filtrer la classification">
    <label class="field">
      <span class="sy-muted">Classification au</span>
      <DatePicker
        v-model="state.date"
        :manual-input="false"
        date-format="dd/mm/yy"
        show-icon
        icon-display="input"
        aria-label="Classification au"
        data-test="classification-date"
      />
    </label>
    <IconField class="search">
      <InputIcon class="pi pi-search" />
      <InputText
        v-model="state.texte"
        placeholder="Code ou nom"
        aria-label="Rechercher dans la classification"
        data-test="classification-search"
      />
    </IconField>
    <div class="actions">
      <Button
        type="button"
        label="Tout déplier"
        icon="pi pi-angle-double-down"
        text
        severity="secondary"
        data-test="classification-expand-all"
        @click="expandAll"
      />
      <Button
        type="button"
        label="Tout replier"
        icon="pi pi-angle-double-up"
        text
        severity="secondary"
        data-test="classification-collapse-all"
        @click="collapseAll"
      />
    </div>
  </div>

  <Message v-if="error" severity="error" :closable="false" data-test="classification-error">
    La classification n'a pas pu être chargée : {{ error }}
  </Message>

  <TreeTable
    v-model:expanded-keys="expanded"
    :value="visible"
    :loading="loading"
    class="tree"
    data-test="classification"
  >
    <template #empty>
      <p class="sy-muted empty">
        {{
          filtering
            ? 'Aucune ligne ne correspond à cette recherche.'
            : 'Aucune catégorie à cette date.'
        }}
      </p>
    </template>
    <Column field="nom" header="Nom" expander header-class="name-col" body-class="name-col">
      <template #body="{ node }">
        <span :class="{ name: node.data.niveau !== 'echelon' }">{{ node.data.nom }}</span>
      </template>
    </Column>
    <Column header="Code">
      <template #body="{ node }">
        <span class="sy-num nowrap">{{ node.data.code }}</span>
      </template>
    </Column>
    <Column header="Niveau">
      <template #body="{ node }">
        <Tag
          :value="NIVEAU_LIBELLE[node.data.niveau as Niveau]"
          :severity="NIVEAU_SEVERITY[node.data.niveau as Niveau]"
        />
      </template>
    </Column>
    <Column header="Rang">
      <template #body="{ node }">
        <span class="sy-num">{{ node.data.rang ?? '' }}</span>
      </template>
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
