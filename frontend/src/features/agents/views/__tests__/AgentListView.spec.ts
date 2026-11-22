import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import * as api from '@/features/agents/api/agents'
import type { AgentResume } from '@/features/agents/api/agents'
import { useAgentListStore } from '@/features/agents/stores/agentList'
import * as referentiels from '@/features/referentiels/api/referentiels'
import { ApiError } from '@/shared/utils/http'

import AgentListView from '../AgentListView.vue'

vi.mock('@/features/agents/api/agents', async (original) => ({
  ...(await original<typeof api>()),
  searchAgents: vi.fn<typeof api.searchAgents>(),
}))
vi.mock('@/features/referentiels/api/referentiels')

const MUKENDI: AgentResume = {
  id: 7,
  matricule: 'ARPTC/0001/2008',
  nom: 'Mukendi',
  postnom: 'Kalonji',
  prenom: 'Patrick',
  statut: 'actif',
  statut_libelle: 'En activité',
  affectation_actuelle: {
    id: 1,
    unite: 2,
    unite_code: 'DRH',
    unite_nom: 'Direction des Ressources humaines',
    fonction: 3,
    fonction_code: 'DIR',
    fonction_nom: 'Directeur',
    date_effet: '2015-01-01',
  },
  classement_actuel: {
    id: 1,
    echelon: 4,
    echelon_numero: 3,
    grade: 5,
    grade_code: 'DIR',
    grade_nom: 'Directeur',
    date_effet: '2015-01-01',
  },
}

function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/agents', name: 'agents', component: AgentListView },
      { path: '/agents/pieces', name: 'agents-pieces', component: { template: '<div />' } },
    ],
  })
}

async function mountAt(url: string) {
  const router = makeRouter()
  await router.push(url)
  await router.isReady()
  const wrapper = mount(AgentListView, {
    global: { plugins: [PrimeVue, router], stubs: { teleport: true } },
    attachTo: document.body,
  })
  await flushPromises()
  return { wrapper, router }
}

function lastCall() {
  return vi.mocked(api.searchAgents).mock.lastCall![0]
}

describe('AgentListView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.stubGlobal(
      'matchMedia',
      vi.fn<() => Partial<MediaQueryList>>(() => ({
        matches: false,
        addEventListener: vi.fn<MediaQueryList['addEventListener']>(),
        removeEventListener: vi.fn<MediaQueryList['removeEventListener']>(),
      })),
    )
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      },
    )
    setActivePinia(createPinia())
    vi.mocked(api.searchAgents).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [MUKENDI],
    })
    vi.mocked(referentiels.fetchUnites).mockResolvedValue([])
    vi.mocked(referentiels.fetchGrades).mockResolvedValue([])
    vi.mocked(referentiels.fetchFonctions).mockResolvedValue([])
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    document.body.innerHTML = ''
  })

  it('asks for the agents En activité by default and shows them', async () => {
    const { wrapper } = await mountAt('/agents')
    expect(lastCall()).toMatchObject({ statut: ['actif'], page: 1, tri: 'nom', taille: 25 })
    const cells = wrapper.findAll('[data-test="agents"] tbody tr td').map((td) => td.text())
    expect(cells).toEqual([
      'ARPTC/0001/2008',
      'Mukendi Kalonji Patrick',
      'DRHDirection des Ressources humaines',
      'Directeur',
      'DIR · éch. 3',
      'En activité',
    ])
    expect(wrapper.find('[data-test="agents-count"]').text()).toBe('1 agent')
  })

  it('reads its filters from the URL', async () => {
    vi.mocked(api.searchAgents).mockResolvedValue({
      count: 60,
      next: null,
      previous: null,
      results: [MUKENDI],
    })
    await mountAt('/agents?q=kab&unite=3&statut=tous&date=2018-01-01&tri=matricule&page=2')
    expect(lastCall()).toMatchObject({
      q: 'kab',
      unite: 3,
      statut: [],
      date: '2018-01-01',
      tri: 'matricule',
      page: 2,
    })
  })

  it('searches the typed text after a pause and writes it to the URL', async () => {
    const { wrapper, router } = await mountAt('/agents')
    await wrapper.find('[data-test="agents-q"]').setValue('muk')
    vi.advanceTimersByTime(350)
    await flushPromises()
    expect(lastCall()).toMatchObject({ q: 'muk', page: 1 })
    expect(router.currentRoute.value.query).toEqual({ q: 'muk' })
    expect(useAgentListStore().filtres.q).toBe('muk')
  })

  it('keeps the search in the store when coming back without a query', async () => {
    useAgentListStore().remplacer({
      q: 'nsimba',
      unite: null,
      grade: null,
      fonction: null,
      statut: ['actif'],
      date: null,
      tri: 'nom',
      page: 1,
    })
    const { router } = await mountAt('/agents')
    expect(lastCall()).toMatchObject({ q: 'nsimba' })
    expect(router.currentRoute.value.query).toEqual({ q: 'nsimba' })
  })

  it('clears the filters back to the default', async () => {
    const { wrapper, router } = await mountAt('/agents?q=kab&statut=tous')
    await wrapper.find('[data-test="agents-effacer"]').trigger('click')
    await flushPromises()
    expect(lastCall()).toMatchObject({ q: '', statut: ['actif'] })
    expect(router.currentRoute.value.query).toEqual({})
  })

  it('links each row to the agent documents page', async () => {
    const { wrapper } = await mountAt('/agents')
    expect(wrapper.find('[data-test="agents-nom"]').attributes('href')).toBe(
      '/agents/pieces?agent=7',
    )
  })

  it('pages through the results', async () => {
    vi.mocked(api.searchAgents).mockResolvedValue({
      count: 60,
      next: '/api/agents/?page=2',
      previous: null,
      results: [MUKENDI],
    })
    const { wrapper, router } = await mountAt('/agents')
    await wrapper.find('.p-paginator-next').trigger('click')
    await flushPromises()
    expect(lastCall()).toMatchObject({ page: 2 })
    expect(router.currentRoute.value.query).toEqual({ page: '2' })
  })

  it('goes back to page 1 when the page no longer exists', async () => {
    vi.mocked(api.searchAgents)
      .mockRejectedValueOnce(new ApiError(404, 'Page non valide.'))
      .mockResolvedValue({ count: 1, next: null, previous: null, results: [MUKENDI] })
    const { router, wrapper } = await mountAt('/agents?page=5')
    expect(lastCall()).toMatchObject({ page: 1 })
    expect(router.currentRoute.value.query).toEqual({})
    expect(wrapper.find('[data-test="agents-error"]').exists()).toBe(false)
  })

  it('shows the empty and error states', async () => {
    vi.mocked(api.searchAgents).mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    })
    let { wrapper } = await mountAt('/agents?q=zzz')
    expect(wrapper.text()).toContain('Aucun agent ne correspond à cette recherche.')
    wrapper.unmount()
    vi.mocked(api.searchAgents).mockRejectedValue(new ApiError(500, 'Erreur du serveur'))
    ;({ wrapper } = await mountAt('/agents'))
    expect(wrapper.find('[data-test="agents-error"]').text()).toContain('Erreur du serveur')
  })
})
