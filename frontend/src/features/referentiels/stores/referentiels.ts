import { ref } from 'vue'
import { defineStore } from 'pinia'

export type Onglet = 'organisation' | 'sites' | 'classification'

/**
 * What the reader chose on the Référentiels screen, kept in Pinia so it
 * survives leaving the screen and coming back (organisation D27,
 * classification D30).
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

  return { onglet, date, texte, expanded, sitesFermes, classification }
})
