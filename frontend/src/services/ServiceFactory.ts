/**
 * ServiceFactory - Centralized service initialization and management
 * 
 * Manages all Socket.IO services and their lifecycle
 */

import { getSocketManager, type AetherTermSocketManager } from './AetherTermSocketManager'
import { getWorkspaceService, type WorkspaceSocketService } from './workspace/WorkspaceSocketService'

export interface ServiceInitializationConfig {
  socketUrl?: string
  debug?: boolean
  timeout?: number
  reconnectionAttempts?: number
  autoInitialize?: boolean
}

/**
 * Service Factory for managing all AetherTerm services
 */
export class ServiceFactory {
  private static instance: ServiceFactory | null = null
  private socketManager: AetherTermSocketManager
  private workspaceService: WorkspaceSocketService
  private initialized: boolean = false

  private constructor() {
    this.socketManager = getSocketManager()
    this.workspaceService = getWorkspaceService()
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): ServiceFactory {
    if (!ServiceFactory.instance) {
      ServiceFactory.instance = new ServiceFactory()
    }
    return ServiceFactory.instance
  }

  /**
   * Initialize all services
   */
  public async initialize(config: ServiceInitializationConfig = {}): Promise<void> {
    if (this.initialized) {
      console.log('✅ Services already initialized')
      return
    }

    const {
      socketUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:57575',
      debug = import.meta.env.DEV,
      timeout = 10000,
      reconnectionAttempts = 5,
      autoInitialize = true
    } = config

    try {
      console.log('🚀 Initializing AetherTerm services...')

      // 1. Connect Socket.IO manager
      await this.socketManager.connect({
        url: socketUrl,
        debug,
        timeout,
        reconnectionAttempts
      })

      // 2. Register all services
      this.socketManager.registerService('workspace', this.workspaceService)

      // 3. Initialize workspace if auto-initialize is enabled
      if (autoInitialize) {
        await this.workspaceService.initializeWorkspace()
      }

      this.initialized = true
      console.log('✅ All AetherTerm services initialized successfully')

    } catch (error) {
      console.error('❌ Failed to initialize services:', error)
      throw error
    }
  }

  /**
   * Shutdown all services
   */
  public shutdown(): void {
    if (!this.initialized) {
      return
    }

    console.log('🔌 Shutting down AetherTerm services...')

    // Disconnect socket manager (this will cleanup all services)
    this.socketManager.disconnect()

    this.initialized = false
    console.log('✅ All services shut down')
  }

  /**
   * Get socket manager
   */
  public getSocketManager(): AetherTermSocketManager {
    return this.socketManager
  }

  /**
   * Get workspace service
   */
  public getWorkspaceService(): WorkspaceSocketService {
    return this.workspaceService
  }

  /**
   * Check if services are initialized
   */
  public isInitialized(): boolean {
    return this.initialized
  }

  /**
   * Wait for services to be ready
   */
  public async waitForReady(timeout: number = 30000): Promise<void> {
    if (this.initialized && this.socketManager.isConnected()) {
      return
    }

    return new Promise((resolve, reject) => {
      const timeoutHandle = setTimeout(() => {
        reject(new Error('Services initialization timeout'))
      }, timeout)

      const checkReady = () => {
        if (this.initialized && this.socketManager.isConnected()) {
          clearTimeout(timeoutHandle)
          resolve()
        } else {
          setTimeout(checkReady, 100)
        }
      }

      checkReady()
    })
  }

  /**
   * Get connection status
   */
  public getConnectionStatus() {
    return this.socketManager.getConnectionStatus()
  }

  /**
   * Get connection state
   */
  public getConnectionState() {
    return this.socketManager.getConnectionState()
  }

  /**
   * Reconnect if needed
   */
  public async reconnect(): Promise<void> {
    if (this.socketManager.isConnected()) {
      return
    }

    this.socketManager.disconnect()
    
    await this.socketManager.connect()
    
    // Re-initialize workspace
    await this.workspaceService.initializeWorkspace()
  }
}

// Export singleton instance getter
export const getServiceFactory = (): ServiceFactory => {
  return ServiceFactory.getInstance()
}

// Export for direct usage
export default ServiceFactory