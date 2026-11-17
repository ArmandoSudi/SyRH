import type { RouteRecordRaw } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  {
    path: 'systeme',
    name: 'systeme',
    component: () => import('./views/SystemView.vue'),
    meta: { title: 'Système' },
  },
]
