/**
 * WorkspaceSocketService - Workspace management via unified Socket.IO
 * 
 * Handles all workspace-related Socket.IO events through the centralized manager
 */

import { ref, reactive, type Ref } from 'vue'
import { BaseSocketService } from '../base/BaseSocketService'
import type { Session, Tab, TerminalTab, AIAssistantTab } from '../../types/session'

export interface WorkspaceState {
  sessions: Session[]
  activeSessionId: string | null
  isLoading: boolean
  lastSync: Date | null
  syncError: string | null
}

export interface TabCreationRequest {
  title: string
  type: 'terminal' | 'ai_assistant'
  assistantType?: 'code' | 'operations' | 'general'
  sessionId?: string
}

export interface TabCreationResponse {
  success: boolean
  tabId?: string
  error?: string
  tab?: Tab
}

/**
 * Workspace Socket Service
 * Replaces direct Socket.IO usage in WorkspaceManager.vue and TabManager.vue
 */
export class WorkspaceSocketService extends BaseSocketService {
  // Reactive workspace state
  private _workspaceState: Ref<WorkspaceState> = ref({
    sessions: [],
    activeSessionId: null,
    isLoading: false,
    lastSync: null,
    syncError: null
  })

  // Event callbacks
  private tabCreatedCallbacks: ((tab: Tab) => void)[] = []
  private tabUpdatedCallbacks: ((tabId: string, updates: Partial<Tab>) => void)[] = []
  private tabDeletedCallbacks: ((tabId: string) => void)[] = []
  private workspaceSyncedCallbacks: ((sessions: Session[]) => void)[] = []

  /**
   * Get event patterns this service handles
   */
  public getEventPatterns(): string[] {
    return [
      'workspace:*',
      'session:*',
      'tab:*'
    ]
  }

  /**
   * Get priority for event routing
   */
  protected getPriority(): number {
    return 10 // High priority for workspace events
  }

  /**
   * Handle incoming workspace events
   */
  protected handleEvent(eventName: string, data: any): void {
    switch (eventName) {
      case 'workspace:sync:response':
        this.handleWorkspaceSync(data)
        break
        
      case 'workspace:tab:created':
        this.handleTabCreated(data)
        break
        
      case 'workspace:tab:updated':
        this.handleTabUpdated(data)
        break
        
      case 'workspace:tab:deleted':
        this.handleTabDeleted(data)
        break
        
      case 'workspace:tab:error':
        this.handleTabError(data)
        break
        
      case 'workspace:session:created':
        this.handleSessionCreated(data)
        break
        
      case 'workspace:session:updated':
        this.handleSessionUpdated(data)
        break
        
      case 'workspace:session:deleted':
        this.handleSessionDeleted(data)
        break
        
      case 'workspace:error':
        this.handleWorkspaceError(data)
        break
        
      default:
        this.log('Unhandled workspace event:', eventName, data)
    }
  }

  /**
   * Initialize workspace - request current state from server
   */
  public async initializeWorkspace(): Promise<void> {
    if (!this.isConnected()) {
      throw new Error('Socket not connected')
    }

    this.updateWorkspaceState({ isLoading: true, syncError: null })
    
    try {
      this.log('Initializing workspace...')
      this.emit('workspace:sync:request')
      
      // Wait for sync response or timeout
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Workspace initialization timeout'))
        }, 10000)
        
        const unsubscribe = this.onWorkspaceSynced(() => {
          clearTimeout(timeout)
          unsubscribe()
          resolve()
        })
      })
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      this.updateWorkspaceState({ 
        isLoading: false, 
        syncError: errorMessage 
      })
      throw error
    }
  }

  /**
   * Create a new tab
   */
  public async createTab(request: TabCreationRequest): Promise<TabCreationResponse> {
    if (!this.isConnected()) {
      throw new Error('Socket not connected')
    }

    try {
      this.log('Creating tab:', request)
      
      // Use correlation for request-response
      const response = await this.emitWithResponse<TabCreationResponse>(
        'workspace:tab:create',
        'workspace:tab:created',
        request,
        15000 // 15 second timeout for tab creation
      )
      
      if (response.success && response.tab) {
        this.log('Tab created successfully:', response.tab.id)
        return response
      } else {
        throw new Error(response.error || 'Tab creation failed')
      }
      
    } catch (error) {
      this.error('Tab creation failed:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  /**
   * Update tab
   */
  public async updateTab(tabId: string, updates: Partial<Tab>): Promise<void> {
    if (!this.isConnected()) {
      throw new Error('Socket not connected')
    }

    this.emit('workspace:tab:update', {
      tabId,
      updates
    })
  }

  /**
   * Delete tab
   */
  public async deleteTab(tabId: string): Promise<void> {
    if (!this.isConnected()) {
      throw new Error('Socket not connected')
    }

    this.emit('workspace:tab:delete', { tabId })
  }

  /**
   * Set active tab
   */
  public setActiveTab(sessionId: string, tabId: string): void {
    if (!this.isConnected()) {
      this.warn('Socket not connected, cannot set active tab')
      return
    }

    this.emit('workspace:session:active_tab', {
      sessionId,
      tabId
    })
  }

  /**
   * Handle workspace sync response
   */
  private handleWorkspaceSync(data: { sessions: Session[] }): void {
    this.log('Workspace synced:', data.sessions.length, 'sessions')
    
    this.updateWorkspaceState({
      sessions: data.sessions,
      activeSessionId: data.sessions[0]?.id || null,
      isLoading: false,
      lastSync: new Date(),
      syncError: null
    })
    
    // Notify callbacks
    this.workspaceSyncedCallbacks.forEach(callback => {
      try {
        callback(data.sessions)
      } catch (error) {
        this.error('Error in workspace synced callback:', error)
      }
    })
  }

  /**
   * Handle tab created event
   */
  private handleTabCreated(data: { tab: Tab }): void {
    this.log('Tab created:', data.tab.id)
    
    // Add tab to appropriate session
    const sessions = [...this._workspaceState.value.sessions]
    const sessionIndex = sessions.findIndex(s => s.tabs.some(t => t.id === data.tab.id))
    
    if (sessionIndex === -1) {
      // Create new session if needed
      const newSession: Session = {
        id: `session-${Date.now()}`,
        name: 'New Session',
        tabs: [data.tab],
        activeTabId: data.tab.id
      }
      sessions.push(newSession)
    } else {
      // Add to existing session
      const existingTabIndex = sessions[sessionIndex].tabs.findIndex(t => t.id === data.tab.id)
      if (existingTabIndex === -1) {
        sessions[sessionIndex].tabs.push(data.tab)
      } else {
        sessions[sessionIndex].tabs[existingTabIndex] = data.tab
      }
    }
    
    this.updateWorkspaceState({ sessions })
    
    // Notify callbacks
    this.tabCreatedCallbacks.forEach(callback => {
      try {
        callback(data.tab)
      } catch (error) {
        this.error('Error in tab created callback:', error)
      }
    })
  }

  /**
   * Handle tab updated event
   */
  private handleTabUpdated(data: { tabId: string; updates: Partial<Tab> }): void {
    this.log('Tab updated:', data.tabId, data.updates)
    
    const sessions = [...this._workspaceState.value.sessions]
    let updated = false
    
    for (const session of sessions) {
      const tabIndex = session.tabs.findIndex(t => t.id === data.tabId)
      if (tabIndex !== -1) {
        session.tabs[tabIndex] = { ...session.tabs[tabIndex], ...data.updates } as Tab
        updated = true
        break
      }
    }
    
    if (updated) {
      this.updateWorkspaceState({ sessions })
      
      // Notify callbacks
      this.tabUpdatedCallbacks.forEach(callback => {
        try {
          callback(data.tabId, data.updates)
        } catch (error) {
          this.error('Error in tab updated callback:', error)
        }
      })
    }
  }

  /**
   * Handle tab deleted event
   */
  private handleTabDeleted(data: { tabId: string }): void {
    this.log('Tab deleted:', data.tabId)
    
    const sessions = [...this._workspaceState.value.sessions]
    let deleted = false
    
    for (const session of sessions) {
      const tabIndex = session.tabs.findIndex(t => t.id === data.tabId)
      if (tabIndex !== -1) {
        session.tabs.splice(tabIndex, 1)
        deleted = true
        break
      }
    }
    
    if (deleted) {
      this.updateWorkspaceState({ sessions })
      
      // Notify callbacks
      this.tabDeletedCallbacks.forEach(callback => {
        try {
          callback(data.tabId)
        } catch (error) {
          this.error('Error in tab deleted callback:', error)
        }
      })
    }
  }

  /**
   * Handle tab error
   */
  private handleTabError(data: { error: string; tabId?: string }): void {
    this.error('Tab error:', data.error, data.tabId)
    
    this.updateWorkspaceState({
      syncError: data.error
    })
  }

  /**
   * Handle session created
   */
  private handleSessionCreated(data: { session: Session }): void {
    this.log('Session created:', data.session.id)
    
    const sessions = [...this._workspaceState.value.sessions]
    const existingIndex = sessions.findIndex(s => s.id === data.session.id)
    
    if (existingIndex === -1) {
      sessions.push(data.session)
    } else {
      sessions[existingIndex] = data.session
    }
    
    this.updateWorkspaceState({ sessions })
  }

  /**
   * Handle session updated
   */
  private handleSessionUpdated(data: { sessionId: string; updates: Partial<Session> }): void {
    this.log('Session updated:', data.sessionId, data.updates)
    
    const sessions = [...this._workspaceState.value.sessions]
    const sessionIndex = sessions.findIndex(s => s.id === data.sessionId)
    
    if (sessionIndex !== -1) {
      sessions[sessionIndex] = { ...sessions[sessionIndex], ...data.updates }
      this.updateWorkspaceState({ sessions })
    }
  }

  /**
   * Handle session deleted
   */
  private handleSessionDeleted(data: { sessionId: string }): void {
    this.log('Session deleted:', data.sessionId)
    
    const sessions = this._workspaceState.value.sessions.filter(s => s.id !== data.sessionId)
    
    this.updateWorkspaceState({
      sessions,
      activeSessionId: this._workspaceState.value.activeSessionId === data.sessionId 
        ? (sessions[0]?.id || null) 
        : this._workspaceState.value.activeSessionId
    })
  }

  /**
   * Handle general workspace error
   */
  private handleWorkspaceError(data: { error: string }): void {
    this.error('Workspace error:', data.error)
    
    this.updateWorkspaceState({
      syncError: data.error,
      isLoading: false
    })
  }

  /**
   * Update workspace state
   */
  private updateWorkspaceState(updates: Partial<WorkspaceState>): void {
    Object.assign(this._workspaceState.value, updates)
  }

  /**
   * Get workspace state (reactive)
   */
  public getWorkspaceState(): Readonly<Ref<WorkspaceState>> {
    return this._workspaceState
  }

  /**
   * Get sessions
   */
  public getSessions(): Session[] {
    return this._workspaceState.value.sessions
  }

  /**
   * Get active session
   */
  public getActiveSession(): Session | null {
    const activeId = this._workspaceState.value.activeSessionId
    return activeId ? this._workspaceState.value.sessions.find(s => s.id === activeId) || null : null
  }

  /**
   * Event subscription methods
   */
  public onTabCreated(callback: (tab: Tab) => void): () => void {
    this.tabCreatedCallbacks.push(callback)
    return () => {
      const index = this.tabCreatedCallbacks.indexOf(callback)
      if (index !== -1) {
        this.tabCreatedCallbacks.splice(index, 1)
      }
    }
  }

  public onTabUpdated(callback: (tabId: string, updates: Partial<Tab>) => void): () => void {
    this.tabUpdatedCallbacks.push(callback)
    return () => {
      const index = this.tabUpdatedCallbacks.indexOf(callback)
      if (index !== -1) {
        this.tabUpdatedCallbacks.splice(index, 1)
      }
    }
  }

  public onTabDeleted(callback: (tabId: string) => void): () => void {
    this.tabDeletedCallbacks.push(callback)
    return () => {
      const index = this.tabDeletedCallbacks.indexOf(callback)
      if (index !== -1) {
        this.tabDeletedCallbacks.splice(index, 1)
      }
    }
  }

  public onWorkspaceSynced(callback: (sessions: Session[]) => void): () => void {
    this.workspaceSyncedCallbacks.push(callback)
    return () => {
      const index = this.workspaceSyncedCallbacks.indexOf(callback)
      if (index !== -1) {
        this.workspaceSyncedCallbacks.splice(index, 1)
      }
    }
  }

  /**
   * Called when service is destroyed
   */
  protected onDestroy(): void {
    // Clear all callbacks
    this.tabCreatedCallbacks = []
    this.tabUpdatedCallbacks = []
    this.tabDeletedCallbacks = []
    this.workspaceSyncedCallbacks = []
  }
}

// Export singleton instance
let workspaceServiceInstance: WorkspaceSocketService | null = null

export const getWorkspaceService = (): WorkspaceSocketService => {
  if (!workspaceServiceInstance) {
    workspaceServiceInstance = new WorkspaceSocketService()
  }
  return workspaceServiceInstance
}

export default WorkspaceSocketService