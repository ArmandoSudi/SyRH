import type { RouteRecordRaw } from 'vue-router'

import { MODULE_PERMISSIONS } from '@/shared/utils/modules'

export const routes: RouteRecordRaw[] = [
  {
    path: 'audit',
    name: 'audit',
    component: () => import('./views/AuditView.vue'),
    meta: { title: "Journal d'audit", permission: MODULE_PERMISSIONS.audit },
  },
]
