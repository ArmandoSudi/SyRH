import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Menu from 'primevue/menu'
import type { MenuItem } from 'primevue/menuitem'
import { createMemoryHistory, createRouter } from 'vue-router'

import * as authApi from '@/features/auth/api/auth'
import { ApiError } from '@/shared/utils/http'
import { useAuthStore } from '@/features/auth/stores/auth'

import UserMenu from '../UserMenu.vue'

vi.mock('@/features/auth/api/auth')

async function mountMenu() {
  vi.mocked(authApi.login).mockResolvedValue({
    id: 1,
    username: 'mkabila',
    first_name: 'Marie',
    last_name: 'Kabila',
    email: '',
    groups: ['Gestion de carrière'],
    permissions: [],
  })
  await useAuthStore().login('mkabila', 'secret')

  const page = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: page },
      { path: '/connexion', component: page },
      { path: '/compte/mot-de-passe', name: 'password', component: page },
    ],
  })
  await router.push('/')
  const wrapper = mount(UserMenu, { global: { plugins: [router, PrimeVue] } })
  const items = wrapper.getComponent(Menu).props('model') as MenuItem[]
  const run = (label: string) =>
    items.find((item) => item.label === label)!.command!({
      originalEvent: new Event('click'),
      item: {},
    })
  return { wrapper, router, run }
}

describe('UserMenu', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
  })

  it("shows the user's name and initials", async () => {
    const { wrapper } = await mountMenu()

    expect(wrapper.get('[data-test="name"]').text()).toBe('Marie Kabila')
    expect(wrapper.get('[data-test="initials"]').text()).toBe('MK')
    expect(wrapper.get('[data-test="role"]').text()).toBe('Gestion de carrière')
  })

  it('signs out and goes to the login page', async () => {
    vi.mocked(authApi.logout).mockResolvedValue()
    const { router, run } = await mountMenu()

    run('Se déconnecter')
    await flushPromises()

    expect(authApi.logout).toHaveBeenCalledTimes(1)
    expect(useAuthStore().isAuthenticated).toBe(false)
    expect(router.currentRoute.value.path).toBe('/connexion')
  })

  it('still leaves when the session was already gone', async () => {
    vi.mocked(authApi.logout).mockRejectedValue(new ApiError(401, 'non'))
    const { router, run } = await mountMenu()

    run('Se déconnecter')
    await flushPromises()

    expect(useAuthStore().isAuthenticated).toBe(false)
    expect(router.currentRoute.value.path).toBe('/connexion')
  })

  it('opens the password screen', async () => {
    const { router, run } = await mountMenu()

    run('Changer le mot de passe')
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('password')
  })
})
