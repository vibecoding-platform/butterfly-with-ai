<template>
  <div class="region-selection">
    <div class="region-grid">
      <button
        v-for="region in regions"
        :key="region.id"
        @click="selectRegion(region)"
        class="region-card"
        :class="{ selected: selectedRegion?.id === region.id }"
      >
        <div class="region-flag">{{ region.flag }}</div>
        <div class="region-name">{{ region.name }}</div>
        <div class="region-code">{{ region.code }}</div>
        <div class="region-status" :class="region.status">{{ region.status }}</div>
        <div class="region-count">{{ region.serverCount }} servers</div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface Region {
  id: string
  name: string
  code: string
  flag: string
  status: 'online' | 'maintenance' | 'offline'
  serverCount: number
}

interface Props {
  regions: Region[]
  selectedRegion?: Region | null
}

interface Emits {
  (e: 'select', region: Region): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const selectRegion = (region: Region) => {
  emit('select', region)
}
</script>

<style scoped lang="scss">
@import '../../../assets/styles/base.scss';

.region-selection {
  width: 100%;
}

.region-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: $spacing-md;
}

.region-card {
  @include button-reset;
  @include card-style;
  @include hover-lift;
  
  padding: $spacing-lg;
  text-align: center;
  transition: all $transition-duration-base $transition-timing-function;
  cursor: pointer;

  &:hover {
    border-color: var(--color-border-secondary);
    background-color: var(--color-bg-tertiary);
  }

  &.selected {
    border-color: var(--color-secondary);
    background-color: var(--color-secondary-light);
    
    .region-name {
      color: var(--color-secondary);
    }
  }

  @include focus-ring;
}

.region-flag {
  font-size: 36px;
  margin-bottom: $spacing-sm;
}

.region-name {
  font-size: $font-size-md;
  font-weight: $font-weight-semibold;
  color: var(--color-text-primary);
  margin-bottom: $spacing-xs;
}

.region-code {
  @include font-mono;
  font-size: $font-size-sm;
  color: var(--color-text-muted);
  background-color: var(--color-bg-tertiary);
  padding: 2px 6px;
  border-radius: $border-radius-sm;
  display: inline-block;
  margin-bottom: $spacing-sm;
}

.region-status {
  font-size: $font-size-xs;
  font-weight: $font-weight-bold;
  text-transform: uppercase;
  padding: $spacing-xs $spacing-sm;
  border-radius: $border-radius-base;
  margin-bottom: $spacing-sm;
  display: inline-block;

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
}

.region-count {
  font-size: $font-size-sm;
  color: var(--color-text-secondary);
  font-weight: $font-weight-medium;
}

// Responsive adjustments
@include mobile-only {
  .region-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: $spacing-sm;
  }

  .region-card {
    padding: $spacing-md;
  }

  .region-flag {
    font-size: 28px;
  }

  .region-name {
    font-size: $font-size-base;
  }
}
</style>