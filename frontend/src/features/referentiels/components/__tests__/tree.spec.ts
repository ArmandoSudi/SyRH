import { describe, expect, it } from 'vitest'

import type { Unite } from '@/features/referentiels/api/referentiels'

import {
  buildTree,
  clesPourIdentites,
  expandedKeys,
  filterTree,
  identitesOuvertes,
  type UniteNode,
} from '../tree'

const SITE = { id: 1, code: 'KIN', nom: 'Siège' }

function unite(id: number, code: string, type: Unite['type'], parent: number | null, nom = code) {
  return {
    id,
    code,
    nom,
    type,
    type_libelle: type,
    parent,
    site: SITE,
    date_ouverture: '2015-01-01',
    date_fermeture: null,
  } satisfies Unite
}

const UNITES: Unite[] = [
  unite(5, 'DRH-SOC', 'service', 2, 'Service Social'),
  unite(2, 'DRH', 'direction', null, 'Direction des Ressources humaines'),
  unite(1, 'DG', 'direction', null, 'Direction générale'),
  unite(6, 'DRH-DEP', 'departement', 2, 'Département Études'),
  unite(7, 'DRH-DEP-B', 'bureau', 6, 'Bureau Archives'),
  unite(3, 'DRH-CAR', 'service', 2, 'Service Gestion de carrière'),
]

function shape(nodes: UniteNode[]): unknown[] {
  return nodes.map((n) => (n.children.length ? [n.data.code, shape(n.children)] : n.data.code))
}

describe('organisation tree', () => {
  it('nests units under their parent, higher levels first, then by code', () => {
    expect(shape(buildTree(UNITES))).toEqual([
      'DG',
      ['DRH', [['DRH-DEP', ['DRH-DEP-B']], 'DRH-CAR', 'DRH-SOC']],
    ])
  })

  it('shows a unit whose parent is missing at the root', () => {
    const tree = buildTree([unite(9, 'ORPHAN', 'service', 42)])

    expect(shape(tree)).toEqual(['ORPHAN'])
  })

  it('keeps matching units and their ancestors, ignoring case and accents', () => {
    const tree = buildTree(UNITES)

    expect(shape(filterTree(tree, 'carriere'))).toEqual([['DRH', ['DRH-CAR']]])
    expect(shape(filterTree(tree, 'archives'))).toEqual([['DRH', [['DRH-DEP', ['DRH-DEP-B']]]]])
    expect(filterTree(tree, 'nothing')).toEqual([])
    expect(filterTree(tree, '  ')).toBe(tree)
  })

  it('lists the keys of every unit that has children', () => {
    expect(expandedKeys(buildTree(UNITES))).toEqual({ '2': true, '6': true })
  })
})

describe('opened rows across a reload', () => {
  it('finds the opened rows by code and gives back the keys of the same codes', () => {
    type N = { key: string; data: { code: string; nom: string }; children: N[] }
    const before: N[] = [
      {
        key: '1',
        data: { code: 'DRH', nom: '' },
        children: [{ key: '2', data: { code: 'DRH-CAR', nom: '' }, children: [] }],
      },
      { key: '3', data: { code: 'DT', nom: '' }, children: [] },
    ]
    const after: N[] = [
      {
        key: '11',
        data: { code: 'DRH', nom: '' },
        children: [{ key: '12', data: { code: 'DRH-CAR', nom: '' }, children: [] }],
      },
      { key: '3', data: { code: 'DT', nom: '' }, children: [] },
    ]
    const opened = identitesOuvertes(before, { '1': true, '2': true })
    expect([...opened]).toEqual(['DRH', 'DRH-CAR'])
    expect(clesPourIdentites(after, opened)).toEqual({ '11': true, '12': true })
  })
})
