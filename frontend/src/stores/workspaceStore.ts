import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAetherTerminalServiceStore } from './aetherTerminalServiceStore'
import { useTerminalTabStore, type TerminalTab } from './terminalTabStore'

export interface WorkspaceState {
  id: string
  name: string
  lastAccessed: Date
  tabs: TerminalTab[]
  isActive: boolean
}

export const useWorkspaceStore = defineStore('workspace', () => {
  // State
  const currentWorkspace = ref<WorkspaceState | null>(null)
  const workspaces = ref<WorkspaceState[]>([])
  const isResuming = ref(false)
  const resumeError = ref<string | null>(null)

  // Store references
  const terminalService = useAetherTerminalServiceStore()
  const terminalTabStore = useTerminalTabStore()

  // Getters
  const hasCurrentWorkspace = computed(() => !!currentWorkspace.value)
  const workspaceCount = computed(() => workspaces.value.length)

  // Actions
  const createWorkspace = (name?: string): WorkspaceState => {
    const workspaceId = `workspace_${Date.now()}`
    const workspace: WorkspaceState = {
      id: workspaceId,
      name: name || `Workspace ${workspaces.value.length + 1}`,
      lastAccessed: new Date(),
      tabs: [],
      isActive: true
    }

    workspaces.value.push(workspace)
    currentWorkspace.value = workspace
    
    console.log('📋 WORKSPACE: Created workspace:', workspace)
    return workspace
  }

  const switchToWorkspace = (workspaceId: string) => {
    const workspace = workspaces.value.find(w => w.id === workspaceId)
    if (workspace) {
      if (currentWorkspace.value) {
        currentWorkspace.value.isActive = false
      }
      
      workspace.isActive = true
      workspace.lastAccessed = new Date()
      currentWorkspace.value = workspace
      
      console.log('📋 WORKSPACE: Switched to workspace:', workspace.name)
    }
  }

  const saveCurrentWorkspace = () => {
    if (!currentWorkspace.value) {
      console.warn('📋 WORKSPACE: No current workspace to save')
      return
    }

    // Capture current tabs
    currentWorkspace.value.tabs = terminalTabStore.activeTabs.map(tab => ({
      ...tab,
      lastActivity: new Date()
    }))
    
    currentWorkspace.value.lastAccessed = new Date()
    
    console.log('📋 WORKSPACE: Saved workspace with', currentWorkspace.value.tabs.length, 'tabs')
  }

  const resumeWorkspace = async (workspaceId?: string): Promise<boolean> => {
    try {
      isResuming.value = true
      resumeError.value = null

      let targetWorkspace: WorkspaceState | null = null

      if (workspaceId) {
        targetWorkspace = workspaces.value.find(w => w.id === workspaceId) || null
      } else {
        // Find the most recently accessed workspace
        targetWorkspace = workspaces.value
          .filter(w => w.tabs.length > 0)
          .sort((a, b) => b.lastAccessed.getTime() - a.lastAccessed.getTime())[0] || null
      }

      if (!targetWorkspace) {
        console.log('📋 WORKSPACE: No workspace to resume, creating default')
        createDefaultWorkspace()
        return true
      }

      console.log('📋 WORKSPACE: Resuming workspace:', targetWorkspace.name, 'with', targetWorkspace.tabs.length, 'tabs')

      // Ensure we have a socket connection
      if (!terminalService.socket) {
        console.log('📋 WORKSPACE: No socket connection, connecting first...')
        await terminalService.connect()
      }

      // Send workspace resume request to backend
      return new Promise((resolve) => {
        const resumeData = {
          workspaceId: targetWorkspace!.id,
          tabs: targetWorkspace!.tabs.map(tab => ({
            id: tab.id,
            sessionId: tab.sessionId,
            type: tab.type,
            subType: tab.subType,
            title: tab.title
          }))
        }

        console.log('📋 WORKSPACE: Sending resume_workspace event:', resumeData)

        // Listen for workspace resume response
        const handleWorkspaceResumed = (data: any) => {
          console.log('📋 WORKSPACE: Received workspace_resumed:', data)
          
          terminalService.socket?.off('workspace_resumed', handleWorkspaceResumed)
          terminalService.socket?.off('workspace_error', handleWorkspaceError)

          if (data.workspaceId === targetWorkspace!.id) {
            // Update current workspace
            currentWorkspace.value = targetWorkspace
            targetWorkspace!.isActive = true
            targetWorkspace!.lastAccessed = new Date()

            // Update sessions for resumed and created tabs
            const allTabResults = (data.resumedTabs || []).concat(data.createdTabs || [])
            allTabResults.forEach((tabResult: any) => {
              terminalTabStore.setTabSession(tabResult.tabId, tabResult.sessionId)
            })

            console.log('📋 WORKSPACE: Workspace resumed successfully:', data.message)
            resolve(true)
          }
        }

        const handleWorkspaceError = (data: any) => {
          console.error('📋 WORKSPACE: Workspace resume error:', data)
          
          terminalService.socket?.off('workspace_resumed', handleWorkspaceResumed)
          terminalService.socket?.off('workspace_error', handleWorkspaceError)
          
          resumeError.value = data.error || 'Failed to resume workspace'
          resolve(false)
        }

        terminalService.socket?.on('workspace_resumed', handleWorkspaceResumed)
        terminalService.socket?.on('workspace_error', handleWorkspaceError)

        // Send the resume request
        terminalService.socket?.emit('resume_workspace', resumeData)

        // Timeout after 10 seconds
        setTimeout(() => {
          terminalService.socket?.off('workspace_resumed', handleWorkspaceResumed)
          terminalService.socket?.off('workspace_error', handleWorkspaceError)
          resumeError.value = 'Workspace resume timeout'
          resolve(false)
        }, 10000)
      })

    } catch (error) {
      console.error('📋 WORKSPACE: Error resuming workspace:', error)
      resumeError.value = error instanceof Error ? error.message : 'Unknown error'
      return false
    } finally {
      isResuming.value = false
    }
  }

  const createDefaultWorkspace = () => {
    const workspace = createWorkspace('Default Workspace')
    
    // Create a default terminal tab
    const defaultTab = terminalTabStore.createTab('terminal', 'Terminal 1', 'pure')
    workspace.tabs = [defaultTab]
    
    console.log('📋 WORKSPACE: Created default workspace with terminal tab')
  }

  const initializeWorkspace = async () => {
    console.log('📋 WORKSPACE: Initializing workspace system...')
    
    // Try to resume the last workspace, or create default
    const resumed = await resumeWorkspace()
    
    if (!resumed && !currentWorkspace.value) {
      createDefaultWorkspace()
    }
    
    console.log('📋 WORKSPACE: Workspace system initialized')
  }

  const updateWorkspaceFromTabs = () => {
    if (currentWorkspace.value) {
      saveCurrentWorkspace()
    }
  }

  // Automatically save workspace when tabs change
  terminalTabStore.$subscribe(() => {
    updateWorkspaceFromTabs()
  })

  return {
    // State
    currentWorkspace,
    workspaces,
    isResuming,
    resumeError,

    // Getters
    hasCurrentWorkspace,
    workspaceCount,

    // Actions
    createWorkspace,
    switchToWorkspace,
    saveCurrentWorkspace,
    resumeWorkspace,
    createDefaultWorkspace,
    initializeWorkspace,
    updateWorkspaceFromTabs
  }
})