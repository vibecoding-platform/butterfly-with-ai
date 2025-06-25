/**
 * Environment configuration for AetherTerm frontend
 */

export interface EnvironmentConfig {
  isDevelopment: boolean
  isProduction: boolean
  enableDevTools: boolean
  enableJWTDevRegister: boolean
  apiBaseUrl: string
  socketUrl: string
}

// Detect development environment
const isDev =
  import.meta.env.DEV ||
  import.meta.env.MODE === 'development' ||
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1' ||
  window.location.hostname.includes('dev') ||
  window.location.port !== ''

export const environment: EnvironmentConfig = {
  isDevelopment: isDev,
  isProduction: !isDev,
  enableDevTools: isDev,
  enableJWTDevRegister: isDev, // Only enable JWT dev registration in development
  apiBaseUrl: isDev ? 'http://localhost:57575' : '',
  socketUrl: isDev ? 'http://localhost:57575' : '',
}

// Export individual flags for convenience
export const {
  isDevelopment,
  isProduction,
  enableDevTools,
  enableJWTDevRegister,
  apiBaseUrl,
  socketUrl,
} = environment

// Debug logging in development
if (isDevelopment) {
  console.log('🔧 AetherTerm Environment Configuration:', environment)
  console.log('🌍 Current location:', {
    hostname: window.location.hostname,
    port: window.location.port,
    protocol: window.location.protocol,
    href: window.location.href,
  })
  console.log('⚡ Vite Environment:', {
    DEV: import.meta.env.DEV,
    PROD: import.meta.env.PROD,
    MODE: import.meta.env.MODE,
  })
}
