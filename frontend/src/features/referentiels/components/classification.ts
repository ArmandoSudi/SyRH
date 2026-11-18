import type { Categorie, Echelon, Grade } from '@/features/referentiels/api/referentiels'
import type { Branch } from '@/features/referentiels/components/tree'

export type Niveau = 'categorie' | 'grade' | 'echelon'

export const NIVEAU_LIBELLE: Record<Niveau, string> = {
  categorie: 'Catégorie',
  grade: 'Grade',
  echelon: 'Échelon',
}

export const NIVEAU_SEVERITY: Record<Niveau, 'primary' | 'info' | 'secondary'> = {
  categorie: 'primary',
  grade: 'info',
  echelon: 'secondary',
}

/** One row of the tree, whatever its level, so one TreeTable draws them all. */
export interface LigneClassification {
  niveau: Niveau
  id: number
  /** Empty for an échelon, which has no code of its own. */
  code: string
  /** "Échelon 3" for an échelon. */
  nom: string
  /** Empty for an échelon, ordered by its number. */
  rang: number | null
  date_ouverture: string
  date_fermeture: string | null
  /** What the text filter searches: an échelon is found by its grade's code. */
  recherche: string
}

export interface ClassificationNode extends Branch<ClassificationNode> {
  data: LigneClassification
  children: ClassificationNode[]
}

function node(
  data: Omit<LigneClassification, 'recherche'>,
  recherche?: string,
): ClassificationNode {
  // Keys carry the level: a catégorie and a grade may share an id.
  return {
    key: `${data.niveau[0]}-${data.id}`,
    data: { ...data, recherche: recherche ?? `${data.code} ${data.nom}` },
    children: [],
  }
}

/** Higher rank first (classification D7); échelons by number (D8); then oldest first. */
function bySiblingOrder(a: ClassificationNode, b: ClassificationNode): number {
  if (a.data.niveau === 'echelon' && b.data.niveau === 'echelon') {
    return a.data.nom.localeCompare(b.data.nom, 'fr', { numeric: true })
  }
  return (
    (b.data.rang ?? 0) - (a.data.rang ?? 0) ||
    a.data.date_ouverture.localeCompare(b.data.date_ouverture)
  )
}

/**
 * The three flat lists from the API as one tree, catégorie → grade → échelon.
 * A row whose parent is not in its list is shown at the root rather than lost.
 */
export function buildClassification(
  categories: Categorie[],
  grades: Grade[],
  echelons: Echelon[],
): ClassificationNode[] {
  const roots: ClassificationNode[] = []
  const byCategorie = new Map<number, ClassificationNode>()
  const byGrade = new Map<number, ClassificationNode>()

  for (const c of categories) {
    const n = node({ niveau: 'categorie', ...pick(c), code: c.code, nom: c.nom, rang: c.rang })
    byCategorie.set(c.id, n)
    roots.push(n)
  }
  for (const g of grades) {
    const n = node({ niveau: 'grade', ...pick(g), code: g.code, nom: g.nom, rang: g.rang })
    byGrade.set(g.id, n)
    ;(byCategorie.get(g.categorie)?.children ?? roots).push(n)
  }
  for (const e of echelons) {
    const n = node(
      { niveau: 'echelon', ...pick(e), code: '', nom: `Échelon ${e.numero}`, rang: null },
      e.libelle,
    )
    ;(byGrade.get(e.grade)?.children ?? roots).push(n)
  }

  const sort = (list: ClassificationNode[]) => {
    list.sort(bySiblingOrder)
    list.forEach((child) => sort(child.children))
  }
  sort(roots)
  return roots
}

function pick(row: Categorie | Grade | Echelon) {
  return { id: row.id, date_ouverture: row.date_ouverture, date_fermeture: row.date_fermeture }
}

export function searchText(node: ClassificationNode): string {
  return node.data.recherche
}
