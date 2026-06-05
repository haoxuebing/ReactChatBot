import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import { initTheme } from './utils/theme'
import { syncThemeState } from './composables/useTheme'

initTheme()
syncThemeState()
createApp(App).mount('#app')
