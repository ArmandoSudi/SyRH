import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

import { useAuthStore } from '@/features/auth/stores/auth'
import * as editionApi from '@/features/referentiels/api/edition'
import * as api from '@/features/referentiels/api/referentiels'
import type {
  Banque,
  Categorie,
  Echelon,
  Fonction,
  Grade,
  MotifSortie,
  Parametre,
  PieceRequise,
  TypeContrat,
  TypeDocument,
  TypeSuspension,
  Site,
  Unite,
} from '@/features/referentiels/api/referentiels'
import { useReferentielsStore } from '@/features/referentiels/stores/referentiels'
import { localDate } from '@/shared/utils/dates'

import ReferentielsView from '../ReferentielsView.vue'

vi.mock('@/features/referentiels/api/referentiels')
vi.mock('@/features/referentiels/api/edition')

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

const FONCTIONS: Fonction[] = [
  {
    id: 1,
    code: 'CS',
    nom: 'Chef de service',
    nature: 'responsabilite',
    nature_libelle: 'Responsabilité',
    ...PERIODE,
  },
  {
    id: 2,
    code: 'CE',
    nom: 'Analyste régulation',
    nature: 'execution',
    nature_libelle: 'Exécution',
    date_ouverture: '2024-01-01',
    date_fermeture: null,
  },
  {
    id: 3,
    code: 'JUR',
    nom: 'Juriste',
    nature: 'execution',
    nature_libelle: 'Exécution',
    ...PERIODE,
  },
]

const TYPES: TypeContrat[] = [
  {
    id: 1,
    code: 'CDD',
    nom: 'Contrat à durée déterminée',
    duree_determinee: true,
    periode_essai: true,
    ...PERIODE,
  },
  {
    id: 2,
    code: 'CDI',
    nom: 'Contrat à durée indéterminée',
    duree_determinee: false,
    periode_essai: true,
    ...PERIODE,
  },
  { id: 3, code: 'STG', nom: 'Stage', duree_determinee: true, periode_essai: false, ...PERIODE },
]

const TYPES_DOCUMENT: TypeDocument[] = [
  { id: 1, code: 'CTR', nom: 'Contrat signé', confidentiel: false, groupes_autorises: [], groupes_autorises_noms: [], ...PERIODE },
  { id: 2, code: 'DEC', nom: 'Décision', confidentiel: false, groupes_autorises: [], groupes_autorises_noms: [], ...PERIODE },
]
const PIECES: PieceRequise[] = [
  {
    id: 1,
    evenement: 'engagement',
    evenement_libelle: 'Engagement',
    type_document: 1,
    obligatoire: true,
    ...PERIODE,
  },
  {
    id: 2,
    evenement: 'promotion',
    evenement_libelle: 'Promotion',
    type_document: 2,
    obligatoire: true,
    ...PERIODE,
  },
  {
    id: 3,
    evenement: 'formation',
    evenement_libelle: 'Formation',
    type_document: 2,
    obligatoire: false,
    ...PERIODE,
  },
]

const MOTIFS: MotifSortie[] = [
  {
    id: 1,
    code: 'DCD',
    nom: 'Décès',
    type_document: 7,
    type_document_libelle: 'ADC — Acte de décès',
    retraite: false,
    deces: true,
    ...PERIODE,
  },
  {
    id: 2,
    code: 'DEM',
    nom: 'Démission',
    type_document: 8,
    type_document_libelle: 'LDM — Lettre de démission',
    retraite: false,
    deces: false,
    ...PERIODE,
  },
  {
    id: 3,
    code: 'RET-ANC',
    nom: 'Retraite pour ancienneté',
    type_document: 9,
    type_document_libelle: 'DRT — Décision de retraite',
    retraite: true,
    deces: false,
    ...PERIODE,
  },
]
const SUSPENSIONS: TypeSuspension[] = [
  {
    id: 1,
    code: 'DETA',
    nom: 'Détachement',
    type_document: 2,
    type_document_libelle: 'DEC — Décision',
    compte_anciennete: true,
    duree_max_mois: null,
    renouvellements_max: null,
    ...PERIODE,
  },
  {
    id: 2,
    code: 'DISPO',
    nom: 'Mise en disponibilité',
    type_document: 2,
    type_document_libelle: 'DEC — Décision',
    compte_anciennete: false,
    duree_max_mois: 24,
    renouvellements_max: 1,
    ...PERIODE,
  },
]

const BANQUES: Banque[] = [
  { id: 1, code: 'BCF', nom: 'Banque Commerciale du Fleuve', swift: 'BCFLCDKI', ...PERIODE },
  { id: 2, code: 'TRC', nom: 'Trésor Crédit', swift: '', ...PERIODE },
  {
    id: 3,
    code: 'UBK',
    nom: 'Union Bank Kivu-Kasaï',
    swift: 'UBKKCDKI',
    date_ouverture: '2022-01-01',
    date_fermeture: null,
  },
]

const PARAMETRES: Parametre[] = [
  {
    id: 1,
    cle: 'age_limite_enfant',
    cle_libelle: 'Âge limite des enfants à charge',
    unite: 'ans',
    valeur: 25,
    ...PERIODE,
  },
  {
    id: 2,
    cle: 'age_retraite',
    cle_libelle: 'Âge de la retraite',
    unite: 'ans',
    valeur: 65,
    ...PERIODE,
  },
]

async function mountView() {
  const wrapper = mount(ReferentielsView, {
    global: { plugins: [PrimeVue, ToastService], stubs: { teleport: true } },
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
    vi.mocked(api.fetchFonctions).mockResolvedValue(FONCTIONS)
    vi.mocked(api.fetchTypesContrat).mockResolvedValue(TYPES)
    vi.mocked(api.fetchTypesDocument).mockResolvedValue(TYPES_DOCUMENT)
    vi.mocked(api.fetchPiecesRequises).mockResolvedValue(PIECES)
    vi.mocked(api.fetchMotifsSortie).mockResolvedValue(MOTIFS)
    vi.mocked(api.fetchTypesSuspension).mockResolvedValue(SUSPENSIONS)
    vi.mocked(api.fetchBanques).mockResolvedValue(BANQUES)
    vi.mocked(api.fetchParametres).mockResolvedValue(PARAMETRES)
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

  describe('fonctions tab', () => {
    function table(wrapper: Awaited<ReturnType<typeof mountView>>) {
      return wrapper
        .findAll('[data-test="fonctions"] tbody tr')
        .map((tr) => tr.findAll('td').map((td) => td.text()))
    }

    beforeEach(() => {
      useReferentielsStore().onglet = 'fonctions'
    })

    it('comes after the classification tab', async () => {
      const wrapper = await mountView()
      const tabs = wrapper.findAll('[role="tab"]').map((tab) => tab.text())
      expect(tabs.slice(0, 4)).toEqual(['Organisation', 'Sites', 'Classification', 'Fonctions'])
    })

    it('lists the fonctions of today, in the order of the API, with their nature', async () => {
      const wrapper = await mountView()

      expect(api.fetchFonctions).toHaveBeenCalledWith({ date: localDate(new Date()) })
      expect(table(wrapper)).toEqual([
        ['CS', 'Chef de service', 'Responsabilité', '01/01/2015', '—'],
        ['CE', 'Analyste régulation', 'Exécution', '01/01/2024', '—'],
        ['JUR', 'Juriste', 'Exécution', '01/01/2015', '—'],
      ])
      expect(wrapper.find('[data-test="fonctions"] .p-tag').exists()).toBe(true)
    })

    it('filters on code or name', async () => {
      const wrapper = await mountView()

      await wrapper.get('[data-test="fonctions-search"]').setValue('regulation')
      expect(table(wrapper).map((row) => row[0])).toEqual(['CE'])

      await wrapper.get('[data-test="fonctions-search"]').setValue('pilote')
      expect(wrapper.get('[data-test="fonctions"]').text()).toContain(
        'Aucune fonction ne correspond à cette recherche.',
      )
    })

    it('reloads at the chosen date, leaving the other dates alone', async () => {
      await mountView()
      const store = useReferentielsStore()

      store.fonctions.date = new Date(2023, 11, 31)
      await flushPromises()

      expect(api.fetchFonctions).toHaveBeenLastCalledWith({ date: '2023-12-31' })
      expect(localDate(store.date)).toBe(localDate(new Date()))
      expect(localDate(store.classification.date)).toBe(localDate(new Date()))
    })

    it('shows an error when the fonctions cannot be loaded', async () => {
      vi.mocked(api.fetchFonctions).mockRejectedValue(new Error('HTTP 502'))
      const wrapper = await mountView()

      expect(wrapper.get('[data-test="fonctions-error"]').text()).toContain('HTTP 502')
      expect(table(wrapper)).toEqual([['Aucune fonction à cette date.']])
    })

    it('offers no action that changes data', async () => {
      const wrapper = await mountView()
      const panel = wrapper.get('[data-test="fonctions"]')
      expect(panel.findAll('button')).toHaveLength(0)
    })
  })

  describe('contract types tab', () => {
    function table(wrapper: Awaited<ReturnType<typeof mountView>>) {
      return wrapper
        .findAll('[data-test="types-contrat"] tbody tr')
        .map((tr) => tr.findAll('td').map((td) => td.text()))
    }

    beforeEach(() => {
      useReferentielsStore().onglet = 'typesContrat'
    })

    it('comes after the fonctions tab', async () => {
      const wrapper = await mountView()
      const tabs = wrapper.findAll('[role="tab"]').map((tab) => tab.text())
      expect(tabs.slice(0, 5)).toEqual([
        'Organisation',
        'Sites',
        'Classification',
        'Fonctions',
        'Types de contrat',
      ])
    })

    it('lists the types of today with their rules as Oui or Non', async () => {
      const wrapper = await mountView()

      expect(api.fetchTypesContrat).toHaveBeenCalledWith({ date: localDate(new Date()) })
      expect(table(wrapper)).toEqual([
        ['CDD', 'Contrat à durée déterminée', 'Oui', 'Oui', '01/01/2015', '—'],
        ['CDI', 'Contrat à durée indéterminée', 'Non', 'Oui', '01/01/2015', '—'],
        ['STG', 'Stage', 'Oui', 'Non', '01/01/2015', '—'],
      ])
    })

    it('filters on code or name, ignoring accents', async () => {
      const wrapper = await mountView()

      await wrapper.get('[data-test="types-contrat-search"]').setValue('indetermin')
      expect(table(wrapper).map((row) => row[0])).toEqual(['CDI'])

      await wrapper.get('[data-test="types-contrat-search"]').setValue('pilote')
      expect(wrapper.get('[data-test="types-contrat"]').text()).toContain(
        'Aucun type ne correspond à cette recherche.',
      )
    })

    it('reloads at the chosen date, leaving the other dates alone', async () => {
      await mountView()
      const store = useReferentielsStore()

      store.typesContrat.date = new Date(2022, 5, 1)
      await flushPromises()

      expect(api.fetchTypesContrat).toHaveBeenLastCalledWith({ date: '2022-06-01' })
      expect(localDate(store.fonctions.date)).toBe(localDate(new Date()))
      expect(localDate(store.classification.date)).toBe(localDate(new Date()))
    })

    it('shows an error when the types cannot be loaded', async () => {
      vi.mocked(api.fetchTypesContrat).mockRejectedValue(new Error('HTTP 502'))
      const wrapper = await mountView()

      expect(wrapper.get('[data-test="types-contrat-error"]').text()).toContain('HTTP 502')
      expect(table(wrapper)).toEqual([['Aucun type de contrat à cette date.']])
    })

    it('offers no action that changes data', async () => {
      const wrapper = await mountView()
      expect(wrapper.get('[data-test="types-contrat"]').findAll('button')).toHaveLength(0)
    })
  })

  describe('documents tab', () => {
    function tree(wrapper: Awaited<ReturnType<typeof mountView>>) {
      return wrapper
        .findAll('[data-test="pieces"] tbody tr')
        .map((tr) => tr.findAll('td').map((td) => td.text()))
    }

    beforeEach(() => {
      useReferentielsStore().onglet = 'pieces'
    })

    it('comes after the contract types tab', async () => {
      const wrapper = await mountView()
      const tabs = wrapper.findAll('[role="tab"]').map((tab) => tab.text())
      expect(tabs.slice(4, 6)).toEqual(['Types de contrat', 'Pièces justificatives'])
    })

    it('lists every event of today with its count, and opens to its documents', async () => {
      const wrapper = await mountView()

      const today = { date: localDate(new Date()) }
      expect(api.fetchTypesDocument).toHaveBeenCalledWith(today)
      expect(api.fetchPiecesRequises).toHaveBeenCalledWith(today)
      const rows = tree(wrapper)
      expect(rows).toHaveLength(14)
      expect(rows[0]).toEqual(['Engagement', '', '1 pièce', '', ''])
      expect(rows.find((r) => r[0] === 'Sortie')).toEqual([
        'Sortie',
        '',
        'Aucune pièce exigée',
        '',
        '',
      ])

      await wrapper.get('[data-test="pieces-expand-all"]').trigger('click')
      const expanded = tree(wrapper)
      expect(expanded[1]).toEqual(['Contrat signé', 'CTR', 'Obligatoire', '01/01/2015', '—'])
      expect(expanded.find((r) => r[1] === 'DEC' && r[2] === 'Facultative')).toBeTruthy()

      await wrapper.get('[data-test="pieces-collapse-all"]').trigger('click')
      expect(tree(wrapper)).toHaveLength(14)
    })

    it('filters on a document, keeping the events that require it', async () => {
      const wrapper = await mountView()

      await wrapper.get('[data-test="pieces-search"]').setValue('décision')
      expect(tree(wrapper).map((r) => r[0])).toEqual([
        'Promotion',
        'Décision',
        'Formation',
        'Décision',
      ])
    })

    it('reloads at the chosen date, leaving the other dates alone', async () => {
      await mountView()
      const store = useReferentielsStore()

      store.pieces.date = new Date(2023, 5, 1)
      await flushPromises()

      expect(api.fetchPiecesRequises).toHaveBeenLastCalledWith({ date: '2023-06-01' })
      expect(api.fetchTypesDocument).toHaveBeenLastCalledWith({ date: '2023-06-01' })
      expect(localDate(store.typesContrat.date)).toBe(localDate(new Date()))
    })

    it('shows an error, and no event rows, when the lists cannot be loaded', async () => {
      vi.mocked(api.fetchPiecesRequises).mockRejectedValue(new Error('HTTP 502'))
      const wrapper = await mountView()

      expect(wrapper.get('[data-test="pieces-error"]').text()).toContain('HTTP 502')
      expect(tree(wrapper)).toEqual([['Aucune pièce à afficher.']])
    })

    it('offers no action that changes data', async () => {
      const wrapper = await mountView()
      const labels = wrapper.findAll('button').map((b) => b.text())
      expect(labels.filter((l) => /ajouter|modifier|supprimer|enregistrer/i.test(l))).toEqual([])
    })
  })

  describe('exit and suspension tab', () => {
    function table(wrapper: Awaited<ReturnType<typeof mountView>>, name: string) {
      return wrapper
        .findAll(`[data-test="${name}"] tbody tr`)
        .map((tr) => tr.findAll('td').map((td) => td.text().replace(/\s+/g, ' ')))
    }

    beforeEach(() => {
      useReferentielsStore().onglet = 'sorties'
    })

    it('comes after the documents tab', async () => {
      const wrapper = await mountView()
      const tabs = wrapper.findAll('[role="tab"]').map((tab) => tab.text())
      expect(tabs.slice(5, 7)).toEqual(['Pièces justificatives', 'Sorties et suspensions'])
    })

    it('lists the reasons and the positions of today with their rules', async () => {
      const wrapper = await mountView()

      const today = { date: localDate(new Date()) }
      expect(api.fetchMotifsSortie).toHaveBeenCalledWith(today)
      expect(api.fetchTypesSuspension).toHaveBeenCalledWith(today)
      expect(table(wrapper, 'motifs')).toEqual([
        ['DCD', 'Décès Décès', 'ADC — Acte de décès', '01/01/2015', '—'],
        ['DEM', 'Démission', 'LDM — Lettre de démission', '01/01/2015', '—'],
        [
          'RET-ANC',
          'Retraite pour ancienneté Retraite',
          'DRT — Décision de retraite',
          '01/01/2015',
          '—',
        ],
      ])
      expect(table(wrapper, 'suspensions')).toEqual([
        [
          'DETA',
          'Détachement',
          'DEC — Décision',
          'Oui',
          'Fixée par la décision',
          'Sans limite',
          '01/01/2015',
          '—',
        ],
        [
          'DISPO',
          'Mise en disponibilité',
          'DEC — Décision',
          'Non',
          '24 mois',
          '1',
          '01/01/2015',
          '—',
        ],
      ])
    })

    it('filters both tables on code, name or document', async () => {
      const wrapper = await mountView()

      await wrapper.get('[data-test="sorties-search"]').setValue('décision')
      expect(table(wrapper, 'motifs').map((r) => r[0])).toEqual(['RET-ANC'])
      expect(table(wrapper, 'suspensions').map((r) => r[0])).toEqual(['DETA', 'DISPO'])

      await wrapper.get('[data-test="sorties-search"]').setValue('demission')
      expect(table(wrapper, 'motifs').map((r) => r[0])).toEqual(['DEM'])
      expect(table(wrapper, 'suspensions')).toEqual([
        ['Aucune position ne correspond à cette recherche.'],
      ])
    })

    it('reloads both lists at the chosen date, leaving the other dates alone', async () => {
      await mountView()
      const store = useReferentielsStore()

      store.sorties.date = new Date(2014, 11, 31)
      await flushPromises()

      expect(api.fetchMotifsSortie).toHaveBeenLastCalledWith({ date: '2014-12-31' })
      expect(api.fetchTypesSuspension).toHaveBeenLastCalledWith({ date: '2014-12-31' })
      expect(localDate(store.pieces.date)).toBe(localDate(new Date()))
    })

    it('shows each error on its own table, keeping the other list', async () => {
      vi.mocked(api.fetchTypesSuspension).mockRejectedValue(new Error('HTTP 502'))
      const wrapper = await mountView()

      expect(wrapper.get('[data-test="suspensions-error"]').text()).toContain('HTTP 502')
      expect(wrapper.find('[data-test="motifs-error"]').exists()).toBe(false)
      expect(table(wrapper, 'suspensions')).toEqual([
        ['Aucune position de suspension à cette date.'],
      ])
      expect(table(wrapper, 'motifs')).toHaveLength(3)
    })

    it('offers no action that changes data', async () => {
      const wrapper = await mountView()
      expect(wrapper.get('[data-test="motifs"]').findAll('button')).toHaveLength(0)
      expect(wrapper.get('[data-test="suspensions"]').findAll('button')).toHaveLength(0)
    })
  })

  describe('banks tab', () => {
    function table(wrapper: Awaited<ReturnType<typeof mountView>>) {
      return wrapper
        .findAll('[data-test="banques"] tbody tr')
        .map((tr) => tr.findAll('td').map((td) => td.text()))
    }

    beforeEach(() => {
      useReferentielsStore().onglet = 'banques'
    })

    it('comes after the exit and suspension tab', async () => {
      const wrapper = await mountView()
      const tabs = wrapper.findAll('[role="tab"]').map((tab) => tab.text())
      expect(tabs.slice(6, 8)).toEqual(['Sorties et suspensions', 'Banques'])
    })

    it('lists the banks of today with their SWIFT/BIC, or a dash', async () => {
      const wrapper = await mountView()

      expect(api.fetchBanques).toHaveBeenCalledWith({ date: localDate(new Date()) })
      expect(table(wrapper)).toEqual([
        ['BCF', 'Banque Commerciale du Fleuve', 'BCFLCDKI', '01/01/2015', '—'],
        ['TRC', 'Trésor Crédit', '—', '01/01/2015', '—'],
        ['UBK', 'Union Bank Kivu-Kasaï', 'UBKKCDKI', '01/01/2022', '—'],
      ])
    })

    it('filters on code, name or SWIFT/BIC', async () => {
      const wrapper = await mountView()

      await wrapper.get('[data-test="banques-search"]').setValue('ubkk')
      expect(table(wrapper).map((row) => row[0])).toEqual(['UBK'])
      await wrapper.get('[data-test="banques-search"]').setValue('tresor')
      expect(table(wrapper).map((row) => row[0])).toEqual(['TRC'])
      await wrapper.get('[data-test="banques-search"]').setValue('pilote')
      expect(wrapper.get('[data-test="banques"]').text()).toContain(
        'Aucune banque ne correspond à cette recherche.',
      )
    })

    it('reloads at the chosen date, leaving the other dates alone', async () => {
      await mountView()
      const store = useReferentielsStore()

      store.banques.date = new Date(2021, 11, 31)
      await flushPromises()

      expect(api.fetchBanques).toHaveBeenLastCalledWith({ date: '2021-12-31' })
      expect(localDate(store.sorties.date)).toBe(localDate(new Date()))
    })

    it('shows an error when the banks cannot be loaded', async () => {
      vi.mocked(api.fetchBanques).mockRejectedValue(new Error('HTTP 502'))
      const wrapper = await mountView()

      expect(wrapper.get('[data-test="banques-error"]').text()).toContain('HTTP 502')
      expect(table(wrapper)).toEqual([['Aucune banque à cette date.']])
    })

    it('offers no action that changes data', async () => {
      const wrapper = await mountView()
      expect(wrapper.get('[data-test="banques"]').findAll('button')).toHaveLength(0)
    })
  })

  describe('parameters tab', () => {
    function table(wrapper: Awaited<ReturnType<typeof mountView>>) {
      return wrapper
        .findAll('[data-test="parametres"] tbody tr')
        .map((tr) => tr.findAll('td').map((td) => td.text()))
    }

    beforeEach(() => {
      useReferentielsStore().onglet = 'parametres'
    })

    it('comes last, after the banks tab', async () => {
      const wrapper = await mountView()
      const tabs = wrapper.findAll('[role="tab"]').map((tab) => tab.text())
      expect(tabs).toHaveLength(9)
      expect(tabs.slice(-2)).toEqual(['Banques', 'Paramètres'])
    })

    it('lists every parameter of today, in order, with "Non renseigné" when missing', async () => {
      const wrapper = await mountView()

      expect(api.fetchParametres).toHaveBeenCalledWith({ date: localDate(new Date()) })
      expect(table(wrapper)).toEqual([
        ['Âge limite des enfants à charge', '25 ans', '01/01/2015', '—'],
        ["Nombre maximal d'enfants pris en charge", 'Non renseigné', '', ''],
        ['Âge de la retraite', '65 ans', '01/01/2015', '—'],
        ['Durée de carrière avant la retraite', 'Non renseigné', '', ''],
        ["Taille maximale d'une pièce justificative", 'Non renseigné', '', ''],
      ])
    })

    it('reloads at the chosen date, leaving the other dates alone', async () => {
      await mountView()
      const store = useReferentielsStore()

      store.parametres.date = new Date(2019, 5, 1)
      await flushPromises()

      expect(api.fetchParametres).toHaveBeenLastCalledWith({ date: '2019-06-01' })
      expect(localDate(store.banques.date)).toBe(localDate(new Date()))
    })

    it('shows an error, and no rows, when the values cannot be loaded', async () => {
      vi.mocked(api.fetchParametres).mockRejectedValue(new Error('HTTP 502'))
      const wrapper = await mountView()

      expect(wrapper.get('[data-test="parametres-error"]').text()).toContain('HTTP 502')
      expect(table(wrapper)).toEqual([['Aucun paramètre à afficher.']])
    })

    it('offers no action that changes data', async () => {
      const wrapper = await mountView()
      expect(wrapper.get('[data-test="parametres"]').findAll('button')).toHaveLength(0)
    })
  })

  describe('editing', () => {
    function signIn(...permissions: string[]) {
      useAuthStore().user = {
        id: 1,
        username: 'editeur',
        first_name: '',
        last_name: '',
        email: '',
        groups: ['Gestion de carrière'],
        permissions,
      }
    }

    const CARRIERE = [
      'fonction',
      'typecontrat',
      'motifsortie',
      'typesuspension',
      'parametre',
      'site',
      'uniteorganisationnelle',
      'categorie',
      'grade',
      'echelon',
      'typedocument',
      'piecerequise',
    ].flatMap((m) => [`referentiels.add_${m}`, `referentiels.change_${m}`])
    const REMUNERATION = ['referentiels.add_banque', 'referentiels.change_banque']

    it('shows no edit action to a reader', async () => {
      signIn()
      for (const onglet of [
        'organisation',
        'sites',
        'classification',
        'fonctions',
        'typesContrat',
        'pieces',
        'sorties',
        'banques',
        'parametres',
      ]) {
        useReferentielsStore().onglet = onglet as never
        const wrapper = await mountView()
        const actions = wrapper.findAll(
          '[data-test$="-ajouter"], [data-test="ligne-actions"], [data-test^="ajouter-"]',
        )
        expect(actions.map(() => onglet)).toEqual([])
        wrapper.unmount()
      }
    })

    it('shows Ajouter and a row menu to an editor, and reloads after a save', async () => {
      signIn(...CARRIERE)
      useReferentielsStore().onglet = 'fonctions'
      vi.mocked(editionApi.creer).mockResolvedValue({ id: 99 })
      const wrapper = await mountView()

      expect(wrapper.findAll('[data-test="ligne-actions"]')).toHaveLength(FONCTIONS.length)
      await wrapper.get('[data-test="fonctions-ajouter"]').trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Ajouter une fonction')
      await wrapper.get('[data-test="champ-code"]').setValue('CPT')
      await wrapper.get('[data-test="champ-nom"]').setValue('Comptable')
      await wrapper.get('[data-test="edition-dialog"] form').trigger('submit')
      await flushPromises()

      expect(editionApi.creer).toHaveBeenCalledWith(
        'fonctions',
        expect.objectContaining({ code: 'CPT' }),
      )
      expect(api.fetchFonctions).toHaveBeenCalledTimes(2)
    })

    it('offers Corriger, Remplacer and Fermer on an open row', async () => {
      signIn(...CARRIERE)
      useReferentielsStore().onglet = 'typesContrat'
      const wrapper = await mountView()
      await wrapper.findAll('[data-test="ligne-actions"]')[0]!.trigger('click')
      await flushPromises()
      const items = wrapper.findAll('[data-test="ligne-menu"] .p-menu-item').map((i) => i.text())
      expect(items).toEqual(['Corriger', 'Remplacer à une date', 'Fermer'])
    })

    it('follows the bank permissions on the Banques tab, and the others elsewhere', async () => {
      signIn(...REMUNERATION)
      useReferentielsStore().onglet = 'banques'
      let wrapper = await mountView()
      expect(wrapper.find('[data-test="banques-ajouter"]').exists()).toBe(true)
      wrapper.unmount()

      useReferentielsStore().onglet = 'fonctions'
      wrapper = await mountView()
      expect(wrapper.find('[data-test="fonctions-ajouter"]').exists()).toBe(false)
      wrapper.unmount()

      signIn(...CARRIERE)
      useReferentielsStore().onglet = 'banques'
      wrapper = await mountView()
      expect(wrapper.find('[data-test="banques-ajouter"]').exists()).toBe(false)
    })

    it('gives each table of Sorties et suspensions its own actions', async () => {
      signIn(...CARRIERE)
      useReferentielsStore().onglet = 'sorties'
      const wrapper = await mountView()
      expect(wrapper.find('[data-test="motifs-ajouter"]').exists()).toBe(true)
      expect(wrapper.find('[data-test="suspensions-ajouter"]').exists()).toBe(true)
      expect(wrapper.findAll('[data-test="ligne-actions"]')).toHaveLength(
        MOTIFS.length + SUSPENSIONS.length,
      )
    })

    it('offers to add a value for a parameter with none at the date', async () => {
      signIn(...CARRIERE)
      useReferentielsStore().onglet = 'parametres'
      vi.mocked(editionApi.creer).mockResolvedValue({})
      const wrapper = await mountView()

      expect(wrapper.findAll('[data-test="ligne-actions"]')).toHaveLength(2)
      await wrapper.get('[data-test="ajouter-enfants_max"]').trigger('click')
      await flushPromises()
      await wrapper.get('[data-test="edition-dialog"] form').trigger('submit')
      await flushPromises()
      expect(vi.mocked(editionApi.creer).mock.calls[0]![1]).toMatchObject({ cle: 'enfants_max' })
    })

    it('offers Ajouter and the row menu on sites, without Remplacer', async () => {
      signIn(...CARRIERE)
      useReferentielsStore().onglet = 'sites'
      const wrapper = await mountView()
      expect(wrapper.find('[data-test="sites-ajouter"]').exists()).toBe(true)
      await wrapper.findAll('[data-test="ligne-actions"]')[0]!.trigger('click')
      await flushPromises()
      const items = wrapper.findAll('[data-test="ligne-menu"] .p-menu-item').map((i) => i.text())
      expect(items).toEqual(['Corriger', 'Fermer'])
    })

    it('adds a direction, or a sub-unit with its parent, site and next type', async () => {
      signIn(...CARRIERE)
      vi.mocked(editionApi.creer).mockResolvedValue({ id: 50 })
      const wrapper = await mountView()

      expect(wrapper.find('[data-test="unites-ajouter"]').exists()).toBe(true)
      await wrapper.get('[data-test="expand-all"]').trigger('click')
      const sous = wrapper.findAll('[data-test="ajouter-sous"]')
      expect(sous).toHaveLength(3) // two directions and a service: each has a level below
      await sous[0]!.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Ajouter une unité')
      await wrapper.get('[data-test="champ-code"]').setValue('DRH-NEW')
      await wrapper.get('[data-test="champ-nom"]').setValue('Département nouveau')
      await wrapper.get('[data-test="edition-dialog"] form').trigger('submit')
      await flushPromises()

      expect(editionApi.creer).toHaveBeenCalledWith(
        'unites',
        expect.objectContaining({ type: 'departement', parent: 1, site_id: SITE.id }),
      )
      // The tree, the dialog's parent choices, then the reload after saving.
      expect(api.fetchUnites).toHaveBeenCalledTimes(3)
    })

    it('keeps the opened units open after a save that gives them new ids', async () => {
      signIn(...CARRIERE)
      const store = useReferentielsStore()
      store.expanded = { '1': true }
      vi.mocked(editionApi.creer).mockResolvedValue({ id: 50 })
      const wrapper = await mountView()
      vi.mocked(api.fetchUnites).mockResolvedValue([
        unite(11, 'DRH', 'direction', null, 'Direction des ressources humaines'),
        unite(12, 'DRH-FOR', 'service', 11, 'Service Formation'),
        unite(3, 'DT', 'direction', null, 'Direction technique'),
      ])
      await wrapper.get('[data-test="unites-ajouter"]').trigger('click')
      await flushPromises()
      await wrapper.get('[data-test="champ-code"]').setValue('DG')
      await wrapper.get('[data-test="champ-nom"]').setValue('Direction générale')
      await wrapper.get('[data-test="edition-dialog"] form').trigger('submit')
      await flushPromises()
      expect(store.expanded).toEqual({ '11': true })
    })

    it('adds a grade under a catégorie and an échelon under a grade, numbered next', async () => {
      signIn(...CARRIERE)
      useReferentielsStore().onglet = 'classification'
      vi.mocked(editionApi.creer).mockResolvedValue({ id: 70 })
      const wrapper = await mountView()

      expect(wrapper.find('[data-test="categories-ajouter"]').exists()).toBe(true)
      await wrapper.get('[data-test="classification-expand-all"]').trigger('click')
      const sous = wrapper.findAll('[data-test="ajouter-sous"]')
      // Two catégories and two grades can have children; échelons cannot.
      expect(sous).toHaveLength(4)

      const directeur = sous.find((b) => b.attributes('aria-label')?.endsWith('à DIR'))!
      expect(directeur.attributes('aria-label')).toBe('Ajouter un échelon à DIR')
      await directeur.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Ajouter un échelon')
      await wrapper.get('[data-test="edition-dialog"] form').trigger('submit')
      await flushPromises()
      expect(editionApi.creer).toHaveBeenCalledWith(
        'echelons',
        expect.objectContaining({ grade: 1, numero: 3 }),
      )
      expect(api.fetchEchelons).toHaveBeenCalledTimes(2)
    })

    it('corrects an échelon from its own row, with its grade fixed', async () => {
      signIn(...CARRIERE)
      useReferentielsStore().onglet = 'classification'
      const wrapper = await mountView()
      await wrapper.get('[data-test="classification-expand-all"]').trigger('click')
      const echelonRow = wrapper
        .findAll('[data-test="classification"] tbody tr')
        .find((tr) => tr.text().includes('Échelon 2'))!
      await echelonRow.get('[data-test="ligne-actions"]').trigger('click')
      await flushPromises()
      await wrapper.findAll('[data-test="ligne-menu"] .p-menu-item-content')[0]!.trigger('click')
      await flushPromises()
      expect(wrapper.get('[data-test="edition-ligne"]').text()).toBe('DIR — Échelon 2')
      expect(wrapper.get('[data-test="champ-grade"]').classes()).toContain('p-disabled')
    })

    it('adds a required document under an event, and lists the document types to edit', async () => {
      signIn(...CARRIERE)
      useReferentielsStore().onglet = 'pieces'
      vi.mocked(editionApi.creer).mockResolvedValue({ id: 80 })
      const wrapper = await mountView()

      const types = wrapper.findAll('[data-test="types-document"] tbody tr').map((tr) =>
        tr
          .findAll('td')
          .map((td) => td.text())
          .slice(0, 2),
      )
      expect(types).toEqual([
        ['CTR', 'Contrat signé'],
        ['DEC', 'Décision'],
      ])
      expect(wrapper.find('[data-test="types-document-ajouter"]').exists()).toBe(true)
      expect(
        wrapper.get('[data-test="types-document"]').findAll('[data-test="ligne-actions"]'),
      ).toHaveLength(2)

      const sous = wrapper.findAll('[data-test="ajouter-sous"]')
      expect(sous).toHaveLength(14) // one per event kind
      const mariage = sous.find((b) => b.attributes('aria-label')?.endsWith('Mariage'))!
      await mariage.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Ajouter une pièce exigée')
      await wrapper.get('[data-test="edition-dialog"] form').trigger('submit')
      await flushPromises()
      expect(editionApi.creer).toHaveBeenCalledWith(
        'pieces-requises',
        expect.objectContaining({ evenement: 'mariage', obligatoire: true }),
      )
      expect(api.fetchPiecesRequises).toHaveBeenCalledTimes(2)
    })

    it('shows the document types to readers, without actions', async () => {
      signIn()
      useReferentielsStore().onglet = 'pieces'
      const wrapper = await mountView()
      expect(wrapper.findAll('[data-test="types-document"] tbody tr')).toHaveLength(2)
      expect(wrapper.find('[data-test="types-document-ajouter"]').exists()).toBe(false)
    })
  })
})
