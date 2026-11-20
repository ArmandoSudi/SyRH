import { ref } from 'vue'
import { defineStore } from 'pinia'

export type Onglet =
  | 'organisation'
  | 'sites'
  | 'classification'
  | 'fonctions'
  | 'typesContrat'
  | 'pieces'
  | 'sorties'
  | 'banques'
  | 'parametres'

/**
 * What the reader chose on the Référentiels screen, kept in Pinia so it
 * survives leaving the screen and coming back (organisation D27,
 * classification D30, fonctions D20, contract types D21, document
 * types D22, exit reasons D22, banks D20, general parameters D20).
 */
export const useReferentielsStore = defineStore('referentiels', () => {
  const onglet = ref<Onglet>('organisation')
  /** The organisation is shown as it is on this day. */
  const date = ref<Date>(new Date())
  const texte = ref('')
  const expanded = ref<Record<string, boolean>>({})
  const sitesFermes = ref(false)

  // The grid has its own date and filter: moving one tree does not move the other.
  const classification = ref({
    date: new Date(),
    texte: '',
    expanded: {} as Record<string, boolean>,
  })

  // The fonctions have their own date and filter too.
  const fonctions = ref({ date: new Date(), texte: '' })

  const typesContrat = ref({ date: new Date(), texte: '' })

  const pieces = ref({ date: new Date(), texte: '', expanded: {} as Record<string, boolean> })

  // One date and one filter for both lists of the tab: exit reasons and suspension types.
  const sorties = ref({ date: new Date(), texte: '' })

  const banques = ref({ date: new Date(), texte: '' })

  // Four rows: a date, no text filter.
  const parametres = ref({ date: new Date() })

  return {
    onglet,
    date,
    texte,
    expanded,
    sitesFermes,
    classification,
    fonctions,
    typesContrat,
    pieces,
    sorties,
    banques,
    parametres,
  }
})
