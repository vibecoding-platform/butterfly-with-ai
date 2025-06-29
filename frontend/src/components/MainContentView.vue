<template>
  <div class="main-content-view" @contextmenu.prevent>
    <!-- Use TerminalView to handle all tab types -->
    <TabContentArea 
      :is-terminal-paused="isTerminalPaused"
      :is-supervisor-locked="isSupervisorLocked"
      @terminal-initialized="$emit('terminal-initialized')"
    />
  </div>
</template>

<script setup lang="ts">
import TabContentArea from './terminal/TabContentArea.vue'

interface Props {
  isTerminalPaused?: boolean
  isSupervisorLocked?: boolean
}

interface Emits {
  (e: 'terminal-initialized'): void
}

defineProps<Props>()
defineEmits<Emits>()
</script>

<style scoped>
.main-content-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  position: relative;
}

.tab-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.terminal-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.ai-chat-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.log-monitor-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  background-color: var(--color-bg-primary);
}

.no-tabs-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  color: #888;
}

.no-tabs-message h3 {
  margin-bottom: 8px;
  color: #aaa;
}

.no-tabs-message p {
  color: #666;
  font-size: 14px;
}
</style>