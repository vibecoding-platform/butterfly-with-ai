<template>
  <div class="admin-control-panel">
    <div class="panel-header">
      <h3>Admin Control Panel</h3>
      <div class="connection-status" :class="connectionStatusClass">
        {{ terminalStore.connectionStatus }}
      </div>
    </div>

    <!-- System Status Section (Moved to top) -->
    <div class="control-section priority">
      <h4>System Status</h4>
      <div class="status-grid">
        <div class="status-item">
          <span class="label">Session ID:</span>
          <span class="value">{{ terminalStore.session.id }}</span>
        </div>
        <div class="status-item">
          <span class="label">Last Activity:</span>
          <span class="value">{{ formatTime(terminalStore.session.lastActivity) }}</span>
        </div>
        <div class="status-item">
          <span class="label">Admin Control:</span>
          <span class="value" :class="{ active: terminalStore.session.adminControlled }">
            {{ terminalStore.session.adminControlled ? 'Enabled' : 'Disabled' }}
          </span>
        </div>
        <div class="status-item">
          <span class="label">Connection Attempts:</span>
          <span class="value">{{ terminalStore.connectionState.reconnectAttempts }}</span>
        </div>
        <div class="status-item">
          <span class="label">AI Risk Level:</span>
          <span class="value" :class="`risk-${terminalStore.aiMonitoring.riskAssessment}`">
            {{ terminalStore.aiMonitoring.riskAssessment.toUpperCase() }}
          </span>
        </div>
        <div class="status-item">
          <span class="label">Procedure Progress:</span>
          <span class="value">
            {{ terminalStore.aiMonitoring.procedureStep }}/{{ terminalStore.aiMonitoring.totalSteps }}
          </span>
        </div>
      </div>
    </div>

    <!-- AI Monitoring Section (Updated) -->
    <div class="control-section">
      <h4>AI Monitoring Status</h4>
      <div class="ai-status">
        <div class="monitoring-indicator" :class="{ active: terminalStore.aiMonitoring.isActive }">
          <span class="indicator-dot"></span>
          {{ terminalStore.aiMonitoring.isActive ? 'Active' : 'Inactive' }}
        </div>
        
        <div v-if="terminalStore.aiMonitoring.currentProcedure" class="current-procedure">
          <h5>Current Procedure</h5>
          <div class="procedure-info">
            <div class="procedure-name">{{ terminalStore.aiMonitoring.currentProcedure }}</div>
            <div class="procedure-progress">
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: (terminalStore.aiMonitoring.procedureStep / terminalStore.aiMonitoring.totalSteps * 100) + '%' }"
                ></div>
              </div>
              <span class="progress-text">
                Step {{ terminalStore.aiMonitoring.procedureStep }} of {{ terminalStore.aiMonitoring.totalSteps }}
              </span>
            </div>
          </div>
        </div>

        <div class="monitoring-rules">
          <h5>Active Monitoring Rules</h5>
          <div class="rules-list">
            <div
              v-for="rule in terminalStore.aiMonitoring.monitoringRules"
              :key="rule"
              class="rule-item"
            >
              <span class="rule-indicator">✓</span>
              {{ rule }}
            </div>
          </div>
        </div>

        <div v-if="terminalStore.aiMonitoring.suggestedActions.length > 0" class="suggested-actions">
          <h5>AI Suggestions</h5>
          <div class="suggestions-list">
            <div
              v-for="action in terminalStore.aiMonitoring.suggestedActions"
              :key="action"
              class="suggestion-item"
            >
              <span class="suggestion-icon">💡</span>
              {{ action }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Terminal Control Section -->
    <div class="control-section">
      <h4>Terminal Control</h4>
      <div class="control-buttons">
        <button 
          @click="toggleTerminalPause"
          :class="{ active: terminalStore.session.isPaused }"
          class="control-btn pause-btn"
        >
          {{ terminalStore.session.isPaused ? 'Resume' : 'Pause' }} Terminal
        </button>
        
        <button 
          @click="toggleOutputSuppression"
          :class="{ active: terminalStore.isOutputSuppressed }"
          class="control-btn suppress-btn"
        >
          {{ terminalStore.isOutputSuppressed ? 'Restore' : 'Suppress' }} Output
        </button>
        
        <button 
          @click="clearTerminalOutput"
          class="control-btn clear-btn"
        >
          Clear Output
        </button>
      </div>
    </div>

    <!-- AI Command Review Section -->
    <div v-if="terminalStore.hasPendingCommands" class="control-section">
      <h4>AI Command Review ({{ terminalStore.pendingCommands.length }})</h4>
      <div class="pending-commands-list">
        <div
          v-for="command in terminalStore.pendingCommands"
          :key="command.id"
          class="pending-command-item"
        >
          <div class="command-info">
            <div class="command-header">
              <div class="command-text">
                <code>{{ command.command }}</code>
              </div>
              <div class="command-meta">
                <span class="risk-level" :class="command.riskLevel">
                  {{ command.riskLevel.toUpperCase() }}
                </span>
                <span class="timestamp">
                  {{ formatTime(command.timestamp) }}
                </span>
              </div>
            </div>
            
            <div v-if="command.aiSuggestion" class="ai-analysis">
              <div class="analysis-header">
                <span class="ai-icon">🤖</span>
                <strong>AI Analysis & Recommendation</strong>
              </div>
              <div class="analysis-content">
                {{ command.aiSuggestion }}
              </div>
            </div>

            <div class="interactive-dialog">
              <div class="dialog-question">
                <strong>Do you want to proceed with this command?</strong>
              </div>
              <div class="dialog-options">
                <button
                  @click="approveCommand(command.id)"
                  class="action-btn approve-btn"
                >
                  ✓ Yes, Execute
                </button>
                <button
                  @click="showRejectDialog(command)"
                  class="action-btn reject-btn"
                >
                  ✗ No, Block
                </button>
                <button
                  @click="requestAlternative(command)"
                  class="action-btn alternative-btn"
                >
                  💡 Suggest Alternative
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Command History Section -->
    <div class="control-section">
      <h4>Recent Commands</h4>
      <div class="command-history">
        <div 
          v-for="command in recentCommands" 
          :key="command.id"
          class="history-item"
          :class="command.status"
        >
          <div class="command-text">
            <code>{{ command.command }}</code>
          </div>
          <div class="command-meta">
            <span class="status" :class="command.status">
              {{ command.status.toUpperCase() }}
            </span>
            <span class="timestamp">
              {{ formatTime(command.timestamp) }}
            </span>
          </div>
          <div v-if="command.rejectionReason" class="rejection-reason">
            <strong>Rejected:</strong> {{ command.rejectionReason }}
          </div>
        </div>
      </div>
    </div>


    <!-- Reject Command Dialog -->
    <div v-if="showRejectModal" class="modal-overlay" @click="closeRejectDialog">
      <div class="modal-content" @click.stop>
        <h3>Reject Command</h3>
        <div class="command-to-reject">
          <code>{{ commandToReject?.command }}</code>
        </div>
        <div class="form-group">
          <label>Rejection Reason:</label>
          <textarea 
            v-model="rejectionReason"
            placeholder="Enter reason for rejection..."
            rows="3"
          ></textarea>
        </div>
        <div class="modal-actions">
          <button @click="confirmRejectCommand" class="action-btn reject-btn">
            Reject Command
          </button>
          <button @click="closeRejectDialog" class="action-btn cancel-btn">
            Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { TerminalCommand } from '../stores/aetherTerminalServiceStore'
import { useAetherTerminalServiceStore } from '../stores/aetherTerminalServiceStore'

const terminalStore = useAetherTerminalServiceStore()

// Local state
const showRejectModal = ref(false)
const commandToReject = ref<TerminalCommand | null>(null)
const rejectionReason = ref('')

// Computed properties
const connectionStatusClass = computed(() => {
  switch (terminalStore.connectionStatus) {
    case 'connected': return 'status-connected'
    case 'connecting': return 'status-connecting'
    case 'reconnecting': return 'status-reconnecting'
    default: return 'status-disconnected'
  }
})

const recentCommands = computed(() => {
  return terminalStore.commandHistory.slice(-10).reverse()
})

// Methods
const toggleTerminalPause = () => {
  if (terminalStore.session.isPaused) {
    terminalStore.resumeTerminal()
  } else {
    terminalStore.pauseTerminal('Paused by administrator')
  }
}

const toggleOutputSuppression = () => {
  if (terminalStore.isOutputSuppressed) {
    terminalStore.suppressOutput(false)
  } else {
    terminalStore.suppressOutput(true, 'Suppressed by administrator')
  }
}

const clearTerminalOutput = () => {
  terminalStore.clearOutput()
}

const approveCommand = (commandId: string) => {
  terminalStore.approveCommand(commandId)
}

const showRejectDialog = (command: TerminalCommand) => {
  commandToReject.value = command
  rejectionReason.value = ''
  showRejectModal.value = true
}

const closeRejectDialog = () => {
  showRejectModal.value = false
  commandToReject.value = null
  rejectionReason.value = ''
}

const confirmRejectCommand = () => {
  if (commandToReject.value && rejectionReason.value.trim()) {
    terminalStore.rejectCommand(commandToReject.value.id, rejectionReason.value.trim())
    closeRejectDialog()
  }
}

const requestAlternative = (command: TerminalCommand) => {
  // Request AI to suggest alternative command
  console.log('Requesting alternative for:', command.command)
  // This would typically emit a socket event to request AI alternatives
  // terminalStore.requestAlternativeCommand(command.id)
}

const formatTime = (date: Date) => {
  return new Date(date).toLocaleTimeString()
}
</script>

<style scoped>
.admin-control-panel {
  background-color: #2d2d2d;
  color: #ffffff;
  padding: 20px;
  height: 100%;
  overflow-y: auto;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #444;
}

.panel-header h3 {
  margin: 0;
  color: #4caf50;
}

.connection-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.status-connected { background-color: #4caf50; color: white; }
.status-connecting { background-color: #ff9800; color: white; }
.status-reconnecting { background-color: #ff9800; color: white; }
.status-disconnected { background-color: #f44336; color: white; }

.control-section {
  margin-bottom: 25px;
}

.control-section h4 {
  margin: 0 0 15px 0;
  color: #ff9800;
  font-size: 16px;
}

.control-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.control-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.pause-btn {
  background-color: #ff9800;
  color: white;
}

.pause-btn.active {
  background-color: #4caf50;
}

.suppress-btn {
  background-color: #2196f3;
  color: white;
}

.suppress-btn.active {
  background-color: #f44336;
}

.clear-btn {
  background-color: #666;
  color: white;
}

.control-btn:hover {
  opacity: 0.8;
}

.pending-commands-list {
  max-height: 300px;
  overflow-y: auto;
}

.pending-command-item {
  background-color: #1e1e1e;
  border: 1px solid #444;
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 10px;
}

.command-info {
  margin-bottom: 10px;
}

.command-text code {
  background-color: #333;
  padding: 4px 8px;
  border-radius: 3px;
  color: #4caf50;
  font-family: 'Courier New', monospace;
}

.command-meta {
  display: flex;
  gap: 15px;
  margin-top: 8px;
  font-size: 12px;
}

.risk-level {
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: bold;
}

.risk-level.low { background-color: #4caf50; }
.risk-level.medium { background-color: #ff9800; }
.risk-level.high { background-color: #ff5722; }
.risk-level.critical { background-color: #f44336; }

.timestamp {
  color: #ccc;
}

.ai-suggestion {
  margin-top: 8px;
  padding: 8px;
  background-color: #333;
  border-radius: 4px;
  font-size: 13px;
  color: #e0e0e0;
}

.command-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.approve-btn {
  background-color: #4caf50;
  color: white;
}

.reject-btn {
  background-color: #f44336;
  color: white;
}

.cancel-btn {
  background-color: #666;
  color: white;
}

.command-history {
  max-height: 200px;
  overflow-y: auto;
}

.history-item {
  padding: 8px;
  margin-bottom: 5px;
  border-radius: 4px;
  border-left: 3px solid;
}

.history-item.approved { border-left-color: #4caf50; background-color: rgba(76, 175, 80, 0.1); }
.history-item.rejected { border-left-color: #f44336; background-color: rgba(244, 67, 54, 0.1); }
.history-item.executed { border-left-color: #2196f3; background-color: rgba(33, 150, 243, 0.1); }

.status .approved { color: #4caf50; }
.status .rejected { color: #f44336; }
.status .executed { color: #2196f3; }

.rejection-reason {
  margin-top: 5px;
  font-size: 12px;
  color: #ff8a80;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 60px;
  height: 34px;
  margin-bottom: 15px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .4s;
  border-radius: 34px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 26px;
  width: 26px;
  left: 4px;
  bottom: 4px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #4caf50;
}

input:checked + .slider:before {
  transform: translateX(26px);
}

.dangerous-commands h5 {
  margin: 10px 0;
  color: #ff5722;
}

.command-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 10px;
}

.command-tag {
  background-color: #f44336;
  color: white;
  padding: 4px 8px;
  border-radius: 3px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.remove-tag {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 14px;
  padding: 0;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-command {
  display: flex;
  gap: 10px;
}

.add-input {
  flex: 1;
  padding: 6px 10px;
  background-color: #1e1e1e;
  border: 1px solid #444;
  color: white;
  border-radius: 4px;
}

.add-btn {
  padding: 6px 12px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  padding: 8px;
  background-color: #1e1e1e;
  border-radius: 4px;
}

.label {
  color: #ccc;
  font-size: 12px;
}

.value {
  color: white;
  font-size: 12px;
  font-weight: bold;
}

.value.active {
  color: #4caf50;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background-color: #2d2d2d;
  padding: 20px;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
}

.modal-content h3 {
  margin: 0 0 15px 0;
  color: #ff9800;
}

.command-to-reject {
  background-color: #1e1e1e;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 15px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  color: #ccc;
}

.form-group textarea {
  width: 100%;
  padding: 8px;
  background-color: #1e1e1e;
  border: 1px solid #444;
  color: white;
  border-radius: 4px;
  resize: vertical;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
</style>