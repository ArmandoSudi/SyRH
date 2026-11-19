import { describe, expect, it } from 'vitest'

import { dureeLibelle, renouvellementsLibelle } from '../sorties'

describe('suspension labels', () => {
  it('reads a duration in months, or as set by the decision when blank', () => {
    expect(dureeLibelle(24)).toBe('24 mois')
    expect(dureeLibelle(1)).toBe('1 mois')
    expect(dureeLibelle(null)).toBe('Fixée par la décision')
  })

  it('reads the renewals as a number, zero included, or without limit when blank', () => {
    expect(renouvellementsLibelle(1)).toBe('1')
    expect(renouvellementsLibelle(0)).toBe('0')
    expect(renouvellementsLibelle(null)).toBe('Sans limite')
  })
})
