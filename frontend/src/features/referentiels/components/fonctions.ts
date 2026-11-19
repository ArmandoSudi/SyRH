import type { Fonction, Nature } from '@/features/referentiels/api/referentiels'
import { normalise } from '@/features/referentiels/components/tree'

export const NATURE_SEVERITY: Record<Nature, 'primary' | 'secondary'> = {
  responsabilite: 'primary',
  execution: 'secondary',
}

/** The fonctions whose code or name contains the text, ignoring case and accents. */
export function filterFonctions(fonctions: Fonction[], texte: string): Fonction[] {
  const wanted = normalise(texte.trim())
  if (!wanted) return fonctions
  return fonctions.filter((f) => normalise(`${f.code} ${f.nom}`).includes(wanted))
}
