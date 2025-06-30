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
  console.log('=== INITIALIZING TERMINAL ===')
  console.log('Tab ID:', props.tabId)
  console.log('Sub Type:', props.subType)
  
  await nextTick()
  terminalEl.value = document.getElementById(`terminal-${props.tabId}`)
  
  if (!terminalEl.value) {
    console.error('❌ Terminal element not found:', `terminal-${props.tabId}`)
    console.log('All available elements with "terminal" in ID:', 
      Array.from(document.querySelectorAll('[id*="terminal"]')).map(el => el.id)
    )
    return
  }
  
  console.log('✅ Terminal element found:', terminalEl.value, 'for tab:', props.tabId)
  console.log('Element dimensions:', {
    width: terminalEl.value.offsetWidth,
    height: terminalEl.value.offsetHeight,
    display: getComputedStyle(terminalEl.value).display,
    visibility: getComputedStyle(terminalEl.value).visibility
  })

  // Create xterm.js instance with enhanced configuration
  terminal.value = new Terminal({
    fontSize: 14,
    fontFamily: '"SF Mono", Monaco, Menlo, "Cascadia Code", "Fira Code", "JetBrains Mono", Consolas, "Courier New", monospace',
    fontWeight: 'normal',
    fontWeightBold: 'bold',
    letterSpacing: 0,
    lineHeight: 1.0,
    theme: {
      background: '#1e1e1e',
      foreground: '#cccccc',
      cursor: '#ffffff',
      cursorAccent: '#000000',
      selectionBackground: '#264f78',
      selectionForeground: '#ffffff',
      black: '#000000',
      red: '#cd3131',
      green: '#0dbc79',
      yellow: '#e5e510',
      blue: '#2472c8',
      magenta: '#bc3fbc',
      cyan: '#11a8cd',
      white: '#e5e5e5',
      brightBlack: '#666666',
      brightRed: '#f14c4c',
      brightGreen: '#23d18b',
      brightYellow: '#f5f543',
      brightBlue: '#3b8eea',
      brightMagenta: '#d670d6',
      brightCyan: '#29b8db',
      brightWhite: '#e5e5e5'
    } as ITheme,
    cursorBlink: true,
    cursorStyle: 'block',
    cursorWidth: 1,
    scrollback: 10000,
    tabStopWidth: 4,
    convertEol: true,
    disableStdin: false,
    allowTransparency: false,
    allowProposedApi: true,
    altClickMovesCursor: true,
    macOptionIsMeta: true,
    rightClickSelectsWord: true,
    screenReaderMode: false,
    scrollOnUserInput: true,
    fastScrollModifier: 'alt',
    fastScrollSensitivity: 5,
    wordSeparator: ' ()[]{}\'"`.,;'
  })

  // Create and attach fit addon
  fitAddon.value = new FitAddon()
  terminal.value.loadAddon(fitAddon.value)

  console.log('🔧 Opening terminal in DOM element...')
  // Open terminal in the container
  terminal.value.open(terminalEl.value)
  console.log('✅ Terminal opened')
  
  // Fit terminal to container
  setTimeout(() => {
    if (fitAddon.value) {
      console.log('🔧 Fitting terminal to container...')
      fitAddon.value.fit()
      console.log('✅ Terminal fitted, dimensions:', {
        cols: terminal.value?.cols,
        rows: terminal.value?.rows
      })
    }
  }, 100)

  // Setup event handlers
  console.log('🔧 Setting up terminal event handlers...')
  setupTerminalEventHandlers()
  console.log('✅ Event handlers set up')
  
  // Connect to backend
  console.log('🔧 Connecting to backend...')
  if (terminalStore.socket && terminalStore.session.id) {
    console.log('Using existing session:', terminalStore.session.id)
    // Only connect if callback isn't already registered
    if (!callbackRegistered.value) {
      connectTerminal()
    } else {
      console.log('ℹ️ Callback already registered, skipping connect')
    }
  } else {
    console.log('Creating new connection for tab:', props.tabId)
    await terminalStore.connect()
    connectTerminal()
  }
  console.log('✅ Backend connection initiated')
  
  // Focus the terminal and emit initialized event
  if (terminal.value) {
    // Focus terminal after a short delay to ensure DOM is ready
    setTimeout(() => {
      if (terminal.value) {
        terminal.value.focus()
        console.log('🎯 Terminal focused')
      }
    }, 100)
    
    emit('terminal-initialized', terminal.value)
    console.log('📡 Terminal initialized event emitted')
  }
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
  console.log('=== CONNECTING TERMINAL ===')
  console.log('Socket exists:', !!terminalStore.socket)
  console.log('Terminal exists:', !!terminal.value)
  console.log('Callback already registered:', callbackRegistered.value)
  
  if (!terminalStore.socket || !terminal.value) {
    console.error('❌ Cannot connect - missing socket or terminal')
    return
  }

  // Only register callback once per component instance
  if (!callbackRegistered.value) {
    console.log('🔧 Setting up output callback...')
    const outputCallback = (data: string) => {
      if (terminal.value) {
        console.log('✅ Writing data to terminal via callback:', data.substring(0, 50) + '...')
        terminal.value.write(data)
      }
    }
    
    terminalStore.onShellOutput(outputCallback)
    callbackRegistered.value = true
    
    // Store callback reference for cleanup
    outputCallbackRef.value = outputCallback
    console.log('✅ Callback registered and stored')
  } else {
    console.log('ℹ️ Callback already registered, skipping')
  }

  // Only request session once per component instance
  if (!sessionRequested.value) {
    console.log('🔧 Requesting new session...')
    terminalStore.socket.emit('create_terminal', {
      tabId: props.tabId,
      subType: props.subType,
      cols: terminal.value?.cols || 80,
      rows: terminal.value?.rows || 24
    })
    sessionRequested.value = true
    console.log('✅ Session request sent')
  } else {
    console.log('ℹ️ Session already requested, skipping')
  }
}

const handleTerminalClick = () => {
  if (terminal.value) {
    terminal.value.focus()
  }
  emit('click')
}

// Watch for session changes (only when initializing)
watch(() => terminalStore.session.id, (newSessionId, oldSessionId) => {
  console.log('🔄 Session ID changed:', {
    old: oldSessionId,
    new: newSessionId,
    terminalExists: !!terminal.value,
    callbackAlreadyRegistered: callbackRegistered.value,
    sessionRequested: sessionRequested.value
  })
  
  // Only register callback once when we first get a valid session
  if (newSessionId && terminal.value && !callbackRegistered.value && !sessionRequested.value) {
    console.log('✅ First session received, registering callback only:', newSessionId)
    
    const outputCallback = (data: string) => {
      if (terminal.value) {
        console.log('✅ Writing data to terminal via callback:', data.substring(0, 50) + '...')
        terminal.value.write(data)
      }
    }
    
    terminalStore.onShellOutput(outputCallback)
    callbackRegistered.value = true
    outputCallbackRef.value = outputCallback
    console.log('✅ Callback registered for session:', newSessionId)
  } else {
    console.log('ℹ️ Skipping session change handling - already initialized or missing requirements')
  }
})

onMounted(() => {
  console.log('🟢 TerminalTab MOUNTED for tab:', props.tabId, 'subType:', props.subType)
  initializeTerminal()
})

onUnmounted(() => {
  console.log('🔴 TerminalTab UNMOUNTED for tab:', props.tabId)
  
  try {
    // Clean up callback registration
    if (outputCallbackRef.value && terminalStore) {
      console.log('🔧 Cleaning up output callback')
      terminalStore.offShellOutput(outputCallbackRef.value)
      outputCallbackRef.value = null
      callbackRegistered.value = false
      sessionRequested.value = false
      console.log('✅ Callback cleaned up')
    }
    
    // Dispose fitAddon first if it exists and is loaded
    if (fitAddon.value && terminal.value) {
      try {
        fitAddon.value.dispose()
        console.log('✅ FitAddon disposed')
      } catch (e) {
        console.warn('FitAddon disposal warning:', e)
      }
    }
    
    // Then dispose terminal
    if (terminal.value) {
      console.log('🔧 Disposing terminal instance')
      terminal.value.dispose()
      console.log('✅ Terminal disposed')
    }
  } catch (error) {
    console.error('Error during terminal cleanup:', error)
  }
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
  border-top: $border-width solid var(--color-border-primary);
  min-height: 300px;
  background-color: var(--color-terminal-bg);
  overflow: hidden;
  
  // Hide xterm.js internal textarea that shouldn't be visible
  :deep(.xterm-helper-textarea) {
    position: absolute !important;
    left: -9999px !important;
    top: -9999px !important;
    opacity: 0 !important;
    pointer-events: none !important;
    z-index: -1 !important;
  }
  
  // Ensure terminal screen is properly displayed
  :deep(.xterm-screen) {
    position: relative;
    z-index: 1;
  }
  
  // Focus handling for terminal
  :deep(.xterm) {
    height: 100%;
    
    &:focus {
      outline: none;
    }
  }
  
  // Make sure viewport fills container
  :deep(.xterm-viewport) {
    background-color: transparent;
  }
}
</style>