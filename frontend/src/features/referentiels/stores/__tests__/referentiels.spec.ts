import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { localDate } from '@/shared/utils/dates'

import { useReferentielsStore } from '../referentiels'

describe('referentiels store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('starts on the organisation of today', () => {
    const store = useReferentielsStore()

    expect(store.onglet).toBe('organisation')
    expect(localDate(store.date)).toBe(localDate(new Date()))
    expect(store.texte).toBe('')
    expect(store.sitesFermes).toBe(false)
  })

  it('keeps choices for the next visit', () => {
    const store = useReferentielsStore()
    store.onglet = 'sites'
    store.texte = 'formation'

    const again = useReferentielsStore()
    expect([again.onglet, again.texte]).toEqual(['sites', 'formation'])
  })

  it('keeps the classification date and filter apart from the organisation ones', () => {
    const store = useReferentielsStore()
    expect(localDate(store.classification.date)).toBe(localDate(new Date()))
    expect(store.classification.texte).toBe('')

    store.onglet = 'classification'
    store.classification.date = new Date(2024, 11, 31)
    store.classification.texte = 'AT2'

    expect(localDate(store.date)).toBe(localDate(new Date()))
    expect(store.texte).toBe('')
    const again = useReferentielsStore()
    expect([
      again.onglet,
      localDate(again.classification.date),
      again.classification.texte,
    ]).toEqual(['classification', '2024-12-31', 'AT2'])

    store.date = new Date(2020, 0, 1)
    expect(localDate(store.classification.date)).toBe('2024-12-31')
  })

  it('keeps the fonctions date and filter apart from the other tabs', () => {
    const store = useReferentielsStore()
    expect(localDate(store.fonctions.date)).toBe(localDate(new Date()))
    expect(store.fonctions.texte).toBe('')

    store.onglet = 'fonctions'
    store.fonctions.date = new Date(2023, 11, 31)
    store.fonctions.texte = 'chef'

    expect(localDate(store.date)).toBe(localDate(new Date()))
    expect(localDate(store.classification.date)).toBe(localDate(new Date()))
    const again = useReferentielsStore()
    expect([again.onglet, localDate(again.fonctions.date), again.fonctions.texte]).toEqual([
      'fonctions',
      '2023-12-31',
      'chef',
    ])
  })

  it('keeps the contract types date and filter apart from the other tabs', () => {
    const store = useReferentielsStore()
    expect(localDate(store.typesContrat.date)).toBe(localDate(new Date()))
    expect(store.typesContrat.texte).toBe('')

    store.onglet = 'typesContrat'
    store.typesContrat.date = new Date(2022, 5, 1)
    store.typesContrat.texte = 'stage'

    expect(localDate(store.fonctions.date)).toBe(localDate(new Date()))
    const again = useReferentielsStore()
    expect([again.onglet, localDate(again.typesContrat.date), again.typesContrat.texte]).toEqual([
      'typesContrat',
      '2022-06-01',
      'stage',
    ])
  })

  it('keeps the documents date, filter and expanded rows apart from the other tabs', () => {
    const store = useReferentielsStore()
    expect(localDate(store.pieces.date)).toBe(localDate(new Date()))

    store.onglet = 'pieces'
    store.pieces.date = new Date(2023, 5, 1)
    store.pieces.texte = 'decision'
    store.pieces.expanded = { 'ev-engagement': true }

    expect(localDate(store.typesContrat.date)).toBe(localDate(new Date()))
    const again = useReferentielsStore()
    expect([
      again.onglet,
      localDate(again.pieces.date),
      again.pieces.texte,
      again.pieces.expanded,
    ]).toEqual(['pieces', '2023-06-01', 'decision', { 'ev-engagement': true }])
  })

  it('keeps the exit and suspension date and filter apart from the other tabs', () => {
    const store = useReferentielsStore()
    expect(localDate(store.sorties.date)).toBe(localDate(new Date()))
    expect(store.sorties.texte).toBe('')

    store.onglet = 'sorties'
    store.sorties.date = new Date(2014, 11, 31)
    store.sorties.texte = 'décision'

    expect(localDate(store.pieces.date)).toBe(localDate(new Date()))
    const again = useReferentielsStore()
    expect([again.onglet, localDate(again.sorties.date), again.sorties.texte]).toEqual([
      'sorties',
      '2014-12-31',
      'décision',
    ])
  })

  it('keeps the banks date and filter apart from the other tabs', () => {
    const store = useReferentielsStore()
    expect(localDate(store.banques.date)).toBe(localDate(new Date()))
    expect(store.banques.texte).toBe('')

    store.onglet = 'banques'
    store.banques.date = new Date(2021, 11, 31)
    store.banques.texte = 'fleuve'

    expect(localDate(store.sorties.date)).toBe(localDate(new Date()))
    const again = useReferentielsStore()
    expect([again.onglet, localDate(again.banques.date), again.banques.texte]).toEqual([
      'banques',
      '2021-12-31',
      'fleuve',
    ])
  })

  it('keeps the parameters date apart from the other tabs', () => {
    const store = useReferentielsStore()
    expect(localDate(store.parametres.date)).toBe(localDate(new Date()))

    store.onglet = 'parametres'
    store.parametres.date = new Date(2019, 5, 1)

    expect(localDate(store.banques.date)).toBe(localDate(new Date()))
    const again = useReferentielsStore()
    expect([again.onglet, localDate(again.parametres.date)]).toEqual(['parametres', '2019-06-01'])
  })
})
