<!--
Workspace-specific Error Boundary Component for AetherTerm
Specialized error handling for workspace and session management components
-->

<template>
  <ErrorBoundary
    name="WorkspaceErrorBoundary"
    :fallback-title="errorTitle"
    :fallback-message="errorMessage"
    :show-retry="true"
    :show-reload="true"
    :show-report="true"
    :show-details="true"
    :on-error="handleWorkspaceError"
    :on-retry="handleWorkspaceRetry"
    ref="errorBoundary"
  >
    <slot />
    
    <!-- Workspace-specific error fallback -->
    <template v-if="showWorkspaceFallback">
      <div class="workspace-error-fallback">
        <div class="workspace-error-header">
          <div class="workspace-icon">🏗️</div>
          <h3>Workspace Error</h3>
        </div>
        
        <div class="workspace-error-content">
          <p class="error-description">
            {{ workspaceErrorDescription }}
          </p>
          
          <div class="workspace-info" v-if="workspaceContext">
            <div class="info-item">
              <strong>Session ID:</strong> {{ workspaceContext.sessionId }}
            </div>
            <div class="info-item" v-if="workspaceContext.activeTabId">
              <strong>Active Tab:</strong> {{ workspaceContext.activeTabId }}
            </div>
            <div class="info-item" v-if="workspaceContext.tabCount !== undefined">
              <strong>Tab Count:</strong> {{ workspaceContext.tabCount }}
            </div>
            <div class="info-item" v-if="workspaceContext.socketState">
              <strong>Socket State:</strong> {{ workspaceContext.socketState }}
            </div>
            <div class="info-item" v-if="workspaceContext.lastOperation">
              <strong>Last Operation:</strong> {{ workspaceContext.lastOperation }}
            </div>
          </div>
          
          <div class="workspace-actions">
            <button @click="handleRefreshWorkspace" class="refresh-btn">
              🔄 Refresh Workspace
            </button>
            <button @click="handleResetSession" class="reset-btn">
              🔄 Reset Session
            </button>
            <button @click="handleSafeMode" class="safe-mode-btn">
              🛡️ Safe Mode
            </button>
            <button @click="handleExportState" class="export-btn">
              📥 Export State
            </button>
          </div>
        </div>
      </div>
    </template>
  </ErrorBoundary>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import ErrorBoundary from './ErrorBoundary.vue'
import { openTelemetryService } from '../services/OpenTelemetryService'

interface WorkspaceContext {
  sessionId?: string
  activeTabId?: string
  tabCount?: number
  socketState?: string
  lastOperation?: string
  workspaceState?: 'loading' | 'loaded' | 'error' | 'empty'
  syncInProgress?: boolean
}

interface Props {
  sessionId?: string
  fallbackMode?: 'generic' | 'workspace'
  onWorkspaceError?: (error: Error, context: WorkspaceContext) => void
  onRefresh?: () => Promise<void>
  onReset?: () => Promise<void>
  onSafeMode?: () => Promise<void>
}

const props = withDefaults(defineProps<Props>(), {
  fallbackMode: 'generic'
})

const emit = defineEmits<{
  workspaceError: [error: Error, context: WorkspaceContext]
  refreshRequested: []
  resetRequested: []
  safeModeRequested: []
  exportRequested: [state: any]
}>()

// Reactive state
const errorBoundary = ref<InstanceType<typeof ErrorBoundary> | null>(null)
const workspaceContext = ref<WorkspaceContext>({})
const lastError = ref<Error | null>(null)
const isWorkspaceSpecificError = ref(false)

// Computed properties
const showWorkspaceFallback = computed(() => 
  isWorkspaceSpecificError.value && props.fallbackMode === 'workspace'
)

const errorTitle = computed(() => {
  if (isWorkspaceSpecificError.value) {
    return 'Workspace Session Error'
  }
  return 'Workspace Component Error'
})

const errorMessage = computed(() => {
  if (isWorkspaceSpecificError.value) {
    return 'The workspace session has encountered an issue and may need to be refreshed or reset.'
  }
  return 'An error occurred in the workspace management component.'
})

const workspaceErrorDescription = computed(() => {
  if (!lastError.value) return 'Unknown workspace error'
  
  const message = lastError.value.message.toLowerCase()
  
  if (message.includes('socket') || message.includes('connection')) {
    return 'The workspace lost connection to the server. This might affect tab management and synchronization.'
  }
  
  if (message.includes('session') || message.includes('sync')) {
    return 'There was an issue with session management or workspace synchronization. Data might be out of sync.'
  }
  
  if (message.includes('tab') || message.includes('pane')) {
    return 'An error occurred while managing tabs or panes. Some workspace state might be corrupted.'
  }
  
  if (message.includes('storage') || message.includes('persist')) {
    return 'There was a problem accessing local storage or persisting workspace state.'
  }
  
  if (message.includes('permission') || message.includes('access')) {
    return 'Permission was denied while accessing workspace resources or browser APIs.'
  }
  
  return `Workspace error: ${lastError.value.message}`
})

// Error handling
const handleWorkspaceError = (error: Error, errorInfo: any) => {
  console.error('🏗️ Workspace Error Boundary caught error:', error)
  
  lastError.value = error
  
  // Determine if this is a workspace-specific error
  const errorMessage = error.message.toLowerCase()
  isWorkspaceSpecificError.value = 
    errorMessage.includes('workspace') ||
    errorMessage.includes('session') ||
    errorMessage.includes('tab') ||
    errorMessage.includes('pane') ||
    errorMessage.includes('sync') ||
    errorMessage.includes('socket') ||
    errorMessage.includes('storage')
  
  // Collect workspace context
  workspaceContext.value = collectWorkspaceContext()
  
  // Log workspace-specific error information
  openTelemetryService.logError('workspace_component_error', error, {
    session_id: props.sessionId,
    workspace_context: workspaceContext.value,
    is_workspace_specific: isWorkspaceSpecificError.value,
    error_type: categorizeWorkspaceError(error)
  })
  
  // Create workspace error trace
  const span = openTelemetryService.createSpan('workspace.error_handling', {
    'workspace.session_id': props.sessionId,
    'workspace.error_category': categorizeWorkspaceError(error),
    'workspace.context': JSON.stringify(workspaceContext.value),
    'error.is_workspace_specific': isWorkspaceSpecificError.value
  })
  
  if (span) {
    span.recordException(error)
    span.end()
  }
  
  // Call custom error handler
  if (props.onWorkspaceError) {
    props.onWorkspaceError(error, workspaceContext.value)
  }
  
  // Emit error event
  emit('workspaceError', error, workspaceContext.value)
}

const handleWorkspaceRetry = () => {
  console.log('🔄 Retrying workspace component...')
  
  // Reset workspace-specific state
  isWorkspaceSpecificError.value = false
  workspaceContext.value = {}
  lastError.value = null
  
  // Log retry action
  openTelemetryService.logInfo('workspace_error_boundary_retry', {
    session_id: props.sessionId,
    retry_type: 'component_retry'
  })
}

// Workspace-specific actions
const handleRefreshWorkspace = async () => {
  console.log('🔄 Refreshing workspace...')
  
  try {
    // Log refresh attempt
    openTelemetryService.logInfo('workspace_refresh_attempt', {
      session_id: props.sessionId,
      context: workspaceContext.value,
      trigger: 'error_recovery'
    })
    
    if (props.onRefresh) {
      await props.onRefresh()
    }
    
    // Reset error boundary after successful refresh
    errorBoundary.value?.reset()
    
    emit('refreshRequested')
    
  } catch (error) {
    console.error('Failed to refresh workspace:', error)
    openTelemetryService.logError('workspace_refresh_failed', error as Error, {
      session_id: props.sessionId
    })
  }
}

const handleResetSession = async () => {
  console.log('🔄 Resetting session...')
  
  if (!confirm('Are you sure you want to reset the session? This will clear all tabs and unsaved work.')) {
    return
  }
  
  try {
    // Log reset attempt
    openTelemetryService.logInfo('workspace_reset_attempt', {
      session_id: props.sessionId,
      context: workspaceContext.value,
      trigger: 'error_recovery'
    })
    
    if (props.onReset) {
      await props.onReset()
    }
    
    // Clear local storage related to workspace
    const keysToRemove = Object.keys(localStorage).filter(key => 
      key.startsWith('aetherterm-') || key.startsWith('workspace-')
    )
    keysToRemove.forEach(key => localStorage.removeItem(key))
    
    // Reset error boundary after reset
    errorBoundary.value?.reset()
    
    emit('resetRequested')
    
  } catch (error) {
    console.error('Failed to reset session:', error)
    openTelemetryService.logError('workspace_reset_failed', error as Error, {
      session_id: props.sessionId
    })
  }
}

const handleSafeMode = async () => {
  console.log('🛡️ Entering safe mode...')
  
  try {
    // Log safe mode activation
    openTelemetryService.logInfo('workspace_safe_mode_activation', {
      session_id: props.sessionId,
      context: workspaceContext.value,
      trigger: 'error_recovery'
    })
    
    if (props.onSafeMode) {
      await props.onSafeMode()
    }
    
    // Reset error boundary for safe mode
    errorBoundary.value?.reset()
    
    emit('safeModeRequested')
    
  } catch (error) {
    console.error('Failed to enter safe mode:', error)
    openTelemetryService.logError('workspace_safe_mode_failed', error as Error, {
      session_id: props.sessionId
    })
  }
}

const handleExportState = () => {
  console.log('📥 Exporting workspace state...')
  
  // Collect comprehensive workspace state
  const workspaceState = {
    sessionId: props.sessionId,
    context: workspaceContext.value,
    error: lastError.value ? {
      name: lastError.value.name,
      message: lastError.value.message,
      stack: lastError.value.stack
    } : null,
    timestamp: new Date().toISOString(),
    localStorage: Object.keys(localStorage).reduce((acc: Record<string, string>, key) => {
      if (key.startsWith('aetherterm-') || key.startsWith('workspace-')) {
        acc[key] = localStorage.getItem(key) || ''
      }
      return acc
    }, {}),
    sessionStorage: Object.keys(sessionStorage).reduce((acc: Record<string, string>, key) => {
      if (key.startsWith('aetherterm-') || key.startsWith('workspace-')) {
        acc[key] = sessionStorage.getItem(key) || ''
      }
      return acc
    }, {}),
    browser: {
      userAgent: navigator.userAgent,
      language: navigator.language,
      online: navigator.onLine,
      cookieEnabled: navigator.cookieEnabled
    },
    page: {
      url: window.location.href,
      title: document.title,
      referrer: document.referrer
    }
  }
  
  // Log export action
  openTelemetryService.logInfo('workspace_state_export', {
    session_id: props.sessionId,
    export_size: JSON.stringify(workspaceState).length
  })
  
  // Copy to clipboard
  navigator.clipboard.writeText(JSON.stringify(workspaceState, null, 2)).then(() => {
    alert('Workspace state exported to clipboard')
  }).catch(() => {
    console.log('Workspace State Export:', workspaceState)
    alert('Workspace state logged to console')
  })
  
  emit('exportRequested', workspaceState)
}

// Utility functions
const collectWorkspaceContext = (): WorkspaceContext => {
  // Try to collect context from various sources
  // This would be enhanced based on actual workspace implementation
  return {
    sessionId: props.sessionId,
    socketState: navigator.onLine ? 'online' : 'offline',
    // Add more context collection as needed
  }
}

const categorizeWorkspaceError = (error: Error): string => {
  const message = error.message.toLowerCase()
  
  if (message.includes('socket') || message.includes('websocket')) {
    return 'socket_error'
  }
  if (message.includes('session') || message.includes('sync')) {
    return 'session_error'
  }
  if (message.includes('tab') || message.includes('pane')) {
    return 'tab_management_error'
  }
  if (message.includes('storage') || message.includes('persist')) {
    return 'storage_error'
  }
  if (message.includes('permission') || message.includes('access')) {
    return 'permission_error'
  }
  if (message.includes('network') || message.includes('connection')) {
    return 'network_error'
  }
  if (message.includes('timeout')) {
    return 'timeout_error'
  }
  
  return 'unknown_error'
}

// Expose methods for parent components
defineExpose({
  refresh: handleRefreshWorkspace,
  reset: handleResetSession,
  safeMode: handleSafeMode,
  exportState: handleExportState,
  resetBoundary: () => errorBoundary.value?.reset(),
  hasError: computed(() => errorBoundary.value?.hasError || false)
})
</script>

<style scoped>
.workspace-error-fallback {
  background-color: #1a1a1a;
  border: 2px solid #444;
  border-radius: 8px;
  padding: 20px;
  color: #ffffff;
  max-width: 700px;
  margin: 20px auto;
}

.workspace-error-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  border-bottom: 1px solid #444;
  padding-bottom: 12px;
}

.workspace-icon {
  font-size: 32px;
}

.workspace-error-header h3 {
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

.workspace-info {
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

.workspace-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.refresh-btn,
.reset-btn,
.safe-mode-btn,
.export-btn {
  background-color: #4a4a4a;
  color: white;
  border: 1px solid #666;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s ease;
  text-align: center;
}

.refresh-btn:hover {
  background-color: #28a745;
  border-color: #28a745;
}

.reset-btn:hover {
  background-color: #dc3545;
  border-color: #dc3545;
}

.safe-mode-btn:hover {
  background-color: #ffc107;
  border-color: #ffc107;
  color: #000;
}

.export-btn:hover {
  background-color: #17a2b8;
  border-color: #17a2b8;
}

.refresh-btn:active,
.reset-btn:active,
.safe-mode-btn:active,
.export-btn:active {
  transform: translateY(1px);
}

@media (max-width: 600px) {
  .workspace-actions {
    grid-template-columns: 1fr;
  }
}
</style>