/**
 * Inventory Store
 * Pinia store for managing inventory state and API interactions
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { inventoryApiService } from '../services/InventoryApiService'
import type {
  InventoryItem,
  InventorySummary,
  ConnectionInfo,
  ConnectionConfig,
  ServiceStatus,
  InventorySearchRequest
} from '../types/inventory'

export const useInventoryStore = defineStore('inventory', () => {
  // State
  const items = ref<InventoryItem[]>([])
  const summary = ref<InventorySummary | null>(null)
  const connections = ref<ConnectionInfo | null>(null)
  const serviceStatus = ref<ServiceStatus | null>(null)
  const isLoading = ref(false)
  const isSearching = ref(false)
  const lastError = ref<string | null>(null)
  const lastSync = ref<Date | null>(null)

  // Computed
  const itemsByProvider = computed(() => {
    const grouped: Record<string, InventoryItem[]> = {}
    items.value.forEach(item => {
      if (!grouped[item.provider]) {
        grouped[item.provider] = []
      }
      grouped[item.provider].push(item)
    })
    return grouped
  })

  const itemsByResourceType = computed(() => {
    const grouped: Record<string, InventoryItem[]> = {}
    items.value.forEach(item => {
      if (!grouped[item.resource_type]) {
        grouped[item.resource_type] = []
      }
      grouped[item.resource_type].push(item)
    })
    return grouped
  })

  const itemsByStatus = computed(() => {
    const grouped: Record<string, InventoryItem[]> = {}
    items.value.forEach(item => {
      if (!grouped[item.status]) {
        grouped[item.status] = []
      }
      grouped[item.status].push(item)
    })
    return grouped
  })

  const totalResources = computed(() => items.value.length)

  const healthyResources = computed(() => 
    items.value.filter(item => 
      item.status.toLowerCase() === 'running' || 
      item.status.toLowerCase() === 'available'
    ).length
  )

  const warningResources = computed(() =>
    items.value.filter(item =>
      item.status.toLowerCase() === 'warning' ||
      item.status.toLowerCase() === 'error' ||
      item.status.toLowerCase() === 'pending'
    ).length
  )

  const offlineResources = computed(() =>
    items.value.filter(item =>
      item.status.toLowerCase() === 'stopped' ||
      item.status.toLowerCase() === 'terminated' ||
      item.status.toLowerCase() === 'unavailable'
    ).length
  )

  // Actions
  const clearError = () => {
    lastError.value = null
  }

  const setLoading = (loading: boolean) => {
    isLoading.value = loading
  }

  const setSearching = (searching: boolean) => {
    isSearching.value = searching
  }

  /**
   * Load all inventory items
   */
  const loadItems = async (options: {
    limit?: number
    provider?: string
    resource_type?: string
    refresh?: boolean
  } = {}) => {
    // Skip if already loaded and not refreshing
    if (items.value.length > 0 && !options.refresh) {
      return items.value
    }

    isLoading.value = true
    lastError.value = null

    try {
      const loadedItems = await inventoryApiService.getResources(options)
      items.value = loadedItems
      lastSync.value = new Date()
      console.log(`Loaded ${loadedItems.length} inventory items`)
      return loadedItems
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load inventory'
      lastError.value = errorMessage
      console.error('Failed to load inventory items:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Search inventory
   */
  const searchItems = async (searchRequest: InventorySearchRequest) => {
    isSearching.value = true
    lastError.value = null

    try {
      const results = await inventoryApiService.searchInventory(searchRequest)
      console.log(`Found ${results.length} search results`)
      return results
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Search failed'
      lastError.value = errorMessage
      console.error('Search failed:', error)
      throw error
    } finally {
      isSearching.value = false
    }
  }

  /**
   * Load inventory summary
   */
  const loadSummary = async (refresh = false) => {
    if (summary.value && !refresh) {
      return summary.value
    }

    try {
      const loadedSummary = await inventoryApiService.getInventorySummary()
      summary.value = loadedSummary
      return loadedSummary
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load summary'
      lastError.value = errorMessage
      console.error('Failed to load inventory summary:', error)
      throw error
    }
  }

  /**
   * Load connections info
   */
  const loadConnections = async (refresh = false) => {
    if (connections.value && !refresh) {
      return connections.value
    }

    try {
      const loadedConnections = await inventoryApiService.listConnections()
      connections.value = loadedConnections
      return loadedConnections
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load connections'
      lastError.value = errorMessage
      console.error('Failed to load connections:', error)
      throw error
    }
  }

  /**
   * Load service status
   */
  const loadServiceStatus = async () => {
    try {
      const status = await inventoryApiService.getServiceStatus()
      serviceStatus.value = status
      return status
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load service status'
      lastError.value = errorMessage
      console.error('Failed to load service status:', error)
      throw error
    }
  }

  /**
   * Add new connection
   */
  const addConnection = async (config: ConnectionConfig) => {
    try {
      const result = await inventoryApiService.addConnection(config)
      // Refresh connections after adding
      await loadConnections(true)
      return result
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to add connection'
      lastError.value = errorMessage
      console.error('Failed to add connection:', error)
      throw error
    }
  }

  /**
   * Remove connection
   */
  const removeConnection = async (connectionName: string) => {
    try {
      const result = await inventoryApiService.removeConnection(connectionName)
      // Refresh connections after removing
      await loadConnections(true)
      return result
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to remove connection'
      lastError.value = errorMessage
      console.error('Failed to remove connection:', error)
      throw error
    }
  }

  /**
   * Sync inventory (refresh all data)
   */
  const syncInventory = async () => {
    isLoading.value = true
    lastError.value = null

    try {
      const syncResult = await inventoryApiService.syncInventory()
      
      // Refresh all data after sync
      await Promise.all([
        loadItems({ refresh: true }),
        loadSummary(true),
        loadConnections(true),
        loadServiceStatus()
      ])

      lastSync.value = new Date()
      console.log('Inventory sync completed:', syncResult)
      return syncResult
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Sync failed'
      lastError.value = errorMessage
      console.error('Inventory sync failed:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Initialize store (load basic data)
   */
  const initialize = async () => {
    try {
      await Promise.all([
        loadItems(),
        loadSummary(),
        loadServiceStatus()
      ])
      console.log('Inventory store initialized')
    } catch (error) {
      console.error('Failed to initialize inventory store:', error)
      // Don't throw - allow partial initialization
    }
  }

  /**
   * Filter items by criteria
   */
  const filterItems = (filters: {
    provider?: string
    resource_type?: string
    status?: string
    search?: string
  }) => {
    return items.value.filter(item => {
      if (filters.provider && item.provider !== filters.provider) return false
      if (filters.resource_type && item.resource_type !== filters.resource_type) return false
      if (filters.status && item.status !== filters.status) return false
      if (filters.search) {
        const search = filters.search.toLowerCase()
        return (
          item.name.toLowerCase().includes(search) ||
          item.resource_type.toLowerCase().includes(search) ||
          item.provider.toLowerCase().includes(search) ||
          item.location.toLowerCase().includes(search)
        )
      }
      return true
    })
  }

  /**
   * Get items by provider
   */
  const getItemsByProvider = (provider: string) => {
    return items.value.filter(item => item.provider === provider)
  }

  /**
   * Get items by resource type
   */
  const getItemsByResourceType = (resourceType: string) => {
    return items.value.filter(item => item.resource_type === resourceType)
  }

  /**
   * Get item by ID
   */
  const getItemById = (id: string) => {
    return items.value.find(item => item.resource_id === id)
  }

  return {
    // State
    items,
    summary,
    connections,
    serviceStatus,
    isLoading,
    isSearching,
    lastError,
    lastSync,

    // Computed
    itemsByProvider,
    itemsByResourceType,
    itemsByStatus,
    totalResources,
    healthyResources,
    warningResources,
    offlineResources,

    // Actions
    clearError,
    setLoading,
    setSearching,
    loadItems,
    searchItems,
    loadSummary,
    loadConnections,
    loadServiceStatus,
    addConnection,
    removeConnection,
    syncInventory,
    initialize,
    filterItems,
    getItemsByProvider,
    getItemsByResourceType,
    getItemById
  }
})