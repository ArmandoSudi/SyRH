import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { createMemoryHistory, createRouter } from 'vue-router'

import * as authApi from '@/api/auth'
import { ApiError } from '@/api/http'

import LoginView from '../LoginView.vue'

vi.mock('@/api/auth')

const marie: authApi.User = {
  id: 1,
  username: 'mkabila',
  first_name: 'Marie',
  last_name: 'Kabila',
  email: '',
}

async function mountLogin(url = '/connexion') {
  const page = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/connexion', component: LoginView },
      { path: '/', component: page },
      { path: '/agents', component: page },
    ],
  })
  await router.push(url)
  const wrapper = mount(LoginView, { global: { plugins: [router, PrimeVue] } })
  return { wrapper, router }
}

async function fillAndSubmit(wrapper: Awaited<ReturnType<typeof mountLogin>>['wrapper']) {
  await wrapper.get('#username').setValue('mkabila')
  await wrapper.get('#password').setValue('secret')
  await wrapper.get('form').trigger('submit')
}

describe('LoginView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
  })

  it('submits the credentials and goes to the dashboard', async () => {
    vi.mocked(authApi.login).mockResolvedValue(marie)
    const { wrapper, router } = await mountLogin()

    await fillAndSubmit(wrapper)
    await flushPromises()

    expect(authApi.login).toHaveBeenCalledWith('mkabila', 'secret')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('returns to the screen first asked for', async () => {
    vi.mocked(authApi.login).mockResolvedValue(marie)
    const { wrapper, router } = await mountLogin('/connexion?redirect=/agents')

    await fillAndSubmit(wrapper)
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/agents')
  })

  it('ignores a redirect to another site', async () => {
    vi.mocked(authApi.login).mockResolvedValue(marie)
    const { wrapper, router } = await mountLogin('/connexion?redirect=https://example.com')

    await fillAndSubmit(wrapper)
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/')
  })

  it('shows the server message and empties the password on failure', async () => {
    vi.mocked(authApi.login).mockRejectedValue(
      new ApiError(400, 'Identifiant ou mot de passe incorrect.'),
    )
    const { wrapper, router } = await mountLogin()

    await fillAndSubmit(wrapper)
    await flushPromises()

    expect(wrapper.get('[data-test="error"]').text()).toBe('Identifiant ou mot de passe incorrect.')
    expect((wrapper.get('#username').element as HTMLInputElement).value).toBe('mkabila')
    expect((wrapper.get('#password').element as HTMLInputElement).value).toBe('')
    expect(router.currentRoute.value.path).toBe('/connexion')
  })

  it('shows a generic message when the server is unreachable', async () => {
    vi.mocked(authApi.login).mockRejectedValue(new TypeError('Failed to fetch'))
    const { wrapper } = await mountLogin()

    await fillAndSubmit(wrapper)
    await flushPromises()

    expect(wrapper.get('[data-test="error"]').text()).toContain('Connexion impossible')
  })

  it('disables the button while signing in', async () => {
    let finish: (user: authApi.User) => void = () => {}
    vi.mocked(authApi.login).mockReturnValue(new Promise((resolve) => (finish = resolve)))
    const { wrapper } = await mountLogin()

    await fillAndSubmit(wrapper)

    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    await wrapper.get('form').trigger('submit')
    expect(authApi.login).toHaveBeenCalledTimes(1)

    finish(marie)
    await flushPromises()
  })

  it('keeps the button disabled until both fields are filled', async () => {
    const { wrapper } = await mountLogin()

    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
  })
})
