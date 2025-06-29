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
      <!-- Terminal Section (Expandable) -->
      <div class="menu-section">
        <button 
          @click="toggleTerminalExpanded"
          @mouseenter="handleTerminalHover"
          class="menu-item section-header"
          :class="{ 'expanded': terminalExpanded }"
        >
          <span class="menu-icon">💻</span>
          <span class="menu-text">Terminal</span>
          <span class="expand-arrow" :class="{ 'rotated': terminalExpanded }">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
              <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </button>
        
        <!-- Terminal Sub-options -->
        <div 
          class="submenu" 
          :class="{ 'expanded': terminalExpanded }"
          @transitionend="onTransitionEnd"
        >
          <div class="submenu-content">
            <button 
              @click="addTab('terminal', 'pure')"
              class="menu-item submenu-item pure-terminal-item"
            >
              <span class="menu-icon">⚡</span>
              <span class="menu-text">Pure Terminal</span>
            </button>
            <button 
              @click="addTab('terminal', 'inventory')"
              class="menu-item submenu-item inventory-terminal-item"
            >
              <span class="menu-icon">📊</span>
              <span class="menu-text">Inventory Terminal</span>
            </button>
          </div>
        </div>
      </div>

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
  (e: 'add-tab', type: 'terminal' | 'ai-agent', subType?: 'pure' | 'inventory'): void
}

const emit = defineEmits<Emits>()

const showMenu = ref(false)
const terminalExpanded = ref(false)

const toggleMenu = () => {
  showMenu.value = !showMenu.value
  // Reset terminal expansion when menu closes
  if (!showMenu.value) {
    terminalExpanded.value = false
  }
}

const toggleTerminalExpanded = () => {
  terminalExpanded.value = !terminalExpanded.value
}

const handleTerminalHover = () => {
  // Auto-expand on hover for better UX
  if (!terminalExpanded.value) {
    terminalExpanded.value = true
  }
}

const addTab = (type: 'terminal' | 'ai-agent', subType?: 'pure' | 'inventory') => {
  emit('add-tab', type, subType)
  showMenu.value = false
  terminalExpanded.value = false
}

const onTransitionEnd = () => {
  // Clean up any transition-related state if needed
}

// Close menu when clicking outside
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as Element
  if (!target.closest('.add-tab-container')) {
    showMenu.value = false
    terminalExpanded.value = false
  }
}

// Close menu on escape key
const handleKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && showMenu.value) {
    showMenu.value = false
    terminalExpanded.value = false
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
  justify-content: space-between;

  &.section-header {
    background-color: var(--color-bg-secondary);
    font-weight: $font-weight-semibold;
    border-bottom: 1px solid var(--color-border-secondary);

    &:hover {
      background-color: var(--color-bg-tertiary);
    }

    &.expanded {
      background-color: var(--color-bg-tertiary);
    }

    .expand-arrow {
      transition: transform 0.2s ease;
      display: flex;
      align-items: center;
      color: var(--color-text-muted);

      &.rotated {
        transform: rotate(180deg);
      }
    }
  }

  &.submenu-item {
    padding-left: calc(#{$spacing-md} + #{$spacing-sm});
    background-color: var(--color-bg-primary);
    border-bottom: 1px solid var(--color-border-tertiary);

    &:last-child {
      border-bottom: none;
    }
  }

  &.pure-terminal-item:hover {
    background-color: var(--color-secondary-light);
    color: var(--color-secondary);
  }

  &.inventory-terminal-item:hover {
    background-color: var(--color-accent-blue-light);
    color: var(--color-accent-blue);
  }

  &.ai-agent-item:hover {
    background-color: var(--color-accent-purple-light);
    color: var(--color-accent-purple);
  }

  &.log-monitor-item:hover {
    background-color: var(--color-warning-light);
    color: var(--color-warning);
  }
}

.submenu {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;

  &.expanded {
    max-height: 200px; // Enough for multiple items
  }
}

.submenu-content {
  background-color: var(--color-bg-primary);
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
.menu-item:not(.section-header) {
  transition: all 0.2s ease;

  &:hover {
    transform: translateX(2px);
    box-shadow: inset 3px 0 0 var(--color-primary);
  }
}

.section-header {
  .menu-text {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
}

/* Responsive */
@include mobile-only {
  .add-tab-menu {
    right: -10px;
    min-width: 160px;
  }

  .menu-item.submenu-item {
    padding-left: $spacing-md;
  }
}

/* Dark mode adjustments */
@media (prefers-color-scheme: dark) {
  .menu-section {
    border-bottom-color: var(--color-border-primary);
  }

  .menu-item.section-header {
    background-color: var(--color-bg-tertiary);

    &:hover, &.expanded {
      background-color: var(--color-bg-quaternary);
    }
  }

  .submenu-content {
    background-color: var(--color-bg-secondary);
  }
}
</style>