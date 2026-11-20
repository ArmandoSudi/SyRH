<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import type { MenuItem } from 'primevue/menuitem'

import type { Mode } from '@/features/referentiels/components/edition/EditionDialog.vue'

/**
 * The menu at the end of a row (reference data screens D11): Corriger, Remplacer à une
 * date, Fermer. A closed row offers only Corriger; each item needs its permission.
 */
const props = defineProps<{
  ferme: boolean
  peutModifier: boolean
  peutRemplacer: boolean
  libelle: string
}>()

const emit = defineEmits<{ action: [mode: Mode] }>()
const menu = ref<InstanceType<typeof Menu> | null>(null)

const items = computed<MenuItem[]>(() => {
  const list: MenuItem[] = []
  if (props.peutModifier) {
    list.push({
      label: 'Corriger',
      icon: 'pi pi-pencil',
      command: () => emit('action', 'corriger'),
    })
  }
  if (!props.ferme && props.peutRemplacer) {
    list.push({
      label: 'Remplacer à une date',
      icon: 'pi pi-calendar-plus',
      command: () => emit('action', 'remplacer'),
    })
  }
  if (!props.ferme && props.peutModifier) {
    list.push({ label: 'Fermer', icon: 'pi pi-ban', command: () => emit('action', 'fermer') })
  }
  return list
})

function toggle(event: Event) {
  menu.value?.toggle(event)
}
</script>

<template>
  <template v-if="items.length">
    <Button
      icon="pi pi-ellipsis-v"
      text
      rounded
      size="small"
      severity="secondary"
      :aria-label="`Actions pour ${libelle}`"
      aria-haspopup="true"
      data-test="ligne-actions"
      @click="toggle"
    />
    <Menu ref="menu" :model="items" popup data-test="ligne-menu" />
  </template>
</template>
