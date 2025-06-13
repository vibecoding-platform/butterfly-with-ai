import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export interface TerminalCommand {
  id: string
  command: string
  timestamp: Date
  status: 'pending' | 'approved' | 'rejected' | 'executed'
  riskLevel: 'low' | 'medium' | 'high' | 'critical'
  aiSuggestion?: string
  rejectionReason?: string
  source: 'user' | 'admin' | 'ai'
}

export interface TerminalSession {
  id: string
  isActive: boolean
  isPaused: boolean
  isReconnecting: boolean
  lastActivity: Date
  adminControlled: boolean
  aiMonitoring: boolean
}

export interface ConnectionState {
  isConnected: boolean
  isConnecting: boolean
  isReconnecting: boolean
  reconnectAttempts: number
  maxReconnectAttempts: number
  lastConnected?: Date
  lastDisconnected?: Date
  connectionError?: string
  latency: number
}

export interface AIMonitoringState {
  isActive: boolean
  monitoringRules: string[]
  currentProcedure?: string
  procedureStep: number
  totalSteps: number
  lastAnalysis?: Date
  riskAssessment: 'low' | 'medium' | 'high' | 'critical'
  suggestedActions: string[]
}

export const useAetherTerminalServiceStore = defineStore('aetherTerminalService', () => {
  // Connection State
  const connectionState = ref<ConnectionState>({
    isConnected: false,
    isConnecting: false,
    isReconnecting: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    latency: 0
  })

  const socket = ref<Socket | null>(null)

  // Terminal State
  const session = ref<TerminalSession>({
    id: '',
    isActive: false,
    isPaused: false,
    isReconnecting: false,
    lastActivity: new Date(),
    adminControlled: false,
    aiMonitoring: true
  })

  const pendingCommands = ref<TerminalCommand[]>([])
  const commandHistory = ref<TerminalCommand[]>([])
  const outputBuffer = ref<string[]>([])
  const isOutputSuppressed = ref(false)

  // AI Monitoring State
  const aiMonitoring = ref<AIMonitoringState>({
    isActive: true,
    monitoringRules: [
      'System file modification detection',
      'Privilege escalation monitoring',
      'Network configuration changes',
      'Service management operations',
      'Data destruction prevention'
    ],
    currentProcedure: 'System maintenance checklist',
    procedureStep: 1,
    totalSteps: 5,
    lastAnalysis: new Date(),
    riskAssessment: 'low',
    suggestedActions: []
  })

  // Dynamic dangerous commands (managed by AI)
  const dangerousCommands = ref<string[]>([])

  // Event Callbacks
  const eventCallbacks = ref<{
    onShellOutput: ((data: string) => void)[]
    onControlOutput: ((data: string) => void)[]
    onChatMessage: ((data: any) => void)[]
    onConnect: (() => void)[]
    onDisconnect: (() => void)[]
    onReconnect: (() => void)[]
    onError: ((error: any) => void)[]
  }>({
    onShellOutput: [],
    onControlOutput: [],
    onChatMessage: [],
    onConnect: [],
    onDisconnect: [],
    onReconnect: [],
    onError: []
  })

  // Getters
  const hasPendingCommands = computed(() => pendingCommands.value.length > 0)
  const isTerminalBlocked = computed(() =>
    session.value.isPaused ||
    session.value.isReconnecting ||
    isOutputSuppressed.value ||
    hasPendingCommands.value ||
    !connectionState.value.isConnected
  )
  const criticalCommandsPending = computed(() =>
    pendingCommands.value.filter(cmd => cmd.riskLevel === 'critical')
  )
  const connectionStatus = computed(() => {
    if (connectionState.value.isConnected) return 'connected'
    if (connectionState.value.isConnecting) return 'connecting'
    if (connectionState.value.isReconnecting) return 'reconnecting'
    return 'disconnected'
  })

  // Connection Actions
  const setSocket = (socketInstance: Socket) => {
    socket.value = socketInstance
    setupSocketListeners()
  }

  const setupSocketListeners = () => {
    if (!socket.value) return

    socket.value.on('connect', () => {
      connectionState.value.isConnected = true
      connectionState.value.isConnecting = false
      connectionState.value.isReconnecting = false
      connectionState.value.reconnectAttempts = 0
      connectionState.value.lastConnected = new Date()
      connectionState.value.connectionError = undefined

      addToOutput('[SYSTEM] Connected to AetherTerm service')
      eventCallbacks.value.onConnect.forEach(callback => callback())
    })

    socket.value.on('disconnect', (reason) => {
      connectionState.value.isConnected = false
      connectionState.value.lastDisconnected = new Date()
      connectionState.value.connectionError = reason

      addToOutput(`[SYSTEM] Disconnected from AetherTerm service: ${reason}`)
      eventCallbacks.value.onDisconnect.forEach(callback => callback())

      // Start reconnection if not intentional
      if (reason !== 'io client disconnect') {
        startReconnection()
      }
    })

    socket.value.on('reconnect', (attemptNumber) => {
      connectionState.value.isReconnecting = false
      connectionState.value.reconnectAttempts = attemptNumber
      addToOutput(`[SYSTEM] Reconnected after ${attemptNumber} attempts`)
      eventCallbacks.value.onReconnect.forEach(callback => callback())
    })

    socket.value.on('reconnect_attempt', (attemptNumber) => {
      connectionState.value.reconnectAttempts = attemptNumber
      addToOutput(`[SYSTEM] Reconnection attempt ${attemptNumber}`)
    })

    socket.value.on('reconnect_failed', () => {
      connectionState.value.isReconnecting = false
      connectionState.value.connectionError = 'Max reconnection attempts reached'
      addToOutput('[SYSTEM] Failed to reconnect after maximum attempts')
    })

    socket.value.on('connect_error', (error) => {
      connectionState.value.connectionError = error.message
      addToOutput(`[SYSTEM] Connection error: ${error.message}`)
      eventCallbacks.value.onError.forEach(callback => callback(error))
    })

    // Terminal specific events
    socket.value.on('shell_output', (data: string) => {
      if (!isOutputSuppressed.value) {
        addToOutput(data)
      }
      eventCallbacks.value.onShellOutput.forEach(callback => callback(data))
    })

    socket.value.on('ctl_output', (data: string) => {
      if (!isOutputSuppressed.value) {
        addToOutput(`[CTL] ${data}`)
      }
      eventCallbacks.value.onControlOutput.forEach(callback => callback(data))
    })

    // Chat specific events
    socket.value.on('chat_message', (data: any) => {
      eventCallbacks.value.onChatMessage.forEach(callback => callback(data))
    })

    // Admin control events
    socket.value.on('admin_pause_terminal', (data: { reason: string }) => {
      pauseTerminal(data.reason)
    })

    socket.value.on('admin_resume_terminal', () => {
      resumeTerminal()
    })

    socket.value.on('admin_suppress_output', (data: { suppress: boolean, reason?: string }) => {
      suppressOutput(data.suppress, data.reason)
    })

    socket.value.on('command_approval', (data: { commandId: string, approved: boolean, reason?: string }) => {
      if (data.approved) {
        approveCommand(data.commandId)
      } else {
        rejectCommand(data.commandId, data.reason || 'Rejected by admin')
      }
    })
  }

  const startReconnection = () => {
    if (connectionState.value.reconnectAttempts >= connectionState.value.maxReconnectAttempts) {
      return
    }

    connectionState.value.isReconnecting = true
    session.value.isReconnecting = true
    addToOutput('[SYSTEM] Starting reconnection process...')
  }

  const connect = () => {
    if (connectionState.value.isConnected || connectionState.value.isConnecting) {
      return
    }

    connectionState.value.isConnecting = true
    addToOutput('[SYSTEM] Connecting to AetherTerm service...')
  }

  const disconnect = () => {
    if (socket.value) {
      socket.value.disconnect()
    }
    connectionState.value.isConnected = false
    connectionState.value.isConnecting = false
    connectionState.value.isReconnecting = false
  }

  // Event Registration
  const onShellOutput = (callback: (data: string) => void) => {
    eventCallbacks.value.onShellOutput.push(callback)
  }

  const onControlOutput = (callback: (data: string) => void) => {
    eventCallbacks.value.onControlOutput.push(callback)
  }

  const onChatMessage = (callback: (data: any) => void) => {
    eventCallbacks.value.onChatMessage.push(callback)
  }

  const onConnect = (callback: () => void) => {
    eventCallbacks.value.onConnect.push(callback)
  }

  const onDisconnect = (callback: () => void) => {
    eventCallbacks.value.onDisconnect.push(callback)
  }

  const onReconnect = (callback: () => void) => {
    eventCallbacks.value.onReconnect.push(callback)
  }

  const onError = (callback: (error: any) => void) => {
    eventCallbacks.value.onError.push(callback)
  }

  // Event Cleanup
  const offShellOutput = (callback?: (data: string) => void) => {
    if (callback) {
      const index = eventCallbacks.value.onShellOutput.indexOf(callback)
      if (index !== -1) {
        eventCallbacks.value.onShellOutput.splice(index, 1)
      }
    } else {
      eventCallbacks.value.onShellOutput = []
    }
  }

  const offControlOutput = (callback?: (data: string) => void) => {
    if (callback) {
      const index = eventCallbacks.value.onControlOutput.indexOf(callback)
      if (index !== -1) {
        eventCallbacks.value.onControlOutput.splice(index, 1)
      }
    } else {
      eventCallbacks.value.onControlOutput = []
    }
  }

  const offChatMessage = (callback?: (data: any) => void) => {
    if (callback) {
      const index = eventCallbacks.value.onChatMessage.indexOf(callback)
      if (index !== -1) {
        eventCallbacks.value.onChatMessage.splice(index, 1)
      }
    } else {
      eventCallbacks.value.onChatMessage = []
    }
  }

  // Terminal Actions
  const initializeSession = (sessionId: string) => {
    session.value.id = sessionId
    session.value.isActive = true
    session.value.lastActivity = new Date()
    addToOutput(`[SYSTEM] Terminal session initialized: ${sessionId}`)
  }

  const pauseTerminal = (reason: string) => {
    session.value.isPaused = true
    addToOutput(`[SYSTEM] Terminal paused: ${reason}`)
  }

  const resumeTerminal = () => {
    session.value.isPaused = false
    addToOutput('[SYSTEM] Terminal resumed')
  }

  const suppressOutput = (suppress: boolean, reason?: string) => {
    isOutputSuppressed.value = suppress
    if (suppress && reason) {
      addToOutput(`[SYSTEM] Output suppressed: ${reason}`)
    } else if (!suppress) {
      addToOutput('[SYSTEM] Output restored')
    }
  }

  const analyzeCommand = (command: string): TerminalCommand => {
    const commandId = Date.now().toString()
    let riskLevel: 'low' | 'medium' | 'high' | 'critical' = 'low'
    let aiSuggestion = ''

    // Check for dangerous commands
    const isDangerous = dangerousCommands.value.some(dangerous =>
      command.toLowerCase().includes(dangerous.toLowerCase())
    )

    if (isDangerous) {
      riskLevel = 'critical'
      aiSuggestion = 'This command may cause system damage or data loss. Consider using safer alternatives.'
    } else if (command.includes('sudo')) {
      riskLevel = 'high'
      aiSuggestion = 'This command requires elevated privileges. Ensure you understand its implications.'
    } else if (command.includes('chmod') || command.includes('chown')) {
      riskLevel = 'medium'
      aiSuggestion = 'This command modifies file permissions. Verify the target files and permissions.'
    }

    return {
      id: commandId,
      command,
      timestamp: new Date(),
      status: riskLevel === 'critical' ? 'pending' : 'approved',
      riskLevel,
      aiSuggestion,
      source: 'user'
    }
  }

  const submitCommand = (command: string): boolean => {
    const analyzedCommand = analyzeCommand(command)

    if (analyzedCommand.status === 'pending') {
      pendingCommands.value.push(analyzedCommand)
      addToOutput(`[AI] Command blocked for review: ${command}`)
      addToOutput(`[AI] Reason: ${analyzedCommand.aiSuggestion}`)

      // Notify admin via socket
      if (socket.value) {
        socket.value.emit('command_review_required', {
          commandId: analyzedCommand.id,
          command: analyzedCommand.command,
          riskLevel: analyzedCommand.riskLevel,
          aiSuggestion: analyzedCommand.aiSuggestion
        })
      }

      return false
    }

    commandHistory.value.push(analyzedCommand)
    session.value.lastActivity = new Date()

    // Send command to server
    if (socket.value) {
      socket.value.emit('terminal_command', {
        command: analyzedCommand.command,
        commandId: analyzedCommand.id
      })
    }

    return true
  }

  const approveCommand = (commandId: string) => {
    const commandIndex = pendingCommands.value.findIndex(cmd => cmd.id === commandId)
    if (commandIndex !== -1) {
      const command = pendingCommands.value[commandIndex]
      command.status = 'approved'
      commandHistory.value.push(command)
      pendingCommands.value.splice(commandIndex, 1)
      addToOutput(`[ADMIN] Command approved: ${command.command}`)

      // Execute the approved command
      if (socket.value) {
        socket.value.emit('terminal_command', {
          command: command.command,
          commandId: command.id
        })
      }

      return command
    }
    return null
  }

  const rejectCommand = (commandId: string, reason: string) => {
    const commandIndex = pendingCommands.value.findIndex(cmd => cmd.id === commandId)
    if (commandIndex !== -1) {
      const command = pendingCommands.value[commandIndex]
      command.status = 'rejected'
      command.rejectionReason = reason
      commandHistory.value.push(command)
      pendingCommands.value.splice(commandIndex, 1)
      addToOutput(`[ADMIN] Command rejected: ${command.command}`)
      addToOutput(`[ADMIN] Reason: ${reason}`)
    }
  }

  const sendChatMessage = (message: any) => {
    if (socket.value) {
      socket.value.emit('chat_message', message)
    }
  }

  const addToOutput = (text: string) => {
    if (!isOutputSuppressed.value) {
      outputBuffer.value.push(`[${new Date().toLocaleTimeString()}] ${text}`)
      // Keep only last 1000 lines
      if (outputBuffer.value.length > 1000) {
        outputBuffer.value = outputBuffer.value.slice(-1000)
      }
    }
  }

  const clearOutput = () => {
    outputBuffer.value = []
  }

  const setAdminControl = (controlled: boolean) => {
    session.value.adminControlled = controlled
    addToOutput(`[SYSTEM] Admin control ${controlled ? 'enabled' : 'disabled'}`)
  }

  const setAIMonitoring = (monitoring: boolean) => {
    session.value.aiMonitoring = monitoring
    addToOutput(`[SYSTEM] AI monitoring ${monitoring ? 'enabled' : 'disabled'}`)
  }

  const addDangerousCommand = (command: string) => {
    if (!dangerousCommands.value.includes(command)) {
      dangerousCommands.value.push(command)
    }
  }

  const removeDangerousCommand = (command: string) => {
    const index = dangerousCommands.value.indexOf(command)
    if (index !== -1) {
      dangerousCommands.value.splice(index, 1)
    }
  }

  // Update AI monitoring state
  const updateAIMonitoring = (updates: Partial<AIMonitoringState>) => {
    Object.assign(aiMonitoring.value, updates)
    addToOutput(`[AI] Monitoring updated: ${JSON.stringify(updates)}`)
  }

  return {
    // State
    connectionState,
    socket,
    session,
    pendingCommands,
    commandHistory,
    outputBuffer,
    isOutputSuppressed,
    dangerousCommands,
    aiMonitoring,

    // Getters
    hasPendingCommands,
    isTerminalBlocked,
    criticalCommandsPending,
    connectionStatus,

    // Connection Actions
    setSocket,
    connect,
    disconnect,
    startReconnection,

    // Event Registration
    onShellOutput,
    onControlOutput,
    onChatMessage,
    onConnect,
    onDisconnect,
    onReconnect,
    onError,

    // Event Cleanup
    offShellOutput,
    offControlOutput,
    offChatMessage,

    // Terminal Actions
    initializeSession,
    pauseTerminal,
    resumeTerminal,
    suppressOutput,
    analyzeCommand,
    submitCommand,
    approveCommand,
    rejectCommand,
    sendChatMessage,
    addToOutput,
    clearOutput,
    setAdminControl,
    setAIMonitoring,
    addDangerousCommand,
    removeDangerousCommand,
    updateAIMonitoring
  }
})
