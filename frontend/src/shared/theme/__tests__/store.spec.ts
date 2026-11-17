import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

import { useThemeStore } from '../store'

// jsdom under recent Node versions does not expose a usable localStorage,
// so the tests bring their own in-memory one.
function memoryStorage(): Storage {
  const items = new Map<string, string>()
  return {
    get length() {
      return items.size
    },
    clear: () => items.clear(),
    getItem: (key) => items.get(key) ?? null,
    key: (index) => [...items.keys()][index] ?? null,
    removeItem: (key) => void items.delete(key),
    setItem: (key, value) => void items.set(key, String(value)),
  }
}

describe('theme store', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', memoryStorage())
    document.documentElement.classList.remove('dark')
    setActivePinia(createPinia())
  })

  it('defaults to the system theme', () => {
    expect(useThemeStore().mode).toBe('system')
  })

  it('applies and persists dark mode', async () => {
    const theme = useThemeStore()

    theme.setMode('dark')
    await nextTick()

    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('syrh-theme')).toBe('dark')
  })

  it('removes the dark class when switching back to light', async () => {
    const theme = useThemeStore()
    theme.setMode('dark')
    await nextTick()

    theme.setMode('light')
    await nextTick()

    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('restores the saved mode', () => {
    localStorage.setItem('syrh-theme', 'dark')

    expect(useThemeStore().mode).toBe('dark')
  })
})
