<template>
  <div class="layer-selection">
    <div class="layer-grid">
      <button
        v-for="layer in layers"
        :key="layer.id"
        @click="selectLayer(layer)"
        class="layer-card"
        :class="{ selected: selectedLayer?.id === layer.id }"
      >
        <div class="layer-icon">{{ layer.icon }}</div>
        <div class="layer-title">{{ layer.title }}</div>
        <div class="layer-description">{{ layer.description }}</div>
        <div class="layer-count">{{ layer.count }} items</div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface Layer {
  id: string
  title: string
  description: string
  icon: string
  count: number
}

interface Props {
  layers: Layer[]
  selectedLayer?: Layer | null
}

interface Emits {
  (e: 'select', layer: Layer): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const selectLayer = (layer: Layer) => {
  emit('select', layer)
}
</script>

<style scoped lang="scss">
@import '../../../assets/styles/base.scss';

.layer-selection {
  width: 100%;
}

.layer-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: $spacing-md;
}

.layer-card {
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
    border-color: var(--color-primary);
    background-color: var(--color-primary-light);
    
    .layer-title {
      color: var(--color-primary);
    }
  }

  @include focus-ring;
}

.layer-icon {
  font-size: 48px;
  margin-bottom: $spacing-md;
}

.layer-title {
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  color: var(--color-text-primary);
  margin-bottom: $spacing-sm;
}

.layer-description {
  font-size: $font-size-sm;
  color: var(--color-text-secondary);
  margin-bottom: $spacing-md;
  line-height: $line-height-relaxed;
}

.layer-count {
  font-size: $font-size-sm;
  color: var(--color-text-muted);
  font-weight: $font-weight-medium;
}

// Responsive adjustments
@include mobile-only {
  .layer-grid {
    grid-template-columns: 1fr;
    gap: $spacing-sm;
  }

  .layer-card {
    padding: $spacing-md;
  }

  .layer-icon {
    font-size: 36px;
    margin-bottom: $spacing-sm;
  }

  .layer-title {
    font-size: $font-size-md;
  }
}
</style>