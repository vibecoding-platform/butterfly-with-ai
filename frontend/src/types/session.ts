export interface TerminalPane {
  id: string
  terminalId: string | null
  isActive: boolean
  title?: string
  shellType?: string
  workingDirectory?: string
  position?: {
    x: number
    y: number
    width: number
    height: number
  }
}

export interface TerminalTab {
  id: string
  title: string
  type: 'terminal'
  isActive: boolean
  isShared: boolean
  connectedUsers: any[]
  panes: TerminalPane[]
  activePaneId?: string
  layout?: string
}

export interface AIAssistantTab {
  id: string
  title: string
  type: 'ai_assistant'
  isActive: boolean
  assistantType: 'code' | 'operations' | 'general'
  contextSessionId?: string
  conversationHistory?: any[]
}

export type Tab = TerminalTab | AIAssistantTab
export type TabType = 'terminal' | 'ai_assistant'

export interface Session {
  id: string
  name: string
  tabs: Tab[]
  activeTabId: string | null
}