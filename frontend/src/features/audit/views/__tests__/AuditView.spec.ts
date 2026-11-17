import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'

import * as auditApi from '@/features/audit/api/audit'
import type { AuditEntry } from '@/features/audit/api/audit'
import { useAuditStore } from '@/features/audit/stores/audit'
import * as authApi from '@/features/auth/api/auth'
import { useAuthStore } from '@/features/auth/stores/auth'
import { MODULE_PERMISSIONS } from '@/shared/utils/modules'

import AuditView from '../AuditView.vue'

vi.mock('@/features/audit/api/audit')
vi.mock('@/features/auth/api/auth')

function row(id: number, overrides: Partial<AuditEntry> = {}): AuditEntry {
  return {
    id,
    date: '2026-11-17T10:15:00+01:00',
    auteur: { id: 2, nom: 'Aline Mbuyi' },
    action: 'modification',
    action_libelle: 'Modification',
    module: 'comptes',
    module_libelle: 'Comptes',
    table: { cle: 'accounts.user', libelle: 'Utilisateur' },
    objet_id: id,
    objet_libelle: `ligne ${id}`,
    ...overrides,
  }
}

async function signInWith(permissions: string[]) {
  vi.mocked(authApi.login).mockResolvedValue({
    id: 1,
    username: 'auditeur',
    first_name: '',
    last_name: '',
    email: '',
    groups: ['Auditeur'],
    permissions,
  })
  await useAuthStore().login('auditeur', 'x')
}

async function mountView() {
  const wrapper = mount(AuditView, {
    global: { plugins: [PrimeVue], stubs: { teleport: true } },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

describe('AuditView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  beforeEach(async () => {
    vi.resetAllMocks()
    // jsdom has no matchMedia; PrimeVue's DatePicker listens to it for its layout.
    vi.stubGlobal(
      'matchMedia',
      vi.fn<() => Partial<MediaQueryList>>(() => ({
        matches: false,
        addEventListener: vi.fn<MediaQueryList['addEventListener']>(),
        removeEventListener: vi.fn<MediaQueryList['removeEventListener']>(),
      })),
    )
    setActivePinia(createPinia())
    await signInWith([MODULE_PERMISSIONS.audit, MODULE_PERMISSIONS.agents])
    vi.mocked(auditApi.fetchEntries).mockResolvedValue({
      count: 120,
      next: '/api/audit/entrees/?page=2',
      previous: null,
      results: [row(1), row(2, { action: 'creation', action_libelle: 'Création' })],
    })
  })

  it('renders one page of entries from the API', async () => {
    const wrapper = await mountView()

    expect(auditApi.fetchEntries).toHaveBeenCalledWith({
      date_debut: undefined,
      date_fin: undefined,
      auteur: undefined,
      module: undefined,
      action: undefined,
      page: undefined,
    })
    const cells = wrapper.findAll('tbody tr').map((tr) => tr.findAll('td').map((td) => td.text()))
    expect(cells[0]).toEqual([
      '17/11/2026 10:15:00',
      'Aline Mbuyi',
      'Modification',
      'Comptes',
      'Utilisateur',
      'ligne 1',
    ])
    expect(wrapper.get('[data-test="total"]').text()).toBe('120 entrées')
    wrapper.unmount()
  })

  it('asks the API for the next page', async () => {
    const wrapper = await mountView()

    await wrapper.get('.p-paginator-next').trigger('click')
    await flushPromises()

    expect(useAuditStore().page).toBe(2)
    expect(auditApi.fetchEntries).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 }))
    wrapper.unmount()
  })

  it('reloads from page 1 when a filter changes', async () => {
    const wrapper = await mountView()
    const store = useAuditStore()
    store.page = 3
    await flushPromises()

    store.action = 'creation'
    await flushPromises()

    expect(store.page).toBe(1)
    expect(auditApi.fetchEntries).toHaveBeenLastCalledWith(
      expect.objectContaining({ action: 'creation', page: undefined }),
    )
    wrapper.unmount()
  })

  it('offers only the reader’s modules plus Comptes', async () => {
    const wrapper = await mountView()

    await wrapper.get('[data-test="module-filter"]').trigger('click')
    await flushPromises()

    const options = [...document.body.querySelectorAll('[role="option"]')].map((li) =>
      li.textContent?.trim(),
    )
    expect(options).toEqual(['Agents', 'Comptes'])
    wrapper.unmount()
  })

  it('opens the detail of a clicked entry', async () => {
    vi.mocked(auditApi.fetchEntry).mockResolvedValue({
      ...row(1),
      changements: [{ champ: 'first_name', libelle: 'prénom', avant: 'Marie', apres: 'Mariam' }],
    })
    const wrapper = await mountView()

    await wrapper.get('tbody tr').trigger('click')
    await flushPromises()

    expect(auditApi.fetchEntry).toHaveBeenCalledWith(1)
    expect(document.body.querySelector('[data-test="audit-panel"]')?.textContent).toContain(
      'Mariam',
    )
    wrapper.unmount()
  })

  it('shows an error when the log cannot be loaded', async () => {
    vi.mocked(auditApi.fetchEntries).mockRejectedValue(new Error('API responded with HTTP 502'))

    const wrapper = await mountView()

    expect(wrapper.get('[data-test="error"]').text()).toContain('HTTP 502')
    wrapper.unmount()
  })

  it('offers no action that changes data', async () => {
    const wrapper = await mountView()

    const labels = wrapper.findAll('button').map((b) => b.attributes('aria-label') ?? b.text())
    expect(labels.join(' ')).not.toMatch(/supprimer|modifier|enregistrer/i)
    wrapper.unmount()
  })
})
