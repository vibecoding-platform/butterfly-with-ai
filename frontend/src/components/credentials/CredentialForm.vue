<template>
  <v-form ref="credentialForm" v-model="formValid">
    <!-- Provider Selection -->
    <v-select
      v-model="form.provider"
      :items="availableProviders"
      item-title="display_name"
      item-value="name"
      label="Cloud Provider"
      required
      :rules="[(v: any) => !!v || 'Provider is required']"
      :disabled="!!editingCredential"
      class="mb-4"
    >
      <template v-slot:selection="{ item }">
        <div class="d-flex align-center">
          <v-icon :color="getProviderColor(item.value)" class="mr-2">
            {{ getProviderIcon(item.value) }}
          </v-icon>
          {{ item.title }}
        </div>
      </template>
      <template v-slot:item="{ item, props }">
        <v-list-item v-bind="props">
          <template v-slot:prepend>
            <v-icon :color="getProviderColor(item.value)">
              {{ getProviderIcon(item.value) }}
            </v-icon>
          </template>
        </v-list-item>
      </template>
    </v-select>

    <!-- Connection Name -->
    <v-text-field
      v-model="form.name"
      label="Connection Name"
      hint="Unique identifier for this connection"
      persistent-hint
      required
      :rules="nameRules"
      class="mb-4"
    />

    <!-- Dynamic Credential Fields -->
    <div v-if="selectedProvider">
      <h4 class="text-h6 mb-3">Required Credentials</h4>
      <div
        v-for="field in selectedProvider.required_credentials"
        :key="field"
        class="mb-4"
      >
        <v-text-field
          v-model="form.credentials[field]"
          :label="getFieldLabel(field)"
          :hint="getFieldHint(field)"
          persistent-hint
          required
          :rules="[(v: any) => !!v || `${getFieldLabel(field)} is required`]"
          :type="isSecretField(field) && !showSecrets[field] ? 'password' : 'text'"
          :append-inner-icon="isSecretField(field) ? (showSecrets[field] ? 'mdi-eye-off' : 'mdi-eye') : undefined"
          @click:append-inner="toggleSecretVisibility(field)"
        />
      </div>

      <div v-if="selectedProvider.optional_credentials?.length">
        <h4 class="text-h6 mb-3 mt-6">Optional Credentials</h4>
        <div
          v-for="field in selectedProvider.optional_credentials"
          :key="field"
          class="mb-4"
        >
          <v-text-field
            v-model="form.credentials[field]"
            :label="getFieldLabel(field)"
            :hint="getFieldHint(field)"
            persistent-hint
            :type="isSecretField(field) && !showSecrets[field] ? 'password' : 'text'"
            :append-inner-icon="isSecretField(field) ? (showSecrets[field] ? 'mdi-eye-off' : 'mdi-eye') : undefined"
            @click:append-inner="toggleSecretVisibility(field)"
          />
        </div>
      </div>
    </div>

    <!-- Test on Save -->
    <v-switch
      v-model="form.testOnSave"
      label="Test connection after saving"
      color="primary"
      class="mt-4"
    />
  </v-form>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue'
import type { Provider } from '@/types/inventory'

// Props
interface Props {
  availableProviders: Provider[]
  editingCredential?: any
  modelValue: any
}

const props = withDefaults(defineProps<Props>(), {
  editingCredential: null
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: any]
  'update:valid': [valid: boolean]
}>()

// State
const credentialForm = ref()
const formValid = ref(false)
const showSecrets = ref<Record<string, boolean>>({})

const form = reactive({
  provider: '',
  name: '',
  credentials: {} as Record<string, string>,
  testOnSave: true
})

// Computed
const selectedProvider = computed(() =>
  props.availableProviders.find(p => p.name === form.provider)
)

const nameRules = [
  (v: string) => !!v || 'Name is required',
  (v: string) => v?.length >= 3 || 'Name must be at least 3 characters',
  (v: string) => /^[a-zA-Z0-9_-]+$/.test(v) || 'Name can only contain letters, numbers, hyphens, and underscores'
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

const getFieldLabel = (field: string): string => {
  const labels: Record<string, string> = {
    access_key_id: 'Access Key ID',
    secret_access_key: 'Secret Access Key',
    session_token: 'Session Token',
    region: 'Default Region',
    client_id: 'Client ID',
    client_secret: 'Client Secret',
    tenant_id: 'Tenant ID',
    subscription_id: 'Subscription ID',
    service_account_key: 'Service Account Key (JSON)',
    project_id: 'Project ID',
    kubeconfig: 'Kubeconfig',
    context: 'Context'
  }
  return labels[field] || field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const getFieldHint = (field: string): string => {
  const hints: Record<string, string> = {
    access_key_id: 'Your AWS access key ID',
    secret_access_key: 'Your AWS secret access key',
    session_token: 'AWS session token (for temporary credentials)',
    region: 'Default AWS region (e.g., us-east-1)',
    client_id: 'Azure application (client) ID',
    client_secret: 'Azure client secret',
    tenant_id: 'Azure tenant (directory) ID',
    subscription_id: 'Azure subscription ID',
    service_account_key: 'JSON key file content for GCP service account',
    project_id: 'GCP project ID',
    kubeconfig: 'Kubernetes configuration file content',
    context: 'Kubernetes context name'
  }
  return hints[field] || ''
}

const isSecretField = (field: string): boolean => {
  const secretFields = ['secret_access_key', 'session_token', 'client_secret', 'service_account_key', 'kubeconfig']
  return secretFields.includes(field)
}

const toggleSecretVisibility = (field: string) => {
  showSecrets.value[field] = !showSecrets.value[field]
}

const resetForm = () => {
  form.provider = ''
  form.name = ''
  form.credentials = {}
  form.testOnSave = true
  showSecrets.value = {}
  credentialForm.value?.resetValidation()
}

const validate = () => {
  return credentialForm.value?.validate()
}

// Watchers
watch(() => form.provider, (newProvider) => {
  if (newProvider && selectedProvider.value) {
    form.credentials = {}
    // Initialize required credentials
    selectedProvider.value.required_credentials.forEach(field => {
      form.credentials[field] = ''
    })
    // Initialize optional credentials
    selectedProvider.value.optional_credentials?.forEach(field => {
      form.credentials[field] = ''
    })
  }
})

watch(form, (newForm) => {
  emit('update:modelValue', { ...newForm })
}, { deep: true })

watch(formValid, (valid) => {
  emit('update:valid', valid)
})

// Initialize form with editing credential
watch(() => props.editingCredential, (credential) => {
  if (credential) {
    form.provider = credential.provider
    form.name = credential.name
    form.credentials = {} // Don't load existing credentials for security
    form.testOnSave = false
  }
}, { immediate: true })

// Expose methods
defineExpose({
  resetForm,
  validate
})
</script>

<style scoped lang="scss">
.v-text-field {
  :deep(.v-field__append-inner) {
    padding-top: 0;
  }
}
</style>