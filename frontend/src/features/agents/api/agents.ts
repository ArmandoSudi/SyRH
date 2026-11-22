import { request } from '@/shared/utils/http'

export type StatutAgent = 'actif' | 'a_venir' | 'inactif' | 'sans_contrat'

/** The assignment in force at the list's date (position history D20). */
export interface AffectationActuelle {
  id: number
  unite: number
  unite_code: string
  unite_nom: string
  fonction: number
  fonction_code: string
  fonction_nom: string
  date_effet: string
}

/** The classification in force at the list's date. */
export interface ClassementActuel {
  id: number
  echelon: number
  echelon_numero: number
  grade: number
  grade_code: string
  grade_nom: string
  date_effet: string
}

/** An agent as the list and the pickers show them (agent identity D19, agent list D9). */
export interface AgentResume {
  id: number
  matricule: string
  nom: string
  postnom: string
  prenom: string
  statut?: StatutAgent
  statut_libelle?: string
  affectation_actuelle?: AffectationActuelle | null
  classement_actuel?: ClassementActuel | null
}

export interface Page<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** The search parameters of /api/agents/ (agent list D4). */
export interface RechercheAgents {
  q?: string
  unite?: number | null
  grade?: number | null
  fonction?: number | null
  statut?: StatutAgent[]
  /** YYYY-MM-DD; today when absent. */
  date?: string | null
  tri?: 'nom' | 'matricule'
  page?: number
  taille?: number
}

export function rechercheQuery(params: RechercheAgents): string {
  const search = new URLSearchParams()
  if (params.q?.trim()) search.set('q', params.q.trim())
  for (const key of ['unite', 'grade', 'fonction'] as const) {
    const value = params[key]
    if (value) search.set(key, String(value))
  }
  if (params.statut?.length) search.set('statut', params.statut.join(','))
  if (params.date) search.set('date', params.date)
  if (params.tri && params.tri !== 'nom') search.set('tri', params.tri)
  if (params.page && params.page > 1) search.set('page', String(params.page))
  if (params.taille) search.set('taille', String(params.taille))
  const text = search.toString()
  return text ? `?${text}` : ''
}

/** One page of agents matching the search, sorted (agent list D4 to D9). */
export function searchAgents(params: RechercheAgents = {}): Promise<Page<AgentResume>> {
  return request<Page<AgentResume>>(`/api/agents/${rechercheQuery(params)}`)
}

/** One agent by id. */
export function fetchAgent(id: number): Promise<AgentResume> {
  return request<AgentResume>(`/api/agents/${id}/`)
}
