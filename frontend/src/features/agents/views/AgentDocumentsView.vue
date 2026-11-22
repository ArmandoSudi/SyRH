<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AutoComplete, { type AutoCompleteCompleteEvent } from 'primevue/autocomplete'
import Message from 'primevue/message'

import { fetchAgents, type AgentResume } from '@/features/agents/api/agents'
import DocumentsPanel from '@/features/agents/components/DocumentsPanel.vue'
import EvenementsPanel from '@/features/agents/components/EvenementsPanel.vue'
import { agentLibelle, filterAgents } from '@/features/agents/components/documents'

/**
 * "Pièces des agents" (document storage D21): pick an agent, then their documents
 * panel. The agent is kept in the URL (?agent=), so a refresh or a shared link lands
 * on the same file. Temporary: roadmap 2.10 mounts the panel on the agent's page.
 */
const route = useRoute()
const router = useRouter()

const agents = ref<AgentResume[]>([])
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

onMounted(async () => {
  try {
    agents.value = await fetchAgents()
    const wanted = Number(route.query.agent)
    choisi.value = agents.value.find((a) => a.id === wanted) ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

function complete(event: AutoCompleteCompleteEvent) {
  suggestions.value = filterAgents(agents.value, event.query).slice(0, 20)
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
