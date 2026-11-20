import { describe, expect, it } from 'vitest'

import type { Parametre } from '@/features/referentiels/api/referentiels'

import { buildParametres, PARAMETRES, valeurLibelle } from '../parametres'

function row(id: number, cle: string, cle_libelle: string, valeur: number, unite = 'ans') {
  return {
    id,
    cle,
    cle_libelle,
    unite,
    valeur,
    date_ouverture: '2015-01-01',
    date_fermeture: null,
  } as Parametre
}

describe('buildParametres', () => {
  it('gives every key in order, with "Non renseigné" for a missing one', () => {
    const lignes = buildParametres([
      row(2, 'age_retraite', 'Âge de la retraite', 65),
      row(1, 'age_limite_enfant', 'Âge limite des enfants à charge', 25),
    ])
    expect(lignes.map((l) => l.cle)).toEqual(PARAMETRES.map((p) => p.cle))
    expect(lignes.map(valeurLibelle)).toEqual([
      '25 ans',
      'Non renseigné',
      '65 ans',
      'Non renseigné',
    ])
  })

  it('keeps a row whose key the client does not know yet, at the end', () => {
    const lignes = buildParametres([row(9, 'age_pivot', 'Âge pivot', 62)])
    expect(lignes).toHaveLength(5)
    expect(lignes[4]).toMatchObject({ cle: 'age_pivot', libelle: 'Âge pivot' })
    expect(valeurLibelle(lignes[4]!)).toBe('62 ans')
  })

  it('shows the unit of each key', () => {
    const [, enfants] = buildParametres([
      row(3, 'enfants_max', "Nombre maximal d'enfants pris en charge", 6, 'enfants'),
    ])
    expect(valeurLibelle(enfants!)).toBe('6 enfants')
  })
})
