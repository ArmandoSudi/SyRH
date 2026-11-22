<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, RouterLink, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import RadioButton from 'primevue/radiobutton'
import Select from 'primevue/select'
import Step from 'primevue/step'
import StepList from 'primevue/steplist'
import StepPanel from 'primevue/steppanel'
import StepPanels from 'primevue/steppanels'
import Stepper from 'primevue/stepper'
import TreeSelect from 'primevue/treeselect'
import { useToast } from 'primevue/usetoast'

import type { AgentResume } from '@/features/agents/api/agents'
import { doublons, engager, matriculeSuivant } from '@/features/agents/api/engagement'
import {
  ETAPES,
  formulaireVide,
  ouvertLe,
  premiereEtapeEnErreur,
  verifierEtape,
  valeursAPlat,
  versEngagement,
} from '@/features/agents/components/engagement'
import { arbreUnites, type NoeudUnite } from '@/features/agents/components/unites'
import {
  fetchEchelons,
  fetchFonctions,
  fetchGrades,
  fetchPiecesRequises,
  fetchTypesContrat,
  fetchTypesDocument,
  fetchUnites,
  type Echelon,
  type Fonction,
  type Grade,
  type TypeContrat,
} from '@/features/referentiels/api/referentiels'
import { formatDate, localDate } from '@/shared/utils/dates'
import { ApiError, type FieldErrors } from '@/shared/utils/http'

/**
 * "Engager un agent" (agent creation form D11 to D17): identity, contact details,
 * contract, post, summary; saved all at once, then the agent's Pièces page opens on the
 * missing hiring pieces.
 */
const router = useRouter()
const toast = useToast()

const form = reactive(formulaireVide())
const etape = ref(0)
const errors = ref<FieldErrors>({})
const general = ref<string | null>(null)
const sending = ref(false)
const saved = ref(false)
const dirty = ref(false)

const typesContrat = ref<TypeContrat[]>([])
const unites = ref<NoeudUnite[]>([])
const uniteIds = ref<Set<number>>(new Set())
const fonctions = ref<Fonction[]>([])
const grades = ref<Grade[]>([])
const echelons = ref<Echelon[]>([])
const piecesExigees = ref<{ nom: string; obligatoire: boolean }[]>([])
const homonymes = ref<AgentResume[]>([])
const autreAgent = ref(false)
let suggestion = ''

const SEXES = [
  { value: 'M', label: 'Masculin' },
  { value: 'F', label: 'Féminin' },
]

const typeChoisi = computed(() =>
  typesContrat.value.find((t) => t.id === form.contrat.type_contrat),
)
const echelonsDuGrade = computed(() =>
  echelons.value
    .filter((e) => e.grade === form.classement.grade)
    .sort((a, b) => a.numero - b.numero),
)
const uniteSelection = computed({
  get: () => (form.affectation.unite ? { [String(form.affectation.unite)]: true } : null),
  set: (value: Record<string, boolean> | null) => {
    const key = value ? Object.keys(value)[0] : undefined
    form.affectation.unite = key ? Number(key) : null
  },
})
const jourReference = computed(() =>
  form.contrat.date_debut ? localDate(form.contrat.date_debut) : localDate(new Date()),
)

// An error leaves as soon as its field changes (D12).
let previous = valeursAPlat(form)
watch(
  form,
  () => {
    dirty.value = true
    const current = valeursAPlat(form)
    const remaining = { ...errors.value }
    let changed = false
    for (const key of Object.keys(remaining)) {
      if (key in current && current[key] !== previous[key]) {
        delete remaining[key]
        changed = true
      }
    }
    if (changed) errors.value = remaining
    previous = current
  },
  { deep: true },
)

function erreur(key: string): string[] {
  return errors.value[key] ?? []
}

/** The reference lists open on the contract's start (D13); a closed choice is cleared. */
async function chargerReferences() {
  const jour = jourReference.value
  const [t, u, f, g, e, p, d] = await Promise.allSettled([
    fetchTypesContrat({ date: jour }),
    fetchUnites({ date: jour }),
    fetchFonctions({ date: jour }),
    fetchGrades({ date: jour }),
    fetchEchelons({ date: jour }),
    fetchPiecesRequises({ date: jour }),
    fetchTypesDocument({ date: jour }),
  ])
  if (t.status === 'fulfilled') typesContrat.value = t.value.filter((r) => ouvertLe(r, jour))
  if (u.status === 'fulfilled') {
    unites.value = arbreUnites(u.value)
    uniteIds.value = new Set(u.value.map((r) => r.id))
  }
  if (f.status === 'fulfilled') fonctions.value = f.value
  if (g.status === 'fulfilled') grades.value = g.value
  if (e.status === 'fulfilled') echelons.value = e.value
  if (p.status === 'fulfilled' && d.status === 'fulfilled') {
    const noms = new Map(d.value.map((type) => [type.id, type.nom]))
    piecesExigees.value = p.value
      .filter((piece) => piece.evenement === 'engagement')
      .map((piece) => ({
        nom: noms.get(piece.type_document) ?? '?',
        obligatoire: piece.obligatoire,
      }))
  }
  if (
    form.contrat.type_contrat &&
    !typesContrat.value.some((r) => r.id === form.contrat.type_contrat)
  )
    form.contrat.type_contrat = null
  if (form.affectation.unite && !uniteIds.value.has(form.affectation.unite))
    form.affectation.unite = null
  if (form.affectation.fonction && !fonctions.value.some((r) => r.id === form.affectation.fonction))
    form.affectation.fonction = null
  if (form.classement.grade && !grades.value.some((r) => r.id === form.classement.grade)) {
    form.classement.grade = null
  }
  if (
    form.classement.echelon &&
    !echelonsDuGrade.value.some((r) => r.id === form.classement.echelon)
  )
    form.classement.echelon = null
}

/** Suggest the matricule from the hiring year, never over HR's own typing (D14). */
async function suggerer() {
  if (!form.contrat.date_debut) return
  if (form.matricule.trim() && form.matricule !== suggestion) return
  try {
    const proposed = await matriculeSuivant(form.contrat.date_debut.getFullYear())
    if (!form.matricule.trim() || form.matricule === suggestion) {
      form.matricule = proposed
      suggestion = proposed
    }
  } catch {
    // No suggestion: HR types it.
  }
}

watch(
  () => form.contrat.date_debut?.getTime(),
  () => {
    void chargerReferences()
    void suggerer()
  },
)
watch(
  () => form.classement.grade,
  () => {
    if (!echelonsDuGrade.value.some((r) => r.id === form.classement.echelon)) {
      form.classement.echelon = null
    }
  },
)
watch(typeChoisi, (type) => {
  if (type && !type.duree_determinee) form.contrat.date_fin = null
  if (type && !type.periode_essai) form.contrat.fin_periode_essai = null
})

async function chercherHomonymes() {
  homonymes.value = []
  autreAgent.value = false
  if (!form.nom.trim() || !form.date_naissance) return
  try {
    homonymes.value = await doublons({
      nom: form.nom.trim(),
      prenom: form.prenom.trim() || undefined,
      date_naissance: localDate(form.date_naissance),
    })
  } catch {
    homonymes.value = []
  }
}

function suivant() {
  const missing = verifierEtape(etape.value, form, typeChoisi.value)
  errors.value = missing
  if (Object.keys(missing).length) return
  etape.value += 1
  if (etape.value === 4) void chercherHomonymes()
}

function precedent() {
  etape.value = Math.max(0, etape.value - 1)
}

const peutEnregistrer = computed(() => homonymes.value.length === 0 || autreAgent.value)

async function enregistrer() {
  for (const i of [0, 1, 2, 3, 4]) {
    const missing = verifierEtape(i, form, typeChoisi.value)
    if (Object.keys(missing).length) {
      errors.value = missing
      etape.value = premiereEtapeEnErreur(missing) ?? i
      return
    }
  }
  sending.value = true
  general.value = null
  errors.value = {}
  try {
    const agent = await engager(versEngagement(form))
    saved.value = true
    toast.add({
      severity: 'success',
      summary: 'Agent engagé',
      detail: `${agent.matricule} — joignez maintenant les pièces d'engagement.`,
      life: 5000,
    })
    void router.push({ name: 'agents-pieces', query: { agent: String(agent.id) } })
  } catch (e) {
    if (e instanceof ApiError && Object.keys(e.fieldErrors).length) {
      errors.value = e.fieldErrors
      etape.value = premiereEtapeEnErreur(e.fieldErrors) ?? 0
    } else {
      general.value = e instanceof Error ? e.message : String(e)
    }
  } finally {
    sending.value = false
  }
}

// Leaving a filled form asks first (D16).
const LEAVE = 'Quitter le formulaire ? Les informations saisies seront perdues.'
onBeforeRouteLeave(() => (saved.value || !dirty.value ? true : window.confirm(LEAVE)))
function beforeUnload(event: BeforeUnloadEvent) {
  if (dirty.value && !saved.value) event.preventDefault()
}
onMounted(() => {
  window.addEventListener('beforeunload', beforeUnload)
  void chargerReferences().then(() => (dirty.value = false))
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload))

const resume = computed(() => {
  const unite = (() => {
    const find = (nodes: NoeudUnite[]): string | undefined => {
      for (const node of nodes) {
        if (node.data === form.affectation.unite) return node.label
        const inner = find(node.children ?? [])
        if (inner) return inner
      }
      return undefined
    }
    return find(unites.value) ?? '—'
  })()
  const grade = grades.value.find((g) => g.id === form.classement.grade)
  const echelon = echelons.value.find((e) => e.id === form.classement.echelon)
  return [
    ['Matricule', form.matricule],
    ['Nom', [form.nom, form.postnom, form.prenom].filter(Boolean).join(' ')],
    ['Sexe', SEXES.find((s) => s.value === form.sexe)?.label ?? '—'],
    [
      'Naissance',
      `${formatDate(form.date_naissance ? localDate(form.date_naissance) : null)} à ${form.lieu_naissance}`,
    ],
    ['Nationalité', form.nationalite],
    [
      'Coordonnées',
      [form.coordonnees.adresse, form.coordonnees.ville, form.coordonnees.telephone]
        .filter(Boolean)
        .join(', ') || 'Non renseignées',
    ],
    [
      'Contrat',
      `${typeChoisi.value?.nom ?? '—'} à partir du ${formatDate(form.contrat.date_debut ? localDate(form.contrat.date_debut) : null)}${form.contrat.date_fin ? ` jusqu'au ${formatDate(localDate(form.contrat.date_fin))}` : ''}`,
    ],
    ['Service', unite],
    ['Fonction', fonctions.value.find((f) => f.id === form.affectation.fonction)?.nom ?? '—'],
    ['Grade', grade && echelon ? `${grade.code} — ${grade.nom}, échelon ${echelon.numero}` : '—'],
  ]
})
</script>

<template>
  <div class="page">
    <RouterLink :to="{ name: 'agents' }" class="retour sy-muted">
      <i class="pi pi-arrow-left" /> Retour à la liste des agents
    </RouterLink>

    <div class="sy-card card">
      <Stepper :value="etape + 1" linear>
        <StepList>
          <Step v-for="(titre, i) in ETAPES" :key="titre" :value="i + 1" :disabled="i > etape">
            {{ titre }}
          </Step>
        </StepList>
        <StepPanels>
          <!-- 1. Identité -->
          <StepPanel :value="1">
            <div class="grid" data-test="etape-identite">
              <label class="field">
                <span>Matricule</span>
                <InputText
                  v-model="form.matricule"
                  :invalid="!!erreur('matricule').length"
                  data-test="f-matricule"
                />
                <small class="sy-muted"
                  >Proposé à l'étape Contrat d'après l'année d'engagement ; modifiable.</small
                >
                <small v-for="m in erreur('matricule')" :key="m" class="error">{{ m }}</small>
              </label>
              <label class="field">
                <span>Nom</span>
                <InputText v-model="form.nom" :invalid="!!erreur('nom').length" data-test="f-nom" />
                <small v-for="m in erreur('nom')" :key="m" class="error">{{ m }}</small>
              </label>
              <label class="field">
                <span>Postnom</span>
                <InputText v-model="form.postnom" data-test="f-postnom" />
              </label>
              <label class="field">
                <span>Prénom</span>
                <InputText v-model="form.prenom" data-test="f-prenom" />
              </label>
              <div class="field">
                <span id="f-sexe-label">Sexe</span>
                <div class="radios" role="radiogroup" aria-labelledby="f-sexe-label">
                  <label v-for="s in SEXES" :key="s.value" class="radio">
                    <RadioButton
                      v-model="form.sexe"
                      :value="s.value"
                      :input-id="`sexe-${s.value}`"
                    />
                    {{ s.label }}
                  </label>
                </div>
                <small v-for="m in erreur('sexe')" :key="m" class="error">{{ m }}</small>
              </div>
              <label class="field">
                <span>Date de naissance</span>
                <DatePicker
                  v-model="form.date_naissance"
                  date-format="dd/mm/yy"
                  show-icon
                  icon-display="input"
                  :max-date="new Date()"
                  :invalid="!!erreur('date_naissance').length"
                  data-test="f-naissance"
                />
                <small v-for="m in erreur('date_naissance')" :key="m" class="error">{{ m }}</small>
              </label>
              <label class="field">
                <span>Lieu de naissance</span>
                <InputText
                  v-model="form.lieu_naissance"
                  :invalid="!!erreur('lieu_naissance').length"
                  data-test="f-lieu"
                />
                <small v-for="m in erreur('lieu_naissance')" :key="m" class="error">{{ m }}</small>
              </label>
              <label class="field">
                <span>Nationalité</span>
                <InputText v-model="form.nationalite" data-test="f-nationalite" />
                <small v-for="m in erreur('nationalite')" :key="m" class="error">{{ m }}</small>
              </label>
            </div>
          </StepPanel>

          <!-- 2. Coordonnées -->
          <StepPanel :value="2">
            <p class="sy-muted">Facultatives : laissez vide pour les saisir plus tard.</p>
            <div class="grid" data-test="etape-coordonnees">
              <label
                v-for="[key, label] in [
                  ['adresse', 'Adresse'],
                  ['commune', 'Commune'],
                  ['ville', 'Ville'],
                  ['telephone', 'Téléphone'],
                  ['telephone_secondaire', 'Second téléphone'],
                  ['courriel', 'Courriel'],
                  ['urgence_nom', 'Personne à contacter en cas d\'urgence'],
                  ['urgence_lien', 'Lien avec l\'agent'],
                  ['urgence_telephone', 'Téléphone de la personne à contacter'],
                ] as const"
                :key="key"
                class="field"
              >
                <span>{{ label }}</span>
                <InputText
                  v-model="form.coordonnees[key]"
                  :invalid="!!erreur(`coordonnees.${key}`).length"
                  :data-test="`f-${key}`"
                />
                <small v-for="m in erreur(`coordonnees.${key}`)" :key="m" class="error">{{
                  m
                }}</small>
              </label>
            </div>
          </StepPanel>

          <!-- 3. Contrat -->
          <StepPanel :value="3">
            <div class="grid" data-test="etape-contrat">
              <label class="field">
                <span>Date de début</span>
                <DatePicker
                  v-model="form.contrat.date_debut"
                  date-format="dd/mm/yy"
                  show-icon
                  icon-display="input"
                  :invalid="!!erreur('contrat.date_debut').length"
                  data-test="f-debut"
                />
                <small class="sy-muted"
                  >Premier jour du contrat ; l'affectation et le classement en partent.</small
                >
                <small v-for="m in erreur('contrat.date_debut')" :key="m" class="error">{{
                  m
                }}</small>
              </label>
              <label class="field">
                <span>Type de contrat</span>
                <Select
                  v-model="form.contrat.type_contrat"
                  :options="typesContrat"
                  option-label="nom"
                  option-value="id"
                  placeholder="Choisir un type"
                  :invalid="!!erreur('contrat.type_contrat').length"
                  data-test="f-type"
                />
                <small v-for="m in erreur('contrat.type_contrat')" :key="m" class="error">{{
                  m
                }}</small>
              </label>
              <label v-if="typeChoisi?.duree_determinee" class="field">
                <span>Date de fin</span>
                <DatePicker
                  v-model="form.contrat.date_fin"
                  date-format="dd/mm/yy"
                  show-icon
                  icon-display="input"
                  :invalid="!!erreur('contrat.date_fin').length"
                  data-test="f-fin"
                />
                <small class="sy-muted">Dernier jour du contrat.</small>
                <small v-for="m in erreur('contrat.date_fin')" :key="m" class="error">{{
                  m
                }}</small>
              </label>
              <label v-if="typeChoisi?.periode_essai" class="field">
                <span>Fin de la période d'essai <span class="sy-muted">(facultative)</span></span>
                <DatePicker
                  v-model="form.contrat.fin_periode_essai"
                  date-format="dd/mm/yy"
                  show-icon
                  icon-display="input"
                  :invalid="!!erreur('contrat.fin_periode_essai').length"
                  data-test="f-essai"
                />
                <small v-for="m in erreur('contrat.fin_periode_essai')" :key="m" class="error">{{
                  m
                }}</small>
              </label>
            </div>
            <small v-for="m in erreur('contrat.non_field_errors')" :key="m" class="error">{{
              m
            }}</small>
          </StepPanel>

          <!-- 4. Poste -->
          <StepPanel :value="4">
            <p class="sy-muted">
              À partir du {{ formatDate(jourReference) }} : seuls les éléments ouverts à cette date
              sont proposés.
            </p>
            <div class="grid" data-test="etape-poste">
              <label class="field">
                <span>Service</span>
                <TreeSelect
                  v-model="uniteSelection"
                  :options="unites"
                  selection-mode="single"
                  filter
                  placeholder="Choisir une unité"
                  :invalid="!!erreur('affectation.unite').length"
                  data-test="f-unite"
                />
                <small v-for="m in erreur('affectation.unite')" :key="m" class="error">{{
                  m
                }}</small>
              </label>
              <label class="field">
                <span>Fonction</span>
                <Select
                  v-model="form.affectation.fonction"
                  :options="fonctions"
                  option-label="nom"
                  option-value="id"
                  filter
                  placeholder="Choisir une fonction"
                  :invalid="!!erreur('affectation.fonction').length"
                  data-test="f-fonction"
                />
                <small v-for="m in erreur('affectation.fonction')" :key="m" class="error">{{
                  m
                }}</small>
              </label>
              <label class="field">
                <span>Grade</span>
                <Select
                  v-model="form.classement.grade"
                  :options="grades.map((g) => ({ value: g.id, label: `${g.code} — ${g.nom}` }))"
                  option-label="label"
                  option-value="value"
                  filter
                  placeholder="Choisir un grade"
                  data-test="f-grade"
                />
              </label>
              <label class="field">
                <span>Échelon</span>
                <Select
                  v-model="form.classement.echelon"
                  :options="
                    echelonsDuGrade.map((e) => ({ value: e.id, label: `Échelon ${e.numero}` }))
                  "
                  option-label="label"
                  option-value="value"
                  :disabled="!form.classement.grade"
                  placeholder="Choisir un échelon"
                  :invalid="!!erreur('classement.echelon').length"
                  data-test="f-echelon"
                />
                <small v-for="m in erreur('classement.echelon')" :key="m" class="error">{{
                  m
                }}</small>
              </label>
            </div>
          </StepPanel>

          <!-- 5. Récapitulatif -->
          <StepPanel :value="5">
            <dl class="resume" data-test="resume">
              <template v-for="[label, value] in resume" :key="label">
                <dt>{{ label }}</dt>
                <dd>{{ value }}</dd>
              </template>
            </dl>
            <div class="pieces" data-test="resume-pieces">
              <strong>Pièces d'engagement à joindre ensuite</strong>
              <ul v-if="piecesExigees.length">
                <li v-for="p in piecesExigees" :key="p.nom">
                  {{ p.nom }}
                  <span class="sy-muted">{{ p.obligatoire ? 'obligatoire' : 'facultative' }}</span>
                </li>
              </ul>
              <p v-else class="sy-muted">Aucune pièce exigée à cette date.</p>
            </div>
            <Message
              v-if="homonymes.length"
              severity="warn"
              :closable="false"
              data-test="homonymes"
            >
              <p>Un agent porte déjà ce nom et cette date de naissance :</p>
              <ul>
                <li v-for="a in homonymes" :key="a.id">
                  <RouterLink
                    :to="{ name: 'agents-pieces', query: { agent: String(a.id) } }"
                    target="_blank"
                  >
                    {{ a.matricule }} — {{ [a.nom, a.postnom, a.prenom].filter(Boolean).join(' ') }}
                  </RouterLink>
                </li>
              </ul>
              <label class="confirm">
                <Checkbox
                  v-model="autreAgent"
                  binary
                  input-id="autre-agent"
                  data-test="autre-agent"
                />
                Il s'agit bien d'un autre agent
              </label>
            </Message>
          </StepPanel>
        </StepPanels>
      </Stepper>

      <Message v-if="general" severity="error" :closable="false" data-test="engagement-erreur">{{
        general
      }}</Message>

      <div class="actions">
        <Button
          v-if="etape > 0"
          label="Précédent"
          icon="pi pi-arrow-left"
          severity="secondary"
          text
          data-test="precedent"
          @click="precedent"
        />
        <Button
          v-if="etape < 4"
          label="Suivant"
          icon="pi pi-arrow-right"
          icon-pos="right"
          class="droite"
          data-test="suivant"
          @click="suivant"
        />
        <Button
          v-else
          label="Engager l'agent"
          icon="pi pi-check"
          class="droite"
          :loading="sending"
          :disabled="!peutEnregistrer"
          data-test="enregistrer"
          @click="enregistrer"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-3);
}

.retour {
  text-decoration: none;
  font-size: 0.9rem;
}

.card {
  padding: var(--sy-space-5);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
  gap: var(--sy-space-4);
  margin-top: var(--sy-space-3);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-1);
}

.radios {
  display: flex;
  gap: var(--sy-space-4);
  min-height: 2.5rem;
  align-items: center;
}

.radio,
.confirm {
  display: inline-flex;
  align-items: center;
  gap: var(--sy-space-2);
}

.error {
  color: var(--sy-danger);
}

.resume {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: var(--sy-space-2) var(--sy-space-4);
  margin: var(--sy-space-3) 0;
}

.resume dt {
  color: var(--sy-muted);
}

.resume dd {
  margin: 0;
}

.pieces ul {
  margin: var(--sy-space-2) 0 var(--sy-space-3);
}

.actions {
  display: flex;
  gap: var(--sy-space-3);
  margin-top: var(--sy-space-4);
}

.droite {
  margin-left: auto;
}
</style>
