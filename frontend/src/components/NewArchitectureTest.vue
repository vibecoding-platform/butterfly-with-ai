<template>
  <div class="new-architecture-test">
    <h2>🧪 New Socket.IO Architecture Test</h2>
    
    <!-- Connection Status -->
    <div class="connection-status">
      <h3>Connection Status</h3>
      <div :class="['status-indicator', connectionStatus]">
        Status: {{ connectionStatus }}
      </div>
      <div v-if="connectionState">
        <div>Socket ID: {{ connectionState.socketId || 'Not connected' }}</div>
        <div>Latency: {{ connectionState.latency }}ms</div>
        <div>Connected At: {{ connectionState.connectedAt ? new Date(connectionState.connectedAt).toLocaleTimeString() : 'Never' }}</div>
      </div>
    </div>

    <!-- Workspace State -->
    <div class="workspace-state">
      <h3>Workspace State</h3>
      <div>Loading: {{ workspaceState.isLoading }}</div>
      <div>Sessions: {{ workspaceState.sessions.length }}</div>
      <div>Active Session: {{ workspaceState.activeSessionId }}</div>
      <div>Last Sync: {{ workspaceState.lastSync ? new Date(workspaceState.lastSync).toLocaleTimeString() : 'Never' }}</div>
      <div v-if="workspaceState.syncError" class="error">
        Error: {{ workspaceState.syncError }}
      </div>
    </div>

    <!-- Test Actions -->
    <div class="test-actions">
      <h3>Test Actions</h3>
      <button @click="initializeWorkspace" :disabled="workspaceState.isLoading">
        Initialize Workspace
      </button>
      <button @click="createTestTab" :disabled="!isConnected">
        Create Test Tab
      </button>
      <button @click="reconnect">
        Reconnect
      </button>
    </div>

    <!-- Sessions Display -->
    <div class="sessions-display" v-if="workspaceState.sessions.length > 0">
      <h3>Sessions ({{ workspaceState.sessions.length }})</h3>
      <div v-for="session in workspaceState.sessions" :key="session.id" class="session">
        <h4>{{ session.name }} ({{ session.id }})</h4>
        <div class="tabs">
          <div v-for="tab in session.tabs" :key="tab.id" 
               :class="['tab', { active: session.activeTabId === tab.id }]">
            {{ tab.title }} ({{ tab.type }})
          </div>
        </div>
      </div>
    </div>

    <!-- Debug Info -->
    <div class="debug-info">
      <h3>Debug Info</h3>
      <pre>{{ JSON.stringify({ connectionState, workspaceState }, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getServiceFactory } from '@/services/ServiceFactory'
import { getWorkspaceService } from '@/services/workspace/WorkspaceSocketService'

const serviceFactory = getServiceFactory()
const workspaceService = getWorkspaceService()

// Reactive refs
const connectionState = ref(serviceFactory.getConnectionState().value)
const workspaceState = ref(workspaceService.getWorkspaceState().value)

const isConnected = computed(() => connectionState.value.status === 'connected')
const connectionStatus = computed(() => connectionState.value.status)

// Watch for state changes
let connectionUnwatch: (() => void) | null = null
let workspaceUnwatch: (() => void) | null = null

onMounted(() => {
  // Watch connection state
  const connectionStateRef = serviceFactory.getConnectionState()
  const connectionInterval = setInterval(() => {
    connectionState.value = connectionStateRef.value
  }, 1000)
  connectionUnwatch = () => clearInterval(connectionInterval)

  // Watch workspace state  
  const workspaceStateRef = workspaceService.getWorkspaceState()
  const workspaceInterval = setInterval(() => {
    workspaceState.value = workspaceStateRef.value
  }, 1000)
  workspaceUnwatch = () => clearInterval(workspaceInterval)
})

onUnmounted(() => {
  if (connectionUnwatch) connectionUnwatch()
  if (workspaceUnwatch) workspaceUnwatch()
})

// Test actions
const initializeWorkspace = async () => {
  try {
    console.log('🚀 Initializing workspace...')
    await workspaceService.initializeWorkspace()
    console.log('✅ Workspace initialized')
  } catch (error) {
    console.error('❌ Failed to initialize workspace:', error)
  }
}

const createTestTab = async () => {
  try {
    console.log('🆕 Creating test tab...')
    const response = await workspaceService.createTab({
      title: 'Test Tab',
      type: 'terminal',
      sessionId: 'test-session'
    })
    console.log('✅ Test tab created:', response)
  } catch (error) {
    console.error('❌ Failed to create test tab:', error)
  }
}

const reconnect = async () => {
  try {
    console.log('🔄 Reconnecting...')
    await serviceFactory.reconnect()
    console.log('✅ Reconnected')
  } catch (error) {
    console.error('❌ Failed to reconnect:', error)
  }
}
</script>

<style scoped>
.new-architecture-test {
  padding: 20px;
  font-family: monospace;
  max-width: 1200px;
  margin: 0 auto;
}

.connection-status,
.workspace-state,
.test-actions,
.sessions-display,
.debug-info {
  margin-bottom: 30px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background: #f9f9f9;
}

.status-indicator {
  padding: 5px 10px;
  border-radius: 3px;
  font-weight: bold;
  display: inline-block;
  margin: 5px 0;
}

.status-indicator.connected {
  background: #28a745;
  color: white;
}

.status-indicator.disconnected {
  background: #dc3545;
  color: white;
}

.status-indicator.connecting {
  background: #ffc107;
  color: black;
}

.status-indicator.error {
  background: #dc3545;
  color: white;
}

.error {
  color: #dc3545;
  font-weight: bold;
}

button {
  margin: 5px;
  padding: 8px 15px;
  border: 1px solid #007bff;
  background: #007bff;
  color: white;
  border-radius: 3px;
  cursor: pointer;
}

button:disabled {
  background: #6c757d;
  border-color: #6c757d;
  cursor: not-allowed;
}

button:hover:not(:disabled) {
  background: #0056b3;
}

.session {
  margin: 10px 0;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 3px;
  background: white;
}

.tabs {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.tab {
  padding: 5px 10px;
  border: 1px solid #ddd;
  border-radius: 3px;
  background: #f8f9fa;
}

.tab.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

pre {
  background: #f8f9fa;
  padding: 10px;
  border-radius: 3px;
  overflow: auto;
  max-height: 400px;
  font-size: 12px;
}
</style>