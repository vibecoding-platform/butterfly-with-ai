/**
 * Workspace synchronization composable for multi-window support
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { getWorkspaceSocketService, type WorkspaceState, type UIState } from '@/services/WorkspaceSocketService'
import type { Tab, TerminalPane } from '@/types/session'

export function useWorkspaceSync() {
  const workspaceService = getWorkspaceSocketService()
  
  // Reactive state
  const tabs = ref<Tab[]>([])
  const activeTabId = ref<string | null>(null)
  const uiState = ref<UIState>({
    activeTabId: undefined,
    panelWidth: 320,
    isPanelVisible: true,
    panelPosition: { x: 20, y: 60 },
    lastUpdated: new Date().toISOString()
  })
  const connectedClients = ref(0)
  const isConnected = ref(false)
  const isInitialized = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const activeTab = computed(() => 
    tabs.value.find(tab => tab.id === activeTabId.value) || null
  )

  const hasMultipleTabs = computed(() => tabs.value.length > 1)

  // Initialize workspace connection
  const connect = async (url?: string) => {
    try {
      await workspaceService.connect(url)
      isConnected.value = true
      setupEventListeners()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Connection failed'
      console.error('Failed to connect to workspace service:', err)
    }
  }

  // Disconnect from workspace
  const disconnect = () => {
    workspaceService.disconnect()
    isConnected.value = false
    isInitialized.value = false
  }

  // Setup event listeners
  const setupEventListeners = () => {
    // Workspace initialization
    workspaceService.on('workspace:initialized', (data: WorkspaceState) => {
      tabs.value = data.tabs
      uiState.value = data.uiState
      activeTabId.value = data.uiState.activeTabId || null
      connectedClients.value = data.connectedClients
      isInitialized.value = true
      error.value = null
    })

    // Tab events
    workspaceService.on('workspace:tab_created', (data: { tab: Tab }) => {
      tabs.value.push(data.tab)
    })

    workspaceService.on('workspace:tab_switched', (data: { tabId: string; uiState: UIState }) => {
      activeTabId.value = data.tabId
      uiState.value = data.uiState
    })

    workspaceService.on('workspace:tab_closed', (data: { tabId: string; uiState: UIState }) => {
      tabs.value = tabs.value.filter(tab => tab.id !== data.tabId)
      uiState.value = data.uiState
      activeTabId.value = data.uiState.activeTabId || null
    })

    // Pane events
    workspaceService.on('workspace:pane_created', (data: { tabId: string; pane: TerminalPane; direction: string }) => {
      const tab = tabs.value.find(t => t.id === data.tabId)
      if (tab && 'panes' in tab) {
        tab.panes.push(data.pane)
        tab.activePaneId = data.pane.id
        
        // Update source pane position (this should come from server, but for safety)
        if (tab.panes.length > 1) {
          const sourcePanes = tab.panes.filter(p => p.id !== data.pane.id)
          sourcePanes.forEach(pane => {
            pane.isActive = false
          })
        }
      }
    })

    workspaceService.on('workspace:pane_closed', (data: { tabId: string; paneId: string; tab: Tab }) => {
      const tabIndex = tabs.value.findIndex(t => t.id === data.tabId)
      if (tabIndex > -1 && data.tab) {
        tabs.value[tabIndex] = data.tab
      }
    })

    // UI state events
    workspaceService.on('workspace:ui_updated', (data: { uiState: UIState; updates: any }) => {
      uiState.value = data.uiState
      
      // Update local activeTabId if it changed
      if (data.uiState.activeTabId !== undefined) {
        activeTabId.value = data.uiState.activeTabId
      }
    })

    // Sync events
    workspaceService.on('workspace:synced', (data: WorkspaceState) => {
      tabs.value = data.tabs
      uiState.value = data.uiState
      activeTabId.value = data.uiState.activeTabId || null
      connectedClients.value = data.connectedClients
    })

    // Error handling
    workspaceService.on('workspace:error', (data: { error: string }) => {
      error.value = data.error
    })
  }

  // Tab operations
  const createTab = async (title?: string, type: string = 'terminal') => {
    try {
      await workspaceService.createTab(title, type)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create tab'
    }
  }

  const switchTab = async (tabId: string) => {
    try {
      await workspaceService.switchTab(tabId)
      // Optimistic update for immediate feedback
      activeTabId.value = tabId
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to switch tab'
    }
  }

  const closeTab = async (tabId: string) => {
    try {
      await workspaceService.closeTab(tabId)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to close tab'
    }
  }

  // Pane operations
  const splitPane = async (tabId: string, paneId: string, direction: 'horizontal' | 'vertical' = 'horizontal') => {
    try {
      await workspaceService.splitPane(tabId, paneId, direction)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to split pane'
    }
  }

  const closePane = async (tabId: string, paneId: string) => {
    try {
      await workspaceService.closePane(tabId, paneId)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to close pane'
    }
  }

  // UI state operations
  const updateUIState = async (updates: Partial<UIState>) => {
    try {
      // Optimistic update for immediate feedback
      Object.assign(uiState.value, updates)
      
      await workspaceService.updateUIState(updates)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update UI state'
    }
  }

  // Request full sync
  const requestSync = async () => {
    try {
      await workspaceService.requestSync()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to sync workspace'
    }
  }

  // Debounced UI state sync
  let uiSyncTimeout: ReturnType<typeof setTimeout> | null = null
  const syncUIStateDebounced = (updates: Partial<UIState>) => {
    if (uiSyncTimeout) {
      clearTimeout(uiSyncTimeout)
    }
    
    uiSyncTimeout = setTimeout(() => {
      updateUIState(updates)
    }, 100) // 100ms debounce
  }

  // Watch for local UI changes that should be synced
  watch(() => uiState.value.panelWidth, (newWidth) => {
    if (isInitialized.value) {
      syncUIStateDebounced({ panelWidth: newWidth })
    }
  })

  watch(() => uiState.value.isPanelVisible, (newVisible) => {
    if (isInitialized.value) {
      syncUIStateDebounced({ isPanelVisible: newVisible })
    }
  })

  watch(() => uiState.value.panelPosition, (newPosition) => {
    if (isInitialized.value) {
      syncUIStateDebounced({ panelPosition: newPosition })
    }
  }, { deep: true })

  // Lifecycle hooks
  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    if (uiSyncTimeout) {
      clearTimeout(uiSyncTimeout)
    }
    disconnect()
  })

  return {
    // State
    tabs,
    activeTabId,
    activeTab,
    uiState,
    connectedClients,
    isConnected,
    isInitialized,
    error,
    hasMultipleTabs,

    // Actions
    connect,
    disconnect,
    createTab,
    switchTab,
    closeTab,
    splitPane,
    closePane,
    updateUIState,
    requestSync,

    // Utilities
    clearError: () => { error.value = null }
  }
}