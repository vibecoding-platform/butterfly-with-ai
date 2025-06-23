import { createPinia } from 'pinia';
import { createApp } from 'vue';
// VueTerm removed - not using vue-term library
import { register } from 'vue-advanced-chat';
import App from './App.vue';
import router from './router';
import TrackedSocketService from './services/tracking/TrackedSocketService';
import { useAetherTerminalServiceStore } from './stores/aetherTerminalServiceStore';
import { openTelemetryService } from './services/OpenTelemetryService';
import { environment } from './config/environment';


// Register vue-advanced-chat
register();

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);


// VueTerm component registration removed

// Initialize TrackedSocketService with connection tracking (but don't connect yet)
const trackedSocketService = TrackedSocketService.getInstance({
  defaultTimeout: 5000,
  slowResponseThreshold: 1000,
  enableDetailedLogging: true,
  enableMetrics: true
});

// Initialize the store without immediate connection
const terminalStore = useAetherTerminalServiceStore();

// Initialize OpenTelemetry RUM
async function initializeRUM() {
  try {
    await openTelemetryService.initialize({
      debug: environment.isDevelopment,
      serviceName: 'aetherterm-frontend',
      serviceNamespace: 'aetherterm',
      environment: environment.isDevelopment ? 'development' : 'production'
    });
    
    // Set initial user context
    openTelemetryService.updateContext({
      userId: 'anonymous',
      sessionId: crypto.randomUUID()
    });
    
    if (environment.isDevelopment) {
      console.log('✅ RUM (OpenTelemetry) initialized successfully');
    }
  } catch (error) {
    console.error('❌ Failed to initialize RUM:', error);
  }
}

// Initialize RUM before mounting the app
initializeRUM();

app.mount('#app');

// Note: Connection and session initialization will be handled by SessionManager component
// after workspace data is loaded and existing sessions are restored
