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

import {
  fetchMotifsSortie,
  fetchTypesSuspension,
  type MotifSortie,
  type PeriodeOptions,
  type TypeSuspension,
} from '@/features/referentiels/api/referentiels'
import { filterByCodeAndName } from '@/features/referentiels/components/lists'
import { dureeLibelle, renouvellementsLibelle } from '@/features/referentiels/components/sorties'
import ActionsLigne from '@/features/referentiels/components/edition/ActionsLigne.vue'
import EditionDialog from '@/features/referentiels/components/edition/EditionDialog.vue'
import { useEdition } from '@/features/referentiels/components/edition/useEdition'
import { useReferentielsStore } from '@/features/referentiels/stores/referentiels'
import { formatDate, localDate } from '@/shared/utils/dates'

// Read-only: exit reasons and suspension types are edited in Django admin until roadmap 1.9
// (exit reasons D21, D22). Both lists share the tab's date and filter.
const store = useReferentielsStore()
const state = store.sorties

/** One list of the tab: its rows, loading and error, loaded on its own. */
function liste<T>(fetch: (options: PeriodeOptions) => Promise<T[]>) {
  const rows = ref<T[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  let latest = 0

  async function load() {
    const call = ++latest
    loading.value = true
    error.value = null
    try {
      const result = await fetch({ date: localDate(state.date) })
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

  return { rows, loading, error, load }
}

const {
  rows: motifsRows,
  loading: motifsLoading,
  error: motifsError,
  load: loadMotifs,
} = liste<MotifSortie>(fetchMotifsSortie)
const {
  rows: suspensionsRows,
  loading: suspensionsLoading,
  error: suspensionsError,
  load: loadSuspensions,
} = liste<TypeSuspension>(fetchTypesSuspension)

const motifsVisibles = computed(() => filterByCodeAndName(motifsRows.value, state.texte))
const suspensionsVisibles = computed(() => filterByCodeAndName(suspensionsRows.value, state.texte))
const filtering = computed(() => state.texte.trim() !== '')

function load() {
  void loadMotifs()
  void loadSuspensions()
}

watch(() => state.date, load)
onMounted(load)

// Each table has its own editors and dialog (reference data screens D10 to D13).
const motifs = useEdition('motifs-sortie', loadMotifs)
const suspensions = useEdition('types-suspension', loadSuspensions)
const {
  droits: droitsMotifs,
  visible: dialogueMotifs,
  mode: modeMotifs,
  ligne: ligneMotifs,
  ouvrir: ouvrirMotifs,
} = motifs
const {
  droits: droitsSuspensions,
  visible: dialogueSuspensions,
  mode: modeSuspensions,
  ligne: ligneSuspensions,
  ouvrir: ouvrirSuspensions,
} = suspensions
</script>

<template>
  <div class="toolbar" role="search" aria-label="Filtrer les motifs et les suspensions">
    <label class="field">
      <span class="sy-muted">Au</span>
      <DatePicker
        v-model="state.date"
        :manual-input="false"
        date-format="dd/mm/yy"
        show-icon
        icon-display="input"
        aria-label="Motifs et suspensions au"
        data-test="sorties-date"
      />
    </label>
    <IconField class="search">
      <InputIcon class="pi pi-search" />
      <InputText
        v-model="state.texte"
        placeholder="Code, nom ou pièce"
        aria-label="Rechercher un motif ou une suspension"
        data-test="sorties-search"
      />
    </IconField>
  </div>

  <div class="section">
    <h3 class="section-title">Motifs de sortie</h3>
    <Button
      v-if="droitsMotifs.ajouter"
      label="Ajouter"
      icon="pi pi-plus"
      size="small"
      data-test="motifs-ajouter"
      @click="ouvrirMotifs('ajouter')"
    />
  </div>
  <Message v-if="motifsError" severity="error" :closable="false" data-test="motifs-error">
    Les motifs de sortie n'ont pas pu être chargés : {{ motifsError }}
  </Message>
  <DataTable
    :value="motifsVisibles"
    :loading="motifsLoading"
    data-key="id"
    class="liste"
    data-test="motifs"
  >
    <template #empty>
      <p class="sy-muted empty">
        {{
          filtering
            ? 'Aucun motif ne correspond à cette recherche.'
            : 'Aucun motif de sortie à cette date.'
        }}
      </p>
    </template>
    <Column header="Code">
      <template #body="{ data }">
        <span class="sy-num nowrap">{{ data.code }}</span>
      </template>
    </Column>
    <Column header="Nom">
      <template #body="{ data }">
        <span class="nom">
          {{ data.nom }}
          <Tag v-if="data.retraite" value="Retraite" severity="info" />
          <Tag v-if="data.deces" value="Décès" severity="secondary" />
        </span>
      </template>
    </Column>
    <Column header="Pièce exigée" field="type_document_libelle" />
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
    <Column v-if="droitsMotifs.modifier" class="actions-col">
      <template #body="{ data }">
        <ActionsLigne
          :ferme="data.date_fermeture !== null"
          :peut-modifier="droitsMotifs.modifier"
          :peut-remplacer="droitsMotifs.remplacer"
          :libelle="data.code"
          @action="(m) => ouvrirMotifs(m, data)"
        />
      </template>
    </Column>
  </DataTable>

  <div class="section">
    <h3 class="section-title">Positions de suspension</h3>
    <Button
      v-if="droitsSuspensions.ajouter"
      label="Ajouter"
      icon="pi pi-plus"
      size="small"
      data-test="suspensions-ajouter"
      @click="ouvrirSuspensions('ajouter')"
    />
  </div>
  <Message v-if="suspensionsError" severity="error" :closable="false" data-test="suspensions-error">
    Les positions de suspension n'ont pas pu être chargées : {{ suspensionsError }}
  </Message>
  <DataTable
    :value="suspensionsVisibles"
    :loading="suspensionsLoading"
    data-key="id"
    class="liste"
    data-test="suspensions"
  >
    <template #empty>
      <p class="sy-muted empty">
        {{
          filtering
            ? 'Aucune position ne correspond à cette recherche.'
            : 'Aucune position de suspension à cette date.'
        }}
      </p>
    </template>
    <Column header="Code">
      <template #body="{ data }">
        <span class="sy-num nowrap">{{ data.code }}</span>
      </template>
    </Column>
    <Column header="Nom" field="nom" />
    <Column header="Pièce exigée" field="type_document_libelle" />
    <Column header="Compte dans l'ancienneté">
      <template #body="{ data }">
        <Tag
          :value="data.compte_anciennete ? 'Oui' : 'Non'"
          :severity="data.compte_anciennete ? 'success' : 'secondary'"
        />
      </template>
    </Column>
    <Column header="Durée maximale">
      <template #body="{ data }">
        <span class="nowrap">{{ dureeLibelle(data.duree_max_mois) }}</span>
      </template>
    </Column>
    <Column header="Renouvellements">
      <template #body="{ data }">{{ renouvellementsLibelle(data.renouvellements_max) }}</template>
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
    <Column v-if="droitsSuspensions.modifier" class="actions-col">
      <template #body="{ data }">
        <ActionsLigne
          :ferme="data.date_fermeture !== null"
          :peut-modifier="droitsSuspensions.modifier"
          :peut-remplacer="droitsSuspensions.remplacer"
          :libelle="data.code"
          @action="(m) => ouvrirSuspensions(m, data)"
        />
      </template>
    </Column>
  </DataTable>

  <EditionDialog
    v-model:visible="dialogueMotifs"
    :edition="motifs.edition"
    :mode="modeMotifs"
    :ligne="ligneMotifs"
    @enregistre="motifs.enregistre"
  />
  <EditionDialog
    v-model:visible="dialogueSuspensions"
    :edition="suspensions.edition"
    :mode="modeSuspensions"
    :ligne="ligneSuspensions"
    @enregistre="suspensions.enregistre"
  />
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

.section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sy-space-2);
  margin: var(--sy-space-4) 0 var(--sy-space-2);
}

.section .section-title {
  margin: 0;
}

.actions-col {
  width: 3rem;
}

.section-title {
  margin: var(--sy-space-4) 0 var(--sy-space-2);
  font-size: 1rem;
  font-weight: 600;
}

.nom {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sy-space-2);
}

/* Narrow screens: each table scrolls inside the card instead of being cut. */
.liste :deep(.p-datatable-table-container) {
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
