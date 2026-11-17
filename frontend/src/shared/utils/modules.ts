/**
 * Which permission opens which SyRH module.
 *
 * Mirrors apps/accounts/roles.py on the backend. Routes (meta.permission) and
 * the side menu both read this map, so a module is shown and opened under the
 * same rule. Hiding is a convenience: the API checks access on its own.
 */
export const MODULE_PERMISSIONS = {
  agents: 'accounts.access_agents',
  carriere: 'accounts.access_carriere',
  personnel: 'accounts.access_personnel',
  paie: 'accounts.access_paie',
  social: 'accounts.access_social',
  formation: 'accounts.access_formation',
  referentiels: 'accounts.access_referentiels',
  systeme: 'accounts.access_systeme',
} as const

export type ModuleKey = keyof typeof MODULE_PERMISSIONS
