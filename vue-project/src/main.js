import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { initAuth } from './lib/auth'

initAuth().finally(() => {
  createApp(App).use(router).mount('#app')
})
