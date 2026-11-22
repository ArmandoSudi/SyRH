import type { Engagement } from '@/features/agents/api/engagement'
import type { TypeContrat } from '@/features/referentiels/api/referentiels'
import { localDate } from '@/shared/utils/dates'
import type { FieldErrors } from '@/shared/utils/http'

/** The form's values, dates as Date (agent creation form D11). */
export interface FormulaireEngagement {
  matricule: string
  nom: string
  postnom: string
  prenom: string
  sexe: 'M' | 'F' | ''
  date_naissance: Date | null
  lieu_naissance: string
  nationalite: string
  coordonnees: {
    adresse: string
    commune: string
    ville: string
    telephone: string
    telephone_secondaire: string
    courriel: string
    urgence_nom: string
    urgence_lien: string
    urgence_telephone: string
  }
  contrat: {
    type_contrat: number | null
    date_debut: Date | null
    date_fin: Date | null
    fin_periode_essai: Date | null
  }
  affectation: { unite: number | null; fonction: number | null }
  classement: { grade: number | null; echelon: number | null }
}

export function formulaireVide(): FormulaireEngagement {
  return {
    matricule: '',
    nom: '',
    postnom: '',
    prenom: '',
    sexe: '',
    date_naissance: null,
    lieu_naissance: '',
    nationalite: 'Congolaise',
    coordonnees: {
      adresse: '',
      commune: '',
      ville: '',
      telephone: '',
      telephone_secondaire: '',
      courriel: '',
      urgence_nom: '',
      urgence_lien: '',
      urgence_telephone: '',
    },
    contrat: { type_contrat: null, date_debut: null, date_fin: null, fin_periode_essai: null },
    affectation: { unite: null, fonction: null },
    classement: { grade: null, echelon: null },
  }
}

export const ETAPES = ['Identité', 'Coordonnées', 'Contrat', 'Poste', 'Récapitulatif'] as const
const OBLIGATOIRE = 'Ce champ est obligatoire.'

const day = (value: Date | null) => (value ? localDate(value) : null)

/** The request body; contact details only when something was typed (D1). */
export function versEngagement(f: FormulaireEngagement): Engagement {
  const coordonnees = Object.values(f.coordonnees).some((v) => v.trim())
    ? { ...f.coordonnees }
    : null
  return {
    matricule: f.matricule,
    nom: f.nom,
    postnom: f.postnom,
    prenom: f.prenom,
    sexe: f.sexe,
    date_naissance: day(f.date_naissance),
    lieu_naissance: f.lieu_naissance,
    nationalite: f.nationalite,
    coordonnees,
    contrat: {
      type_contrat: f.contrat.type_contrat,
      date_debut: day(f.contrat.date_debut),
      date_fin: day(f.contrat.date_fin),
      fin_periode_essai: day(f.contrat.fin_periode_essai),
    },
    affectation: { ...f.affectation },
    classement: { echelon: f.classement.echelon },
  }
}

/** The required fields missing on a step, as errors keyed like the server's (D12). */
export function verifierEtape(
  etape: number,
  f: FormulaireEngagement,
  type: TypeContrat | undefined,
): FieldErrors {
  const missing: string[] = []
  if (etape === 0) {
    // The matricule is proposed at the Contrat step (D14): it is checked before saving.
    if (!f.nom.trim()) missing.push('nom')
    if (!f.sexe) missing.push('sexe')
    if (!f.date_naissance) missing.push('date_naissance')
    if (!f.lieu_naissance.trim()) missing.push('lieu_naissance')
  } else if (etape === 4) {
    if (!f.matricule.trim()) missing.push('matricule')
  } else if (etape === 2) {
    if (!f.contrat.type_contrat) missing.push('contrat.type_contrat')
    if (!f.contrat.date_debut) missing.push('contrat.date_debut')
    if (type?.duree_determinee && !f.contrat.date_fin) missing.push('contrat.date_fin')
  } else if (etape === 3) {
    if (!f.affectation.unite) missing.push('affectation.unite')
    if (!f.affectation.fonction) missing.push('affectation.fonction')
    if (!f.classement.echelon) missing.push('classement.echelon')
  }
  return Object.fromEntries(missing.map((key) => [key, [OBLIGATOIRE]]))
}

/** The step that holds a server error's field (D12). */
export function etapeDuChamp(key: string): number {
  if (key.startsWith('coordonnees.')) return 1
  if (key.startsWith('contrat.')) return 2
  if (key.startsWith('affectation.') || key.startsWith('classement.')) return 3
  return 0
}

/** The first step holding one of the errors, or null. */
export function premiereEtapeEnErreur(errors: FieldErrors): number | null {
  const steps = Object.keys(errors).map(etapeDuChamp)
  return steps.length ? Math.min(...steps) : null
}

/** Whether a dated reference row is open on a day. */
export function ouvertLe(
  row: { date_ouverture?: string; date_fermeture: string | null },
  jour: string,
): boolean {
  return (
    (!row.date_ouverture || row.date_ouverture <= jour) &&
    (!row.date_fermeture || jour < row.date_fermeture)
  )
}

/** The form's values keyed like the errors ('nom', 'contrat.date_fin'), to compare. */
export function valeursAPlat(f: FormulaireEngagement): Record<string, string> {
  const flat: Record<string, string> = {}
  const walk = (node: object, prefix: string) => {
    for (const [key, value] of Object.entries(node)) {
      if (value instanceof Date) flat[prefix + key] = value.toISOString()
      else if (value && typeof value === 'object') walk(value, `${prefix}${key}.`)
      else flat[prefix + key] = String(value ?? '')
    }
  }
  walk(f, '')
  // The échelon's error is the grade's too.
  flat['classement.echelon'] += `|${flat['classement.grade']}`
  return flat
}
