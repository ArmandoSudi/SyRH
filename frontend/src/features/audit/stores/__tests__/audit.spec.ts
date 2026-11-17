import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { toQueryString } from '@/features/audit/api/audit'

import { localDate, useAuditStore } from '../audit'

describe('audit store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('builds the API query from the filters', () => {
    const store = useAuditStore()
    store.periode = [new Date(2026, 10, 1), new Date(2026, 10, 17)]
    store.auteur = '  mbuyi '
    store.module = 'comptes'
    store.action = 'modification'
    store.page = 3

    expect(toQueryString(store.query)).toBe(
      '?date_debut=2026-11-01&date_fin=2026-11-17&auteur=mbuyi&module=comptes' +
        '&action=modification&page=3',
    )
  })

  it('sends nothing for empty filters and the first page', () => {
    const store = useAuditStore()
    store.periode = [new Date(2026, 10, 1), null]

    expect(toQueryString(store.query)).toBe('?date_debut=2026-11-01')
    store.periode = null
    expect(toQueryString(store.query)).toBe('')
    expect(store.hasFilters).toBe(false)
  })

  it('keeps the filters across uses and resets them on demand', () => {
    useAuditStore().module = 'agents'

    const again = useAuditStore()
    expect(again.module).toBe('agents')
    expect(again.hasFilters).toBe(true)

    again.reset()
    expect(again.module).toBeNull()
    expect(again.page).toBe(1)
  })

  it('formats dates in local time', () => {
    expect(localDate(new Date(2026, 0, 5, 23, 30))).toBe('2026-01-05')
  })
})
