import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import * as authApi from '@/features/auth/api/auth'
import { ApiError, request } from '@/shared/utils/http'
import { useAuthStore } from '@/features/auth/stores/auth'

import { installAuthGuards, safeRedirect } from '../guards'

vi.mock('@/features/auth/api/auth')

type FetchMock = (url: string, init?: RequestInit) => Promise<unknown>

const marie: authApi.User = {
  id: 1,
  username: 'mkabila',
  first_name: 'Marie',
  last_name: 'Kabila',
  email: '',
  groups: [],
  permissions: [],
}

const page = { template: '<div />' }

function makeRouter() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/connexion', component: page, meta: { public: true } },
      { path: '/', component: page },
      { path: '/agents', component: page },
    ],
  })
  installAuthGuards(router)
  return router
}

describe('safeRedirect', () => {
  it('keeps paths inside the application', () => {
    expect(safeRedirect('/agents')).toBe('/agents')
    expect(safeRedirect('/agents?statut=actif#haut')).toBe('/agents?statut=actif#haut')
  })

  it.each([
    'https://example.com',
    '//evil.example',
    '/\\evil.example',
    'agents',
    'javascript:alert(1)',
    '',
    undefined,
    null,
    ['/agents'],
    '/connexion',
    '/connexion?redirect=/agents',
  ])('falls back to the dashboard for %j', (value) => {
    expect(safeRedirect(value)).toBe('/')
  })
})

describe('auth guards', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
  })

  it('sends an anonymous visitor to the login page, remembering the target', async () => {
    vi.mocked(authApi.fetchMe).mockRejectedValue(new ApiError(401, 'non'))
    const router = makeRouter()

    await router.push('/agents?statut=actif')

    expect(router.currentRoute.value.path).toBe('/connexion')
    expect(router.currentRoute.value.query).toEqual({ redirect: '/agents?statut=actif' })
  })

  it('adds no redirect when the target is the dashboard', async () => {
    vi.mocked(authApi.fetchMe).mockRejectedValue(new ApiError(401, 'non'))
    const router = makeRouter()

    await router.push('/')

    expect(router.currentRoute.value.fullPath).toBe('/connexion')
  })

  it('lets a signed-in user through', async () => {
    vi.mocked(authApi.fetchMe).mockResolvedValue(marie)
    const router = makeRouter()

    await router.push('/agents')

    expect(router.currentRoute.value.path).toBe('/agents')
  })

  it('never shows the login page to a signed-in user', async () => {
    vi.mocked(authApi.fetchMe).mockResolvedValue(marie)
    const router = makeRouter()

    await router.push('/connexion')
    expect(router.currentRoute.value.path).toBe('/')

    await router.push('/connexion?redirect=/agents')
    expect(router.currentRoute.value.path).toBe('/agents')
  })

  it('treats an unreachable API as anonymous', async () => {
    vi.mocked(authApi.fetchMe).mockRejectedValue(new TypeError('Failed to fetch'))
    const router = makeRouter()

    await router.push('/agents')

    expect(router.currentRoute.value.path).toBe('/connexion')
  })

  it('returns to the login page when the session expires mid-use', async () => {
    vi.mocked(authApi.fetchMe).mockResolvedValue(marie)
    const router = makeRouter()
    await router.push('/agents')
    vi.stubGlobal('fetch', vi.fn<FetchMock>().mockResolvedValue({ ok: false, status: 401 }))

    await expect(request('/api/health/')).rejects.toMatchObject({ status: 401 })
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/connexion'))

    expect(router.currentRoute.value.query).toEqual({ redirect: '/agents' })
    expect(useAuthStore().isAuthenticated).toBe(false)
    vi.unstubAllGlobals()
  })
})
