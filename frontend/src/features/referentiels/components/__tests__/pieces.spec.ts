import { describe, expect, it } from 'vitest'

import type { PieceRequise, TypeDocument } from '@/features/referentiels/api/referentiels'

import { buildPieces, EVENEMENTS, filterPieces, nombreLibelle } from '../pieces'

const PERIODE = { date_ouverture: '2015-01-01', date_fermeture: null }
const TYPES: TypeDocument[] = [
  { id: 1, code: 'CTR', nom: 'Contrat signé', confidentiel: false, groupes_autorises: [], groupes_autorises_noms: [], ...PERIODE },
  { id: 2, code: 'DEC', nom: 'Décision', confidentiel: false, groupes_autorises: [], groupes_autorises_noms: [], ...PERIODE },
  { id: 3, code: 'AMA', nom: 'Acte de mariage', confidentiel: false, groupes_autorises: [], groupes_autorises_noms: [], ...PERIODE },
]

function piece(
  id: number,
  evenement: PieceRequise['evenement'],
  type_document: number,
  obligatoire = true,
): PieceRequise {
  const label = EVENEMENTS.find((e) => e.value === evenement)!.label
  return { id, evenement, evenement_libelle: label, type_document, obligatoire, ...PERIODE }
}

const PIECES = [
  piece(1, 'engagement', 1),
  piece(2, 'promotion', 2),
  piece(3, 'interim', 2),
  piece(4, 'mariage', 3),
  piece(5, 'formation', 2, false),
]

describe('buildPieces', () => {
  it('shows every event kind in order, with its count, even without documents', () => {
    const tree = buildPieces(TYPES, PIECES)

    expect(tree.map((n) => n.data.nom)).toEqual(EVENEMENTS.map((e) => e.label))
    expect(tree).toHaveLength(14)
    const byLabel = Object.fromEntries(tree.map((n) => [n.data.nom, n]))
    expect(byLabel['Engagement']!.data.nombre).toBe(1)
    expect(byLabel['Sortie']!.data.nombre).toBe(0)
    expect(byLabel['Sortie']!.children).toEqual([])
  })

  it('puts each document under its event, with its type and flag', () => {
    const formation = buildPieces(TYPES, PIECES).find((n) => n.key === 'ev-formation')!
    expect(
      formation.children.map((c) => [c.key, c.data.code, c.data.nom, c.data.obligatoire]),
    ).toEqual([['pr-5', 'DEC', 'Décision', false]])
  })

  it('keeps a requirement whose type is missing, by its id', () => {
    const tree = buildPieces([], [piece(9, 'naissance', 42)])
    const naissance = tree.find((n) => n.key === 'ev-naissance')!
    expect(naissance.children[0]!.data).toMatchObject({ code: '?', nom: 'Type de pièce n° 42' })
  })
})

describe('filterPieces', () => {
  const tree = buildPieces(TYPES, PIECES)

  it('keeps an event that matches with all its documents', () => {
    const result = filterPieces(tree, 'mariage')
    expect(result.map((n) => n.data.nom)).toEqual(['Mariage'])
    expect(result[0]!.children.map((c) => c.data.code)).toEqual(['AMA'])
  })

  it('keeps the events of a matching document, with only that document', () => {
    const result = filterPieces(tree, 'decision')
    expect(result.map((n) => n.data.nom)).toEqual(['Promotion', 'Intérim', 'Formation'])
    expect(result.every((n) => n.children.length === 1)).toBe(true)
  })

  it('matches an event label ignoring accents', () => {
    expect(filterPieces(tree, 'interim').map((n) => n.data.nom)).toEqual(['Intérim'])
  })

  it('returns everything without text, nothing when nothing matches', () => {
    expect(filterPieces(tree, ' ')).toBe(tree)
    expect(filterPieces(tree, 'pilote')).toEqual([])
  })
})

describe('nombreLibelle', () => {
  it('says how many documents an event requires', () => {
    expect([0, 1, 3].map(nombreLibelle)).toEqual(['Aucune pièce exigée', '1 pièce', '3 pièces'])
  })
})
