import { createPinia } from 'pinia'
import { createApp } from 'vue'
import VueTerm from 'vue-term'
// import 'vue-term/dist/style.css'; // This path seems incorrect, commenting out for now
import { register } from 'vue-advanced-chat'
import App from './App.vue'
import router from './router'
import AetherTermService from './services/AetherTermService'
import { useAetherTerminalServiceStore } from './stores/aetherTerminalServiceStore'

// Register vue-advanced-chat
register()

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.component('VueTerm', VueTerm) // Register VueTerm globally

// Initialize AetherTermService and connect it to the store
const aetherTermService = AetherTermService.getInstance()
const socket = aetherTermService.connect()

// Initialize the store with the socket connection
const terminalStore = useAetherTerminalServiceStore()
//terminalStore.setSocket(socket);
terminalStore.setSocket(socket)
terminalStore.initializeSession(`session_${Date.now()}`)

app.mount('#app')
