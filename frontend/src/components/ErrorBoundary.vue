<!--
Generic Vue Error Boundary Component for AetherTerm
Catches component errors and integrates with OpenTelemetryService
-->

<template>
  <div class="error-boundary">
    <!-- Normal content when no error -->
    <slot v-if="!hasError" />
    
    <!-- Error fallback UI -->
    <div v-else class="error-fallback">
      <div class="error-container">
        <div class="error-icon">🚨</div>
        <div class="error-content">
          <h3 class="error-title">{{ errorTitle }}</h3>
          <p class="error-message">{{ errorMessage }}</p>
          
          <!-- Error details toggle -->
          <button 
            v-if="showDetailsToggle" 
            @click="showDetails = !showDetails"
            class="details-toggle"
          >
            {{ showDetails ? '▼ Hide Details' : '▶ Show Details' }}
          </button>
          
          <!-- Detailed error information -->
          <div v-if="showDetails" class="error-details">
            <div class="detail-section">
              <strong>Error:</strong> {{ error?.name || 'Unknown' }}
            </div>
            <div class="detail-section">
              <strong>Message:</strong> {{ error?.message || 'No message' }}
            </div>
            <div v-if="componentName" class="detail-section">
              <strong>Component:</strong> {{ componentName }}
            </div>
            <div v-if="errorInfo" class="detail-section">
              <strong>Context:</strong>
              <pre class="error-context">{{ JSON.stringify(errorInfo, null, 2) }}</pre>
            </div>
            <div v-if="error?.stack" class="detail-section">
              <strong>Stack Trace:</strong>
              <pre class="error-stack">{{ error.stack }}</pre>
            </div>
          </div>
          
          <!-- Action buttons -->
          <div class="error-actions">
            <button @click="handleRetry" class="retry-btn">
              🔄 Retry
            </button>
            <button @click="handleReload" class="reload-btn">
              ↻ Reload Page
            </button>
            <button v-if="showReportButton" @click="handleReport" class="report-btn">
              📤 Report Issue
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured, computed, onMounted } from 'vue'
import { openTelemetryService, type ErrorBoundaryInfo } from '../services/OpenTelemetryService'

interface Props {
  name?: string
  fallbackTitle?: string
  fallbackMessage?: string
  showRetry?: boolean
  showReload?: boolean
  showReport?: boolean
  showDetails?: boolean
  onError?: (error: Error, errorInfo: any) => void
  onRetry?: () => void
}

const props = withDefaults(defineProps<Props>(), {
  name: 'ErrorBoundary',
  fallbackTitle: 'Something went wrong',
  fallbackMessage: 'An unexpected error occurred in this component.',
  showRetry: true,
  showReload: true,
  showReport: false,
  showDetails: false
})

// Reactive state
const hasError = ref(false)
const error = ref<Error | null>(null)
const errorInfo = ref<any>(null)
const showDetails = ref(false)
const componentName = ref<string>('')
const retryKey = ref(0)

// Computed properties
const errorTitle = computed(() => props.fallbackTitle)
const errorMessage = computed(() => {
  if (error.value?.message) {
    return `${props.fallbackMessage}: ${error.value.message}`
  }
  return props.fallbackMessage
})

const showDetailsToggle = computed(() => props.showDetails || !!error.value?.stack)
const showReportButton = computed(() => props.showReport)

// Error capture handler
onErrorCaptured((err: Error, instance: any, info: string) => {
  console.error('🚨 Error Boundary caught error:', err)
  
  // Set error state
  hasError.value = true
  error.value = err
  errorInfo.value = info
  componentName.value = instance?.$options.name || instance?.$options.__name || 'Unknown Component'
  
  // Extract component props for context (be careful with sensitive data)
  const propsData = instance?.$props ? 
    Object.keys(instance.$props).reduce((acc: Record<string, any>, key: string) => {
      const value = instance.$props[key]
      // Only include simple values, avoid functions and circular references
      if (typeof value !== 'function' && typeof value !== 'object') {
        acc[key] = value
      } else if (value && typeof value === 'object') {
        acc[key] = '[Object]'
      }
      return acc
    }, {}) : undefined

  // Create error boundary info for OpenTelemetry
  const errorBoundaryInfo: ErrorBoundaryInfo = {
    componentName: componentName.value,
    propsData,
    error: err,
    errorInfo: info,
    componentStack: info,
    errorBoundary: props.name
  }

  // Log to OpenTelemetry
  openTelemetryService.logErrorBoundary(errorBoundaryInfo)

  // Call custom error handler if provided
  if (props.onError) {
    try {
      props.onError(err, errorBoundaryInfo)
    } catch (handlerError) {
      console.error('Error in custom error handler:', handlerError)
    }
  }

  // Prevent the error from propagating further up
  return false
})

// Action handlers
const handleRetry = () => {
  console.log('🔄 Retrying component...')
  
  // Reset error state
  hasError.value = false
  error.value = null
  errorInfo.value = null
  showDetails.value = false
  
  // Force component re-render by changing key
  retryKey.value++
  
  // Log retry action
  openTelemetryService.logInfo('error_boundary_retry', {
    error_boundary: props.name,
    component: componentName.value,
    retry_count: retryKey.value
  })
  
  // Call custom retry handler if provided
  if (props.onRetry) {
    try {
      props.onRetry()
    } catch (retryError) {
      console.error('Error in custom retry handler:', retryError)
    }
  }
}

const handleReload = () => {
  console.log('↻ Reloading page...')
  
  // Log reload action
  openTelemetryService.logInfo('error_boundary_reload', {
    error_boundary: props.name,
    component: componentName.value,
    error_message: error.value?.message
  })
  
  // Small delay to ensure log is sent
  setTimeout(() => {
    window.location.reload()
  }, 100)
}

const handleReport = () => {
  console.log('📤 Reporting issue...')
  
  // Create issue report data
  const reportData = {
    error: {
      name: error.value?.name,
      message: error.value?.message,
      stack: error.value?.stack
    },
    component: componentName.value,
    errorBoundary: props.name,
    userAgent: navigator.userAgent,
    url: window.location.href,
    timestamp: new Date().toISOString()
  }
  
  // Log report action
  openTelemetryService.logInfo('error_boundary_report', {
    error_boundary: props.name,
    component: componentName.value,
    report_data: JSON.stringify(reportData).substring(0, 1000)
  })
  
  // Copy to clipboard for now (could be enhanced to send to issue tracker)
  navigator.clipboard.writeText(JSON.stringify(reportData, null, 2)).then(() => {
    alert('Error report copied to clipboard. Please paste it when reporting the issue.')
  }).catch(() => {
    alert('Failed to copy error report. Please check the console for details.')
    console.log('Error Report:', reportData)
  })
}

// Component lifecycle
onMounted(() => {
  // Log error boundary mount
  openTelemetryService.logInfo('error_boundary_mounted', {
    error_boundary: props.name
  })
})

// Expose retry method for parent components
defineExpose({
  retry: handleRetry,
  hasError: computed(() => hasError.value),
  error: computed(() => error.value),
  reset: () => {
    hasError.value = false
    error.value = null
    errorInfo.value = null
  }
})
</script>

<style scoped>
.error-boundary {
  width: 100%;
  height: 100%;
}

.error-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  padding: 20px;
  background-color: #1e1e1e;
  color: #ffffff;
  border: 1px solid #444;
  border-radius: 8px;
}

.error-container {
  max-width: 600px;
  text-align: center;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.error-content {
  text-align: left;
}

.error-title {
  color: #ff6b6b;
  font-size: 18px;
  font-weight: bold;
  margin: 0 0 8px 0;
}

.error-message {
  color: #cccccc;
  font-size: 14px;
  margin: 0 0 16px 0;
  line-height: 1.5;
}

.details-toggle {
  background: none;
  border: 1px solid #666;
  color: #cccccc;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  margin-bottom: 16px;
  transition: all 0.2s ease;
}

.details-toggle:hover {
  background-color: #333;
  border-color: #888;
}

.error-details {
  background-color: #2a2a2a;
  border: 1px solid #444;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 16px;
  font-size: 12px;
}

.detail-section {
  margin-bottom: 8px;
}

.detail-section strong {
  color: #ffffff;
  display: inline-block;
  width: 80px;
}

.error-context,
.error-stack {
  background-color: #1a1a1a;
  border: 1px solid #444;
  border-radius: 3px;
  padding: 8px;
  margin-top: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 10px;
  color: #cccccc;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.error-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 16px;
}

.retry-btn,
.reload-btn,
.report-btn {
  background-color: #4a4a4a;
  color: white;
  border: 1px solid #666;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s ease;
}

.retry-btn:hover {
  background-color: #28a745;
  border-color: #28a745;
}

.reload-btn:hover {
  background-color: #17a2b8;
  border-color: #17a2b8;
}

.report-btn:hover {
  background-color: #6c757d;
  border-color: #6c757d;
}

.retry-btn:active,
.reload-btn:active,
.report-btn:active {
  transform: translateY(1px);
}
</style>