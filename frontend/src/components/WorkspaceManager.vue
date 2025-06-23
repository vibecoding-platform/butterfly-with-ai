<template>
  <div class="workspace-manager">
    <!-- Tab Management -->
    <div class="workspace-tabs">
      <div 
        v-for="tab in tabs" 
        :key="tab.id"
        class="workspace-tab"
        :class="{ 
          'active': tab.id === activeTabId,
          'has-panes': tab.panes && tab.panes.length > 1
        }"
        @click="switchTab(tab.id)"
      >
        <div class="tab-info">
          <span class="tab-name">{{ tab.title }}</span>
          <span class="pane-count" v-if="tab.panes && tab.panes.length > 1">
            {{ tab.panes.length }}
          </span>
        </div>
        <button 
          class="close-tab"
          @click.stop="closeTab(tab.id)"
          v-if="tabs.length > 1"
        >
          ×
        </button>
      </div>
      
      <!-- New Tab Button -->
      <button class="new-tab-btn" @click="createTab">
        +
      </button>
    </div>

    <!-- Workspace Sync Loading -->
    <div v-if="workspaceSyncInProgress" class="workspace-loading">
      <div class="loading-container">
        <div class="loading-spinner"></div>
        <div class="loading-text">
          <h3>Initializing Workspace</h3>
          <p>Loading tabs and terminals...</p>
          <div class="loading-steps">
            <div class="step" :class="{ completed: syncStep >= 1, active: syncStep === 0 }">
              {{ syncStep >= 1 ? '✓' : '⏳' }} Connecting to server
            </div>
            <div class="step" :class="{ completed: syncStep >= 2, active: syncStep === 1 }">
              {{ syncStep >= 2 ? '✓' : syncStep === 1 ? '⏳' : '⭕' }} Loading workspace state
            </div>
            <div class="step" :class="{ completed: syncStep >= 3, active: syncStep === 2 }">
              {{ syncStep >= 3 ? '✓' : syncStep === 2 ? '⏳' : '⭕' }} Restoring tabs
            </div>
            <div class="step" :class="{ completed: syncStep >= 4, active: syncStep === 3 }">
              {{ syncStep >= 4 ? '✓' : syncStep === 3 ? '⏳' : '⭕' }} Loading terminals
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Active Tab Content -->
    <div v-else-if="workspaceSyncCompleted && activeTab" class="tab-content">
      <div class="tab-layout">
        <!-- Main Pane Area -->
        <div class="pane-area">
          <TerminalPaneManager 
            v-if="activeTab && activeTab.type === 'terminal'"
            :terminalTab="activeTab as any" 
            :session-id="'workspace-session'"
            :tab-id="activeTab.id"
          />
        </div>
      </div>
    </div>
    
    <!-- No Tab State -->
    <div v-else-if="workspaceSyncCompleted && !activeTab" class="no-tabs">
      <div class="welcome-message">
        <h3>Welcome to AetherTerm</h3>
        <p>Create a new tab to get started</p>
        <button class="create-tab-btn" @click="createTab">
          Create Tab
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import io from 'socket.io-client'
import TerminalPaneManager from './TerminalPaneManager.vue'

interface Tab {
  id: string
  title: string
  type: 'terminal' | 'ai_assistant'
  isActive: boolean
  isShared: boolean
  connectedUsers: any[]
  panes: Pane[]
  activePaneId: string | null
  layout: string
}

interface Pane {
  id: string
  terminalId: string
  title: string
  shellType: string
  workingDirectory: string
  position: any
  isActive: boolean
}

interface UIState {
  activeTabId: string | null
  panelWidth: number
  isPanelVisible: boolean
  panelPosition: { x: number; y: number }
  lastUpdated: string
}

// Reactive state
const tabs = ref<Tab[]>([])
const activeTabId = ref<string | null>(null)
const uiState = ref<UIState>({
  activeTabId: null,
  panelWidth: 320,
  isPanelVisible: true,
  panelPosition: { x: 20, y: 60 },
  lastUpdated: ''
})
const connectedClients = ref(0)

// Workspace sync state
const workspaceSyncInProgress = ref(false)
const workspaceSyncCompleted = ref(false)
const syncStep = ref(0) // 0: connecting, 1: loading, 2: restoring, 3: terminals

// UI controls bound to state
const panelWidth = ref(320)
const isPanelVisible = ref(true)

// Computed
const activeTab = computed(() => {
  return tabs.value.find(tab => tab.id === activeTabId.value) || null
})

// Watch activeTabId changes
watch(activeTabId, (newTabId, oldTabId) => {
  console.log('🔄 activeTabId changed:', { from: oldTabId, to: newTabId })
  console.log('🔄 activeTab computed:', activeTab.value?.title)
})

// Socket.IO connection
let socket: any = null

const initializeWorkspace = async () => {
  try {
    workspaceSyncInProgress.value = true
    syncStep.value = 0
    console.log('[WORKSPACE] WorkspaceManager: Starting workspace initialization...')
    
    // Step 1: Connect to socket
    console.log('[WORKSPACE] WorkspaceManager: Connecting to AgentServer...')
    socket = io('http://localhost:57575')
    
    socket.on('connect', () => {
      console.log('🔌 Connected to workspace')
      syncStep.value = 1
      socket.emit('workspace:initialize', {
        environ: {
          REMOTE_ADDR: '127.0.0.1',
          HTTP_USER_AGENT: 'Workspace Manager UI'
        }
      })
    })
  } catch (error) {
    console.error('WorkspaceManager: Failed to initialize workspace:', error)
    workspaceSyncCompleted.value = true
    workspaceSyncInProgress.value = false
  }

  socket.on('workspace:initialized', async (data: any) => {
    console.log('✅ Workspace initialized:', data)
    syncStep.value = 2
    
    tabs.value = data.tabs || []
    connectedClients.value = data.connectedClients || 0
    
    // Step 3: Restore tabs
    console.log(`[WORKSPACE] WorkspaceManager: Workspace sync completed. Found ${tabs.value.length} existing tabs`)
    syncStep.value = 3
    
    // Sync UI state
    if (data.uiState) {
      uiState.value = data.uiState
      panelWidth.value = data.uiState.panelWidth
      isPanelVisible.value = data.uiState.isPanelVisible
    }
    
    // Step 4: Loading terminals / final setup
    syncStep.value = 4
    
    // Small delay to show final step
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // Mark sync as completed
    workspaceSyncCompleted.value = true
    workspaceSyncInProgress.value = false
    
    // Set default active tab if none selected
    if (!activeTabId.value && tabs.value.length > 0) {
      activeTabId.value = tabs.value[0].id
    } else if (tabs.value.length === 0) {
      console.log('[WORKSPACE] WorkspaceManager: No existing tabs found, creating initial tab...')
      createTab()
    }
  })

  socket.on('workspace:tab_created', (data: any) => {
    console.log('📝 Tab created:', data.tab)
    // Check if tab already exists to prevent duplicates
    const existingTab = tabs.value.find(tab => tab.id === data.tab.id)
    if (!existingTab) {
      tabs.value.push(data.tab)
    } else {
      console.log('⚠️ Tab already exists, skipping duplicate:', data.tab.id)
    }
  })

  socket.on('workspace:tab_switched', (data: any) => {
    console.log('🔄 Tab switched:', data)
    console.log('🔄 Current activeTabId before:', activeTabId.value)
    console.log('🔄 New tabId from server:', data.tabId)
    console.log('🔄 Available tabs:', tabs.value.map(t => ({ id: t.id, title: t.title })))
    
    activeTabId.value = data.tabId
    
    console.log('🔄 Current activeTabId after:', activeTabId.value)
    
    if (data.uiState) {
      uiState.value = data.uiState
    }
  })

  socket.on('workspace:ui_updated', (data: any) => {
    console.log('🎛️ UI updated:', data)
    if (data.panelWidth !== undefined) {
      panelWidth.value = data.panelWidth
      uiState.value.panelWidth = data.panelWidth
    }
    if (data.isPanelVisible !== undefined) {
      isPanelVisible.value = data.isPanelVisible  
      uiState.value.isPanelVisible = data.isPanelVisible
    }
  })

  socket.on('workspace:client_connected', (data: any) => {
    console.log('👤 Client connected:', data)
    connectedClients.value = data.client_count
  })

  socket.on('workspace:client_disconnected', (data: any) => {
    console.log('👤 Client disconnected:', data)  
    connectedClients.value = data.client_count
  })

  socket.on('workspace:error', (data: any) => {
    console.error('❌ Workspace error:', data)
  })
}

// Actions
const createTab = () => {
  if (socket) {
    socket.emit('workspace:tab:create', {
      title: `Tab ${tabs.value.length + 1}`,
      type: 'terminal'
    })
  }
}

const switchTab = (tabId: string) => {
  console.log('👆 User clicked tab:', tabId)
  console.log('👆 Current activeTabId before click:', activeTabId.value)
  
  // Update local UI immediately
  activeTabId.value = tabId
  
  // Notify server but don't wait for response (server won't broadcast)
  if (socket) {
    console.log('👆 Sending workspace:tab:switch event')
    socket.emit('workspace:tab:switch', { tabId })
  } else {
    console.log('❌ Socket not available')
  }
}

const closeTab = (tabId: string) => {
  if (socket) {
    socket.emit('workspace:tab:close', { tabId })
  }
}

const splitPane = (paneId: string) => {
  if (socket && activeTab.value) {
    socket.emit('workspace:pane:split', {
      tabId: activeTab.value.id,
      paneId,
      direction: 'horizontal'
    })
  }
}

const updateUIState = () => {
  if (socket) {
    socket.emit('workspace:ui:update', {
      panelWidth: panelWidth.value,
      isPanelVisible: isPanelVisible.value
    })
  }
}

// Lifecycle
onMounted(() => {
  initializeWorkspace()
})

onUnmounted(() => {
  if (socket) {
    socket.disconnect()
  }
})
</script>

<style scoped>
.workspace-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #1e1e1e;
}

.workspace-tabs {
  display: flex;
  background-color: #2d2d2d;
  border-bottom: 1px solid #444;
  overflow-x: auto;
  flex-shrink: 0;
}

.workspace-tab {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-right: 1px solid #444;
  cursor: pointer;
  background-color: #2d2d2d;
  color: #ccc;
  transition: all 0.2s ease;
  min-width: 120px;
  max-width: 200px;
}

.workspace-tab:hover {
  background-color: #3d3d3d;
  color: #fff;
}

.workspace-tab.active {
  background-color: #4caf50;
  color: white;
}

.workspace-tab.has-panes {
  border-top: 2px solid #2196f3;
}

.tab-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
}

.tab-name {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pane-count {
  background-color: rgba(33, 150, 243, 0.8);
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 12px;
  font-weight: bold;
  min-width: 18px;
  text-align: center;
}

.close-tab {
  background: none;
  border: none;
  color: inherit;
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
  margin-left: 4px;
  opacity: 0.6;
  transition: opacity 0.2s ease;
}

.close-tab:hover {
  opacity: 1;
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.new-tab-btn {
  background: none;
  border: none;
  color: #4caf50;
  font-size: 20px;
  cursor: pointer;
  padding: 8px 12px;
  transition: all 0.2s ease;
  min-width: 40px;
}

.new-tab-btn:hover {
  background-color: #3d3d3d;
  color: #66bb6a;
}

.tab-content {
  flex: 1;
  overflow: hidden;
}

.tab-layout {
  display: flex;
  height: 100%;
  position: relative;
}

.pane-area {
  flex: 1;
  overflow: hidden;
}

.no-tabs {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #1e1e1e;
}

.welcome-message {
  text-align: center;
  color: #ccc;
}

.welcome-message h3 {
  color: #4caf50;
  margin-bottom: 8px;
  font-size: 20px;
}

.welcome-message p {
  margin-bottom: 20px;
  font-size: 14px;
}

.create-tab-btn {
  background-color: #4caf50;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background-color 0.2s ease;
}

.create-tab-btn:hover {
  background-color: #45a049;
}

/* Workspace Loading Animation */
.workspace-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #1e1e1e;
  padding: 40px;
}

.loading-container {
  text-align: center;
  max-width: 400px;
}

.loading-spinner {
  width: 60px;
  height: 60px;
  border: 4px solid #444;
  border-top: 4px solid #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 24px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text h3 {
  color: #4caf50;
  margin-bottom: 8px;
  font-size: 20px;
  font-weight: 600;
}

.loading-text p {
  color: #ccc;
  margin-bottom: 24px;
  font-size: 14px;
}

.loading-steps {
  text-align: left;
  max-width: 280px;
  margin: 0 auto;
}

.step {
  color: #666;
  font-size: 13px;
  padding: 4px 0;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: color 0.3s ease;
}

.step.completed {
  color: #4caf50;
}

.step.active {
  color: #2196f3;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* Scrollbar for workspace tabs */
.workspace-tabs::-webkit-scrollbar {
  height: 3px;
}

.workspace-tabs::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.workspace-tabs::-webkit-scrollbar-thumb {
  background: #666;
  border-radius: 3px;
}

.workspace-tabs::-webkit-scrollbar-thumb:hover {
  background: #888;
}
</style>