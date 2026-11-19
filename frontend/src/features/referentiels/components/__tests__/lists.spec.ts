import { describe, expect, it } from 'vitest'

import type {
  Banque,
  Fonction,
  MotifSortie,
  TypeContrat,
} from '@/features/referentiels/api/referentiels'

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

  it('also matches the required document of exit reasons and suspension types', () => {
    const motif = (id: number, code: string, nom: string, libelle: string): MotifSortie => ({
      id,
      code,
      nom,
      type_document: id,
      type_document_libelle: libelle,
      retraite: false,
      deces: false,
      ...PERIODE,
    })
    const motifs = [
      motif(1, 'DEM', 'Démission', 'LDM — Lettre de démission'),
      motif(2, 'DCD', 'Décès', 'ADC — Acte de décès'),
    ]
    expect(filterByCodeAndName(motifs, 'lettre').map((m) => m.code)).toEqual(['DEM'])
    expect(filterByCodeAndName(motifs, 'adc').map((m) => m.code)).toEqual(['DCD'])
    expect(filterByCodeAndName(motifs, 'deces').map((m) => m.code)).toEqual(['DCD'])
  })

  it('also matches the SWIFT/BIC of banks', () => {
    const banques: Banque[] = [
      { id: 1, code: 'BCF', nom: 'Banque Commerciale du Fleuve', swift: 'BCFLCDKI', ...PERIODE },
      { id: 2, code: 'TRC', nom: 'Trésor Crédit', swift: '', ...PERIODE },
    ]
    expect(filterByCodeAndName(banques, 'bcfl').map((b) => b.code)).toEqual(['BCF'])
    expect(filterByCodeAndName(banques, 'tresor').map((b) => b.code)).toEqual(['TRC'])
  })
})
