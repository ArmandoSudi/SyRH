import { describe, expect, it } from 'vitest'

import { formatDate, localDate } from '../dates'

describe('dates', () => {
  it('formats a local date as YYYY-MM-DD without shifting to UTC', () => {
    expect(localDate(new Date(2026, 0, 5, 23, 30))).toBe('2026-01-05')
  })

  it('shows an ISO date as dd/mm/yyyy', () => {
    expect(formatDate('2025-07-01')).toBe('01/07/2025')
    expect(formatDate(null)).toBe('—')
  })
})
