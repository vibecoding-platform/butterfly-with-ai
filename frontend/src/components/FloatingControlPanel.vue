<template>
  <div class="sidebar-control-panel">
    <!-- Panel Toggle Button (positioned at edge of panel) -->
    <div 
      class="control-toggle"
      :class="{ 'panel-visible': panelVisible }"
      @click="handleToggle"
    >
      <div class="toggle-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path v-if="panelVisible" d="M15 18l-6-6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path v-else d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
    </div>

    <!-- Quick Access Buttons (always visible in panel) -->
    <div v-if="panelVisible" class="quick-actions">
      <button class="quick-action" title="Chat Mode" @click="$emit('switch-tab', 'chat')">
        💬
      </button>
      <button class="quick-action" title="Debug Info" @click="$emit('switch-tab', 'debug')">
        🔍
      </button>
      <button class="quick-action" title="Socket Monitor" @click="$emit('switch-tab', 'socket-monitor')">
        📊
      </button>
      <button class="quick-action" title="Test Mode" @click="$emit('switch-tab', 'test')">
        🧪
      </button>
    </div>

    <!-- Connection Status -->
    <div v-if="panelVisible" class="connection-status">
      <div class="status-indicator connected" title="Connected to AetherTerm"></div>
      <span class="status-text">Connected</span>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  panelVisible: boolean
  panelWidth: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'toggle-panel': []
  'switch-tab': [tab: string]
}>()

const handleToggle = () => {
  emit('toggle-panel')
}
</script>

<style scoped>
.sidebar-control-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #2d2d2d;
}

.control-toggle {
  position: absolute;
  top: 50%;
  right: -20px;
  transform: translateY(-50%);
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 0 8px 8px 0;
  padding: 8px 6px;
  cursor: pointer;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  width: 20px;
  height: 40px;
}

.control-toggle:hover {
  background: #45a049;
  transform: translateY(-50%) translateX(2px);
  box-shadow: 4px 0 12px rgba(0, 0, 0, 0.2);
}

.control-toggle.panel-visible {
  background: #ff9800;
}

.control-toggle.panel-visible:hover {
  background: #f57c00;
}

.toggle-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  margin-top: auto;
  margin-bottom: 60px;
}

.quick-action {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 8px;
  background: #3d3d3d;
  color: #ccc;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #555;
}

.quick-action:hover {
  background: #4d4d4d;
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  margin-top: auto;
  border-top: 1px solid #444;
  background: #252525;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4caf50;
  box-shadow: 0 0 4px rgba(76, 175, 80, 0.5);
  animation: pulse 2s infinite;
}

.status-indicator.connected {
  background: #4caf50;
}

.status-indicator.disconnected {
  background: #f44336;
  box-shadow: 0 0 4px rgba(244, 67, 54, 0.5);
}

.status-text {
  font-size: 11px;
  color: #999;
  font-weight: 500;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

/* Mobile adjustments */
@media (max-width: 768px) {
  .quick-actions {
    padding: 12px;
    gap: 6px;
  }
  
  .quick-action {
    width: 35px;
    height: 35px;
    font-size: 14px;
  }
  
  .connection-status {
    padding: 8px 12px;
  }
}
</style>