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
})
