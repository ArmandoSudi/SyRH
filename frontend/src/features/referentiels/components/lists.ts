import { normalise } from '@/features/referentiels/components/tree'

/**
 * The rows of a flat list (fonctions, contract types, exit reasons, suspension types,
 * banks) whose code, name, required document or SWIFT/BIC contains the text, ignoring
 * case and accents.
 */
export function filterByCodeAndName<
  T extends { code: string; nom: string; type_document_libelle?: string; swift?: string },
>(rows: T[], texte: string): T[] {
  const wanted = normalise(texte.trim())
  if (!wanted) return rows
  return rows.filter((row) =>
    normalise(
      `${row.code} ${row.nom} ${row.type_document_libelle ?? ''} ${row.swift ?? ''}`,
    ).includes(wanted),
  )
}
