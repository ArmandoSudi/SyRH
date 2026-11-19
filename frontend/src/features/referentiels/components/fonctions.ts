import type { Nature } from '@/features/referentiels/api/referentiels'

export const NATURE_SEVERITY: Record<Nature, 'primary' | 'secondary'> = {
  responsabilite: 'primary',
  execution: 'secondary',
}
