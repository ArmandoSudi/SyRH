import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'

import * as api from '@/features/referentiels/api/referentiels'
import type {
  Categorie,
  Echelon,
  Grade,
  Site,
  Unite,
} from '@/features/referentiels/api/referentiels'
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
    type_libelle: {
      direction: 'Direction',
      departement: 'Département',
      service: 'Service',
      bureau: 'Bureau',
    }[type],
    parent,
    site: SITE,
    date_ouverture: '2015-01-01',
    date_fermeture: null,
  } satisfies Unite
}

const SITES: Site[] = [
  { ...SITE, ville: 'Kinshasa', siege: true, date_fermeture: null },
  {
    id: 2,
    code: 'LUB',
    nom: 'Lubumbashi',
    ville: 'Lubumbashi',
    siege: false,
    date_fermeture: null,
  },
]

const PERIODE = { date_ouverture: '2015-01-01', date_fermeture: null }
const CATEGORIES: Categorie[] = [
  { id: 1, code: 'AM', nom: 'Agents de maîtrise', rang: 2, ...PERIODE },
  { id: 2, code: 'CD', nom: 'Cadres de direction', rang: 4, ...PERIODE },
]
const GRADES: Grade[] = [
  { id: 1, code: 'DIR', nom: 'Directeur', categorie: 2, rang: 2, ...PERIODE },
  { id: 2, code: 'AGM', nom: 'Agent de maîtrise', categorie: 1, rang: 1, ...PERIODE },
]
const ECHELONS: Echelon[] = [
  { id: 1, grade: 1, numero: 1, libelle: 'DIR — Échelon 1', ...PERIODE },
  { id: 2, grade: 1, numero: 2, libelle: 'DIR — Échelon 2', ...PERIODE },
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
  return wrapper
    .findAll('[data-test="tree"] tbody tr')
    .map((tr) => tr.findAll('td').map((td) => td.text()))
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
    vi.mocked(api.fetchCategories).mockResolvedValue(CATEGORIES)
    vi.mocked(api.fetchGrades).mockResolvedValue(GRADES)
    vi.mocked(api.fetchEchelons).mockResolvedValue(ECHELONS)
  })

  it('shows the organisation of today as a tree', async () => {
    const wrapper = await mountView()

    expect(api.fetchUnites).toHaveBeenCalledWith({ date: localDate(new Date()) })
    expect(rows(wrapper)).toEqual([
      [
        'Direction des Ressources humaines',
        'DRH',
        'Direction',
        'Siège — Kinshasa',
        '01/01/2015',
        '—',
      ],
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
    const cells = wrapper
      .findAll('[data-test="sites"] tbody tr')
      .map((tr) => tr.findAll('td').map((td) => td.text()))
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

  describe('classification tab', () => {
    function grid(wrapper: Awaited<ReturnType<typeof mountView>>) {
      return wrapper
        .findAll('[data-test="classification"] tbody tr')
        .map((tr) => tr.findAll('td').map((td) => td.text()))
    }

    beforeEach(() => {
      useReferentielsStore().onglet = 'classification'
    })

    it('shows the grid of today, highest catégorie first', async () => {
      const wrapper = await mountView()

      const today = { date: localDate(new Date()) }
      expect(api.fetchCategories).toHaveBeenCalledWith(today)
      expect(api.fetchGrades).toHaveBeenCalledWith(today)
      expect(api.fetchEchelons).toHaveBeenCalledWith(today)
      expect(api.fetchUnites).not.toHaveBeenCalled()
      expect(grid(wrapper)).toEqual([
        ['Cadres de direction', 'CD', 'Catégorie', '4', '01/01/2015', '—'],
        ['Agents de maîtrise', 'AM', 'Catégorie', '2', '01/01/2015', '—'],
      ])

      await wrapper.get('[data-test="classification-expand-all"]').trigger('click')
      expect(grid(wrapper).map((r) => [r[0], r[2]])).toEqual([
        ['Cadres de direction', 'Catégorie'],
        ['Directeur', 'Grade'],
        ['Échelon 1', 'Échelon'],
        ['Échelon 2', 'Échelon'],
        ['Agents de maîtrise', 'Catégorie'],
        ['Agent de maîtrise', 'Grade'],
      ])

      await wrapper.get('[data-test="classification-collapse-all"]').trigger('click')
      expect(grid(wrapper)).toHaveLength(2)
      wrapper.unmount()
    })

    it('filters on a grade code, keeping its catégorie and its échelons', async () => {
      const wrapper = await mountView()

      await wrapper.get('[data-test="classification-search"]').setValue('dir')

      expect(grid(wrapper).map((r) => r[0])).toEqual([
        'Cadres de direction',
        'Directeur',
        'Échelon 1',
        'Échelon 2',
      ])
      wrapper.unmount()
    })

    it('reloads the grid at the chosen date, leaving the organisation date alone', async () => {
      const wrapper = await mountView()
      const store = useReferentielsStore()

      store.classification.date = new Date(2024, 11, 31)
      await flushPromises()

      for (const fetch of [api.fetchCategories, api.fetchGrades, api.fetchEchelons]) {
        expect(fetch).toHaveBeenLastCalledWith({ date: '2024-12-31' })
      }
      expect(localDate(store.date)).toBe(localDate(new Date()))
      wrapper.unmount()
    })

    it('shows an error when the grid cannot be loaded', async () => {
      vi.mocked(api.fetchGrades).mockRejectedValue(new Error('API responded with HTTP 502'))

      const wrapper = await mountView()

      expect(wrapper.get('[data-test="classification-error"]').text()).toContain('HTTP 502')
      expect(grid(wrapper).join(' ')).toContain('Aucune catégorie à cette date.')
      wrapper.unmount()
    })

    it('offers no action that changes data', async () => {
      const wrapper = await mountView()

      const labels = wrapper.findAll('button').map((b) => b.attributes('aria-label') ?? b.text())
      expect(labels.join(' ')).not.toMatch(/ajouter|créer|supprimer|modifier|enregistrer|fermer/i)
      wrapper.unmount()
    })
  })
})
