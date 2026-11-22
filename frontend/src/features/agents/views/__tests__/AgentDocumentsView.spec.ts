import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { createMemoryHistory, createRouter } from 'vue-router'

import * as api from '@/features/agents/api/agents'
import * as documentsApi from '@/features/agents/api/documents'
import * as evenementsApi from '@/features/agents/api/evenements'
import { ApiError } from '@/shared/utils/http'

import AgentDocumentsView from '../AgentDocumentsView.vue'

vi.mock('@/features/agents/api/agents')
vi.mock('@/features/agents/api/documents', async (original) => ({
  ...(await original<typeof documentsApi>()),
  listDocuments: vi.fn<typeof documentsApi.listDocuments>(),
}))
vi.mock('@/features/agents/api/evenements', async (original) => ({
  ...(await original<typeof evenementsApi>()),
  listEvenements: vi.fn<typeof evenementsApi.listEvenements>(),
}))
vi.mock('@/features/referentiels/api/referentiels')

const AGENT = {
  id: 7,
  matricule: 'ARPTC/0001/2008',
  nom: 'Mukendi',
  postnom: '',
  prenom: 'Patrick',
}

async function mountAt(url: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/agents/pieces', component: AgentDocumentsView }],
  })
  await router.push(url)
  await router.isReady()
  const wrapper = mount(AgentDocumentsView, {
    global: { plugins: [PrimeVue, ToastService, router], stubs: { teleport: true } },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

describe('AgentDocumentsView picker', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.stubGlobal(
      'matchMedia',
      vi.fn<() => Partial<MediaQueryList>>(() => ({
        matches: false,
        addEventListener: vi.fn<MediaQueryList['addEventListener']>(),
        removeEventListener: vi.fn<MediaQueryList['removeEventListener']>(),
      })),
    )
    setActivePinia(createPinia())
    vi.mocked(documentsApi.listDocuments).mockResolvedValue([])
    vi.mocked(evenementsApi.listEvenements).mockResolvedValue([])
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    document.body.innerHTML = ''
  })

  it('restores ?agent= by loading that agent', async () => {
    vi.mocked(api.fetchAgent).mockResolvedValue(AGENT)
    const wrapper = await mountAt('/agents/pieces?agent=7')
    expect(api.fetchAgent).toHaveBeenCalledWith(7)
    expect(wrapper.find('.title').text()).toBe('ARPTC/0001/2008 — Mukendi Patrick')
    expect(api.searchAgents).not.toHaveBeenCalled()
  })

  it('shows the empty state for an unknown agent', async () => {
    vi.mocked(api.fetchAgent).mockRejectedValue(new ApiError(404, 'Introuvable'))
    const wrapper = await mountAt('/agents/pieces?agent=999')
    expect(wrapper.find('[data-test="agents-vide"]').exists()).toBe(true)
  })

  it('searches the server as the user types, every status', async () => {
    vi.mocked(api.searchAgents).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [AGENT],
    })
    const wrapper = await mountAt('/agents/pieces')
    wrapper.findComponent({ name: 'AutoComplete' }).vm.$emit('complete', { query: 'muk' })
    await flushPromises()
    expect(api.searchAgents).toHaveBeenCalledWith({ q: 'muk', taille: 20 })
    expect(wrapper.findComponent({ name: 'AutoComplete' }).props('suggestions')).toEqual([AGENT])
  })
})
