import type { RouteRecordRaw } from 'vue-router'

import { MODULE_PERMISSIONS } from '@/shared/utils/modules'

export const routes: RouteRecordRaw[] = [
  {
    path: 'agents',
    name: 'agents',
    component: () => import('./views/AgentListView.vue'),
    meta: { title: 'Agents', permission: MODULE_PERMISSIONS.agents },
  },
  {
    path: 'agents/nouveau',
    name: 'agents-nouveau',
    component: () => import('./views/AgentCreateView.vue'),
    meta: { title: 'Engager un agent', permission: 'agents.add_agent' },
  },
  {
    path: 'agents/pieces',
    name: 'agents-pieces',
    component: () => import('./views/AgentDocumentsView.vue'),
    meta: { title: 'Pièces des agents', permission: MODULE_PERMISSIONS.agents },
  },
]
