import type { RouteRecordRaw } from 'vue-router'

import { MODULE_PERMISSIONS } from '@/shared/utils/modules'

export const routes: RouteRecordRaw[] = [
  {
    path: 'systeme',
    name: 'systeme',
    component: () => import('./views/SystemView.vue'),
    meta: { title: 'Système', permission: MODULE_PERMISSIONS.systeme },
  },
]
