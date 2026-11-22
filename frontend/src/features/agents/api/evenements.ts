import { request } from '@/shared/utils/http'

/** A document as an event lists it, with the link that attaches it (documents on events D21). */
export interface PieceEvenement {
  id: number
  lien: number | null
  nom_original: string
  type_document_code: string
  type_mime: string
}

/** A required piece of an event, satisfied or missing. */
export interface PieceExigee {
  code: string
  nom: string
  obligatoire: boolean
  satisfaite: boolean
  /** The documents the user may read. */
  documents: PieceEvenement[]
  /** Attached documents the user may not read (confidential). */
  confidentielles: number
}

export type ModeleEvenement = 'contrat' | 'affectation' | 'classement'

/** One event of an agent with its pieces and status (documents on events D21). */
export interface EvenementEtat {
  cle: string
  modele: ModeleEvenement
  id: number
  /** The event kind; null when the row belongs to the hiring. */
  evenement: string | null
  evenement_libelle: string
  /** YYYY-MM-DD. */
  date: string
  libelle: string
  complet: boolean
  manquantes: string[]
  pieces: PieceExigee[]
  autres: PieceEvenement[]
  autres_confidentielles: number
}

function base(agentId: number): string {
  return `/api/agents/${agentId}/evenements/`
}

/** The agent's events, newest first, with their required pieces. */
export function listEvenements(agentId: number): Promise<EvenementEtat[]> {
  return request<EvenementEtat[]>(base(agentId))
}

/** Attaches one of the agent's documents to an event; returns the event's new status. */
export function attachDocument(
  agentId: number,
  evenement: Pick<EvenementEtat, 'modele' | 'id'>,
  documentId: number,
): Promise<EvenementEtat> {
  return request<EvenementEtat>(`${base(agentId)}${evenement.modele}/${evenement.id}/pieces/`, {
    method: 'POST',
    body: { document: documentId },
  })
}

/** Removes a link; the document stays in the file (D4). */
export function detachDocument(
  agentId: number,
  evenement: Pick<EvenementEtat, 'modele' | 'id'>,
  lien: number,
): Promise<EvenementEtat> {
  return request<EvenementEtat>(
    `${base(agentId)}${evenement.modele}/${evenement.id}/pieces/${lien}/retrait/`,
    { method: 'POST' },
  )
}
