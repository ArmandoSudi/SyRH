<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AutoComplete, { type AutoCompleteCompleteEvent } from 'primevue/autocomplete'
import Message from 'primevue/message'

import { fetchAgent, searchAgents, type AgentResume } from '@/features/agents/api/agents'
import DocumentsPanel from '@/features/agents/components/DocumentsPanel.vue'
import EvenementsPanel from '@/features/agents/components/EvenementsPanel.vue'
import { agentLibelle } from '@/features/agents/components/documents'
import { ApiError } from '@/shared/utils/http'

/**
 * "Pièces des agents" (document storage D21): pick an agent, then their documents and
 * events. The agent is kept in the URL (?agent=), so a refresh, a shared link or a row of
 * the agent list lands on the same file. The picker searches the server as the user
 * types, every status included (agent list D17). Temporary: roadmap 2.10 mounts the
 * panels on the agent's page.
 */
const route = useRoute()
const router = useRouter()

const suggestions = ref<AgentResume[]>([])
const choisi = ref<AgentResume | string | null>(null)
const loading = ref(true)
// Each section reloads when the other changed the agent's documents.
const versionDocuments = ref(0)
const versionEvenements = ref(0)
const error = ref<string | null>(null)

const agent = computed(() =>
  choisi.value && typeof choisi.value === 'object' ? choisi.value : null,
)

async function charger(query: unknown) {
  const wanted = Number(query)
  if (!Number.isInteger(wanted) || wanted <= 0) {
    choisi.value = null
    loading.value = false
    return
  }
  if (agent.value?.id === wanted) return
  loading.value = true
  error.value = null
  try {
    choisi.value = await fetchAgent(wanted)
  } catch (e) {
    choisi.value = null
    if (!(e instanceof ApiError && e.status === 404)) {
      error.value = e instanceof Error ? e.message : String(e)
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => void charger(route.query.agent))
watch(
  () => route.query.agent,
  (value) => void charger(value),
)

let latest = 0
async function complete(event: AutoCompleteCompleteEvent) {
  const call = ++latest
  try {
    const page = await searchAgents({ q: event.query, taille: 20 })
    if (call === latest) suggestions.value = page.results
  } catch {
    if (call === latest) suggestions.value = []
  }
}

function select() {
  if (agent.value) void router.replace({ query: { agent: String(agent.value.id) } })
}

function clear() {
  void router.replace({ query: {} })
}
</script>

<template>
  <div class="page">
    <div class="picker">
      <label for="agent-picker" class="sy-muted">Agent</label>
      <AutoComplete
        v-model="choisi"
        input-id="agent-picker"
        :suggestions="suggestions"
        :option-label="agentLibelle"
        force-selection
        :disabled="loading"
        placeholder="Matricule ou nom de l'agent"
        class="autocomplete"
        data-test="agent-picker"
        @complete="complete"
        @option-select="select"
        @clear="clear"
      />
    </div>

    <Message v-if="error" severity="error" :closable="false" data-test="agents-error">
      Les agents n'ont pas pu être chargés : {{ error }}
    </Message>

    <div v-if="agent" class="sy-card card">
      <h2 class="title">{{ agentLibelle(agent) }}</h2>
      <DocumentsPanel
        :key="`d-${agent.id}`"
        :agent-id="agent.id"
        :version="versionDocuments"
        @change="versionEvenements++"
      />
      <EvenementsPanel
        :key="`e-${agent.id}`"
        :agent-id="agent.id"
        :version="versionEvenements"
        @change="versionDocuments++"
      />
    </div>
    <p v-else-if="!loading && !error" class="sy-muted" data-test="agents-vide">
      Choisissez un agent pour voir ses pièces justificatives.
    </p>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-4);
}

.picker {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-1);
  max-width: 32rem;
  font-size: 0.85rem;
}

.autocomplete,
.autocomplete :deep(input) {
  width: 100%;
}

.card {
  padding: var(--sy-space-5);
}

.title {
  margin: 0 0 var(--sy-space-4);
  font-size: 1.1rem;
}
</style>
