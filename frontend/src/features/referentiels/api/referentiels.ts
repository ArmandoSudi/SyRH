import { request } from '@/shared/utils/http'

export type TypeUnite = 'direction' | 'departement' | 'service' | 'bureau'

export interface SiteResume {
  id: number
  code: string
  nom: string
}

export interface Site extends SiteResume {
  ville: string
  siege: boolean
  /** First day the site is closed, YYYY-MM-DD. */
  date_fermeture: string | null
}

export interface Unite {
  id: number
  code: string
  nom: string
  type: TypeUnite
  type_libelle: string
  parent: number | null
  site: SiteResume
  date_ouverture: string
  /** First day the unit no longer exists, YYYY-MM-DD. */
  date_fermeture: string | null
}

function query(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value)
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

/** Units open on a date (the API defaults to today), or every unit with toutes. */
export function fetchUnites(options: { date?: string; toutes?: boolean } = {}): Promise<Unite[]> {
  return request<Unite[]>(
    `/api/referentiels/unites/${query({ date: options.date, toutes: options.toutes ? '1' : undefined })}`,
  )
}

/** Open sites, or every site with toutes. */
export function fetchSites(options: { toutes?: boolean } = {}): Promise<Site[]> {
  return request<Site[]>(
    `/api/referentiels/sites/${query({ toutes: options.toutes ? '1' : undefined })}`,
  )
}
