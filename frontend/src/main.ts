import '@fontsource-variable/plus-jakarta-sans'
import 'primeicons/primeicons.css'
import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { fr } from 'primelocale/js/fr.js'

import App from './App.vue'
import router from './router'
import { SyRHPreset } from './theme/preset'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  locale: fr,
  theme: {
    preset: SyRHPreset,
    options: {
      darkModeSelector: '.dark',
    },
  },
})

app.mount('#app')
