<template>
  <div class="inventory-search-panel">
    <div class="search-header">
      <h3>🔍 Inventory Search</h3>
      <div class="search-info">
        <span class="item-count">{{ filteredItems.length }} items found</span>
      </div>
    </div>

    <!-- Search Input -->
    <div class="search-input-container">
      <input
        v-model="searchQuery"
        @input="onSearchInput"
        placeholder="Search services, files, commands, servers..."
        class="search-input"
        ref="searchInput"
      />
      <button 
        v-if="searchQuery"
        @click="clearSearch"
        class="clear-search-btn"
        title="Clear search"
      >
        ✕
      </button>
    </div>

    <!-- Filter Tabs -->
    <div class="filter-tabs">
      <button
        v-for="filter in filterOptions"
        :key="filter.key"
        @click="activeFilter = filter.key"
        class="filter-tab"
        :class="{ active: activeFilter === filter.key }"
      >
        <span class="filter-icon">{{ filter.icon }}</span>
        <span class="filter-label">{{ filter.label }}</span>
        <span class="filter-count">({{ getFilteredCount(filter.key) }})</span>
      </button>
    </div>

    <!-- Search Results -->
    <div class="search-results">
      <div v-if="isSearching || isLoading" class="search-loading">
        <div class="loading-spinner"></div>
        <span>{{ isSearching ? 'Searching inventory...' : 'Loading inventory...' }}</span>
      </div>
      
      <div v-else-if="apiError" class="api-error">
        <span class="error-icon">⚠️</span>
        <p>Error: {{ apiError }}</p>
        <button @click="loadInitialInventory" class="retry-btn">Retry</button>
      </div>

      <div v-else-if="filteredItems.length === 0 && (searchQuery || inventoryItems.length === 0)" class="no-results">
        <span class="no-results-icon">🤷‍♂️</span>
        <p>No items found for "{{ searchQuery }}"</p>
        <p class="suggestion">Try searching for:</p>
        <ul class="suggestions">
          <li>Service names (nginx, postgres, redis)</li>
          <li>File paths (/var/log, /etc/nginx)</li>
          <li>Commands (ls, grep, docker)</li>
          <li>Server names (web-server-01, db-cluster)</li>
        </ul>
      </div>

      <div v-else class="results-list">
        <div
          v-for="item in filteredItems"
          :key="item.id"
          class="result-item"
          :class="item.type"
          @click="openItemInTab(item)"
          @contextmenu.prevent="showItemContextMenu(item, $event)"
        >
          <div class="item-icon">{{ item.icon }}</div>
          <div class="item-content">
            <div class="item-title">{{ item.title }}</div>
            <div class="item-description">{{ item.description }}</div>
            <div class="item-meta">
              <span class="item-type">{{ item.type }}</span>
              <span class="item-location">{{ item.location }}</span>
              <span v-if="item.status" class="item-status" :class="item.status">
                {{ item.status }}
              </span>
            </div>
          </div>
          <div class="item-actions">
            <button
              @click.stop="openItemInTerminal(item)"
              class="action-btn terminal-btn"
              title="Open in Terminal"
            >
              💻
            </button>
            <button
              @click.stop="openItemInAI(item)"
              class="action-btn ai-btn"
              title="Analyze with AI"
            >
              🤖
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Context Menu -->
    <div
      v-if="contextMenu.show"
      class="context-menu"
      :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
      @click.stop
    >
      <button @click="contextMenu.item && openItemInTerminal(contextMenu.item)" class="context-menu-item">
        <span class="context-icon">💻</span>
        Open in Terminal
      </button>
      <button @click="contextMenu.item && openItemInAI(contextMenu.item)" class="context-menu-item">
        <span class="context-icon">🤖</span>
        Analyze with AI
      </button>
      <button @click="contextMenu.item && copyItemPath(contextMenu.item)" class="context-menu-item">
        <span class="context-icon">📋</span>
        Copy Path
      </button>
      <button @click="contextMenu.item && showItemDetails(contextMenu.item)" class="context-menu-item">
        <span class="context-icon">ℹ️</span>
        Show Details
      </button>
    </div>

    <!-- Background overlay for context menu -->
    <div 
      v-if="contextMenu.show" 
      @click="contextMenu.show = false"
      class="context-overlay"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useTerminalTabStore } from '../stores/terminalTabStore'
import { inventoryApiService } from '../services/InventoryApiService'
import type { InventoryItem, LegacyInventoryItem } from '../types/inventory'

// Using imported types from inventory.ts

const tabStore = useTerminalTabStore()
const searchQuery = ref('')
const activeFilter = ref('all')
const isSearching = ref(false)
const searchInput = ref<HTMLInputElement | null>(null)
const apiError = ref<string | null>(null)
const isLoading = ref(false)

// Context menu state
const contextMenu = ref({
  show: false,
  x: 0,
  y: 0,
  item: null as LegacyInventoryItem | null
})

// Real inventory data from API
const inventoryItems = ref<LegacyInventoryItem[]>([])
const rawInventoryItems = ref<InventoryItem[]>([])

const filterOptions = [
  { key: 'all', label: 'All', icon: '📄' },
  { key: 'service', label: 'Services', icon: '⚙️' },
  { key: 'file', label: 'Files', icon: '📁' },
  { key: 'command', label: 'Commands', icon: '💻' },
  { key: 'server', label: 'Servers', icon: '🖥️' },
  { key: 'container', label: 'Containers', icon: '📦' },
  { key: 'database', label: 'Databases', icon: '🗄️' }
]

const filteredItems = computed(() => {
  let items = inventoryItems.value

  // Apply type filter
  if (activeFilter.value !== 'all') {
    items = items.filter(item => item.type === activeFilter.value)
  }

  // Apply search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    items = items.filter(item =>
      item.title.toLowerCase().includes(query) ||
      item.description.toLowerCase().includes(query) ||
      item.location.toLowerCase().includes(query) ||
      item.command?.toLowerCase().includes(query)
    )
  }

  return items
})

const getFilteredCount = (filterKey: string) => {
  if (filterKey === 'all') {
    return inventoryItems.value.length
  }
  return inventoryItems.value.filter(item => item.type === filterKey).length
}

const onSearchInput = async () => {
  if (!searchQuery.value.trim()) {
    return
  }
  
  isSearching.value = true
  apiError.value = null
  
  try {
    const searchResults = await inventoryApiService.searchInventory({
      search_term: searchQuery.value,
      provider_filter: activeFilter.value !== 'all' ? activeFilter.value : undefined
    })
    
    // Convert API results to legacy format
    const legacyResults = inventoryApiService.convertToLegacyFormat(searchResults)
    
    // Update inventory items with search results
    inventoryItems.value = legacyResults
    rawInventoryItems.value = searchResults
    
  } catch (error) {
    console.error('Search failed:', error)
    apiError.value = error instanceof Error ? error.message : 'Search failed'
  } finally {
    isSearching.value = false
  }
}

const clearSearch = () => {
  searchQuery.value = ''
  searchInput.value?.focus()
}

const openItemInTab = (item: LegacyInventoryItem) => {
  // Default action: open in terminal
  openItemInTerminal(item)
}

const openItemInTerminal = (item: LegacyInventoryItem) => {
  const tab = tabStore.createTab('terminal', `${item.title}`)
  
  // In a real implementation, you would:
  // 1. Send the command to the terminal
  // 2. Set up the terminal session
  // 3. Execute the command
  
  console.log(`Opening "${item.title}" in terminal with command: ${item.command}`)
  
  // For now, just show a placeholder
  setTimeout(() => {
    tabStore.updateTabStatus(tab.id, 'active')
  }, 1000)
}

const openItemInAI = (item: LegacyInventoryItem) => {
  const tab = tabStore.createTab('ai-agent', `AI: ${item.title}`)
  
  // In a real implementation, you would:
  // 1. Open AI chat tab
  // 2. Send analysis prompt
  // 3. Include relevant context
  
  console.log(`Analyzing "${item.title}" with AI prompt: ${item.aiAnalysisPrompt}`)
  
  setTimeout(() => {
    tabStore.updateTabStatus(tab.id, 'active')
  }, 1000)
}

const showItemContextMenu = (item: LegacyInventoryItem, event: MouseEvent) => {
  contextMenu.value = {
    show: true,
    x: event.clientX,
    y: event.clientY,
    item
  }
}

const copyItemPath = (item: LegacyInventoryItem) => {
  navigator.clipboard.writeText(item.location)
  contextMenu.value.show = false
  console.log(`Copied: ${item.location}`)
}

const showItemDetails = (item: LegacyInventoryItem) => {
  contextMenu.value.show = false
  console.log(`Showing details for: ${item.title}`)
  // In real implementation, open details modal/panel
}

// Close context menu on outside click
const handleClickOutside = (event: MouseEvent) => {
  if (contextMenu.value.show) {
    contextMenu.value.show = false
  }
}

const loadInitialInventory = async () => {
  isLoading.value = true
  apiError.value = null
  
  try {
    // Load initial inventory data
    const resources = await inventoryApiService.getResources({ limit: 1000 })
    rawInventoryItems.value = resources
    
    // Convert to legacy format for UI compatibility
    inventoryItems.value = inventoryApiService.convertToLegacyFormat(resources)
    
    console.log(`Loaded ${resources.length} inventory items from API`)
  } catch (error) {
    console.error('Failed to load inventory:', error)
    apiError.value = error instanceof Error ? error.message : 'Failed to load inventory'
    
    // Fallback to empty array
    inventoryItems.value = []
    rawInventoryItems.value = []
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  searchInput.value?.focus()
  
  // Load initial inventory data
  await loadInitialInventory()
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.inventory-search-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #2d2d2d;
  color: #ffffff;
  position: relative;
}

.search-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #444;
  background-color: #1e1e1e;
}

.search-header h3 {
  margin: 0;
  color: #4caf50;
  font-size: 16px;
}

.search-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.item-count {
  font-size: 12px;
  color: #888;
}

.search-input-container {
  position: relative;
  padding: 15px;
  border-bottom: 1px solid #444;
}

.search-input {
  width: 100%;
  padding: 12px 40px 12px 12px;
  border: 1px solid #444;
  border-radius: 6px;
  background-color: #1e1e1e;
  color: #ffffff;
  font-size: 14px;
  font-family: inherit;
  box-sizing: border-box;
}

.search-input:focus {
  outline: none;
  border-color: #4caf50;
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

.clear-search-btn {
  position: absolute;
  right: 25px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  padding: 4px;
  border-radius: 2px;
  font-size: 12px;
}

.clear-search-btn:hover {
  color: #ccc;
  background-color: rgba(255, 255, 255, 0.1);
}

.filter-tabs {
  display: flex;
  overflow-x: auto;
  border-bottom: 1px solid #444;
  background-color: #1e1e1e;
}

.filter-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  background: none;
  border: none;
  color: #ccc;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
}

.filter-tab:hover {
  background-color: #3d3d3d;
  color: #4caf50;
}

.filter-tab.active {
  color: #4caf50;
  border-bottom-color: #4caf50;
  background-color: #2d2d2d;
}

.filter-icon {
  font-size: 14px;
}

.filter-count {
  color: #666;
  font-size: 11px;
}

.search-results {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.search-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px;
  color: #888;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #444;
  border-top: 2px solid #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.api-error {
  text-align: center;
  padding: 40px 20px;
  color: #f44336;
}

.error-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.retry-btn {
  margin-top: 16px;
  padding: 8px 16px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s ease;
}

.retry-btn:hover {
  background-color: #45a049;
}

.no-results {
  text-align: center;
  padding: 40px 20px;
  color: #888;
}

.no-results-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.suggestion {
  margin-top: 20px;
  margin-bottom: 10px;
  color: #aaa;
  font-size: 14px;
}

.suggestions {
  text-align: left;
  display: inline-block;
  color: #666;
  font-size: 13px;
}

.results-list {
  padding: 10px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  background-color: #3d3d3d;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}

.result-item:hover {
  background-color: #4d4d4d;
  transform: translateX(2px);
}

.result-item.service {
  border-left-color: #2196f3;
}

.result-item.file {
  border-left-color: #ff9800;
}

.result-item.command {
  border-left-color: #4caf50;
}

.result-item.server {
  border-left-color: #9c27b0;
}

.result-item.container {
  border-left-color: #00bcd4;
}

.result-item.database {
  border-left-color: #f44336;
}

.item-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-weight: bold;
  font-size: 14px;
  color: #e0e0e0;
  margin-bottom: 4px;
}

.item-description {
  font-size: 12px;
  color: #aaa;
  margin-bottom: 6px;
}

.item-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 11px;
}

.item-type {
  background-color: #555;
  padding: 2px 6px;
  border-radius: 3px;
  text-transform: uppercase;
  font-weight: bold;
}

.item-location {
  color: #888;
  font-family: monospace;
}

.item-status {
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: bold;
}

.item-status.running {
  background-color: #4caf50;
  color: white;
}

.item-status.stopped {
  background-color: #f44336;
  color: white;
}

.item-status.error {
  background-color: #ff5722;
  color: white;
}

.item-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.action-btn {
  width: 28px;
  height: 28px;
  background: none;
  border: 1px solid #666;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.action-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
  border-color: #4caf50;
}

.terminal-btn:hover {
  color: #2196f3;
  border-color: #2196f3;
}

.ai-btn:hover {
  color: #9c27b0;
  border-color: #9c27b0;
}

/* Context Menu */
.context-menu {
  position: fixed;
  background-color: #2d2d2d;
  border: 1px solid #444;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 1001;
  min-width: 180px;
  overflow: hidden;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 16px;
  background: none;
  border: none;
  color: #e0e0e0;
  font-size: 13px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  text-align: left;
}

.context-menu-item:hover {
  background-color: #3d3d3d;
}

.context-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.context-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  background: transparent;
}

/* Scrollbar styling */
.search-results::-webkit-scrollbar {
  width: 8px;
}

.search-results::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.search-results::-webkit-scrollbar-thumb {
  background: #666;
  border-radius: 4px;
}

.search-results::-webkit-scrollbar-thumb:hover {
  background: #888;
}
</style>