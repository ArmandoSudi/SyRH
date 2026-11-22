import { describe, expect, it } from 'vitest'

import type { TypeDocument } from '@/features/referentiels/api/referentiels'

import {
  checkFile,
  FICHIER_VIDE,
  filterAgents,
  FORMAT_REFUSE,
  formatTaille,
  tropGros,
  typesDeposables,
} from '../documents'

function file(name: string, size: number): File {
  return new File([new Uint8Array(size)], name)
}

function type(id: number, code: string, confidentiel = false, groupes: string[] = []) {
  return {
    id,
    code,
    nom: code,
    confidentiel,
    groupes_autorises: [],
    groupes_autorises_noms: groupes,
    date_ouverture: '2015-01-01',
    date_fermeture: null,
  } as TypeDocument
}

describe('checkFile', () => {
  it('accepts PDF, JPEG and PNG under the limit', () => {
    for (const name of ['a.pdf', 'b.JPG', 'c.jpeg', 'd.png']) {
      expect(checkFile(file(name, 10), 10)).toBeNull()
    }
  })

  it('refuses another extension, an empty file and a too-large one, with the server words', () => {
    expect(checkFile(file('a.docx', 10), 10)).toBe(FORMAT_REFUSE)
    expect(checkFile(file('sans-extension', 10), 10)).toBe(FORMAT_REFUSE)
    expect(checkFile(file('a.pdf', 0), 10)).toBe(FICHIER_VIDE)
    expect(checkFile(file('a.pdf', 1024 * 1024 + 1), 1)).toBe(tropGros(1))
    expect(tropGros(10)).toBe('Le fichier dépasse la taille maximale de 10 Mo.')
  })

  it('leaves the size to the server when the limit is unknown', () => {
    expect(checkFile(file('a.pdf', 5 * 1024 * 1024), null)).toBeNull()
  })
})

describe('formatTaille', () => {
  it('uses o, Ko and Mo with a French decimal comma', () => {
    expect(formatTaille(850)).toBe('850 o')
    expect(formatTaille(12_700)).toBe('12,4 Ko')
    expect(formatTaille(3_355_443)).toBe('3,2 Mo')
  })
})

describe('typesDeposables', () => {
  it('keeps ordinary types and the confidential ones shared with a profile of the user', () => {
    const types = [
      type(1, 'CTR'),
      type(2, 'CMD', true, ['Social']),
      type(3, 'CNI', true, ['Gestion de carrière']),
    ]
    expect(typesDeposables(types, ['Gestion de carrière']).map((t) => t.code)).toEqual([
      'CTR',
      'CNI',
    ])
    expect(typesDeposables(types, ['Social']).map((t) => t.code)).toEqual(['CTR', 'CMD'])
  })
})

describe('filterAgents', () => {
  const agents = [
    { id: 1, matricule: 'ARPTC/0001/2020', nom: 'Mukendi', postnom: 'Kabongo', prenom: 'Élodie' },
    { id: 2, matricule: 'ARPTC/0002/2020', nom: 'Nsimba', postnom: '', prenom: 'Paul' },
  ]

  it('matches the matricule or a name, case and accents ignored', () => {
    expect(filterAgents(agents, '0002').map((a) => a.id)).toEqual([2])
    expect(filterAgents(agents, 'elodie').map((a) => a.id)).toEqual([1])
    expect(filterAgents(agents, '  ').map((a) => a.id)).toEqual([1, 2])
  })
})
