import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface ServerContext {
  id: string
  name: string
  ip: string
  os: string
  uptime: string
  status: 'online' | 'maintenance' | 'offline' | 'warning'
  cpu: number
  memory: number
  disk: number
}

export interface PreExecutionCommand {
  id: string
  command: string
  description?: string
  order: number
  condition?: () => boolean
}

export interface TerminalTab {
  id: string
  title: string
  type: 'terminal' | 'ai-agent' | 'log-monitor'
  subType?: 'pure' | 'inventory'
  isActive: boolean
  sessionId?: string
  lastActivity: Date
  status: 'active' | 'connecting' | 'disconnected' | 'error'
  serverContext?: ServerContext
  preExecutionCommands?: PreExecutionCommand[]
  commandsExecuted?: boolean
}

export const useTerminalTabStore = defineStore('terminalTab', () => {
  // State
  const tabs = ref<TerminalTab[]>([])
  const activeTabId = ref<string | null>(null)
  const nextTabId = ref(1)
  const logMonitorTab = ref<TerminalTab | null>(null)

  // Getters
  const activeTabs = computed(() => tabs.value.filter(tab => tab.isActive))
  const displayTabs = computed(() => tabs.value.filter(tab => tab.isActive))
  const activeTab = computed(() => {
    if (activeTabId.value === 'log-monitor-fixed') {
      return logMonitorTab.value
    }
    return tabs.value.find(tab => tab.id === activeTabId.value) || null
  })
  const terminalTabs = computed(() => tabs.value.filter(tab => tab.type === 'terminal'))
  const aiChatTabs = computed(() => tabs.value.filter(tab => tab.type === 'ai-agent'))
  const logMonitorTabs = computed(() => tabs.value.filter(tab => tab.type === 'log-monitor'))
  const isLogMonitorActive = computed(() => activeTabId.value === 'log-monitor-fixed')

  // Actions
  const createTab = (
    type: 'terminal' | 'ai-agent', 
    title?: string, 
    subType?: 'pure' | 'inventory',
    serverContext?: ServerContext
  ): TerminalTab => {
    console.log('📋 STORE: createTab called with:', { type, title, subType, serverContext })
    
    const id = `tab-${nextTabId.value++}`
    let defaultTitle = type === 'terminal' 
      ? `Terminal ${terminalTabs.value.length + 1}` 
      : `AI Chat ${aiChatTabs.value.length + 1}`
    
    // Override title for inventory terminals with server context
    if (type === 'terminal' && subType === 'inventory' && serverContext) {
      defaultTitle = `${serverContext.name}`
    }
    
    const newTab: TerminalTab = {
      id,
      title: title || defaultTitle,
      type,
      subType,
      isActive: true,
      lastActivity: new Date(),
      status: 'connecting',
      serverContext
    }

    console.log('📋 STORE: Created new tab:', newTab)
    tabs.value.push(newTab)
    activeTabId.value = id
    console.log('📋 STORE: Tab added to store, total tabs:', tabs.value.length)
    console.log('📋 STORE: Active tab ID set to:', id)

    return newTab
  }

  const closeTab = (tabId: string) => {
    const tabIndex = tabs.value.findIndex(tab => tab.id === tabId)
    if (tabIndex === -1) return

    const tab = tabs.value[tabIndex]
    tab.isActive = false

    // If this was the active tab, switch to another tab
    if (activeTabId.value === tabId) {
      const remainingTabs = tabs.value.filter(t => t.isActive && t.id !== tabId)
      activeTabId.value = remainingTabs.length > 0 ? remainingTabs[remainingTabs.length - 1].id : null
    }

    // Remove the tab after a delay to allow for cleanup
    setTimeout(() => {
      const index = tabs.value.findIndex(tab => tab.id === tabId)
      if (index !== -1) {
        tabs.value.splice(index, 1)
      }
    }, 100)
  }

  const switchToTab = (tabId: string) => {
    if (tabId === 'log-monitor-fixed') {
      activeTabId.value = tabId
      if (logMonitorTab.value) {
        logMonitorTab.value.lastActivity = new Date()
      }
      return
    }
    
    const tab = tabs.value.find(t => t.id === tabId)
    if (tab && tab.isActive) {
      activeTabId.value = tabId
      tab.lastActivity = new Date()
    }
  }
  
  const switchToLogMonitor = () => {
    activeTabId.value = 'log-monitor-fixed'
    if (logMonitorTab.value) {
      logMonitorTab.value.lastActivity = new Date()
    }
  }

  const updateTabTitle = (tabId: string, title: string) => {
    const tab = tabs.value.find(t => t.id === tabId)
    if (tab) {
      tab.title = title
    }
  }

  const updateTabStatus = (tabId: string, status: TerminalTab['status']) => {
    const tab = tabs.value.find(t => t.id === tabId)
    if (tab) {
      tab.status = status
    }
  }
  
  const markCommandsExecuted = (tabId: string) => {
    const tab = tabs.value.find(t => t.id === tabId)
    if (tab) {
      tab.commandsExecuted = true
    }
  }
  
  const getTabCommands = (tabId: string): PreExecutionCommand[] => {
    const tab = tabs.value.find(t => t.id === tabId)
    return tab?.preExecutionCommands || []
  }
  
  const hasUnexecutedCommands = (tabId: string): boolean => {
    const tab = tabs.value.find(t => t.id === tabId)
    return !!(tab && tab.preExecutionCommands && !tab.commandsExecuted)
  }

  const updateTabSessionId = (tabId: string, sessionId: string) => {
    const tab = tabs.value.find(t => t.id === tabId)
    if (tab) {
      tab.sessionId = sessionId
    }
  }

  // Create inventory terminal with server context
  const createInventoryTerminal = (serverContext: ServerContext): TerminalTab => {
    const tab = createTab('terminal', undefined, 'inventory', serverContext)
    
    // Set up pre-execution commands for inventory terminal
    tab.preExecutionCommands = generateInventoryCommands(serverContext)
    tab.commandsExecuted = false
    
    return tab
  }
  
  // Create or switch to log monitor tab (ensures single instance)
  const createLogMonitorTab = (): TerminalTab => {
    // Check if there's already an active log monitor tab
    const existingLogTab = logMonitorTabs.value.find(tab => tab.isActive)
    
    if (existingLogTab) {
      // Switch to existing log monitor tab instead of creating a new one
      switchToTab(existingLogTab.id)
      return existingLogTab
    } else {
      // Use the dedicated logMonitorTab instead
      if (logMonitorTab.value) {
        switchToLogMonitor()
        return logMonitorTab.value
      }
      
      // Fallback: create in regular tabs (shouldn't happen)
      const logTab: TerminalTab = {
        id: `tab-${nextTabId.value++}`,
        title: 'Log Monitor',
        type: 'log-monitor',
        isActive: true,
        lastActivity: new Date(),
        status: 'active'
      }
      tabs.value.push(logTab)
      activeTabId.value = logTab.id
      return logTab
    }
  }
  
  // Generate pre-execution commands for inventory terminals
  const generateInventoryCommands = (serverContext: ServerContext): PreExecutionCommand[] => {
    const commands: PreExecutionCommand[] = []
    
    // Determine server type from name
    const serverType = getServerType(serverContext.name)
    
    // Welcome message with server type
    commands.push({
      id: 'welcome',
      command: `echo "=== Connecting to ${serverType} Server: ${serverContext.name} ==="\r`,
      description: 'Display welcome message',
      order: 1
    })
    
    // Server information
    commands.push({
      id: 'server-info',
      command: `echo "Server: ${serverContext.name} (${serverContext.ip})"\r`,
      description: 'Display server information',
      order: 2
    })
    
    commands.push({
      id: 'os-info',
      command: `echo "OS: ${serverContext.os}"\r`,
      description: 'Display OS information',
      order: 3
    })
    
    commands.push({
      id: 'status-info',
      command: `echo "Status: ${serverContext.status.toUpperCase()}"\r`,
      description: 'Display server status',
      order: 4
    })
    
    // Warning for problematic servers
    if (serverContext.status === 'warning' || serverContext.status === 'maintenance') {
      commands.push({
        id: 'warning',
        command: `echo "⚠️  WARNING: Server has ${serverContext.status} status"\r`,
        description: 'Display warning message',
        order: 5
      })
    }
    
    // Resource usage with warnings
    if (serverContext.cpu || serverContext.memory || serverContext.disk) {
      const resourceWarnings = []
      if (serverContext.cpu && serverContext.cpu > 80) resourceWarnings.push('HIGH CPU')
      if (serverContext.memory && serverContext.memory > 80) resourceWarnings.push('HIGH MEMORY')
      if (serverContext.disk && serverContext.disk > 80) resourceWarnings.push('HIGH DISK')
      
      commands.push({
        id: 'resources',
        command: `echo "Resources - CPU: ${serverContext.cpu}% | Memory: ${serverContext.memory}% | Disk: ${serverContext.disk}%${resourceWarnings.length > 0 ? ' ⚠️  ' + resourceWarnings.join(', ') : ''}"\r`,
        description: 'Display resource usage',
        order: 6
      })
    }
    
    // Add server-type specific diagnostic commands
    const typeCommands = getServerTypeCommands(serverType, serverContext)
    typeCommands.forEach(cmd => commands.push(cmd))
    
    // Separator before connection
    commands.push({
      id: 'separator',
      command: `echo "=== Initiating SSH Connection ==="\r`,
      description: 'Display connection separator',
      order: 9
    })
    
    // SSH connection command
    commands.push({
      id: 'ssh-connect',
      command: `ssh ${serverContext.name}@${serverContext.ip}\r`,
      description: 'Connect via SSH',
      order: 10
    })
    
    return commands.sort((a, b) => a.order - b.order)
  }
  
  // Helper function to determine server type
  const getServerType = (serverName: string): string => {
    const name = serverName.toLowerCase()
    if (name.includes('database') || name.includes('db')) return 'Database'
    if (name.includes('web')) return 'Web'
    if (name.includes('api')) return 'API'
    if (name.includes('load-balancer') || name.includes('lb')) return 'Load Balancer'
    if (name.includes('monitoring') || name.includes('monitor')) return 'Monitoring'
    return 'General'
  }
  
  // Helper function to get server-type specific commands
  const getServerTypeCommands = (serverType: string, serverContext: ServerContext): PreExecutionCommand[] => {
    const commands: PreExecutionCommand[] = []
    const order = 7 // Start after basic info
    
    switch (serverType) {
      case 'Database':
        commands.push({
          id: 'db-check',
          command: `echo "Checking database services..."\r`,
          description: 'Database service check',
          order: order
        })
        break
      case 'Web':
        commands.push({
          id: 'web-check',
          command: `echo "Checking web server status..."\r`,
          description: 'Web server status check',
          order: order
        })
        break
      case 'API':
        commands.push({
          id: 'api-check',
          command: `echo "Checking API endpoints..."\r`,
          description: 'API endpoint check',
          order: order
        })
        break
      case 'Load Balancer':
        commands.push({
          id: 'lb-check',
          command: `echo "Checking load balancer configuration..."\r`,
          description: 'Load balancer check',
          order: order
        })
        break
      case 'Monitoring':
        commands.push({
          id: 'monitor-check',
          command: `echo "Checking monitoring services..."\r`,
          description: 'Monitoring service check',
          order: order
        })
        break
      default:
        commands.push({
          id: 'general-check',
          command: `echo "Performing general system check..."\r`,
          description: 'General system check',
          order: order
        })
    }
    
    return commands
  }

  // Initialize with default terminal tab and log monitor
  const initializeDefaultTab = () => {
    if (tabs.value.length === 0) {
      createTab('terminal', 'Terminal 1')
    }
    
    // Always create log monitor tab if not exists
    if (!logMonitorTab.value) {
      const logTab: TerminalTab = {
        id: 'log-monitor-fixed',
        title: 'Log Monitor',
        type: 'log-monitor',
        isActive: true,
        lastActivity: new Date(),
        status: 'active'
      }
      logMonitorTab.value = logTab
    }
  }

  return {
    // State
    tabs,
    activeTabId,
    logMonitorTab,
    
    // Getters
    activeTabs,
    displayTabs,
    activeTab,
    terminalTabs,
    aiChatTabs,
    logMonitorTabs,
    isLogMonitorActive,

    // Actions
    createTab,
    createInventoryTerminal,
    createLogMonitorTab,
    closeTab,
    switchToTab,
    switchToLogMonitor,
    updateTabTitle,
    updateTabStatus,
    updateTabSessionId,
    initializeDefaultTab,
    markCommandsExecuted,
    getTabCommands,
    hasUnexecutedCommands,
    
    // Helper functions
    getServerType
  }
})