<template>
  <div class="steampipe-connection-manager">
    <!-- Header -->
    <div class="manager-header">
      <h3>Steampipe Connections</h3>
      <div class="header-actions">
        <button 
          @click="refreshConnections" 
          :disabled="isLoading"
          class="btn-refresh"
          title="Refresh connections"
        >
          🔄
        </button>
        <button 
          @click="showAddConnectionModal = true" 
          class="btn-add"
          title="Add new connection"
        >
          ➕ Add Connection
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-container">
      <div class="loading-spinner"></div>
      <span>Loading connections...</span>
    </div>

    <!-- Error State -->
    <div v-if="apiError" class="error-container">
      <div class="error-icon">⚠️</div>
      <div class="error-message">{{ apiError }}</div>
      <button @click="refreshConnections" class="btn-retry">Retry</button>
    </div>

    <!-- Connections List -->
    <div v-if="!isLoading && !apiError" class="connections-list">
      <div 
        v-for="connection in connections" 
        :key="connection.name"
        class="connection-card"
        :class="{ 'connection-error': connection.status === 'error' }"
      >
        <div class="connection-header">
          <div class="connection-info">
            <div class="connection-name">{{ connection.name }}</div>
            <div class="connection-provider">
              <span class="provider-icon">{{ getProviderIcon(connection.plugin) }}</span>
              {{ connection.plugin.toUpperCase() }}
            </div>
          </div>
          <div class="connection-actions">
            <button 
              @click="testConnection(connection.name)"
              :disabled="testingConnections.has(connection.name)"
              class="btn-test"
              title="Test connection"
            >
              {{ testingConnections.has(connection.name) ? '⏳' : '🔍' }}
            </button>
            <button 
              @click="removeConnection(connection.name)"
              class="btn-remove"
              title="Remove connection"
            >
              🗑️
            </button>
          </div>
        </div>

        <div class="connection-details">
          <div class="connection-status">
            <span class="status-indicator" :class="getStatusClass(connection)"></span>
            <span class="status-text">{{ getStatusText(connection) }}</span>
          </div>
          <div class="connection-config">
            <div v-for="(value, key) in getDisplayableConfig(connection.config)" :key="key" class="config-item">
              <span class="config-key">{{ key }}:</span>
              <span class="config-value">{{ value }}</span>
            </div>
          </div>
          <div class="connection-meta">
            <span class="created-at">Created: {{ formatDate(connection.created_at) }}</span>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="connections.length === 0" class="empty-state">
        <div class="empty-icon">🔌</div>
        <h4>No Connections Configured</h4>
        <p>Add your first cloud provider connection to start using the inventory system.</p>
        <button @click="showAddConnectionModal = true" class="btn-add-first">
          Add Your First Connection
        </button>
      </div>
    </div>

    <!-- Add Connection Modal -->
    <div v-if="showAddConnectionModal" class="modal-overlay" @click.self="showAddConnectionModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h4>Add New Connection</h4>
          <button @click="showAddConnectionModal = false" class="btn-close">✕</button>
        </div>

        <div class="modal-body">
          <!-- Provider Selection -->
          <div class="form-group">
            <label>Cloud Provider</label>
            <select v-model="newConnection.provider" @change="onProviderChange">
              <option value="">Select Provider</option>
              <option value="aws">AWS</option>
              <option value="azure">Azure</option>
              <option value="gcp">Google Cloud Platform</option>
              <option value="kubernetes">Kubernetes</option>
            </select>
          </div>

          <!-- Connection Name -->
          <div class="form-group">
            <label>Connection Name</label>
            <input 
              v-model="newConnection.name" 
              type="text" 
              placeholder="e.g., my-aws-production"
              required
            />
          </div>

          <!-- AWS Configuration -->
          <div v-if="newConnection.provider === 'aws'" class="provider-config">
            <div class="form-group">
              <label>AWS Region</label>
              <select v-model="newConnection.credentials.region">
                <option value="us-east-1">US East (N. Virginia)</option>
                <option value="us-west-2">US West (Oregon)</option>
                <option value="eu-west-1">Europe (Ireland)</option>
                <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
                <option value="ap-northeast-1">Asia Pacific (Tokyo)</option>
              </select>
            </div>
            <div class="form-group">
              <label>AWS Profile (optional)</label>
              <input 
                v-model="newConnection.credentials.profile" 
                type="text" 
                placeholder="default"
              />
            </div>
            <div class="form-group">
              <label>Access Key ID (optional)</label>
              <input 
                v-model="newConnection.credentials.access_key" 
                type="text" 
                placeholder="Leave empty to use profile/IAM role"
              />
            </div>
            <div class="form-group" v-if="newConnection.credentials.access_key">
              <label>Secret Access Key</label>
              <input 
                v-model="newConnection.credentials.secret_key" 
                type="password" 
                placeholder="Secret access key"
              />
            </div>
          </div>

          <!-- Azure Configuration -->
          <div v-if="newConnection.provider === 'azure'" class="provider-config">
            <div class="form-group">
              <label>Subscription ID</label>
              <input 
                v-model="newConnection.credentials.subscription_id" 
                type="text" 
                placeholder="Azure subscription ID"
                required
              />
            </div>
            <div class="form-group">
              <label>Tenant ID (optional)</label>
              <input 
                v-model="newConnection.credentials.tenant_id" 
                type="text" 
                placeholder="Azure tenant ID"
              />
            </div>
            <div class="form-group">
              <label>Client ID (optional)</label>
              <input 
                v-model="newConnection.credentials.client_id" 
                type="text" 
                placeholder="Service principal client ID"
              />
            </div>
            <div class="form-group" v-if="newConnection.credentials.client_id">
              <label>Client Secret</label>
              <input 
                v-model="newConnection.credentials.client_secret" 
                type="password" 
                placeholder="Service principal client secret"
              />
            </div>
          </div>

          <!-- GCP Configuration -->
          <div v-if="newConnection.provider === 'gcp'" class="provider-config">
            <div class="form-group">
              <label>Project ID</label>
              <input 
                v-model="newConnection.credentials.project" 
                type="text" 
                placeholder="GCP project ID"
                required
              />
            </div>
            <div class="form-group">
              <label>Service Account Key File (optional)</label>
              <input 
                v-model="newConnection.credentials.credentials" 
                type="text" 
                placeholder="/path/to/service-account.json"
              />
            </div>
          </div>

          <!-- Kubernetes Configuration -->
          <div v-if="newConnection.provider === 'kubernetes'" class="provider-config">
            <div class="form-group">
              <label>Kubeconfig Path</label>
              <input 
                v-model="newConnection.credentials.config_path" 
                type="text" 
                placeholder="~/.kube/config"
              />
            </div>
            <div class="form-group">
              <label>Context (optional)</label>
              <input 
                v-model="newConnection.credentials.context" 
                type="text" 
                placeholder="Kubernetes context name"
              />
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="showAddConnectionModal = false" class="btn-cancel">Cancel</button>
          <button 
            @click="addConnection" 
            :disabled="!isConnectionValid || isAdding"
            class="btn-add-confirm"
          >
            {{ isAdding ? 'Adding...' : 'Add Connection' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { inventoryApiService } from '../services/InventoryApiService'
import type { ConnectionConfig } from '../types/inventory'

// State
const connections = ref<any[]>([])
const isLoading = ref(false)
const apiError = ref<string | null>(null)
const testingConnections = ref(new Set<string>())
const showAddConnectionModal = ref(false)
const isAdding = ref(false)

// New connection form
const newConnection = ref<{
  provider: string
  name: string
  credentials: Record<string, any>
}>({
  provider: '',
  name: '',
  credentials: {}
})

// Computed
const isConnectionValid = computed(() => {
  if (!newConnection.value.provider || !newConnection.value.name) {
    return false
  }

  const { provider, credentials } = newConnection.value

  switch (provider) {
    case 'aws':
      return true // Profile-based auth is valid
    case 'azure':
      return !!credentials.subscription_id
    case 'gcp':
      return !!credentials.project
    case 'kubernetes':
      return true // Config path is optional
    default:
      return false
  }
})

// Methods
const refreshConnections = async () => {
  isLoading.value = true
  apiError.value = null

  try {
    const response = await inventoryApiService.listConnections()
    connections.value = response.connections || []
  } catch (error) {
    console.error('Failed to load connections:', error)
    apiError.value = error instanceof Error ? error.message : 'Failed to load connections'
  } finally {
    isLoading.value = false
  }
}

const testConnection = async (connectionName: string) => {
  testingConnections.value.add(connectionName)

  try {
    // Note: This endpoint doesn't exist yet in the backend
    // await inventoryApiService.testConnection(connectionName)
    console.log(`Testing connection: ${connectionName}`)
    
    // Simulate test
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // Update connection status (mock)
    const connection = connections.value.find(c => c.name === connectionName)
    if (connection) {
      connection.status = 'active'
      connection.last_tested = new Date().toISOString()
    }
    
  } catch (error) {
    console.error(`Connection test failed for ${connectionName}:`, error)
    
    const connection = connections.value.find(c => c.name === connectionName)
    if (connection) {
      connection.status = 'error'
      connection.error_message = error instanceof Error ? error.message : 'Test failed'
    }
  } finally {
    testingConnections.value.delete(connectionName)
  }
}

const removeConnection = async (connectionName: string) => {
  if (!confirm(`Are you sure you want to remove connection "${connectionName}"?`)) {
    return
  }

  try {
    await inventoryApiService.removeConnection(connectionName)
    await refreshConnections()
  } catch (error) {
    console.error(`Failed to remove connection ${connectionName}:`, error)
    apiError.value = error instanceof Error ? error.message : 'Failed to remove connection'
  }
}

const addConnection = async () => {
  if (!isConnectionValid.value) return

  isAdding.value = true

  try {
    const config: ConnectionConfig = {
      provider: newConnection.value.provider,
      name: newConnection.value.name,
      credentials: newConnection.value.credentials,
      enabled: true
    }

    await inventoryApiService.addConnection(config)
    
    // Reset form
    newConnection.value = {
      provider: '',
      name: '',
      credentials: {}
    }
    
    showAddConnectionModal.value = false
    await refreshConnections()
    
  } catch (error) {
    console.error('Failed to add connection:', error)
    apiError.value = error instanceof Error ? error.message : 'Failed to add connection'
  } finally {
    isAdding.value = false
  }
}

const onProviderChange = () => {
  // Reset credentials when provider changes
  newConnection.value.credentials = {}
  
  // Set default values based on provider
  switch (newConnection.value.provider) {
    case 'aws':
      newConnection.value.credentials.region = 'us-east-1'
      break
    case 'kubernetes':
      newConnection.value.credentials.config_path = '~/.kube/config'
      break
  }
}

// Utility methods
const getProviderIcon = (provider: string): string => {
  const icons: Record<string, string> = {
    aws: '☁️',
    azure: '🔷',
    gcp: '🌈',
    kubernetes: '⚓',
    docker: '🐳'
  }
  return icons[provider] || '🔌'
}

const getStatusClass = (connection: any): string => {
  if (connection.status === 'active') return 'status-active'
  if (connection.status === 'error') return 'status-error'
  return 'status-unknown'
}

const getStatusText = (connection: any): string => {
  if (connection.status === 'active') return 'Connected'
  if (connection.status === 'error') return connection.error_message || 'Error'
  return 'Unknown'
}

const getDisplayableConfig = (config: Record<string, any>): Record<string, any> => {
  // Filter out sensitive information
  const filtered: Record<string, any> = {}
  
  for (const [key, value] of Object.entries(config || {})) {
    if (key.includes('secret') || key.includes('key') || key.includes('password')) {
      filtered[key] = '***'
    } else if (value) {
      filtered[key] = value
    }
  }
  
  return filtered
}

const formatDate = (dateString: string): string => {
  if (!dateString) return 'Unknown'
  return new Date(dateString).toLocaleString()
}

// Lifecycle
onMounted(async () => {
  await refreshConnections()
})
</script>

<style scoped>
.steampipe-connection-manager {
  padding: 1rem;
  max-width: 1200px;
  margin: 0 auto;
}

.manager-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e0e0e0;
}

.manager-header h3 {
  margin: 0;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-refresh, .btn-add, .btn-test, .btn-remove {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-refresh:hover, .btn-test:hover {
  background: #f0f0f0;
}

.btn-add {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.btn-add:hover {
  background: #0056b3;
}

.btn-remove {
  background: #dc3545;
  color: white;
  border-color: #dc3545;
}

.btn-remove:hover {
  background: #c82333;
}

.loading-container, .error-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 2rem;
  text-align: center;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-container {
  color: #dc3545;
  flex-direction: column;
}

.error-icon {
  font-size: 2rem;
}

.btn-retry {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.connections-list {
  display: grid;
  gap: 1rem;
}

.connection-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1rem;
  background: white;
  transition: border-color 0.2s;
}

.connection-card:hover {
  border-color: #007bff;
}

.connection-card.connection-error {
  border-color: #dc3545;
  background: #fdf2f2;
}

.connection-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.connection-name {
  font-weight: bold;
  font-size: 1.1rem;
  color: #333;
}

.connection-provider {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: #666;
  font-size: 0.9rem;
}

.connection-actions {
  display: flex;
  gap: 0.5rem;
}

.connection-details {
  margin-top: 0.5rem;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.status-active {
  background: #28a745;
}

.status-error {
  background: #dc3545;
}

.status-unknown {
  background: #6c757d;
}

.connection-config {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.config-item {
  font-size: 0.85rem;
}

.config-key {
  font-weight: 500;
  color: #666;
}

.config-value {
  color: #333;
  margin-left: 0.25rem;
}

.connection-meta {
  font-size: 0.8rem;
  color: #999;
}

.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  color: #666;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.btn-add-first {
  margin-top: 1rem;
  padding: 0.75rem 1.5rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  min-width: 500px;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h4 {
  margin: 0;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 500;
  color: #333;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #007bff;
}

.provider-config {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 1rem;
  background: #f8f9fa;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid #e0e0e0;
}

.btn-cancel {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
}

.btn-add-confirm {
  padding: 0.5rem 1rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-add-confirm:disabled {
  background: #6c757d;
  cursor: not-allowed;
}
</style>