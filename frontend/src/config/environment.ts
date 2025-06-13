// Environment configuration for backend connection
export interface BackendConfig {
  host: string
  port: number
  protocol: 'http' | 'https'
  socketPath: string
}

// Development configuration (can be overridden)
const developmentConfig: BackendConfig = {
  host: import.meta.env.VITE_BACKEND_HOST || 'localhost',
  port: parseInt(import.meta.env.VITE_BACKEND_PORT || '57575') || 57575,
  protocol: (import.meta.env.VITE_BACKEND_PROTOCOL as 'http' | 'https') || 'http',
  socketPath: import.meta.env.VITE_SOCKET_PATH || '/socket.io/'
}

// Production configuration (derived from current location)
const productionConfig: BackendConfig = {
  host: window.location.hostname,
  port: parseInt(window.location.port) || (window.location.protocol === 'https:' ? 443 : 80),
  protocol: window.location.protocol.replace(':', '') as 'http' | 'https',
  socketPath: window.location.pathname + 'socket.io/'
}

// Determine if we're in development mode
const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development'

// Export the appropriate configuration
export const backendConfig: BackendConfig = isDevelopment ? developmentConfig : productionConfig

// Helper function to get the full backend URL
export const getBackendUrl = (): string => {
  return `${backendConfig.protocol}://${backendConfig.host}:${backendConfig.port}`
}

// Helper function to get the socket.io URL
export const getSocketUrl = (): string => {
  return getBackendUrl()
}

// Helper function to get the socket.io path
export const getSocketPath = (): string => {
  return backendConfig.socketPath
}

// Debug information
export const getConnectionInfo = () => {
  return {
    mode: isDevelopment ? 'development' : 'production',
    backendUrl: getBackendUrl(),
    socketUrl: getSocketUrl(),
    socketPath: getSocketPath(),
    config: backendConfig
  }
}