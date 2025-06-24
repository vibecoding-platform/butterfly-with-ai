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
      
      <!-- Regular Terminal Tab Button -->
      <button class="new-tab-btn terminal-tab-btn" @click="createTerminalTab" title="新しいターミナルタブ">
        +
      </button>
      
      <!-- Spacer for right alignment -->
      <div class="tab-spacer"></div>
      
      <!-- AI Agent Tab Button (Right Aligned) -->
      <div class="ai-agent-tab-container">
        <button 
          class="new-tab-btn ai-agent-tab-btn" 
          @click="createDevelopmentAI"
          @contextmenu.prevent="showAITypeSelector"
          @mousedown="startLongPress"
          @mouseup="cancelLongPress"
          @mouseleave="cancelLongPress"
          title="開発AI (右クリック: AIタイプ選択)"
        >
          🤖
        </button>
        <div class="ai-agent-tooltip">
          <h4>AIエージェントタブを作成</h4>
          <p>自動化タスクを実行するAIエージェント環境</p>
          <ul>
            <li>• <strong>左クリック:</strong> 開発AI (デフォルト)</li>
            <li>• <strong>右クリック:</strong> 開発AI/運用AI選択</li>
          </ul>
          <div class="ai-types">
            <div class="ai-type">
              <strong>Coding AI:</strong> コード解析・テスト・ビルド・進捗可視化
            </div>
            <div class="ai-type">
              <strong>Operation AI:</strong> 手順書読込・半自動実行・進捗追跡
            </div>
          </div>
        </div>
      </div>
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

    <!-- AI Type Selector Dialog -->
    <div v-if="showAITypeDialog" class="ai-type-overlay" @click="closeAITypeDialog">
      <div class="ai-type-modal" @click.stop>
        <h3>AIエージェントタイプ選択</h3>
        <div class="ai-type-options">
          <button class="ai-type-option development" @click="createDevelopmentAI">
            <div class="ai-type-icon">💻</div>
            <div class="ai-type-content">
              <h4>Coding AI</h4>
              <p>コード解析・テスト・ビルド・進捗可視化AI</p>
            </div>
          </button>
          <button class="ai-type-option operations" @click="createOperationsAI">
            <div class="ai-type-icon">📋</div>
            <div class="ai-type-content">
              <h4>Operation AI</h4>
              <p>手順書読込・半自動実行・進捗追跡AI</p>
            </div>
          </button>
        </div>
        <button class="ai-type-cancel" @click="closeAITypeDialog">キャンセル</button>
      </div>
    </div>

    <!-- AI Agent Tab Selector Dialog -->
    <TabTypeSelector
      v-if="showAIAgentSelector"
      @create="handleAIAgentCreate"
      @cancel="handleAIAgentCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import io from 'socket.io-client'
import TerminalPaneManager from './TerminalPaneManager.vue'
import TabTypeSelector, { type TabTypeConfig } from './TabTypeSelector.vue'

interface Tab {
  id: string
  title: string
  type: 'terminal' | 'ai_assistant' | 'ai_agent'
  isActive: boolean
  isShared: boolean
  connectedUsers: any[]
  panes: Pane[]
  activePaneId: string | null
  layout: string
  agentConfig?: any  // AI Agent specific configuration
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

// AI Agent state
const showAIAgentSelector = ref(false)
const showAITypeDialog = ref(false)

// Long press handling
let longPressTimer: number | null = null

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

const createTerminalTab = () => {
  if (socket) {
    socket.emit('workspace:tab:create', {
      title: `Terminal ${tabs.value.length + 1}`,
      type: 'terminal'
    })
  }
}

const showAIAgentDialog = () => {
  showAIAgentSelector.value = true
}

const createDevelopmentAI = () => {
  if (socket) {
    socket.emit('workspace:tab:create', {
      title: `Coding AI ${tabs.value.length + 1}`,
      type: 'ai_agent',
      agentConfig: {
        type: 'build',
        name: `Coding AI ${tabs.value.length + 1}`,
        task: 'Code analysis, testing, build automation, progress visualization and development goal tracking',
        autonomy: 'semi'
      }
    })
  }
  closeAITypeDialog()
}

const createOperationsAI = () => {
  if (socket) {
    socket.emit('workspace:tab:create', {
      title: `Operation AI ${tabs.value.length + 1}`,
      type: 'ai_agent',
      agentConfig: {
        type: 'operations',
        name: `Operation AI ${tabs.value.length + 1}`,
        task: 'Manual reading, semi-automated execution, progress tracking and operational goal management',
        autonomy: 'semi'
      }
    })
  }
  closeAITypeDialog()
}

const showAITypeSelector = () => {
  showAITypeDialog.value = true
}

const closeAITypeDialog = () => {
  showAITypeDialog.value = false
}

const startLongPress = () => {
  longPressTimer = window.setTimeout(() => {
    showAITypeSelector()
  }, 500) // 500ms long press
}

const cancelLongPress = () => {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
}

const handleAIAgentCreate = (config: TabTypeConfig) => {
  if (socket && config.type === 'ai_agent' && config.agentConfig) {
    socket.emit('workspace:tab:create', {
      title: config.agentConfig.name || `AI Agent ${tabs.value.length + 1}`,
      type: 'ai_agent',
      agentConfig: config.agentConfig
    })
  }
  showAIAgentSelector.value = false
}

const handleAIAgentCancel = () => {
  showAIAgentSelector.value = false
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

/* Tab Spacer for right alignment */
.tab-spacer {
  flex: 1;
}

/* AI Agent Tab Button Styling */
.ai-agent-tab-btn {
  background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  font-size: 16px;
  min-width: 44px;
}

.ai-agent-tab-btn:hover {
  background: linear-gradient(135deg, #f57c00 0%, #ef6c00 100%);
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(255, 152, 0, 0.3);
}

/* Terminal Tab Button Styling */
.terminal-tab-btn:hover {
  background-color: #3d3d3d;
  color: #66bb6a;
  border-radius: 4px;
}

/* AI Agent Tab Container and Tooltip */
.ai-agent-tab-container {
  position: relative;
  display: inline-block;
}

.ai-agent-tooltip {
  position: absolute;
  bottom: 60px;
  right: 0;
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  width: 280px;
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transform: translateY(10px);
  transition: all 0.3s ease;
  backdrop-filter: blur(8px);
  font-size: 13px;
  line-height: 1.4;
}

.ai-agent-tab-container:hover .ai-agent-tooltip {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.ai-agent-tooltip h4 {
  margin: 0 0 8px 0;
  color: #1f2937;
  font-size: 14px;
  font-weight: 600;
}

.ai-agent-tooltip p {
  margin: 0 0 12px 0;
  color: #6b7280;
  font-size: 12px;
}

.ai-agent-tooltip ul {
  margin: 0 0 12px 0;
  padding: 0;
  list-style: none;
}

.ai-agent-tooltip li {
  color: #374151;
  font-size: 11px;
  margin-bottom: 4px;
  padding-left: 8px;
}

.ai-agent-tooltip small {
  color: #9ca3af;
  font-size: 10px;
  font-style: italic;
}

.ai-types {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.ai-type {
  font-size: 11px;
  color: #374151;
  margin-bottom: 6px;
  line-height: 1.3;
}

/* Arrow for tooltip */
.ai-agent-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  right: 20px;
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid #ffffff;
}

.ai-agent-tooltip::before {
  content: '';
  position: absolute;
  top: 100%;
  right: 19px;
  width: 0;
  height: 0;
  border-left: 9px solid transparent;
  border-right: 9px solid transparent;
  border-top: 9px solid #e0e0e0;
}

/* AI Type Selection Dialog */
.ai-type-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  backdrop-filter: blur(4px);
}

.ai-type-modal {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  max-width: 400px;
  width: 90%;
  animation: modalSlideIn 0.2s ease-out;
}

.ai-type-modal h3 {
  margin: 0 0 20px 0;
  color: #1f2937;
  font-size: 18px;
  font-weight: 600;
  text-align: center;
}

.ai-type-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.ai-type-option {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
  text-align: left;
}

.ai-type-option:hover {
  border-color: #3b82f6;
  background: #f8fafc;
}

.ai-type-option.development {
  border-color: #10b981;
}

.ai-type-option.development:hover {
  border-color: #059669;
  background: #f0fdf4;
}

.ai-type-option.operations {
  border-color: #f59e0b;
}

.ai-type-option.operations:hover {
  border-color: #d97706;
  background: #fffbeb;
}

.ai-type-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.ai-type-content h4 {
  margin: 0 0 4px 0;
  color: #1f2937;
  font-size: 16px;
  font-weight: 600;
}

.ai-type-content p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.4;
}

.ai-type-cancel {
  width: 100%;
  padding: 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #374151;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
}

.ai-type-cancel:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}
</style>