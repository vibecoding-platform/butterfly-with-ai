<template>
  <div class="terminal-container">
    <!-- Connection Status -->
    <div v-if="!terminalStore.connectionState.isConnected" class="connection-status">
      <div class="status-indicator" :class="connectionStatusClass">
        {{ connectionStatusText }}
      </div>
      <div v-if="terminalStore.connectionState.isReconnecting" class="reconnect-info">
        Reconnection attempt: {{ terminalStore.connectionState.reconnectAttempts }}/{{ terminalStore.connectionState.maxReconnectAttempts }}
      </div>
    </div>

    <!-- Terminal Blocked Overlay -->
    <div v-if="terminalStore.isTerminalBlocked" class="terminal-overlay">
      <div class="overlay-content">
        <div v-if="terminalStore.session.isPaused" class="block-reason">
          <h3>Terminal Paused</h3>
          <p>Terminal has been paused by administrator</p>
        </div>
        <div v-else-if="terminalStore.hasPendingCommands" class="block-reason">
          <h3>Commands Pending Review</h3>
          <p>{{ terminalStore.pendingCommands.length }} command(s) awaiting approval</p>
          <div class="pending-commands">
            <div v-for="cmd in terminalStore.pendingCommands" :key="cmd.id" class="pending-command">
              <code>{{ cmd.command }}</code>
              <span class="risk-level" :class="cmd.riskLevel">{{ cmd.riskLevel }}</span>
            </div>
          </div>
        </div>
        <div v-else-if="terminalStore.isOutputSuppressed" class="block-reason">
          <h3>Output Suppressed</h3>
          <p>Terminal output is currently suppressed</p>
        </div>
        <div v-else-if="!terminalStore.connectionState.isConnected" class="block-reason">
          <h3>Connection Lost</h3>
          <p>Reconnecting to terminal service...</p>
        </div>
      </div>
    </div>

    <!-- Terminal Output Buffer -->
    <div class="terminal-output" ref="outputContainer">
      <div v-for="(line, index) in terminalStore.outputBuffer" :key="index" class="output-line">
        {{ line }}
      </div>
    </div>

    <!-- Command Input -->
    <div class="command-input-container">
      <input
        v-model="currentCommand"
        @keyup.enter="submitCommand"
        :disabled="terminalStore.isTerminalBlocked"
        class="command-input"
        placeholder="Enter command..."
      />
      <button
        @click="submitCommand"
        :disabled="terminalStore.isTerminalBlocked || !currentCommand.trim()"
        class="submit-button"
      >
        Execute
      </button>
    </div>

    <!-- VueTerm Integration (if needed) -->
    <div v-if="showVueTerm" class="vue-term-container">
      <VueTerm :shell-ws="shellWs" :ctl-ws="ctlWs" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAetherTerminalServiceStore } from '../stores/aetherTerminalServiceStore'

const terminalStore = useAetherTerminalServiceStore()

const shellWs = ref<WebSocket | null>(null)
const ctlWs = ref<WebSocket | null>(null)
const currentCommand = ref('')
const outputContainer = ref<HTMLElement>()
const showVueTerm = ref(false) // Toggle for VueTerm integration

// Connection status computed properties
const connectionStatusClass = computed(() => {
  switch (terminalStore.connectionStatus) {
    case 'connected': return 'status-connected'
    case 'connecting': return 'status-connecting'
    case 'reconnecting': return 'status-reconnecting'
    default: return 'status-disconnected'
  }
})

const connectionStatusText = computed(() => {
  switch (terminalStore.connectionStatus) {
    case 'connected': return 'Connected'
    case 'connecting': return 'Connecting...'
    case 'reconnecting': return 'Reconnecting...'
    default: return 'Disconnected'
  }
})

// Terminal output handlers
const handleShellOutput = (data: string) => {
  console.log('Shell Output:', data)
  // Output is already handled by the store
}

const handleControlOutput = (data: string) => {
  console.log('Control Output:', data)
  // Output is already handled by the store
}

const handleConnect = () => {
  console.log('Terminal connected')
}

const handleDisconnect = () => {
  console.log('Terminal disconnected')
}

const handleError = (error: any) => {
  console.error('Terminal error:', error)
}

// Command submission
const submitCommand = () => {
  const command = currentCommand.value.trim()
  if (!command || terminalStore.isTerminalBlocked) return

  const success = terminalStore.submitCommand(command)
  if (success) {
    currentCommand.value = ''
  }
}

// Auto-scroll output
watch(() => terminalStore.outputBuffer.length, () => {
  nextTick(() => {
    if (outputContainer.value) {
      outputContainer.value.scrollTop = outputContainer.value.scrollHeight
    }
  })
})

onMounted(() => {
  // Register event handlers with the store
  terminalStore.onShellOutput(handleShellOutput)
  terminalStore.onControlOutput(handleControlOutput)
  terminalStore.onConnect(handleConnect)
  terminalStore.onDisconnect(handleDisconnect)
  terminalStore.onError(handleError)
})

onUnmounted(() => {
  // Clean up event handlers
  terminalStore.offShellOutput(handleShellOutput)
  terminalStore.offControlOutput(handleControlOutput)
})
</script>

<style scoped>
.terminal-container {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  background-color: #1e1e1e;
  color: #ffffff;
  font-family: 'Courier New', monospace;
  position: relative;
}

.connection-status {
  padding: 8px 12px;
  background-color: #2d2d2d;
  border-bottom: 1px solid #444;
}

.status-indicator {
  font-size: 12px;
  font-weight: bold;
}

.status-connected { color: #4caf50; }
.status-connecting { color: #ff9800; }
.status-reconnecting { color: #ff9800; }
.status-disconnected { color: #f44336; }

.reconnect-info {
  font-size: 11px;
  color: #ccc;
  margin-top: 4px;
}

.terminal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.overlay-content {
  background-color: #2d2d2d;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  max-width: 400px;
}

.block-reason h3 {
  margin: 0 0 10px 0;
  color: #ff9800;
}

.pending-commands {
  margin-top: 15px;
  text-align: left;
}

.pending-command {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background-color: #1e1e1e;
  margin: 4px 0;
  border-radius: 4px;
}

.pending-command code {
  color: #4caf50;
}

.risk-level {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: bold;
}

.risk-level.low { background-color: #4caf50; }
.risk-level.medium { background-color: #ff9800; }
.risk-level.high { background-color: #ff5722; }
.risk-level.critical { background-color: #f44336; }

.terminal-output {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  font-size: 14px;
  line-height: 1.4;
}

.output-line {
  margin: 2px 0;
  white-space: pre-wrap;
}

.command-input-container {
  display: flex;
  padding: 10px;
  background-color: #2d2d2d;
  border-top: 1px solid #444;
}

.command-input {
  flex: 1;
  background-color: #1e1e1e;
  border: 1px solid #444;
  color: #ffffff;
  padding: 8px 12px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}

.command-input:focus {
  outline: none;
  border-color: #4caf50;
}

.command-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.submit-button {
  margin-left: 10px;
  padding: 8px 16px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.submit-button:hover:not(:disabled) {
  background-color: #45a049;
}

.submit-button:disabled {
  background-color: #666;
  cursor: not-allowed;
}

.vue-term-container {
  height: 300px;
  border-top: 1px solid #444;
}
</style>