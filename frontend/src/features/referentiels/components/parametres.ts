import type { CleParametre, Parametre } from '@/features/referentiels/api/referentiels'

/**
 * The general parameters in display order, as the backend declares them in
 * apps/referentiels/models.py (Cle, general parameters D2). A backend test checks that
 * this list matches. Every key is shown, even with no value at the date.
 */
export const PARAMETRES: { cle: CleParametre; libelle: string }[] = [
  { cle: 'age_limite_enfant', libelle: 'Âge limite des enfants à charge' },
  { cle: 'enfants_max', libelle: "Nombre maximal d'enfants pris en charge" },
  { cle: 'age_retraite', libelle: 'Âge de la retraite' },
  { cle: 'duree_carriere', libelle: 'Durée de carrière avant la retraite' },
]

/** One row of the tab: a key and its value at the date, or none. */
export interface LigneParametre {
  cle: string
  libelle: string
  parametre: Parametre | null
}

/**
 * One row per key of PARAMETRES, in order, with its value open at the date or null;
 * a row whose key the client does not know yet is kept at the end, not lost.
 */
export function buildParametres(rows: Parametre[]): LigneParametre[] {
  const byKey = new Map(rows.map((row) => [row.cle as string, row]))
  const known = PARAMETRES.map(({ cle, libelle }) => ({
    cle,
    libelle,
    parametre: byKey.get(cle) ?? null,
  }))
  const keys = new Set<string>(PARAMETRES.map((p) => p.cle))
  const unknown = rows
    .filter((row) => !keys.has(row.cle))
    .map((row) => ({ cle: row.cle, libelle: row.cle_libelle, parametre: row }))
  return [...known, ...unknown]
}

/** "25 ans", or "Non renseigné" when the key has no value at the date. */
export function valeurLibelle(ligne: LigneParametre): string {
  const p = ligne.parametre
  return p ? `${p.valeur} ${p.unite}` : 'Non renseigné'
}
