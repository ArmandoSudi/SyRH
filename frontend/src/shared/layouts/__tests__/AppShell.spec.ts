import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { createMemoryHistory, createRouter } from 'vue-router'

import * as authApi from '@/features/auth/api/auth'
import { useAuthStore } from '@/features/auth/stores/auth'
import { MODULE_PERMISSIONS } from '@/shared/utils/modules'

import AppShell from '../AppShell.vue'

vi.mock('@/features/auth/api/auth')

const page = { template: '<div data-test="page">page</div>' }

async function mountAs(permissions: string[], url = '/') {
  vi.mocked(authApi.login).mockResolvedValue({
    id: 1,
    username: 'u',
    first_name: 'Test',
    last_name: 'User',
    email: '',
    groups: permissions.length ? ['Profil'] : [],
    permissions,
  })
  await useAuthStore().login('u', 'p')

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/',
        component: AppShell,
        children: [
          { path: '', component: page },
          ...Object.entries(MODULE_PERMISSIONS).map(([key, permission]) => ({
            path: key,
            component: page,
            meta: { title: key, permission },
          })),
          { path: 'design', component: page, meta: { permission: MODULE_PERMISSIONS.systeme } },
        ],
      },
    ],
  })
  await router.push(url)
  const wrapper = mount({ template: '<RouterView />' }, { global: { plugins: [router, PrimeVue] } })
  await flushPromises()
  return { wrapper, router }
}

function menu(wrapper: Awaited<ReturnType<typeof mountAs>>['wrapper']) {
  return wrapper.findAll('nav a').map((link) => link.attributes('href'))
}

describe('AppShell', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
  })

  it('shows only the modules of the user', async () => {
    const { wrapper } = await mountAs([
      MODULE_PERMISSIONS.agents,
      MODULE_PERMISSIONS.paie,
      MODULE_PERMISSIONS.referentiels,
    ])

    expect(menu(wrapper)).toEqual(['/', '/agents', '/paie', '/referentiels'])
    expect(wrapper.find('.group').exists()).toBe(true)
  })

  it('shows the technical pages to the system administrator', async () => {
    const { wrapper } = await mountAs([MODULE_PERMISSIONS.referentiels, MODULE_PERMISSIONS.systeme])

    expect(menu(wrapper)).toEqual(['/', '/referentiels', '/systeme', '/design'])
  })

  it('hides the Administration heading when it would be empty', async () => {
    const { wrapper } = await mountAs([])

    expect(menu(wrapper)).toEqual(['/'])
    expect(wrapper.find('.group').exists()).toBe(false)
  })

  it('refuses a module without its permission, keeping the URL', async () => {
    const { wrapper, router } = await mountAs([MODULE_PERMISSIONS.agents], '/social')

    expect(wrapper.find('[data-test="access-denied"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="page"]').exists()).toBe(false)
    expect(router.currentRoute.value.path).toBe('/social')
    expect(wrapper.get('[data-test="access-denied"] a').attributes('href')).toBe('/')
  })

  it('opens a module with its permission', async () => {
    const { wrapper } = await mountAs([MODULE_PERMISSIONS.social], '/social')

    expect(wrapper.find('[data-test="page"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="access-denied"]').exists()).toBe(false)
  })
})
