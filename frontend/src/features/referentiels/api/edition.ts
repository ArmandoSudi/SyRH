import { request } from '@/shared/utils/http'

/** The reference tables editable in SyRH: the six flat lists (reference data screens D1)
 * and the seven tree tables (tree reference screens D1). */
export type TableEditable =
  | 'fonctions'
  | 'types-contrat'
  | 'banques'
  | 'motifs-sortie'
  | 'types-suspension'
  | 'parametres'
  | 'sites'
  | 'unites'
  | 'categories'
  | 'grades'
  | 'echelons'
  | 'types-document'
  | 'pieces-requises'

export type Valeurs = Record<string, unknown>

const url = (table: TableEditable) => `/api/referentiels/${table}/`

/** Creates a row; the server answers with the saved row. */
export function creer<T>(table: TableEditable, data: Valeurs): Promise<T> {
  return request<T>(url(table), { method: 'POST', body: data })
}

/** Corrects a row in place, closing date included (D3). */
export function corriger<T>(table: TableEditable, id: number, data: Valeurs): Promise<T> {
  return request<T>(`${url(table)}${id}/`, { method: 'PATCH', body: data })
}

/** Closes a row on dateEffet and opens its successor with the values sent (D3, D4). */
export function remplacer<T>(
  table: TableEditable,
  id: number,
  dateEffet: string,
  data: Valeurs,
): Promise<T> {
  return request<T>(`${url(table)}${id}/successeur/`, {
    method: 'POST',
    body: { ...data, date_effet: dateEffet },
  })
}

/** What replacing a row on dateEffet would carry over, by kind, and what blocks it
 * (tree reference screens D9). */
export interface Suite {
  total: number
  par_genre: { libelle: string; nombre: number }[]
  bloquants: string[]
}

export function suite(table: TableEditable, id: number, dateEffet: string): Promise<Suite> {
  return request<Suite>(`${url(table)}${id}/suite/?date_effet=${dateEffet}`)
}
