import { io, Socket } from 'socket.io-client'
import { socketUrl, apiBaseUrl } from '../config/environment'
import type { InventoryItem, InventorySummary } from '../types/inventory'

interface VueTermWebSockets {
  shellWs: WebSocket | null
  ctlWs: WebSocket | null
}

class AetherTermService {
  private socket: Socket | null = null
  private shellWs: WebSocket | null = null
  private ctlWs: WebSocket | null = null
  private static instance: AetherTermService

  private constructor() {}

  static getInstance(): AetherTermService {
    if (!AetherTermService.instance) {
      AetherTermService.instance = new AetherTermService()
    }
    return AetherTermService.instance
  }

  connect(): Socket {
    if (!this.socket) {
      this.socket = io(socketUrl || window.location.origin, {
        path: '/socket.io',
      })

      this.socket.on('connect', () => {
        console.log('AetherTerm Socket.IO connected')
        this.setupVueTermWebSockets()
      })

      this.socket.on('disconnect', () => {
        console.log('AetherTerm Socket.IO disconnected')
        this.closeVueTermWebSockets()
      })
    }
    return this.socket
  }

  private setupVueTermWebSockets(): void {
    // No need to create separate WebSocket connections for VueTerm
    // VueTerm will use the existing Socket.IO connection
    console.log('VueTerm using Socket.IO')
  }

  private closeVueTermWebSockets(): void {
    // No need to close separate WebSocket connections
  }

  getSocket(): Socket | null {
    return this.socket
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
    this.closeVueTermWebSockets()
  }

  // Terminal specific methods (using Socket.IO)
  // onShellOutput(callback: (data: string) => void): void {
  //   if (this.socket) {
  //     this.socket.on('shell_output', callback)
  //   }
  // }

  onControlOutput(callback: (data: string) => void): void {
    if (this.socket) {
      this.socket.on('ctl_output', callback)
    }
  }

  // Connection event methods
  onConnect(callback: () => void): void {
    if (this.socket) {
      this.socket.on('connect', callback)
    }
  }

  onDisconnect(callback: () => void): void {
    if (this.socket) {
      this.socket.on('disconnect', callback)
    }
  }

  onError(callback: (error: any) => void): void {
    if (this.socket) {
      this.socket.on('connect_error', callback)
    }
  }

  // Chat specific methods (using Socket.IO)
  onChatMessage(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on('chat_message', callback)
    }
  }

  sendChatMessage(message: any): void {
    if (this.socket) {
      this.socket.emit('chat_message', message)
    }
  }

  // Terminal command methods (using Socket.IO)
  sendCommand(command: string, commandId?: string): void {
    if (this.socket) {
      console.log('Sending command:', command) // Debug log
      this.socket.emit('terminal_command', {
        command: command,
        commandId: commandId || Date.now().toString(),
      })
    }
  }

  // Admin control methods (using Socket.IO)
  onAdminPauseTerminal(callback: (data: { reason: string }) => void): void {
    if (this.socket) {
      this.socket.on('admin_pause_terminal', callback)
    }
  }

  onAdminResumeTerminal(callback: () => void): void {
    if (this.socket) {
      this.socket.on('admin_resume_terminal', callback)
    }
  }

  onAdminSuppressOutput(callback: (data: { suppress: boolean; reason?: string }) => void): void {
    if (this.socket) {
      this.socket.on('admin_suppress_output', callback)
    }
  }

  onCommandApproval(
    callback: (data: { commandId: string; approved: boolean; reason?: string }) => void
  ): void {
    if (this.socket) {
      this.socket.on('command_approval', callback)
    }
  }

  // Emit command review required
  emitCommandReviewRequired(data: {
    commandId: string
    command: string
    riskLevel: string
    aiSuggestion: string
  }): void {
    if (this.socket) {
      this.socket.emit('command_review_required', data)
    }
  }

  // Cleanup methods
  offShellOutput(callback?: (data: string) => void): void {
    if (this.socket) {
      this.socket.off('shell_output', callback)
    }
  }

  offControlOutput(callback?: (data: string) => void): void {
    if (this.socket) {
      this.socket.off('ctl_output', callback)
    }
  }

  offChatMessage(callback?: (data: any) => void): void {
    if (this.socket) {
      this.socket.off('chat_message', callback)
    }
  }

  offConnect(callback?: () => void): void {
    if (this.socket) {
      this.socket.off('connect', callback)
    }
  }

  offDisconnect(callback?: () => void): void {
    if (this.socket) {
      this.socket.off('disconnect', callback)
    }
  }

  offError(callback?: (error: any) => void): void {
    if (this.socket) {
      this.socket.off('connect_error', callback)
    }
  }

  // Inventory HTTP methods (REST API calls)
  
  /**
   * Make HTTP request to inventory API
   */
  private async makeInventoryRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${apiBaseUrl}/api/inventory${endpoint}`
    
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(`HTTP ${response.status}: ${errorData.detail || errorData.message || 'Request failed'}`)
      }

      return await response.json()
    } catch (error) {
      console.error(`Inventory API request failed [${endpoint}]:`, error)
      throw error
    }
  }

  /**
   * Get inventory summary via HTTP
   */
  async getInventorySummary(): Promise<InventorySummary> {
    return this.makeInventoryRequest<InventorySummary>('/summary')
  }

  /**
   * Get inventory resources via HTTP
   */
  async getInventoryResources(options: {
    limit?: number
    provider?: string
    resource_type?: string
  } = {}): Promise<InventoryItem[]> {
    const params = new URLSearchParams()
    
    if (options.limit) params.append('limit', options.limit.toString())
    if (options.provider) params.append('provider', options.provider)
    if (options.resource_type) params.append('resource_type', options.resource_type)
    
    const endpoint = `/resources${params.toString() ? `?${params.toString()}` : ''}`
    return this.makeInventoryRequest<InventoryItem[]>(endpoint)
  }

  /**
   * Search inventory via HTTP
   */
  async searchInventory(searchTerm: string, providerFilter?: string): Promise<InventoryItem[]> {
    return this.makeInventoryRequest<InventoryItem[]>('/search', {
      method: 'POST',
      body: JSON.stringify({
        search_term: searchTerm,
        provider_filter: providerFilter
      })
    })
  }

  /**
   * Get service status via HTTP
   */
  async getInventoryServiceStatus(): Promise<any> {
    return this.makeInventoryRequest('/status')
  }

  /**
   * Trigger inventory sync via HTTP
   */
  async syncInventory(): Promise<any> {
    return this.makeInventoryRequest('/sync', {
      method: 'POST'
    })
  }

  // Socket.IO inventory events

  /**
   * Listen for inventory update events
   */
  onInventoryUpdate(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on('inventory_update', callback)
    }
  }

  /**
   * Listen for inventory sync status
   */
  onInventorySyncStatus(callback: (data: { status: string; progress: number; message: string }) => void): void {
    if (this.socket) {
      this.socket.on('inventory_sync_status', callback)
    }
  }

  /**
   * Request inventory refresh via socket
   */
  requestInventoryRefresh(): void {
    if (this.socket) {
      this.socket.emit('request_inventory_refresh')
    }
  }

  /**
   * Subscribe to inventory resource updates
   */
  subscribeToResourceUpdates(resourceId: string): void {
    if (this.socket) {
      this.socket.emit('subscribe_resource_updates', { resource_id: resourceId })
    }
  }

  /**
   * Unsubscribe from inventory resource updates
   */
  unsubscribeFromResourceUpdates(resourceId: string): void {
    if (this.socket) {
      this.socket.emit('unsubscribe_resource_updates', { resource_id: resourceId })
    }
  }

  // Cleanup methods for inventory events

  offInventoryUpdate(callback?: (data: any) => void): void {
    if (this.socket) {
      this.socket.off('inventory_update', callback)
    }
  }

  offInventorySyncStatus(callback?: (data: any) => void): void {
    if (this.socket) {
      this.socket.off('inventory_sync_status', callback)
    }
  }
}

export default AetherTermService
