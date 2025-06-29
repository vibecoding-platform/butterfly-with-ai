<template>
  <div class="server-selection">
    <div class="server-list">
      <div
        v-for="server in servers"
        :key="server.id"
        @click="selectServer(server)"
        class="server-item"
        :class="server.status"
      >
        <div class="server-icon">🖥️</div>
        <div class="server-content">
          <div class="server-name">{{ server.name }}</div>
          <div class="server-details">
            <span class="server-ip">{{ server.ip }}</span>
            <span class="server-os">{{ server.os }}</span>
            <span class="server-uptime">Uptime: {{ server.uptime }}</span>
          </div>
          <div class="server-metrics">
            <div class="metric">
              <span class="metric-label">CPU</span>
              <div class="metric-bar">
                <div class="metric-fill" :style="{ width: server.cpu + '%' }"></div>
              </div>
              <span class="metric-value">{{ server.cpu }}%</span>
            </div>
            <div class="metric">
              <span class="metric-label">RAM</span>
              <div class="metric-bar">
                <div class="metric-fill" :style="{ width: server.memory + '%' }"></div>
              </div>
              <span class="metric-value">{{ server.memory }}%</span>
            </div>
            <div class="metric">
              <span class="metric-label">Disk</span>
              <div class="metric-bar">
                <div class="metric-fill" :style="{ width: server.disk + '%' }"></div>
              </div>
              <span class="metric-value">{{ server.disk }}%</span>
            </div>
          </div>
        </div>
        <div class="server-status" :class="server.status">{{ server.status }}</div>
        <div class="server-actions">
          <button @click.stop="handleTerminalAction(server)" class="action-btn terminal">💻</button>
          <button @click.stop="handleAIAction(server)" class="action-btn ai">🤖</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface Server {
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

interface Props {
  servers: Server[]
}

interface Emits {
  (e: 'select', server: Server): void
  (e: 'terminal-action', server: Server): void
  (e: 'ai-action', server: Server): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const selectServer = (server: Server) => {
  emit('select', server)
}

const handleTerminalAction = (server: Server) => {
  emit('terminal-action', server)
}

const handleAIAction = (server: Server) => {
  emit('ai-action', server)
}
</script>

<style scoped lang="scss">
@import '../../../assets/styles/base.scss';

.server-selection {
  width: 100%;
}

.server-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.server-item {
  @include flex-start;
  @include card-style;
  
  padding: $spacing-md;
  gap: $spacing-md;
  cursor: pointer;
  transition: all $transition-duration-base $transition-timing-function;

  &:hover {
    border-color: var(--color-border-secondary);
    background-color: var(--color-bg-tertiary);
  }

  &.online {
    border-left: 4px solid var(--color-status-success);
  }

  &.maintenance {
    border-left: 4px solid var(--color-status-warning);
  }

  &.offline {
    border-left: 4px solid var(--color-status-error);
  }

  &.warning {
    border-left: 4px solid var(--color-accent-orange);
  }
}

.server-icon {
  font-size: $font-size-xl;
  flex-shrink: 0;
}

.server-content {
  @include flex-column;
  flex: 1;
  gap: $spacing-sm;
  min-width: 0;
}

.server-name {
  font-size: $font-size-md;
  font-weight: $font-weight-semibold;
  color: var(--color-text-primary);
}

.server-details {
  @include flex-start;
  gap: $spacing-md;
  font-size: $font-size-sm;
  color: var(--color-text-secondary);
  flex-wrap: wrap;
}

.server-ip {
  @include font-mono;
  background-color: var(--color-bg-secondary);
  padding: 2px 6px;
  border-radius: $border-radius-sm;
}

.server-os,
.server-uptime {
  font-size: $font-size-xs;
  color: var(--color-text-muted);
}

.server-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-md;
}

.metric {
  @include flex-start;
  gap: $spacing-xs;
  font-size: $font-size-xs;
  align-items: center;
}

.metric-label {
  min-width: 30px;
  color: var(--color-text-muted);
  font-weight: $font-weight-medium;
}

.metric-bar {
  flex: 1;
  height: 6px;
  background-color: var(--color-bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.metric-fill {
  height: 100%;
  background-color: var(--color-primary);
  transition: width $transition-duration-base $transition-timing-function;
}

.metric-value {
  min-width: 35px;
  text-align: right;
  color: var(--color-text-secondary);
  @include font-mono;
}

.server-status {
  flex-shrink: 0;
  padding: $spacing-xs $spacing-sm;
  border-radius: $border-radius-base;
  font-size: $font-size-xs;
  font-weight: $font-weight-bold;
  text-transform: uppercase;

  &.online {
    background-color: var(--color-status-success);
    color: var(--color-text-primary);
  }

  &.maintenance {
    background-color: var(--color-status-warning);
    color: var(--color-bg-primary);
  }

  &.offline {
    background-color: var(--color-status-error);
    color: var(--color-text-primary);
  }

  &.warning {
    background-color: var(--color-accent-orange);
    color: var(--color-text-primary);
  }
}

.server-actions {
  @include flex-center;
  gap: $spacing-xs;
  flex-shrink: 0;
}

.action-btn {
  @include button-reset;
  @include flex-center;
  
  width: 36px;
  height: 36px;
  border-radius: $border-radius-base;
  background-color: var(--color-bg-tertiary);
  border: $border-width solid var(--color-border-primary);
  font-size: $font-size-md;
  transition: $transition-colors;

  &:hover {
    background-color: var(--color-bg-elevated);
    border-color: var(--color-border-secondary);
  }

  &.terminal:hover {
    background-color: var(--color-secondary-light);
    border-color: var(--color-secondary);
  }

  &.ai:hover {
    background-color: var(--color-accent-purple-light);
    border-color: var(--color-accent-purple);
  }
}

// Responsive adjustments
@include mobile-only {
  .server-item {
    flex-direction: column;
    gap: $spacing-sm;
  }

  .server-details {
    flex-direction: column;
    gap: $spacing-xs;
  }

  .server-metrics {
    grid-template-columns: 1fr;
    gap: $spacing-sm;
  }

  .server-actions {
    align-self: flex-end;
  }
}
</style>