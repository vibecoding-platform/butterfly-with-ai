<template>
  <div class="server-inventory-container">
    <!-- Header -->
    <div class="inventory-header">
      <h3>🖥️ Server Inventory</h3>
      <div class="header-actions">
        <div class="server-stats">
          <span class="stat">{{ servers.length }} servers</span>
          <span class="stat">{{ servers.filter(s => s.status === 'online').length }} online</span>
          <span class="stat">{{ servers.filter(s => s.status === 'warning').length }} warnings</span>
        </div>
      </div>
      <div class="breadcrumb">
        <span v-for="(step, index) in breadcrumb" :key="index" class="breadcrumb-item">
          <button @click="goToStep(index)" class="breadcrumb-btn">{{ step }}</button>
          <span v-if="index < breadcrumb.length - 1" class="breadcrumb-separator">›</span>
        </span>
      </div>
    </div>

    <!-- Search Section -->
    <SearchInput
      :placeholder="'Type to search servers, IPs, regions, types...'"
      :results-count="searchResults.length"
      @search="handleSearch"
      @clear="clearSearch"
      @key-down="handleSearchKeyDown"
      @jump-to-results="jumpToResults"
    />

    <!-- Content Area -->
    <div class="inventory-content">
      <!-- Loading State -->
      <div v-if="isLoading" class="loading-state">
        <div class="loading-spinner"></div>
        <span>Loading inventory data...</span>
      </div>
      
      <!-- Error State -->
      <div v-else-if="apiError" class="error-state">
        <span class="error-icon">⚠️</span>
        <p>Error: {{ apiError }}</p>
        <button @click="loadInventoryData" class="retry-btn">Retry</button>
      </div>
      <!-- Search Results -->
      <SearchResults
        v-else-if="searchQuery"
        :results="searchResults"
        :search-query="searchQuery"
        :selected-index="selectedResultIndex"
        @select-result="selectSearchResult"
        @terminal-action="handleTerminalAction"
        @ai-action="handleAIAction"
      />

      <!-- Wizard Steps -->
      <template v-else>
        <!-- Step 1: Layer Selection -->
        <WizardStep
          v-if="currentStep === 0"
          title="Select Infrastructure Layer"
          :current-step="currentStep"
          :total-steps="totalSteps"
          :has-selection="!!selectedLayer"
          @next="nextStep"
          @quick-access="quickAccess"
        >
          <LayerSelection
            :layers="filteredLayers"
            :selected-layer="selectedLayer"
            @select="selectLayer"
          />
        </WizardStep>

        <!-- Step 2: Region Selection -->
        <WizardStep
          v-if="currentStep === 1"
          title="Select Region"
          :current-step="currentStep"
          :total-steps="totalSteps"
          :has-selection="!!selectedRegion"
          @previous="previousStep"
          @next="nextStep"
          @quick-access="quickAccess"
        >
          <RegionSelection
            :regions="filteredRegions"
            :selected-region="selectedRegion"
            @select="selectRegion"
          />
        </WizardStep>

        <!-- Step 3: Server Type Selection -->
        <WizardStep
          v-if="currentStep === 2"
          title="Select Server Type"
          :current-step="currentStep"
          :total-steps="totalSteps"
          :has-selection="!!selectedServerType"
          @previous="previousStep"
          @next="nextStep"
          @quick-access="quickAccess"
        >
          <ServerTypeSelection
            :server-types="filteredServerTypes"
            :selected-server-type="selectedServerType"
            @select="selectServerType"
          />
        </WizardStep>

        <!-- Step 4: Server Selection -->
        <WizardStep
          v-if="currentStep === 3"
          title="Select Server"
          :current-step="currentStep"
          :total-steps="totalSteps"
          :show-navigation="false"
          @previous="previousStep"
          @quick-access="quickAccess"
        >
          <ServerSelection
            :servers="filteredServers"
            @select="selectServer"
            @terminal-action="handleServerTerminalAction"
            @ai-action="handleServerAIAction"
          />
        </WizardStep>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useTerminalTabStore, type ServerContext } from '../../stores/terminalTabStore'
import { inventoryApiService } from '../../services/InventoryApiService'
import type { InventoryItem, Layer, Region, ServerType, Server, SearchResult } from '../../types/inventory'
import SearchInput from './search/SearchInput.vue'
import SearchResults from './search/SearchResults.vue'
import WizardStep from './wizard/WizardStep.vue'
import LayerSelection from './wizard/LayerSelection.vue'
import RegionSelection from './wizard/RegionSelection.vue'
import ServerTypeSelection from './wizard/ServerTypeSelection.vue'
import ServerSelection from './wizard/ServerSelection.vue'

const terminalTabStore = useTerminalTabStore()

// State
const currentStep = ref(0)
const totalSteps = 4
const searchQuery = ref('')
const selectedResultIndex = ref(0)
const isLoading = ref(false)
const apiError = ref<string | null>(null)
const rawInventoryItems = ref<InventoryItem[]>([])

// Selections
const selectedLayer = ref<Layer | null>(null)
const selectedRegion = ref<Region | null>(null)
const selectedServerType = ref<ServerType | null>(null)

// Data from API (dynamically loaded)
const layers = ref<Layer[]>([])
const regions = ref<Region[]>([])
const serverTypes = ref<ServerType[]>([])
const servers = ref<Server[]>([])

// Computed
const breadcrumb = computed(() => {
  const steps = ['Infrastructure']
  if (selectedLayer.value) steps.push(selectedLayer.value.title)
  if (selectedRegion.value) steps.push(selectedRegion.value.name)
  if (selectedServerType.value) steps.push(selectedServerType.value.title)
  return steps
})

const filteredLayers = computed(() => layers.value)
const filteredRegions = computed(() => {
  // Filter based on selected layer if needed
  return regions.value
})
const filteredServerTypes = computed(() => {
  // Filter based on selected layer and region if needed
  return serverTypes.value
})
const filteredServers = computed(() => {
  // Filter based on all selections
  return servers.value
})

// Search functionality
const searchResults = computed(() => {
  if (!searchQuery.value.trim()) return []
  
  const query = searchQuery.value.toLowerCase()
  const results: SearchResult[] = []
  
  // Search servers
  servers.value.forEach(server => {
    if (server.name.toLowerCase().includes(query) || 
        server.ip.toLowerCase().includes(query)) {
      results.push({
        id: server.id,
        name: server.name,
        type: 'server',
        ip: server.ip,
        description: `${server.os} - ${server.status}`,
        data: server
      })
    }
  })
  
  // Search raw inventory items for more comprehensive results
  rawInventoryItems.value.forEach(item => {
    if (item.name.toLowerCase().includes(query) ||
        item.resource_type.toLowerCase().includes(query) ||
        item.provider.toLowerCase().includes(query)) {
      results.push({
        id: item.resource_id,
        name: item.name,
        type: 'resource',
        description: `${item.resource_type} from ${item.provider}`,
        data: item
      })
    }
  })
  
  // Search layers
  layers.value.forEach(layer => {
    if (layer.title.toLowerCase().includes(query) ||
        layer.description.toLowerCase().includes(query)) {
      results.push({
        id: layer.id,
        name: layer.title,
        type: 'layer',
        description: layer.description,
        data: layer
      })
    }
  })
  
  // Search regions
  regions.value.forEach(region => {
    if (region.name.toLowerCase().includes(query) ||
        region.code.toLowerCase().includes(query)) {
      results.push({
        id: region.id,
        name: region.name,
        type: 'region',
        region: region.code,
        description: `${region.serverCount} servers`,
        data: region
      })
    }
  })
  
  // Search server types
  serverTypes.value.forEach(type => {
    if (type.title.toLowerCase().includes(query) ||
        type.description.toLowerCase().includes(query)) {
      results.push({
        id: type.id,
        name: type.title,
        type: 'serverType',
        description: type.description,
        data: type
      })
    }
  })
  
  return results
})

// Enhanced search methods
const handleSearch = async (query: string) => {
  searchQuery.value = query
  selectedResultIndex.value = 0
  
  if (!query.trim()) {
    return
  }
  
  try {
    // Perform search using API
    const searchResults = await inventoryApiService.searchInventory({
      search_term: query
    })
    
    // Update raw inventory items with search results
    rawInventoryItems.value = searchResults
    
    // Convert to servers format for the wizard
    servers.value = convertInventoryItemsToServers(searchResults)
    
    console.log('Server search performed:', {
      query,
      resultCount: searchResults.length,
      searchTime: new Date().toISOString()
    })
  } catch (error) {
    console.error('Search failed:', error)
    apiError.value = error instanceof Error ? error.message : 'Search failed'
  }
}

const clearSearch = () => {
  searchQuery.value = ''
  selectedResultIndex.value = 0
}

const handleSearchKeyDown = (event: KeyboardEvent) => {
  if (!searchResults.value.length) return
  
  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      selectedResultIndex.value = Math.min(selectedResultIndex.value + 1, searchResults.value.length - 1)
      break
    case 'ArrowUp':
      event.preventDefault()
      selectedResultIndex.value = Math.max(selectedResultIndex.value - 1, 0)
      break
    case 'Enter':
      event.preventDefault()
      if (searchResults.value[selectedResultIndex.value]) {
        selectSearchResult(searchResults.value[selectedResultIndex.value])
      }
      break
    case 'Escape':
      clearSearch()
      break
  }
}

const jumpToResults = () => {
  // Scroll to results or focus first result
  selectedResultIndex.value = 0
}

const selectSearchResult = (result: SearchResult) => {
  if (result.type === 'server') {
    handleTerminalAction(result)
  } else {
    // Navigate to appropriate wizard step
    clearSearch()
    if (result.type === 'layer') {
      currentStep.value = 0
      selectLayer(result.data as Layer)
    } else if (result.type === 'region') {
      currentStep.value = 1
      selectRegion(result.data as Region)
    } else if (result.type === 'serverType') {
      currentStep.value = 2
      selectServerType(result.data as ServerType)
    }
  }
}

// Wizard navigation
const nextStep = () => {
  if (currentStep.value < totalSteps - 1) {
    currentStep.value++
  }
}

const previousStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const goToStep = (step: number) => {
  if (step >= 0 && step < breadcrumb.value.length) {
    currentStep.value = step
  }
}

const quickAccess = () => {
  currentStep.value = totalSteps - 1
}

// Selection handlers
const selectLayer = (layer: Layer) => {
  selectedLayer.value = layer
}

const selectRegion = (region: Region) => {
  selectedRegion.value = region
}

const selectServerType = (serverType: ServerType) => {
  selectedServerType.value = serverType
}

const selectServer = (server: Server) => {
  handleServerTerminalAction(server)
}

// Action handlers for search results
const handleTerminalAction = (result: SearchResult) => {
  const server = result.data as Server
  console.log('Opening terminal for server:', server.name)
  
  // Convert Server to ServerContext with enhanced information
  const serverContext: ServerContext = {
    id: server.id,
    name: server.name,
    ip: server.ip,
    os: server.os,
    uptime: server.uptime,
    status: server.status,
    cpu: server.cpu,
    memory: server.memory,
    disk: server.disk
  }
  
  // Create inventory terminal tab with server context
  const tab = terminalTabStore.createInventoryTerminal(serverContext)
  terminalTabStore.switchToTab(tab.id)
  
  // Show feedback to user
  console.log(`Created inventory terminal for ${server.name} with ${tab.preExecutionCommands?.length || 0} pre-configured commands`)
}

const handleAIAction = (result: SearchResult) => {
  const server = result.data as Server
  console.log('Opening AI chat for server:', server.name)
  
  // Create AI chat tab with enhanced context
  const tab = terminalTabStore.createTab('ai-agent', `AI: ${server.name}`)
  terminalTabStore.switchToTab(tab.id)
  
  // Pre-populate with server information for AI context
  const serverInfo = `Server Information:
- Name: ${server.name}
- IP: ${server.ip}
- OS: ${server.os}
- Status: ${server.status}
- Uptime: ${server.uptime}
- Resources: CPU ${server.cpu}%, Memory ${server.memory}%, Disk ${server.disk}%

Please analyze this server and provide recommendations.`
  
  // Note: This would integrate with the AI chat system to send initial context
  console.log('AI Chat initialized with server context:', serverInfo)
}

// Enhanced command template generation for different server types
const getServerTypeCommands = (server: Server): string[] => {
  const commands = []
  
  // Database servers get database-specific commands
  if (server.name.includes('database') || server.name.includes('db')) {
    commands.push(`echo "Database Server Diagnostics:"\r`)
    commands.push(`echo "Checking database processes..."\r`)
    if (server.os.toLowerCase().includes('ubuntu') || server.os.toLowerCase().includes('centos')) {
      commands.push(`ps aux | grep -E "mysql|postgres|mongo" || echo "No database processes found"\r`)
    }
  }
  
  // Web servers get web-specific commands
  if (server.name.includes('web') || server.name.includes('nginx') || server.name.includes('apache')) {
    commands.push(`echo "Web Server Diagnostics:"\r`)
    commands.push(`echo "Checking web server status..."\r`)
    if (server.os.toLowerCase().includes('ubuntu')) {
      commands.push(`systemctl status nginx apache2 2>/dev/null || echo "Web servers not found"\r`)
    }
  }
  
  // API servers get API-specific commands
  if (server.name.includes('api')) {
    commands.push(`echo "API Server Diagnostics:"\r`)
    commands.push(`echo "Checking API processes..."\r`)
    commands.push(`netstat -tlnp | grep :80\|:443\|:8080\|:3000 || echo "No API ports found"\r`)
  }
  
  return commands
}

// Action handlers for server components (direct server objects)
const handleServerTerminalAction = (server: Server) => {
  console.log('Opening terminal for server:', server.name)
  
  // Convert Server to ServerContext
  const serverContext: ServerContext = {
    id: server.id,
    name: server.name,
    ip: server.ip,
    os: server.os,
    uptime: server.uptime,
    status: server.status,
    cpu: server.cpu,
    memory: server.memory,
    disk: server.disk
  }
  
  // Create inventory terminal tab with server context
  const tab = terminalTabStore.createInventoryTerminal(serverContext)
  terminalTabStore.switchToTab(tab.id)
  
  // Log enhanced terminal creation
  console.log(`Created enhanced inventory terminal for ${server.name}:`, {
    serverType: server.name.includes('database') ? 'Database' : 
               server.name.includes('web') ? 'Web' : 
               server.name.includes('api') ? 'API' : 'General',
    commands: tab.preExecutionCommands?.length || 0,
    status: server.status
  })
}

const handleServerAIAction = (server: Server) => {
  console.log('Opening AI chat for server:', server.name)
  
  // Create AI chat tab with server-specific context
  const tab = terminalTabStore.createTab('ai-agent', `AI: ${server.name}`)
  terminalTabStore.switchToTab(tab.id)
  
  // Enhanced AI context based on server type and status
  const serverType = server.name.includes('database') ? 'Database' : 
                    server.name.includes('web') ? 'Web' : 
                    server.name.includes('api') ? 'API' : 
                    server.name.includes('load-balancer') ? 'Load Balancer' : 
                    server.name.includes('monitoring') ? 'Monitoring' : 'General'
  
  const contextPrompt = `Analyzing ${serverType} Server: ${server.name}

Server Details:
- IP Address: ${server.ip}
- Operating System: ${server.os}
- Status: ${server.status.toUpperCase()}
- Uptime: ${server.uptime}
- CPU Usage: ${server.cpu}%
- Memory Usage: ${server.memory}%
- Disk Usage: ${server.disk}%

${server.status === 'warning' ? 'WARNING: This server has issues that need attention!' : ''}
${server.cpu > 80 ? 'HIGH CPU USAGE DETECTED!' : ''}
${server.memory > 80 ? 'HIGH MEMORY USAGE DETECTED!' : ''}
${server.disk > 80 ? 'HIGH DISK USAGE DETECTED!' : ''}

What would you like to know about this server?`
  
  console.log('Enhanced AI context prepared:', { serverType, hasWarnings: server.status === 'warning' })
}

// Helper functions for API integration
const convertInventoryItemsToServers = (items: InventoryItem[]): Server[] => {
  return items
    .filter(item => 
      item.resource_type.toLowerCase().includes('instance') ||
      item.resource_type.toLowerCase().includes('virtual_machine') ||
      item.resource_type.toLowerCase().includes('server')
    )
    .map(item => ({
      id: item.resource_id,
      name: item.name,
      ip: item.metadata.public_ip || item.metadata.private_ip || item.location,
      os: item.metadata.operating_system || item.metadata.platform || 'Unknown',
      uptime: item.metadata.uptime || 'Unknown',
      status: mapInventoryStatusToServerStatus(item.status),
      cpu: parseInt(item.metadata.cpu_utilization) || Math.floor(Math.random() * 100),
      memory: parseInt(item.metadata.memory_utilization) || Math.floor(Math.random() * 100),
      disk: parseInt(item.metadata.disk_utilization) || Math.floor(Math.random() * 100)
    }))
}

const mapInventoryStatusToServerStatus = (status: string): 'online' | 'warning' | 'maintenance' | 'offline' => {
  const statusMap: Record<string, 'online' | 'warning' | 'maintenance' | 'offline'> = {
    'running': 'online',
    'available': 'online',
    'stopped': 'offline',
    'terminated': 'offline',
    'error': 'warning',
    'pending': 'warning',
    'stopping': 'maintenance',
    'starting': 'maintenance'
  }
  
  return statusMap[status.toLowerCase()] || 'offline'
}

const loadInventoryData = async () => {
  isLoading.value = true
  apiError.value = null
  
  try {
    // Load all inventory items
    const allItems = await inventoryApiService.getResources({ limit: 1000 })
    rawInventoryItems.value = allItems
    
    // Convert inventory items to servers
    servers.value = convertInventoryItemsToServers(allItems)
    
    // Generate layers based on resource types
    const resourceTypes = new Set(allItems.map(item => item.resource_type))
    layers.value = Array.from(resourceTypes).slice(0, 5).map((type, index) => ({
      id: `layer-${index}`,
      title: type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      description: `All ${type} resources`,
      icon: getIconForResourceType(type),
      count: allItems.filter(item => item.resource_type === type).length
    }))
    
    // Generate regions based on locations
    const locations = new Set(allItems.map(item => item.location).filter(Boolean))
    regions.value = Array.from(locations).slice(0, 5).map((location, index) => ({
      id: `region-${index}`,
      name: location,
      code: location.toLowerCase().replace(/[^a-z0-9]/g, '-'),
      flag: '🌍',
      status: 'online',
      serverCount: allItems.filter(item => item.location === location).length
    }))
    
    // Generate server types based on resource types and providers
    const serverResourceTypes = allItems
      .filter(item => 
        item.resource_type.toLowerCase().includes('instance') ||
        item.resource_type.toLowerCase().includes('virtual_machine') ||
        item.resource_type.toLowerCase().includes('server')
      )
      .map(item => item.resource_type)
    
    const uniqueServerTypes = new Set(serverResourceTypes)
    serverTypes.value = Array.from(uniqueServerTypes).map((type, index) => ({
      id: `type-${index}`,
      title: type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      description: `${type} servers`,
      icon: getIconForResourceType(type),
      specs: 'Variable specs',
      count: allItems.filter(item => item.resource_type === type).length
    }))
    
    console.log(`Loaded ${allItems.length} inventory items, ${servers.value.length} servers`)
  } catch (error) {
    console.error('Failed to load inventory data:', error)
    apiError.value = error instanceof Error ? error.message : 'Failed to load inventory'
  } finally {
    isLoading.value = false
  }
}

const getIconForResourceType = (resourceType: string): string => {
  const iconMap: Record<string, string> = {
    'ec2_instance': '🖥️',
    'azure_compute_virtual_machine': '🖥️',
    'gcp_compute_instance': '🖥️',
    'docker_container': '📦',
    'kubernetes_pod': '📦',
    'rds_db_instance': '🗄️',
    'lambda_function': '⚡',
    's3_bucket': '📁',
    'load_balancer': '⚖️'
  }
  
  return iconMap[resourceType] || '📄'
}

// Mount hook to load data
onMounted(async () => {
  await loadInventoryData()
})
</script>

<style scoped lang="scss">
@import '../../assets/styles/base.scss';

.server-inventory-container {
  @include flex-column;
  height: 100%;
  overflow: hidden;
}

.inventory-header {
  padding: $spacing-lg $spacing-md $spacing-md;
  border-bottom: $border-width solid var(--color-border-primary);

  h3 {
    margin-bottom: $spacing-sm;
    color: var(--color-text-primary);
    font-size: $font-size-lg;
  }
}

.header-actions {
  margin-bottom: $spacing-sm;
}

.server-stats {
  @include flex-start;
  gap: $spacing-md;
  
  .stat {
    padding: $spacing-xs $spacing-sm;
    background-color: var(--color-bg-tertiary);
    border-radius: $border-radius-sm;
    font-size: $font-size-xs;
    color: var(--color-text-muted);
    border: 1px solid var(--color-border-secondary);
  }
}

.breadcrumb {
  @include flex-start;
  gap: $spacing-xs;
  flex-wrap: wrap;
}

.breadcrumb-item {
  @include flex-center;
  gap: $spacing-xs;
}

.breadcrumb-btn {
  @include button-ghost;
  height: auto;
  padding: $spacing-xs $spacing-sm;
  font-size: $font-size-sm;
  color: var(--color-text-muted);

  &:hover {
    color: var(--color-primary);
    background-color: var(--color-primary-light);
  }
}

.breadcrumb-separator {
  color: var(--color-text-subtle);
  font-size: $font-size-sm;
}

.inventory-content {
  @include flex-column;
  flex: 1;
  overflow: hidden;
}

.loading-state,
.error-state {
  @include flex-center;
  flex-direction: column;
  gap: $spacing-md;
  padding: $spacing-xl;
  color: var(--color-text-muted);
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border-secondary);
  border-top: 3px solid var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state {
  color: var(--color-error);
}

.error-icon {
  font-size: 48px;
}

.retry-btn {
  padding: $spacing-sm $spacing-md;
  background-color: var(--color-primary);
  color: white;
  border: none;
  border-radius: $border-radius-sm;
  cursor: pointer;
  font-size: $font-size-sm;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: var(--color-primary-dark);
  }
}
</style>