import { describe, expect, it } from 'vitest'

import type { Fonction } from '@/features/referentiels/api/referentiels'

import { filterFonctions } from '../fonctions'

const PERIODE = { date_ouverture: '2015-01-01', date_fermeture: null }
const FONCTIONS: Fonction[] = [
  {
    id: 1,
    code: 'CS',
    nom: 'Chef de service',
    nature: 'responsabilite',
    nature_libelle: 'Responsabilité',
    ...PERIODE,
  },
  {
    id: 2,
    code: 'ING',
    nom: 'Ingénieur télécoms',
    nature: 'execution',
    nature_libelle: 'Exécution',
    ...PERIODE,
  },
  {
    id: 3,
    code: 'JUR',
    nom: 'Juriste',
    nature: 'execution',
    nature_libelle: 'Exécution',
    ...PERIODE,
  },
]

const codes = (list: Fonction[]) => list.map((f) => f.code)

describe('filterFonctions', () => {
  it('keeps everything without text', () => {
    expect(codes(filterFonctions(FONCTIONS, '  '))).toEqual(['CS', 'ING', 'JUR'])
  })

  it('matches the code or the name, ignoring case and accents', () => {
    expect(codes(filterFonctions(FONCTIONS, 'jur'))).toEqual(['JUR'])
    expect(codes(filterFonctions(FONCTIONS, 'ingenieur'))).toEqual(['ING'])
    expect(codes(filterFonctions(FONCTIONS, 'SERVICE'))).toEqual(['CS'])
  })

  it('returns nothing when nothing matches', () => {
    expect(filterFonctions(FONCTIONS, 'pilote')).toEqual([])
  })
})
