<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable, { type DataTablePageEvent } from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import TreeSelect from 'primevue/treeselect'

import { searchAgents, type AgentResume } from '@/features/agents/api/agents'
import { STATUTS, statutSeverity } from '@/features/agents/components/statuts'
import { arbreUnites, type NoeudUnite } from '@/features/agents/components/unites'
import {
  filtresDepuisQuery,
  queryDepuisFiltres,
  rechercheDepuisFiltres,
  useAgentListStore,
  type FiltresAgents,
} from '@/features/agents/stores/agentList'
import {
  fetchFonctions,
  fetchGrades,
  fetchUnites,
  type Fonction,
  type Grade,
} from '@/features/referentiels/api/referentiels'
import { useAuthStore } from '@/features/auth/stores/auth'
import { localDate, parseDate } from '@/shared/utils/dates'
import { ApiError } from '@/shared/utils/http'

/**
 * The agent list (agent list D12 to D15): search by matricule or name, service (with its
 * sub-units), grade, function and status, at a date; 25 agents a page. The filters live
 * in the URL and in Pinia. A row opens the agent's documents page until roadmap 2.10.
 */
const route = useRoute()
const router = useRouter()
const store = useAgentListStore()
const auth = useAuthStore()

const agents = ref<AgentResume[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)
const texte = ref(store.filtres.q)

const unites = ref<NoeudUnite[]>([])
const grades = ref<Grade[]>([])
const fonctions = ref<Fonction[]>([])

const filtres = computed(() => store.filtres)
const TAILLE = 25
const TRIS = [
  { value: 'nom', label: 'Nom' },
  { value: 'matricule', label: 'Matricule' },
]

function appliquer(partiel: Partial<FiltresAgents>) {
  // Widgets may re-emit their current value (on mount, on options loading): ignore it,
  // or the page would go back to 1.
  const courant = store.filtres as unknown as Record<string, unknown>
  const change = Object.entries(partiel).some(
    ([key, value]) => JSON.stringify(value) !== JSON.stringify(courant[key]),
  )
  if (!change) return
  const suivants: FiltresAgents = { ...store.filtres, page: 1, ...partiel }
  store.remplacer(suivants)
  void router.replace({ query: queryDepuisFiltres(suivants) })
}

let latest = 0
async function load() {
  const call = ++latest
  loading.value = true
  error.value = null
  try {
    const page = await searchAgents(rechercheDepuisFiltres(store.filtres))
    if (call !== latest) return
    agents.value = page.results
    total.value = page.count
  } catch (e) {
    if (call !== latest) return
    // A page beyond the end (fewer agents since the link was made): back to page 1.
    if (e instanceof ApiError && e.status === 404 && store.filtres.page > 1) {
      appliquer({ page: 1 })
      return
    }
    error.value = e instanceof Error ? e.message : String(e)
    agents.value = []
    total.value = 0
  } finally {
    if (call === latest) loading.value = false
  }
}

async function loadReferences() {
  const date = store.filtres.date ?? localDate(new Date())
  const [u, g, f] = await Promise.allSettled([
    fetchUnites({ date }),
    fetchGrades({ date }),
    fetchFonctions({ date }),
  ])
  if (u.status === 'fulfilled') unites.value = arbreUnites(u.value)
  if (g.status === 'fulfilled') grades.value = g.value
  if (f.status === 'fulfilled') fonctions.value = f.value
}

// The URL wins when it carries a search; otherwise the store's search goes into the URL.
onMounted(() => {
  if (Object.keys(route.query).length > 0 || !store.touche) {
    store.remplacer(filtresDepuisQuery(route.query))
  } else {
    void router.replace({ query: queryDepuisFiltres(store.filtres) })
  }
  texte.value = store.filtres.q
  void loadReferences()
})

// Another page (the top-bar search) may change the URL while the list is open.
watch(
  () => route.query,
  (query) => {
    const depuis = filtresDepuisQuery(query)
    if (JSON.stringify(depuis) !== JSON.stringify(store.filtres)) {
      store.remplacer(depuis)
      texte.value = depuis.q
    }
  },
)

watch(
  () => JSON.stringify(store.filtres),
  () => void load(),
  { immediate: true },
)
watch(
  () => store.filtres.date,
  () => void loadReferences(),
)

let timer: ReturnType<typeof setTimeout> | undefined
watch(texte, (value) => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    if (value !== store.filtres.q) appliquer({ q: value })
  }, 300)
})

const uniteSelection = computed({
  get: () => (filtres.value.unite ? { [String(filtres.value.unite)]: true } : null),
  set: (value: Record<string, boolean> | null) => {
    const key = value ? Object.keys(value)[0] : undefined
    appliquer({ unite: key ? Number(key) : null })
  },
})
const dateSituation = computed({
  get: () => parseDate(filtres.value.date),
  set: (value: Date | null) => appliquer({ date: value ? localDate(value) : null }),
})
const gradeOptions = computed(() =>
  grades.value.map((g) => ({ value: g.id, label: `${g.code} — ${g.nom}` })),
)
const fonctionOptions = computed(() => fonctions.value.map((f) => ({ value: f.id, label: f.nom })))
const filtre = computed(
  () =>
    !!(filtres.value.q || filtres.value.unite || filtres.value.grade || filtres.value.fonction) ||
    filtres.value.date !== null ||
    filtres.value.statut.join(',') !== 'actif',
)
const compte = computed(() =>
  total.value === 1 ? '1 agent' : `${total.value.toLocaleString('fr-FR')} agents`,
)

function effacer() {
  store.effacer()
  texte.value = ''
  void router.replace({ query: {} })
}

function page(event: DataTablePageEvent) {
  // Before the first answer the paginator knows no total and resets its offset: ignore it.
  if (total.value === 0) return
  appliquer({ page: event.page + 1 })
}

function lien(agent: AgentResume) {
  return { name: 'agents-pieces', query: { agent: String(agent.id) } }
}

function noms(agent: AgentResume): string {
  return [agent.nom, agent.postnom, agent.prenom].filter(Boolean).join(' ')
}
</script>

<template>
  <div class="page">
    <div class="toolbar" role="search" aria-label="Rechercher des agents">
      <IconField class="search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="texte"
          placeholder="Matricule ou nom"
          aria-label="Matricule ou nom"
          data-test="agents-q"
        />
      </IconField>
      <TreeSelect
        v-model="uniteSelection"
        :options="unites"
        selection-mode="single"
        placeholder="Service"
        aria-label="Service"
        show-clear
        filter
        class="filtre"
        data-test="agents-unite"
      />
      <Select
        :model-value="filtres.grade"
        :options="gradeOptions"
        option-label="label"
        option-value="value"
        placeholder="Grade"
        aria-label="Grade"
        show-clear
        filter
        class="filtre"
        data-test="agents-grade"
        @update:model-value="(v: number | null) => appliquer({ grade: v ?? null })"
      />
      <Select
        :model-value="filtres.fonction"
        :options="fonctionOptions"
        option-label="label"
        option-value="value"
        placeholder="Fonction"
        aria-label="Fonction"
        show-clear
        filter
        class="filtre"
        data-test="agents-fonction"
        @update:model-value="(v: number | null) => appliquer({ fonction: v ?? null })"
      />
      <MultiSelect
        :model-value="filtres.statut"
        :options="STATUTS"
        option-label="label"
        option-value="value"
        placeholder="Tous les statuts"
        aria-label="Statut"
        display="chip"
        :show-toggle-all="false"
        class="filtre"
        data-test="agents-statut"
        @update:model-value="(v: FiltresAgents['statut']) => appliquer({ statut: v })"
      />
      <label class="field">
        <span class="sy-muted">Situation au</span>
        <DatePicker
          v-model="dateSituation"
          date-format="dd/mm/yy"
          show-icon
          icon-display="input"
          placeholder="Aujourd'hui"
          show-button-bar
          aria-label="Situation au"
          data-test="agents-date"
        />
      </label>
    </div>

    <div class="summary">
      <span class="sy-muted" data-test="agents-count">{{ compte }}</span>
      <label class="tri">
        <span class="sy-muted">Trier par</span>
        <Select
          :model-value="filtres.tri"
          :options="TRIS"
          option-label="label"
          option-value="value"
          aria-label="Trier par"
          data-test="agents-tri"
          @update:model-value="(v: FiltresAgents['tri']) => appliquer({ tri: v })"
        />
      </label>
      <RouterLink
        v-if="auth.can('agents.add_agent')"
        :to="{ name: 'agents-nouveau' }"
        class="p-button nouveau"
        data-test="agents-nouveau"
      >
        <i class="pi pi-user-plus" /> Nouvel agent
      </RouterLink>
      <Button
        v-if="filtre"
        label="Effacer les filtres"
        icon="pi pi-filter-slash"
        text
        severity="secondary"
        data-test="agents-effacer"
        @click="effacer"
      />
    </div>

    <Message v-if="error" severity="error" :closable="false" data-test="agents-error">
      Les agents n'ont pas pu être chargés : {{ error }}
    </Message>

    <DataTable
      :value="agents"
      :loading="loading"
      data-key="id"
      lazy
      paginator
      :rows="TAILLE"
      :total-records="total"
      :first="(filtres.page - 1) * TAILLE"
      class="agents"
      data-test="agents"
      @page="page"
    >
      <template #empty>
        <p class="sy-muted empty">
          {{ filtre ? 'Aucun agent ne correspond à cette recherche.' : 'Aucun agent.' }}
        </p>
      </template>
      <Column header="Matricule">
        <template #body="{ data }">
          <RouterLink :to="lien(data)" class="sy-num nowrap lien">{{ data.matricule }}</RouterLink>
        </template>
      </Column>
      <Column header="Nom">
        <template #body="{ data }">
          <RouterLink :to="lien(data)" class="lien" data-test="agents-nom">
            {{ noms(data) }}
          </RouterLink>
        </template>
      </Column>
      <Column header="Service">
        <template #body="{ data }">
          <template v-if="data.affectation_actuelle">
            <span class="sy-num">{{ data.affectation_actuelle.unite_code }}</span>
            <span class="sy-muted bloc">{{ data.affectation_actuelle.unite_nom }}</span>
          </template>
          <span v-else class="sy-muted">—</span>
        </template>
      </Column>
      <Column header="Fonction">
        <template #body="{ data }">
          {{ data.affectation_actuelle?.fonction_nom ?? '—' }}
        </template>
      </Column>
      <Column header="Grade">
        <template #body="{ data }">
          <template v-if="data.classement_actuel">
            <span class="sy-num">{{ data.classement_actuel.grade_code }}</span>
            <span class="sy-muted"> · éch. {{ data.classement_actuel.echelon_numero }}</span>
          </template>
          <span v-else class="sy-muted">—</span>
        </template>
      </Column>
      <Column header="Statut">
        <template #body="{ data }">
          <Tag
            :value="data.statut_libelle"
            :severity="statutSeverity(data.statut)"
            data-test="agents-statut-tag"
          />
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-3);
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: var(--sy-space-3);
}

.search {
  min-width: 16rem;
  flex: 1 1 16rem;
}

.search :deep(input) {
  width: 100%;
}

.filtre {
  min-width: 11rem;
  max-width: 18rem;
}

.field,
.tri {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-1);
  font-size: 0.85rem;
}

.tri {
  flex-direction: row;
  align-items: center;
  gap: var(--sy-space-2);
}

.summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sy-space-3);
}

.nouveau {
  order: 10;
  margin-left: auto;
  gap: var(--sy-space-2);
  text-decoration: none;
}

.lien {
  color: var(--sy-text);
  text-decoration: none;
  font-weight: 600;
}

.lien:hover {
  text-decoration: underline;
}

.bloc {
  display: block;
  font-size: 0.8rem;
}

.nowrap,
.agents :deep(.p-tag) {
  white-space: nowrap;
}

.empty {
  margin: 0;
}

/* Narrow screens: the table scrolls inside the card instead of being cut. */
.agents :deep(.p-datatable-table-container) {
  overflow-x: auto;
}
</style>
