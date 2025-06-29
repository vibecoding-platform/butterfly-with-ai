/**
 * Inventory API Service
 * Handles all HTTP requests to the AetherTerm Inventory API
 */

import { apiBaseUrl } from '../config/environment'
import type {
  InventoryItem,
  InventorySummary,
  ConnectionConfig,
  ConnectionInfo,
  InventorySearchRequest,
  InventoryQueryRequest,
  InventoryQueryResponse,
  ProvidersResponse,
  ServiceStatus,
  SyncResponse
} from '../types/inventory'

class InventoryApiService {
  private baseUrl: string

  constructor() {
    this.baseUrl = `${apiBaseUrl}/api/inventory`
  }

  /**
   * Make HTTP request with error handling
   */
  private async makeRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(`HTTP ${response.status}: ${errorData.detail || errorData.message || 'Request failed'}`)
      }

      return await response.json()
    } catch (error) {
      console.error(`Inventory API request failed [${endpoint}]:`, error)
      throw error
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; service: string; timestamp: string }> {
    return this.makeRequest('/health')
  }

  /**
   * Get service status
   */
  async getServiceStatus(): Promise<ServiceStatus> {
    return this.makeRequest('/status')
  }

  /**
   * Get inventory summary
   */
  async getInventorySummary(): Promise<InventorySummary> {
    return this.makeRequest('/summary')
  }

  /**
   * Get all inventory resources
   */
  async getResources(options: {
    limit?: number
    provider?: string
    resource_type?: string
  } = {}): Promise<InventoryItem[]> {
    const params = new URLSearchParams()
    
    if (options.limit) params.append('limit', options.limit.toString())
    if (options.provider) params.append('provider', options.provider)
    if (options.resource_type) params.append('resource_type', options.resource_type)
    
    const endpoint = `/resources${params.toString() ? `?${params.toString()}` : ''}`
    return this.makeRequest(endpoint)
  }

  /**
   * Search inventory
   */
  async searchInventory(searchRequest: InventorySearchRequest): Promise<InventoryItem[]> {
    return this.makeRequest('/search', {
      method: 'POST',
      body: JSON.stringify(searchRequest),
    })
  }

  /**
   * Execute custom SQL query
   */
  async executeQuery(queryRequest: InventoryQueryRequest): Promise<InventoryQueryResponse> {
    return this.makeRequest('/query', {
      method: 'POST',
      body: JSON.stringify(queryRequest),
    })
  }

  /**
   * List connections
   */
  async listConnections(): Promise<ConnectionInfo> {
    return this.makeRequest('/connections')
  }

  /**
   * Add new connection
   */
  async addConnection(config: ConnectionConfig): Promise<{ status: string; message: string; connection: any }> {
    return this.makeRequest('/connections', {
      method: 'POST',
      body: JSON.stringify(config),
    })
  }

  /**
   * Remove connection
   */
  async removeConnection(connectionName: string): Promise<{ status: string; message: string }> {
    return this.makeRequest(`/connections/${encodeURIComponent(connectionName)}`, {
      method: 'DELETE',
    })
  }

  /**
   * Get supported providers
   */
  async getSupportedProviders(): Promise<ProvidersResponse> {
    return this.makeRequest('/providers')
  }

  /**
   * Trigger inventory sync
   */
  async syncInventory(): Promise<SyncResponse> {
    return this.makeRequest('/sync', {
      method: 'POST',
    })
  }

  /**
   * Convert inventory items to legacy format for backward compatibility
   */
  convertToLegacyFormat(items: InventoryItem[]): any[] {
    return items.map(item => ({
      id: item.resource_id,
      title: item.name,
      description: `${item.resource_type} from ${item.provider}`,
      type: this.mapResourceTypeToLegacyType(item.resource_type),
      icon: this.getIconForResourceType(item.resource_type),
      location: item.location,
      status: this.mapStatusToLegacyStatus(item.status),
      command: this.generateCommandForResource(item),
      aiAnalysisPrompt: `Analyze ${item.resource_type} ${item.name} from ${item.provider}`,
      metadata: item.metadata,
      provider: item.provider,
      resource_type: item.resource_type,
      last_updated: item.last_updated
    }))
  }

  /**
   * Map resource type to legacy type
   */
  private mapResourceTypeToLegacyType(resourceType: string): string {
    const typeMap: Record<string, string> = {
      'ec2_instance': 'server',
      'azure_compute_virtual_machine': 'server',
      'gcp_compute_instance': 'server',
      'kubernetes_node': 'server',
      'vsphere_virtual_machine': 'server',
      'docker_container': 'container',
      'kubernetes_pod': 'container',
      'rds_db_instance': 'database',
      'azure_sql_database': 'database',
      'gcp_sql_database_instance': 'database',
      's3_bucket': 'file',
      'azure_storage_account': 'file',
      'gcp_storage_bucket': 'file',
      'lambda_function': 'service',
      'azure_function_app': 'service',
      'gcp_cloud_function': 'service'
    }
    
    return typeMap[resourceType] || 'service'
  }

  /**
   * Get icon for resource type
   */
  private getIconForResourceType(resourceType: string): string {
    const iconMap: Record<string, string> = {
      'ec2_instance': '🖥️',
      'azure_compute_virtual_machine': '🖥️',
      'gcp_compute_instance': '🖥️',
      'kubernetes_node': '🖥️',
      'vsphere_virtual_machine': '🖥️',
      'docker_container': '📦',
      'kubernetes_pod': '📦',
      'rds_db_instance': '🗄️',
      'azure_sql_database': '🗄️',
      'gcp_sql_database_instance': '🗄️',
      's3_bucket': '📁',
      'azure_storage_account': '📁',
      'gcp_storage_bucket': '📁',
      'lambda_function': '⚡',
      'azure_function_app': '⚡',
      'gcp_cloud_function': '⚡',
      'load_balancer': '⚖️',
      'security_group': '🛡️',
      'vpc': '🌐',
      'subnet': '🌐'
    }
    
    return iconMap[resourceType] || '📄'
  }

  /**
   * Map status to legacy status format
   */
  private mapStatusToLegacyStatus(status: string): string {
    const statusMap: Record<string, string> = {
      'running': 'running',
      'stopped': 'stopped',
      'pending': 'unknown',
      'terminated': 'error',
      'error': 'error',
      'available': 'running',
      'unavailable': 'stopped'
    }
    
    return statusMap[status.toLowerCase()] || 'unknown'
  }

  /**
   * Generate command for resource
   */
  private generateCommandForResource(item: InventoryItem): string {
    const resourceType = item.resource_type.toLowerCase()
    
    if (resourceType.includes('instance') || resourceType.includes('virtual_machine')) {
      return `# Connect to ${item.name}\necho "Server: ${item.name} (${item.provider})"\necho "Status: ${item.status}"`
    } else if (resourceType.includes('container') || resourceType.includes('pod')) {
      return `# Container info for ${item.name}\necho "Container: ${item.name}"\necho "Provider: ${item.provider}"`
    } else if (resourceType.includes('database')) {
      return `# Database info for ${item.name}\necho "Database: ${item.name}"\necho "Status: ${item.status}"`
    } else if (resourceType.includes('bucket') || resourceType.includes('storage')) {
      return `# Storage info for ${item.name}\necho "Storage: ${item.name}"\necho "Location: ${item.location}"`
    } else {
      return `# Resource info for ${item.name}\necho "Resource: ${item.name} (${item.resource_type})"\necho "Provider: ${item.provider}"`
    }
  }
}

// Export singleton instance
export const inventoryApiService = new InventoryApiService()
export default inventoryApiService