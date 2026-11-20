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

  it('describes the six tables, each with a code or a key', () => {
    expect(Object.keys(EDITIONS)).toHaveLength(6)
    for (const edition of Object.values(EDITIONS)) {
      const names = edition.champs.map((c) => c.nom)
      expect(names.includes('code') || names.includes('cle')).toBe(true)
      expect(edition.confirmation).toMatch(/enregistrée?\.$/)
    }
  })
})
