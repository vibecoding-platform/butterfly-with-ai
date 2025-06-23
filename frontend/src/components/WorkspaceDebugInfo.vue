<template>
  <div class="workspace-debug">
    <div class="debug-header">
      <h3>🔍 Debug Information</h3>
      <div class="connection-status">
        <span :class="connectionStatusClass">
          {{ connectionStatus }}
        </span>
        <span class="client-count">
          Clients: {{ connectedClients }}
        </span>
      </div>
    </div>

    <!-- Workspace State -->
    <div class="debug-section">
      <h4>📊 Workspace State</h4>
      <div class="info-grid">
        <div class="info-item">
          <label>Total Tabs:</label>
          <span>{{ tabs.length }}</span>
        </div>
        <div class="info-item">
          <label>Active Tab:</label>
          <span>{{ activeTabId || 'None' }}</span>
        </div>
        <div class="info-item">
          <label>Total Panes:</label>
          <span>{{ totalPanes }}</span>
        </div>
        <div class="info-item">
          <label>Last Updated:</label>
          <span>{{ lastUpdated }}</span>
        </div>
      </div>
    </div>

    <!-- UI State -->
    <div class="debug-section">
      <h4>🎛️ UI State</h4>
      <div class="info-grid">
        <div class="info-item">
          <label>Panel Width:</label>
          <span>{{ uiState.panelWidth }}px</span>
        </div>
        <div class="info-item">
          <label>Panel Visible:</label>
          <span>{{ uiState.isPanelVisible ? 'Yes' : 'No' }}</span>
        </div>
        <div class="info-item">
          <label>Panel Position:</label>
          <span>{{ uiState.panelPosition?.x }}, {{ uiState.panelPosition?.y }}</span>
        </div>
      </div>
    </div>

    <!-- Tabs Details -->
    <div class="debug-section">
      <h4>📋 Tabs Details</h4>
      <div class="tabs-list">
        <div 
          v-for="tab in tabs" 
          :key="tab.id"
          class="tab-detail"
          :class="{ 'active': tab.id === activeTabId }"
        >
          <div class="tab-header">
            <span class="tab-title">{{ tab.title }}</span>
            <span class="tab-id">{{ tab.id }}</span>
          </div>
          <div class="tab-info">
            <div class="info-row">
              <label>Type:</label>
              <span>{{ tab.type }}</span>
            </div>
            <div class="info-row">
              <label>Panes:</label>
              <span>{{ tab.panes?.length || 0 }}</span>
            </div>
            <div class="info-row">
              <label>Active Pane:</label>
              <span>{{ tab.activePaneId || 'None' }}</span>
            </div>
            <div class="info-row">
              <label>Layout:</label>
              <span>{{ tab.layout || 'default' }}</span>
            </div>
          </div>
          
          <!-- Panes in this tab -->
          <div v-if="tab.panes && tab.panes.length > 0" class="panes-list">
            <h5>Panes:</h5>
            <div 
              v-for="pane in tab.panes" 
              :key="pane.id"
              class="pane-detail"
              :class="{ 'active': pane.id === tab.activePaneId }"
            >
              <div class="pane-info">
                <label>ID:</label>
                <span>{{ pane.id }}</span>
              </div>
              <div class="pane-info">
                <label>Terminal:</label>
                <span>{{ pane.terminalId }}</span>
              </div>
              <div class="pane-info">
                <label>Shell:</label>
                <span>{{ pane.shellType }}</span>
              </div>
              <div class="pane-info">
                <label>Directory:</label>
                <span>{{ pane.workingDirectory }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Raw JSON Data -->
    <div class="debug-section">
      <h4>📄 Raw JSON Data</h4>
      <details class="json-details">
        <summary>Click to expand full state</summary>
        <pre class="json-display">{{ JSON.stringify({ 
          tabs, 
          activeTabId, 
          uiState, 
          connectedClients,
          timestamp: new Date().toISOString()
        }, null, 2) }}</pre>
      </details>
    </div>

    <!-- Live Events Log -->
    <div class="debug-section">
      <h4>📡 Live Events Log</h4>
      <div class="events-controls">
        <button @click="clearEventLog" class="clear-btn">Clear Log</button>
        <label>
          <input v-model="autoScroll" type="checkbox" />
          Auto Scroll
        </label>
      </div>
      <div class="events-log" ref="eventsLogRef">
        <div 
          v-for="event in eventLog" 
          :key="event.id"
          class="event-entry"
          :class="event.type"
        >
          <span class="event-time">{{ event.timestamp }}</span>
          <span class="event-type">{{ event.type }}</span>
          <span class="event-data">{{ event.data }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import io from 'socket.io-client'

// Types
interface Tab {
  id: string
  title: string
  type: string
  isActive: boolean
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

interface EventLogEntry {
  id: number
  timestamp: string
  type: string
  data: string
}

// State
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
const eventLog = ref<EventLogEntry[]>([])
const autoScroll = ref(true)
const eventsLogRef = ref<HTMLElement>()

let socket: any = null
let eventCounter = 0

// Computed
const totalPanes = computed(() => {
  return tabs.value.reduce((total, tab) => total + (tab.panes?.length || 0), 0)
})

const lastUpdated = computed(() => {
  if (uiState.value.lastUpdated) {
    return new Date(uiState.value.lastUpdated).toLocaleTimeString()
  }
  return 'Never'
})

const connectionStatus = computed(() => {
  return socket?.connected ? 'Connected' : 'Disconnected'
})

const connectionStatusClass = computed(() => {
  return socket?.connected ? 'connected' : 'disconnected'
})

// Event logging
const addEventLog = (type: string, data: any) => {
  const entry: EventLogEntry = {
    id: ++eventCounter,
    timestamp: new Date().toLocaleTimeString(),
    type,
    data: typeof data === 'string' ? data : JSON.stringify(data)
  }
  
  eventLog.value.push(entry)
  
  // Limit log size
  if (eventLog.value.length > 100) {
    eventLog.value.shift()
  }
  
  // Auto scroll if enabled
  if (autoScroll.value) {
    nextTick(() => {
      if (eventsLogRef.value) {
        eventsLogRef.value.scrollTop = eventsLogRef.value.scrollHeight
      }
    })
  }
}

const clearEventLog = () => {
  eventLog.value = []
  eventCounter = 0
}

// Socket connection
const initializeSocket = () => {
  socket = io('http://localhost:57575')
  
  socket.on('connect', () => {
    addEventLog('connect', 'Connected to workspace')
    socket.emit('workspace:initialize', {
      environ: {
        REMOTE_ADDR: '127.0.0.1',
        HTTP_USER_AGENT: 'Debug Panel'
      }
    })
  })

  socket.on('disconnect', () => {
    addEventLog('disconnect', 'Disconnected from workspace')
  })

  socket.on('workspace:initialized', (data: any) => {
    addEventLog('workspace:initialized', `Received workspace state with ${data.tabs?.length || 0} tabs`)
    tabs.value = data.tabs || []
    connectedClients.value = data.connectedClients || 0
    
    if (data.uiState) {
      uiState.value = data.uiState
    }
    
    // Set default active tab if none selected
    if (!activeTabId.value && tabs.value.length > 0) {
      activeTabId.value = tabs.value[0].id
    }
  })

  socket.on('workspace:tab_created', (data: any) => {
    addEventLog('tab_created', `New tab: ${data.tab.title} (${data.tab.id})`)
    const existingTab = tabs.value.find(tab => tab.id === data.tab.id)
    if (!existingTab) {
      tabs.value.push(data.tab)
    }
  })

  socket.on('workspace:tab_switched', (data: any) => {
    addEventLog('tab_switched', `Switched to tab: ${data.tabId}`)
    // Note: Don't update activeTabId here to maintain per-window independence
  })

  socket.on('workspace:ui_updated', (data: any) => {
    addEventLog('ui_updated', `UI state updated: ${Object.keys(data).join(', ')}`)
    if (data.panelWidth !== undefined) {
      uiState.value.panelWidth = data.panelWidth
    }
    if (data.isPanelVisible !== undefined) {
      uiState.value.isPanelVisible = data.isPanelVisible
    }
  })

  socket.on('workspace:client_connected', (data: any) => {
    addEventLog('client_connected', `Client connected (total: ${data.client_count})`)
    connectedClients.value = data.client_count
  })

  socket.on('workspace:client_disconnected', (data: any) => {
    addEventLog('client_disconnected', `Client disconnected (total: ${data.client_count})`)
    connectedClients.value = data.client_count
  })

  socket.on('workspace:error', (data: any) => {
    addEventLog('error', `Error: ${data.error}`)
  })

  // Terminal events
  socket.on('terminal:created', (data: any) => {
    addEventLog('terminal:created', `Terminal created: ${data.terminalId}`)
  })

  socket.on('terminal:data', (data: any) => {
    addEventLog('terminal:data', `Data for terminal ${data.terminalId}: ${data.data.length} bytes`)
  })
}

// Lifecycle
onMounted(() => {
  initializeSocket()
})

onUnmounted(() => {
  if (socket) {
    socket.disconnect()
  }
})
</script>

<style scoped>
.workspace-debug {
  padding: 15px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.4;
  color: #e0e0e0;
  background: #1e1e1e;
  height: 100%;
  overflow-y: auto;
}

.debug-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #444;
}

.debug-header h3 {
  margin: 0;
  color: #4caf50;
  font-size: 16px;
}

.connection-status {
  display: flex;
  gap: 10px;
  align-items: center;
}

.connected {
  color: #4caf50;
  font-weight: bold;
}

.disconnected {
  color: #f44336;
  font-weight: bold;
}

.client-count {
  color: #2196f3;
  font-weight: bold;
}

.debug-section {
  margin-bottom: 25px;
  padding: 15px;
  background: #2d2d2d;
  border-radius: 5px;
  border: 1px solid #444;
}

.debug-section h4 {
  margin: 0 0 15px 0;
  color: #64b5f6;
  font-size: 14px;
  font-weight: bold;
}

.debug-section h5 {
  margin: 10px 0 5px 0;
  color: #81c784;
  font-size: 12px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.info-item, .info-row, .pane-info {
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
}

.info-item label, .info-row label, .pane-info label {
  color: #bbb;
  font-weight: bold;
}

.info-item span, .info-row span, .pane-info span {
  color: #fff;
  word-break: break-all;
}

.tabs-list {
  space-y: 10px;
}

.tab-detail {
  background: #333;
  border: 1px solid #555;
  border-radius: 3px;
  padding: 10px;
  margin-bottom: 10px;
}

.tab-detail.active {
  border-color: #4caf50;
  background: #2e4a2e;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 5px;
  border-bottom: 1px solid #555;
}

.tab-title {
  color: #81c784;
  font-weight: bold;
}

.tab-id {
  color: #666;
  font-size: 10px;
  font-family: monospace;
}

.tab-info {
  margin-bottom: 10px;
}

.panes-list {
  margin-top: 10px;
}

.pane-detail {
  background: #444;
  border: 1px solid #666;
  border-radius: 3px;
  padding: 8px;
  margin-bottom: 5px;
}

.pane-detail.active {
  border-color: #2196f3;
  background: #2a3a4a;
}

.json-details {
  margin-top: 10px;
}

.json-details summary {
  color: #64b5f6;
  cursor: pointer;
  padding: 5px 0;
}

.json-details summary:hover {
  color: #90caf9;
}

.json-display {
  background: #1a1a1a;
  border: 1px solid #444;
  border-radius: 3px;
  padding: 10px;
  margin-top: 10px;
  overflow-x: auto;
  font-size: 11px;
  line-height: 1.3;
  color: #e0e0e0;
}

.events-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.clear-btn {
  background: #f44336;
  color: white;
  border: none;
  padding: 5px 10px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 11px;
}

.clear-btn:hover {
  background: #d32f2f;
}

.events-controls label {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #bbb;
  font-size: 11px;
}

.events-log {
  background: #1a1a1a;
  border: 1px solid #444;
  border-radius: 3px;
  height: 200px;
  overflow-y: auto;
  padding: 5px;
}

.event-entry {
  display: flex;
  gap: 10px;
  padding: 2px 5px;
  border-bottom: 1px solid #333;
  font-size: 10px;
  line-height: 1.3;
}

.event-entry:hover {
  background: #2d2d2d;
}

.event-time {
  color: #666;
  min-width: 60px;
  flex-shrink: 0;
}

.event-type {
  color: #64b5f6;
  min-width: 120px;
  flex-shrink: 0;
  font-weight: bold;
}

.event-data {
  color: #e0e0e0;
  word-break: break-all;
}

.event-entry.connect .event-type {
  color: #4caf50;
}

.event-entry.disconnect .event-type {
  color: #f44336;
}

.event-entry.error .event-type {
  color: #ff5722;
}

.event-entry.tab_created .event-type {
  color: #2196f3;
}

.event-entry.ui_updated .event-type {
  color: #ff9800;
}

/* Scrollbar styling */
.workspace-debug::-webkit-scrollbar,
.events-log::-webkit-scrollbar {
  width: 8px;
}

.workspace-debug::-webkit-scrollbar-track,
.events-log::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.workspace-debug::-webkit-scrollbar-thumb,
.events-log::-webkit-scrollbar-thumb {
  background: #666;
  border-radius: 4px;
}

.workspace-debug::-webkit-scrollbar-thumb:hover,
.events-log::-webkit-scrollbar-thumb:hover {
  background: #888;
}
</style>