<template>
  <div class="search-container">
    <div class="search-input-wrapper">
      <div class="search-icon">🔍</div>
      <input
        ref="searchInput"
        v-model="searchQuery"
        @input="onSearchInput"
        @keydown="handleKeyDown"
        :placeholder="placeholder"
        class="search-input"
        autocomplete="off"
      />
      <div v-if="searchQuery" class="search-clear" @click="clearSearch">✕</div>
    </div>
    
    <!-- Search Results Counter -->
    <div v-if="searchQuery" class="search-info">
      <span class="search-results-count">
        {{ resultsCount }} result{{ resultsCount !== 1 ? 's' : '' }} found
      </span>
      <button 
        v-if="resultsCount > 0" 
        @click="$emit('jump-to-results')" 
        class="jump-to-results"
      >
        Jump to Results →
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
  placeholder?: string
  resultsCount?: number
}

interface Emits {
  (e: 'search', query: string): void
  (e: 'clear'): void
  (e: 'key-down', event: KeyboardEvent): void
  (e: 'jump-to-results'): void
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: 'Type to search...',
  resultsCount: 0
})

const emit = defineEmits<Emits>()

const searchInput = ref<HTMLInputElement>()
const searchQuery = ref('')

const onSearchInput = () => {
  emit('search', searchQuery.value)
}

const clearSearch = () => {
  searchQuery.value = ''
  emit('clear')
  searchInput.value?.focus()
}

const handleKeyDown = (event: KeyboardEvent) => {
  emit('key-down', event)
}

// Focus input when component mounts
const focus = () => {
  searchInput.value?.focus()
}

// Watch for external changes to search query
watch(() => props.resultsCount, () => {
  // Could add auto-scroll or other logic here
})

defineExpose({
  focus,
  clearSearch
})
</script>

<style scoped lang="scss">
@import '../../../assets/styles/base.scss';

.search-container {
  padding: $spacing-md;
  border-bottom: $border-width solid var(--color-border-primary);
}

.search-input-wrapper {
  position: relative;
  @include flex-center;
}

.search-icon {
  position: absolute;
  left: $spacing-md;
  font-size: $font-size-md;
  color: var(--color-text-muted);
  z-index: 1;
}

.search-input {
  @include search-input;
  width: 100%;
  height: $search-input-height;
  padding-right: $spacing-3xl; // Space for clear button
}

.search-clear {
  position: absolute;
  right: $spacing-md;
  @include flex-center;
  width: 20px;
  height: 20px;
  background-color: var(--color-text-muted);
  color: var(--color-bg-primary);
  border-radius: 50%;
  font-size: $font-size-xs;
  cursor: pointer;
  transition: $transition-colors;
  z-index: 1;

  &:hover {
    background-color: var(--color-text-secondary);
  }
}

.search-info {
  @include flex-between;
  margin-top: $spacing-sm;
  font-size: $font-size-sm;
}

.search-results-count {
  color: var(--color-text-muted);
}

.jump-to-results {
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
</style>