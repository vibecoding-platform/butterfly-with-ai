<template>
  <div class="wizard-step">
    <div class="step-header">
      <h4>{{ title }}</h4>
      <div class="step-progress">
        <div class="step-indicator">
          Step {{ currentStep + 1 }} of {{ totalSteps }}
        </div>
        <div v-if="showQuickAccess" class="quick-access">
          <button @click="$emit('quick-access')" class="quick-access-btn">
            Quick Access
          </button>
        </div>
      </div>
    </div>

    <div class="step-content">
      <slot />
    </div>

    <div v-if="showNavigation" class="step-navigation">
      <button 
        v-if="currentStep > 0"
        @click="$emit('previous')"
        class="nav-btn secondary"
      >
        ← Previous
      </button>
      
      <div class="nav-spacer"></div>
      
      <button 
        v-if="currentStep < totalSteps - 1 && hasSelection"
        @click="$emit('next')"
        class="nav-btn primary"
      >
        Next →
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title: string
  currentStep: number
  totalSteps: number
  hasSelection?: boolean
  showQuickAccess?: boolean
  showNavigation?: boolean
}

interface Emits {
  (e: 'previous'): void
  (e: 'next'): void
  (e: 'quick-access'): void
}

withDefaults(defineProps<Props>(), {
  hasSelection: false,
  showQuickAccess: true,
  showNavigation: true
})

defineEmits<Emits>()
</script>

<style scoped lang="scss">
@import '../../../assets/styles/base.scss';

.wizard-step {
  @include flex-column;
  flex: 1;
  overflow: hidden;
}

.step-header {
  padding: $spacing-lg $spacing-md $spacing-md;
  border-bottom: $border-width solid var(--color-border-primary);

  h4 {
    margin-bottom: $spacing-sm;
    color: var(--color-text-primary);
    font-size: $font-size-lg;
  }
}

.step-progress {
  @include flex-between;
  align-items: center;
}

.step-indicator {
  font-size: $font-size-sm;
  color: var(--color-text-muted);
  font-weight: $font-weight-medium;
}

.quick-access {
  flex-shrink: 0;
}

.quick-access-btn {
  @include button-ghost;
  height: auto;
  padding: $spacing-xs $spacing-sm;
  font-size: $font-size-sm;
  color: var(--color-primary);

  &:hover {
    color: var(--color-primary-dark);
    background-color: var(--color-primary-light);
  }
}

.step-content {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-md;
}

.step-navigation {
  @include flex-between;
  padding: $spacing-md;
  border-top: $border-width solid var(--color-border-primary);
  background-color: var(--color-bg-secondary);
}

.nav-spacer {
  flex: 1;
}

.nav-btn {
  @include button-base;
  gap: $spacing-xs;

  &.primary {
    @include button-primary;
  }

  &.secondary {
    @include button-secondary;
  }
}

// Responsive adjustments
@include mobile-only {
  .step-header {
    padding: $spacing-md $spacing-sm $spacing-sm;
  }

  .step-content {
    padding: $spacing-sm;
  }

  .step-navigation {
    padding: $spacing-sm;
  }

  .step-progress {
    flex-direction: column;
    gap: $spacing-sm;
    align-items: flex-start;
  }

  .quick-access {
    align-self: flex-end;
  }
}
</style>