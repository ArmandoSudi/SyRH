import type { TableEditable, Valeurs } from '@/features/referentiels/api/edition'
import { EVENEMENTS } from '@/features/referentiels/components/pieces'
import { PARAMETRES } from '@/features/referentiels/components/parametres'

/** What kind of input a field needs in the edit dialog (reference data screens D12). */
export type Genre = 'texte' | 'oui-non' | 'choix' | 'nombre' | 'date' | 'parent'

/** Tables a parent field picks from, among their rows open today (tree reference D11). */
export type Source = 'sites' | 'unites' | 'categories' | 'grades' | 'types-document'

export interface Champ {
  nom: string
  libelle: string
  genre: Genre
  requis?: boolean
  aide?: string
  choix?: { value: string; label: string }[]
  /** For a parent field: the table to pick from. */
  source?: Source
  /** For a parent field: which rows fit the form's other values (a unit's level). */
  filtre?: (row: Valeurs, valeurs: Valeurs) => boolean
  /** Reads the field's value from a row, when the API returns it another way (a nested site). */
  lire?: (row: Valeurs) => unknown
  /** Never changes after creation: read-only when correcting (D8, tree reference D2). */
  fixe?: boolean
  /** Also kept when replacing: the successor is the same parameter or the same event. */
  garde?: boolean
}

export interface Edition {
  table: TableEditable
  /** Django model name, for the add_… / change_… permissions (D10). */
  modele: string
  /** "une fonction", for the dialog titles. */
  un: string
  /** "Fonction enregistrée.", once saved (D13). */
  confirmation: string
  champs: Champ[]
  /** The date fields; DATES unless the table has no opening date (sites). */
  dates?: Champ[]
  /** False when rows cannot be replaced at a date (sites, tree reference D1). */
  remplacable?: boolean
  /** True when replacing a row carries its children over: show the preview (D9, D16). */
  suite?: boolean
}

const CODE: Champ = { nom: 'code', libelle: 'Code', genre: 'texte', requis: true }
const NOM: Champ = { nom: 'nom', libelle: 'Nom', genre: 'texte', requis: true }
const PIECE: Champ = {
  nom: 'type_document',
  libelle: 'Pièce exigée',
  genre: 'parent',
  source: 'types-document',
  requis: true,
  aide: 'Choisie parmi les types de pièce ouverts.',
}
const RANG: Champ = {
  nom: 'rang',
  libelle: 'Rang',
  genre: 'nombre',
  requis: true,
  aide: 'Un rang plus élevé désigne un niveau plus élevé.',
}

/** The opening and closing dates every row has, after its own fields. */
export const DATES: Champ[] = [
  { nom: 'date_ouverture', libelle: "Date d'ouverture", genre: 'date', requis: true },
  {
    nom: 'date_fermeture',
    libelle: 'Date de fermeture',
    genre: 'date',
    aide: 'Premier jour où la ligne ne s’applique plus. Vide : toujours ouverte.',
  },
]

/** Levels of the organisation: a parent's level is strictly lower (organisation D2). */
export const NIVEAUX: Record<string, number> = {
  direction: 1,
  departement: 2,
  service: 3,
  bureau: 4,
}
export const TYPES_UNITE = [
  { value: 'direction', label: 'Direction' },
  { value: 'departement', label: 'Département' },
  { value: 'service', label: 'Service' },
  { value: 'bureau', label: 'Bureau' },
]

export const EDITIONS: Record<TableEditable, Edition> = {
  fonctions: {
    table: 'fonctions',
    modele: 'fonction',
    un: 'une fonction',
    confirmation: 'Fonction enregistrée.',
    champs: [
      CODE,
      NOM,
      {
        nom: 'nature',
        libelle: 'Nature',
        genre: 'choix',
        requis: true,
        choix: [
          { value: 'responsabilite', label: 'Responsabilité' },
          { value: 'execution', label: 'Exécution' },
        ],
      },
    ],
  },
  'types-contrat': {
    table: 'types-contrat',
    modele: 'typecontrat',
    un: 'un type de contrat',
    confirmation: 'Type de contrat enregistré.',
    champs: [
      CODE,
      NOM,
      {
        nom: 'duree_determinee',
        libelle: 'Durée déterminée',
        genre: 'oui-non',
        aide: 'Un contrat de ce type doit avoir une date de fin.',
      },
      {
        nom: 'periode_essai',
        libelle: "Période d'essai",
        genre: 'oui-non',
        aide: 'Un contrat de ce type peut comporter une période d’essai.',
      },
    ],
  },
  banques: {
    table: 'banques',
    modele: 'banque',
    un: 'une banque',
    confirmation: 'Banque enregistrée.',
    champs: [
      CODE,
      NOM,
      {
        nom: 'swift',
        libelle: 'Code SWIFT/BIC',
        genre: 'texte',
        aide: '8 ou 11 caractères, par exemple ABCDCDKI. Facultatif.',
      },
    ],
  },
  'motifs-sortie': {
    table: 'motifs-sortie',
    modele: 'motifsortie',
    un: 'un motif de sortie',
    confirmation: 'Motif de sortie enregistré.',
    champs: [
      CODE,
      NOM,
      PIECE,
      {
        nom: 'retraite',
        libelle: 'Retraite',
        genre: 'oui-non',
        aide: 'Compté dans les prévisions et alertes de départ à la retraite.',
      },
      {
        nom: 'deces',
        libelle: 'Décès',
        genre: 'oui-non',
        aide: 'La sortie profite aux ayants droit.',
      },
    ],
  },
  'types-suspension': {
    table: 'types-suspension',
    modele: 'typesuspension',
    un: 'une position de suspension',
    confirmation: 'Position de suspension enregistrée.',
    champs: [
      CODE,
      NOM,
      PIECE,
      {
        nom: 'compte_anciennete',
        libelle: "Compte dans l'ancienneté",
        genre: 'oui-non',
        aide: 'La période compte dans l’ancienneté et les 30 ans de carrière.',
      },
      {
        nom: 'duree_max_mois',
        libelle: 'Durée maximale (mois)',
        genre: 'nombre',
        aide: 'Vide : fixée par la décision.',
      },
      {
        nom: 'renouvellements_max',
        libelle: 'Renouvellements maximum',
        genre: 'nombre',
        aide: 'Vide : sans limite.',
      },
    ],
  },
  parametres: {
    table: 'parametres',
    modele: 'parametre',
    un: 'une valeur de paramètre',
    confirmation: 'Paramètre enregistré.',
    champs: [
      {
        nom: 'cle',
        libelle: 'Paramètre',
        genre: 'choix',
        requis: true,
        fixe: true,
        garde: true,
        choix: PARAMETRES.map(({ cle, libelle }) => ({ value: cle, label: libelle })),
      },
      { nom: 'valeur', libelle: 'Valeur', genre: 'nombre', requis: true },
    ],
  },
  sites: {
    table: 'sites',
    modele: 'site',
    un: 'un site',
    confirmation: 'Site enregistré.',
    remplacable: false,
    champs: [
      CODE,
      NOM,
      { nom: 'ville', libelle: 'Ville', genre: 'texte', requis: true },
      {
        nom: 'siege',
        libelle: 'Siège',
        genre: 'oui-non',
        aide: 'Un seul site ouvert peut être le siège.',
      },
    ],
    dates: DATES.filter((d) => d.nom === 'date_fermeture'),
  },
  unites: {
    table: 'unites',
    modele: 'uniteorganisationnelle',
    un: 'une unité',
    confirmation: 'Unité enregistrée.',
    suite: true,
    champs: [
      {
        nom: 'type',
        libelle: 'Type',
        genre: 'choix',
        requis: true,
        fixe: true,
        choix: TYPES_UNITE,
      },
      CODE,
      NOM,
      {
        nom: 'parent',
        libelle: 'Unité parente',
        genre: 'parent',
        source: 'unites',
        fixe: true,
        aide: 'Une unité d’un niveau supérieur. Vide pour une direction.',
        filtre: (row, valeurs) =>
          (NIVEAUX[String(row.type)] ?? 0) < (NIVEAUX[String(valeurs.type)] ?? 0),
      },
      {
        nom: 'site_id',
        libelle: 'Site',
        genre: 'parent',
        source: 'sites',
        requis: true,
        fixe: true,
        lire: (row) => (row.site as { id?: number } | null)?.id ?? null,
      },
    ],
  },
  categories: {
    table: 'categories',
    modele: 'categorie',
    un: 'une catégorie',
    confirmation: 'Catégorie enregistrée.',
    suite: true,
    champs: [CODE, NOM, RANG],
  },
  grades: {
    table: 'grades',
    modele: 'grade',
    un: 'un grade',
    confirmation: 'Grade enregistré.',
    suite: true,
    champs: [
      {
        nom: 'categorie',
        libelle: 'Catégorie',
        genre: 'parent',
        source: 'categories',
        requis: true,
        fixe: true,
      },
      CODE,
      NOM,
      RANG,
    ],
  },
  echelons: {
    table: 'echelons',
    modele: 'echelon',
    un: 'un échelon',
    confirmation: 'Échelon enregistré.',
    champs: [
      {
        nom: 'grade',
        libelle: 'Grade',
        genre: 'parent',
        source: 'grades',
        requis: true,
        fixe: true,
      },
      { nom: 'numero', libelle: 'Numéro', genre: 'nombre', requis: true },
    ],
  },
  'types-document': {
    table: 'types-document',
    modele: 'typedocument',
    un: 'un type de pièce',
    confirmation: 'Type de pièce enregistré.',
    suite: true,
    champs: [CODE, NOM],
  },
  'pieces-requises': {
    table: 'pieces-requises',
    modele: 'piecerequise',
    un: 'une pièce exigée',
    confirmation: 'Pièce exigée enregistrée.',
    champs: [
      {
        nom: 'evenement',
        libelle: 'Événement',
        genre: 'choix',
        requis: true,
        fixe: true,
        garde: true,
        choix: EVENEMENTS.map(({ value, label }) => ({ value, label })),
      },
      { ...PIECE, fixe: true },
      {
        nom: 'obligatoire',
        libelle: 'Obligatoire',
        genre: 'oui-non',
        aide: 'Une pièce obligatoire manquante bloque la validation de l’événement.',
      },
    ],
  },
}

type Can = (permission: string) => boolean

export function peutAjouter(can: Can, edition: Edition): boolean {
  return can(`referentiels.add_${edition.modele}`)
}

export function peutModifier(can: Can, edition: Edition): boolean {
  return can(`referentiels.change_${edition.modele}`)
}

/** Closing a row and opening its successor needs both (D6); sites have no successor. */
export function peutRemplacer(can: Can, edition: Edition): boolean {
  return edition.remplacable !== false && peutAjouter(can, edition) && peutModifier(can, edition)
}
