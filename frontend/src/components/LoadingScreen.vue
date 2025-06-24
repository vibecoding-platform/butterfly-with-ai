<template>
  <div class="loading-screen">
    <div class="loading-container">
      <!-- Loading Animation -->
      <div class="loading-animation">
        <div class="loading-spinner"></div>
        <div class="loading-pulse"></div>
      </div>
      
      <!-- Loading Title -->
      <h1 class="loading-title">🚀 Initializing AetherTerm</h1>
      
      <!-- Loading Message -->
      <p class="loading-message">{{ loadingMessage }}</p>
      
      <!-- Progress Indicator -->
      <div class="progress-container">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <div class="progress-text">{{ progressPercent }}%</div>
      </div>
      
      <!-- Loading Steps -->
      <div class="loading-steps">
        <div 
          v-for="(step, index) in loadingSteps" 
          :key="index"
          class="loading-step"
          :class="{
            'step-completed': step.completed,
            'step-active': step.active,
            'step-pending': !step.completed && !step.active
          }"
        >
          <div class="step-icon">
            <div v-if="step.completed" class="step-check">✓</div>
            <div v-else-if="step.active" class="step-spinner"></div>
            <div v-else class="step-dot"></div>
          </div>
          <span class="step-text">{{ step.text }}</span>
        </div>
      </div>
      
      <!-- Timeout Warning -->
      <div v-if="showTimeoutWarning" class="timeout-warning">
        <p class="warning-text">
          ⚠️ Initialization is taking longer than expected...
        </p>
        <p class="warning-subtext">
          This may indicate a connection issue. Please wait or try refreshing the page.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface LoadingStep {
  text: string
  completed: boolean
  active: boolean
}

const props = withDefaults(defineProps<{
  initialMessage?: string
  showProgress?: boolean
  timeout?: number
}>(), {
  initialMessage: 'Starting services...',
  showProgress: true,
  timeout: 30000
})

const emit = defineEmits<{
  timeout: []
}>()

// Loading state
const loadingMessage = ref(props.initialMessage)
const progressPercent = ref(0)
const showTimeoutWarning = ref(false)
const startTime = Date.now()

// Loading steps
const loadingSteps = ref<LoadingStep[]>([
  { text: 'Connecting to server...', completed: false, active: true },
  { text: 'Initializing Socket.IO...', completed: false, active: false },
  { text: 'Loading workspace...', completed: false, active: false },
  { text: 'Setting up AI services...', completed: false, active: false },
  { text: 'Ready!', completed: false, active: false }
])

// Progress simulation
const progressInterval = ref<number | null>(null)
const timeoutHandle = ref<number | null>(null)

const simulateProgress = () => {
  const elapsed = Date.now() - startTime
  const expectedDuration = props.timeout * 0.8 // Complete progress at 80% of timeout
  
  if (elapsed < expectedDuration) {
    progressPercent.value = Math.min(95, (elapsed / expectedDuration) * 100)
    
    // Update active step
    const stepProgress = Math.floor((progressPercent.value / 100) * loadingSteps.value.length)
    loadingSteps.value.forEach((step, index) => {
      if (index < stepProgress) {
        step.completed = true
        step.active = false
      } else if (index === stepProgress) {
        step.completed = false
        step.active = true
      } else {
        step.completed = false
        step.active = false
      }
    })
    
    // Update loading message based on current step
    const currentStep = loadingSteps.value[stepProgress]
    if (currentStep) {
      loadingMessage.value = currentStep.text
    }
  } else {
    // Show timeout warning
    showTimeoutWarning.value = true
    loadingMessage.value = 'Connection timeout - please wait...'
  }
}

// Timeout handling
const handleTimeout = () => {
  showTimeoutWarning.value = true
  loadingMessage.value = 'Initialization timed out'
  emit('timeout')
}

// Methods for external control
defineExpose({
  setProgress: (percent: number) => {
    progressPercent.value = Math.min(100, Math.max(0, percent))
  },
  setMessage: (message: string) => {
    loadingMessage.value = message
  },
  completeStep: (stepIndex: number) => {
    if (stepIndex < loadingSteps.value.length) {
      loadingSteps.value[stepIndex].completed = true
      loadingSteps.value[stepIndex].active = false
      
      // Activate next step
      if (stepIndex + 1 < loadingSteps.value.length) {
        loadingSteps.value[stepIndex + 1].active = true
      }
    }
  }
})

onMounted(() => {
  // Start progress simulation
  if (props.showProgress) {
    progressInterval.value = window.setInterval(simulateProgress, 200)
  }
  
  // Set timeout
  if (props.timeout > 0) {
    timeoutHandle.value = window.setTimeout(handleTimeout, props.timeout)
  }
})

onUnmounted(() => {
  if (progressInterval.value) {
    clearInterval(progressInterval.value)
  }
  if (timeoutHandle.value) {
    clearTimeout(timeoutHandle.value)
  }
})
</script>

<style scoped>
.loading-screen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9998;
  padding: 20px;
}

.loading-container {
  text-align: center;
  max-width: 500px;
  width: 100%;
}

.loading-animation {
  position: relative;
  margin-bottom: 32px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-spinner {
  width: 80px;
  height: 80px;
  border: 3px solid rgba(59, 130, 246, 0.3);
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-pulse {
  position: absolute;
  width: 120px;
  height: 120px;
  border: 2px solid rgba(59, 130, 246, 0.2);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.5;
  }
}

.loading-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 16px 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.loading-message {
  font-size: 1.25rem;
  color: #cbd5e1;
  margin: 0 0 32px 0;
  min-height: 1.5rem;
}

.progress-container {
  margin-bottom: 32px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #06b6d4);
  border-radius: 4px;
  transition: width 0.3s ease;
  position: relative;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.progress-text {
  font-size: 0.875rem;
  color: #94a3b8;
  font-weight: 600;
}

.loading-steps {
  text-align: left;
  margin-bottom: 32px;
}

.loading-step {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  transition: all 0.3s ease;
}

.step-icon {
  width: 24px;
  height: 24px;
  margin-right: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-check {
  width: 20px;
  height: 20px;
  background: #10b981;
  border-radius: 50%;
  color: white;
  font-size: 12px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(59, 130, 246, 0.3);
  border-top: 2px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.step-dot {
  width: 8px;
  height: 8px;
  background: #64748b;
  border-radius: 50%;
}

.step-text {
  font-size: 1rem;
  transition: color 0.3s ease;
}

.step-completed .step-text {
  color: #10b981;
}

.step-active .step-text {
  color: #3b82f6;
  font-weight: 600;
}

.step-pending .step-text {
  color: #64748b;
}

.timeout-warning {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  padding: 16px;
  margin-top: 24px;
}

.warning-text {
  color: #fca5a5;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.warning-subtext {
  color: #fecaca;
  font-size: 0.875rem;
  margin: 0;
}

/* Responsive */
@media (max-width: 640px) {
  .loading-container {
    padding: 24px;
  }
  
  .loading-title {
    font-size: 2rem;
  }
  
  .loading-message {
    font-size: 1.125rem;
  }
  
  .loading-animation {
    height: 100px;
  }
  
  .loading-spinner {
    width: 60px;
    height: 60px;
  }
  
  .loading-pulse {
    width: 100px;
    height: 100px;
  }
}
</style>