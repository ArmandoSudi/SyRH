import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import DatePicker from 'primevue/datepicker'
import RadioButton from 'primevue/radiobutton'
import Select from 'primevue/select'
import ToastService from 'primevue/toastservice'
import TreeSelect from 'primevue/treeselect'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import * as api from '@/features/agents/api/engagement'
import * as referentiels from '@/features/referentiels/api/referentiels'
import { ApiError } from '@/shared/utils/http'

import AgentCreateView from '../AgentCreateView.vue'

vi.mock('@/features/agents/api/engagement')
vi.mock('@/features/referentiels/api/referentiels')

const P = { date_ouverture: '2015-01-01', date_fermeture: null }
const CDI = { id: 1, code: 'CDI', nom: 'CDI', duree_determinee: false, periode_essai: true, ...P }
const CDD = { id: 2, code: 'CDD', nom: 'CDD', duree_determinee: true, periode_essai: true, ...P }
const UNITE = { id: 5, code: 'DRH', nom: 'Direction RH', type: 'direction', type_libelle: 'Direction',
  parent: null, site: { id: 1, code: 'KIN', nom: 'Kinshasa' }, ...P } as const // prettier-ignore
const FONCTION = { id: 6, code: 'DIR', nom: 'Directeur', nature: 'responsabilite', nature_libelle: 'Responsabilité', ...P } as const // prettier-ignore
const GRADE = { id: 7, categorie: 1, code: 'A1', nom: 'Attaché', rang: 1, ...P }
const ECHELON = { id: 8, grade: 7, numero: 1, libelle: 'A1 — Échelon 1', ...P }

function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/agents', name: 'agents', component: { template: '<div />' } },
      { path: '/agents/nouveau', name: 'agents-nouveau', component: AgentCreateView },
      { path: '/agents/pieces', name: 'agents-pieces', component: { template: '<div />' } },
    ],
  })
}

async function mountForm() {
  const router = makeRouter()
  await router.push('/agents/nouveau')
  await router.isReady()
  const wrapper = mount({ template: '<RouterView />' }, {
    global: { plugins: [PrimeVue, ToastService, router], stubs: { teleport: true } },
    attachTo: document.body,
  })
  await flushPromises()
  return { wrapper, router }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type W = VueWrapper<any>

async function next(wrapper: W) {
  await wrapper.find('[data-test="suivant"]').trigger('click')
  await flushPromises()
}

function errors(wrapper: W) {
  return wrapper.findAll('.error').map((e) => e.text())
}

async function fillIdentity(wrapper: W) {
  await wrapper.find('[data-test="f-nom"]').setValue('Mukendi')
  await wrapper.find('[data-test="f-prenom"]').setValue('Patrick')
  await wrapper.find('[data-test="f-lieu"]').setValue('Kananga')
  wrapper.findAllComponents(RadioButton)[0]!.vm.$emit('update:modelValue', 'M')
  wrapper.findAllComponents(DatePicker)[0]!.vm.$emit('update:modelValue', new Date(1972, 3, 18))
  await flushPromises()
}

function select(wrapper: W, test: string) {
  return wrapper.findAllComponents(Select).find((s) => s.attributes('data-test') === test)!
}

async function fillContract(wrapper: W, type = CDI) {
  wrapper.findAllComponents(DatePicker).find((d) => d.attributes('data-test') === 'f-debut')!
    .vm.$emit('update:modelValue', new Date(2026, 0, 5)) // prettier-ignore
  await flushPromises()
  select(wrapper, 'f-type').vm.$emit('update:modelValue', type.id)
  await flushPromises()
}

async function fillPost(wrapper: W) {
  wrapper.findComponent(TreeSelect).vm.$emit('update:modelValue', { '5': true })
  select(wrapper, 'f-fonction').vm.$emit('update:modelValue', 6)
  select(wrapper, 'f-grade').vm.$emit('update:modelValue', 7)
  await flushPromises()
  select(wrapper, 'f-echelon').vm.$emit('update:modelValue', 8)
  await flushPromises()
}

async function toSummary(wrapper: W) {
  await fillIdentity(wrapper)
  await next(wrapper)
  await next(wrapper) // contact details are optional
  await fillContract(wrapper)
  await next(wrapper)
  await fillPost(wrapper)
  await next(wrapper)
}

describe('AgentCreateView', () => {
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
    vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} }) // prettier-ignore
    setActivePinia(createPinia())
    vi.mocked(referentiels.fetchTypesContrat).mockResolvedValue([CDI, CDD])
    vi.mocked(referentiels.fetchUnites).mockResolvedValue([UNITE])
    vi.mocked(referentiels.fetchFonctions).mockResolvedValue([FONCTION])
    vi.mocked(referentiels.fetchGrades).mockResolvedValue([GRADE])
    vi.mocked(referentiels.fetchEchelons).mockResolvedValue([ECHELON])
    vi.mocked(referentiels.fetchPiecesRequises).mockResolvedValue([
      { id: 1, evenement: 'engagement', evenement_libelle: 'Engagement', type_document: 3, obligatoire: true, ...P },
    ]) // prettier-ignore
    vi.mocked(referentiels.fetchTypesDocument).mockResolvedValue([
      { id: 3, code: 'CTR', nom: 'Contrat signé', confidentiel: false, groupes_autorises: [], groupes_autorises_noms: [], ...P },
    ]) // prettier-ignore
    vi.mocked(api.matriculeSuivant).mockResolvedValue('ARPTC/0013/2026')
    vi.mocked(api.doublons).mockResolvedValue([])
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    document.body.innerHTML = ''
  })

  it('checks each step before the next', async () => {
    const { wrapper } = await mountForm()
    await next(wrapper)
    expect(errors(wrapper)).toHaveLength(4) // nom, sexe, birth date and place
    expect(wrapper.find('[data-test="etape-identite"]').isVisible()).toBe(true)
    await fillIdentity(wrapper)
    expect(errors(wrapper)).toHaveLength(0) // each error leaves with its field
    await next(wrapper)
    await next(wrapper)
    await next(wrapper)
    expect(errors(wrapper)).toEqual(['Ce champ est obligatoire.', 'Ce champ est obligatoire.'])
  })

  it('shows the end date only for a fixed-term type, and requires it', async () => {
    const { wrapper } = await mountForm()
    await fillIdentity(wrapper)
    await next(wrapper)
    await next(wrapper)
    await fillContract(wrapper, CDD)
    expect(wrapper.find('[data-test="f-fin"]').exists()).toBe(true)
    await next(wrapper)
    expect(errors(wrapper)).toEqual(['Ce champ est obligatoire.'])
    select(wrapper, 'f-type').vm.$emit('update:modelValue', CDI.id)
    await flushPromises()
    expect(wrapper.find('[data-test="f-fin"]').exists()).toBe(false)
  })

  it('suggests the matricule from the start year, never over typed text', async () => {
    const { wrapper } = await mountForm()
    await fillContract(wrapper)
    expect(api.matriculeSuivant).toHaveBeenCalledWith(2026)
    expect((wrapper.find('[data-test="f-matricule"]').element as HTMLInputElement).value).toBe(
      'ARPTC/0013/2026',
    )
    await wrapper.find('[data-test="f-matricule"]').setValue('ARPTC/0500/2026')
    wrapper.findAllComponents(DatePicker).find((d) => d.attributes('data-test') === 'f-debut')!
      .vm.$emit('update:modelValue', new Date(2027, 0, 5)) // prettier-ignore
    await flushPromises()
    expect((wrapper.find('[data-test="f-matricule"]').element as HTMLInputElement).value).toBe(
      'ARPTC/0500/2026',
    )
  })

  it('reloads the lists on the start date and drops a choice no longer open', async () => {
    const { wrapper } = await mountForm()
    await toSummary(wrapper)
    vi.mocked(referentiels.fetchFonctions).mockResolvedValue([])
    await wrapper.find('[data-test="precedent"]').trigger('click')
    await wrapper.find('[data-test="precedent"]').trigger('click')
    await flushPromises()
    wrapper.findAllComponents(DatePicker).find((d) => d.attributes('data-test') === 'f-debut')!
      .vm.$emit('update:modelValue', new Date(2016, 0, 1)) // prettier-ignore
    await flushPromises()
    expect(referentiels.fetchFonctions).toHaveBeenLastCalledWith({ date: '2016-01-01' })
    expect(select(wrapper, 'f-fonction').props('modelValue')).toBeNull()
  })

  it('shows the summary with the hiring pieces, then saves and opens the Pièces page', async () => {
    vi.mocked(api.engager).mockResolvedValue({ id: 42, matricule: 'ARPTC/0013/2026', nom: 'Mukendi', postnom: '', prenom: 'Patrick' }) // prettier-ignore
    const { wrapper, router } = await mountForm()
    await toSummary(wrapper)
    expect(wrapper.find('[data-test="resume"]').text()).toContain('ARPTC/0013/2026')
    expect(wrapper.find('[data-test="resume-pieces"]').text()).toContain('Contrat signé')
    await wrapper.find('[data-test="enregistrer"]').trigger('click')
    await flushPromises()
    const body = vi.mocked(api.engager).mock.calls[0]![0]
    expect(body).toMatchObject({
      matricule: 'ARPTC/0013/2026',
      nom: 'Mukendi',
      sexe: 'M',
      date_naissance: '1972-04-18',
      coordonnees: null,
      contrat: { type_contrat: 1, date_debut: '2026-01-05', date_fin: null },
      affectation: { unite: 5, fonction: 6 },
      classement: { echelon: 8 },
    })
    expect(router.currentRoute.value.fullPath).toBe('/agents/pieces?agent=42')
  })

  it('brings server errors back to their step and field', async () => {
    vi.mocked(api.engager).mockRejectedValue(
      new ApiError(400, 'Requête invalide', {
        matricule: ['Ce matricule est déjà attribué à un autre agent.'],
        'classement.echelon': ["L'échelon n'est pas ouvert."],
      }),
    )
    const { wrapper } = await mountForm()
    await toSummary(wrapper)
    await wrapper.find('[data-test="enregistrer"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-test="etape-identite"]').isVisible()).toBe(true)
    expect(errors(wrapper)).toContain('Ce matricule est déjà attribué à un autre agent.')
  })

  it('needs the box ticked when a possible duplicate exists', async () => {
    vi.mocked(api.doublons).mockResolvedValue([
      {
        id: 3,
        matricule: 'ARPTC/0001/2008',
        nom: 'Mukendi',
        postnom: 'Kalonji',
        prenom: 'Patrick',
      },
    ])
    const { wrapper } = await mountForm()
    await toSummary(wrapper)
    expect(api.doublons).toHaveBeenCalledWith({
      nom: 'Mukendi',
      prenom: 'Patrick',
      date_naissance: '1972-04-18',
    })
    expect(wrapper.find('[data-test="homonymes"]').text()).toContain('ARPTC/0001/2008')
    expect(wrapper.find('[data-test="enregistrer"]').attributes('disabled')).toBeDefined()
  })

  it('asks before leaving a filled form', async () => {
    const confirm = vi.fn<(m?: string) => boolean>().mockReturnValue(false)
    vi.stubGlobal('confirm', confirm)
    const { wrapper, router } = await mountForm()
    await wrapper.find('[data-test="f-nom"]').setValue('Mukendi')
    await router.push('/agents')
    expect(confirm).toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/agents/nouveau')
  })
})
