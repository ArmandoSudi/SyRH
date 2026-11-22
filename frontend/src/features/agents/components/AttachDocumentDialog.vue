<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import RadioButton from 'primevue/radiobutton'

import { listDocuments, type Document } from '@/features/agents/api/documents'
import {
  attachDocument,
  type EvenementEtat,
  type PieceExigee,
} from '@/features/agents/api/evenements'
import { formatDate } from '@/shared/utils/dates'
import { ApiError } from '@/shared/utils/http'

/**
 * "Joindre une pièce" (documents on events D24): pick one of the agent's documents for
 * an event, those of the required type first, or upload a new one. Documents already
 * attached to the event are left out.
 */
const props = defineProps<{
  agentId: number
  evenement: EvenementEtat | null
  /** The required piece being completed; null to attach any document. */
  piece: PieceExigee | null
  /** Whether the user may upload a new document. */
  peutDeposer: boolean
}>()

const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{
  joint: [evenement: EvenementEtat]
  deposer: [code: string | null]
}>()

const documents = ref<Document[]>([])
const choisi = ref<number | null>(null)
const loading = ref(false)
const sending = ref(false)
const error = ref<string | null>(null)

const dejaJoints = computed(() => {
  const ids = new Set<number>()
  for (const piece of props.evenement?.pieces ?? []) piece.documents.forEach((d) => ids.add(d.id))
  props.evenement?.autres.forEach((d) => ids.add(d.id))
  return ids
})
const disponibles = computed(() => documents.value.filter((d) => !dejaJoints.value.has(d.id)))
const duType = computed(() =>
  props.piece ? disponibles.value.filter((d) => d.type_document_code === props.piece!.code) : [],
)
const autres = computed(() =>
  disponibles.value.filter((d) => !duType.value.some((m) => m.id === d.id)),
)
const titre = computed(() =>
  props.piece ? `Joindre : ${props.piece.nom}` : 'Joindre une pièce à l’événement',
)

watch(visible, async (open) => {
  if (!open) return
  choisi.value = null
  error.value = null
  loading.value = true
  try {
    documents.value = await listDocuments(props.agentId)
    choisi.value = duType.value[0]?.id ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

async function joindre() {
  if (!props.evenement || choisi.value === null) {
    error.value = 'Choisissez la pièce à joindre.'
    return
  }
  sending.value = true
  error.value = null
  try {
    const etat = await attachDocument(props.agentId, props.evenement, choisi.value)
    visible.value = false
    emit('joint', etat)
  } catch (e) {
    if (e instanceof ApiError && e.fieldErrors.document) {
      error.value = e.fieldErrors.document[0] ?? e.message
    } else {
      error.value = e instanceof Error ? e.message : String(e)
    }
  } finally {
    sending.value = false
  }
}

function deposer() {
  visible.value = false
  emit('deposer', props.piece?.code ?? null)
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="titre"
    :style="{ width: '34rem' }"
    data-test="joindre-dialog"
  >
    <p v-if="evenement" class="sy-muted intro">
      {{ evenement.evenement_libelle }} du {{ formatDate(evenement.date) }} —
      {{ evenement.libelle }}
    </p>
    <p v-if="loading" class="sy-muted">Chargement des pièces…</p>
    <template v-else>
      <fieldset v-if="duType.length > 0" class="group" data-test="joindre-du-type">
        <legend>Pièces de ce type</legend>
        <label v-for="d in duType" :key="d.id" class="choice">
          <RadioButton v-model="choisi" :value="d.id" :input-id="`doc-${d.id}`" />
          <span>{{ d.nom_original }}</span>
          <span class="sy-muted">{{ formatDate(d.date_document) }}</span>
        </label>
      </fieldset>
      <fieldset v-if="autres.length > 0" class="group" data-test="joindre-autres">
        <legend>{{ piece ? 'Autres pièces du dossier' : 'Pièces du dossier' }}</legend>
        <label v-for="d in autres" :key="d.id" class="choice">
          <RadioButton v-model="choisi" :value="d.id" :input-id="`doc-${d.id}`" />
          <span>{{ d.nom_original }}</span>
          <span class="sy-muted">{{ d.type_document_nom }}</span>
        </label>
      </fieldset>
      <p v-if="disponibles.length === 0" class="sy-muted" data-test="joindre-vide">
        Aucune autre pièce dans le dossier de l'agent.
      </p>
    </template>
    <Message v-if="error" severity="error" :closable="false" data-test="joindre-erreur">
      {{ error }}
    </Message>

    <template #footer>
      <Button
        v-if="peutDeposer"
        label="Déposer une nouvelle pièce"
        icon="pi pi-upload"
        severity="secondary"
        text
        class="deposer"
        data-test="joindre-deposer"
        @click="deposer"
      />
      <Button label="Annuler" severity="secondary" text @click="visible = false" />
      <Button
        label="Joindre"
        icon="pi pi-link"
        :loading="sending"
        :disabled="choisi === null"
        data-test="joindre-confirmer"
        @click="joindre"
      />
    </template>
  </Dialog>
</template>

<style scoped>
.intro {
  margin-top: 0;
}

.group {
  border: none;
  margin: 0 0 var(--sy-space-3);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-2);
}

legend {
  font-weight: 600;
  margin-bottom: var(--sy-space-2);
}

.choice {
  display: flex;
  align-items: center;
  gap: var(--sy-space-2);
}

.deposer {
  margin-right: auto;
}
</style>
