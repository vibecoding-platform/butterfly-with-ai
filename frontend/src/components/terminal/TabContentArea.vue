<template>
  <div class="terminal-view" @contextmenu.prevent>
    <!-- Command Execution Overlay -->
    <div 
      v-if="isExecutingQueue && terminalTabStore.activeTab?.subType === 'inventory'"
      class="command-execution-overlay"
    >
      <div class="execution-status">
        <div class="spinner"></div>
        <h3>Initializing {{ terminalTabStore.activeTab?.serverContext?.name }}...</h3>
        <p>Executing pre-configured commands</p>
        <div class="progress-info">
          {{ commandQueue.filter(c => c.executed).length }} / {{ commandQueue.length }} commands completed
        </div>
      </div>
    </div>

    <!-- LogMonitor Tab Content (separate from regular tabs) -->
    <div 
      v-if="terminalTabStore.isLogMonitorActive"
      class="tab-content"
    >
      <LogMonitorTab />
    </div>

    <!-- Active Terminal Tab Content -->
    <div 
      v-for="tab in terminalTabStore.tabs" 
      :key="tab.id"
      v-show="tab.isActive && !terminalTabStore.isLogMonitorActive"
      class="tab-content"
    >
      <!-- Direct tab component usage based on type -->
      <TerminalTabComponent 
        v-if="tab.type === 'terminal'" 
        :tab-id="tab.id"
        :sub-type="tab.subType"
        @click="hideSelectionPopup"
      />
      
      <AIAgentTab 
        v-else-if="tab.type === 'ai-agent'" 
        :tab-id="tab.id"
      />
      
      <div v-else class="unknown-tab-content">
        <div class="unknown-message">
          <h4>Unknown tab type: {{ tab.type }}</h4>
          <p>This tab type is not supported.</p>
        </div>
      </div>
    </div>

    <!-- Default message when no tabs -->
    <div v-if="terminalTabStore.tabs.length === 0" class="no-tabs-message">
      <h3>No active sessions</h3>
      <p>Click the + button to create a new terminal or AI chat session.</p>
    </div>

    <!-- Selection Action Popup -->
    <SelectionActionPopup
      :show="showSelectionPopup"
      :position="popupPosition"
      :selected-text="selectedText"
      @copy="onCopyAction"
      @send-to-ai="onSendToAI"
      @hide="hideSelectionPopup"
    />
  </div>
</template>

<script setup lang="ts">
import { ClipboardAddon } from '@xterm/addon-clipboard'
import { FitAddon } from '@xterm/addon-fit'
import { SearchAddon } from '@xterm/addon-search'
import { SerializeAddon } from '@xterm/addon-serialize'
import { Unicode11Addon } from '@xterm/addon-unicode11'
import { WebLinksAddon } from '@xterm/addon-web-links'
import { Terminal, type ITheme } from '@xterm/xterm'
import '@xterm/xterm/css/xterm.css'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAetherTerminalServiceStore } from '../../stores/aetherTerminalServiceStore'
import { useTerminalTabStore } from '../../stores/terminalTabStore'
import SelectionActionPopup from '../SelectionActionPopup.vue'
import TerminalTabComponent from './TerminalTab.vue'
import AIAgentTab from './AIAgentTab.vue'
import LogMonitorTab from './LogMonitorTab.vue'

interface Props {
  isTerminalPaused?: boolean
  isSupervisorLocked?: boolean
}

interface Emits {
  (e: 'terminal-initialized'): void
}

interface QueuedCommand {
  id: string
  command: string
  timestamp: Date
  executed: boolean
  tabId: string
}

const props = defineProps<Props>()
defineEmits<Emits>()

const terminalEl = ref<HTMLElement | null>(null)
const terminal = ref<Terminal | null>(null)
const fitAddon = ref<FitAddon | null>(null)
const searchAddon = ref<SearchAddon | null>(null)
const clipboardAddon = ref<ClipboardAddon | null>(null)
const serializeAddon = ref<SerializeAddon | null>(null)
const contextMenuObserver = ref<MutationObserver | null>(null)
const keyboardCleanup = ref<(() => void) | null>(null)
const resizeCleanup = ref<(() => void) | null>(null)

// Command queue for pre-execution
const commandQueue = ref<QueuedCommand[]>([])
const isExecutingQueue = ref(false)
const terminalReady = ref(false)

const terminalStore = useAetherTerminalServiceStore()
const terminalTabStore = useTerminalTabStore()

// Get active tab from store
const activeTab = computed(() => terminalTabStore.activeTab)

// Selection popup state
const showSelectionPopup = ref(false)
const popupPosition = ref({ x: 0, y: 0 })
const selectedText = ref('')

const isSupervisorLocked = computed(() => {
  return props.isSupervisorLocked || terminalStore.isSupervisorLocked
})

const theme: ITheme = {
  background: '#1e1e1e',
  foreground: '#ffffff',
  cursor: '#ffffff',
  cursorAccent: '#000000',
  selectionBackground: 'rgba(255, 255, 255, 0.3)',
  selectionForeground: '#000000',
  black: '#000000',
  red: '#cd3131',
  green: '#0dbc79',
  yellow: '#e5e510',
  blue: '#3b78ff',
  magenta: '#bc3fbc',
  cyan: '#0dc2c2',
  white: '#e5e5e5',
  brightBlack: '#666666',
  brightRed: '#f14c4c',
  brightGreen: '#23d18b',
  brightYellow: '#f5f543',
  brightBlue: '#3b8eea',
  brightMagenta: '#d670d6',
  brightCyan: '#29b8db',
  brightWhite: '#ffffff',
}

onMounted(async () => {
  console.log('TerminalView mounted')
  
  // Wait for active tab to initialize terminals
  setTimeout(() => {
    initializeActiveTerminal()
  }, 100)
})

// Watch for terminal readiness to execute queued commands
watch(terminalReady, (isReady) => {
  if (isReady && !isExecutingQueue.value) {
    executeQueuedCommands()
  }
})

// Watch for session readiness with better timing
watch(() => terminalStore.session.id, (sessionId) => {
  if (sessionId && terminal.value && !terminalReady.value) {
    // Small delay to ensure terminal is fully connected
    setTimeout(() => {
      if (!terminalReady.value) {
        terminalReady.value = true
        console.log('Terminal ready set from session ID change')
      }
    }, 200)
  }
})

// Watch for active tab changes to handle inventory terminal initialization
watch(() => activeTab.value, (newTab, oldTab) => {
  if (newTab && newTab.id !== oldTab?.id) {
    // Reset terminal state for new tab
    terminalReady.value = false
    commandQueue.value = []
    
    // Queue commands for inventory terminals immediately
    if (newTab.subType === 'inventory' && newTab.serverContext) {
      queueInventoryCommands(newTab)
    }
  }
})

const initializeActiveTerminal = () => {
  const activeTabValue = activeTab.value
  if (!activeTabValue || activeTabValue.type !== 'terminal') return

  const terminalId = `terminal-${activeTabValue.id}`
  terminalEl.value = document.getElementById(terminalId)
  console.log('Terminal element found:', terminalEl.value, 'for tab:', activeTabValue.id)
  
  if (terminalEl.value) {
    terminal.value = new Terminal({
      // Essential options
      convertEol: true,
      cursorBlink: true,
      disableStdin: false,
      
      // Enhanced buffer options for better screen buffer support
      scrollback: 10000,              // Increased from 1000 for better buffer retention
      altClickMovesCursor: false,     // Better alternate screen support
      allowTransparency: true,        // Theme flexibility
      
      // Font and display improvements
      fontFamily: 'Monaco, Menlo, "SF Mono", "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace',
      fontSize: 14,
      lineHeight: 1.0,
      letterSpacing: 0,
      
      // Cursor configuration for better visibility
      cursorStyle: 'block',
      cursorWidth: 1,
      
      // Scroll behavior for better alternate screen buffer experience
      scrollSensitivity: 1,
      fastScrollSensitivity: 5,
      scrollOnUserInput: true,
      
      // Screen buffer and rendering improvements
      screenReaderMode: false,        // Better performance
      macOptionIsMeta: false,         // Platform compatibility
      macOptionClickForcesSelection: false,
      
      // Enhanced theme support
      theme: theme,
      allowProposedApi: true,
    })

    // Initialize and load all addons for enhanced functionality
    fitAddon.value = new FitAddon()
    terminal.value.loadAddon(fitAddon.value)

    // Search addon for buffer searching capabilities
    searchAddon.value = new SearchAddon()
    terminal.value.loadAddon(searchAddon.value)

    // Clipboard addon for better copy/paste functionality
    clipboardAddon.value = new ClipboardAddon()
    terminal.value.loadAddon(clipboardAddon.value)

    // Serialize addon for session persistence
    serializeAddon.value = new SerializeAddon()
    terminal.value.loadAddon(serializeAddon.value)

    // Web links addon for clickable URLs
    const webLinksAddon = new WebLinksAddon()
    terminal.value.loadAddon(webLinksAddon)

    // Unicode support addon
    const unicode11Addon = new Unicode11Addon()
    terminal.value.loadAddon(unicode11Addon)
    
    // Activate Unicode 11 for better character support
    terminal.value.unicode.activeVersion = '11'
    
    // Refresh terminal to apply all configurations
    terminal.value?.refresh(0, terminal.value.rows - 1)

    terminal.value.open(terminalEl.value)
    fitAddon.value.fit()

    // Setup context menu prevention
    setupContextMenuPrevention()

    // Setup terminal event handlers
    setupTerminalEventHandlers()

    // Setup shell output handler after terminal is initialized
    setupShellOutputHandler()

    // Setup keyboard and resize handlers
    keyboardCleanup.value = setupKeyboardHandlers()
    resizeCleanup.value = setupResizeHandler()

    // Handle inventory terminal auto-command execution
    if (activeTab.value.subType === 'inventory' && activeTab.value.serverContext) {
      console.log('Inventory terminal detected for server:', activeTab.value.serverContext.name)
      queueInventoryCommands(activeTab.value)
    }
  }
}

const setupContextMenuPrevention = () => {
  if (!terminalEl.value) return

  // Ensure context menu is disabled on all xterm elements
  const disableContextMenuOnElement = (element: Element) => {
    element.addEventListener('contextmenu', (e: Event) => {
      e.preventDefault()
      e.stopPropagation()
    })
  }

  // Disable context menu on existing xterm elements
  const xtermElements = terminalEl.value.querySelectorAll('.xterm, .xterm-screen, .xterm-viewport, .xterm-rows')
  xtermElements.forEach(disableContextMenuOnElement)

  // Use MutationObserver to catch dynamically added xterm elements
  contextMenuObserver.value = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          const element = node as Element
          // Check if the added element or its children contain xterm classes
          if (element.classList?.contains('xterm') || 
              element.classList?.contains('xterm-screen') ||
              element.classList?.contains('xterm-viewport') ||
              element.classList?.contains('xterm-rows')) {
            disableContextMenuOnElement(element)
          }
          // Also check children of added elements
          const childXtermElements = element.querySelectorAll?.('.xterm, .xterm-screen, .xterm-viewport, .xterm-rows')
          childXtermElements?.forEach(disableContextMenuOnElement)
        }
      })
    })
  })

  // Start observing the terminal container for changes
  contextMenuObserver.value.observe(terminalEl.value, {
    childList: true,
    subtree: true,
    attributes: false
  })
}

const setupShellOutputHandler = () => {
  // Connect to the socket and receive data
  let motdContent = ''

  terminalStore.onShellOutput((data: string) => {
    console.log('onShellOutput callback triggered with data:', data)
    console.log('Terminal ref exists:', !!terminal.value)
    console.log('Terminal element exists:', !!terminalEl.value)
    
    // Detect MOTD content (contains multiple color sequences and text)
    if (data.includes('\\u001b[34;1m') && data.includes('\\u001b[37;1m') && data.length > 100) {
      motdContent = data
      console.log('MOTD content detected and stored')
    }

    // Check for clear screen sequences that might clear MOTD
    if (data.includes('\\u001b[2J') || data.includes('\\u001b[H')) {
      // Re-display MOTD after clear screen
      if (motdContent) {
        setTimeout(() => {
          terminal.value?.write(motdContent)
          console.log('MOTD re-displayed after clear screen')
        }, 100)
      }
    }

    if (terminal.value) {
      terminal.value.write(data)
      console.log('Data written to terminal:', data)
    } else {
      console.warn('Terminal not initialized, cannot write data:', data)
    }
    
    // Check if terminal is ready based on shell prompt or system messages
    if (!terminalReady.value && 
        (data.includes('$') || data.includes('#') || data.includes('>') || 
         data.includes('Welcome') || data.includes('login:'))) {
      setTimeout(() => {
        if (!terminalReady.value && terminalStore.session.id) {
          terminalReady.value = true
          console.log('Terminal ready detected from shell prompt')
        }
      }, 100)
    }
  })
}

const setupTerminalEventHandlers = () => {
  if (!terminal.value) return

  // Listen for terminal resize events and send to backend
  terminal.value.onResize((dimensions) => {
    console.log('Terminal resized:', dimensions)
    // Send resize event to backend
    if (terminalStore.socket && terminalStore.session.id) {
      terminalStore.socket.emit('terminal_resize', {
        session: terminalStore.session.id,
        cols: dimensions.cols,
        rows: dimensions.rows,
      })
    }
  })
  
  // Check if terminal becomes ready when session is established
  const sessionReadyCheck = () => {
    if (terminalStore.session.id && !terminalReady.value) {
      setTimeout(() => {
        terminalReady.value = true
        console.log('Terminal ready detected from session establishment')
      }, 500)
    }
  }
  
  // Watch for session changes
  watch(() => terminalStore.session.id, sessionReadyCheck)

  terminal.value.onKey((e) => {
    const ev = e.domEvent

    if (isSupervisorLocked.value || props.isTerminalPaused) {
      ev.preventDefault()
      return
    }

    // Send all key inputs to backend (don't handle locally)
    sendInput(e.key)
  })

  // Handle text selection events
  terminal.value.onSelectionChange(() => {
    const selection = terminal.value?.getSelection()
    if (selection && selection.trim()) {
      selectedText.value = selection
      showSelectionPopup.value = false // Hide popup initially
    } else {
      hideSelectionPopup()
    }
  })

  // Handle mouse events for selection popup
  terminalEl.value?.addEventListener('mouseup', (event: MouseEvent) => {
    setTimeout(() => {
      const selection = terminal.value?.getSelection()
      if (selection && selection.trim()) {
        selectedText.value = selection.trim()
        
        // Position popup near mouse cursor, considering viewport boundaries
        const terminalRect = terminalEl.value?.getBoundingClientRect()
        if (terminalRect) {
          const menuWidth = 320 // Max width of context menu
          const menuHeight = 400 // Estimated height of context menu
          
          let x = event.clientX - terminalRect.left
          let y = event.clientY - terminalRect.top
          
          // Adjust horizontal position to keep menu in viewport
          if (x + menuWidth > terminalRect.width) {
            x = terminalRect.width - menuWidth - 10
          }
          if (x < 0) x = 10
          
          // Adjust vertical position to keep menu in viewport
          if (y + menuHeight > terminalRect.height) {
            y = event.clientY - terminalRect.top - menuHeight - 10
          }
          if (y < 0) y = 10
          
          popupPosition.value = { x, y }
        }
        
        showSelectionPopup.value = true
      }
    }, 10) // Small delay to ensure selection is processed
  })

  // Handle right-click for context menu - always prevent default browser menu
  terminalEl.value?.addEventListener('contextmenu', (event: MouseEvent) => {
    // Always prevent the default browser context menu
    event.preventDefault()
    event.stopPropagation()
    
    setTimeout(() => {
      const selection = terminal.value?.getSelection()
      if (selection && selection.trim()) {
        selectedText.value = selection.trim()
        
        // Position context menu at right-click location
        const terminalRect = terminalEl.value?.getBoundingClientRect()
        if (terminalRect) {
          const menuWidth = 320
          const menuHeight = 400
          
          let x = event.clientX - terminalRect.left
          let y = event.clientY - terminalRect.top
          
          // Adjust position to keep menu in viewport
          if (x + menuWidth > terminalRect.width) {
            x = terminalRect.width - menuWidth - 10
          }
          if (x < 0) x = 10
          
          if (y + menuHeight > terminalRect.height) {
            y = event.clientY - terminalRect.top - menuHeight - 10
          }
          if (y < 0) y = 10
          
          popupPosition.value = { x, y }
          showSelectionPopup.value = true
        }
      }
      // If no selection, we still prevent the default menu but don't show our popup
    }, 10)
  })
}

const setupKeyboardHandlers = () => {
  // Handle keyboard events for context menu and search
  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && showSelectionPopup.value) {
      hideSelectionPopup()
      event.preventDefault()
      return
    }
    
    // Handle Ctrl+F for search (Cmd+F on Mac)
    if ((event.ctrlKey || event.metaKey) && event.key === 'f') {
      event.preventDefault()
      // Focus on search if implemented in UI, for now just log
      console.log('Search shortcut triggered')
      return
    }
    
    // Handle Ctrl+C for copy when text is selected
    if ((event.ctrlKey || event.metaKey) && event.key === 'c') {
      const selection = terminal.value?.getSelection()
      if (selection && selection.trim()) {
        event.preventDefault()
        copySelection()
        return
      }
    }
    
    // Handle Ctrl+A for select all in terminal
    if ((event.ctrlKey || event.metaKey) && event.key === 'a') {
      if (terminal.value) {
        event.preventDefault()
        terminal.value.selectAll()
        return
      }
    }
  }

  document.addEventListener('keydown', handleKeyDown)

  // Return cleanup function instead of using onUnmounted in async context
  return () => {
    document.removeEventListener('keydown', handleKeyDown)
  }
}

const setupResizeHandler = () => {
  const handleResize = () => {
    if (fitAddon.value && terminal.value) {
      fitAddon.value.fit()
      // Send new terminal size after fit
      setTimeout(() => {
        if (terminal.value && terminalStore.socket && terminalStore.session.id) {
          terminalStore.socket.emit('terminal_resize', {
            session: terminalStore.session.id,
            cols: terminal.value.cols,
            rows: terminal.value.rows,
          })
        }
      }, 100)
    }
  }

  window.addEventListener('resize', handleResize)
  
  // Return cleanup function instead of using onUnmounted in async context
  return () => {
    window.removeEventListener('resize', handleResize)
  }
}

onUnmounted(() => {
  terminalStore.offShellOutput()
  
  // Clean up keyboard and resize handlers
  if (keyboardCleanup.value) {
    keyboardCleanup.value()
    keyboardCleanup.value = null
  }
  
  if (resizeCleanup.value) {
    resizeCleanup.value()
    resizeCleanup.value = null
  }
  
  // Dispose of all addons before terminal
  searchAddon.value?.dispose()
  clipboardAddon.value?.dispose()
  serializeAddon.value?.dispose()
  fitAddon.value = null
  searchAddon.value = null
  clipboardAddon.value = null
  serializeAddon.value = null
  
  terminal.value?.dispose()
  
  // Cleanup context menu observer
  if (contextMenuObserver.value) {
    contextMenuObserver.value.disconnect()
    contextMenuObserver.value = null
  }
  
  // Clear command queue
  commandQueue.value = []
  isExecutingQueue.value = false
  terminalReady.value = false
})

// Send input to backend for real-time processing
const sendInput = (input: string) => {
  console.log('Sending input to backend:', input)
  terminalStore.sendInput(input)
}

// Queue inventory commands for execution when terminal is ready
const queueInventoryCommands = (tab: typeof activeTab.value) => {
  if (!tab || tab.subType !== 'inventory' || !tab.serverContext) return
  
  console.log('Queueing inventory commands for server:', tab.serverContext.name)
  
  // Clear existing queue for this tab
  commandQueue.value = commandQueue.value.filter(cmd => cmd.tabId !== tab.id)
  
  // Get pre-execution commands from store
  const storeCommands = terminalTabStore.getTabCommands(tab.id)
  
  // Add to local queue
  storeCommands.forEach((storeCommand) => {
    commandQueue.value.push({
      id: `${tab.id}-${storeCommand.id}`,
      command: storeCommand.command,
      timestamp: new Date(),
      executed: false,
      tabId: tab.id
    })
  })
  
  console.log('Queued commands from store:', storeCommands.length)
  
  // Try to execute immediately if terminal is ready
  if (terminalReady.value) {
    executeQueuedCommands()
  }
}

// Execute all queued commands for the current tab
const executeQueuedCommands = async () => {
  if (!activeTab.value || isExecutingQueue.value) return
  
  const tabCommands = commandQueue.value.filter(
    cmd => cmd.tabId === activeTab.value!.id && !cmd.executed
  )
  
  if (tabCommands.length === 0) return
  
  console.log('Executing queued commands:', tabCommands.length)
  isExecutingQueue.value = true
  
  try {
    // Wait for terminal session to be fully ready
    if (!terminalStore.session.id) {
      console.log('Waiting for terminal session...')
      await waitForSession()
    }
    
    // Add small delay to ensure terminal is fully initialized
    await new Promise(resolve => setTimeout(resolve, 300))
    
    for (const command of tabCommands) {
      if (terminalStore.session.id) {
        console.log('Executing command:', command.command)
        await executeCommandWithDelay(command.command)
        command.executed = true
      }
    }
    
    // Mark commands as executed in the store
    if (activeTab.value.id) {
      terminalTabStore.markCommandsExecuted(activeTab.value.id)
    }
  } catch (error) {
    console.error('Error executing queued commands:', error)
  } finally {
    isExecutingQueue.value = false
    
    // Clean up executed commands
    commandQueue.value = commandQueue.value.filter(cmd => !cmd.executed)
  }
}

// Wait for terminal session to be ready
const waitForSession = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error('Terminal session timeout'))
    }, 10000) // 10 second timeout
    
    const checkSession = () => {
      if (terminalStore.session.id) {
        clearTimeout(timeout)
        resolve()
      } else {
        setTimeout(checkSession, 100)
      }
    }
    
    checkSession()
  })
}

// Execute a single command with appropriate delay
const executeCommandWithDelay = (command: string): Promise<void> => {
  return new Promise((resolve) => {
    sendInput(command)
    // Wait between commands to ensure proper execution
    // Longer delay for SSH commands, shorter for echo commands
    const delay = command.includes('ssh ') ? 1000 : 300
    setTimeout(resolve, delay)
  })
}

// Selection popup event handlers
const hideSelectionPopup = () => {
  showSelectionPopup.value = false
  selectedText.value = ''
}

const onCopyAction = async () => {
  const success = await copySelection()
  if (success) {
    console.log('Text copied successfully')
    // Optional: Show a toast notification
  } else {
    console.warn('Failed to copy text to clipboard')
  }
}

const onSendToAI = (text: string, prompt?: string) => {
  console.log('Sending text to AI:', text, 'with prompt:', prompt)
  
  // Create or switch to AI chat tab
  const aiTab = terminalTabStore.createTab('ai-agent', 'AI Analysis')
  terminalTabStore.switchToTab(aiTab.id)
  
  // Send message to AI with custom prompt or default
  const message = prompt || `Please analyze this terminal output: ${text}`
  const chatMessage = {
    type: 'user',
    message,
    timestamp: new Date(),
    source: 'terminal_selection',
    terminalOutput: text
  }
  terminalStore.sendChatMessage(chatMessage)
}

// Enhanced clipboard operations
const copySelection = async () => {
  if (terminal.value) {
    const selection = terminal.value.getSelection()
    if (selection) {
      try {
        // Use the standard clipboard API directly
        await navigator.clipboard.writeText(selection)
        console.log('Text copied to clipboard')
        return true
      } catch (error) {
        console.warn('Failed to copy to clipboard:', error)
        return false
      }
    }
  }
  return false
}

// Visual feedback helpers
const getStatusClass = () => {
  if (!terminalStore.session.id) return 'connecting'
  if (isExecutingQueue.value) return 'executing'
  if (terminalReady.value) return 'ready'
  return 'waiting'
}

const getStatusText = () => {
  if (!terminalStore.session.id) return 'Connecting to terminal...'
  if (isExecutingQueue.value) return 'Executing commands...'
  if (terminalReady.value && commandQueue.value.length > 0) return 'Ready to execute'
  if (terminalReady.value) return 'Terminal ready'
  return 'Waiting for terminal...'
}

const getProgressPercentage = () => {
  if (commandQueue.value.length === 0) return 0
  const executed = commandQueue.value.filter(c => c.executed).length
  return Math.round((executed / commandQueue.value.length) * 100)
}
</script>

<style scoped lang="scss">
.terminal-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  position: relative;
}

.xterm-container {
  flex: 1;
  border-top: 1px solid #444;
  min-height: 300px;
  background-color: #1e1e1e;
  
  /* Prevent context menu on all terminal content */
  * {
    -webkit-user-select: text; /* Allow text selection */
    -moz-user-select: text;
    -ms-user-select: text;
    user-select: text;
  }
}

.command-execution-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(30, 30, 30, 0.95);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(2px);
}

.execution-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  color: #ffffff;
  max-width: 400px;
  padding: 24px;
  background: #2d2d2d;
  border-radius: 8px;
  border: 1px solid #444;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #444;
  border-top: 3px solid #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.execution-status h3 {
  margin: 0 0 8px 0;
  color: #ffffff;
  font-size: 18px;
}

.execution-status p {
  margin: 0 0 16px 0;
  color: #cccccc;
  font-size: 14px;
}

.progress-info {
  color: #4caf50;
  font-size: 14px;
  font-weight: 500;
}

.terminal-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background-color: #2d2d2d;
  border-bottom: 1px solid #444;
  font-size: 14px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  
  &.connecting {
    background-color: #ff9800;
    animation: pulse 1.5s infinite;
  }
  
  &.executing {
    background-color: #2196f3;
    animation: pulse 1s infinite;
  }
  
  &.ready {
    background-color: #4caf50;
  }
  
  &.waiting {
    background-color: #ffc107;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  color: #cccccc;
  font-weight: 500;
}

.progress-bar {
  width: 200px;
  height: 4px;
  background-color: #444;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: #4caf50;
  transition: width 0.3s ease;
  border-radius: 2px;
}

.tab-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.terminal-tab-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  position: relative;
}

.ai-agent-tab-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.log-monitor-tab-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  background-color: #1e1e1e;
}

.no-tabs-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  color: #cccccc;

  h3 {
    margin-bottom: 8px;
    color: #aaaaaa;
  }

  p {
    color: #888888;
    font-size: 14px;
  }
}

.unknown-tab-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  color: #cccccc;
  
  .unknown-message {
    padding: 32px;
    
    h4 {
      margin-bottom: 8px;
      color: #ff9800;
    }

    p {
      color: #888888;
      font-size: 14px;
    }
  }
}
</style>