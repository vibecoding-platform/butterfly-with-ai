import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { register } from 'vue-advanced-chat'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'
import AetherTermService from './services/AetherTermService'
import { useAetherTerminalServiceStore } from './stores/aetherTerminalServiceStore'
import { useWorkspaceStore } from './stores/workspaceStore'
import { useThemeStore } from './stores/themeStore'
import { initializeTelemetry, getEnvironmentConfig } from './utils/telemetry'

// Initialize OpenTelemetry for frontend tracing
try {
  const telemetryConfig = getEnvironmentConfig()
  initializeTelemetry(telemetryConfig)
  console.log('🔬 Frontend telemetry initialized')
} catch (error) {
  console.warn('⚠️ Frontend telemetry initialization failed:', error)
}

// Register vue-advanced-chat
register()

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(vuetify)

// Initialize AetherTermService and connect it to the store
const aetherTermService = AetherTermService.getInstance()
const socket = aetherTermService.connect()

// Initialize the store with the socket connection
const terminalStore = useAetherTerminalServiceStore()
terminalStore.setSocket(socket)

// Initialize workspace system
const workspaceStore = useWorkspaceStore()

// Initialize theme system
const themeStore = useThemeStore()

// Setup application initialization
const initializeApp = async () => {
  try {
    console.log('🚀 APP: Initializing application...')
    
    // Initialize theme system first (before any UI rendering)
    console.log('🎨 THEME: Loading theme configuration...')
    await themeStore.loadThemeConfig()
    console.log('🎨 THEME: Theme system initialized successfully')
    
    // Connect to service
    await terminalStore.connect()
    
    // Initialize workspace system (this will resume last workspace or create default)
    await workspaceStore.initializeWorkspace()
    
    console.log('🚀 APP: Application initialized successfully')
  } catch (error) {
    console.error('🚀 APP: Failed to initialize application:', error)
    // Fallback: create default workspace if everything fails
    workspaceStore.createDefaultWorkspace()
  }
}

// Initialize after mounting
app.mount('#app')

// Initialize application after Vue is mounted
setTimeout(() => {
  initializeApp()
}, 100)
