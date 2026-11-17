import type { RouteRecordRaw } from 'vue-router'

import { MODULE_PERMISSIONS } from '@/shared/utils/modules'

export const routes: RouteRecordRaw[] = [
  {
    path: 'referentiels',
    name: 'referentiels',
    component: () => import('./views/ReferentielsView.vue'),
    meta: { title: 'Référentiels', permission: MODULE_PERMISSIONS.referentiels },
  },
]
