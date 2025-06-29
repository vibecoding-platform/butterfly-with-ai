<template>
  <v-container class="cloud-credentials-manager">
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center justify-space-between">
            <div class="d-flex align-center">
              <v-icon class="mr-2" color="primary">mdi-key-variant</v-icon>
              Cloud Credentials Management
            </div>
            <v-btn
              color="primary"
              variant="elevated"
              @click="showAddDialog = true"
              :disabled="loading"
            >
              <v-icon class="mr-2">mdi-plus</v-icon>
              Add Credentials
            </v-btn>
          </v-card-title>

          <v-card-text>
            <!-- Tenant Info -->
            <v-alert
              v-if="currentTenant"
              type="info"
              variant="tonal"
              class="mb-4"
            >
              <v-icon>mdi-domain</v-icon>
              Managing credentials for tenant: <strong>{{ currentTenant.name }}</strong>
            </v-alert>

            <!-- Loading -->
            <v-progress-linear
              v-if="loading"
              indeterminate
              color="primary"
              class="mb-4"
            />

            <!-- Error -->
            <v-alert
              v-if="error"
              type="error"
              variant="outlined"
              class="mb-4"
              closable
              @click:close="error = null"
            >
              {{ error }}
            </v-alert>

            <!-- Success -->
            <v-alert
              v-if="successMessage"
              type="success"
              variant="outlined"
              class="mb-4"
              closable
              @click:close="successMessage = null"
            >
              {{ successMessage }}
            </v-alert>

            <!-- Credentials List -->
            <CredentialsList
              :credentials="credentials"
              :available-providers="availableProviders"
              :loading="loading"
              @test-connection="testConnection"
              @edit-credential="editCredential"
              @delete-credential="confirmDelete"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Add/Edit Credential Dialog -->
    <CredentialDialog
      v-model="showAddDialog"
      :available-providers="availableProviders"
      :editing-credential="editingCredential"
      :saving="saving"
      @save="saveCredential"
      @cancel="cancelEdit"
    />

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="400px">
      <v-card>
        <v-card-title class="text-h5">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          Confirm Deletion
        </v-card-title>
        <v-card-text>
          Are you sure you want to delete the credentials for
          <strong>{{ credentialToDelete?.name }}</strong>?
          This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDeleteDialog = false">Cancel</v-btn>
          <v-btn
            color="error"
            variant="elevated"
            @click="deleteCredential"
            :loading="deleting"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import CredentialsList from './credentials/CredentialsList.vue'
import CredentialDialog from './credentials/CredentialDialog.vue'
import type { Provider } from '@/types/inventory'

// Types
interface CloudCredential {
  id: string
  tenantId: string
  provider: string
  name: string
  status: 'active' | 'error' | 'testing'
  lastTested?: string
  createdAt: string
  updatedAt: string
  testing?: boolean
}

interface Tenant {
  id: string
  name: string
  domain: string
}


// State
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const showAddDialog = ref(false)
const showDeleteDialog = ref(false)

const credentials = ref<CloudCredential[]>([])
const availableProviders = ref<Provider[]>([])
const currentTenant = ref<Tenant | null>(null)
const editingCredential = ref<CloudCredential | null>(null)
const credentialToDelete = ref<CloudCredential | null>(null)



// Methods
const loadCredentials = async () => {
  loading.value = true
  error.value = null
  
  try {
    // Mock data for now - replace with actual API call
    credentials.value = [
      {
        id: '1',
        tenantId: 'tenant-123',
        provider: 'aws',
        name: 'production-aws',
        status: 'active',
        lastTested: '2024-01-15T10:30:00Z',
        createdAt: '2024-01-10T09:00:00Z',
        updatedAt: '2024-01-15T10:30:00Z'
      },
      {
        id: '2',
        tenantId: 'tenant-123',
        provider: 'azure',
        name: 'staging-azure',
        status: 'error',
        lastTested: '2024-01-14T15:20:00Z',
        createdAt: '2024-01-12T11:00:00Z',
        updatedAt: '2024-01-14T15:20:00Z'
      }
    ]

    currentTenant.value = {
      id: 'tenant-123',
      name: 'Acme Corporation',
      domain: 'acme.com'
    }
  } catch (err) {
    error.value = 'Failed to load credentials'
    console.error('Load credentials error:', err)
  } finally {
    loading.value = false
  }
}

const loadProviders = async () => {
  try {
    // Mock data - replace with actual API call
    availableProviders.value = [
      {
        name: 'aws',
        display_name: 'Amazon Web Services',
        required_credentials: ['access_key_id', 'secret_access_key'],
        optional_credentials: ['session_token', 'region']
      },
      {
        name: 'azure',
        display_name: 'Microsoft Azure',
        required_credentials: ['client_id', 'client_secret', 'tenant_id'],
        optional_credentials: ['subscription_id']
      },
      {
        name: 'gcp',
        display_name: 'Google Cloud Platform',
        required_credentials: ['service_account_key'],
        optional_credentials: ['project_id']
      },
      {
        name: 'kubernetes',
        display_name: 'Kubernetes',
        required_credentials: ['kubeconfig'],
        optional_credentials: ['context']
      }
    ]
  } catch (err) {
    error.value = 'Failed to load providers'
    console.error('Load providers error:', err)
  }
}


const resetForm = () => {
  editingCredential.value = null
}

const editCredential = (credential: CloudCredential) => {
  editingCredential.value = credential
  showAddDialog.value = true
}

const cancelEdit = () => {
  showAddDialog.value = false
  resetForm()
}

const saveCredential = async (formData: any) => {
  saving.value = true
  error.value = null

  try {
    const payload = {
      tenantId: currentTenant.value?.id,
      provider: formData.provider,
      name: formData.name,
      credentials: formData.credentials
    }

    if (editingCredential.value) {
      // Update existing credential
      console.log('Updating credential:', payload)
      successMessage.value = 'Credentials updated successfully'
    } else {
      // Create new credential
      console.log('Creating credential:', payload)
      successMessage.value = 'Credentials added successfully'
    }

    if (formData.testOnSave) {
      // Test the connection
      await testConnection({
        provider: formData.provider,
        name: formData.name
      } as CloudCredential)
    }

    showAddDialog.value = false
    resetForm()
    await loadCredentials()
  } catch (err) {
    error.value = 'Failed to save credentials'
    console.error('Save credential error:', err)
  } finally {
    saving.value = false
  }
}

const testConnection = async (credential: CloudCredential) => {
  credential.testing = true
  error.value = null

  try {
    // Mock test - replace with actual API call
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    const success = Math.random() > 0.3 // 70% success rate for demo
    
    if (success) {
      credential.status = 'active'
      credential.lastTested = new Date().toISOString()
      successMessage.value = `Connection test successful for ${credential.name}`
    } else {
      credential.status = 'error'
      error.value = `Connection test failed for ${credential.name}`
    }
  } catch (err) {
    credential.status = 'error'
    error.value = 'Connection test failed'
    console.error('Test connection error:', err)
  } finally {
    credential.testing = false
  }
}

const confirmDelete = (credential: CloudCredential) => {
  credentialToDelete.value = credential
  showDeleteDialog.value = true
}

const deleteCredential = async () => {
  if (!credentialToDelete.value) return

  deleting.value = true
  error.value = null

  try {
    // Mock delete - replace with actual API call
    console.log('Deleting credential:', credentialToDelete.value.id)
    
    credentials.value = credentials.value.filter(c => c.id !== credentialToDelete.value?.id)
    successMessage.value = `Credentials for ${credentialToDelete.value.name} deleted successfully`
    
    showDeleteDialog.value = false
    credentialToDelete.value = null
  } catch (err) {
    error.value = 'Failed to delete credentials'
    console.error('Delete credential error:', err)
  } finally {
    deleting.value = false
  }
}


// Lifecycle
onMounted(async () => {
  await Promise.all([
    loadCredentials(),
    loadProviders()
  ])
})
</script>

<style scoped lang="scss">
.cloud-credentials-manager {
  .v-data-table {
    :deep(.v-data-table__td) {
      vertical-align: middle;
    }
  }

  .v-alert {
    .v-icon {
      margin-right: 8px;
    }
  }

  .v-text-field {
    :deep(.v-field__append-inner) {
      padding-top: 0;
    }
  }
}
</style>