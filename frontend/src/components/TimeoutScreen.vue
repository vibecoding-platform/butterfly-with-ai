<template>
  <div class="timeout-screen">
    <div class="timeout-container">
      <!-- Timeout Icon -->
      <div class="timeout-icon">
        <svg width="80" height="80" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" stroke="#f59e0b" stroke-width="2"/>
          <path d="m15 9-6 6" stroke="#f59e0b" stroke-width="2"/>
          <path d="m9 9 6 6" stroke="#f59e0b" stroke-width="2"/>
          <circle cx="12" cy="12" r="3" stroke="#f59e0b" stroke-width="2" fill="none"/>
        </svg>
      </div>
      
      <!-- Timeout Title -->
      <h1 class="timeout-title">⏱️ Initialization Timeout</h1>
      
      <!-- Timeout Message -->
      <p class="timeout-message">
        AetherTerm services are taking longer than expected to initialize.
      </p>
      
      <!-- Error Details -->
      <div v-if="errorMessage" class="error-details">
        <details class="error-details-toggle">
          <summary>Error Details</summary>
          <div class="error-details-content">
            <p class="error-text">{{ errorMessage }}</p>
            <div class="error-info">
              <h3>Possible Causes</h3>
              <ul class="error-causes">
                <li>Server is not responding</li>
                <li>Network connectivity issues</li>
                <li>Server overload or maintenance</li>
                <li>Firewall blocking connection</li>
              </ul>
            </div>
          </div>
        </details>
      </div>
      
      <!-- Action Buttons -->
      <div class="timeout-actions">
        <button 
          class="btn btn-primary" 
          @click="handleRetry"
          :disabled="retrying"
        >
          <span v-if="retrying" class="loading-spinner"></span>
          {{ retrying ? 'Retrying...' : 'Retry Initialization' }}
        </button>
        
        <button 
          class="btn btn-secondary" 
          @click="handleReload"
        >
          Reload Page
        </button>
        
        <button 
          class="btn btn-outline" 
          @click="handleContinueAnyway"
          v-if="allowContinue"
        >
          Continue Anyway
        </button>
      </div>
      
      <!-- Status Information -->
      <div class="status-info">
        <div class="status-item">
          <span class="status-label">Initialization Time:</span>
          <span class="status-value">{{ formatDuration(duration) }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">Server URL:</span>
          <span class="status-value">{{ serverUrl || 'localhost:57575' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">Timestamp:</span>
          <span class="status-value">{{ formatTimestamp(timestamp) }}</span>
        </div>
      </div>
      
      <!-- Troubleshooting Tips -->
      <div class="troubleshooting">
        <h3>Troubleshooting Tips</h3>
        <ul class="tips-list">
          <li>Check your network connection</li>
          <li>Verify the server is running</li>
          <li>Try refreshing the page</li>
          <li>Check browser console for errors</li>
          <li>Contact system administrator if problem persists</li>
        </ul>
      </div>
      
      <!-- Support Links -->
      <div class="support-links">
        <a href="#" @click="copyDiagnosticInfo" class="support-link">
          Copy Diagnostic Info
        </a>
        <span class="separator">|</span>
        <a href="#" @click="openConsole" class="support-link">
          Open Browser Console
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface TimeoutScreenProps {
  errorMessage?: string
  serverUrl?: string
  timestamp?: Date
  duration?: number
  allowContinue?: boolean
}

const props = withDefaults(defineProps<TimeoutScreenProps>(), {
  errorMessage: '',
  serverUrl: '',
  timestamp: () => new Date(),
  duration: 30000,
  allowContinue: true
})

const emit = defineEmits<{
  retry: []
  reload: []
  continue: []
}>()

const retrying = ref(false)
const elapsedTime = ref(props.duration)

// Update elapsed time every second
const timeInterval = ref<number | null>(null)

const formatDuration = (ms: number): string => {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  
  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`
  }
  return `${remainingSeconds}s`
}

const formatTimestamp = (timestamp: Date): string => {
  return timestamp.toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const handleRetry = async () => {
  retrying.value = true
  
  try {
    emit('retry')
    
    // Wait for retry operation
    await new Promise(resolve => setTimeout(resolve, 2000))
    
  } catch (error) {
    console.error('Retry failed:', error)
  } finally {
    retrying.value = false
  }
}

const handleReload = () => {
  emit('reload')
  window.location.reload()
}

const handleContinueAnyway = () => {
  emit('continue')
}

const copyDiagnosticInfo = async () => {
  const diagnosticInfo = {
    error: 'Initialization Timeout',
    message: props.errorMessage,
    timestamp: props.timestamp.toISOString(),
    duration: props.duration,
    serverUrl: props.serverUrl,
    userAgent: navigator.userAgent,
    url: window.location.href,
    cookies: document.cookie ? 'enabled' : 'disabled',
    localStorage: typeof Storage !== 'undefined' ? 'supported' : 'not supported'
  }
  
  try {
    await navigator.clipboard.writeText(JSON.stringify(diagnosticInfo, null, 2))
    alert('Diagnostic information copied to clipboard')
  } catch (error) {
    console.error('Failed to copy diagnostic info:', error)
    alert('Failed to copy diagnostic information')
  }
}

const openConsole = () => {
  alert('Press F12 or right-click and select "Inspect Element" to open browser console')
}

onMounted(() => {
  // Update elapsed time periodically
  timeInterval.value = window.setInterval(() => {
    elapsedTime.value += 1000
  }, 1000)
})

onUnmounted(() => {
  if (timeInterval.value) {
    clearInterval(timeInterval.value)
  }
})
</script>

<style scoped>
.timeout-screen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #451a03 0%, #7c2d12 50%, #dc2626 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9997;
  padding: 20px;
  overflow-y: auto;
}

.timeout-container {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  max-width: 700px;
  width: 100%;
  padding: 40px;
  text-align: center;
  max-height: 90vh;
  overflow-y: auto;
}

.timeout-icon {
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.timeout-title {
  font-size: 2rem;
  font-weight: 700;
  color: #7c2d12;
  margin: 0 0 16px 0;
}

.timeout-message {
  font-size: 1.125rem;
  color: #6b7280;
  margin: 0 0 32px 0;
  line-height: 1.6;
}

.error-details {
  margin: 24px 0;
  text-align: left;
}

.error-details-toggle {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
}

.error-details-toggle summary {
  cursor: pointer;
  font-weight: 600;
  color: #374151;
  outline: none;
}

.error-details-content {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
}

.error-text {
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  background: #f9fafb;
  padding: 12px;
  border-radius: 4px;
  font-size: 0.875rem;
  color: #dc2626;
  margin-bottom: 16px;
}

.error-info h3 {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
  margin: 0 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.error-causes {
  margin: 0;
  padding-left: 20px;
  color: #6b7280;
  font-size: 0.875rem;
}

.error-causes li {
  margin-bottom: 4px;
}

.timeout-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 32px;
}

.btn {
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 140px;
  justify-content: center;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #dc2626;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #b91c1c;
}

.btn-secondary {
  background: #6b7280;
  color: white;
}

.btn-secondary:hover {
  background: #4b5563;
}

.btn-outline {
  background: transparent;
  color: #dc2626;
  border: 1px solid #dc2626;
}

.btn-outline:hover {
  background: #dc2626;
  color: white;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.status-info {
  margin-bottom: 32px;
  text-align: left;
  background: #f9fafb;
  padding: 16px;
  border-radius: 8px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 0.875rem;
}

.status-item:last-child {
  margin-bottom: 0;
}

.status-label {
  font-weight: 600;
  color: #374151;
}

.status-value {
  color: #6b7280;
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
}

.troubleshooting {
  margin-bottom: 32px;
  text-align: left;
}

.troubleshooting h3 {
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
  margin: 0 0 12px 0;
}

.tips-list {
  margin: 0;
  padding-left: 20px;
  color: #6b7280;
  font-size: 0.875rem;
}

.tips-list li {
  margin-bottom: 6px;
}

.support-links {
  border-top: 1px solid #e5e7eb;
  padding-top: 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.support-link {
  color: #dc2626;
  text-decoration: none;
  font-size: 0.875rem;
  cursor: pointer;
}

.support-link:hover {
  text-decoration: underline;
}

.separator {
  color: #d1d5db;
}

/* Responsive */
@media (max-width: 640px) {
  .timeout-container {
    padding: 24px;
    margin: 20px;
  }
  
  .timeout-title {
    font-size: 1.5rem;
  }
  
  .timeout-actions {
    flex-direction: column;
    align-items: stretch;
  }
  
  .btn {
    width: 100%;
  }
  
  .status-item {
    flex-direction: column;
    gap: 4px;
  }
}
</style>