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
})
