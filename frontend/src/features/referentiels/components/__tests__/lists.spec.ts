import { describe, expect, it } from 'vitest'

import type { Fonction, TypeContrat } from '@/features/referentiels/api/referentiels'

import { filterByCodeAndName } from '../lists'

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

describe('filterByCodeAndName', () => {
  it('keeps everything without text', () => {
    expect(codes(filterByCodeAndName(FONCTIONS, '  '))).toEqual(['CS', 'ING', 'JUR'])
  })

  it('matches the code or the name, ignoring case and accents', () => {
    expect(codes(filterByCodeAndName(FONCTIONS, 'jur'))).toEqual(['JUR'])
    expect(codes(filterByCodeAndName(FONCTIONS, 'ingenieur'))).toEqual(['ING'])
    expect(codes(filterByCodeAndName(FONCTIONS, 'SERVICE'))).toEqual(['CS'])
  })

  it('returns nothing when nothing matches', () => {
    expect(filterByCodeAndName(FONCTIONS, 'pilote')).toEqual([])
  })

  it('works on contract types too', () => {
    const types: TypeContrat[] = [
      {
        id: 1,
        code: 'CDI',
        nom: 'Contrat à durée indéterminée',
        duree_determinee: false,
        periode_essai: true,
        ...PERIODE,
      },
      {
        id: 2,
        code: 'STG',
        nom: 'Stage',
        duree_determinee: true,
        periode_essai: false,
        ...PERIODE,
      },
    ]
    expect(filterByCodeAndName(types, 'indetermin').map((t) => t.code)).toEqual(['CDI'])
    expect(filterByCodeAndName(types, 'stg').map((t) => t.code)).toEqual(['STG'])
  })
})
