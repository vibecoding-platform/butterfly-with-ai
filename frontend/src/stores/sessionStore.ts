import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { Session, Tab, TerminalTab, AIAssistantTab } from '@/types/session'

export const useSessionStore = defineStore('session', () => {
  // Default session
  const defaultSession: Session = reactive({
    id: 'default-session',
    name: 'Default Session',
    tabs: [
      {
        id: 'terminal-default',
        title: 'Terminal 1',
        type: 'terminal' as const,
        isActive: true,
        isShared: false,
        connectedUsers: [],
        panes: [
          {
            id: 'pane-default',
            terminalId: null,
            isActive: true
          }
        ],
        activePaneId: 'pane-default',
        layout: 'horizontal'
      }
    ],
    activeTabId: 'terminal-default'
  })

  const sessions = ref<Session[]>([defaultSession])
  const activeSessionId = ref('default-session')

  // Getters
  const activeSession = () => {
    return sessions.value.find(s => s.id === activeSessionId.value) || defaultSession
  }

  // Actions
  const switchToTab = (sessionId: string, tabId: string) => {
    const session = sessions.value.find(s => s.id === sessionId)
    if (session && session.tabs.find(t => t.id === tabId)) {
      session.activeTabId = tabId
      console.log(`🎯 Switched to tab ${tabId} in session ${sessionId}`)
    }
  }

  const addTab = (sessionId: string, tab: Tab) => {
    const session = sessions.value.find(s => s.id === sessionId)
    if (session) {
      session.tabs.push(tab)
      console.log(`➕ Added tab ${tab.id} to session ${sessionId}`)
    }
  }

  const removeTab = (sessionId: string, tabId: string) => {
    const session = sessions.value.find(s => s.id === sessionId)
    if (session) {
      const tabIndex = session.tabs.findIndex(t => t.id === tabId)
      if (tabIndex !== -1) {
        session.tabs.splice(tabIndex, 1)
        
        // If this was the active tab, switch to another one
        if (session.activeTabId === tabId) {
          session.activeTabId = session.tabs.length > 0 ? session.tabs[0].id : null
        }
        
        console.log(`❌ Removed tab ${tabId} from session ${sessionId}`)
      }
    }
  }

  const createTerminalTab = (sessionId: string, title: string): TerminalTab => {
    const tabId = `terminal-${Date.now()}`
    const paneId = `pane-${tabId}`
    return {
      id: tabId,
      title,
      type: 'terminal',
      isActive: true,
      isShared: false,
      connectedUsers: [],
      panes: [
        {
          id: paneId,
          terminalId: null,
          isActive: true
        }
      ],
      activePaneId: paneId,
      layout: 'horizontal'
    }
  }

  const createAIAssistantTab = (sessionId: string, title: string, assistantType: 'code' | 'operations' | 'general'): AIAssistantTab => {
    return {
      id: `ai-${Date.now()}`,
      title,
      type: 'ai_assistant',
      isActive: true,
      assistantType,
      contextSessionId: sessionId,
      conversationHistory: []
    }
  }

  return {
    sessions,
    activeSessionId,
    activeSession,
    switchToTab,
    addTab,
    removeTab,
    createTerminalTab,
    createAIAssistantTab
  }
})