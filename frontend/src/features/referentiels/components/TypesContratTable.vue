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

import { fetchTypesContrat, type TypeContrat } from '@/features/referentiels/api/referentiels'
import { filterByCodeAndName } from '@/features/referentiels/components/lists'
import ActionsLigne from '@/features/referentiels/components/edition/ActionsLigne.vue'
import EditionDialog from '@/features/referentiels/components/edition/EditionDialog.vue'
import { useEdition } from '@/features/referentiels/components/edition/useEdition'
import { useReferentielsStore } from '@/features/referentiels/stores/referentiels'
import { formatDate, localDate } from '@/shared/utils/dates'

// Read-only: contract types are edited in Django admin until roadmap 1.9 (contract types D20, D21).
const store = useReferentielsStore()
const state = store.typesContrat

const types = ref<TypeContrat[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

let latest = 0

async function load() {
  const call = ++latest
  loading.value = true
  error.value = null
  try {
    const rows = await fetchTypesContrat({ date: localDate(state.date) })
    if (call !== latest) return // a newer request superseded this one
    types.value = rows
  } catch (e) {
    if (call !== latest) return
    error.value = e instanceof Error ? e.message : String(e)
    types.value = []
  } finally {
    if (call === latest) loading.value = false
  }
}

const visible = computed(() => filterByCodeAndName(types.value, state.texte))
function ouiNon(value: boolean): string {
  return value ? 'Oui' : 'Non'
}

const filtering = computed(() => state.texte.trim() !== '')

watch(
  () => state.date,
  () => void load(),
)
onMounted(load)

// Editors add, correct, replace and close rows here (reference data screens D10 to D13).
const {
  edition,
  droits,
  visible: dialogue,
  mode,
  ligne,
  initial,
  ouvrir,
  enregistre,
} = useEdition('types-contrat', load)
</script>

<template>
  <div class="toolbar" role="search" aria-label="Filtrer les types de contrat">
    <label class="field">
      <span class="sy-muted">Types au</span>
      <DatePicker
        v-model="state.date"
        :manual-input="false"
        date-format="dd/mm/yy"
        show-icon
        icon-display="input"
        aria-label="Types au"
        data-test="types-contrat-date"
      />
    </label>
    <IconField class="search">
      <InputIcon class="pi pi-search" />
      <InputText
        v-model="state.texte"
        placeholder="Code ou nom"
        aria-label="Rechercher un type de contrat"
        data-test="types-contrat-search"
      />
    </IconField>
    <Button
      v-if="droits.ajouter"
      label="Ajouter"
      icon="pi pi-plus"
      class="ajouter"
      data-test="types-contrat-ajouter"
      @click="ouvrir('ajouter')"
    />
  </div>

  <Message v-if="error" severity="error" :closable="false" data-test="types-contrat-error">
    Les types de contrat n'ont pas pu être chargés : {{ error }}
  </Message>

  <DataTable
    :value="visible"
    :loading="loading"
    data-key="id"
    class="types"
    data-test="types-contrat"
  >
    <template #empty>
      <p class="sy-muted empty">
        {{
          filtering
            ? 'Aucun type ne correspond à cette recherche.'
            : 'Aucun type de contrat à cette date.'
        }}
      </p>
    </template>
    <Column header="Code">
      <template #body="{ data }">
        <span class="sy-num nowrap">{{ data.code }}</span>
      </template>
    </Column>
    <Column header="Nom" field="nom" />
    <Column header="Durée déterminée">
      <template #body="{ data }">{{ ouiNon(data.duree_determinee) }}</template>
    </Column>
    <Column header="Période d'essai">
      <template #body="{ data }">{{ ouiNon(data.periode_essai) }}</template>
    </Column>
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
    <Column v-if="droits.modifier" class="actions-col">
      <template #body="{ data }">
        <ActionsLigne
          :ferme="data.date_fermeture !== null"
          :peut-modifier="droits.modifier"
          :peut-remplacer="droits.remplacer"
          :libelle="data.code"
          @action="(m) => ouvrir(m, data)"
        />
      </template>
    </Column>
  </DataTable>

  <EditionDialog
    v-model:visible="dialogue"
    :edition="edition"
    :mode="mode"
    :ligne="ligne"
    :initial="initial"
    @enregistre="enregistre"
  />
</template>

<style scoped>
.ajouter {
  margin-left: auto;
}

.actions-col {
  width: 3rem;
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

/* Narrow screens: the table scrolls inside the card instead of being cut. */
.types :deep(.p-datatable-table-container) {
  overflow-x: auto;
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
}
</style>
