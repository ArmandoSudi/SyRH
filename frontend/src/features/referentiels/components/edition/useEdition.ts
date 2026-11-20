import { computed, ref } from 'vue'
import { useToast } from 'primevue/usetoast'

import type { TableEditable, Valeurs } from '@/features/referentiels/api/edition'
import {
  EDITIONS,
  peutAjouter,
  peutModifier,
  peutRemplacer,
} from '@/features/referentiels/components/edition/champs'
import type { Mode } from '@/features/referentiels/components/edition/EditionDialog.vue'
import { useAuthStore } from '@/features/auth/stores/auth'

/**
 * What a tab needs to edit one table: the user's rights on it (D10), the dialog's state,
 * and what happens after a save (a confirmation and a reload, D13).
 */
export function useEdition(table: TableEditable, reload: () => unknown) {
  const auth = useAuthStore()
  const toast = useToast()
  const edition = EDITIONS[table]
  const can = (permission: string) => auth.can(permission)

  const droits = computed(() => ({
    ajouter: peutAjouter(can, edition),
    modifier: peutModifier(can, edition),
    remplacer: peutRemplacer(can, edition),
  }))

  const visible = ref(false)
  const mode = ref<Mode>('ajouter')
  const ligne = ref<Valeurs | null>(null)
  const initial = ref<Valeurs | undefined>(undefined)

  function ouvrir(nouveau: Mode, row: Valeurs | null = null, depart?: Valeurs) {
    mode.value = nouveau
    ligne.value = row
    initial.value = depart
    visible.value = true
  }

  function enregistre() {
    toast.add({ severity: 'success', summary: edition.confirmation, life: 3000 })
    void reload()
  }

  return { edition, droits, visible, mode, ligne, initial, ouvrir, enregistre }
}
