import { describe, expect, it } from 'vitest'

import { rechercheQuery } from '@/features/agents/api/agents'

import { filtresDepuisQuery, filtresParDefaut, queryDepuisFiltres } from '../agentList'

describe('agent list filters and the URL', () => {
  it('defaults to En activité, page 1, sorted by name', () => {
    expect(filtresParDefaut()).toEqual({
      q: '',
      unite: null,
      grade: null,
      fonction: null,
      statut: ['actif'],
      date: null,
      tri: 'nom',
      page: 1,
    })
    expect(queryDepuisFiltres(filtresParDefaut())).toEqual({})
  })

  it('round-trips every filter', () => {
    const filtres = {
      q: 'kab',
      unite: 3,
      grade: 4,
      fonction: 5,
      statut: ['a_venir' as const, 'sans_contrat' as const],
      date: '2018-01-01',
      tri: 'matricule' as const,
      page: 2,
    }
    const query = queryDepuisFiltres(filtres)
    expect(query).toEqual({
      q: 'kab',
      unite: '3',
      grade: '4',
      fonction: '5',
      statut: 'a_venir,sans_contrat',
      date: '2018-01-01',
      tri: 'matricule',
      page: '2',
    })
    expect(filtresDepuisQuery(query as Record<string, string>)).toEqual(filtres)
  })

  it('keeps "every status" as statut=tous and ignores junk', () => {
    const tous = { ...filtresParDefaut(), statut: [] }
    expect(queryDepuisFiltres(tous)).toEqual({ statut: 'tous' })
    expect(filtresDepuisQuery({ statut: 'tous' }).statut).toEqual([])
    const junk = filtresDepuisQuery({ unite: 'abc', statut: 'retraite,actif', date: '1/1/2020' })
    expect(junk.unite).toBeNull()
    expect(junk.statut).toEqual(['actif'])
    expect(junk.date).toBeNull()
  })

  it('builds the API query', () => {
    expect(rechercheQuery({ ...filtresParDefaut(), taille: 25 })).toBe('?statut=actif&taille=25')
    expect(rechercheQuery({ q: ' muk ', statut: [], unite: 3, page: 2, tri: 'matricule' })).toBe(
      '?q=muk&unite=3&tri=matricule&page=2',
    )
  })
})
