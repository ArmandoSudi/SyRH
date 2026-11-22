<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'

import { retireDocument, type Document } from '@/features/agents/api/documents'
import { ApiError, type FieldErrors } from '@/shared/utils/http'

/**
 * "Retirer la pièce" (document storage D17): a wrong upload leaves the list with its
 * reason; the file is kept and still opens. It cannot be undone.
 */
const props = defineProps<{ agentId: number; document: Document | null }>()

const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ retire: [document: Document] }>()

const MOTIF_MIN = 10

const motif = ref('')
const errors = ref<FieldErrors>({})
const general = ref<string | null>(null)
const sending = ref(false)

watch(visible, (open) => {
  if (!open) return
  motif.value = ''
  errors.value = {}
  general.value = null
})

async function retirer() {
  if (!props.document) return
  if (motif.value.trim().length < MOTIF_MIN) {
    errors.value = { motif: ['Indiquez le motif du retrait, en 10 caractères au moins.'] }
    return
  }
  sending.value = true
  errors.value = {}
  general.value = null
  try {
    const document = await retireDocument(props.agentId, props.document.id, motif.value.trim())
    visible.value = false
    emit('retire', document)
  } catch (e) {
    if (e instanceof ApiError && Object.keys(e.fieldErrors).length > 0) {
      errors.value = e.fieldErrors
    } else {
      general.value = e instanceof Error ? e.message : String(e)
    }
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    header="Retirer la pièce"
    :style="{ width: '30rem' }"
    data-test="retrait-dialog"
  >
    <div class="form">
      <p v-if="document" class="sy-muted">
        « {{ document.nom_original }} » ({{ document.type_document_nom }}) quittera la liste. Le
        fichier est conservé et reste consultable ; le retrait ne peut pas être annulé.
      </p>
      <label class="field">
        <span>Motif du retrait</span>
        <Textarea
          v-model="motif"
          rows="3"
          auto-resize
          :invalid="!!errors.motif"
          placeholder="Par exemple : déposée sur le mauvais agent"
          aria-label="Motif du retrait"
          data-test="retrait-motif"
        />
        <small v-for="m in errors.motif" :key="m" class="error">{{ m }}</small>
      </label>
      <Message v-if="general" severity="error" :closable="false">{{ general }}</Message>
    </div>

    <template #footer>
      <Button label="Annuler" severity="secondary" text @click="visible = false" />
      <Button
        label="Retirer"
        icon="pi pi-eye-slash"
        severity="danger"
        :loading="sending"
        data-test="retrait-confirmer"
        @click="retirer"
      />
    </template>
  </Dialog>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-3);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-1);
}

.error {
  color: var(--sy-danger);
}
</style>
