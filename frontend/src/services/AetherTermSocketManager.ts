/**
 * AetherTermSocketManager - Singleton Socket.IO Connection Manager
 * 
 * Centralized Socket.IO connection management for all AetherTerm components.
 * Replaces multiple independent connections with a single shared connection.
 */

import { io, Socket } from 'socket.io-client'
import { ref, reactive, computed, type Ref } from 'vue'

// Connection state interface
export interface ConnectionState {
  status: 'disconnected' | 'connecting' | 'connected' | 'error'
  latency: number
  reconnectAttempts: number
  lastError: string | null
  connectedAt: Date | null
  socketId: string | null
}

// Event routing interface
export interface EventRoute {
  pattern: string | RegExp
  handler: (eventName: string, data: any) => void
  priority: number
}

// Service factory interface
export interface SocketService {
  initialize(manager: AetherTermSocketManager): void
  destroy(): void
  getEventPatterns(): string[]
}

/**
 * Singleton Socket.IO Connection Manager
 */
export class AetherTermSocketManager {
  private static instance: AetherTermSocketManager | null = null
  private socket: Socket | null = null
  private eventRoutes: EventRoute[] = []
  private services: Map<string, SocketService> = new Map()
  
  // Reactive connection state
  private _connectionState: Ref<ConnectionState> = ref({
    status: 'disconnected',
    latency: 0,
    reconnectAttempts: 0,
    lastError: null,
    connectedAt: null,
    socketId: null
  })

  // Request tracking for correlation
  private pendingRequests: Map<string, {
    resolve: (data: any) => void
    reject: (error: any) => void
    timestamp: number
    timeout: NodeJS.Timeout
  }> = new Map()

  private constructor() {
    // Private constructor for singleton pattern
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): AetherTermSocketManager {
    if (!AetherTermSocketManager.instance) {
      AetherTermSocketManager.instance = new AetherTermSocketManager()
    }
    return AetherTermSocketManager.instance
  }

  /**
   * Initialize connection with configuration
   */
  public async connect(options: {
    url?: string
    debug?: boolean
    timeout?: number
    reconnectionAttempts?: number
  } = {}): Promise<void> {
    const {
      url = import.meta.env.VITE_BACKEND_URL || 'http://localhost:57575',
      debug = false,
      timeout = 10000,
      reconnectionAttempts = 5
    } = options

    if (this.socket?.connected) {
      console.log('🔗 Socket.IO already connected')
      return
    }

    this.updateConnectionState({ status: 'connecting' })

    try {
      // Create single Socket.IO connection
      this.socket = io(url, {
        timeout,
        reconnectionAttempts,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        transports: ['websocket', 'polling'],
        upgrade: true,
        rememberUpgrade: true,
        forceNew: false  // ✅ Critical: Do NOT force new connections
      })

      this.setupEventHandlers()
      
      // Wait for connection
      await new Promise<void>((resolve, reject) => {
        const connectTimeout = setTimeout(() => {
          reject(new Error('Connection timeout'))
        }, timeout)

        this.socket!.once('connect', () => {
          clearTimeout(connectTimeout)
          this.updateConnectionState({
            status: 'connected',
            connectedAt: new Date(),
            socketId: this.socket!.id,
            reconnectAttempts: 0,
            lastError: null
          })
          resolve()
        })

        this.socket!.once('connect_error', (error) => {
          clearTimeout(connectTimeout)
          this.updateConnectionState({
            status: 'error',
            lastError: error.message
          })
          reject(error)
        })
      })

      console.log('✅ AetherTermSocketManager connected:', this.socket.id)
      
    } catch (error) {
      this.updateConnectionState({
        status: 'error',
        lastError: error instanceof Error ? error.message : 'Unknown error'
      })
      throw error
    }
  }

  /**
   * Setup core Socket.IO event handlers
   */
  private setupEventHandlers(): void {
    if (!this.socket) return

    // Connection events
    this.socket.on('connect', () => {
      this.updateConnectionState({
        status: 'connected',
        connectedAt: new Date(),
        socketId: this.socket!.id,
        reconnectAttempts: 0,
        lastError: null
      })
      console.log('🔗 Socket.IO connected:', this.socket!.id)
    })

    this.socket.on('disconnect', (reason) => {
      this.updateConnectionState({
        status: 'disconnected',
        connectedAt: null,
        socketId: null,
        lastError: reason
      })
      console.log('🔌 Socket.IO disconnected:', reason)
    })

    this.socket.on('reconnect', (attemptNumber) => {
      this.updateConnectionState({
        status: 'connected',
        reconnectAttempts: attemptNumber,
        lastError: null
      })
      console.log('🔄 Socket.IO reconnected after', attemptNumber, 'attempts')
    })

    this.socket.on('reconnect_error', (error) => {
      this.updateConnectionState({
        lastError: error.message
      })
    })

    this.socket.on('reconnect_failed', () => {
      this.updateConnectionState({
        status: 'error',
        lastError: 'Reconnection failed'
      })
      console.error('❌ Socket.IO reconnection failed')
    })

    // Latency monitoring
    this.socket.on('pong', (latency) => {
      this.updateConnectionState({ latency })
    })

    // Global event router - routes all events to registered services
    this.socket.onAny((eventName: string, ...args: any[]) => {
      this.routeEvent(eventName, args[0])
    })
  }

  /**
   * Route events to registered services
   */
  private routeEvent(eventName: string, data: any): void {
    // Sort routes by priority (higher priority first)
    const sortedRoutes = [...this.eventRoutes].sort((a, b) => b.priority - a.priority)
    
    for (const route of sortedRoutes) {
      let matches = false
      
      if (typeof route.pattern === 'string') {
        // Simple string pattern matching with wildcards
        const regex = new RegExp(route.pattern.replace(/\*/g, '.*'))
        matches = regex.test(eventName)
      } else {
        // RegExp pattern
        matches = route.pattern.test(eventName)
      }
      
      if (matches) {
        try {
          route.handler(eventName, data)
        } catch (error) {
          console.error(`❌ Error in event route for ${eventName}:`, error)
        }
        break // Stop after first match
      }
    }
  }

  /**
   * Register event route for service
   */
  public registerEventRoute(pattern: string | RegExp, handler: (eventName: string, data: any) => void, priority: number = 0): void {
    this.eventRoutes.push({ pattern, handler, priority })
    
    // Sort routes by priority
    this.eventRoutes.sort((a, b) => b.priority - a.priority)
  }

  /**
   * Unregister event route
   */
  public unregisterEventRoute(handler: (eventName: string, data: any) => void): void {
    this.eventRoutes = this.eventRoutes.filter(route => route.handler !== handler)
  }

  /**
   * Register a service
   */
  public registerService(name: string, service: SocketService): void {
    if (this.services.has(name)) {
      console.warn(`⚠️ Service ${name} already registered, replacing...`)
      this.services.get(name)?.destroy()
    }
    
    this.services.set(name, service)
    service.initialize(this)
    
    console.log(`✅ Service ${name} registered`)
  }

  /**
   * Unregister a service
   */
  public unregisterService(name: string): void {
    const service = this.services.get(name)
    if (service) {
      service.destroy()
      this.services.delete(name)
      console.log(`🗑️ Service ${name} unregistered`)
    }
  }

  /**
   * Emit event with optional response correlation
   */
  public emit(eventName: string, data?: any): void {
    if (!this.socket?.connected) {
      console.warn('⚠️ Socket not connected, cannot emit:', eventName)
      return
    }

    this.socket.emit(eventName, data)
  }

  /**
   * Emit event and wait for response with correlation
   */
  public async emitWithResponse<T = any>(
    requestEvent: string, 
    responseEvent: string, 
    data?: any, 
    timeout: number = 10000
  ): Promise<T> {
    if (!this.socket?.connected) {
      throw new Error('Socket not connected')
    }

    const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    return new Promise<T>((resolve, reject) => {
      // Set up timeout
      const timeoutHandle = setTimeout(() => {
        this.pendingRequests.delete(requestId)
        reject(new Error(`Request timeout after ${timeout}ms`))
      }, timeout)

      // Store request for correlation
      this.pendingRequests.set(requestId, {
        resolve,
        reject,
        timestamp: Date.now(),
        timeout: timeoutHandle
      })

      // Listen for response
      const responseHandler = (responseData: any) => {
        if (responseData._requestId === requestId) {
          const request = this.pendingRequests.get(requestId)
          if (request) {
            clearTimeout(request.timeout)
            this.pendingRequests.delete(requestId)
            resolve(responseData)
          }
          this.socket!.off(responseEvent, responseHandler)
        }
      }

      this.socket!.on(responseEvent, responseHandler)

      // Emit request with correlation ID
      this.socket!.emit(requestEvent, {
        ...data,
        _requestId: requestId
      })
    })
  }

  /**
   * Get connection state (reactive)
   */
  public getConnectionState(): Readonly<Ref<ConnectionState>> {
    return this._connectionState
  }

  /**
   * Get connection status (computed)
   */
  public getConnectionStatus() {
    return computed(() => this._connectionState.value.status)
  }

  /**
   * Check if connected
   */
  public isConnected(): boolean {
    return this.socket?.connected === true
  }

  /**
   * Get raw socket instance (use sparingly)
   */
  public getSocket(): Socket | null {
    return this.socket
  }

  /**
   * Disconnect and cleanup
   */
  public disconnect(): void {
    if (this.socket) {
      // Cleanup all services
      for (const [name, service] of this.services) {
        service.destroy()
      }
      this.services.clear()
      
      // Clear event routes
      this.eventRoutes = []
      
      // Clear pending requests
      for (const request of this.pendingRequests.values()) {
        clearTimeout(request.timeout)
        request.reject(new Error('Connection closed'))
      }
      this.pendingRequests.clear()
      
      // Disconnect socket
      this.socket.disconnect()
      this.socket = null
      
      this.updateConnectionState({
        status: 'disconnected',
        connectedAt: null,
        socketId: null
      })
      
      console.log('🔌 AetherTermSocketManager disconnected')
    }
  }

  /**
   * Update connection state
   */
  private updateConnectionState(updates: Partial<ConnectionState>): void {
    Object.assign(this._connectionState.value, updates)
  }

  /**
   * Get service instance
   */
  public getService<T extends SocketService>(name: string): T | null {
    return (this.services.get(name) as T) || null
  }

  /**
   * Get all registered services
   */
  public getServices(): string[] {
    return Array.from(this.services.keys())
  }
}

// Export singleton instance getter
export const getSocketManager = (): AetherTermSocketManager => {
  return AetherTermSocketManager.getInstance()
}

// Export for direct usage
export default AetherTermSocketManager