import { describe, expect, it } from 'vitest'

import type { Categorie, Echelon, Grade } from '@/features/referentiels/api/referentiels'

import { buildClassification, searchText, type ClassificationNode } from '../classification'
import { expandedKeys, filterTree } from '../tree'

const DATES = { date_ouverture: '2015-01-01', date_fermeture: null }

function categorie(id: number, code: string, rang: number, nom = code): Categorie {
  return { id, code, nom, rang, ...DATES }
}

function grade(id: number, code: string, cat: number, rang: number, nom = code): Grade {
  return { id, code, nom, categorie: cat, rang, ...DATES }
}

function echelon(id: number, gradeId: number, code: string, numero: number): Echelon {
  return { id, grade: gradeId, numero, libelle: `${code} — Échelon ${numero}`, ...DATES }
}

// Given out of order on purpose; ids collide across levels on purpose.
const CATEGORIES = [categorie(1, 'AM', 2, 'Agents de maîtrise'), categorie(2, 'CD', 4, 'Cadres')]
const GRADES = [
  grade(1, 'AT2', 2, 1, 'Attaché de 2e classe'),
  grade(2, 'AGM', 1, 1, 'Agent de maîtrise'),
  grade(3, 'AT1', 2, 2, 'Attaché de 1re classe'),
]
const ECHELONS = [
  echelon(1, 1, 'AT2', 10),
  echelon(2, 1, 'AT2', 2),
  echelon(3, 1, 'AT2', 1),
  echelon(4, 3, 'AT1', 1),
]

function shape(nodes: ClassificationNode[]): unknown[] {
  return nodes.map((n) => {
    const label = n.data.code || n.data.nom
    return n.children.length ? [label, shape(n.children)] : label
  })
}

describe('classification tree', () => {
  it('nests catégorie → grade → échelon, higher ranks first, échelons by number', () => {
    expect(shape(buildClassification(CATEGORIES, GRADES, ECHELONS))).toEqual([
      [
        'CD',
        [
          ['AT1', ['Échelon 1']],
          ['AT2', ['Échelon 1', 'Échelon 2', 'Échelon 10']],
        ],
      ],
      ['AM', ['AGM']],
    ])
  })

  it('gives each level its own keys, so equal ids do not collide', () => {
    const tree = buildClassification(CATEGORIES, GRADES, ECHELONS)
    const keys: string[] = []
    const walk = (list: ClassificationNode[]) =>
      list.forEach((n) => {
        keys.push(n.key)
        walk(n.children)
      })
    walk(tree)

    expect(new Set(keys).size).toBe(keys.length)
    expect(keys).toContain('c-1')
    expect(keys).toContain('g-1')
    expect(keys).toContain('e-1')
  })

  it('describes each row for the table', () => {
    const [cd] = buildClassification(CATEGORIES, GRADES, ECHELONS)
    const at1 = cd!.children[0]!
    const step = at1.children[0]!

    expect([cd!.data.niveau, cd!.data.rang]).toEqual(['categorie', 4])
    expect([at1.data.niveau, at1.data.code, at1.data.rang]).toEqual(['grade', 'AT1', 2])
    expect([step.data.niveau, step.data.code, step.data.nom, step.data.rang]).toEqual([
      'echelon',
      '',
      'Échelon 1',
      null,
    ])
  })

  it('shows a row whose parent is missing at the root rather than losing it', () => {
    const tree = buildClassification([], [grade(9, 'ORPH', 99, 1)], [echelon(9, 98, 'X', 1)])

    expect(shape(tree)).toEqual(['ORPH', 'Échelon 1'])
  })

  it('finds a grade with its catégorie and its échelons', () => {
    const tree = buildClassification(CATEGORIES, GRADES, ECHELONS)

    expect(shape(filterTree(tree, 'at1', searchText))).toEqual([['CD', [['AT1', ['Échelon 1']]]]])
  })

  it('finds an échelon with its ancestors, accents ignored', () => {
    const tree = buildClassification(CATEGORIES, GRADES, ECHELONS)

    expect(shape(filterTree(tree, 'AT2 — echelon 10', searchText))).toEqual([
      ['CD', [['AT2', ['Échelon 10']]]],
    ])
    expect(shape(filterTree(tree, 'maitrise', searchText))).toEqual([['AM', ['AGM']]])
  })

  it('expands every row that has children', () => {
    const keys = expandedKeys(buildClassification(CATEGORIES, GRADES, ECHELONS))

    expect(Object.keys(keys).sort()).toEqual(['c-1', 'c-2', 'g-1', 'g-3'])
  })
})
