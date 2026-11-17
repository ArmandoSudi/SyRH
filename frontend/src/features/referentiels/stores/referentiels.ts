import { ref } from 'vue'
import { defineStore } from 'pinia'

export type Onglet = 'organisation' | 'sites'

/**
 * What the reader chose on the Référentiels screen, kept in Pinia so it
 * survives leaving the screen and coming back (D27).
 */
export const useReferentielsStore = defineStore('referentiels', () => {
  const onglet = ref<Onglet>('organisation')
  /** The organisation is shown as it is on this day. */
  const date = ref<Date>(new Date())
  const texte = ref('')
  const expanded = ref<Record<string, boolean>>({})
  const sitesFermes = ref(false)

  return { onglet, date, texte, expanded, sitesFermes }
})
