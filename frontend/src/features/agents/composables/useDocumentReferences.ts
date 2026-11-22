import { ref } from 'vue'

import { typesDeposables } from '@/features/agents/components/documents'
import { useAuthStore } from '@/features/auth/stores/auth'
import {
  fetchParametres,
  fetchTypesDocument,
  type TypeDocument,
} from '@/features/referentiels/api/referentiels'
import { localDate } from '@/shared/utils/dates'

/**
 * What the add dialog needs (document storage D12, D22): the document types open today
 * that the user may upload, and the size limit in Mo (null when it cannot be read).
 */
export function useDocumentReferences() {
  const auth = useAuthStore()
  const types = ref<TypeDocument[]>([])
  const maxMo = ref<number | null>(null)

  async function load() {
    const today = localDate(new Date())
    const [typeRows, parametres] = await Promise.allSettled([
      fetchTypesDocument({ date: today }),
      fetchParametres({ date: today }),
    ])
    if (typeRows.status === 'fulfilled') {
      types.value = typesDeposables(typeRows.value, auth.user?.groups ?? [])
    }
    if (parametres.status === 'fulfilled') {
      maxMo.value = parametres.value.find((p) => p.cle === 'taille_max_piece')?.valeur ?? null
    }
  }

  return { types, maxMo, load }
}
