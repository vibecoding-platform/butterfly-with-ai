<template>
  <div class="search-results-container">
    <!-- Search Results Display -->
    <div v-if="results.length > 0" class="search-results">
      <h4>Search Results</h4>
      <div class="search-results-list">
        <div
          v-for="(result, index) in results"
          :key="result.id"
          @click="selectResult(result)"
          class="search-result-item"
          :class="{ highlighted: index === selectedIndex }"
        >
          <div class="result-type-badge" :class="result.type">{{ result.type }}</div>
          <div class="result-content">
            <div class="result-name" v-html="highlightMatch(result.name, searchQuery)"></div>
            <div class="result-details">
              <span v-if="result.ip" class="result-ip" v-html="highlightMatch(result.ip, searchQuery)"></span>
              <span v-if="result.region" class="result-region">{{ result.region }}</span>
              <span v-if="result.layer" class="result-layer">{{ result.layer }}</span>
            </div>
            <div v-if="result.description" class="result-description">{{ result.description }}</div>
          </div>
          <div class="result-actions">
            <button @click.stop="handleTerminalAction(result)" class="result-action-btn terminal">💻</button>
            <button @click.stop="handleAIAction(result)" class="result-action-btn ai">🤖</button>
          </div>
        </div>
      </div>
    </div>

    <!-- No Search Results -->
    <div v-else-if="searchQuery" class="no-search-results">
      <div class="no-results-icon">🤷‍♂️</div>
      <h4>No results found</h4>
      <p>No items match "{{ searchQuery }}"</p>
      <div class="search-suggestions">
        <p>Try searching for:</p>
        <ul>
          <li>Server names (web-server-01, api-server)</li>
          <li>IP addresses (10.0.1.10, 192.168)</li>
          <li>Regions (us-east, europe, tokyo)</li>
          <li>Server types (web, database, api)</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface SearchResult {
  id: string
  name: string
  type: 'server' | 'layer' | 'region' | 'serverType' | 'resource'
  ip?: string
  region?: string
  layer?: string
  description?: string
  data: any // Original data object
}

interface Props {
  results: SearchResult[]
  searchQuery: string
  selectedIndex?: number
}

interface Emits {
  (e: 'select-result', result: SearchResult): void
  (e: 'terminal-action', result: SearchResult): void
  (e: 'ai-action', result: SearchResult): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const selectResult = (result: SearchResult) => {
  emit('select-result', result)
}

const handleTerminalAction = (result: SearchResult) => {
  emit('terminal-action', result)
}

const handleAIAction = (result: SearchResult) => {
  emit('ai-action', result)
}

const highlightMatch = (text: string, query: string): string => {
  if (!query.trim()) return text
  
  const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi')
  return text.replace(regex, '<mark class="search-highlight">$1</mark>')
}

const escapeRegExp = (string: string): string => {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
</script>

<style scoped lang="scss">
@import '../../../assets/styles/base.scss';

.search-results-container {
  flex: 1;
  overflow-y: auto;
}

.search-results {
  padding: $spacing-md;

  h4 {
    margin-bottom: $spacing-md;
    color: var(--color-text-primary);
    font-size: $font-size-md;
  }
}

.search-results-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.search-result-item {
  @include search-result-item;
  
  &:last-child {
    margin-bottom: 0;
  }
}

.result-type-badge {
  padding: $spacing-xs $spacing-sm;
  border-radius: $border-radius-sm;
  font-size: $font-size-xs;
  font-weight: $font-weight-bold;
  text-transform: uppercase;
  flex-shrink: 0;

  &.server {
    background-color: var(--color-secondary-light);
    color: var(--color-secondary);
  }

  &.layer {
    background-color: var(--color-primary-light);
    color: var(--color-primary);
  }

  &.region {
    background-color: var(--color-accent-purple-light);
    color: var(--color-accent-purple);
  }

  &.serverType {
    background-color: rgba(255, 152, 0, 0.1);
    color: var(--color-accent-orange);
  }

  &.resource {
    background-color: rgba(76, 175, 80, 0.1);
    color: #4caf50;
  }
}

.result-content {
  @include flex-column;
  flex: 1;
  gap: $spacing-xs;
  min-width: 0;
}

.result-name {
  font-weight: $font-weight-semibold;
  color: var(--color-text-primary);
  @include text-truncate;
}

.result-details {
  @include flex-start;
  gap: $spacing-md;
  font-size: $font-size-sm;
  color: var(--color-text-secondary);
  flex-wrap: wrap;
}

.result-ip {
  @include font-mono;
  background-color: var(--color-bg-secondary);
  padding: 2px 4px;
  border-radius: $border-radius-sm;
}

.result-region,
.result-layer {
  padding: 2px 6px;
  background-color: var(--color-bg-tertiary);
  border-radius: $border-radius-sm;
  font-size: $font-size-xs;
}

.result-description {
  font-size: $font-size-sm;
  color: var(--color-text-muted);
  @include text-truncate;
}

.result-actions {
  @include flex-center;
  gap: $spacing-xs;
  flex-shrink: 0;
}

.result-action-btn {
  @include button-reset;
  @include flex-center;
  
  width: 32px;
  height: 32px;
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

.no-search-results {
  @include flex-column-center;
  padding: $spacing-4xl $spacing-md;
  text-align: center;
  color: var(--color-text-muted);

  .no-results-icon {
    font-size: 48px;
    margin-bottom: $spacing-lg;
  }

  h4 {
    margin-bottom: $spacing-sm;
    color: var(--color-text-secondary);
  }

  p {
    margin-bottom: $spacing-lg;
    color: var(--color-text-muted);
  }
}

.search-suggestions {
  text-align: left;
  max-width: 400px;

  p {
    margin-bottom: $spacing-sm;
    font-weight: $font-weight-medium;
    color: var(--color-text-secondary);
  }

  ul {
    list-style: none;
    padding: 0;

    li {
      padding: $spacing-xs 0;
      color: var(--color-text-muted);
      font-size: $font-size-sm;

      &::before {
        content: '•';
        color: var(--color-primary);
        margin-right: $spacing-sm;
      }
    }
  }
}

// Global search highlight style
:deep(.search-highlight) {
  @include search-highlight;
}
</style>