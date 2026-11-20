import { describe, expect, it } from 'vitest'

import { EDITIONS, peutAjouter, peutModifier, peutRemplacer } from '../champs'

describe('edit rights', () => {
  const can = (held: string[]) => (permission: string) => held.includes(permission)

  it('follows the Django permissions of each table', () => {
    const banques = EDITIONS.banques
    expect(peutAjouter(can(['referentiels.add_banque']), banques)).toBe(true)
    expect(peutModifier(can(['referentiels.add_banque']), banques)).toBe(false)
    expect(peutRemplacer(can(['referentiels.add_banque']), banques)).toBe(false)
    const both = can(['referentiels.add_banque', 'referentiels.change_banque'])
    expect(peutRemplacer(both, banques)).toBe(true)
    expect(peutAjouter(both, EDITIONS.fonctions)).toBe(false)
  })

  it('describes the thirteen tables, each with what identifies a row', () => {
    expect(Object.keys(EDITIONS)).toHaveLength(13)
    for (const edition of Object.values(EDITIONS)) {
      const names = edition.champs.map((c) => c.nom)
      expect(['code', 'cle', 'numero', 'evenement'].some((n) => names.includes(n))).toBe(true)
      expect(edition.confirmation).toMatch(/enregistrée?\.$/)
    }
  })

  it('offers no replacement on sites, which have no opening date', () => {
    const all = () => true
    expect(peutRemplacer(all, EDITIONS.sites)).toBe(false)
    expect(peutRemplacer(all, EDITIONS.unites)).toBe(true)
    expect(EDITIONS.sites.dates?.map((d) => d.nom)).toEqual(['date_fermeture'])
  })

  it('lets a unit pick only a parent of a higher level', () => {
    const parent = EDITIONS.unites.champs.find((c) => c.nom === 'parent')!
    const direction = { type: 'direction' }
    const service = { type: 'service' }
    expect(parent.filtre!(direction, { type: 'departement' })).toBe(true)
    expect(parent.filtre!(service, { type: 'departement' })).toBe(false)
    expect(parent.filtre!(direction, { type: 'direction' })).toBe(false)
  })
})
