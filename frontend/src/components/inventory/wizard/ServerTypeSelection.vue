<template>
  <div class="server-type-selection">
    <div class="type-grid">
      <button
        v-for="type in serverTypes"
        :key="type.id"
        @click="selectServerType(type)"
        class="type-card"
        :class="{ selected: selectedServerType?.id === type.id }"
      >
        <div class="type-icon">{{ type.icon }}</div>
        <div class="type-title">{{ type.title }}</div>
        <div class="type-description">{{ type.description }}</div>
        <div class="type-specs">{{ type.specs }}</div>
        <div class="type-count">{{ type.count }} instances</div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface ServerType {
  id: string
  title: string
  description: string
  icon: string
  specs: string
  count: number
}

interface Props {
  serverTypes: ServerType[]
  selectedServerType?: ServerType | null
}

interface Emits {
  (e: 'select', serverType: ServerType): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const selectServerType = (serverType: ServerType) => {
  emit('select', serverType)
}
</script>

<style scoped lang="scss">
@import '../../../assets/styles/base.scss';

.server-type-selection {
  width: 100%;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: $spacing-md;
}

.type-card {
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
    border-color: var(--color-accent-orange);
    background-color: rgba(255, 152, 0, 0.1);
    
    .type-title {
      color: var(--color-accent-orange);
    }
  }

  @include focus-ring;
}

.type-icon {
  font-size: 42px;
  margin-bottom: $spacing-md;
}

.type-title {
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  color: var(--color-text-primary);
  margin-bottom: $spacing-sm;
}

.type-description {
  font-size: $font-size-sm;
  color: var(--color-text-secondary);
  margin-bottom: $spacing-md;
  line-height: $line-height-relaxed;
}

.type-specs {
  @include font-mono;
  font-size: $font-size-xs;
  color: var(--color-text-muted);
  background-color: var(--color-bg-tertiary);
  padding: $spacing-xs $spacing-sm;
  border-radius: $border-radius-sm;
  margin-bottom: $spacing-md;
  display: inline-block;
}

.type-count {
  font-size: $font-size-sm;
  color: var(--color-text-muted);
  font-weight: $font-weight-medium;
}

// Responsive adjustments
@include mobile-only {
  .type-grid {
    grid-template-columns: 1fr;
    gap: $spacing-sm;
  }

  .type-card {
    padding: $spacing-md;
  }

  .type-icon {
    font-size: 32px;
    margin-bottom: $spacing-sm;
  }

  .type-title {
    font-size: $font-size-md;
  }
}
</style>