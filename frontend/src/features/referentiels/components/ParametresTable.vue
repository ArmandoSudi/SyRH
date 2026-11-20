<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Message from 'primevue/message'

import { fetchParametres, type Parametre } from '@/features/referentiels/api/referentiels'
import { buildParametres, valeurLibelle } from '@/features/referentiels/components/parametres'
import { useReferentielsStore } from '@/features/referentiels/stores/referentiels'
import { formatDate, localDate } from '@/shared/utils/dates'

// Read-only: parameters are edited in Django admin until roadmap 1.9 (general parameters
// D19, D20). Every key is listed, with "Non renseigné" when it has no value at the date.
const store = useReferentielsStore()
const state = store.parametres

const rows = ref<Parametre[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

let latest = 0

async function load() {
  const call = ++latest
  loading.value = true
  error.value = null
  try {
    const result = await fetchParametres({ date: localDate(state.date) })
    if (call !== latest) return // a newer request superseded this one
    rows.value = result
  } catch (e) {
    if (call !== latest) return
    error.value = e instanceof Error ? e.message : String(e)
    rows.value = []
  } finally {
    if (call === latest) loading.value = false
  }
}

// Nothing to list when the values could not be loaded: "Non renseigné" would mislead.
const lignes = computed(() => (error.value ? [] : buildParametres(rows.value)))

watch(
  () => state.date,
  () => void load(),
)
onMounted(load)
</script>

<template>
  <div class="toolbar" role="search" aria-label="Choisir la date des paramètres">
    <label class="field">
      <span class="sy-muted">Paramètres au</span>
      <DatePicker
        v-model="state.date"
        :manual-input="false"
        date-format="dd/mm/yy"
        show-icon
        icon-display="input"
        aria-label="Paramètres au"
        data-test="parametres-date"
      />
    </label>
  </div>

  <Message v-if="error" severity="error" :closable="false" data-test="parametres-error">
    Les paramètres n'ont pas pu être chargés : {{ error }}
  </Message>

  <DataTable
    :value="lignes"
    :loading="loading"
    data-key="cle"
    class="parametres"
    data-test="parametres"
  >
    <template #empty>
      <p class="sy-muted empty">Aucun paramètre à afficher.</p>
    </template>
    <Column header="Paramètre" field="libelle" />
    <Column header="Valeur">
      <template #body="{ data }">
        <span :class="data.parametre ? 'sy-num nowrap' : 'sy-muted'">
          {{ valeurLibelle(data) }}
        </span>
      </template>
    </Column>
    <Column header="Ouverture">
      <template #body="{ data }">
        <span class="sy-num nowrap">{{
          data.parametre ? formatDate(data.parametre.date_ouverture) : ''
        }}</span>
      </template>
    </Column>
    <Column header="Fermeture">
      <template #body="{ data }">
        <span class="sy-num nowrap">{{
          data.parametre ? formatDate(data.parametre.date_fermeture) : ''
        }}</span>
      </template>
    </Column>
  </DataTable>
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

/* Narrow screens: the table scrolls inside the card instead of being cut. */
.parametres :deep(.p-datatable-table-container) {
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
  .field {
    flex: 1 1 100%;
    min-width: 0;
  }
}
</style>
