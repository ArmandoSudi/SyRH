import { computed, ref, watchEffect } from 'vue'
import { defineStore } from 'pinia'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'syrh-theme'
const MODES: ThemeMode[] = ['light', 'dark', 'system']

function readStoredMode(): ThemeMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY) as ThemeMode | null
    return stored && MODES.includes(stored) ? stored : 'system'
  } catch {
    return 'system'
  }
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(readStoredMode())

  const systemQuery =
    typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-color-scheme: dark)')
      : null
  const systemIsDark = ref(systemQuery?.matches ?? false)
  systemQuery?.addEventListener('change', (event) => {
    systemIsDark.value = event.matches
  })

  const isDark = computed(() =>
    mode.value === 'system' ? systemIsDark.value : mode.value === 'dark',
  )

  // The same class is set before first paint by the inline script in index.html.
  watchEffect(() => {
    document.documentElement.classList.toggle('dark', isDark.value)
  })

  function setMode(next: ThemeMode) {
    mode.value = next
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Storage unavailable (private mode): the choice lasts for this page only.
    }
  }

  return { mode, isDark, setMode }
})
