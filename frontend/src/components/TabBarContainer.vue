<template>
  <div class="terminal-tab-bar" @contextmenu.prevent>
    <!-- Existing Tabs -->
    <div class="tab-list">
      <div
        v-for="tab in tabStore.displayTabs"
        :key="tab.id"
        class="terminal-tab"
        :class="{ 
          'active': tab.id === tabStore.activeTabId,
          'terminal': tab.type === 'terminal',
          'ai-agent': tab.type === 'ai-agent',
          'log-monitor': tab.type === 'log-monitor',
          'pure-terminal': tab.type === 'terminal' && tab.subType === 'pure',
          'inventory-terminal': tab.type === 'terminal' && tab.subType === 'inventory',
          'connecting': tab.status === 'connecting',
          'error': tab.status === 'error'
        }"
        @click="tabStore.switchToTab(tab.id)"
      >
        <div class="tab-content">
          <span class="tab-icon">
            {{ tab.type === 'terminal' 
                ? (tab.subType === 'inventory' ? '📊' : '💻') 
                : tab.type === 'ai-agent'
                  ? '🤖'
                  : '📈' }}
          </span>
          <span class="tab-title">{{ tab.title }}</span>
          <span class="tab-status-indicator" :class="tab.status"></span>
        </div>
        <button 
          v-if="tabStore.displayTabs.length > 1"
          @click.stop="tabStore.closeTab(tab.id)"
          class="tab-close-btn"
          title="Close Tab"
        >
          ✕
        </button>
      </div>
    </div>

    <!-- Add Tab Button with Menu -->
    <TabCreationMenu @add-tab="addNewTab" />

    <!-- Fixed Log Monitor Tab -->
    <div
      class="terminal-tab fixed-tab log-monitor-tab"
      :class="{ 'active': isLogMonitorActive }"
      @click="switchToLogMonitor"
    >
      <div class="tab-content">
        <span class="tab-icon">📈</span>
        <span class="tab-title">Log Monitor</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useTerminalTabStore } from '../stores/terminalTabStore'
import TabCreationMenu from './terminal/tabs/TabCreationMenu.vue'

const tabStore = useTerminalTabStore()

// Check if log monitor tab is active
const isLogMonitorActive = computed(() => {
  return tabStore.isLogMonitorActive
})

// Switch to log monitor
const switchToLogMonitor = () => {
  tabStore.switchToLogMonitor()
}

const addNewTab = (type: 'terminal' | 'ai-agent', subType?: 'pure' | 'inventory') => {
  tabStore.createTab(type, undefined, subType)
}

onMounted(() => {
  // Initialize default tab if none exist
  tabStore.initializeDefaultTab()
})
</script>

<style scoped>
.terminal-tab-bar {
  display: flex;
  align-items: center;
  background-color: #1e1e1e;
  border-bottom: 1px solid #444;
  min-height: 40px;
  position: relative;
  overflow-x: auto;
  overflow-y: visible;
}

.tab-list {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.terminal-tab {
  display: flex;
  align-items: center;
  min-width: 120px;
  max-width: 200px;
  height: 40px;
  background-color: #2d2d2d;
  border-right: 1px solid #444;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  padding: 0 12px;
  gap: 8px;
}

.terminal-tab:hover {
  background-color: #3d3d3d;
}

.terminal-tab.active {
  background-color: #4caf50;
  color: white;
}

.terminal-tab.terminal {
  border-top: 2px solid #2196f3;
}

.terminal-tab.ai-agent {
  border-top: 2px solid #9c27b0;
}

.terminal-tab.log-monitor {
  border-top: 2px solid #ff9800;
}

.terminal-tab.pure-terminal {
  border-top: 2px solid #2196f3;
}

.terminal-tab.inventory-terminal {
  border-top: 2px solid #ff9800;
}

.terminal-tab.active.terminal {
  border-top: 2px solid #1976d2;
}

.terminal-tab.active.pure-terminal {
  border-top: 2px solid #1976d2;
}

.terminal-tab.active.inventory-terminal {
  border-top: 2px solid #f57c00;
}

.terminal-tab.active.ai-agent {
  border-top: 2px solid #7b1fa2;
}

.terminal-tab.active.log-monitor {
  border-top: 2px solid #f57c00;
}

/* Fixed tab styling */
.terminal-tab.fixed-tab {
  border-left: 2px solid #444;
  background-color: #1a1a1a;
  position: relative;
}

.terminal-tab.fixed-tab:hover {
  background-color: #2a2a2a;
}

.terminal-tab.fixed-tab.active {
  background-color: #f57c00;
  color: white;
}

.terminal-tab.fixed-tab::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background-color: #f57c00;
}

.tab-content {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.tab-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.tab-title {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.tab-status-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-left: auto;
}

.tab-status-indicator.active {
  background-color: #4caf50;
}

.tab-status-indicator.connecting {
  background-color: #ff9800;
  animation: pulse 2s infinite;
}

.tab-status-indicator.disconnected {
  background-color: #f44336;
}

.tab-status-indicator.error {
  background-color: #f44336;
  animation: blink 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.tab-close-btn {
  background: none;
  border: none;
  color: #ccc;
  font-size: 12px;
  cursor: pointer;
  padding: 2px;
  border-radius: 2px;
  transition: all 0.2s ease;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tab-close-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: white;
}

.terminal-tab.active .tab-close-btn {
  color: rgba(255, 255, 255, 0.8);
}

.terminal-tab.active .tab-close-btn:hover {
  background-color: rgba(255, 255, 255, 0.2);
  color: white;
}

/* Responsive */
@media (max-width: 768px) {
  .terminal-tab {
    min-width: 100px;
    max-width: 150px;
    padding: 0 8px;
  }
  
  .tab-title {
    font-size: 12px;
  }
}
</style>