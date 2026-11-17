<script setup lang="ts">
import { useThemeStore, type ThemeMode } from '@/shared/theme/store'

const theme = useThemeStore()

const options: { mode: ThemeMode; icon: string; label: string }[] = [
  { mode: 'light', icon: 'pi pi-sun', label: 'Thème clair' },
  { mode: 'dark', icon: 'pi pi-moon', label: 'Thème sombre' },
  { mode: 'system', icon: 'pi pi-desktop', label: 'Thème du système' },
]
</script>

<template>
  <div class="toggle" role="radiogroup" aria-label="Thème d'affichage">
    <button
      v-for="option in options"
      :key="option.mode"
      type="button"
      role="radio"
      :aria-checked="theme.mode === option.mode"
      :aria-label="option.label"
      :title="option.label"
      :class="{ active: theme.mode === option.mode }"
      @click="theme.setMode(option.mode)"
    >
      <i :class="option.icon" aria-hidden="true" />
    </button>
  </div>
</template>

<style scoped>
.toggle {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  border-radius: var(--sy-radius-pill);
  background: var(--sy-surface);
  border: 1px solid var(--sy-border);
}

button {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--sy-muted);
  cursor: pointer;
}

button:hover {
  color: var(--sy-text);
}

button.active {
  background: var(--sy-inverse);
  color: var(--sy-on-inverse);
}
</style>
