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

/** A row of the grid, open from date_ouverture to date_fermeture excluded. */
interface Periode {
  id: number
  date_ouverture: string
  /** First day the row no longer exists, YYYY-MM-DD. */
  date_fermeture: string | null
}

export interface Categorie extends Periode {
  code: string
  nom: string
  /** A higher rank is a higher catégorie. */
  rang: number
}

export interface Grade extends Periode {
  categorie: number
  code: string
  nom: string
  /** Rank within the catégorie; a higher rank is a higher grade. */
  rang: number
}

export interface Echelon extends Periode {
  grade: number
  numero: number
  /** "A1 — Échelon 3" */
  libelle: string
}

export type Nature = 'responsabilite' | 'execution'

/** A job function, open from date_ouverture to date_fermeture excluded (fonctions D16). */
export interface Fonction extends Periode {
  code: string
  nom: string
  /** Responsabilité: the holder heads a unit or a team. */
  nature: Nature
  /** "Responsabilité" or "Exécution" */
  nature_libelle: string
}

/** A contract type and the rules phase 2.3 reads from it (contract types D17). */
export interface TypeContrat extends Periode {
  code: string
  nom: string
  /** A contract of this type must have an end date. */
  duree_determinee: boolean
  /** A contract of this type may have a probation period. */
  periode_essai: boolean
}

/** A kind of supporting document (document types D19). */
export interface TypeDocument extends Periode {
  code: string
  nom: string
}

/** Event kinds that rest on a document, in the order of the agent's life (document types D2). */
export type Evenement =
  | 'engagement'
  | 'promotion'
  | 'mutation'
  | 'detachement'
  | 'disponibilite'
  | 'reprise'
  | 'interim'
  | 'sanction'
  | 'distinction'
  | 'sortie'
  | 'mariage'
  | 'naissance'
  | 'fin_dependance'
  | 'formation'

/** A document type an event kind requires; type_document is the type's id. */
export interface PieceRequise extends Periode {
  evenement: Evenement
  evenement_libelle: string
  type_document: number
  obligatoire: boolean
}

/** A reason an agent leaves for good (exit reasons D19); type_document is the type's id. */
export interface MotifSortie extends Periode {
  code: string
  nom: string
  type_document: number
  type_document_libelle: string
  /** Counted in the retirement forecast and alerts. */
  retraite: boolean
  /** The exit goes to the heirs. */
  deces: boolean
}

/** A position that suspends a career without ending it (exit reasons D19). */
export interface TypeSuspension extends Periode {
  code: string
  nom: string
  type_document: number
  type_document_libelle: string
  compte_anciennete: boolean
  /** Longest single period; null when the decision sets it. */
  duree_max_mois: number | null
  /** Renewals allowed; null for no limit. */
  renouvellements_max: number | null
}

export interface PeriodeOptions {
  date?: string
  toutes?: boolean
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

function periode(options: PeriodeOptions): string {
  return query({ date: options.date, toutes: options.toutes ? '1' : undefined })
}

/** Catégories open on a date (the API defaults to today), highest first, or all with toutes. */
export function fetchCategories(options: PeriodeOptions = {}): Promise<Categorie[]> {
  return request<Categorie[]>(`/api/referentiels/categories/${periode(options)}`)
}

/** Grades open on a date, in grid order, or all with toutes. */
export function fetchGrades(options: PeriodeOptions = {}): Promise<Grade[]> {
  return request<Grade[]>(`/api/referentiels/grades/${periode(options)}`)
}

/** Échelons open on a date, in grid order, or all with toutes. */
export function fetchEchelons(options: PeriodeOptions = {}): Promise<Echelon[]> {
  return request<Echelon[]>(`/api/referentiels/echelons/${periode(options)}`)
}

/** Fonctions open on a date, responsabilité first then by name, or all with toutes. */
export function fetchFonctions(options: PeriodeOptions = {}): Promise<Fonction[]> {
  return request<Fonction[]>(`/api/referentiels/fonctions/${periode(options)}`)
}

/** Contract types open on a date, by name, or all with toutes. */
export function fetchTypesContrat(options: PeriodeOptions = {}): Promise<TypeContrat[]> {
  return request<TypeContrat[]>(`/api/referentiels/types-contrat/${periode(options)}`)
}

/** Document types open on a date, by name, or all with toutes. */
export function fetchTypesDocument(options: PeriodeOptions = {}): Promise<TypeDocument[]> {
  return request<TypeDocument[]>(`/api/referentiels/types-document/${periode(options)}`)
}

/** Required documents open on a date, in event order, mandatory first, or all with toutes. */
export function fetchPiecesRequises(options: PeriodeOptions = {}): Promise<PieceRequise[]> {
  return request<PieceRequise[]>(`/api/referentiels/pieces-requises/${periode(options)}`)
}

/** Exit reasons open on a date (the API defaults to today), by name, or all with toutes. */
export function fetchMotifsSortie(options: PeriodeOptions = {}): Promise<MotifSortie[]> {
  return request<MotifSortie[]>(`/api/referentiels/motifs-sortie/${periode(options)}`)
}

/** Suspension types open on a date, by name, or all with toutes. */
export function fetchTypesSuspension(options: PeriodeOptions = {}): Promise<TypeSuspension[]> {
  return request<TypeSuspension[]>(`/api/referentiels/types-suspension/${periode(options)}`)
}
