import type { AgentResume } from '@/features/agents/api/agents'
import { request } from '@/shared/utils/http'

/** What the hiring form sends (agent creation form D1); dates as YYYY-MM-DD. */
export interface Engagement {
  matricule: string
  nom: string
  postnom: string
  prenom: string
  sexe: 'M' | 'F' | ''
  date_naissance: string | null
  lieu_naissance: string
  nationalite: string
  coordonnees: Record<string, string> | null
  contrat: {
    type_contrat: number | null
    date_debut: string | null
    date_fin: string | null
    fin_periode_essai: string | null
  }
  affectation: { unite: number | null; fonction: number | null }
  classement: { echelon: number | null }
}

/** Hires an agent, all or nothing; answers the new agent (D2, D5). */
export function engager(engagement: Engagement): Promise<AgentResume> {
  return request<AgentResume>('/api/agents/', { method: 'POST', body: engagement })
}

/** The next matricule in the bulletin style for a hiring year (D6). */
export async function matriculeSuivant(annee: number): Promise<string> {
  const body = await request<{ matricule: string }>(`/api/agents/matricule-suivant/?annee=${annee}`)
  return body.matricule
}

/** Agents with the same nom and birth date, and prénom when given (D7). */
export function doublons(params: {
  nom: string
  prenom?: string
  date_naissance: string
}): Promise<AgentResume[]> {
  const search = new URLSearchParams({ nom: params.nom, date_naissance: params.date_naissance })
  if (params.prenom) search.set('prenom', params.prenom)
  return request<AgentResume[]>(`/api/agents/doublons/?${search.toString()}`)
}
