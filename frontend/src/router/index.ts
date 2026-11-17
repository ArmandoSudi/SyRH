import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import * as audit from '@/features/audit/routes'
import * as auth from '@/features/auth/routes'
import * as dashboard from '@/features/dashboard/routes'
import * as design from '@/features/design/routes'
import * as referentiels from '@/features/referentiels/routes'
import * as systeme from '@/features/systeme/routes'
import AppShell from '@/shared/layouts/AppShell.vue'
import { MODULE_PERMISSIONS } from '@/shared/utils/modules'

import { installAuthGuards } from './guards'

// Each feature declares its own lazy-loaded routes; this file only assembles them.

// Stand-ins for modules the roadmap has not reached yet. Each one moves to its
// feature's routes.ts when that feature is built.
const placeholder = () => import('./PlaceholderView.vue')
const upcoming: RouteRecordRaw[] = (
  [
    ['agents', 'Agents'],
    ['carriere', 'Carrière'],
    ['personnel', 'Présences et absences'],
    ['paie', 'Paie'],
    ['social', 'Social'],
    ['formation', 'Formation'],
  ] as const
).map(([path, title]) => ({
  path,
  name: path,
  component: placeholder,
  meta: { title, permission: MODULE_PERMISSIONS[path] },
}))

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    ...auth.publicRoutes,
    {
      path: '/',
      component: AppShell,
      children: [
        ...dashboard.routes,
        ...upcoming,
        ...referentiels.routes,
        ...audit.routes,
        ...systeme.routes,
        ...design.routes,
        ...auth.routes,
      ],
    },
  ],
})

installAuthGuards(router)

router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} · SyRH` : 'SyRH'
})

export default router
