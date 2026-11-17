import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import * as authApi from '@/features/auth/api/auth'
import { ApiError } from '@/shared/utils/http'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<authApi.User | null>(null)
  const isAuthenticated = computed(() => user.value !== null)

  const displayName = computed(() => {
    if (!user.value) return ''
    const fullName = `${user.value.first_name} ${user.value.last_name}`.trim()
    return fullName || user.value.username
  })

  const initials = computed(() => {
    if (!user.value) return ''
    const { first_name, last_name, username } = user.value
    const letters = first_name && last_name ? first_name[0]! + last_name[0]! : username.slice(0, 2)
    return letters.toUpperCase()
  })

  const permissions = computed(() => new Set(user.value?.permissions ?? []))

  /** Whether the user holds a permission; no permission required means yes. */
  function can(permission?: string): boolean {
    return !permission || permissions.value.has(permission)
  }

  /** At least one profile (group): a user without one can open no module. */
  const hasProfile = computed(() => (user.value?.groups.length ?? 0) > 0)

  const roleLabel = computed(() => user.value?.groups.join(', ') ?? '')

  let initialising: Promise<void> | null = null

  /** Asks the server who is signed in. Runs once; later calls share the result. */
  function init(): Promise<void> {
    initialising ??= authApi.fetchMe().then(
      (me) => {
        user.value = me
      },
      (error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
          user.value = null
          return
        }
        // Server unreachable: let the next navigation try again.
        initialising = null
        throw error
      },
    )
    return initialising
  }

  async function login(username: string, password: string) {
    user.value = await authApi.login(username, password)
    initialising = Promise.resolve()
  }

  async function logout() {
    await authApi.logout()
    clear()
  }

  /** Forgets the user locally, when the server says the session is gone. */
  function clear() {
    user.value = null
    initialising = Promise.resolve()
  }

  return {
    user,
    isAuthenticated,
    displayName,
    initials,
    can,
    hasProfile,
    roleLabel,
    init,
    login,
    logout,
    clear,
  }
})
