import type {
  Evenement,
  PieceRequise,
  TypeDocument,
} from '@/features/referentiels/api/referentiels'
import { normalise, type Branch } from '@/features/referentiels/components/tree'

/**
 * Event kinds in the order of the agent's life, as the backend declares them in
 * apps/referentiels/models.py (Evenement, document types D2). A backend test checks
 * that this list matches. Every kind is shown, even with no requirement.
 */
export const EVENEMENTS: { value: Evenement; label: string }[] = [
  { value: 'engagement', label: 'Engagement' },
  { value: 'renouvellement', label: 'Renouvellement de contrat' },
  { value: 'avancement', label: "Avancement d'échelon" },
  { value: 'promotion', label: 'Promotion' },
  { value: 'mutation', label: 'Mutation ou changement de fonction' },
  { value: 'detachement', label: 'Détachement' },
  { value: 'disponibilite', label: 'Mise en disponibilité' },
  { value: 'reprise', label: 'Reprise de service' },
  { value: 'interim', label: 'Intérim' },
  { value: 'sanction', label: 'Sanction' },
  { value: 'distinction', label: 'Distinction' },
  { value: 'sortie', label: 'Sortie' },
  { value: 'mariage', label: 'Mariage' },
  { value: 'naissance', label: 'Naissance' },
  { value: 'fin_dependance', label: 'Fin de qualité de dépendant' },
  { value: 'formation', label: 'Formation' },
]

/** One row of the tree: an event kind, or a document it requires. */
export interface LignePiece {
  niveau: 'evenement' | 'piece'
  /** The document's code; empty for an event. */
  code: string
  /** The event's label, or the document's name. */
  nom: string
  /** For a document. */
  obligatoire: boolean | null
  /** For an event: how many documents it requires. */
  nombre: number | null
  date_ouverture: string | null
  date_fermeture: string | null
}

export interface PieceNode extends Branch<PieceNode> {
  data: LignePiece
  children: PieceNode[]
}

/**
 * Every event kind as a root, in order, with the documents it requires under it in
 * the API's order (mandatory first, then by name). A requirement whose type is not
 * in the list is still shown, by its id, rather than lost.
 */
export function buildPieces(types: TypeDocument[], pieces: PieceRequise[]): PieceNode[] {
  const typeById = new Map(types.map((t) => [t.id, t]))
  const roots = EVENEMENTS.map(({ value, label }): PieceNode => ({
    key: `ev-${value}`,
    data: {
      niveau: 'evenement',
      code: '',
      nom: label,
      obligatoire: null,
      nombre: 0,
      date_ouverture: null,
      date_fermeture: null,
    },
    children: [],
  }))
  const byEvent = new Map(EVENEMENTS.map(({ value }, i) => [value, roots[i]!]))

  for (const piece of pieces) {
    const parent = byEvent.get(piece.evenement)
    if (!parent) continue // an event kind this screen does not know yet
    const type = typeById.get(piece.type_document)
    parent.children.push({
      key: `pr-${piece.id}`,
      data: {
        niveau: 'piece',
        code: type?.code ?? '?',
        nom: type?.nom ?? `Type de pièce n° ${piece.type_document}`,
        obligatoire: piece.obligatoire,
        nombre: null,
        date_ouverture: piece.date_ouverture,
        date_fermeture: piece.date_fermeture,
      },
      children: [],
    })
    parent.data.nombre = parent.children.length
  }
  return roots
}

/**
 * Events whose label matches, with all their documents; otherwise events with the
 * documents whose code or name matches. Ignores case and accents.
 */
export function filterPieces(nodes: PieceNode[], text: string): PieceNode[] {
  const wanted = normalise(text.trim())
  if (!wanted) return nodes
  const matches = (node: PieceNode) =>
    normalise(`${node.data.code} ${node.data.nom}`).includes(wanted)
  return nodes.flatMap((event) => {
    if (matches(event)) return [event]
    const children = event.children.filter(matches)
    return children.length ? [{ ...event, children }] : []
  })
}

export function nombreLibelle(nombre: number): string {
  if (nombre === 0) return 'Aucune pièce exigée'
  return nombre === 1 ? '1 pièce' : `${nombre} pièces`
}
