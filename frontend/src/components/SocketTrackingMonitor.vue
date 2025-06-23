<!--
Socket.IO Connection Tracking Monitor
Real-time monitoring dashboard for Socket.IO Vue ↔ Python communication
-->

<template>
  <div class="socket-tracking-monitor">
    <div class="monitor-header">
      <h3>🔗 Socket.IO Connection Monitor</h3>
      <div class="status-indicators">
        <span :class="['status-indicator', connectionStatus]">
          {{ connectionStatus.toUpperCase() }}
        </span>
        <span class="pending-count">
          {{ pendingRequests.length }} pending
        </span>
      </div>
    </div>

    <div class="metrics-summary">
      <div class="metric-card">
        <div class="metric-value">{{ metrics.totalRequests }}</div>
        <div class="metric-label">Total Requests</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{{ metrics.totalResponses }}</div>
        <div class="metric-label">Responses</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{{ Math.round(metrics.averageResponseTime) }}ms</div>
        <div class="metric-label">Avg Response</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{{ metrics.errorCount }}</div>
        <div class="metric-label">Errors</div>
      </div>
    </div>

    <div class="monitoring-sections">
      <!-- Pending Requests -->
      <div class="monitor-section">
        <h4>⏳ Pending Requests ({{ pendingRequests.length }})</h4>
        <div class="pending-list">
          <div 
            v-for="request in pendingRequests" 
            :key="request.requestId"
            :class="['pending-item', getRequestStatusClass(request)]"
          >
            <div class="request-info">
              <span class="event-name">{{ request.eventName }}</span>
              <span class="request-id">{{ request.requestId.substring(0, 8) }}...</span>
            </div>
            <div class="request-timing">
              {{ getTimeSince(request.timestamp) }}s ago
            </div>
          </div>
        </div>
        <div v-if="pendingRequests.length === 0" class="empty-state">
          ✅ No pending requests
        </div>
      </div>

      <!-- Recent Activity -->
      <div class="monitor-section">
        <h4>📊 Recent Activity</h4>
        <div class="activity-list">
          <div 
            v-for="activity in recentActivity" 
            :key="activity.id"
            :class="['activity-item', activity.type]"
          >
            <div class="activity-icon">
              {{ getActivityIcon(activity.type) }}
            </div>
            <div class="activity-details">
              <div class="activity-event">{{ activity.eventName }}</div>
              <div class="activity-meta">
                {{ activity.duration ? `${Math.round(activity.duration)}ms` : '' }}
                {{ activity.error ? `Error: ${activity.error}` : '' }}
              </div>
            </div>
            <div class="activity-time">
              {{ formatTime(activity.timestamp) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Event Metrics -->
      <div class="monitor-section">
        <h4>📈 Event Metrics</h4>
        <div class="event-metrics">
          <div 
            v-for="[eventName, eventMetric] in eventMetricsArray" 
            :key="eventName"
            class="event-metric-item"
          >
            <div class="event-name">{{ eventName }}</div>
            <div class="event-stats">
              <span class="stat">{{ eventMetric.requestCount }} req</span>
              <span class="stat">{{ Math.round(eventMetric.averageTime) }}ms avg</span>
              <span class="stat">{{ Math.round(eventMetric.successRate * 100) }}% success</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="monitor-actions">
      <button @click="clearMetrics" class="action-button">
        🗑️ Clear Metrics
      </button>
      <button @click="exportData" class="action-button">
        📤 Export Data
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import TrackedSocketService from '../services/tracking/TrackedSocketService'
import type { 
  PendingRequest, 
  ConnectionMetrics 
} from '../services/tracking/ISocketConnectionTracker'

// Reactive data
const connectionStatus = ref<'connected' | 'disconnected' | 'connecting'>('disconnected')
const pendingRequests = ref<PendingRequest[]>([])
const metrics = ref<ConnectionMetrics>({
  totalRequests: 0,
  totalResponses: 0,
  averageResponseTime: 0,
  timeoutCount: 0,
  errorCount: 0,
  pendingCount: 0,
  eventMetrics: new Map()
})

const recentActivity = ref<Array<{
  id: string
  type: 'request' | 'response' | 'timeout' | 'error'
  eventName: string
  timestamp: number
  duration?: number
  error?: string
}>>([])

// Computed properties
const eventMetricsArray = computed(() => {
  return Array.from(metrics.value.eventMetrics.entries())
})

// Service instance
let trackedService: TrackedSocketService | null = null
let updateInterval: number | null = null

// Lifecycle
onMounted(() => {
  trackedService = TrackedSocketService.getInstance()
  
  // Monitor connection status
  const socket = trackedService.getSocket()
  if (socket) {
    connectionStatus.value = socket.connected ? 'connected' : 'disconnected'
    
    socket.on('connect', () => {
      connectionStatus.value = 'connected'
      addActivity('response', 'socket:connect', Date.now())
    })
    
    socket.on('disconnect', () => {
      connectionStatus.value = 'disconnected'
      addActivity('response', 'socket:disconnect', Date.now())
    })
  }
  
  // Setup tracking callbacks
  const tracker = trackedService.getTracker()
  
  tracker.onRequestTimeout((request) => {
    addActivity('timeout', request.eventName, Date.now(), undefined, 'Request timeout')
  })
  
  tracker.onSlowResponse((request, duration) => {
    addActivity('response', request.eventName, Date.now(), duration)
  })
  
  tracker.onError((request, error) => {
    addActivity('error', request.eventName, Date.now(), undefined, error)
  })
  
  // Start periodic updates
  updateInterval = window.setInterval(updateData, 1000)
  updateData()
})

onUnmounted(() => {
  if (updateInterval) {
    clearInterval(updateInterval)
  }
})

// Methods
function updateData() {
  if (!trackedService) return
  
  pendingRequests.value = trackedService.getPendingRequests()
  metrics.value = trackedService.getConnectionMetrics()
}

function getRequestStatusClass(request: PendingRequest): string {
  const age = Date.now() - request.timestamp
  if (age > 5000) return 'timeout-warning'
  if (age > 2000) return 'slow-warning'
  return 'normal'
}

function getTimeSince(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000)
  return seconds.toString()
}

function getActivityIcon(type: string): string {
  switch (type) {
    case 'request': return '📤'
    case 'response': return '📥'
    case 'timeout': return '⏰'
    case 'error': return '❌'
    default: return '📊'
  }
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString()
}

function addActivity(
  type: 'request' | 'response' | 'timeout' | 'error',
  eventName: string,
  timestamp: number,
  duration?: number,
  error?: string
) {
  const activity = {
    id: `${timestamp}_${Math.random()}`,
    type,
    eventName,
    timestamp,
    duration,
    error
  }
  
  recentActivity.value.unshift(activity)
  
  // Keep only last 20 activities
  if (recentActivity.value.length > 20) {
    recentActivity.value = recentActivity.value.slice(0, 20)
  }
}

function clearMetrics() {
  if (trackedService) {
    trackedService.clearTrackingMetrics()
    recentActivity.value = []
    updateData()
  }
}

function exportData() {
  const data = {
    timestamp: new Date().toISOString(),
    connectionStatus: connectionStatus.value,
    metrics: {
      ...metrics.value,
      eventMetrics: Object.fromEntries(metrics.value.eventMetrics)
    },
    pendingRequests: pendingRequests.value,
    recentActivity: recentActivity.value
  }
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { 
    type: 'application/json' 
  })
  
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `socket-tracking-${Date.now()}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.socket-tracking-monitor {
  background: #1e1e1e;
  color: #ffffff;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  padding: 16px;
  border-radius: 8px;
  max-height: 80vh;
  overflow-y: auto;
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  border-bottom: 1px solid #333;
  padding-bottom: 8px;
}

.monitor-header h3 {
  margin: 0;
  color: #00d4aa;
}

.status-indicators {
  display: flex;
  gap: 12px;
  align-items: center;
}

.status-indicator {
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 10px;
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

.pending-count {
  background: #6c757d;
  color: white;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
}

.metrics-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  background: #2d2d2d;
  padding: 12px;
  border-radius: 6px;
  text-align: center;
}

.metric-value {
  font-size: 18px;
  font-weight: bold;
  color: #00d4aa;
}

.metric-label {
  font-size: 10px;
  color: #aaa;
  margin-top: 4px;
}

.monitoring-sections {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.monitor-section {
  background: #2d2d2d;
  padding: 12px;
  border-radius: 6px;
}

.monitor-section h4 {
  margin: 0 0 8px 0;
  color: #00d4aa;
  font-size: 12px;
}

.pending-list, .activity-list, .event-metrics {
  max-height: 200px;
  overflow-y: auto;
}

.pending-item, .activity-item, .event-metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  margin-bottom: 4px;
  background: #1a1a1a;
  border-radius: 4px;
  border-left: 3px solid #555;
}

.pending-item.timeout-warning {
  border-left-color: #dc3545;
  background: #2d1a1a;
}

.pending-item.slow-warning {
  border-left-color: #ffc107;
  background: #2d2a1a;
}

.pending-item.normal {
  border-left-color: #28a745;
}

.activity-item.error {
  border-left-color: #dc3545;
}

.activity-item.timeout {
  border-left-color: #ffc107;
}

.activity-item.response {
  border-left-color: #28a745;
}

.activity-item.request {
  border-left-color: #007bff;
}

.request-info, .activity-details {
  flex: 1;
}

.event-name, .activity-event {
  font-weight: bold;
  color: #fff;
}

.request-id, .activity-meta {
  font-size: 10px;
  color: #aaa;
}

.request-timing, .activity-time {
  font-size: 10px;
  color: #aaa;
}

.activity-icon {
  margin-right: 8px;
}

.event-stats {
  display: flex;
  gap: 8px;
}

.stat {
  font-size: 10px;
  color: #aaa;
}

.empty-state {
  text-align: center;
  color: #aaa;
  font-style: italic;
  padding: 16px;
}

.monitor-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  border-top: 1px solid #333;
  padding-top: 12px;
}

.action-button {
  background: #6c757d;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 10px;
  transition: background 0.2s;
}

.action-button:hover {
  background: #5a6268;
}
</style>