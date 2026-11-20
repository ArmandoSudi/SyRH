import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'

import * as editionApi from '@/features/referentiels/api/edition'
import type { Valeurs } from '@/features/referentiels/api/edition'
import * as api from '@/features/referentiels/api/referentiels'
import { localDate } from '@/shared/utils/dates'
import { ApiError } from '@/shared/utils/http'

import { EDITIONS } from '../champs'
import EditionDialog, { type Mode } from '../EditionDialog.vue'

vi.mock('@/features/referentiels/api/edition')
vi.mock('@/features/referentiels/api/referentiels')

const JUR = {
  id: 7,
  code: 'JUR',
  nom: 'Juriste',
  nature: 'execution',
  date_ouverture: '2015-01-01',
  date_fermeture: null,
}

async function open(
  table: keyof typeof EDITIONS,
  mode: Mode,
  ligne: Valeurs | null = null,
  initial?: Valeurs,
) {
  const wrapper = mount(EditionDialog, {
    props: { edition: EDITIONS[table], mode, ligne, initial, visible: false },
    global: { plugins: [PrimeVue], stubs: { teleport: true } },
    attachTo: document.body,
  })
  await wrapper.setProps({ visible: true })
  await flushPromises()
  return wrapper
}

describe('EditionDialog', () => {
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
    vi.mocked(api.fetchTypesDocument).mockResolvedValue([
      { id: 2, code: 'DEC', nom: 'Décision', date_ouverture: '2015-01-01', date_fermeture: null },
    ])
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    document.body.innerHTML = ''
  })

  it('adds a row with its fields, the first nature and today as opening date', async () => {
    vi.mocked(editionApi.creer).mockResolvedValue({ id: 9 })
    const wrapper = await open('fonctions', 'ajouter')

    expect(wrapper.text()).toContain('Ajouter une fonction')
    await wrapper.get('[data-test="champ-code"]').setValue(' cpt ')
    await wrapper.get('[data-test="champ-nom"]').setValue('Comptable')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(editionApi.creer).toHaveBeenCalledWith('fonctions', {
      code: 'cpt',
      nom: 'Comptable',
      nature: 'responsabilite',
      date_ouverture: localDate(new Date()),
      date_fermeture: null,
    })
    expect(wrapper.emitted('enregistre')).toEqual([[{ id: 9 }]])
    expect(wrapper.emitted('update:visible')).toEqual([[false]])
  })

  it('corrects a row, prefilled with its values', async () => {
    vi.mocked(editionApi.corriger).mockResolvedValue({ ...JUR, nom: 'Juriste principal' })
    const wrapper = await open('fonctions', 'corriger', JUR)

    expect(wrapper.get('[data-test="edition-ligne"]').text()).toBe('JUR — Juriste')
    const nom = wrapper.get<HTMLInputElement>('[data-test="champ-nom"]')
    expect(nom.element.value).toBe('Juriste')
    await nom.setValue('Juriste principal')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(editionApi.corriger).toHaveBeenCalledWith('fonctions', 7, {
      code: 'JUR',
      nom: 'Juriste principal',
      nature: 'execution',
      date_ouverture: '2015-01-01',
      date_fermeture: null,
    })
  })

  it('replaces a row only once a date of effect is given, without its dates', async () => {
    vi.mocked(editionApi.remplacer).mockResolvedValue({ id: 8 })
    const wrapper = await open('fonctions', 'remplacer', JUR)

    expect(wrapper.find('[data-test="champ-date_ouverture"]').exists()).toBe(false)
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('[data-test="erreur-date_effet"]').text()).toContain('Indiquez la date')
    expect(editionApi.remplacer).not.toHaveBeenCalled()
  })

  it('closes a row with only its closing date, today by default', async () => {
    vi.mocked(editionApi.corriger).mockResolvedValue({ ...JUR })
    const wrapper = await open('fonctions', 'fermer', JUR)

    expect(wrapper.findAll('form input[id^="champ-"]').map((i) => i.attributes('id'))).toEqual([
      'champ-date_fermeture',
    ])
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(editionApi.corriger).toHaveBeenCalledWith('fonctions', 7, {
      date_fermeture: localDate(new Date()),
    })
  })

  it('shows the server errors under their fields, and the others at the top', async () => {
    vi.mocked(editionApi.creer).mockRejectedValue(
      new ApiError(400, 'Une autre fonction porte déjà ce code sur une partie de cette période.', {
        nom: ['Ce champ ne peut être vide.'],
        inconnu: ['Message sans champ affiché.'],
      }),
    )
    const wrapper = await open('fonctions', 'ajouter')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[data-test="erreur-nom"]').text()).toBe('Ce champ ne peut être vide.')
    const top = wrapper.get('[data-test="edition-erreur"]').text()
    expect(top).toContain('porte déjà ce code')
    expect(top).toContain('Message sans champ affiché.')
    expect(wrapper.emitted('enregistre')).toBeUndefined()
  })

  it('says when the user may not write', async () => {
    vi.mocked(editionApi.creer).mockRejectedValue(
      new ApiError(403, 'Vous ne pouvez pas modifier cette liste.'),
    )
    const wrapper = await open('banques', 'ajouter')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('[data-test="edition-erreur"]').text()).toContain('Vous ne pouvez pas')
  })

  it("keeps a parameter's key fixed when correcting, and does not send it", async () => {
    vi.mocked(editionApi.corriger).mockResolvedValue({})
    const row = {
      id: 3,
      cle: 'age_retraite',
      cle_libelle: 'Âge de la retraite',
      valeur: 65,
      date_ouverture: '2015-01-01',
      date_fermeture: null,
    }
    const wrapper = await open('parametres', 'corriger', row)

    expect(wrapper.get('[data-test="edition-ligne"]').text()).toBe('Âge de la retraite')
    expect(wrapper.get('[data-test="champ-cle"]').classes()).toContain('p-disabled')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    const sent = vi.mocked(editionApi.corriger).mock.calls[0]![2]
    expect(sent).not.toHaveProperty('cle')
    expect(sent).toMatchObject({ valeur: 65 })
  })

  it('starts from the values given when adding, such as a missing key', async () => {
    vi.mocked(editionApi.creer).mockResolvedValue({})
    const wrapper = await open('parametres', 'ajouter', null, { cle: 'enfants_max' })
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(vi.mocked(editionApi.creer).mock.calls[0]![1]).toMatchObject({ cle: 'enfants_max' })
  })

  it('loads the open document types for the tables that need one', async () => {
    await open('motifs-sortie', 'ajouter')
    expect(api.fetchTypesDocument).toHaveBeenCalledWith({ date: localDate(new Date()) })

    vi.mocked(api.fetchTypesDocument).mockClear()
    await open('fonctions', 'ajouter')
    expect(api.fetchTypesDocument).not.toHaveBeenCalled()
  })

  it('opens on its first field; Escape is left to the dialog itself', async () => {
    // PrimeVue's Dialog closes on Escape (closeOnEscape, on by default); the walkthrough
    // checks it in a real browser.
    const wrapper = await open('fonctions', 'corriger', JUR)
    // jsdom runs no transition: send the "shown" event the browser would.
    wrapper.findComponent({ name: 'Dialog' }).vm.$emit('show')
    await flushPromises()
    expect(document.activeElement?.id).toBe('champ-code')
    expect(wrapper.findComponent({ name: 'Dialog' }).props('closeOnEscape')).toBe(true)
  })

  it('cancels without saving', async () => {
    const wrapper = await open('fonctions', 'corriger', JUR)
    await wrapper.get('[data-test="edition-annuler"]').trigger('click')
    expect(wrapper.emitted('update:visible')).toEqual([[false]])
    expect(editionApi.corriger).not.toHaveBeenCalled()
  })

  describe('tree tables', () => {
    const UNITES = [
      { id: 1, code: 'DRH', nom: 'Direction RH', type: 'direction', parent: null },
      { id: 2, code: 'DRH-CAR', nom: 'Département Carrière', type: 'departement', parent: 1 },
      { id: 3, code: 'DRH-CAR-PRO', nom: 'Service Promotions', type: 'service', parent: 2 },
    ]
    const SERVICE = {
      ...UNITES[2],
      site: { id: 5, code: 'KIN', nom: 'Siège' },
      date_ouverture: '2015-01-01',
      date_fermeture: null,
    }

    beforeEach(() => {
      vi.mocked(api.fetchUnites).mockResolvedValue(UNITES as never)
      vi.mocked(api.fetchSites).mockResolvedValue([
        { id: 5, code: 'KIN', nom: 'Siège', ville: 'Kinshasa', siege: true, date_fermeture: null },
      ])
    })

    async function options(wrapper: Awaited<ReturnType<typeof open>>, champ: string) {
      await wrapper.get(`[data-test="champ-${champ}"]`).trigger('click')
      await flushPromises()
      return wrapper.findAll('.p-select-option').map((o) => o.text())
    }

    it('lists only parents of a higher level for a unit', async () => {
      const wrapper = await open('unites', 'ajouter', null, { type: 'service', parent: 2 })
      expect(await options(wrapper, 'parent')).toEqual([
        'DRH — Direction RH',
        'DRH-CAR — Département Carrière',
      ])
    })

    it('reads the nested site, and keeps type, parent and site fixed when correcting', async () => {
      vi.mocked(editionApi.corriger).mockResolvedValue({})
      const wrapper = await open('unites', 'corriger', SERVICE)
      for (const champ of ['type', 'parent', 'site_id']) {
        expect(wrapper.get(`[data-test="champ-${champ}"]`).classes()).toContain('p-disabled')
      }
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      const sent = vi.mocked(editionApi.corriger).mock.calls[0]![2]
      expect(Object.keys(sent).sort()).toEqual(['code', 'date_fermeture', 'date_ouverture', 'nom'])
    })

    it('lets a replacement move the unit, sending its site as an id', async () => {
      vi.mocked(editionApi.remplacer).mockResolvedValue({})
      vi.mocked(editionApi.suite).mockResolvedValue({ total: 0, par_genre: [], bloquants: [] })
      const wrapper = await open('unites', 'remplacer', SERVICE)
      expect(wrapper.get('[data-test="champ-parent"]').classes()).not.toContain('p-disabled')
      wrapper
        .findComponent({ name: 'DatePicker' })
        .vm.$emit('update:modelValue', new Date(2027, 0, 1))
      await flushPromises()
      expect(wrapper.get('[data-test="edition-apercu"]').text()).toContain('Aucune ligne')
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(editionApi.remplacer).toHaveBeenCalledWith(
        'unites',
        3,
        '2027-01-01',
        expect.objectContaining({ parent: 2, site_id: 5, type: 'service' }),
      )
    })

    it('shows what follows a replacement and asks to confirm', async () => {
      vi.mocked(editionApi.remplacer).mockResolvedValue({})
      vi.mocked(editionApi.suite).mockResolvedValue({
        total: 4,
        par_genre: [
          { libelle: 'départements', nombre: 3 },
          { libelle: 'service', nombre: 1 },
        ],
        bloquants: [],
      })
      const wrapper = await open('unites', 'remplacer', {
        ...SERVICE,
        ...UNITES[0],
        type: 'direction',
      })
      wrapper
        .findComponent({ name: 'DatePicker' })
        .vm.$emit('update:modelValue', new Date(2027, 0, 1))
      await flushPromises()

      expect(editionApi.suite).toHaveBeenCalledWith('unites', 1, '2027-01-01')
      expect(wrapper.get('[data-test="edition-apercu"]').text()).toContain(
        'Les 4 lignes rattachées suivront : 3 départements, 1 service.',
      )
      const save = wrapper.get('[data-test="edition-enregistrer"]')
      expect(save.attributes('disabled')).toBeDefined()
      await wrapper.get('[data-test="edition-confirme"] input').setValue(true)
      expect(save.attributes('disabled')).toBeUndefined()
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(editionApi.remplacer).toHaveBeenCalled()
    })

    it('disables saving when rows block the replacement', async () => {
      vi.mocked(editionApi.suite).mockResolvedValue({
        total: 1,
        par_genre: [{ libelle: 'département', nombre: 1 }],
        bloquants: ['DRH-NEW — Nouveau département'],
      })
      const wrapper = await open('unites', 'remplacer', { ...SERVICE, ...UNITES[0] })
      wrapper
        .findComponent({ name: 'DatePicker' })
        .vm.$emit('update:modelValue', new Date(2027, 0, 1))
      await flushPromises()
      expect(wrapper.get('[data-test="edition-apercu"]').text()).toContain('DRH-NEW')
      expect(wrapper.get('[data-test="edition-enregistrer"]').attributes('disabled')).toBeDefined()
    })

    it('has no preview for a table whose rows carry nothing', async () => {
      const row = { id: 9, grade: 1, numero: 2, libelle: 'A1 — Échelon 2',
                    date_ouverture: '2015-01-01', date_fermeture: null } // prettier-ignore
      const wrapper = await open('echelons', 'remplacer', row)
      expect(wrapper.get('[data-test="edition-ligne"]').text()).toBe('A1 — Échelon 2')
      wrapper
        .findComponent({ name: 'DatePicker' })
        .vm.$emit('update:modelValue', new Date(2027, 0, 1))
      await flushPromises()
      expect(editionApi.suite).not.toHaveBeenCalled()
    })
  })
})
