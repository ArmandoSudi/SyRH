import { request } from '@/shared/utils/http'

export type AuditAction = 'creation' | 'modification' | 'suppression'

/** One changed field. A many-to-many field has ajoutes / retires instead of avant / apres. */
export interface AuditChange {
  champ: string
  libelle: string
  avant?: unknown
  apres?: unknown
  ajoutes?: string[]
  retires?: string[]
}

export interface AuditEntry {
  id: number
  /** ISO date and time, with offset. */
  date: string
  auteur: { id: number | null; nom: string }
  action: AuditAction
  action_libelle: string
  module: string
  module_libelle: string
  table: { cle: string; libelle: string }
  objet_id: number
  objet_libelle: string
}

export interface AuditEntryDetail extends AuditEntry {
  changements: AuditChange[]
}

export interface Page<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Filters of the list, in the API's own names (D24). */
export interface AuditQuery {
  date_debut?: string
  date_fin?: string
  auteur?: string
  module?: string
  action?: AuditAction
  page?: number
}

export function toQueryString(query: AuditQuery): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  }
  const text = params.toString()
  return text ? `?${text}` : ''
}

export function fetchEntries(query: AuditQuery): Promise<Page<AuditEntry>> {
  return request<Page<AuditEntry>>(`/api/audit/entrees/${toQueryString(query)}`)
}

export function fetchEntry(id: number): Promise<AuditEntryDetail> {
  return request<AuditEntryDetail>(`/api/audit/entrees/${id}/`)
}
