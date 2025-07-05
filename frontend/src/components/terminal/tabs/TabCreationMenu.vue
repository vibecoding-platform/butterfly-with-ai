<template>
  <div class="add-tab-container">
    <button
      @click="toggleMenu"
      class="add-tab-btn"
      :class="{ 'menu-open': showMenu }"
      title="Add New Tab"
    >
      +
    </button>

    <!-- Add Tab Menu -->
    <div v-if="showMenu" class="add-tab-menu" @click.stop>
      <!-- Terminal (Direct Action) -->
      <button 
        @click="addTab('terminal')"
        class="menu-item terminal-item"
      >
        <span class="menu-icon">💻</span>
        <span class="menu-text">Terminal</span>
      </button>

      <!-- AI Agent (Direct Action) -->
      <button 
        @click="addTab('ai-agent')"
        class="menu-item ai-agent-item"
      >
        <span class="menu-icon">🤖</span>
        <span class="menu-text">AI Agent</span>
      </button>

    </div>

    <!-- Background overlay when menu is open -->
    <div 
      v-if="showMenu" 
      @click="showMenu = false"
      class="menu-overlay"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface Emits {
  (e: 'add-tab', type: 'terminal' | 'ai-agent'): void
}

const emit = defineEmits<Emits>()

const showMenu = ref(false)

const toggleMenu = () => {
  console.log('🔥 Toggle menu clicked, current state:', showMenu.value)
  showMenu.value = !showMenu.value
  console.log('🔥 Menu state after toggle:', showMenu.value)
}

const addTab = (type: 'terminal' | 'ai-agent') => {
  console.log('🔥 Add tab clicked, type:', type)
  emit('add-tab', type)
  showMenu.value = false
}

// Close menu when clicking outside
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as Element
  if (!target.closest('.add-tab-container')) {
    showMenu.value = false
  }
}

// Close menu on escape key
const handleKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && showMenu.value) {
    showMenu.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped lang="scss">
@import '../../../assets/styles/base.scss';

.add-tab-container {
  position: relative;
  flex-shrink: 0;
}

.add-tab-btn {
  @include button-reset;
  @include flex-center;
  
  width: $tab-height;
  height: $tab-height;
  background-color: var(--color-bg-secondary);
  border-right: $border-width solid var(--color-border-primary);
  color: var(--color-text-muted);
  font-size: $font-size-lg;
  font-weight: $font-weight-bold;
  transition: $transition-colors;

  &:hover {
    background-color: var(--color-bg-tertiary);
    color: var(--color-primary);
  }

  &.menu-open {
    background-color: var(--color-primary);
    color: var(--color-text-primary);
  }

  @include focus-ring;
}

.add-tab-menu {
  @include context-menu;
  
  position: absolute;
  top: 100%;
  right: 0;
  min-width: 180px;
  overflow: hidden;
  z-index: 1000; // Ensure menu appears above other elements
  background-color: var(--color-bg-primary); // Ensure background is set
  border: 1px solid var(--color-border-primary); // Add border for visibility
}

.menu-section {
  border-bottom: 1px solid var(--color-border-secondary);

  &:last-child {
    border-bottom: none;
  }
}

.menu-item {
  @include context-menu-item;
  
  gap: $spacing-sm;
  position: relative;

  &.terminal-item:hover {
    background-color: var(--color-secondary-light);
    color: var(--color-secondary);
  }

  &.ai-agent-item:hover {
    background-color: var(--color-accent-purple-light);
    color: var(--color-accent-purple);
  }

}

.menu-icon {
  font-size: $font-size-md;
  flex-shrink: 0;
}

.menu-text {
  font-weight: $font-weight-medium;
  flex: 1;
}

.menu-overlay {
  @include fixed-full;
  z-index: $z-index-modal-backdrop;
  background: transparent;
}

// Animation for menu item appearance
.menu-item {
  opacity: 0;
  transform: translateY(-4px);
  animation: menuItemAppear 0.2s ease forwards;

  @for $i from 1 through 5 {
    &:nth-child(#{$i}) {
      animation-delay: #{($i - 1) * 0.03}s;
    }
  }
}

@keyframes menuItemAppear {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// Enhanced hover effects
.menu-item {
  transition: all 0.2s ease;

  &:hover {
    transform: translateX(2px);
    box-shadow: inset 3px 0 0 var(--color-primary);
  }
}

/* Responsive */
@include mobile-only {
  .add-tab-menu {
    right: -10px;
    min-width: 160px;
  }
}

</style>