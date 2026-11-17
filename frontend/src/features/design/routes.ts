import type { RouteRecordRaw } from 'vue-router'

import { MODULE_PERMISSIONS } from '@/shared/utils/modules'

export const routes: RouteRecordRaw[] = [
  {
    path: 'design',
    name: 'design',
    component: () => import('./views/DesignView.vue'),
    meta: { title: 'Système de design', permission: MODULE_PERMISSIONS.systeme },
  },
]
