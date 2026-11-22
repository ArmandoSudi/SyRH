<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'

import { uploadDocument, type Document } from '@/features/agents/api/documents'
import { ACCEPT, checkFile, formatTaille } from '@/features/agents/components/documents'
import type { TypeDocument } from '@/features/referentiels/api/referentiels'
import { localDate } from '@/shared/utils/dates'
import { ApiError, type FieldErrors } from '@/shared/utils/http'

/**
 * "Ajouter une pièce" (document storage D22): the type, the optional date printed on
 * the document, and the file, checked here first with the server's own messages, then
 * sent with a progress bar. The server's refusals show under their field.
 */
const props = defineProps<{
  agentId: number
  /** The types the user may upload, open today. */
  types: TypeDocument[]
  /** The size limit in Mo, or null when it could not be read. */
  maxMo: number | null
}>()

const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ depose: [document: Document] }>()

const typeDocument = ref<number | null>(null)
const dateDocument = ref<Date | null>(null)
const fichier = ref<File | null>(null)
const errors = ref<FieldErrors>({})
const general = ref<string | null>(null)
const progress = ref<number | null>(null)
const input = ref<HTMLInputElement | null>(null)

const sending = computed(() => progress.value !== null)
const options = computed(() =>
  props.types.map((type) => ({ value: type.id, label: `${type.nom} (${type.code})` })),
)

watch(visible, (open) => {
  if (!open) return
  typeDocument.value = null
  dateDocument.value = null
  fichier.value = null
  errors.value = {}
  general.value = null
  progress.value = null
  if (input.value) input.value.value = ''
})

function choisir(event: Event) {
  const files = (event.target as HTMLInputElement).files
  fichier.value = files && files.length > 0 ? files[0]! : null
  const others: FieldErrors = { ...errors.value }
  delete others.fichier
  const message = fichier.value ? checkFile(fichier.value, props.maxMo) : null
  errors.value = message ? { ...others, fichier: [message] } : others
}

async function deposer() {
  const local: FieldErrors = {}
  if (typeDocument.value === null) local.type_document = ['Choisissez le type de pièce.']
  if (!fichier.value) {
    local.fichier = ['Choisissez le fichier à déposer.']
  } else {
    const message = checkFile(fichier.value, props.maxMo)
    if (message) local.fichier = [message]
  }
  errors.value = local
  general.value = null
  if (Object.keys(local).length > 0) return

  progress.value = 0
  try {
    const document = await uploadDocument(
      props.agentId,
      {
        type_document: typeDocument.value!,
        fichier: fichier.value!,
        date_document: dateDocument.value ? localDate(dateDocument.value) : null,
      },
      (fraction) => {
        progress.value = Math.round(fraction * 100)
      },
    )
    visible.value = false
    emit('depose', document)
  } catch (e) {
    if (e instanceof ApiError && Object.keys(e.fieldErrors).length > 0) {
      errors.value = e.fieldErrors
    } else {
      general.value = e instanceof Error ? e.message : String(e)
    }
  } finally {
    progress.value = null
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    header="Ajouter une pièce"
    :closable="!sending"
    :style="{ width: '32rem' }"
    data-test="ajout-dialog"
  >
    <form class="form" @submit.prevent="deposer">
      <label class="field">
        <span>Type de pièce</span>
        <Select
          v-model="typeDocument"
          :options="options"
          option-label="label"
          option-value="value"
          filter
          placeholder="Choisir un type"
          :invalid="!!errors.type_document"
          aria-label="Type de pièce"
          data-test="ajout-type"
        />
        <small v-for="m in errors.type_document" :key="m" class="error">{{ m }}</small>
      </label>

      <label class="field">
        <span>Date de la pièce <span class="sy-muted">(facultative)</span></span>
        <DatePicker
          v-model="dateDocument"
          date-format="dd/mm/yy"
          show-icon
          icon-display="input"
          :max-date="new Date()"
          aria-label="Date de la pièce"
          data-test="ajout-date"
        />
        <small v-for="m in errors.date_document" :key="m" class="error">{{ m }}</small>
      </label>

      <div class="field">
        <span id="ajout-fichier-label">Fichier</span>
        <input
          ref="input"
          type="file"
          :accept="ACCEPT"
          aria-labelledby="ajout-fichier-label"
          class="file"
          data-test="ajout-fichier"
          @change="choisir"
        />
        <small class="sy-muted">
          PDF, JPEG ou PNG<template v-if="maxMo !== null">, {{ maxMo }} Mo au plus</template>.
        </small>
        <small v-if="fichier" class="sy-muted" data-test="ajout-choisi">
          {{ fichier.name }} — {{ formatTaille(fichier.size) }}
        </small>
        <small v-for="m in errors.fichier" :key="m" class="error" data-test="ajout-fichier-erreur">
          {{ m }}
        </small>
      </div>

      <ProgressBar
        v-if="sending"
        :value="progress ?? 0"
        aria-label="Envoi du fichier"
        data-test="ajout-progression"
      />
      <Message v-if="general" severity="error" :closable="false" data-test="ajout-erreur">
        {{ general }}
      </Message>
    </form>

    <template #footer>
      <Button
        label="Annuler"
        severity="secondary"
        text
        :disabled="sending"
        @click="visible = false"
      />
      <Button
        label="Déposer"
        icon="pi pi-upload"
        :loading="sending"
        data-test="ajout-deposer"
        @click="deposer"
      />
    </template>
  </Dialog>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-4);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-1);
}

.file {
  font: inherit;
  color: var(--sy-text);
}

.error {
  color: var(--sy-danger);
}
</style>
