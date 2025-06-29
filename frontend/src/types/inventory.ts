/**
 * TypeScript interfaces for AetherTerm Inventory API
 * Matches backend models from inventory_api.py
 */

export interface InventoryItem {
  provider: string
  resource_type: string
  resource_id: string
  name: string
  status: string
  location: string
  metadata: Record<string, any>
  last_updated: string
}

export interface InventorySummary {
  total_resources: number
  by_provider: Record<string, number>
  by_resource_type: Record<string, number>
  by_status: Record<string, number>
  last_updated: string
}

export interface ConnectionConfig {
  provider: string
  name: string
  credentials: Record<string, string>
  enabled: boolean
}

export interface ConnectionInfo {
  connections: any[]
  active_plugins: string[]
  steampipe_status: string
}

export interface InventorySearchRequest {
  search_term: string
  provider_filter?: string
  resource_type_filter?: string
}

export interface InventoryQueryRequest {
  sql: string
  limit?: number
}

export interface InventoryQueryResponse {
  status: string
  query: string
  data: any[]
  count: number
  execution_time?: number
}

export interface Provider {
  name: string
  display_name: string
  required_credentials: string[]
  optional_credentials: string[]
}

export interface ProvidersResponse {
  cloud_providers: Provider[]
  onpremise_providers: Provider[]
}

export interface ServiceStatus {
  service_status: string
  steampipe_status: string
  active_connections: number
  active_plugins: string[]
  last_check: string
  error?: string
}

export interface SyncResponse {
  status: string
  message: string
  summary: InventorySummary
}

// Legacy inventory item interface for backward compatibility
export interface LegacyInventoryItem {
  id: string
  title: string
  description: string
  type: 'service' | 'file' | 'command' | 'server' | 'container' | 'database'
  icon: string
  location: string
  status?: 'running' | 'stopped' | 'error' | 'unknown'
  command?: string
  aiAnalysisPrompt?: string
  metadata?: Record<string, any>
  provider?: string
  resource_type?: string
  last_updated?: string
}

// Frontend-specific types for UI components
export interface SearchResult {
  id: string
  name: string
  type: 'server' | 'layer' | 'region' | 'serverType' | 'resource'
  ip?: string
  region?: string
  description?: string
  data: any
}

export interface Layer {
  id: string
  title: string
  description: string
  icon: string
  count: number
}

export interface Region {
  id: string
  name: string
  code: string
  flag: string
  status: 'online' | 'offline' | 'maintenance'
  serverCount: number
}

export interface ServerType {
  id: string
  title: string
  description: string
  icon: string
  specs: string
  count: number
}

export interface Server {
  id: string
  name: string
  ip: string
  os: string
  uptime: string
  status: 'online' | 'warning' | 'maintenance' | 'offline'
  cpu: number
  memory: number
  disk: number
}

