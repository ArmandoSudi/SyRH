import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

import * as api from '@/features/agents/api/documents'
import type { Document } from '@/features/agents/api/documents'
import { useAuthStore } from '@/features/auth/stores/auth'
import * as referentiels from '@/features/referentiels/api/referentiels'
import type { Parametre, TypeDocument } from '@/features/referentiels/api/referentiels'
import { ApiError } from '@/shared/utils/http'

import DocumentsPanel from '../DocumentsPanel.vue'

vi.mock('@/features/agents/api/documents', async (original) => ({
  ...(await original<typeof api>()),
  listDocuments: vi.fn<typeof api.listDocuments>(),
  uploadDocument: vi.fn<typeof api.uploadDocument>(),
  retireDocument: vi.fn<typeof api.retireDocument>(),
}))
vi.mock('@/features/referentiels/api/referentiels')

function piece(id: number, values: Partial<Document> = {}): Document {
  return {
    id,
    type_document: 1,
    type_document_code: 'CTR',
    type_document_nom: 'Contrat signé',
    confidentiel: false,
    nom_original: `piece-${id}.pdf`,
    type_mime: 'application/pdf',
    taille: 12_700,
    date_document: '2021-03-01',
    retire: false,
    motif_retrait: '',
    date_retrait: null,
    retire_par: null,
    retire_par_nom: null,
    cree_par: 1,
    cree_par_nom: 'Aline Mbuyi',
    date_creation: '2026-11-22T10:00:00+01:00',
    date_modification: '2026-11-22T10:00:00+01:00',
    modifie_par: 1,
    ...values,
  }
}

const TYPES: TypeDocument[] = [
  {
    id: 1,
    code: 'CTR',
    nom: 'Contrat signé',
    confidentiel: false,
    groupes_autorises: [],
    groupes_autorises_noms: [],
    date_ouverture: '2015-01-01',
    date_fermeture: null,
  },
  {
    id: 2,
    code: 'CMD',
    nom: 'Certificat médical',
    confidentiel: true,
    groupes_autorises: [3],
    groupes_autorises_noms: ['Social'],
    date_ouverture: '2015-01-01',
    date_fermeture: null,
  },
]

const TAILLE: Parametre = {
  id: 9,
  cle: 'taille_max_piece',
  cle_libelle: "Taille maximale d'une pièce justificative",
  unite: 'Mo',
  valeur: 1,
  date_ouverture: '2015-01-01',
  date_fermeture: null,
}

function signIn(...permissions: string[]) {
  useAuthStore().user = {
    id: 1,
    username: 'carriere',
    first_name: 'Aline',
    last_name: 'Mbuyi',
    email: '',
    groups: ['Gestion de carrière'],
    permissions: ['accounts.access_agents', ...permissions],
  }
}

const EDITOR = ['agents.add_document', 'agents.change_document']

async function mountPanel() {
  const wrapper = mount(DocumentsPanel, {
    props: { agentId: 7 },
    global: { plugins: [PrimeVue, ToastService], stubs: { teleport: true } },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

type Wrapper = Awaited<ReturnType<typeof mountPanel>>

function rows(wrapper: Wrapper) {
  return wrapper.findAll('[data-test="documents"] tbody tr').map((tr) => tr.text())
}

function choose(wrapper: Wrapper, file: File) {
  const input = wrapper.find('[data-test="ajout-fichier"]')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  return input.trigger('change')
}

describe('DocumentsPanel', () => {
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
    vi.mocked(api.listDocuments).mockResolvedValue([piece(1), piece(2)])
    vi.mocked(referentiels.fetchTypesDocument).mockResolvedValue(TYPES)
    vi.mocked(referentiels.fetchParametres).mockResolvedValue([TAILLE])
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    document.body.innerHTML = ''
  })

  it('lists the documents with their links', async () => {
    signIn()
    const wrapper = await mountPanel()
    expect(api.listDocuments).toHaveBeenCalledWith(7, false)
    expect(rows(wrapper)).toHaveLength(2)
    expect(rows(wrapper)[0]).toContain('Contrat signé')
    expect(rows(wrapper)[0]).toContain('piece-1.pdf')
    expect(rows(wrapper)[0]).toContain('12,4 Ko')
    expect(rows(wrapper)[0]).toContain('01/03/2021')
    expect(rows(wrapper)[0]).toContain('Aline Mbuyi')
    const ouvrir = wrapper.find('[data-test="documents-ouvrir"]')
    expect(ouvrir.attributes('href')).toBe('/api/agents/7/documents/1/fichier/')
    expect(ouvrir.attributes('target')).toBe('_blank')
    const telecharger = wrapper.find('[data-test="documents-telecharger"]')
    expect(telecharger.attributes('href')).toBe(
      '/api/agents/7/documents/1/fichier/?telechargement=1',
    )
  })

  it('hides add and retire without the permissions', async () => {
    signIn()
    const wrapper = await mountPanel()
    expect(wrapper.find('[data-test="documents-ajouter"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="documents-retirer"]').exists()).toBe(false)
    expect(referentiels.fetchTypesDocument).not.toHaveBeenCalled()
  })

  it('toggles the retired documents, shown with their reason', async () => {
    signIn(...EDITOR)
    const wrapper = await mountPanel()
    vi.mocked(api.listDocuments).mockResolvedValue([
      piece(1),
      piece(3, {
        retire: true,
        motif_retrait: 'Mauvais agent sélectionné',
        retire_par_nom: 'Aline Mbuyi',
        date_retrait: '2026-11-22T11:00:00+01:00',
      }),
    ])
    await wrapper.find('[data-test="documents-retires"] input').setValue(true)
    await flushPromises()
    expect(api.listDocuments).toHaveBeenLastCalledWith(7, true)
    expect(wrapper.find('[data-test="documents-motif"]').text()).toContain(
      'Mauvais agent sélectionné',
    )
    // A retired document cannot be retired again.
    expect(wrapper.findAll('[data-test="documents-retirer"]')).toHaveLength(1)
  })

  it('shows a load error', async () => {
    signIn()
    vi.mocked(api.listDocuments).mockRejectedValue(new ApiError(500, 'Erreur du serveur'))
    const wrapper = await mountPanel()
    expect(wrapper.find('[data-test="documents-error"]').text()).toContain('Erreur du serveur')
  })

  describe('adding', () => {
    it('offers only the types the user may read', async () => {
      signIn(...EDITOR)
      const wrapper = await mountPanel()
      await wrapper.find('[data-test="documents-ajouter"]').trigger('click')
      const select = wrapper.findComponent({ name: 'Select' })
      expect(select.props('options')).toEqual([{ value: 1, label: 'Contrat signé (CTR)' }])
    })

    it('refuses a wrong format or a too-large file before sending', async () => {
      signIn(...EDITOR)
      const wrapper = await mountPanel()
      await wrapper.find('[data-test="documents-ajouter"]').trigger('click')
      await choose(wrapper, new File(['x'], 'lettre.docx'))
      expect(wrapper.find('[data-test="ajout-fichier-erreur"]').text()).toBe(
        'Format refusé : seuls les fichiers PDF, JPEG et PNG sont acceptés.',
      )
      await choose(wrapper, new File([new Uint8Array(1024 * 1024 + 1)], 'scan.pdf'))
      expect(wrapper.find('[data-test="ajout-fichier-erreur"]').text()).toBe(
        'Le fichier dépasse la taille maximale de 1 Mo.',
      )
      await wrapper.find('[data-test="ajout-deposer"]').trigger('click')
      expect(api.uploadDocument).not.toHaveBeenCalled()
    })

    it('uploads with progress, then reloads', async () => {
      signIn(...EDITOR)
      let finish: (value: Document) => void = () => {}
      vi.mocked(api.uploadDocument).mockImplementation((_agent, _values, onProgress) => {
        onProgress?.(0.4)
        return new Promise((resolve) => {
          finish = resolve
        })
      })
      const wrapper = await mountPanel()
      await wrapper.find('[data-test="documents-ajouter"]').trigger('click')
      wrapper.findComponent({ name: 'Select' }).vm.$emit('update:modelValue', 1)
      await choose(wrapper, new File(['%PDF-1.4'], 'contrat.pdf'))
      await wrapper.find('[data-test="ajout-deposer"]').trigger('click')
      await flushPromises()
      expect(wrapper.find('[data-test="ajout-progression"]').exists()).toBe(true)
      expect(wrapper.find('[data-test="ajout-progression"]').text()).toContain('40')
      const [agentId, values] = vi.mocked(api.uploadDocument).mock.calls[0]!
      expect(agentId).toBe(7)
      expect(values.type_document).toBe(1)
      expect(values.fichier.name).toBe('contrat.pdf')
      finish(piece(5))
      await flushPromises()
      expect(api.listDocuments).toHaveBeenCalledTimes(2)
      expect(wrapper.find('[data-test="ajout-dialog"]').exists()).toBe(false)
    })

    it('shows the server refusals next to their field', async () => {
      signIn(...EDITOR)
      vi.mocked(api.uploadDocument).mockRejectedValue(
        new ApiError(400, 'Requête invalide', {
          fichier: ['Ce fichier est déjà déposé pour cet agent avec ce type de pièce.'],
        }),
      )
      const wrapper = await mountPanel()
      await wrapper.find('[data-test="documents-ajouter"]').trigger('click')
      wrapper.findComponent({ name: 'Select' }).vm.$emit('update:modelValue', 1)
      await choose(wrapper, new File(['%PDF-1.4'], 'contrat.pdf'))
      await wrapper.find('[data-test="ajout-deposer"]').trigger('click')
      await flushPromises()
      expect(wrapper.find('[data-test="ajout-fichier-erreur"]').text()).toBe(
        'Ce fichier est déjà déposé pour cet agent avec ce type de pièce.',
      )
    })

    it('asks for the type and the file', async () => {
      signIn(...EDITOR)
      const wrapper = await mountPanel()
      await wrapper.find('[data-test="documents-ajouter"]').trigger('click')
      await wrapper.find('[data-test="ajout-deposer"]').trigger('click')
      expect(wrapper.text()).toContain('Choisissez le type de pièce.')
      expect(wrapper.text()).toContain('Choisissez le fichier à déposer.')
      expect(api.uploadDocument).not.toHaveBeenCalled()
    })
  })

  describe('retiring', () => {
    it('requires a reason of 10 characters, then retires and reloads', async () => {
      signIn(...EDITOR)
      vi.mocked(api.retireDocument).mockResolvedValue(piece(1, { retire: true }))
      const wrapper = await mountPanel()
      await wrapper.find('[data-test="documents-retirer"]').trigger('click')
      await wrapper.find('[data-test="retrait-motif"]').setValue('court')
      await wrapper.find('[data-test="retrait-confirmer"]').trigger('click')
      expect(wrapper.text()).toContain('Indiquez le motif du retrait, en 10 caractères au moins.')
      expect(api.retireDocument).not.toHaveBeenCalled()
      await wrapper.find('[data-test="retrait-motif"]').setValue('Mauvais agent sélectionné')
      await wrapper.find('[data-test="retrait-confirmer"]').trigger('click')
      await flushPromises()
      expect(api.retireDocument).toHaveBeenCalledWith(7, 1, 'Mauvais agent sélectionné')
      expect(api.listDocuments).toHaveBeenCalledTimes(2)
    })
  })
})
