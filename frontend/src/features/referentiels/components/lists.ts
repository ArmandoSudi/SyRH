import { normalise } from '@/features/referentiels/components/tree'

/**
 * The rows of a flat list (fonctions, contract types) whose code or name contains
 * the text, ignoring case and accents.
 */
export function filterByCodeAndName<T extends { code: string; nom: string }>(
  rows: T[],
  texte: string,
): T[] {
  const wanted = normalise(texte.trim())
  if (!wanted) return rows
  return rows.filter((row) => normalise(`${row.code} ${row.nom}`).includes(wanted))
}
