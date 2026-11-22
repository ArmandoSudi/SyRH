import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

import * as documentsApi from '@/features/agents/api/documents'
import type { Document } from '@/features/agents/api/documents'
import * as api from '@/features/agents/api/evenements'
import type { EvenementEtat } from '@/features/agents/api/evenements'
import { useAuthStore } from '@/features/auth/stores/auth'
import * as referentiels from '@/features/referentiels/api/referentiels'
import { ApiError } from '@/shared/utils/http'

import EvenementsPanel from '../EvenementsPanel.vue'

vi.mock('@/features/agents/api/evenements', async (original) => ({
  ...(await original<typeof api>()),
  listEvenements: vi.fn<typeof api.listEvenements>(),
  attachDocument: vi.fn<typeof api.attachDocument>(),
  detachDocument: vi.fn<typeof api.detachDocument>(),
}))
vi.mock('@/features/agents/api/documents', async (original) => ({
  ...(await original<typeof documentsApi>()),
  listDocuments: vi.fn<typeof documentsApi.listDocuments>(),
  uploadDocument: vi.fn<typeof documentsApi.uploadDocument>(),
}))
vi.mock('@/features/referentiels/api/referentiels')

function engagement(values: Partial<EvenementEtat> = {}): EvenementEtat {
  return {
    cle: 'contrat-1',
    modele: 'contrat',
    id: 1,
    evenement: 'engagement',
    evenement_libelle: 'Engagement',
    date: '2020-03-01',
    libelle: 'CDD du 01/03/2020 au 28/02/2021 — ARPTC/0001/2020',
    complet: false,
    manquantes: ['DIP'],
    pieces: [
      {
        code: 'CTR',
        nom: 'Contrat signé',
        obligatoire: true,
        satisfaite: true,
        documents: [
          {
            id: 10,
            lien: 100,
            nom_original: 'contrat.pdf',
            type_document_code: 'CTR',
            type_mime: 'application/pdf',
          },
        ],
        confidentielles: 0,
      },
      {
        code: 'CNI',
        nom: "Pièce d'identité",
        obligatoire: true,
        satisfaite: true,
        documents: [],
        confidentielles: 1,
      },
      {
        code: 'DIP',
        nom: 'Diplôme',
        obligatoire: true,
        satisfaite: false,
        documents: [],
        confidentielles: 0,
      },
    ],
    autres: [],
    autres_confidentielles: 0,
    ...values,
  }
}

const AFFECTATION: EvenementEtat = {
  cle: 'affectation-3',
  modele: 'affectation',
  id: 3,
  evenement: null,
  evenement_libelle: 'Engagement (inclus)',
  date: '2020-03-01',
  libelle: 'SCAR · Juriste depuis le 01/03/2020 — ARPTC/0001/2020',
  complet: true,
  manquantes: [],
  pieces: [],
  autres: [],
  autres_confidentielles: 0,
}

function doc(id: number, code: string, nom: string): Document {
  return {
    id,
    type_document: id,
    type_document_code: code,
    type_document_nom: code,
    confidentiel: false,
    nom_original: nom,
    type_mime: 'application/pdf',
    taille: 100,
    date_document: null,
    retire: false,
    motif_retrait: '',
    date_retrait: null,
    retire_par: null,
    retire_par_nom: null,
    cree_par: 1,
    cree_par_nom: 'X',
    date_creation: '2026-11-22T10:00:00+01:00',
    date_modification: '2026-11-22T10:00:00+01:00',
    modifie_par: 1,
  }
}

function signIn(...permissions: string[]) {
  useAuthStore().user = {
    id: 1,
    username: 'carriere',
    first_name: '',
    last_name: '',
    email: '',
    groups: ['Gestion de carrière'],
    permissions: ['accounts.access_agents', ...permissions],
  }
}

const EDITOR = ['agents.add_piecejointe', 'agents.change_piecejointe', 'agents.add_document']

async function mountPanel() {
  const wrapper = mount(EvenementsPanel, {
    props: { agentId: 7 },
    global: { plugins: [PrimeVue, ToastService], stubs: { teleport: true } },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

describe('EvenementsPanel', () => {
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
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      },
    )
    setActivePinia(createPinia())
    vi.mocked(api.listEvenements).mockResolvedValue([engagement(), AFFECTATION])
    vi.mocked(referentiels.fetchTypesDocument).mockResolvedValue([])
    vi.mocked(referentiels.fetchParametres).mockResolvedValue([])
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    document.body.innerHTML = ''
  })

  it('lists the events with their status and pieces', async () => {
    signIn()
    const wrapper = await mountPanel()
    expect(api.listEvenements).toHaveBeenCalledWith(7)
    const cards = wrapper.findAll('[data-test="evenement"]')
    expect(cards).toHaveLength(2)
    expect(cards[0]!.find('[data-test="evenement-statut"]').text()).toBe('1 pièce manquante')
    expect(cards[0]!.findAll('[data-test="piece"]')).toHaveLength(3)
    expect(cards[0]!.text()).toContain('contrat.pdf')
    expect(cards[0]!.find('[data-test="piece-confidentielle"]').text()).toBe(
      'Pièce confidentielle fournie',
    )
    expect(cards[1]!.text()).toContain("Fait partie de l'engagement")
    expect(cards[1]!.find('[data-test="evenement-statut"]').exists()).toBe(false)
  })

  it('hides the editing buttons without the permissions', async () => {
    signIn()
    const wrapper = await mountPanel()
    expect(wrapper.find('[data-test="piece-joindre"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="piece-detacher"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="evenement-joindre"]').exists()).toBe(false)
  })

  it('attaches an existing document of the required type', async () => {
    signIn(...EDITOR)
    vi.mocked(documentsApi.listDocuments).mockResolvedValue([
      doc(10, 'CTR', 'contrat.pdf'),
      doc(11, 'DIP', 'diplome.pdf'),
      doc(12, 'DEC', 'decision.pdf'),
    ])
    vi.mocked(api.attachDocument).mockResolvedValue(engagement({ complet: true, manquantes: [] }))
    const wrapper = await mountPanel()
    await wrapper.find('[data-test="piece-joindre"]').trigger('click')
    await flushPromises()
    const duType = wrapper.find('[data-test="joindre-du-type"]')
    expect(duType.text()).toContain('diplome.pdf')
    // The document already attached is not offered again.
    expect(wrapper.find('[data-test="joindre-autres"]').text()).not.toContain('contrat.pdf')
    await wrapper.find('[data-test="joindre-confirmer"]').trigger('click')
    await flushPromises()
    expect(api.attachDocument).toHaveBeenCalledWith(7, expect.objectContaining({ id: 1 }), 11)
    expect(wrapper.find('[data-test="evenement-statut"]').text()).toBe('Complet')
  })

  it('shows a refusal from the server', async () => {
    signIn(...EDITOR)
    vi.mocked(documentsApi.listDocuments).mockResolvedValue([doc(11, 'DIP', 'diplome.pdf')])
    vi.mocked(api.attachDocument).mockRejectedValue(
      new ApiError(400, 'Requête invalide', {
        document: ['Une pièce retirée ne peut pas être jointe.'],
      }),
    )
    const wrapper = await mountPanel()
    await wrapper.find('[data-test="piece-joindre"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-test="joindre-confirmer"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-test="joindre-erreur"]').text()).toBe(
      'Une pièce retirée ne peut pas être jointe.',
    )
  })

  it('uploads a new document and attaches it', async () => {
    signIn(...EDITOR)
    vi.mocked(documentsApi.listDocuments).mockResolvedValue([])
    vi.mocked(referentiels.fetchTypesDocument).mockResolvedValue([
      {
        id: 4,
        code: 'DIP',
        nom: 'Diplôme',
        confidentiel: false,
        groupes_autorises: [],
        groupes_autorises_noms: [],
        date_ouverture: '2015-01-01',
        date_fermeture: null,
      },
    ])
    vi.mocked(documentsApi.uploadDocument).mockResolvedValue(doc(20, 'DIP', 'nouveau.pdf'))
    vi.mocked(api.attachDocument).mockResolvedValue(engagement({ complet: true, manquantes: [] }))
    const wrapper = await mountPanel()
    await wrapper.find('[data-test="piece-joindre"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-test="joindre-vide"]').exists()).toBe(true)
    await wrapper.find('[data-test="joindre-deposer"]').trigger('click')
    await flushPromises()
    // The add dialog opens with the missing type preselected.
    const select = wrapper.findComponent({ name: 'Select' })
    expect(select.props('modelValue')).toBe(4)
    const input = wrapper.find('[data-test="ajout-fichier"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['%PDF-1.4'], 'nouveau.pdf')],
      configurable: true,
    })
    await input.trigger('change')
    await wrapper.find('[data-test="ajout-deposer"]').trigger('click')
    await flushPromises()
    expect(api.attachDocument).toHaveBeenCalledWith(7, expect.objectContaining({ id: 1 }), 20)
    expect(wrapper.emitted('change')).toHaveLength(1)
    expect(wrapper.find('[data-test="evenement-statut"]').text()).toBe('Complet')
  })

  it('removes a link', async () => {
    signIn(...EDITOR)
    vi.mocked(api.detachDocument).mockResolvedValue(engagement({ manquantes: ['CTR', 'DIP'] }))
    const wrapper = await mountPanel()
    await wrapper.find('[data-test="piece-detacher"]').trigger('click')
    await flushPromises()
    expect(api.detachDocument).toHaveBeenCalledWith(7, expect.objectContaining({ id: 1 }), 100)
    expect(wrapper.find('[data-test="evenement-statut"]').text()).toBe('2 pièces manquantes')
  })

  it('reloads when the page bumps its version', async () => {
    signIn()
    const wrapper = await mountPanel()
    await wrapper.setProps({ version: 1 })
    await flushPromises()
    expect(api.listEvenements).toHaveBeenCalledTimes(2)
  })

  it('shows a load error and the empty state', async () => {
    signIn()
    vi.mocked(api.listEvenements).mockRejectedValue(new ApiError(500, 'Erreur du serveur'))
    let wrapper = await mountPanel()
    expect(wrapper.find('[data-test="evenements-error"]').text()).toContain('Erreur du serveur')
    wrapper.unmount()
    vi.mocked(api.listEvenements).mockResolvedValue([])
    wrapper = await mountPanel()
    expect(wrapper.find('[data-test="evenements-vide"]').exists()).toBe(true)
  })
})
