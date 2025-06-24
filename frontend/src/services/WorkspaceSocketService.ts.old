/**
 * Workspace management socket service for multi-window synchronization
 */

import { io, Socket } from 'socket.io-client'
import type { Tab, TerminalPane } from '@/types/session'

export interface UIState {
  activeTabId?: string
  panelWidth: number
  isPanelVisible: boolean
  panelPosition: { x: number; y: number }
  lastUpdated: string
}

export interface WorkspaceState {
  tabs: Tab[]
  uiState: UIState
  connectedClients: number
  timestamp: string
}

class WorkspaceSocketService {
  private socket: Socket | null = null
  private _callbacks: Map<string, Function[]> = new Map()
  private _isInitialized = false

  constructor() {
    // Lazy initialization
  }

  connect(url: string = 'http://localhost:57575') {
    if (this.socket?.connected) {
      console.log('Workspace socket already connected')
      return
    }

    this.socket = io(url, {
      transports: ['websocket', 'polling'],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    })

    this.setupEventListeners()
    
    return new Promise<void>((resolve, reject) => {
      if (!this.socket) {
        reject(new Error('Failed to create socket'))
        return
      }

      this.socket.on('connect', () => {
        console.log('Connected to workspace socket')
        this.initializeWorkspace()
        resolve()
      })

      this.socket.on('connect_error', (error) => {
        console.error('Workspace socket connection error:', error)
        reject(error)
      })

      setTimeout(() => {
        reject(new Error('Workspace socket connection timeout'))
      }, 5000)
    })
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this._isInitialized = false
    }
  }

  private setupEventListeners() {
    if (!this.socket) return

    // Workspace initialization
    this.socket.on('workspace:initialized', (data: WorkspaceState) => {
      console.log('Workspace initialized:', data)
      this._isInitialized = true
      this._emit('workspace:initialized', data)
    })

    // Tab events
    this.socket.on('workspace:tab_created', (data: { tab: Tab }) => {
      console.log('Tab created:', data.tab)
      this._emit('workspace:tab_created', data)
    })

    this.socket.on('workspace:tab_switched', (data: { tabId: string; uiState: UIState }) => {
      console.log('Tab switched:', data.tabId)
      this._emit('workspace:tab_switched', data)
    })

    this.socket.on('workspace:tab_closed', (data: { tabId: string; uiState: UIState }) => {
      console.log('Tab closed:', data.tabId)
      this._emit('workspace:tab_closed', data)
    })

    // Pane events
    this.socket.on('workspace:pane_created', (data: { tabId: string; pane: TerminalPane; direction: string }) => {
      console.log('Pane created:', data.pane)
      this._emit('workspace:pane_created', data)
    })

    this.socket.on('workspace:pane_closed', (data: { tabId: string; paneId: string; tab: Tab }) => {
      console.log('Pane closed:', data.paneId)
      this._emit('workspace:pane_closed', data)
    })

    // UI state events
    this.socket.on('workspace:ui_updated', (data: { uiState: UIState; updates: any }) => {
      console.log('UI state updated:', data.updates)
      this._emit('workspace:ui_updated', data)
    })

    // Sync events
    this.socket.on('workspace:synced', (data: WorkspaceState) => {
      console.log('Workspace synced:', data)
      this._emit('workspace:synced', data)
    })

    // Error handling
    this.socket.on('workspace:error', (data: { error: string }) => {
      console.error('Workspace error:', data.error)
      this._emit('workspace:error', data)
    })
  }

  // Initialize workspace for this client
  private initializeWorkspace() {
    if (!this.socket) return

    this.socket.emit('workspace:initialize', {
      environ: {
        // Add any environment data if needed
      }
    })
  }

  // Tab operations
  async createTab(title?: string, type: string = 'terminal'): Promise<void> {
    if (!this.socket?.connected) {
      throw new Error('Workspace socket not connected')
    }

    this.socket.emit('workspace:tab:create', {
      title,
      type
    })
  }

  async switchTab(tabId: string): Promise<void> {
    if (!this.socket?.connected) {
      throw new Error('Workspace socket not connected')
    }

    this.socket.emit('workspace:tab:switch', {
      tabId
    })
  }

  async closeTab(tabId: string): Promise<void> {
    if (!this.socket?.connected) {
      throw new Error('Workspace socket not connected')
    }

    this.socket.emit('workspace:tab:close', {
      tabId
    })
  }

  // Pane operations
  async splitPane(tabId: string, paneId: string, direction: 'horizontal' | 'vertical' = 'horizontal'): Promise<void> {
    if (!this.socket?.connected) {
      throw new Error('Workspace socket not connected')
    }

    this.socket.emit('workspace:pane:split', {
      tabId,
      paneId,
      direction
    })
  }

  async closePane(tabId: string, paneId: string): Promise<void> {
    if (!this.socket?.connected) {
      throw new Error('Workspace socket not connected')
    }

    this.socket.emit('workspace:pane:close', {
      tabId,
      paneId
    })
  }

  // UI state operations
  async updateUIState(updates: Partial<UIState>): Promise<void> {
    if (!this.socket?.connected) {
      throw new Error('Workspace socket not connected')
    }

    this.socket.emit('workspace:ui:update', {
      updates
    })
  }

  // Request full workspace sync
  async requestSync(): Promise<void> {
    if (!this.socket?.connected) {
      throw new Error('Workspace socket not connected')
    }

    this.socket.emit('workspace:sync:request')
  }

  // Event subscription
  on(event: string, callback: Function): void {
    if (!this._callbacks.has(event)) {
      this._callbacks.set(event, [])
    }
    this._callbacks.get(event)!.push(callback)
  }

  off(event: string, callback?: Function): void {
    if (!callback) {
      this._callbacks.delete(event)
      return
    }

    const callbacks = this._callbacks.get(event)
    if (callbacks) {
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  private _emit(event: string, data: any): void {
    const callbacks = this._callbacks.get(event)
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Error in workspace event callback for ${event}:`, error)
        }
      })
    }
  }

  // Utility methods
  get isConnected(): boolean {
    return this.socket?.connected || false
  }

  get isInitialized(): boolean {
    return this._isInitialized
  }
}

// Singleton instance
let workspaceSocketService: WorkspaceSocketService | null = null

export function getWorkspaceSocketService(): WorkspaceSocketService {
  if (!workspaceSocketService) {
    workspaceSocketService = new WorkspaceSocketService()
  }
  return workspaceSocketService
}

export default WorkspaceSocketService