import { ref } from 'vue'
import { applyTheme } from '../utils/theme'

export const isDark = ref(document.documentElement.classList.contains('dark'))

export function toggleTheme() {
  const next = isDark.value ? 'light' : 'dark'
  applyTheme(next)
  isDark.value = next === 'dark'
}

export function syncThemeState() {
  isDark.value = document.documentElement.classList.contains('dark')
}
