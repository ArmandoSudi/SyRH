import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import * as authApi from '@/features/auth/api/auth'
import { ApiError } from '@/shared/utils/http'

import { useAuthStore } from '../auth'

vi.mock('@/features/auth/api/auth')

const marie: authApi.User = {
  id: 1,
  username: 'mkabila',
  first_name: 'Marie',
  last_name: 'Kabila',
  email: 'mkabila@example.org',
  groups: [],
  permissions: [],
}

describe('auth store', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
  })

  it('loads the signed-in user', async () => {
    vi.mocked(authApi.fetchMe).mockResolvedValue(marie)
    const auth = useAuthStore()

    await auth.init()

    expect(auth.isAuthenticated).toBe(true)
    expect(auth.displayName).toBe('Marie Kabila')
    expect(auth.initials).toBe('MK')
  })

  it('treats a 401 on start-up as anonymous, not as an error', async () => {
    vi.mocked(authApi.fetchMe).mockRejectedValue(new ApiError(401, 'non'))
    const auth = useAuthStore()

    await expect(auth.init()).resolves.toBeUndefined()

    expect(auth.isAuthenticated).toBe(false)
  })

  it('asks the server only once', async () => {
    vi.mocked(authApi.fetchMe).mockResolvedValue(marie)
    const auth = useAuthStore()

    await Promise.all([auth.init(), auth.init()])
    await auth.init()

    expect(authApi.fetchMe).toHaveBeenCalledTimes(1)
  })

  it('retries after a server failure', async () => {
    vi.mocked(authApi.fetchMe).mockRejectedValueOnce(new ApiError(502, 'panne'))
    vi.mocked(authApi.fetchMe).mockResolvedValueOnce(marie)
    const auth = useAuthStore()

    await expect(auth.init()).rejects.toBeInstanceOf(ApiError)
    await auth.init()

    expect(auth.isAuthenticated).toBe(true)
  })

  it('sets the user on login and clears it on logout', async () => {
    vi.mocked(authApi.login).mockResolvedValue(marie)
    vi.mocked(authApi.logout).mockResolvedValue()
    const auth = useAuthStore()

    await auth.login('mkabila', 'secret')
    expect(auth.user).toEqual(marie)

    await auth.logout()
    expect(auth.user).toBeNull()
    expect(authApi.fetchMe).not.toHaveBeenCalled()
  })

  it('falls back to the username when the name is empty', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ ...marie, first_name: '', last_name: '' })
    const auth = useAuthStore()

    await auth.login('mkabila', 'secret')

    expect(auth.displayName).toBe('mkabila')
    expect(auth.initials).toBe('MK')
  })

  it('answers can() from the permissions of the payload', async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      ...marie,
      groups: ['Rémunération'],
      permissions: ['accounts.access_agents', 'accounts.access_paie'],
    })
    const auth = useAuthStore()

    await auth.login('mkabila', 'secret')

    expect(auth.can('accounts.access_paie')).toBe(true)
    expect(auth.can('accounts.access_social')).toBe(false)
    expect(auth.can(undefined)).toBe(true)
    expect(auth.hasProfile).toBe(true)
    expect(auth.roleLabel).toBe('Rémunération')
  })

  it('lists every group in the role label', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ ...marie, groups: ['Formation', 'Social'] })
    const auth = useAuthStore()

    await auth.login('mkabila', 'secret')

    expect(auth.roleLabel).toBe('Formation, Social')
  })

  it('has no profile and no permission without a group', async () => {
    vi.mocked(authApi.login).mockResolvedValue(marie)
    const auth = useAuthStore()

    await auth.login('mkabila', 'secret')

    expect(auth.hasProfile).toBe(false)
    expect(auth.can('accounts.access_agents')).toBe(false)
  })
})
