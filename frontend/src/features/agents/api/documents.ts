import { request, upload } from '@/shared/utils/http'

export type TypeMime = 'application/pdf' | 'image/jpeg' | 'image/png'

/** One scanned document of an agent's file (document storage D20). */
export interface Document {
  id: number
  type_document: number
  type_document_code: string
  type_document_nom: string
  confidentiel: boolean
  nom_original: string
  type_mime: TypeMime
  /** Size of the file in bytes. */
  taille: number
  /** The date printed on the document, YYYY-MM-DD. */
  date_document: string | null
  retire: boolean
  motif_retrait: string
  date_retrait: string | null
  retire_par: number | null
  retire_par_nom: string | null
  cree_par: number | null
  cree_par_nom: string | null
  date_creation: string
  date_modification: string
  modifie_par: number | null
}

function base(agentId: number): string {
  return `/api/agents/${agentId}/documents/`
}

/** The documents the user may read, newest first; retired ones on request (D17, D18). */
export function listDocuments(agentId: number, retires = false): Promise<Document[]> {
  return request<Document[]>(`${base(agentId)}${retires ? '?retires=1' : ''}`)
}

export interface NouveauDocument {
  type_document: number
  fichier: File
  /** YYYY-MM-DD, optional. */
  date_document?: string | null
}

/** Uploads one document; onProgress receives a fraction from 0 to 1. */
export function uploadDocument(
  agentId: number,
  values: NouveauDocument,
  onProgress?: (fraction: number) => void,
): Promise<Document> {
  const form = new FormData()
  form.append('type_document', String(values.type_document))
  form.append('fichier', values.fichier, values.fichier.name)
  if (values.date_document) form.append('date_document', values.date_document)
  return upload<Document>(base(agentId), form, onProgress)
}

/** Retires a wrong upload with its reason; the file stays readable (D17). */
export function retireDocument(agentId: number, id: number, motif: string): Promise<Document> {
  return request<Document>(`${base(agentId)}${id}/retrait/`, {
    method: 'POST',
    body: { motif },
  })
}

/** Where the file is served: inline by default, as an attachment to download (D19). */
export function documentUrl(agentId: number, id: number, telechargement = false): string {
  return `${base(agentId)}${id}/fichier/${telechargement ? '?telechargement=1' : ''}`
}
