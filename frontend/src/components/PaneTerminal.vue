<template>
  <div class="pane-terminal">
    <!-- Connection Status -->
    <div v-if="showConnectionStatus" class="connection-status">
      <div class="status-indicator">
        {{ connectionStatus }}
      </div>
    </div>

    <!-- Xterm.js Terminal -->
    <div :id="terminalId" class="xterm-container"></div>
  </div>
</template>

<script setup lang="ts">
import { FitAddon } from '@xterm/addon-fit'
import { Terminal, type ITheme } from '@xterm/xterm'
import '@xterm/xterm/css/xterm.css'
import { onMounted, onUnmounted, ref, watch } from 'vue'
import io from 'socket.io-client'

interface Props {
  tabId: string
  paneId: string
  terminalId: string
}

const props = defineProps<Props>()

// Helper function to create hierarchical event names
const createEventName = (operation: string) => {
  return `workspace:tab:${props.tabId}:pane:${props.paneId}:terminal:${operation}`
}

// Terminal creation state management
const terminalCreationRequested = ref(false)
const paneReadyForTerminal = ref(false)

// Function to create terminal session
const createTerminalSession = () => {
  if (!socket.value || !paneReadyForTerminal.value) {
    console.log(`⚠️ Cannot create terminal: socket=${!!socket.value}, ready=${paneReadyForTerminal.value}`)
    return
  }
  
  console.log(`🚀 Creating terminal session for pane ${props.paneId}`)
  connectionStatus.value = 'Creating Terminal...'
  console.log(`📤 Sending ${createEventName('create')} for ${props.terminalId}`)
  socket.value.emit(createEventName('create'), {
    paneId: props.paneId,
    terminalId: props.terminalId,
    cols: terminal.value?.cols || 80,
    rows: terminal.value?.rows || 24
  })
  terminalCreationRequested.value = true
}

// Function to request terminal creation (can be called externally)
const requestTerminalCreation = () => {
  terminalCreationRequested.value = true
  if (paneReadyForTerminal.value) {
    createTerminalSession()
  } else {
    console.log(`📋 Terminal creation requested, waiting for pane to be ready...`)
    connectionStatus.value = 'Waiting for Connection...'
  }
}

const terminal = ref<Terminal | null>(null)
const fitAddon = ref<FitAddon | null>(null)
const socket = ref<any>(null)
const isConnected = ref(false)
const connectionStatus = ref('Connecting...')

// Debug: Log component props
console.log(`🔧 PaneTerminal created with tabId: ${props.tabId}, paneId: ${props.paneId}, terminalId: ${props.terminalId}`)

// Watch isConnected for debugging
watch(isConnected, (newValue, oldValue) => {
  console.log(`🔄 isConnected changed from ${oldValue} to ${newValue} for pane ${props.paneId}`)
  console.log(`🔄 connectionStatus is now: ${connectionStatus.value}`)
  console.log(`🔄 Template should ${newValue ? 'hide' : 'show'} connection status`)
}, { immediate: true })

// Simple reactive ref for debugging
const showConnectionStatus = ref(true)

// Watch isConnected and update showConnectionStatus
watch(isConnected, (newValue) => {
  showConnectionStatus.value = !newValue
  console.log(`🎭 showConnectionStatus updated: ${showConnectionStatus.value} (isConnected: ${newValue}) for pane ${props.paneId}`)
}, { immediate: true })

// Terminal theme
const terminalTheme: ITheme = {
  background: '#1e1e1e',
  foreground: '#d4d4d4',
  cursor: '#ffffff',
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
}

const initializeTerminal = () => {
  console.log(`🖥️ Initializing terminal for pane ${props.paneId}`)
  
  // Create terminal instance
  terminal.value = new Terminal({
    theme: terminalTheme,
    fontSize: 14,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    cursorBlink: true,
    rows: 24,
    cols: 80,
    // Mouse support for wheel scrolling and buffer access
    scrollback: 10000,           // Large scroll buffer
    scrollOnUserInput: true,     // Scroll to bottom on input
    scrollSensitivity: 5,        // Mouse wheel sensitivity
    fastScrollSensitivity: 5,    // Fast scroll sensitivity
    fastScrollModifier: 'shift', // Shift+wheel for fast scroll
    altClickMovesCursor: true,   // Alt+click to move cursor
    rightClickSelectsWord: true, // Right-click word selection
    linkHandler: {
      activate: (event, uri) => {
        console.log('Link clicked:', uri)
        window.open(uri, '_blank')
      }
    }
  })
  
  // Enable mouse event handling after terminal creation
  terminal.value.options.disableStdin = false  // Ensure stdin is enabled for mouse events

  // Create fit addon
  fitAddon.value = new FitAddon()
  terminal.value.loadAddon(fitAddon.value)

  // Mount terminal to DOM
  const terminalElement = document.getElementById(props.terminalId)
  if (terminalElement) {
    terminal.value.open(terminalElement)
    fitAddon.value.fit()
    
    // Add focus event to set this terminal as primary for input
    terminalElement.addEventListener('focus', () => {
      if (socket.value && isConnected.value) {
        socket.value.emit(createEventName('focus'), {
          terminalId: props.terminalId
        })
        console.log(`🎯 Set focus for terminal ${props.terminalId}`)
      }
    })
    
    // Also handle click events to set focus
    terminalElement.addEventListener('click', () => {
      if (socket.value && isConnected.value) {
        socket.value.emit(createEventName('focus'), {
          terminalId: props.terminalId
        })
      }
    })
    
    // Disable context menu and handle right-click paste
    terminalElement.addEventListener('contextmenu', (event) => {
      event.preventDefault()
      // Right-click paste
      navigator.clipboard.readText().then((text) => {
        if (text && socket.value && isConnected.value) {
          console.log('📋 Right-click paste:', text.substring(0, 50) + '...')
          socket.value.emit(createEventName('input'), {
            terminalId: props.terminalId,
            data: text
          })
        }
      }).catch((err) => {
        console.error('❌ Right-click paste failed:', err)
      })
    })
    
    // Add middle-click paste support (Linux style)
    terminalElement.addEventListener('mousedown', (event) => {
      if (event.button === 1) { // Middle mouse button
        event.preventDefault()
        navigator.clipboard.readText().then((text) => {
          if (text && socket.value && isConnected.value) {
            console.log('📋 Middle-click paste:', text.substring(0, 50) + '...')
            socket.value.emit(createEventName('input'), {
              terminalId: props.terminalId,
              data: text
            })
          }
        }).catch((err) => {
          console.error('❌ Middle-click paste failed:', err)
        })
      }
    })
    
    // Auto-copy on text selection
    let selectionTimeout: ReturnType<typeof setTimeout> | null = null
    terminalElement.addEventListener('mouseup', () => {
      // Clear previous timeout
      if (selectionTimeout) {
        clearTimeout(selectionTimeout)
      }
      
      // Small delay to ensure selection is complete
      selectionTimeout = setTimeout(() => {
        if (terminal.value) {
          const selection = terminal.value.getSelection()
          if (selection && selection.trim().length > 0) {
            navigator.clipboard.writeText(selection).then(() => {
              console.log('📋 Auto-copied selection:', selection.substring(0, 50) + '...')
              showCopyFeedback()
            }).catch((err) => {
              console.error('❌ Auto-copy failed:', err)
              // Try fallback
              fallbackCopyToClipboard(selection)
            })
          }
        }
      }, 50)
    })
    
    // Also handle selection changes via keyboard
    if (terminal.value) {
      terminal.value.onSelectionChange(() => {
        // Clear previous timeout
        if (selectionTimeout) {
          clearTimeout(selectionTimeout)
        }
        
        // Small delay to avoid excessive copying during selection
        selectionTimeout = setTimeout(() => {
          if (terminal.value) {
            const selection = terminal.value.getSelection()
            if (selection && selection.trim().length > 0) {
              navigator.clipboard.writeText(selection).then(() => {
                console.log('📋 Auto-copied keyboard selection:', selection.substring(0, 50) + '...')
                showCopyFeedback()
              }).catch((err) => {
                console.error('❌ Auto-copy failed:', err)
                fallbackCopyToClipboard(selection)
              })
            }
          }
        }, 100)
      })
    }
    
    // Add mouse wheel handling for buffer access
    terminalElement.addEventListener('wheel', (event) => {
      // Get current buffer information
      if (terminal.value) {
        const buffer = terminal.value.buffer.active
        const bufferLength = buffer.length
        const viewportY = terminal.value.buffer.active.viewportY
        const baseY = terminal.value.buffer.active.baseY
        
        console.log('🖱️ Mouse wheel event:', {
          deltaY: event.deltaY,
          bufferLength,
          viewportY,
          baseY,
          scrollback: terminal.value.options.scrollback
        })
        
        // Send buffer position to server for synchronization
        if (socket.value && isConnected.value && Math.abs(event.deltaY) > 0) {
          socket.value.emit(createEventName('scroll'), {
            terminalId: props.terminalId,
            deltaY: event.deltaY,
            viewportY,
            baseY,
            bufferLength
          })
        }
      }
    })
    
    // Add keyboard shortcuts for buffer navigation and clipboard
    terminalElement.addEventListener('keydown', (event) => {
      if (terminal.value) {
        // Ctrl+Shift+C: Copy selected text to clipboard (manual copy)
        if (event.ctrlKey && event.shiftKey && event.key === 'C') {
          const selection = terminal.value.getSelection()
          if (selection) {
            navigator.clipboard.writeText(selection).then(() => {
              console.log('📋 Manual copied to clipboard:', selection.substring(0, 50) + '...')
              showCopyFeedback()
            }).catch((err) => {
              console.error('❌ Failed to copy to clipboard:', err)
              fallbackCopyToClipboard(selection)
            })
          }
          event.preventDefault()
          return
        }
        
        // Ctrl+Shift+V: Paste from clipboard
        if (event.ctrlKey && event.shiftKey && event.key === 'V') {
          navigator.clipboard.readText().then((text) => {
            if (text && socket.value && isConnected.value) {
              console.log('📋 Pasting from clipboard:', text.substring(0, 50) + '...')
              // Send paste text as terminal input
              socket.value.emit(createEventName('input'), {
                terminalId: props.terminalId,
                data: text
              })
            }
          }).catch((err) => {
            console.error('❌ Failed to read from clipboard:', err)
          })
          event.preventDefault()
          return
        }
        
        // Ctrl+Shift+Home: Jump to start of buffer
        if (event.ctrlKey && event.shiftKey && event.key === 'Home') {
          terminal.value.scrollToTop()
          console.log('📋 Scrolled to buffer start')
          event.preventDefault()
          return
        }
        
        // Ctrl+Shift+End: Jump to end of buffer
        if (event.ctrlKey && event.shiftKey && event.key === 'End') {
          terminal.value.scrollToBottom()
          console.log('📋 Scrolled to buffer end')
          event.preventDefault()
          return
        }
        
        // Page Up/Down for buffer navigation
        if (event.key === 'PageUp') {
          terminal.value.scrollPages(-1)
          console.log('📋 Scrolled up one page')
          event.preventDefault()
          return
        }
        
        if (event.key === 'PageDown') {
          terminal.value.scrollPages(1)
          console.log('📋 Scrolled down one page')
          event.preventDefault()
          return
        }
      }
    })
  }

  // Initialize socket connection
  initializeSocket()
}

const initializeSocket = () => {
  console.log(`🔄 Initializing socket for pane ${props.paneId}, terminalId ${props.terminalId}`)
  
  socket.value = io('http://localhost:57575', {
    transports: ['websocket', 'polling'],
    timeout: 20000,
    forceNew: true
  })
  
  // Add connection status debugging
  socket.value.on('connect', () => {
    console.log(`🔌 Socket connected for pane ${props.paneId}`)
    connectionStatus.value = 'Connected'
    paneReadyForTerminal.value = true
    
    // Check if terminal creation was already requested while socket was connecting
    if (terminalCreationRequested.value) {
      createTerminalSession()
    } else {
      connectionStatus.value = 'Ready for Terminal'
      console.log(`⏳ Pane ${props.paneId} ready for terminal creation`)
    }
  })
  
  socket.value.on('connect_error', (error: any) => {
    console.error(`❌ Socket connection error for pane ${props.paneId}:`, error)
    connectionStatus.value = `Connection Error: ${error.message}`
  })
  
  socket.value.on('reconnect', (attemptNumber: number) => {
    console.log(`🔄 Socket reconnected for pane ${props.paneId} (attempt ${attemptNumber})`)
  })
  
  socket.value.on('reconnect_error', (error: any) => {
    console.error(`❌ Socket reconnection error for pane ${props.paneId}:`, error)
  })

  socket.value.on('disconnect', () => {
    console.log(`🔌 Socket disconnected for pane ${props.paneId}`)
    isConnected.value = false
    connectionStatus.value = 'Disconnected'
  })

  socket.value.on(createEventName('created'), (data: any) => {
    console.log(`📨 Received ${createEventName('created')}:`, data)
    console.log(`🔍 Comparing terminalIds: received=${data.terminalId}, expected=${props.terminalId}`)
    if (data.terminalId === props.terminalId) {
      console.log(`✅ Terminal created for pane ${props.paneId}`)
      connectionStatus.value = 'Ready'
      console.log(`🔄 Setting isConnected to true for ${props.paneId}`)
      isConnected.value = true  // Terminal is fully ready
      console.log(`🔄 isConnected is now: ${isConnected.value}`)
    } else {
      console.log(`⚠️ Received ${createEventName('created')} for different terminal: ${data.terminalId}`)
    }
  })

  socket.value.on(createEventName('error'), (data: any) => {
    console.log(`📨 Received ${createEventName('error')}:`, data)
    if (data.terminalId === props.terminalId) {
      console.error(`❌ Terminal error for pane ${props.paneId}:`, data.error)
      connectionStatus.value = `Error: ${data.error}`
    }
  })

  socket.value.on(createEventName('data'), (data: any) => {
    console.log(`📨 Received ${createEventName('data')} for ${data.terminalId}:`, data.data.length, 'bytes')
    if (data.terminalId === props.terminalId && terminal.value) {
      console.log(`📝 Writing to terminal ${props.terminalId}:`, data.data.substring(0, 50) + '...')
      console.log(`🔍 Terminal state: isConnected=${isConnected.value}, terminal=${!!terminal.value}`)
      try {
        terminal.value.write(data.data)
        console.log(`✅ Successfully wrote data to terminal ${props.terminalId}`)
      } catch (error) {
        console.error(`❌ Error writing to terminal ${props.terminalId}:`, error)
      }
    } else {
      console.log(`⚠️ Data not written: terminalId=${data.terminalId}, expected=${props.terminalId}, terminal=${!!terminal.value}`)
    }
  })

  // Handle hierarchical buffer restore events
  socket.value.on(createEventName('buffer_restore'), (data: any) => {
    console.log(`📨 Received ${createEventName('buffer_restore')} for ${data.terminalId}:`, data.buffer_size, 'chars')
    if (data.terminalId === props.terminalId && terminal.value) {
      console.log(`🔄 Restoring terminal buffer for ${props.terminalId}: ${data.buffer_size} characters`)
      try {
        // Clear terminal first to avoid duplicate content
        terminal.value.clear()
        // Write the restored buffer content
        terminal.value.write(data.data)
        console.log(`✅ Successfully restored ${data.buffer_size} characters for terminal ${props.terminalId}`)
      } catch (error) {
        console.error(`❌ Error restoring buffer for terminal ${props.terminalId}:`, error)
      }
    } else {
      console.log(`⚠️ Buffer restore not applied: terminalId=${data.terminalId}, expected=${props.terminalId}, terminal=${!!terminal.value}`)
    }
  })
  
  // Also listen to non-hierarchical terminal:data events as fallback
  socket.value.on('terminal:data', (data: any) => {
    console.log(`📨 Received fallback terminal:data for ${data.terminalId}:`, data.data.length, 'bytes')
    if (data.terminalId === props.terminalId && terminal.value) {
      console.log(`📝 Writing fallback data to terminal ${props.terminalId}:`, data.data.substring(0, 50) + '...')
      try {
        terminal.value.write(data.data)
        console.log(`✅ Successfully wrote fallback data to terminal ${props.terminalId}`)
      } catch (error) {
        console.error(`❌ Error writing fallback data to terminal ${props.terminalId}:`, error)
      }
    }
  })
  
  // Add general event debugging
  socket.value.onAny((eventName: string, ...args: any[]) => {
    console.log(`📡 Received event ${eventName}:`, args)
  })

  // Handle terminal input
  if (terminal.value) {
    terminal.value.onData((data: string) => {
      if (socket.value && isConnected.value) {
        socket.value.emit(createEventName('input'), {
          terminalId: props.terminalId,
          data: data
        })
      }
    })
    
    // Handle terminal resize
    terminal.value.onResize((size: { cols: number; rows: number }) => {
      if (socket.value && isConnected.value) {
        socket.value.emit(createEventName('resize'), {
          terminalId: props.terminalId,
          cols: size.cols,
          rows: size.rows
        })
      }
    })
  }
}

const cleanup = () => {
  console.log(`🧹 Cleaning up terminal for pane ${props.paneId}`)
  
  if (socket.value) {
    if (isConnected.value) {
      socket.value.emit(createEventName('close'), {
        terminalId: props.terminalId
      })
    }
    socket.value.disconnect()
    socket.value = null
  }
  
  if (terminal.value) {
    try {
      // Only dispose addons if they were loaded
      if (fitAddon.value) {
        fitAddon.value = null // Don't dispose fitAddon separately
      }
      terminal.value.dispose()
      terminal.value = null
    } catch (error) {
      console.warn(`⚠️ Error disposing terminal for pane ${props.paneId}:`, error)
    }
  }
  
  // Reset connection state
  isConnected.value = false
  showConnectionStatus.value = true
  connectionStatus.value = 'Disconnected'
}

// Handle window resize
const handleResize = () => {
  if (fitAddon.value && terminal.value) {
    fitAddon.value.fit()
  }
}

onMounted(() => {
  // Delay initialization to ensure DOM is ready
  setTimeout(initializeTerminal, 100)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  cleanup()
  window.removeEventListener('resize', handleResize)
})

// Watch for pane changes - reinitialize if paneId or terminalId changes
watch(() => [props.paneId, props.terminalId], ([newPaneId, newTerminalId], [oldPaneId, oldTerminalId]) => {
  console.log(`🔄 Pane/Terminal changed: ${oldPaneId}/${oldTerminalId} -> ${newPaneId}/${newTerminalId}`)
  
  if (oldPaneId !== newPaneId || oldTerminalId !== newTerminalId) {
    // Clean up old connection
    cleanup()
    // Reinitialize with new IDs
    setTimeout(initializeTerminal, 100)
  } else {
    // Just resize if same pane
    setTimeout(() => {
      if (fitAddon.value && terminal.value) {
        fitAddon.value.fit()
      }
    }, 100)
  }
})

// Clipboard helper functions
const showCopyFeedback = () => {
  // Show a brief visual feedback for copy operation
  const terminalElement = document.getElementById(props.terminalId)
  if (terminalElement) {
    const feedback = document.createElement('div')
    feedback.textContent = 'Copied!'
    feedback.style.cssText = `
      position: absolute;
      top: 10px;
      right: 10px;
      background: #4caf50;
      color: white;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      z-index: 1000;
      pointer-events: none;
    `
    terminalElement.style.position = 'relative'
    terminalElement.appendChild(feedback)
    
    setTimeout(() => {
      if (feedback.parentNode) {
        feedback.parentNode.removeChild(feedback)
      }
    }, 1500)
  }
}

const fallbackCopyToClipboard = (text: string) => {
  // Fallback for older browsers
  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.style.position = 'fixed'
  textArea.style.left = '-999999px'
  textArea.style.top = '-999999px'
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  
  try {
    const successful = document.execCommand('copy')
    if (successful) {
      console.log('📋 Fallback copy successful')
      showCopyFeedback()
    } else {
      console.error('❌ Fallback copy failed')
    }
  } catch (err) {
    console.error('❌ Fallback copy error:', err)
  } finally {
    document.body.removeChild(textArea)
  }
}


// Buffer access functions
const getBufferContent = (startLine?: number, endLine?: number) => {
  if (!terminal.value) return ''
  
  const buffer = terminal.value.buffer.active
  const start = startLine || 0
  const end = endLine || buffer.length
  
  let content = ''
  for (let i = start; i < Math.min(end, buffer.length); i++) {
    const line = buffer.getLine(i)
    if (line) {
      content += line.translateToString(true) + '\n'
    }
  }
  
  console.log(`📋 Retrieved buffer content: lines ${start}-${end} (${content.length} chars)`)
  return content
}

const getVisibleContent = () => {
  if (!terminal.value) return ''
  
  const buffer = terminal.value.buffer.active
  const viewportY = buffer.viewportY
  const rows = terminal.value.rows
  
  return getBufferContent(viewportY, viewportY + rows)
}

const getScrollbackContent = () => {
  if (!terminal.value) return ''
  
  const buffer = terminal.value.buffer.active
  return getBufferContent(0, buffer.length)
}

const searchInBuffer = (searchTerm: string) => {
  if (!terminal.value) return []
  
  const content = getScrollbackContent()
  const lines = content.split('\n')
  const matches = []
  
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes(searchTerm)) {
      matches.push({
        lineNumber: i,
        content: lines[i],
        position: lines[i].indexOf(searchTerm)
      })
    }
  }
  
  console.log(`🔍 Found ${matches.length} matches for "${searchTerm}"`)
  return matches
}

// Clipboard API functions
const copySelection = async () => {
  const selection = terminal.value?.getSelection()
  if (selection) {
    try {
      await navigator.clipboard.writeText(selection)
      console.log('📋 API copy successful')
      showCopyFeedback()
      return true
    } catch (err) {
      console.error('❌ API copy failed:', err)
      fallbackCopyToClipboard(selection)
      return false
    }
  }
  return false
}

const pasteFromClipboard = async () => {
  try {
    const text = await navigator.clipboard.readText()
    if (text && socket.value && isConnected.value) {
      console.log('📋 API paste successful')
      socket.value.emit(createEventName('input'), {
        terminalId: props.terminalId,
        data: text
      })
      return true
    }
  } catch (err) {
    console.error('❌ API paste failed:', err)
  }
  return false
}

// Expose functions for parent component
defineExpose({
  requestTerminalCreation,
  getBufferContent,
  getVisibleContent, 
  getScrollbackContent,
  searchInBuffer,
  copySelection,
  pasteFromClipboard,
  terminal: () => terminal.value
})
</script>

<style scoped>
.pane-terminal {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #1e1e1e;
}

.connection-status {
  padding: 8px;
  background-color: #2d2d2d;
  border-bottom: 1px solid #444;
  color: #ccc;
  font-size: 12px;
  text-align: center;
}

.status-indicator {
  font-weight: bold;
}

.xterm-container {
  flex: 1;
  padding: 4px;
  min-height: 0;
}

/* Override xterm.js default styles for better integration */
:deep(.xterm) {
  height: 100% !important;
}

:deep(.xterm-viewport) {
  overflow-y: auto;
}

:deep(.xterm-screen) {
  width: 100% !important;
  height: 100% !important;
}
</style>