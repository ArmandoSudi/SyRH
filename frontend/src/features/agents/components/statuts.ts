import type { StatutAgent } from '@/features/agents/api/agents'

/**
 * An agent's statuses in display order, as the backend declares them in
 * apps/agents/models.py (StatutAgent, agent list D2). A backend test checks that this
 * list matches.
 */
export const STATUTS: { value: StatutAgent; label: string }[] = [
  { value: 'actif', label: 'En activité' },
  { value: 'a_venir', label: 'À venir' },
  { value: 'inactif', label: 'Sans contrat en cours' },
  { value: 'sans_contrat', label: 'Sans contrat' },
]

export const STATUT_DEFAUT: StatutAgent[] = ['actif']

/** The tag colour of a status. */
export function statutSeverity(statut: StatutAgent | undefined): string {
  switch (statut) {
    case 'actif':
      return 'success'
    case 'a_venir':
      return 'info'
    case 'inactif':
      return 'warn'
    default:
      return 'secondary'
  }
}
