import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import type { AuditAction, AuditQuery } from '@/features/audit/api/audit'
import { localDate } from '@/shared/utils/dates'

/**
 * Filters and page of the audit log. Kept in Pinia so they survive leaving
 * the screen and coming back (D32).
 */
export const useAuditStore = defineStore('audit', () => {
  /** [start, end] from the range picker; the end is null while picking. */
  const periode = ref<(Date | null)[] | null>(null)
  const auteur = ref('')
  const module = ref<string | null>(null)
  const action = ref<AuditAction | null>(null)
  const page = ref(1)

  const query = computed<AuditQuery>(() => {
    const [debut, fin] = periode.value ?? []
    return {
      date_debut: debut ? localDate(debut) : undefined,
      date_fin: fin ? localDate(fin) : undefined,
      auteur: auteur.value.trim() || undefined,
      module: module.value ?? undefined,
      action: action.value ?? undefined,
      page: page.value > 1 ? page.value : undefined,
    }
  })

  const hasFilters = computed(
    () => !!(periode.value?.[0] || auteur.value.trim() || module.value || action.value),
  )

  function reset() {
    periode.value = null
    auteur.value = ''
    module.value = null
    action.value = null
    page.value = 1
  }

  return { periode, auteur, module, action, page, query, hasFilters, reset }
})
