<template>
  <div class="tab-manager">
    <!-- Tab Bar -->
    <div class="tab-bar">
      <!-- Terminal Tabs -->
      <div class="tab-group terminal-group">
        <div class="tab-group-label">Terminals</div>
        <div 
          v-for="tab in terminalTabs" 
          :key="tab.id"
          class="tab terminal-tab"
          :class="{ 
            'active': tab.id === session.activeTabId,
            'shared': tab.isShared && tab.connectedUsers.length > 1
          }"
          @click="switchToTab(tab.id)"
        >
          <div class="tab-content">
            <span class="tab-title">{{ tab.title }}</span>
            <span v-if="tab.isShared && tab.connectedUsers.length > 1" class="user-indicator">
              {{ tab.connectedUsers.length }}
            </span>
          </div>
          <button 
            class="close-tab"
            @click.stop="closeTab(tab.id)"
          >
            ×
          </button>
        </div>
      </div>

      <!-- AI Assistant Tabs -->
      <div class="tab-group ai-group" v-if="aiAssistantTabs.length > 0">
        <div class="tab-group-label">AI Assistants</div>
        <div 
          v-for="tab in aiAssistantTabs" 
          :key="tab.id"
          class="tab ai-tab"
          :class="{ 
            'active': tab.id === session.activeTabId
          }"
          @click="switchToTab(tab.id)"
        >
          <div class="tab-content">
            <span class="tab-icon">🤖</span>
            <span class="tab-title">{{ tab.title }}</span>
            <span class="assistant-type">{{ tab.assistantType }}</span>
          </div>
          <button 
            class="close-tab"
            @click.stop="closeTab(tab.id)"
          >
            ×
          </button>
        </div>
      </div>

      <!-- New Tab Dropdown -->
      <div class="new-tab-container">
        <button 
          class="new-tab-btn"
          @click="toggleNewTabMenu"
          ref="newTabButton"
        >
          + New
        </button>
        
        <div 
          v-if="showNewTabMenu" 
          class="new-tab-menu"
          ref="newTabMenu"
        >
          <button @click="createTerminalTab">
            🖥️ Terminal
          </button>
          <button @click="createAIAssistant('code')">
            💻 Code Assistant
          </button>
          <button @click="createAIAssistant('operations')">
            ⚙️ Operations Assistant
          </button>
          <button @click="createAIAssistant('general')">
            🤖 General Assistant
          </button>
        </div>
      </div>
    </div>

    <!-- Tab Content -->
    <div class="tab-content-area">
      <!-- Terminal Tab Content -->
      <div 
        v-if="activeTab?.type === 'terminal'"
        class="terminal-content"
      >
        <TerminalPaneManager 
          :key="activeTab.id"
          :terminal-tab="activeTab"
          :session-id="session.id"
          :tab-id="activeTab.id"
        />
      </div>

      <!-- AI Assistant Tab Content -->
      <div 
        v-else-if="activeTab?.type === 'ai_assistant'"
        class="ai-content"
      >
        <AIAssistantComponent 
          :key="activeTab.id"
          :tab="activeTab as AIAssistantTab"
          :session-id="session.id"
        />
      </div>

      <!-- No Active Tab -->
      <div v-else class="no-tab-content">
        <div class="empty-message">
          <h3>No active tab</h3>
          <p>Create a new tab to get started</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useSessionStore } from '@/stores/sessionStore'
import TerminalPaneManager from './TerminalPaneManager.vue'
import AIAssistantComponent from './AIAssistantComponent.vue'
import type { Session, Tab, TerminalTab, AIAssistantTab, TabType } from '@/types/session'
import { getWorkspaceService } from '@/services/workspace/WorkspaceSocketService'

interface Props {
  session: Session
}

const props = defineProps<Props>()
const sessionStore = useSessionStore()
const workspaceService = getWorkspaceService()

// Tab menu state
const showNewTabMenu = ref(false)
const newTabButton = ref<HTMLElement>()
const newTabMenu = ref<HTMLElement>()

// Computed properties
const terminalTabs = computed(() => 
  props.session.tabs.filter(tab => tab.type === 'terminal') as TerminalTab[]
)

const aiAssistantTabs = computed(() => 
  props.session.tabs.filter(tab => tab.type === 'ai_assistant') as AIAssistantTab[]
)

const activeTab = computed(() => 
  props.session.tabs.find(tab => tab.id === props.session.activeTabId)
)

// Tab management functions
const switchToTab = (tabId: string) => {
  sessionStore.switchToTab(props.session.id, tabId)
  // TODO: Emit tab:switch event
}

const closeTab = (tabId: string) => {
  sessionStore.removeTab(props.session.id, tabId)
  // TODO: Emit tab:close event
}

const createTerminalTab = async () => {
  const terminalCount = terminalTabs.value.length
  
  try {
    console.log('🆕 Creating new terminal tab via WorkspaceService')
    
    // Use WorkspaceSocketService instead of direct Socket.IO
    const response = await workspaceService.createTab({
      title: `Terminal ${terminalCount + 1}`,
      type: 'terminal',
      sessionId: props.session.id
    })
    
    if (response.success && response.tab) {
      // Tab will be automatically added to session via WorkspaceService event handling
      // Just update UI state
      showNewTabMenu.value = false
      
      // Switch to the new tab
      sessionStore.switchToTab(props.session.id, response.tab.id)
      
      console.log('📋 Tab creation completed')
    } else {
      throw new Error(response.error || 'Tab creation failed')
    }
    
  } catch (error) {
    console.error('❌ Error creating terminal tab:', error)
    // TODO: Show error message to user
  }
}

const createAIAssistant = async (assistantType: 'code' | 'operations' | 'general') => {
  const aiCount = aiAssistantTabs.value.length
  const titles = {
    code: 'Code Assistant',
    operations: 'Operations Assistant', 
    general: 'General Assistant'
  }
  
  try {
    console.log('🤖 Creating new AI assistant tab via WorkspaceService')
    
    const response = await workspaceService.createTab({
      title: `${titles[assistantType]} ${aiCount + 1}`,
      type: 'ai_assistant',
      assistantType,
      sessionId: props.session.id
    })
    
    if (response.success && response.tab) {
      console.log('✅ AI Assistant tab created successfully:', response.tab.id)
      
      // Tab will be automatically added via WorkspaceService event handling
      showNewTabMenu.value = false
      
      // Switch to the new tab
      sessionStore.switchToTab(props.session.id, response.tab.id)
    } else {
      throw new Error(response.error || 'AI Assistant tab creation failed')
    }
    
  } catch (error) {
    console.error('❌ Error creating AI assistant tab:', error)
    // TODO: Show error message to user
  }
}

const toggleNewTabMenu = () => {
  showNewTabMenu.value = !showNewTabMenu.value
}

// Close menu when clicking outside
const handleClickOutside = (event: Event) => {
  if (
    showNewTabMenu.value &&
    newTabButton.value &&
    newTabMenu.value &&
    !newTabButton.value.contains(event.target as Node) &&
    !newTabMenu.value.contains(event.target as Node)
  ) {
    showNewTabMenu.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.tab-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #1e1e1e;
}

.tab-bar {
  display: flex;
  background-color: #2d2d2d;
  border-bottom: 1px solid #444;
  overflow-x: auto;
  flex-shrink: 0;
  padding: 4px 0;
}

.tab-group {
  display: flex;
  align-items: center;
  margin-right: 16px;
}

.tab-group-label {
  font-size: 11px;
  color: #888;
  text-transform: uppercase;
  font-weight: 600;
  padding: 4px 8px;
  margin-right: 4px;
  border-right: 1px solid #444;
}

.tab {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  margin: 2px;
  border-radius: 4px;
  cursor: pointer;
  background-color: #3d3d3d;
  color: #ccc;
  transition: all 0.2s ease;
  min-width: 100px;
  max-width: 180px;
  border: 1px solid transparent;
}

.tab:hover {
  background-color: #4d4d4d;
  color: #fff;
}

.tab.active {
  background-color: #4caf50;
  color: white;
  border-color: #4caf50;
}

.terminal-tab.shared {
  border-top: 2px solid #2196f3;
}

.ai-tab {
  background-color: #3d2f4d;
  border-color: #7b1fa2;
}

.ai-tab:hover {
  background-color: #4d3f5d;
}

.ai-tab.active {
  background-color: #7b1fa2;
  border-color: #9c27b0;
}

.tab-content {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
}

.tab-title {
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-icon {
  font-size: 14px;
}

.user-indicator {
  background-color: rgba(33, 150, 243, 0.8);
  color: white;
  font-size: 9px;
  padding: 1px 4px;
  border-radius: 10px;
  font-weight: bold;
  min-width: 14px;
  text-align: center;
}

.assistant-type {
  background-color: rgba(156, 39, 176, 0.3);
  color: #e1bee7;
  font-size: 9px;
  padding: 1px 4px;
  border-radius: 8px;
  text-transform: uppercase;
  font-weight: 500;
}

.close-tab {
  background: none;
  border: none;
  color: inherit;
  font-size: 14px;
  cursor: pointer;
  padding: 0 4px;
  margin-left: 4px;
  opacity: 0.6;
  transition: opacity 0.2s ease;
}

.close-tab:hover {
  opacity: 1;
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.new-tab-container {
  position: relative;
  margin-left: auto;
  margin-right: 8px;
}

.new-tab-btn {
  background-color: #4caf50;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: background-color 0.2s ease;
}

.new-tab-btn:hover {
  background-color: #45a049;
}

.new-tab-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background-color: #3d3d3d;
  border: 1px solid #555;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  min-width: 160px;
  z-index: 1000;
  margin-top: 4px;
}

.new-tab-menu button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  background: none;
  border: none;
  color: #ccc;
  font-size: 13px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.new-tab-menu button:first-child {
  border-radius: 6px 6px 0 0;
}

.new-tab-menu button:last-child {
  border-radius: 0 0 6px 6px;
}

.new-tab-menu button:hover {
  background-color: #4d4d4d;
  color: #fff;
}

.tab-content-area {
  flex: 1;
  overflow: hidden;
  background-color: #1e1e1e;
}

.terminal-content,
.ai-content {
  height: 100%;
}

.no-tab-content {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-message {
  text-align: center;
  color: #888;
}

.empty-message h3 {
  color: #4caf50;
  margin-bottom: 8px;
  font-size: 18px;
}

.empty-message p {
  font-size: 14px;
}

/* Scrollbar for tab bar */
.tab-bar::-webkit-scrollbar {
  height: 3px;
}

.tab-bar::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.tab-bar::-webkit-scrollbar-thumb {
  background: #666;
  border-radius: 3px;
}

.tab-bar::-webkit-scrollbar-thumb:hover {
  background: #888;
}
</style>