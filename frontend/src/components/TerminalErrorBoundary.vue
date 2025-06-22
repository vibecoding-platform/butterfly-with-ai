<!--
Terminal-specific Error Boundary Component for AetherTerm
Specialized error handling for terminal-related components
-->

<template>
  <ErrorBoundary
    name="TerminalErrorBoundary"
    :fallback-title="errorTitle"
    :fallback-message="errorMessage"
    :show-retry="true"
    :show-reload="false"
    :show-report="true"
    :show-details="true"
    :on-error="handleTerminalError"
    :on-retry="handleTerminalRetry"
    ref="errorBoundary"
  >
    <slot />
    
    <!-- Terminal-specific error fallback -->
    <template v-if="showTerminalFallback">
      <div class="terminal-error-fallback">
        <div class="terminal-error-header">
          <div class="terminal-icon">🖥️</div>
          <h3>Terminal Error</h3>
        </div>
        
        <div class="terminal-error-content">
          <p class="error-description">
            {{ terminalErrorDescription }}
          </p>
          
          <div class="terminal-info" v-if="terminalContext">
            <div class="info-item">
              <strong>Terminal ID:</strong> {{ terminalContext.terminalId }}
            </div>
            <div class="info-item" v-if="terminalContext.lastCommand">
              <strong>Last Command:</strong> {{ terminalContext.lastCommand }}
            </div>
            <div class="info-item" v-if="terminalContext.connectionState">
              <strong>Connection:</strong> {{ terminalContext.connectionState }}
            </div>
            <div class="info-item" v-if="terminalContext.processId">
              <strong>Process ID:</strong> {{ terminalContext.processId }}
            </div>
          </div>
          
          <div class="terminal-actions">
            <button @click="handleReconnect" class="reconnect-btn">
              🔌 Reconnect Terminal
            </button>
            <button @click="handleCreateNew" class="new-terminal-btn">
              ➕ New Terminal
            </button>
            <button @click="handleDiagnostics" class="diagnostics-btn">
              🔍 Run Diagnostics
            </button>
          </div>
        </div>
      </div>
    </template>
  </ErrorBoundary>
</template>

<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import ErrorBoundary from './ErrorBoundary.vue'
import { openTelemetryService } from '../services/OpenTelemetryService'

interface TerminalContext {
  terminalId?: string
  lastCommand?: string
  connectionState?: string
  processId?: string
  socketConnected?: boolean
  ptyState?: string
}

interface Props {
  terminalId?: string
  fallbackMode?: 'generic' | 'terminal'
  onTerminalError?: (error: Error, context: TerminalContext) => void
  onReconnect?: () => Promise<void>
  onCreateNew?: () => Promise<void>
}

const props = withDefaults(defineProps<Props>(), {
  fallbackMode: 'generic'
})

const emit = defineEmits<{
  terminalError: [error: Error, context: TerminalContext]
  reconnectRequested: []
  newTerminalRequested: []
  diagnosticsRequested: []
}>()

// Reactive state
const errorBoundary = ref<InstanceType<typeof ErrorBoundary> | null>(null)
const terminalContext = ref<TerminalContext>({})
const lastError = ref<Error | null>(null)
const isTerminalSpecificError = ref(false)

// Computed properties
const showTerminalFallback = computed(() => 
  isTerminalSpecificError.value && props.fallbackMode === 'terminal'
)

const errorTitle = computed(() => {
  if (isTerminalSpecificError.value) {
    return 'Terminal Connection Error'
  }
  return 'Terminal Component Error'
})

const errorMessage = computed(() => {
  if (isTerminalSpecificError.value) {
    return 'The terminal connection has encountered an issue and needs to be restored.'
  }
  return 'An error occurred in the terminal component.'
})

const terminalErrorDescription = computed(() => {
  if (!lastError.value) return 'Unknown terminal error'
  
  const message = lastError.value.message.toLowerCase()
  
  if (message.includes('socket') || message.includes('connection')) {
    return 'The terminal lost connection to the server. This might be due to network issues or server problems.'
  }
  
  if (message.includes('pty') || message.includes('process')) {
    return 'The terminal process has stopped or crashed. A new terminal session may be needed.'
  }
  
  if (message.includes('permission') || message.includes('access')) {
    return 'There was a permission issue accessing the terminal. Please check your access rights.'
  }
  
  if (message.includes('timeout')) {
    return 'The terminal operation timed out. The server might be overloaded or unreachable.'
  }
  
  return `Terminal error: ${lastError.value.message}`
})

// Error handling
const handleTerminalError = (error: Error, errorInfo: any) => {
  console.error('🖥️ Terminal Error Boundary caught error:', error)
  
  lastError.value = error
  
  // Determine if this is a terminal-specific error
  const errorMessage = error.message.toLowerCase()
  isTerminalSpecificError.value = 
    errorMessage.includes('terminal') ||
    errorMessage.includes('pty') ||
    errorMessage.includes('socket') ||
    errorMessage.includes('connection') ||
    errorMessage.includes('process')
  
  // Collect terminal context
  terminalContext.value = collectTerminalContext()
  
  // Log terminal-specific error information
  openTelemetryService.logError('terminal_component_error', error, {
    terminal_id: props.terminalId,
    terminal_context: terminalContext.value,
    is_terminal_specific: isTerminalSpecificError.value,
    error_type: categorizeTerminalError(error)
  })
  
  // Create terminal error trace
  const span = openTelemetryService.traceTerminalOperation({
    terminalId: props.terminalId || 'unknown',
    operation: 'error_handling'
  })
  
  if (span) {
    span.recordException(error)
    span.setAttributes({
      'error.category': categorizeTerminalError(error),
      'terminal.context': JSON.stringify(terminalContext.value),
      'error.is_terminal_specific': isTerminalSpecificError.value
    })
    span.end()
  }
  
  // Call custom error handler
  if (props.onTerminalError) {
    props.onTerminalError(error, terminalContext.value)
  }
  
  // Emit error event
  emit('terminalError', error, terminalContext.value)
}

const handleTerminalRetry = () => {
  console.log('🔄 Retrying terminal component...')
  
  // Reset terminal-specific state
  isTerminalSpecificError.value = false
  terminalContext.value = {}
  lastError.value = null
  
  // Log retry action
  openTelemetryService.logInfo('terminal_error_boundary_retry', {
    terminal_id: props.terminalId,
    retry_type: 'component_retry'
  })
}

// Terminal-specific actions
const handleReconnect = async () => {
  console.log('🔌 Reconnecting terminal...')
  
  try {
    // Log reconnection attempt
    openTelemetryService.logInfo('terminal_reconnect_attempt', {
      terminal_id: props.terminalId,
      context: terminalContext.value
    })
    
    if (props.onReconnect) {
      await props.onReconnect()
    }
    
    // Reset error boundary after successful reconnection
    errorBoundary.value?.reset()
    
    emit('reconnectRequested')
    
  } catch (error) {
    console.error('Failed to reconnect terminal:', error)
    openTelemetryService.logError('terminal_reconnect_failed', error as Error, {
      terminal_id: props.terminalId
    })
  }
}

const handleCreateNew = async () => {
  console.log('➕ Creating new terminal...')
  
  try {
    // Log new terminal creation
    openTelemetryService.logInfo('terminal_new_creation', {
      terminal_id: props.terminalId,
      trigger: 'error_recovery'
    })
    
    if (props.onCreateNew) {
      await props.onCreateNew()
    }
    
    // Reset error boundary after creating new terminal
    errorBoundary.value?.reset()
    
    emit('newTerminalRequested')
    
  } catch (error) {
    console.error('Failed to create new terminal:', error)
    openTelemetryService.logError('terminal_creation_failed', error as Error, {
      terminal_id: props.terminalId
    })
  }
}

const handleDiagnostics = () => {
  console.log('🔍 Running terminal diagnostics...')
  
  // Collect diagnostic information
  const diagnostics = {
    terminalId: props.terminalId,
    context: terminalContext.value,
    error: lastError.value ? {
      name: lastError.value.name,
      message: lastError.value.message,
      stack: lastError.value.stack
    } : null,
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    url: window.location.href,
    connectionState: {
      online: navigator.onLine,
      connectionType: (navigator as any).connection?.effectiveType || 'unknown'
    }
  }
  
  // Log diagnostics
  openTelemetryService.logInfo('terminal_diagnostics', {
    terminal_id: props.terminalId,
    diagnostics: JSON.stringify(diagnostics).substring(0, 2000)
  })
  
  // Copy diagnostics to clipboard
  navigator.clipboard.writeText(JSON.stringify(diagnostics, null, 2)).then(() => {
    alert('Diagnostic information copied to clipboard')
  }).catch(() => {
    console.log('Terminal Diagnostics:', diagnostics)
    alert('Diagnostic information logged to console')
  })
  
  emit('diagnosticsRequested')
}

// Utility functions
const collectTerminalContext = (): TerminalContext => {
  // Try to collect context from various sources
  // This would be enhanced based on actual terminal implementation
  return {
    terminalId: props.terminalId,
    connectionState: navigator.onLine ? 'online' : 'offline',
    // Add more context collection as needed
  }
}

const categorizeTerminalError = (error: Error): string => {
  const message = error.message.toLowerCase()
  
  if (message.includes('socket') || message.includes('websocket')) {
    return 'socket_error'
  }
  if (message.includes('connection') || message.includes('disconnect')) {
    return 'connection_error'
  }
  if (message.includes('pty') || message.includes('process')) {
    return 'process_error'
  }
  if (message.includes('permission') || message.includes('access')) {
    return 'permission_error'
  }
  if (message.includes('timeout')) {
    return 'timeout_error'
  }
  if (message.includes('data') || message.includes('buffer')) {
    return 'data_error'
  }
  
  return 'unknown_error'
}

// Expose methods for parent components
defineExpose({
  reconnect: handleReconnect,
  createNew: handleCreateNew,
  runDiagnostics: handleDiagnostics,
  reset: () => errorBoundary.value?.reset(),
  hasError: computed(() => errorBoundary.value?.hasError || false)
})
</script>

<style scoped>
.terminal-error-fallback {
  background-color: #1a1a1a;
  border: 2px solid #444;
  border-radius: 8px;
  padding: 20px;
  color: #ffffff;
  max-width: 600px;
  margin: 20px auto;
}

.terminal-error-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  border-bottom: 1px solid #444;
  padding-bottom: 12px;
}

.terminal-icon {
  font-size: 32px;
}

.terminal-error-header h3 {
  margin: 0;
  color: #ff6b6b;
  font-size: 18px;
}

.error-description {
  color: #cccccc;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 16px;
}

.terminal-info {
  background-color: #2a2a2a;
  border: 1px solid #444;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 16px;
}

.info-item {
  margin-bottom: 6px;
  font-size: 12px;
}

.info-item strong {
  color: #ffffff;
  display: inline-block;
  width: 120px;
}

.terminal-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.reconnect-btn,
.new-terminal-btn,
.diagnostics-btn {
  background-color: #4a4a4a;
  color: white;
  border: 1px solid #666;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s ease;
}

.reconnect-btn:hover {
  background-color: #28a745;
  border-color: #28a745;
}

.new-terminal-btn:hover {
  background-color: #007bff;
  border-color: #007bff;
}

.diagnostics-btn:hover {
  background-color: #6c757d;
  border-color: #6c757d;
}

.reconnect-btn:active,
.new-terminal-btn:active,
.diagnostics-btn:active {
  transform: translateY(1px);
}
</style>