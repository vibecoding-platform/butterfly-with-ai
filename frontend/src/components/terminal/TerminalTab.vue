<template>
  <div class="terminal-tab-container">
    <!-- Terminal Status Indicator for Inventory Terminals -->
    <div 
      v-if="subType === 'inventory' && showStatusBar"
      class="terminal-status-bar"
    >
      <div class="status-indicator">
        <span class="status-dot connecting"></span>
        <span class="status-text">Initializing terminal...</span>
      </div>
      <div v-if="showProgress" class="progress-bar">
        <div 
          class="progress-fill"
          :style="{ width: '0%' }"
        ></div>
      </div>
    </div>
    
    <!-- Xterm.js Container -->
    <div 
      :id="`terminal-${tabId}`" 
      class="xterm-container"
      @click="handleTerminalClick"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { Terminal, type ITheme } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { useAetherTerminalServiceStore } from '../../stores/aetherTerminalServiceStore'
import { useTerminalTabStore } from '../../stores/terminalTabStore'

interface Props {
  tabId: string
  subType?: 'pure' | 'inventory' | 'agent' | 'main-agent'
}

interface Emits {
  (e: 'click'): void
  (e: 'terminal-initialized', terminal: Terminal): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Terminal instance and addons
const terminal = ref<Terminal | null>(null)
const fitAddon = ref<FitAddon | null>(null)
const terminalEl = ref<HTMLElement | null>(null)

// Status bar visibility (can be controlled by parent or internal logic)
const showStatusBar = ref(false)
const showProgress = ref(false)

// Store references
const terminalStore = useAetherTerminalServiceStore()
const terminalTabStore = useTerminalTabStore()

// Terminal initialization
const initializeTerminal = async () => {
  console.log('Initializing terminal for tab:', props.tabId)
  
  await nextTick()
  terminalEl.value = document.getElementById(`terminal-${props.tabId}`)
  
  if (!terminalEl.value) {
    console.error('Terminal element not found:', `terminal-${props.tabId}`)
    return
  }

  // Create simple xterm.js instance
  terminal.value = new Terminal({
    fontSize: 14,
    fontFamily: 'Monaco, Menlo, "Courier New", monospace',
    theme: {
      background: '#1e1e1e',
      foreground: '#ffffff',
      cursor: '#ffffff'
    } as ITheme,
    cursorBlink: true,
    scrollback: 1000,
    convertEol: true
  })

  // Create and attach fit addon
  fitAddon.value = new FitAddon()
  terminal.value.loadAddon(fitAddon.value)

  // Open terminal
  terminal.value.open(terminalEl.value)
  
  // Fit terminal to container
  fitAddon.value.fit()

  // Setup event handlers
  setupTerminalEventHandlers()
  
  // Connect to backend
  if (terminalStore.socket && terminalStore.session.id) {
    if (!callbackRegistered.value) {
      connectTerminal()
    }
  } else {
    await terminalStore.connect()
    connectTerminal()
  }
  
  // Focus terminal
  terminal.value.focus()
  emit('terminal-initialized', terminal.value)
}

const setupTerminalEventHandlers = () => {
  if (!terminal.value) return

  // Handle terminal resize
  terminal.value.onResize((dimensions) => {
    console.log('📐 Terminal resized:', dimensions)
    
    if (terminalStore.socket && terminalStore.session.id) {
      terminalStore.socket.emit('terminal_resize', {
        session: terminalStore.session.id,
        cols: dimensions.cols,
        rows: dimensions.rows
      })
    }
  })

  // Handle user input
  terminal.value.onData((data) => {
    if (terminalStore.socket && terminalStore.session.id) {
      console.log('📤 Sending terminal input:', { session: terminalStore.session.id, data: data.substring(0, 20) + '...' })
      terminalStore.socket.emit('terminal_input', {
        session: terminalStore.session.id,
        data: data
      })
    } else {
      console.warn('⚠️ Cannot send input - no socket or session')
    }
  })
}

// Track if callback is already registered to prevent duplicates
const callbackRegistered = ref(false)
const outputCallbackRef = ref<((data: string) => void) | null>(null)
const sessionRequested = ref(false)

const connectTerminal = () => {
  console.log('Connecting terminal for tab:', props.tabId)
  
  if (!terminalStore.socket || !terminal.value) {
    console.error('Cannot connect - missing socket or terminal')
    return
  }

  // Only register callback once per component instance
  if (!callbackRegistered.value) {
    const outputCallback = (data: string) => {
      if (terminal.value) {
        terminal.value.write(data)
      }
    }
    
    terminalStore.onShellOutput(outputCallback)
    callbackRegistered.value = true
    outputCallbackRef.value = outputCallback
  }

  // Only request session once per component instance
  if (!sessionRequested.value) {
    // Generate session ID based on tab ID for consistency
    const sessionId = `terminal_${props.tabId}_${Date.now()}`
    
    // Check if there's an existing session to resume for this specific tab
    const existingSession = terminalTabStore.getTabSession(props.tabId)
    if (existingSession) {
      console.log('Resuming existing session for tab:', props.tabId, existingSession)
      terminalStore.socket.emit('resume_terminal', {
        sessionId: existingSession,
        tabId: props.tabId,
        subType: props.subType,
        cols: terminal.value?.cols || 80,
        rows: terminal.value?.rows || 24
      })
    } else {
      console.log('Creating new session for tab:', props.tabId, sessionId)
      // Store session ID for this tab
      terminalTabStore.setTabSession(props.tabId, sessionId)
      
      terminalStore.socket.emit('create_terminal', {
        session: sessionId,
        tabId: props.tabId,
        subType: props.subType,
        cols: terminal.value?.cols || 80,
        rows: terminal.value?.rows || 24
      })
    }
    sessionRequested.value = true
  }
}

const handleTerminalClick = () => {
  if (terminal.value) {
    terminal.value.focus()
  }
  emit('click')
}



onMounted(() => {
  console.log('Terminal mounted for tab:', props.tabId, 'subType:', props.subType)
  initializeTerminal()
})

onUnmounted(() => {
  console.log('Terminal unmounted for tab:', props.tabId)
  
  try {
    // Clean up callback registration
    if (outputCallbackRef.value && terminalStore) {
      terminalStore.offShellOutput(outputCallbackRef.value)
      outputCallbackRef.value = null
      callbackRegistered.value = false
      sessionRequested.value = false
    }
    
    // Dispose fitAddon first if it exists and is loaded
    if (fitAddon.value && terminal.value) {
      try {
        fitAddon.value.dispose()
      } catch (e) {
        console.warn('FitAddon disposal warning:', e)
      }
    }
    
    // Then dispose terminal
    if (terminal.value) {
      terminal.value.dispose()
    }
  } catch (error) {
    console.error('Error during terminal cleanup:', error)
  }
})

// Expose terminal instance for external use
defineExpose({
  terminal: () => terminal.value
})
</script>

<style scoped lang="scss">
@import '../../assets/styles/base.scss';

.terminal-tab-container {
  @include flex-column;
  flex: 1;
  overflow: hidden;
}

.terminal-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-sm $spacing-md;
  background-color: var(--color-bg-secondary);
  border-bottom: $border-width solid var(--color-border-primary);
  min-height: 32px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  
  &.connecting {
    background-color: var(--color-warning);
    animation: pulse 2s infinite;
  }
  
  &.ready {
    background-color: var(--color-success);
  }
}

.status-text {
  font-size: $font-size-sm;
  color: var(--color-text-primary);
  font-weight: $font-weight-medium;
}

.progress-bar {
  width: 120px;
  height: 4px;
  background-color: var(--color-bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: var(--color-primary);
  transition: width 0.3s ease;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.xterm-container {
  flex: 1;
  min-height: 300px;
  background-color: #1e1e1e;
  
  :deep(.xterm) {
    height: 100%;
    
    &:focus {
      outline: none;
    }
  }
}
</style>