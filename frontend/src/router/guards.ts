import type { Router } from 'vue-router'

import { setUnauthorizedHandler } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

export const LOGIN_PATH = '/connexion'

/**
 * Where to go after signing in. Only paths inside the application are
 * honoured, so a crafted link cannot bounce the user to another site.
 */
export function safeRedirect(value: unknown): string {
  if (typeof value !== 'string') return '/'
  const isLocalPath = value.startsWith('/') && !value.startsWith('//') && !value.includes('\\')
  if (!isLocalPath || value.split(/[?#]/)[0] === LOGIN_PATH) return '/'
  return value
}

/** Routes are protected by default; a route opts out with `meta.public`. */
export function installAuthGuards(router: Router) {
  router.beforeEach(async (to) => {
    const auth = useAuthStore()
    try {
      await auth.init()
    } catch {
      // API unreachable: treat as anonymous; the login page reports the failure.
    }

    if (to.meta.public) {
      return auth.isAuthenticated && to.path === LOGIN_PATH ? safeRedirect(to.query.redirect) : true
    }
    if (!auth.isAuthenticated) {
      const query = to.fullPath === '/' ? {} : { redirect: to.fullPath }
      return { path: LOGIN_PATH, query }
    }
    return true
  })

  // The session expired while the user was working: back to the login page,
  // remembering the screen they were on.
  setUnauthorizedHandler(() => {
    useAuthStore().clear()
    const current = router.currentRoute.value
    if (current.path === LOGIN_PATH) return
    const query = current.fullPath === '/' ? {} : { redirect: current.fullPath }
    void router.push({ path: LOGIN_PATH, query })
  })
}
