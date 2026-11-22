import type { AgentResume } from '@/features/agents/api/agents'
import type { TypeDocument } from '@/features/referentiels/api/referentiels'

/**
 * Checks and labels of the documents panel (document storage D11, D12, D22). The
 * messages are the server's, word for word: the browser checks first so the user
 * waits for nothing, and the server stays the authority.
 */
export const FORMAT_REFUSE = 'Format refusé : seuls les fichiers PDF, JPEG et PNG sont acceptés.'
export const FICHIER_VIDE = 'Le fichier est vide.'
export const ACCEPT = '.pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png'
const EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png']
const MO = 1024 * 1024

export function tropGros(mo: number): string {
  return `Le fichier dépasse la taille maximale de ${mo} Mo.`
}

/** The message for a file the server would refuse, or null; maxMo null when unknown. */
export function checkFile(file: File, maxMo: number | null): string | null {
  const extension = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (!EXTENSIONS.includes(extension)) return FORMAT_REFUSE
  if (file.size === 0) return FICHIER_VIDE
  if (maxMo !== null && file.size > maxMo * MO) return tropGros(maxMo)
  return null
}

/** "850 o", "12,4 Ko", "3,2 Mo". */
export function formatTaille(octets: number): string {
  const nombre = (value: number) =>
    value.toLocaleString('fr-FR', { maximumFractionDigits: 1, minimumFractionDigits: 0 })
  if (octets < 1024) return `${octets} o`
  if (octets < MO) return `${nombre(octets / 1024)} Ko`
  return `${nombre(octets / MO)} Mo`
}

/** "PDF", "JPEG", "PNG". */
export function formatLibelle(mime: string): string {
  return mime.split('/').pop()?.toUpperCase() ?? mime
}

/** An ISO datetime as dd/mm/yyyy in local time. */
export function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR')
}

/**
 * The document types a user may upload: open today, and for a confidential one,
 * shared with one of the user's profiles (D14, D22).
 */
export function typesDeposables(types: TypeDocument[], groupes: string[]): TypeDocument[] {
  const mine = new Set(groupes)
  return types.filter(
    (type) => !type.confidentiel || type.groupes_autorises_noms.some((nom) => mine.has(nom)),
  )
}

/** "ARPTC/0001/2020 — Mukendi Kabongo Jean". */
export function agentLibelle(agent: AgentResume): string {
  const noms = [agent.nom, agent.postnom, agent.prenom].filter(Boolean).join(' ')
  return `${agent.matricule} — ${noms}`
}

/** Agents whose matricule or names contain the text, case and accents ignored. */
export function filterAgents(agents: AgentResume[], texte: string): AgentResume[] {
  const plain = (value: string) =>
    value
      .normalize('NFD')
      .replace(/\p{Diacritic}/gu, '')
      .toLowerCase()
  const wanted = plain(texte.trim())
  if (!wanted) return agents
  return agents.filter((agent) => plain(agentLibelle(agent)).includes(wanted))
}
