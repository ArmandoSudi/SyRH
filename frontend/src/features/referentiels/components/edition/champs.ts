import type { TableEditable } from '@/features/referentiels/api/edition'
import { PARAMETRES } from '@/features/referentiels/components/parametres'

/** What kind of input a field needs in the edit dialog (reference data screens D12). */
export type Genre = 'texte' | 'oui-non' | 'choix' | 'nombre' | 'date' | 'piece'

export interface Champ {
  nom: string
  libelle: string
  genre: Genre
  requis?: boolean
  aide?: string
  choix?: { value: string; label: string }[]
  /** Never changes after creation: shown read-only when correcting (D8). */
  fixe?: boolean
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
}

const CODE: Champ = { nom: 'code', libelle: 'Code', genre: 'texte', requis: true }
const NOM: Champ = { nom: 'nom', libelle: 'Nom', genre: 'texte', requis: true }
const PIECE: Champ = {
  nom: 'type_document',
  libelle: 'Pièce exigée',
  genre: 'piece',
  requis: true,
  aide: 'Choisie parmi les types de pièce ouverts.',
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
        choix: PARAMETRES.map(({ cle, libelle }) => ({ value: cle, label: libelle })),
      },
      { nom: 'valeur', libelle: 'Valeur', genre: 'nombre', requis: true },
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

/** Closing a row and opening its successor needs both (D6). */
export function peutRemplacer(can: Can, edition: Edition): boolean {
  return peutAjouter(can, edition) && peutModifier(can, edition)
}
