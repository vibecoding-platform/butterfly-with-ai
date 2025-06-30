<template>
  <div class="tab-content-wrapper">
    <TerminalTabComponent 
      v-if="tab.type === 'terminal'" 
      :tab-id="tab.id"
      :sub-type="tab.subType"
      @click="$emit('click')"
    />
    
    <AIAgentTab 
      v-else-if="tab.type === 'ai-agent'" 
      :tab-id="tab.id"
    />
    
    <LogMonitorTab 
      v-else-if="tab.type === 'log-monitor'" 
    />
    
    <div v-else class="unknown-content">
      <div class="unknown-message">
        <h4>Unknown tab type: {{ tab.type }}</h4>
        <p>This tab type is not supported.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { type TerminalTab } from '../../../stores/terminalTabStore'
import TerminalTabComponent from '../AetherTerminalComponent.vue'
import AIAgentTab from '../AIAgentTab.vue'
import LogMonitorTab from '../LogMonitorTab.vue'

interface Props {
  tab: TerminalTab
}

interface Emits {
  (e: 'click'): void
}

defineProps<Props>()
defineEmits<Emits>()
</script>

<style scoped lang="scss">
@import '../../../assets/styles/base.scss';

.tab-content-wrapper {
  @include flex-column;
  flex: 1;
  overflow: hidden;
}

.terminal-content {
  @include flex-column;
  flex: 1;
  overflow: hidden;
}

.ai-chat-content {
  @include flex-column;
  flex: 1;
  overflow: hidden;
}

.xterm-container {
  flex: 1;
  border-top: $border-width solid var(--color-border-primary);
  min-height: 300px;
  background-color: var(--color-terminal-bg);
}

.unknown-content {
  @include flex-column-center;
  flex: 1;
  text-align: center;
  color: var(--color-text-muted);

  .unknown-message {
    padding: $spacing-xl;
    
    h4 {
      margin-bottom: $spacing-sm;
      color: var(--color-status-warning);
    }

    p {
      color: var(--color-text-subtle);
      font-size: $font-size-sm;
    }
  }
}
</style>