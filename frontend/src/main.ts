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
import { getServiceFactory } from './services/ServiceFactory';


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

// Initialize all services
async function initializeServices() {
  try {
    // Initialize RUM first
    await initializeRUM();
    
    // Initialize AetherTerm services (Socket.IO, Workspace, etc.)
    const serviceFactory = getServiceFactory();
    await serviceFactory.initialize({
      socketUrl: import.meta.env.VITE_BACKEND_URL || 'http://localhost:57575',
      debug: environment.isDevelopment,
      timeout: 10000,
      reconnectionAttempts: 5,
      autoInitialize: true
    });
    
    if (environment.isDevelopment) {
      console.log('✅ All AetherTerm services initialized successfully');
    }
    
  } catch (error) {
    console.error('❌ Failed to initialize services:', error);
    // Continue mounting app even if services fail to initialize
  }
}

// Initialize services and mount app
initializeServices().then(() => {
  app.mount('#app');
}).catch((error) => {
  console.error('❌ Critical initialization error:', error);
  // Mount app anyway to show error state
  app.mount('#app');
});

// Note: Socket.IO connection is now managed centrally by ServiceFactory
// Components should use WorkspaceSocketService instead of direct Socket.IO
