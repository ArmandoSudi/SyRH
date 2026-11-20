import { request } from '@/shared/utils/http'

/** The six flat lists editable in SyRH (reference data screens D1). */
export type TableEditable =
  'fonctions' | 'types-contrat' | 'banques' | 'motifs-sortie' | 'types-suspension' | 'parametres'

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
