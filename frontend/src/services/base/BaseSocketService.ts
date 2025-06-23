/**
 * BaseSocketService - Abstract base class for Socket.IO services
 * 
 * Provides common functionality for all socket-based services
 */

import type { AetherTermSocketManager, SocketService } from '../AetherTermSocketManager'

export abstract class BaseSocketService implements SocketService {
  protected manager: AetherTermSocketManager | null = null
  protected eventHandlers: Map<string, (eventName: string, data: any) => void> = new Map()
  
  /**
   * Initialize service with socket manager
   */
  public initialize(manager: AetherTermSocketManager): void {
    this.manager = manager
    this.setupEventHandlers()
    this.onInitialize()
  }

  /**
   * Destroy service and cleanup
   */
  public destroy(): void {
    // Unregister all event handlers
    for (const handler of this.eventHandlers.values()) {
      this.manager?.unregisterEventRoute(handler)
    }
    this.eventHandlers.clear()
    
    this.onDestroy()
    this.manager = null
  }

  /**
   * Get event patterns this service handles
   */
  public abstract getEventPatterns(): string[]

  /**
   * Setup event handlers - called during initialization
   */
  protected setupEventHandlers(): void {
    if (!this.manager) return

    const patterns = this.getEventPatterns()
    
    for (const pattern of patterns) {
      const handler = (eventName: string, data: any) => {
        this.handleEvent(eventName, data)
      }
      
      this.eventHandlers.set(pattern, handler)
      this.manager.registerEventRoute(pattern, handler, this.getPriority())
    }
  }

  /**
   * Handle incoming events
   */
  protected abstract handleEvent(eventName: string, data: any): void

  /**
   * Get priority for event routing (higher = processed first)
   */
  protected getPriority(): number {
    return 0
  }

  /**
   * Called when service is initialized
   */
  protected onInitialize(): void {
    // Override in subclasses if needed
  }

  /**
   * Called when service is destroyed
   */
  protected onDestroy(): void {
    // Override in subclasses if needed
  }

  /**
   * Emit event via manager
   */
  protected emit(eventName: string, data?: any): void {
    if (!this.manager) {
      console.warn(`⚠️ ${this.constructor.name}: Manager not initialized`)
      return
    }
    
    this.manager.emit(eventName, data)
  }

  /**
   * Emit event and wait for response
   */
  protected async emitWithResponse<T = any>(
    requestEvent: string,
    responseEvent: string,
    data?: any,
    timeout?: number
  ): Promise<T> {
    if (!this.manager) {
      throw new Error(`${this.constructor.name}: Manager not initialized`)
    }
    
    return this.manager.emitWithResponse<T>(requestEvent, responseEvent, data, timeout)
  }

  /**
   * Check if manager is connected
   */
  protected isConnected(): boolean {
    return this.manager?.isConnected() === true
  }

  /**
   * Get connection state
   */
  protected getConnectionState() {
    return this.manager?.getConnectionState()
  }

  /**
   * Log with service name prefix
   */
  protected log(message: string, ...args: any[]): void {
    console.log(`🔌 ${this.constructor.name}:`, message, ...args)
  }

  /**
   * Log warning with service name prefix
   */
  protected warn(message: string, ...args: any[]): void {
    console.warn(`⚠️ ${this.constructor.name}:`, message, ...args)
  }

  /**
   * Log error with service name prefix
   */
  protected error(message: string, ...args: any[]): void {
    console.error(`❌ ${this.constructor.name}:`, message, ...args)
  }
}