<template>
  <div class="terminal-status" @contextmenu.prevent>
    <!-- Connection Status -->
    <div v-if="!terminalStore.connectionState.isConnected" class="status-bar connection-status">
      <div class="status-indicator" :class="connectionStatusClass">
        {{ connectionStatusText }}
      </div>
      <div v-if="terminalStore.connectionState.isReconnecting" class="reconnect-info">
        Reconnection attempt:
        {{ terminalStore.connectionState.reconnectAttempts }}/{{
          terminalStore.connectionState.maxReconnectAttempts
        }}
      </div>
    </div>

    <!-- Terminal Lock Status -->
    <div v-if="terminalStore.isTerminalBlocked" class="status-bar lock-status">
      <div class="status-indicator">🔒 Terminal Locked</div>
    </div>

    <!-- Terminal Pause Status -->
    <div v-if="isTerminalPaused" class="status-bar pause-status">
      <div class="status-indicator">
        ⏸️ Input Paused
        <button @click="$emit('resume')" class="resume-btn">Resume</button>
      </div>
    </div>

    <!-- Terminal Blocked Overlay -->
    <div v-if="terminalStore.isTerminalBlocked" class="terminal-overlay"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAetherTerminalServiceStore } from '../../stores/aetherTerminalServiceStore'

interface Props {
  isTerminalPaused?: boolean
}

interface Emits {
  (e: 'resume'): void
}

defineProps<Props>()
defineEmits<Emits>()

const terminalStore = useAetherTerminalServiceStore()

// Connection status computed properties
const connectionStatusClass = computed(() => {
  switch (terminalStore.connectionStatus) {
    case 'connected':
      return 'status-connected'
    case 'connecting':
      return 'status-connecting'
    case 'reconnecting':
      return 'status-reconnecting'
    default:
      return 'status-disconnected'
  }
})

const connectionStatusText = computed(() => {
  switch (terminalStore.connectionStatus) {
    case 'connected':
      return 'Connected'
    case 'connecting':
      return 'Connecting...'
    case 'reconnecting':
      return 'Reconnecting...'
    default:
      return 'Disconnected'
  }
})
</script>

<style scoped lang="scss">
@import '../../assets/styles/base.scss';

.terminal-status {
  position: relative;
}

.status-bar {
  @include terminal-status-bar;
  @include flex-between;
}

.connection-status {
  background-color: var(--color-bg-secondary);
}

.lock-status {
  background-color: var(--color-status-error);
  text-align: center;
  color: var(--color-text-primary);
}

.pause-status {
  background-color: var(--color-status-warning);
  text-align: center;
  color: var(--color-bg-primary);
}

.status-indicator {
  @include flex-center;
  gap: $spacing-sm;
  font-size: $font-size-sm;
  font-weight: $font-weight-bold;
  
  &.status-connected {
    @include status-connected;
  }
  
  &.status-connecting {
    @include status-connecting;
  }
  
  &.status-reconnecting {
    @include status-connecting;
  }
  
  &.status-disconnected {
    @include status-disconnected;
  }
}

.reconnect-info {
  font-size: $font-size-xs;
  color: var(--color-text-muted);
}

.resume-btn {
  @include button-primary;
  height: $button-height-sm;
  padding: 0 $button-padding-x-sm;
  font-size: $font-size-xs;
  background-color: var(--color-status-success);
  
  &:hover {
    background-color: var(--color-primary-dark);
  }
}

.terminal-overlay {
  @include absolute-full;
  background-color: rgba(0, 0, 0, 0.2);
  z-index: $z-index-modal-backdrop;
}
</style>