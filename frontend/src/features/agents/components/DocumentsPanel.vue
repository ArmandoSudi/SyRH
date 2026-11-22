<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { useToast } from 'primevue/usetoast'

import { documentUrl, listDocuments, type Document } from '@/features/agents/api/documents'
import AddDocumentDialog from '@/features/agents/components/AddDocumentDialog.vue'
import RetireDocumentDialog from '@/features/agents/components/RetireDocumentDialog.vue'
import {
  formatDateTime,
  formatLibelle,
  formatTaille,
  typesDeposables,
} from '@/features/agents/components/documents'
import { useAuthStore } from '@/features/auth/stores/auth'
import {
  fetchParametres,
  fetchTypesDocument,
  type TypeDocument,
} from '@/features/referentiels/api/referentiels'
import { formatDate, localDate } from '@/shared/utils/dates'

/**
 * An agent's scanned documents (document storage D21, D22): list, open, download, add
 * and retire. Mounted by the "Pièces des agents" page, then by the agent summary page of
 * roadmap 2.10. Buttons follow the user's rights; the API checks them on its own.
 */
const props = defineProps<{ agentId: number }>()

const auth = useAuthStore()
const toast = useToast()
const peutAjouter = computed(() => auth.can('agents.add_document'))
const peutRetirer = computed(() => auth.can('agents.change_document'))

const documents = ref<Document[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const retires = ref(false)

const types = ref<TypeDocument[]>([])
const maxMo = ref<number | null>(null)
const ajout = ref(false)
const retrait = ref(false)
const cible = ref<Document | null>(null)

let latest = 0

async function load() {
  const call = ++latest
  loading.value = true
  error.value = null
  try {
    const rows = await listDocuments(props.agentId, retires.value)
    if (call !== latest) return // a newer request superseded this one
    documents.value = rows
  } catch (e) {
    if (call !== latest) return
    error.value = e instanceof Error ? e.message : String(e)
    documents.value = []
  } finally {
    if (call === latest) loading.value = false
  }
}

/** What the add dialog needs: the types open today and the size limit (D12, D22). */
async function loadReferences() {
  const today = localDate(new Date())
  const [typeRows, parametres] = await Promise.allSettled([
    fetchTypesDocument({ date: today }),
    fetchParametres({ date: today }),
  ])
  if (typeRows.status === 'fulfilled') {
    types.value = typesDeposables(typeRows.value, auth.user?.groups ?? [])
  }
  if (parametres.status === 'fulfilled') {
    maxMo.value = parametres.value.find((p) => p.cle === 'taille_max_piece')?.valeur ?? null
  }
}

watch(
  () => [props.agentId, retires.value],
  () => void load(),
)
onMounted(() => {
  void load()
  if (peutAjouter.value) void loadReferences()
})

function ouvrirRetrait(document: Document) {
  cible.value = document
  retrait.value = true
}

function depose(document: Document) {
  toast.add({
    severity: 'success',
    summary: 'Pièce déposée',
    detail: document.nom_original,
    life: 3000,
  })
  void load()
}

function retire(document: Document) {
  toast.add({
    severity: 'success',
    summary: 'Pièce retirée',
    detail: document.nom_original,
    life: 3000,
  })
  void load()
}
</script>

<template>
  <section class="panel" aria-label="Pièces justificatives" data-test="documents-panel">
    <div class="toolbar">
      <label class="toggle">
        <ToggleSwitch v-model="retires" data-test="documents-retires" />
        <span>Afficher les pièces retirées</span>
      </label>
      <Button
        v-if="peutAjouter"
        label="Ajouter une pièce"
        icon="pi pi-plus"
        class="ajouter"
        data-test="documents-ajouter"
        @click="ajout = true"
      />
    </div>

    <Message v-if="error" severity="error" :closable="false" data-test="documents-error">
      Les pièces n'ont pas pu être chargées : {{ error }}
    </Message>

    <DataTable
      :value="documents"
      :loading="loading"
      data-key="id"
      class="documents"
      :row-class="(row: Document) => (row.retire ? 'retiree' : '')"
      data-test="documents"
    >
      <template #empty>
        <p class="sy-muted empty">
          {{ retires ? 'Aucune pièce pour cet agent.' : 'Aucune pièce en cours pour cet agent.' }}
        </p>
      </template>
      <Column header="Type">
        <template #body="{ data }">
          <span class="type">
            <i
              v-if="data.confidentiel"
              class="pi pi-lock"
              title="Pièce confidentielle"
              aria-label="Pièce confidentielle"
            />
            {{ data.type_document_nom }}
          </span>
          <span class="sy-muted sy-num code">{{ data.type_document_code }}</span>
        </template>
      </Column>
      <Column header="Fichier">
        <template #body="{ data }">
          <span class="nom">{{ data.nom_original }}</span>
          <span class="sy-muted">{{ formatLibelle(data.type_mime) }}</span>
          <Tag
            v-if="data.retire"
            value="Retirée"
            severity="secondary"
            :title="data.motif_retrait"
            class="tag"
          />
          <p v-if="data.retire" class="sy-muted motif" data-test="documents-motif">
            {{ data.motif_retrait }} — {{ data.retire_par_nom ?? 'système' }},
            {{ formatDateTime(data.date_retrait) }}
          </p>
        </template>
      </Column>
      <Column header="Date de la pièce">
        <template #body="{ data }">
          <span class="sy-num nowrap">{{ formatDate(data.date_document) }}</span>
        </template>
      </Column>
      <Column header="Taille">
        <template #body="{ data }">
          <span class="sy-num nowrap">{{ formatTaille(data.taille) }}</span>
        </template>
      </Column>
      <Column header="Déposée">
        <template #body="{ data }">
          <span class="sy-num nowrap">{{ formatDateTime(data.date_creation) }}</span>
          <span class="sy-muted par">{{ data.cree_par_nom ?? 'système' }}</span>
        </template>
      </Column>
      <Column class="actions-col">
        <template #body="{ data }">
          <div class="actions">
            <a
              :href="documentUrl(agentId, data.id)"
              target="_blank"
              rel="noopener"
              class="p-button p-button-text p-button-secondary p-button-sm p-button-icon-only"
              :title="`Ouvrir ${data.nom_original}`"
              :aria-label="`Ouvrir ${data.nom_original}`"
              data-test="documents-ouvrir"
            >
              <i class="pi pi-external-link" />
            </a>
            <a
              :href="documentUrl(agentId, data.id, true)"
              class="p-button p-button-text p-button-secondary p-button-sm p-button-icon-only"
              :title="`Télécharger ${data.nom_original}`"
              :aria-label="`Télécharger ${data.nom_original}`"
              data-test="documents-telecharger"
            >
              <i class="pi pi-download" />
            </a>
            <Button
              v-if="peutRetirer && !data.retire"
              icon="pi pi-eye-slash"
              text
              size="small"
              severity="danger"
              :title="`Retirer ${data.nom_original}`"
              :aria-label="`Retirer ${data.nom_original}`"
              data-test="documents-retirer"
              @click="ouvrirRetrait(data)"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <AddDocumentDialog
      v-if="peutAjouter"
      v-model:visible="ajout"
      :agent-id="agentId"
      :types="types"
      :max-mo="maxMo"
      @depose="depose"
    />
    <RetireDocumentDialog
      v-if="peutRetirer"
      v-model:visible="retrait"
      :agent-id="agentId"
      :document="cible"
      @retire="retire"
    />
  </section>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sy-space-3);
  margin-bottom: var(--sy-space-4);
}

.toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--sy-space-2);
  font-size: 0.9rem;
}

.ajouter {
  margin-left: auto;
}

.type,
.nom {
  display: block;
}

.type .pi-lock {
  color: var(--sy-warning);
  margin-right: var(--sy-space-1);
}

.code,
.par {
  display: block;
  font-size: 0.8rem;
}

.tag {
  margin-left: var(--sy-space-2);
}

.motif {
  margin: var(--sy-space-1) 0 0;
  font-size: 0.8rem;
}

.actions {
  display: flex;
  gap: var(--sy-space-1);
  justify-content: flex-end;
}

.actions-col {
  width: 8rem;
}

.documents :deep(.retiree) {
  opacity: 0.6;
}

/* Narrow screens: the table scrolls inside the card instead of being cut. */
.documents :deep(.p-datatable-table-container) {
  overflow-x: auto;
}

.nowrap {
  white-space: nowrap;
}

.empty {
  margin: 0;
}
</style>
