<template>
  <div v-if="userInfo?.isSupervisor" class="supervisor-control-panel">
    <div class="panel-header">
      <h3>Supervisor Control Panel</h3>
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
          -------
        </div>
        <div class="status-item">
          <span class="label">Supervisor Control:</span>
          <span class="value" :class="{ active: terminalStore.session.supervisorControlled }">
            {{ terminalStore.session.supervisorControlled ? 'Enabled' : 'Disabled' }}
          </span>
          -------
        </div>
        <div class="status-item">
          <span class="label">AIRisk:</span>
          <span class="value" :class="`risk-${terminalStore.aiMonitoring.riskAssessment}`">
            {{ terminalStore.aiMonitoring.riskAssessment.toUpperCase() }}
          </span>
        </div>
        -------
        <div class="status-item">
          <span class="label">Procedure Status:</span>
          <span class="value">
            {{ terminalStore.aiMonitoring.procedureStep }}/{{
              terminalStore.aiMonitoring.totalSteps
            }}
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
                  :style="{
                    width:
                      (terminalStore.aiMonitoring.procedureStep /
                        terminalStore.aiMonitoring.totalSteps) *
                        100 +
                      '%',
                  }"
                ></div>
              </div>
              <span class="progress-text">
                Step {{ terminalStore.aiMonitoring.procedureStep }} of
                {{ terminalStore.aiMonitoring.totalSteps }}
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

        <div
          v-if="terminalStore.aiMonitoring.suggestedActions.length > 0"
          class="suggested-actions"
        >
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
                <button @click="approveCommand(command.id)" class="action-btn approve-btn">
                  ✓ Yes, Execute
                </button>
                <button @click="showRejectDialog(command)" class="action-btn reject-btn">
                  ✗ No, Block
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
          <button @click="closeRejectDialog" class="action-btn cancel-btn">Cancel</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Non-Supervisor Message -->
  <div v-else class="access-denied">
    <div class="access-denied-content">
      <!-- JWT not found -->
      <div v-if="!userInfo" class="auth-error">
        <h3>🔑 Authentication Required</h3>
        <p>Please log in to access the Supervisor Control Panel.</p>
        <div class="auth-details">
          <p>No valid JWT token found.</p>
          <small>Token sources checked: localStorage, sessionStorage, URL params, cookies</small>
        </div>
      </div>

      <!-- JWT found but insufficient privileges -->
      <div v-else class="privilege-error">
        <h3>🔒 Access Restricted</h3>
        <p>Supervisor privileges required to access this panel.</p>
        <div class="user-info">
          <p><strong>Current user:</strong> {{ userInfo.email || 'Unknown' }}</p>
          <p><strong>Roles:</strong> {{ userInfo.roles?.join(', ') || 'None' }}</p>
        </div>
        <div class="privilege-requirements">
          <h4>Required privileges (any of):</h4>
          <ul>
            <li><code>isSupervisor: true</code></li>
            <li><code>roles: ["supervisor", "admin"]</code></li>
            <li><code>permissions: ["terminal:supervise", "admin:all"]</code></li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import type { TerminalCommand } from '../stores/aetherTerminalServiceStore'
  import { useAetherTerminalServiceStore } from '../stores/aetherTerminalServiceStore'
  import { getCurrentUser, getJWTToken, decodeJWT, isSupervisor } from '../utils/auth'

  const terminalStore = useAetherTerminalServiceStore()

  // User authentication state
  const userInfo = ref<{ email?: string; roles?: string[]; isSupervisor: boolean } | null>(null)

  // Check authentication on mount
  onMounted(() => {
    userInfo.value = getCurrentUser()

    // Debug JWT token status
    console.log('=== JWT Authentication Debug ===')
    console.log('User info loaded:', userInfo.value)

    const token = getJWTToken()
    if (token) {
      console.log('JWT token found:', token.substring(0, 50) + '...')
      const payload = decodeJWT(token)
      console.log('JWT payload:', payload)
      console.log('Is supervisor?', isSupervisor())
    } else {
      console.log('No JWT token found')
    }
    console.log('=================================')
  })

  // Local state
  const showRejectModal = ref(false)
  const commandToReject = ref<TerminalCommand | null>(null)
  const rejectionReason = ref('')

  // Computed properties
  const connectionStatusClass = computed(() => {
    switch (terminalStore.connectionStatus) {
      case 'connected':
        return 'status-connected'
      case 'connecting':
        return 'status-connecting'
      case 'reconnecting':
        return 'status-reconnecting'
      default:
        return 'status-disconnected'
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
      terminalStore.pauseTerminal('Paused by supervisor')
    }
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

  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString()
  }
</script>

<style scoped>
  .supervisor-control-panel {
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

  .status-connected {
    background-color: #4caf50;
    color: white;
  }

  .status-connecting {
    background-color: #ff9800;
    color: white;
  }

  .status-reconnecting {
    background-color: #ff9800;
    color: white;
  }

  .status-disconnected {
    background-color: #f44336;
    color: white;
  }

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

  .risk-level.low {
    background-color: #4caf50;
  }

  .risk-level.medium {
    background-color: #ff9800;
  }

  .risk-level.high {
    background-color: #ff5722;
  }

  .risk-level.critical {
    background-color: #f44336;
  }

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

  .history-item.approved {
    border-left-color: #4caf50;
    background-color: rgba(76, 175, 80, 0.1);
  }

  .history-item.rejected {
    border-left-color: #f44336;
    background-color: rgba(244, 67, 54, 0.1);
  }

  .history-item.executed {
    border-left-color: #2196f3;
    background-color: rgba(33, 150, 243, 0.1);
  }

  .status .approved {
    color: #4caf50;
  }

  .status .rejected {
    color: #f44336;
  }

  .status .executed {
    color: #2196f3;
  }

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
    transition: 0.4s;
    border-radius: 34px;
  }

  .slider:before {
    position: absolute;
    content: '';
    height: 26px;
    width: 26px;
    left: 4px;
    bottom: 4px;
    background-color: white;
    transition: 0.4s;
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

  .access-denied {
    background-color: #2d2d2d;
    color: #ffffff;
    padding: 20px;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  .access-denied-content {
    text-align: center;
    max-width: 400px;
    padding: 30px;
    border: 2px solid #444;
    border-radius: 8px;
    background-color: #1e1e1e;
  }

  .access-denied-content h3 {
    margin: 0 0 15px 0;
    color: #ff9800;
    font-size: 18px;
  }

  .access-denied-content p {
    margin: 10px 0;
    color: #ccc;
    line-height: 1.4;
  }

  .user-info {
    margin-top: 20px;
    padding: 15px;
    background-color: #333;
    border-radius: 4px;
    border-left: 3px solid #2196f3;
  }

  .user-info p {
    margin: 5px 0;
    font-size: 13px;
    color: #e0e0e0;
  }

  .auth-error {
    margin-top: 20px;
    padding: 15px;
    background-color: rgba(244, 67, 54, 0.1);
    border-radius: 4px;
    border-left: 3px solid #f44336;
  }

  .auth-error p {
    margin: 0;
    color: #ff8a80;
    font-size: 13px;
  }

  .auth-details {
    margin-top: 15px;
    padding: 10px;
    background-color: #333;
    border-radius: 4px;
    border-left: 3px solid #ff9800;
  }

  .auth-details p {
    margin: 5px 0;
    color: #e0e0e0;
    font-size: 13px;
  }

  .auth-details small {
    color: #bbb;
    font-size: 11px;
  }

  .privilege-error {
    /* Uses same styles as auth-error but with different content */
  }

  .privilege-requirements {
    margin-top: 15px;
    padding: 10px;
    background-color: #333;
    border-radius: 4px;
    border-left: 3px solid #9c27b0;
  }

  .privilege-requirements h4 {
    margin: 0 0 10px 0;
    color: #e1bee7;
    font-size: 14px;
  }

  .privilege-requirements ul {
    margin: 0;
    padding-left: 20px;
  }

  .privilege-requirements li {
    margin: 5px 0;
    color: #e0e0e0;
    font-size: 12px;
  }

  .privilege-requirements code {
    background-color: #444;
    padding: 2px 6px;
    border-radius: 3px;
    color: #4caf50;
    font-family: 'Courier New', monospace;
    font-size: 11px;
  }
</style>
