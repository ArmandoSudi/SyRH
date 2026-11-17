import type { RouteRecordRaw } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  {
    path: 'design',
    name: 'design',
    component: () => import('./views/DesignView.vue'),
    meta: { title: 'Système de design' },
  },
]
