<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'

import { fetchSites, type Site } from '@/features/referentiels/api/referentiels'
import ActionsLigne from '@/features/referentiels/components/edition/ActionsLigne.vue'
import EditionDialog from '@/features/referentiels/components/edition/EditionDialog.vue'
import { useEdition } from '@/features/referentiels/components/edition/useEdition'
import { useReferentielsStore } from '@/features/referentiels/stores/referentiels'
import { formatDate, localDate } from '@/shared/utils/dates'

const store = useReferentielsStore()

const sites = ref<Site[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

let latest = 0

async function load() {
  const call = ++latest
  loading.value = true
  error.value = null
  try {
    const rows = await fetchSites({ toutes: store.sitesFermes })
    if (call !== latest) return
    sites.value = rows
  } catch (e) {
    if (call !== latest) return
    error.value = e instanceof Error ? e.message : String(e)
    sites.value = []
  } finally {
    if (call === latest) loading.value = false
  }
}

/** The closing date is the first day closed. */
function statut(site: Site): string {
  if (!site.date_fermeture) return 'Ouvert'
  const closing = formatDate(site.date_fermeture)
  return site.date_fermeture > localDate(new Date()) ? `Ferme le ${closing}` : `Fermé le ${closing}`
}

watch(
  () => store.sitesFermes,
  () => void load(),
)
onMounted(load)

// Editors add, correct and close sites; a site has no successor (tree reference D1, D12).
const {
  edition,
  droits,
  visible: dialogue,
  mode,
  ligne,
  initial,
  ouvrir,
  enregistre,
} = useEdition('sites', load)
</script>

<template>
  <div class="toolbar">
    <label class="toggle">
      <ToggleSwitch v-model="store.sitesFermes" data-test="closed-sites" />
      <span>Afficher les sites fermés</span>
    </label>
    <Button
      v-if="droits.ajouter"
      label="Ajouter"
      icon="pi pi-plus"
      class="ajouter"
      data-test="sites-ajouter"
      @click="ouvrir('ajouter')"
    />
  </div>

  <Message v-if="error" severity="error" :closable="false" data-test="sites-error">
    Les sites n'ont pas pu être chargés : {{ error }}
  </Message>

  <DataTable :value="sites" :loading="loading" data-key="id" class="sites" data-test="sites">
    <template #empty>
      <p class="sy-muted empty">Aucun site.</p>
    </template>
    <Column header="Code">
      <template #body="{ data }">
        <span class="sy-num">{{ data.code }}</span>
      </template>
    </Column>
    <Column header="Nom" field="nom" />
    <Column header="Ville" field="ville" />
    <Column header="Siège">
      <template #body="{ data }">
        <Tag v-if="data.siege" value="Siège" severity="primary" />
      </template>
    </Column>
    <Column header="Statut">
      <template #body="{ data }">
        <span class="nowrap">{{ statut(data) }}</span>
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
  margin-bottom: var(--sy-space-4);
}

.toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--sy-space-2);
  cursor: pointer;
}

.sites :deep(.p-datatable-table-container) {
  overflow-x: auto;
}

.nowrap {
  white-space: nowrap;
}

.empty {
  padding: var(--sy-space-4) 0;
  text-align: center;
}
</style>
