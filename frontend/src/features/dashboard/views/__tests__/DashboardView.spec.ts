import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'

import * as authApi from '@/features/auth/api/auth'
import { useAuthStore } from '@/features/auth/stores/auth'

import DashboardView from '../DashboardView.vue'

vi.mock('@/features/auth/api/auth')

async function mountWithGroups(groups: string[]) {
  vi.mocked(authApi.login).mockResolvedValue({
    id: 1,
    username: 'u',
    first_name: '',
    last_name: '',
    email: '',
    groups,
    permissions: [],
  })
  await useAuthStore().login('u', 'p')
  return mount(DashboardView, { global: { plugins: [PrimeVue] } })
}

describe('DashboardView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
  })

  it('tells a user without profile to contact the administrator', async () => {
    const wrapper = await mountWithGroups([])

    expect(wrapper.get('[data-test="no-profile"]').text()).toContain('Aucun profil')
  })

  it('shows no notice to a user with a profile', async () => {
    const wrapper = await mountWithGroups(['Formation'])

    expect(wrapper.find('[data-test="no-profile"]').exists()).toBe(false)
  })
})
