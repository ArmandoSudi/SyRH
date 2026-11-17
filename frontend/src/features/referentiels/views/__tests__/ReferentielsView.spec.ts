import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'

import * as api from '@/features/referentiels/api/referentiels'
import type { Site, Unite } from '@/features/referentiels/api/referentiels'
import { useReferentielsStore } from '@/features/referentiels/stores/referentiels'
import { localDate } from '@/shared/utils/dates'

import ReferentielsView from '../ReferentielsView.vue'

vi.mock('@/features/referentiels/api/referentiels')

const SITE = { id: 1, code: 'KIN', nom: 'Siège — Kinshasa' }

function unite(id: number, code: string, type: Unite['type'], parent: number | null, nom: string) {
  return {
    id,
    code,
    nom,
    type,
    type_libelle: { direction: 'Direction', departement: 'Département', service: 'Service', bureau: 'Bureau' }[type],
    parent,
    site: SITE,
    date_ouverture: '2015-01-01',
    date_fermeture: null,
  } satisfies Unite
}

const SITES: Site[] = [
  { ...SITE, ville: 'Kinshasa', siege: true, date_fermeture: null },
  { id: 2, code: 'LUB', nom: 'Lubumbashi', ville: 'Lubumbashi', siege: false, date_fermeture: null },
]

async function mountView() {
  const wrapper = mount(ReferentielsView, {
    global: { plugins: [PrimeVue], stubs: { teleport: true } },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

function rows(wrapper: Awaited<ReturnType<typeof mountView>>) {
  return wrapper.findAll('[data-test="tree"] tbody tr').map((tr) =>
    tr.findAll('td').map((td) => td.text()),
  )
}

describe('ReferentielsView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  beforeEach(() => {
    vi.resetAllMocks()
    // jsdom has no matchMedia; PrimeVue's DatePicker listens to it for its layout.
    vi.stubGlobal(
      'matchMedia',
      vi.fn<() => Partial<MediaQueryList>>(() => ({
        matches: false,
        addEventListener: vi.fn<MediaQueryList['addEventListener']>(),
        removeEventListener: vi.fn<MediaQueryList['removeEventListener']>(),
      })),
    )
    // Nor ResizeObserver, which PrimeVue's tab list uses for its ink bar.
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      },
    )
    setActivePinia(createPinia())
    vi.mocked(api.fetchUnites).mockResolvedValue([
      unite(1, 'DRH', 'direction', null, 'Direction des Ressources humaines'),
      unite(2, 'DRH-FOR', 'service', 1, 'Service Formation'),
      unite(3, 'DT', 'direction', null, 'Direction technique'),
    ])
    vi.mocked(api.fetchSites).mockResolvedValue(SITES)
  })

  it('shows the organisation of today as a tree', async () => {
    const wrapper = await mountView()

    expect(api.fetchUnites).toHaveBeenCalledWith({ date: localDate(new Date()) })
    expect(rows(wrapper)).toEqual([
      ['Direction des Ressources humaines', 'DRH', 'Direction', 'Siège — Kinshasa', '01/01/2015', '—'],
      ['Direction technique', 'DT', 'Direction', 'Siège — Kinshasa', '01/01/2015', '—'],
    ])

    await wrapper.get('[data-test="expand-all"]').trigger('click')
    expect(rows(wrapper).map((r) => r[1])).toEqual(['DRH', 'DRH-FOR', 'DT'])

    await wrapper.get('[data-test="collapse-all"]').trigger('click')
    expect(rows(wrapper).map((r) => r[1])).toEqual(['DRH', 'DT'])
    wrapper.unmount()
  })

  it('filters on code or name, keeping the ancestors open', async () => {
    const wrapper = await mountView()

    await wrapper.get('[data-test="search"]').setValue('formation')

    expect(rows(wrapper).map((r) => r[1])).toEqual(['DRH', 'DRH-FOR'])
    wrapper.unmount()
  })

  it('reloads the tree at the chosen date', async () => {
    const wrapper = await mountView()

    useReferentielsStore().date = new Date(2025, 5, 30)
    await flushPromises()

    expect(api.fetchUnites).toHaveBeenLastCalledWith({ date: '2025-06-30' })
    wrapper.unmount()
  })

  it('shows an error when the organisation cannot be loaded', async () => {
    vi.mocked(api.fetchUnites).mockRejectedValue(new Error('API responded with HTTP 502'))

    const wrapper = await mountView()

    expect(wrapper.get('[data-test="error"]').text()).toContain('HTTP 502')
    wrapper.unmount()
  })

  it('lists the sites and asks for closed ones on request', async () => {
    useReferentielsStore().onglet = 'sites'
    const wrapper = await mountView()

    expect(api.fetchSites).toHaveBeenCalledWith({ toutes: false })
    const cells = wrapper.findAll('[data-test="sites"] tbody tr').map((tr) =>
      tr.findAll('td').map((td) => td.text()),
    )
    expect(cells).toEqual([
      ['KIN', 'Siège — Kinshasa', 'Kinshasa', 'Siège', 'Ouvert'],
      ['LUB', 'Lubumbashi', 'Lubumbashi', '', 'Ouvert'],
    ])

    useReferentielsStore().sitesFermes = true
    await flushPromises()
    expect(api.fetchSites).toHaveBeenLastCalledWith({ toutes: true })
    wrapper.unmount()
  })

  it('offers no action that changes data', async () => {
    const wrapper = await mountView()

    const labels = wrapper.findAll('button').map((b) => b.attributes('aria-label') ?? b.text())
    expect(labels.join(' ')).not.toMatch(/ajouter|créer|supprimer|modifier|enregistrer|fermer/i)
    wrapper.unmount()
  })
})
