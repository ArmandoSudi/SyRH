<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import TreeTable from 'primevue/treetable'

import {
  fetchPiecesRequises,
  fetchTypesDocument,
  type PieceRequise,
  type TypeDocument,
} from '@/features/referentiels/api/referentiels'
import { buildPieces, filterPieces, nombreLibelle } from '@/features/referentiels/components/pieces'
import { expandedKeys } from '@/features/referentiels/components/tree'
import type { Valeurs } from '@/features/referentiels/api/edition'
import ActionsLigne from '@/features/referentiels/components/edition/ActionsLigne.vue'
import EditionDialog from '@/features/referentiels/components/edition/EditionDialog.vue'
import { useEdition } from '@/features/referentiels/components/edition/useEdition'
import { useReferentielsStore } from '@/features/referentiels/stores/referentiels'
import { formatDate, localDate } from '@/shared/utils/dates'

// Editors change the requirements and the document types here (tree reference screens D15).
const store = useReferentielsStore()
const state = store.pieces

const lists = ref<{ types: TypeDocument[]; pieces: PieceRequise[] }>({ types: [], pieces: [] })
const loading = ref(false)
const error = ref<string | null>(null)

let latest = 0

async function load() {
  const call = ++latest
  loading.value = true
  error.value = null
  try {
    const options = { date: localDate(state.date) }
    const [types, pieces] = await Promise.all([
      fetchTypesDocument(options),
      fetchPiecesRequises(options),
    ])
    if (call !== latest) return // a newer request superseded this one
    lists.value = { types, pieces }
  } catch (e) {
    if (call !== latest) return
    error.value = e instanceof Error ? e.message : String(e)
    lists.value = { types: [], pieces: [] }
  } finally {
    if (call === latest) loading.value = false
  }
}

// Without data (an error), no event row is shown: an empty list would claim that
// nothing is required.
const tree = computed(() => (error.value ? [] : buildPieces(lists.value.types, lists.value.pieces)))
const visible = computed(() => filterPieces(tree.value, state.texte))
const filtering = computed(() => state.texte.trim() !== '')

// While filtering, every event that matches is shown opened.
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

const pieces = useEdition('pieces-requises', load)
const types = useEdition('types-document', load)
const { droits: droitsPieces, ouvrir: ouvrirPiece } = pieces
const { droits: droitsTypes, ouvrir: ouvrirType } = types
const dialogues = [
  { cle: 'pieces', ...pieces },
  { cle: 'types', ...types },
]

/** The requirement behind a tree row (its key is pr-<id>). */
function piece(key: string): Valeurs | null {
  const id = Number(key.slice(3))
  return (lists.value.pieces.find((p) => p.id === id) as unknown as Valeurs) ?? null
}

/** Add a requirement under an event row (its key is ev-<event>). */
function ajouterPiece(key: string) {
  ouvrirPiece('ajouter', null, { evenement: key.slice(3), obligatoire: true })
}
</script>

<template>
  <div class="toolbar" role="search" aria-label="Filtrer les pièces justificatives">
    <label class="field">
      <span class="sy-muted">Pièces au</span>
      <DatePicker
        v-model="state.date"
        :manual-input="false"
        date-format="dd/mm/yy"
        show-icon
        icon-display="input"
        aria-label="Pièces au"
        data-test="pieces-date"
      />
    </label>
    <IconField class="search">
      <InputIcon class="pi pi-search" />
      <InputText
        v-model="state.texte"
        placeholder="Pièce ou événement"
        aria-label="Rechercher une pièce ou un événement"
        data-test="pieces-search"
      />
    </IconField>
    <div class="actions">
      <Button
        type="button"
        label="Tout déplier"
        icon="pi pi-angle-double-down"
        text
        severity="secondary"
        data-test="pieces-expand-all"
        @click="expandAll"
      />
      <Button
        type="button"
        label="Tout replier"
        icon="pi pi-angle-double-up"
        text
        severity="secondary"
        data-test="pieces-collapse-all"
        @click="collapseAll"
      />
    </div>
  </div>

  <Message v-if="error" severity="error" :closable="false" data-test="pieces-error">
    Les pièces justificatives n'ont pas pu être chargées : {{ error }}
  </Message>

  <TreeTable
    v-model:expanded-keys="expanded"
    :value="visible"
    :loading="loading"
    class="tree"
    data-test="pieces"
  >
    <template #empty>
      <p class="sy-muted empty">
        {{
          filtering
            ? 'Aucune pièce ni aucun événement ne correspond à cette recherche.'
            : 'Aucune pièce à afficher.'
        }}
      </p>
    </template>
    <Column
      field="nom"
      header="Événement / pièce"
      expander
      header-class="name-col"
      body-class="name-col"
    >
      <template #body="{ node }">
        <span :class="{ name: node.data.niveau === 'evenement' }">{{ node.data.nom }}</span>
      </template>
    </Column>
    <Column header="Code">
      <template #body="{ node }">
        <span class="sy-num nowrap">{{ node.data.code }}</span>
      </template>
    </Column>
    <Column header="Exigence">
      <template #body="{ node }">
        <span v-if="node.data.niveau === 'evenement'" class="sy-muted nowrap">
          {{ nombreLibelle(node.data.nombre) }}
        </span>
        <Tag
          v-else
          :value="node.data.obligatoire ? 'Obligatoire' : 'Facultative'"
          :severity="node.data.obligatoire ? 'primary' : 'secondary'"
        />
      </template>
    </Column>
    <Column header="Ouverture">
      <template #body="{ node }">
        <span v-if="node.data.niveau === 'piece'" class="sy-num nowrap">
          {{ formatDate(node.data.date_ouverture) }}
        </span>
      </template>
    </Column>
    <Column header="Fermeture">
      <template #body="{ node }">
        <span v-if="node.data.niveau === 'piece'" class="sy-num nowrap">
          {{ formatDate(node.data.date_fermeture) }}
        </span>
      </template>
    </Column>
    <Column v-if="droitsPieces.ajouter || droitsPieces.modifier" class="actions-col">
      <template #body="{ node }">
        <Button
          v-if="node.data.niveau === 'evenement' && droitsPieces.ajouter"
          icon="pi pi-plus"
          text
          rounded
          size="small"
          severity="secondary"
          :aria-label="`Ajouter une pièce exigée pour ${node.data.nom}`"
          data-test="ajouter-sous"
          @click="ajouterPiece(node.key)"
        />
        <ActionsLigne
          v-else-if="node.data.niveau === 'piece'"
          :ferme="node.data.date_fermeture !== null"
          :peut-modifier="droitsPieces.modifier"
          :peut-remplacer="droitsPieces.remplacer"
          :libelle="node.data.code"
          @action="(m) => ouvrirPiece(m, piece(node.key))"
        />
      </template>
    </Column>
  </TreeTable>

  <div class="section">
    <h3 class="section-title">Types de pièce</h3>
    <Button
      v-if="droitsTypes.ajouter"
      label="Ajouter"
      icon="pi pi-plus"
      size="small"
      data-test="types-document-ajouter"
      @click="ouvrirType('ajouter')"
    />
  </div>
  <DataTable
    :value="error ? [] : lists.types"
    :loading="loading"
    data-key="id"
    class="types"
    data-test="types-document"
  >
    <template #empty>
      <p class="sy-muted empty">Aucun type de pièce à cette date.</p>
    </template>
    <Column header="Code">
      <template #body="{ data }">
        <span class="sy-num nowrap">{{ data.code }}</span>
      </template>
    </Column>
    <Column header="Nom" field="nom" />
    <Column header="Ouverture">
      <template #body="{ data }">
        <span class="sy-num nowrap">{{ formatDate(data.date_ouverture) }}</span>
      </template>
    </Column>
    <Column header="Fermeture">
      <template #body="{ data }">
        <span class="sy-num nowrap">{{ formatDate(data.date_fermeture) }}</span>
      </template>
    </Column>
    <Column v-if="droitsTypes.modifier" class="actions-col">
      <template #body="{ data }">
        <ActionsLigne
          :ferme="data.date_fermeture !== null"
          :peut-modifier="droitsTypes.modifier"
          :peut-remplacer="droitsTypes.remplacer"
          :libelle="data.code"
          @action="(m) => ouvrirType(m, data)"
        />
      </template>
    </Column>
  </DataTable>

  <EditionDialog
    v-for="d in dialogues"
    :key="d.cle"
    v-model:visible="d.visible.value"
    :edition="d.edition"
    :mode="d.mode.value"
    :ligne="d.ligne.value"
    :initial="d.initial.value"
    @enregistre="d.enregistre"
  />
</template>

<style scoped>
.actions-col {
  width: 3rem;
}

.section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sy-space-2);
  margin: var(--sy-space-5, 1.5rem) 0 var(--sy-space-2);
}

.section-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.types :deep(.p-datatable-table-container) {
  overflow-x: auto;
}

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

  /* The buttons wrap rather than stick out of the card on a phone. */
  .actions {
    flex-wrap: wrap;
    margin-left: 0;
    white-space: normal;
  }
}
</style>
