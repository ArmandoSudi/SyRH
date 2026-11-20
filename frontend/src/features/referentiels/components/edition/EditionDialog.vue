<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'

import {
  corriger,
  creer,
  remplacer,
  suite,
  type Suite,
  type Valeurs,
} from '@/features/referentiels/api/edition'
import {
  fetchCategories,
  fetchGrades,
  fetchSites,
  fetchTypesDocument,
  fetchUnites,
} from '@/features/referentiels/api/referentiels'
import {
  DATES,
  type Champ,
  type Edition,
  type Source,
} from '@/features/referentiels/components/edition/champs'
import { localDate, parseDate } from '@/shared/utils/dates'
import { ApiError, type FieldErrors } from '@/shared/utils/http'

export type Mode = 'ajouter' | 'corriger' | 'remplacer' | 'fermer'

/**
 * One dialog for every reference table (reference data screens D11 to D14, tree reference
 * screens D11 and D16): add a row,
 * correct it, replace it from a date (close and open a successor), or close it. The
 * fields come from the table's description; the rules and their messages from the
 * server, shown under each field.
 */
const props = defineProps<{
  edition: Edition
  mode: Mode
  /** The row acted on; null when adding. */
  ligne?: Valeurs | null
  /** Values to start from when adding (a parameter's key, for instance). */
  initial?: Valeurs
}>()

const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ enregistre: [row: Valeurs] }>()

const valeurs = reactive<Valeurs>({})
const dateEffet = ref<Date | null>(null)
const errors = ref<FieldErrors>({})
const topError = ref<string | null>(null)
const saving = ref(false)
const parents = reactive<Partial<Record<Source, Valeurs[]>>>({})
const apercu = ref<Suite | null>(null)
const confirme = ref(false)
const form = ref<HTMLFormElement | null>(null)

const dates = computed(() => props.edition.dates ?? DATES)

/** The fields this mode shows, in order. */
const champs = computed<Champ[]>(() => {
  const own = props.edition.champs
  switch (props.mode) {
    case 'ajouter':
    case 'corriger':
      return [...own, ...dates.value]
    case 'remplacer':
      // A successor is a new row: it may change a fixed field (a unit moving), not a kept one.
      return own.filter((c) => !c.garde)
    case 'fermer':
      return DATES.filter((c) => c.nom === 'date_fermeture')
  }
  return own
})

const titre = computed(
  () =>
    ({
      ajouter: `Ajouter ${props.edition.un}`,
      corriger: `Corriger ${props.edition.un}`,
      remplacer: 'Remplacer à une date',
      fermer: 'Fermer à une date',
    })[props.mode],
)

const sousTitre = computed(() => {
  const row = props.ligne
  if (!row) return ''
  if (row.code) return `${String(row.code)} — ${String(row.nom ?? '')}`
  return String(row.libelle ?? row.cle_libelle ?? row.evenement_libelle ?? '')
})

const explication = computed(
  () =>
    ({
      ajouter: '',
      corriger: 'Pour une erreur de saisie. Un vrai changement se remplace à une date.',
      remplacer:
        'La ligne actuelle se ferme à la date d’effet ; la nouvelle s’applique à partir de ce jour.',
      fermer: 'La ligne ne s’applique plus à partir de cette date.',
    })[props.mode],
)

function vide(champ: Champ): unknown {
  if (champ.genre === 'oui-non') return false
  if (champ.genre === 'texte') return ''
  if (champ.genre === 'choix' && champ.requis) return champ.choix?.[0]?.value ?? null
  if (champ.nom === 'date_ouverture') return new Date()
  return null
}

function depuis(champ: Champ, value: unknown): unknown {
  if (champ.genre === 'date') return parseDate(value as string | null)
  if (champ.genre === 'texte') return (value as string | null) ?? ''
  return value ?? null
}

function reset() {
  for (const key of Object.keys(valeurs)) delete valeurs[key]
  for (const champ of [...props.edition.champs, ...DATES]) {
    const source = props.mode === 'ajouter' ? props.initial : props.ligne
    if (source && champ.nom in source) valeurs[champ.nom] = depuis(champ, source[champ.nom])
    else if (source && champ.lire && props.mode !== 'ajouter')
      valeurs[champ.nom] = champ.lire(source)
    else valeurs[champ.nom] = vide(champ)
  }
  if (props.mode === 'fermer') valeurs.date_fermeture = valeurs.date_fermeture ?? new Date()
  dateEffet.value = null
  apercu.value = null
  confirme.value = false
  errors.value = {}
  topError.value = null
}

const FETCH: Record<Source, (date: string) => Promise<unknown[]>> = {
  sites: () => fetchSites(),
  unites: (date) => fetchUnites({ date }),
  categories: (date) => fetchCategories({ date }),
  grades: (date) => fetchGrades({ date }),
  'types-document': (date) => fetchTypesDocument({ date }),
}

/** The rows the parent fields pick from: open today (tree reference screens D11). */
async function loadParents() {
  const today = localDate(new Date())
  const sources = new Set(props.edition.champs.flatMap((c) => (c.source ? [c.source] : [])))
  await Promise.all(
    [...sources].map(async (source) => {
      try {
        parents[source] = (await FETCH[source](today)) as Valeurs[]
      } catch {
        parents[source] = []
      }
    }),
  )
}

function optionsFor(champ: Champ) {
  const rows = (champ.source && parents[champ.source]) || []
  return rows
    .filter((row) => !champ.filtre || champ.filtre(row, valeurs))
    .map((row) => ({ value: row.id, label: `${String(row.code)} — ${String(row.nom)}` }))
}

/** What replacing on the chosen date would carry over (tree reference screens D9, D16). */
watch(dateEffet, async (date) => {
  apercu.value = null
  confirme.value = false
  if (props.mode !== 'remplacer' || !props.edition.suite || !date || !props.ligne) return
  try {
    apercu.value = await suite(props.edition.table, Number(props.ligne.id), localDate(date))
  } catch {
    apercu.value = null
  }
})

const detailSuite = computed(() =>
  (apercu.value?.par_genre ?? []).map((g) => `${g.nombre} ${g.libelle}`).join(', '),
)
const bloque = computed(
  () =>
    Boolean(apercu.value?.bloquants.length) || (Boolean(apercu.value?.total) && !confirme.value),
)

watch(
  visible,
  (open) => {
    if (!open) return
    reset()
    void loadParents()
  },
  { immediate: true },
)

/** Once the dialog is shown (it focuses its close button itself), focus the first field. */
async function focusFirstField() {
  await nextTick()
  form.value?.querySelector<HTMLElement>('input:not([disabled]), [tabindex="0"]')?.focus()
}

function versServeur(champ: Champ): unknown {
  const value = valeurs[champ.nom]
  if (champ.genre === 'date') return value instanceof Date ? localDate(value) : null
  if (champ.genre === 'texte') return String(value ?? '').trim()
  return value ?? null
}

function payload(): Valeurs {
  const data: Valeurs = {}
  for (const champ of champs.value) {
    if (props.mode === 'corriger' && champ.fixe) continue
    data[champ.nom] = versServeur(champ)
  }
  return data
}

const shown = computed(() => new Set(champs.value.map((c) => c.nom)))

async function save() {
  errors.value = {}
  topError.value = null
  if (props.mode === 'remplacer' && !dateEffet.value) {
    errors.value = { date_effet: ['Indiquez la date à partir de laquelle la ligne change.'] }
    return
  }
  if (bloque.value) return
  saving.value = true
  const { table } = props.edition
  const id = Number(props.ligne?.id)
  try {
    let row: Valeurs
    if (props.mode === 'ajouter') row = await creer<Valeurs>(table, payload())
    else if (props.mode === 'remplacer')
      row = await remplacer<Valeurs>(table, id, localDate(dateEffet.value!), payload())
    else row = await corriger<Valeurs>(table, id, payload())
    visible.value = false
    emit('enregistre', row)
  } catch (e) {
    if (e instanceof ApiError && e.status === 400) {
      const placed: FieldErrors = {}
      const elsewhere: string[] = []
      for (const [name, messages] of Object.entries(e.fieldErrors)) {
        if (shown.value.has(name) || name === 'date_effet') placed[name] = messages
        else elsewhere.push(...messages)
      }
      errors.value = placed
      const general = e.message.startsWith('API responded') ? [] : [e.message]
      topError.value = [...general, ...elsewhere].join(' ') || null
    } else if (e instanceof ApiError && e.status === 403) {
      topError.value = e.message
    } else if (!(e instanceof ApiError && e.status === 401)) {
      topError.value = 'Enregistrement impossible pour le moment. Réessayez dans un instant.'
    }
  } finally {
    saving.value = false
  }
}

function isDisabled(champ: Champ): boolean {
  return props.mode === 'corriger' && Boolean(champ.fixe)
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="titre"
    :draggable="false"
    class="edition-dialog"
    :style="{ width: '32rem' }"
    :breakpoints="{ '640px': '94vw' }"
    data-test="edition-dialog"
    @show="focusFirstField"
  >
    <form ref="form" class="form" novalidate @submit.prevent="save">
      <p v-if="sousTitre" class="sous-titre" data-test="edition-ligne">{{ sousTitre }}</p>
      <p v-if="explication" class="sy-muted explication">{{ explication }}</p>

      <Message v-if="topError" severity="error" :closable="false" data-test="edition-erreur">
        {{ topError }}
      </Message>

      <div v-if="mode === 'remplacer'" class="champ">
        <label for="champ-date_effet">Date d'effet <span aria-hidden="true">*</span></label>
        <DatePicker
          v-model="dateEffet"
          input-id="champ-date_effet"
          date-format="dd/mm/yy"
          show-icon
          icon-display="input"
          :show-on-focus="false"
          :invalid="Boolean(errors.date_effet)"
          data-test="champ-date_effet"
        />
        <small v-for="m in errors.date_effet" :key="m" class="erreur" data-test="erreur-date_effet">
          {{ m }}
        </small>
        <div v-if="apercu" class="apercu" data-test="edition-apercu">
          <Message v-if="apercu.bloquants.length" severity="error" :closable="false">
            Ces lignes rattachées ouvrent à cette date ou après et ne peuvent pas suivre :
            {{ apercu.bloquants.join(', ') }}. Corrigez-les ou fermez-les d'abord.
          </Message>
          <template v-else-if="apercu.total">
            <p class="suite">
              {{
                apercu.total === 1
                  ? 'La ligne rattachée suivra'
                  : `Les ${apercu.total} lignes rattachées suivront`
              }}
              : {{ detailSuite }}.
            </p>
            <label class="confirme" for="edition-confirme">
              <Checkbox
                v-model="confirme"
                binary
                input-id="edition-confirme"
                data-test="edition-confirme"
              />
              Je confirme : elles seront fermées à cette date et recréées sous la nouvelle ligne.
            </label>
          </template>
          <p v-else class="sy-muted suite">Aucune ligne rattachée ne suit.</p>
        </div>
      </div>

      <div v-for="champ in champs" :key="champ.nom" class="champ" :class="champ.genre">
        <label :for="`champ-${champ.nom}`">
          {{ champ.libelle }}
          <span v-if="champ.requis" aria-hidden="true">*</span>
        </label>

        <InputText
          v-if="champ.genre === 'texte'"
          :id="`champ-${champ.nom}`"
          v-model="valeurs[champ.nom] as string"
          :invalid="Boolean(errors[champ.nom])"
          :data-test="`champ-${champ.nom}`"
        />
        <ToggleSwitch
          v-else-if="champ.genre === 'oui-non'"
          v-model="valeurs[champ.nom] as boolean"
          :input-id="`champ-${champ.nom}`"
          :data-test="`champ-${champ.nom}`"
        />
        <Select
          v-else-if="champ.genre === 'choix'"
          v-model="valeurs[champ.nom]"
          :input-id="`champ-${champ.nom}`"
          :options="champ.choix"
          option-label="label"
          option-value="value"
          :disabled="isDisabled(champ)"
          :invalid="Boolean(errors[champ.nom])"
          :data-test="`champ-${champ.nom}`"
        />
        <Select
          v-else-if="champ.genre === 'parent'"
          v-model="valeurs[champ.nom]"
          :input-id="`champ-${champ.nom}`"
          :options="optionsFor(champ)"
          option-label="label"
          option-value="value"
          filter
          :show-clear="!champ.requis"
          :placeholder="champ.requis ? 'Choisir' : 'Aucune'"
          :disabled="isDisabled(champ)"
          :invalid="Boolean(errors[champ.nom])"
          :data-test="`champ-${champ.nom}`"
        />
        <InputNumber
          v-else-if="champ.genre === 'nombre'"
          v-model="valeurs[champ.nom] as number | null"
          :input-id="`champ-${champ.nom}`"
          :use-grouping="false"
          :min="0"
          :invalid="Boolean(errors[champ.nom])"
          :data-test="`champ-${champ.nom}`"
        />
        <DatePicker
          v-else-if="champ.genre === 'date'"
          v-model="valeurs[champ.nom] as Date | null"
          :input-id="`champ-${champ.nom}`"
          date-format="dd/mm/yy"
          show-icon
          icon-display="input"
          :show-on-focus="false"
          :show-button-bar="!champ.requis"
          :invalid="Boolean(errors[champ.nom])"
          :data-test="`champ-${champ.nom}`"
        />

        <small v-if="champ.aide" class="sy-muted aide">{{ champ.aide }}</small>
        <small
          v-for="m in errors[champ.nom]"
          :key="m"
          class="erreur"
          :data-test="`erreur-${champ.nom}`"
        >
          {{ m }}
        </small>
      </div>

      <div class="actions">
        <Button
          type="button"
          label="Annuler"
          severity="secondary"
          text
          data-test="edition-annuler"
          @click="visible = false"
        />
        <Button
          type="submit"
          label="Enregistrer"
          icon="pi pi-check"
          :loading="saving"
          :disabled="bloque"
          data-test="edition-enregistrer"
        />
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-3);
}

.sous-titre {
  margin: 0;
  font-weight: 600;
}

.explication {
  margin: 0;
  font-size: 0.85rem;
}

.champ {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-1);
}

.champ label {
  font-size: 0.85rem;
  font-weight: 500;
}

.champ :deep(input),
.champ :deep(.p-select),
.champ :deep(.p-inputnumber),
.champ :deep(.p-datepicker) {
  width: 100%;
}

.aide {
  font-size: 0.8rem;
}

.erreur {
  color: var(--p-red-500, #d33);
  font-size: 0.8rem;
}

.apercu {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-2);
  margin-top: var(--sy-space-2);
}

.suite {
  margin: 0;
  font-size: 0.85rem;
}

.confirme {
  display: flex;
  align-items: flex-start;
  gap: var(--sy-space-2);
  font-size: 0.85rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--sy-space-2);
  margin-top: var(--sy-space-2);
}
</style>
