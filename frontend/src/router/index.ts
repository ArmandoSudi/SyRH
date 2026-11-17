import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import * as auth from '@/features/auth/routes'
import * as dashboard from '@/features/dashboard/routes'
import * as design from '@/features/design/routes'
import * as systeme from '@/features/systeme/routes'
import AppShell from '@/shared/layouts/AppShell.vue'

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
    ['referentiels', 'Référentiels'],
  ] as const
).map(([path, title]) => ({ path, name: path, component: placeholder, meta: { title } }))

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
