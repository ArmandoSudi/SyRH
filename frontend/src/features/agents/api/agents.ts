import { request } from '@/shared/utils/http'

/** An agent as the agent picker shows them (agent identity D19). */
export interface AgentResume {
  id: number
  matricule: string
  nom: string
  postnom: string
  prenom: string
}

/** Every agent, by name; the list screen of 2.8 adds search and pagination. */
export function fetchAgents(): Promise<AgentResume[]> {
  return request<AgentResume[]>('/api/agents/')
}
