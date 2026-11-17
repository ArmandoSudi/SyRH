import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'

import type { AuditEntryDetail } from '@/features/audit/api/audit'

import AuditEntryPanel from '../AuditEntryPanel.vue'
import { formatValue } from '../format'

function entry(overrides: Partial<AuditEntryDetail>): AuditEntryDetail {
  return {
    id: 1,
    date: '2026-11-17T10:15:00+01:00',
    auteur: { id: 2, nom: 'Aline Mbuyi' },
    action: 'modification',
    action_libelle: 'Modification',
    module: 'comptes',
    module_libelle: 'Comptes',
    table: { cle: 'accounts.user', libelle: 'Utilisateur' },
    objet_id: 7,
    objet_libelle: 'mkabila',
    changements: [],
    ...overrides,
  }
}

function rows(data: AuditEntryDetail) {
  const wrapper = mount(AuditEntryPanel, {
    props: { entry: data },
    global: { plugins: [PrimeVue] },
  })
  return {
    wrapper,
    cells: wrapper
      .findAll('[data-test="change"]')
      .map((row) => row.findAll('th, td').map((cell) => cell.text())),
  }
}

describe('AuditEntryPanel', () => {
  it('shows old and new values of a modification', () => {
    const { wrapper, cells } = rows(
      entry({
        changements: [
          { champ: 'first_name', libelle: 'prénom', avant: 'Marie', apres: 'Mariam' },
          { champ: 'password', libelle: 'mot de passe', avant: '••••••', apres: '••••••' },
        ],
      }),
    )

    expect(wrapper.text()).toContain('Aline Mbuyi')
    expect(wrapper.text()).toContain('Utilisateur · Comptes')
    expect(cells).toEqual([
      ['prénom', 'Marie', 'Mariam'],
      ['mot de passe', '••••••', '••••••'],
    ])
  })

  it('shows a creation with empty old values', () => {
    const { cells } = rows(
      entry({
        action: 'creation',
        action_libelle: 'Création',
        changements: [{ champ: 'name', libelle: 'nom', avant: null, apres: 'Social' }],
      }),
    )

    expect(cells).toEqual([['nom', '—', 'Social']])
  })

  it('shows a deletion and many-to-many changes', () => {
    const { cells } = rows(
      entry({
        action: 'suppression',
        action_libelle: 'Suppression',
        changements: [
          { champ: 'nom', libelle: 'nom', avant: 'Kinshasa', apres: null },
          { champ: 'groups', libelle: 'groupes', ajoutes: ['Social'], retires: ['Formation'] },
        ],
      }),
    )

    expect(cells).toEqual([
      ['nom', 'Kinshasa', '—'],
      ['groupes', 'Retirés : Formation', 'Ajoutés : Social'],
    ])
  })

  it('formats every kind of stored value', () => {
    expect(formatValue(true)).toBe('Oui')
    expect(formatValue(false)).toBe('Non')
    expect(formatValue({ id: 3, libelle: 'Kinshasa' })).toBe('Kinshasa')
    expect(formatValue('2026-11-17')).toBe('17/11/2026')
    expect(formatValue('2026-11-17T10:15:00+01:00')).toBe('17/11/2026 10:15:00')
    expect(formatValue('12.50')).toBe('12.50')
    expect(formatValue('')).toBe('—')
  })
})
