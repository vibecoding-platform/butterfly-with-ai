<template>
  <v-data-table
    :headers="headers"
    :items="credentials"
    :loading="loading"
    item-value="id"
    class="elevation-1"
  >
    <template v-slot:item.provider="{ item }">
      <div class="d-flex align-center">
        <v-icon :color="getProviderColor(item.provider)" class="mr-2">
          {{ getProviderIcon(item.provider) }}
        </v-icon>
        {{ getProviderDisplayName(item.provider) }}
      </div>
    </template>

    <template v-slot:item.status="{ item }">
      <v-chip
        :color="item.status === 'active' ? 'success' : item.status === 'testing' ? 'warning' : 'error'"
        size="small"
        variant="tonal"
      >
        <v-icon class="mr-1" size="small">
          {{ item.status === 'active' ? 'mdi-check-circle' : 
              item.status === 'testing' ? 'mdi-clock' : 'mdi-alert-circle' }}
        </v-icon>
        {{ item.status }}
      </v-chip>
    </template>

    <template v-slot:item.lastTested="{ item }">
      <span v-if="item.lastTested">
        {{ formatDate(item.lastTested) }}
      </span>
      <span v-else class="text-disabled">Never</span>
    </template>

    <template v-slot:item.actions="{ item }">
      <v-btn
        icon="mdi-test-tube"
        size="small"
        variant="text"
        color="primary"
        @click="$emit('test-connection', item)"
        :loading="item.testing"
        title="Test Connection"
      />
      <v-btn
        icon="mdi-pencil"
        size="small"
        variant="text"
        color="primary"
        @click="$emit('edit-credential', item)"
        title="Edit"
      />
      <v-btn
        icon="mdi-delete"
        size="small"
        variant="text"
        color="error"
        @click="$emit('delete-credential', item)"
        title="Delete"
      />
    </template>

    <template v-slot:no-data>
      <div class="text-center py-8">
        <v-icon size="64" color="grey-lighten-2">mdi-key-off</v-icon>
        <p class="text-h6 mt-4 mb-2">No credentials configured</p>
        <p class="text-body-2 text-disabled">
          Add cloud provider credentials to start managing your infrastructure
        </p>
      </div>
    </template>
  </v-data-table>
</template>

<script setup lang="ts">
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

// Props
interface Props {
  credentials: CloudCredential[]
  availableProviders: Provider[]
  loading?: boolean
}

withDefaults(defineProps<Props>(), {
  loading: false
})

// Emits
defineEmits<{
  'test-connection': [credential: CloudCredential]
  'edit-credential': [credential: CloudCredential]
  'delete-credential': [credential: CloudCredential]
}>()

// Constants
const headers = [
  { title: 'Provider', key: 'provider', sortable: true },
  { title: 'Name', key: 'name', sortable: true },
  { title: 'Status', key: 'status', sortable: true },
  { title: 'Last Tested', key: 'lastTested', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, width: '150px' }
]

// Methods
const getProviderIcon = (provider: string): string => {
  const icons: Record<string, string> = {
    aws: 'mdi-aws',
    azure: 'mdi-microsoft-azure',
    gcp: 'mdi-google-cloud',
    kubernetes: 'mdi-kubernetes'
  }
  return icons[provider] || 'mdi-cloud'
}

const getProviderColor = (provider: string): string => {
  const colors: Record<string, string> = {
    aws: 'orange-darken-2',
    azure: 'blue',
    gcp: 'red',
    kubernetes: 'blue-darken-2'
  }
  return colors[provider] || 'grey'
}

const getProviderDisplayName = (provider: string): string => {
  const availableProviders = defineProps<Props>().availableProviders
  const provider$ = availableProviders.find(p => p.name === provider)
  return provider$?.display_name || provider
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped lang="scss">
.v-data-table {
  :deep(.v-data-table__td) {
    vertical-align: middle;
  }
}
</style>