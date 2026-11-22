import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { LocationQuery, LocationQueryRaw } from 'vue-router'

import type { RechercheAgents, StatutAgent } from '@/features/agents/api/agents'
import { STATUT_DEFAUT, STATUTS } from '@/features/agents/components/statuts'

/** The list's filters, as the URL carries them (agent list D14). */
export interface FiltresAgents {
  q: string
  unite: number | null
  grade: number | null
  fonction: number | null
  statut: StatutAgent[]
  /** YYYY-MM-DD, or null for today. */
  date: string | null
  tri: 'nom' | 'matricule'
  page: number
}

export function filtresParDefaut(): FiltresAgents {
  return {
    q: '',
    unite: null,
    grade: null,
    fonction: null,
    statut: [...STATUT_DEFAUT],
    date: null,
    tri: 'nom',
    page: 1,
  }
}

function one(value: LocationQuery[string] | undefined): string | null {
  const first = Array.isArray(value) ? value[0] : value
  return first ?? null
}

function id(value: LocationQuery[string] | undefined): number | null {
  const n = Number(one(value))
  return Number.isInteger(n) && n > 0 ? n : null
}

/** Filters from a URL query; missing keys take their default. `statut=tous` means none. */
export function filtresDepuisQuery(query: LocationQuery): FiltresAgents {
  const filtres = filtresParDefaut()
  filtres.q = one(query.q) ?? ''
  filtres.unite = id(query.unite)
  filtres.grade = id(query.grade)
  filtres.fonction = id(query.fonction)
  const statut = one(query.statut)
  if (statut === 'tous') filtres.statut = []
  else if (statut) {
    const known = new Set(STATUTS.map((s) => s.value))
    filtres.statut = statut.split(',').filter((s): s is StatutAgent => known.has(s as StatutAgent))
  }
  const date = one(query.date)
  filtres.date = date && /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : null
  filtres.tri = one(query.tri) === 'matricule' ? 'matricule' : 'nom'
  filtres.page = id(query.page) ?? 1
  return filtres
}

/** The URL query of filters: only what differs from the defaults. */
export function queryDepuisFiltres(filtres: FiltresAgents): LocationQueryRaw {
  const query: LocationQueryRaw = {}
  if (filtres.q.trim()) query.q = filtres.q.trim()
  if (filtres.unite) query.unite = String(filtres.unite)
  if (filtres.grade) query.grade = String(filtres.grade)
  if (filtres.fonction) query.fonction = String(filtres.fonction)
  const defaut = STATUT_DEFAUT.join(',')
  const statut = filtres.statut.join(',')
  if (statut !== defaut) query.statut = statut || 'tous'
  if (filtres.date) query.date = filtres.date
  if (filtres.tri !== 'nom') query.tri = filtres.tri
  if (filtres.page > 1) query.page = String(filtres.page)
  return query
}

/** What the API is asked for these filters. */
export function rechercheDepuisFiltres(filtres: FiltresAgents): RechercheAgents {
  return { ...filtres, taille: 25 }
}

/**
 * The agent list's filters, kept in Pinia so they survive leaving the screen and
 * coming back (agent list D14); the view mirrors them into the URL.
 */
export const useAgentListStore = defineStore('agentList', () => {
  const filtres = ref<FiltresAgents>(filtresParDefaut())
  /** Whether the store holds a search the user made (else the URL decides). */
  const touche = ref(false)

  function remplacer(nouveaux: FiltresAgents) {
    filtres.value = nouveaux
    touche.value = true
  }

  function effacer() {
    remplacer(filtresParDefaut())
  }

  return { filtres, touche, remplacer, effacer }
})
