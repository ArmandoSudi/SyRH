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
})
