<template>
  <v-dialog v-model="show" max-width="800px" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">{{ editingCredential ? 'mdi-pencil' : 'mdi-plus' }}</v-icon>
        {{ editingCredential ? 'Edit' : 'Add' }} Cloud Credentials
      </v-card-title>

      <v-card-text>
        <CredentialForm
          ref="credentialFormRef"
          v-model="formData"
          @update:valid="formValid = $event"
          :available-providers="availableProviders"
          :editing-credential="editingCredential"
        />
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          variant="text"
          @click="cancel"
          :disabled="saving"
        >
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          @click="save"
          :loading="saving"
          :disabled="!formValid"
        >
          {{ editingCredential ? 'Update' : 'Save' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import CredentialForm from './CredentialForm.vue'
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
}

// Props
interface Props {
  modelValue: boolean
  availableProviders: Provider[]
  editingCredential?: CloudCredential | null
  saving?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  editingCredential: null,
  saving: false
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'save': [formData: any]
  'cancel': []
}>()

// State
const credentialFormRef = ref()
const formValid = ref(false)
const formData = ref({
  provider: '',
  name: '',
  credentials: {},
  testOnSave: true
})

// Computed
const show = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Methods
const save = async () => {
  if (!credentialFormRef.value?.validate()) return
  
  emit('save', formData.value)
}

const cancel = () => {
  credentialFormRef.value?.resetForm()
  emit('cancel')
}

// Watchers
watch(show, (newShow) => {
  if (!newShow) {
    // Reset form when dialog closes
    setTimeout(() => {
      credentialFormRef.value?.resetForm()
      formData.value = {
        provider: '',
        name: '',
        credentials: {},
        testOnSave: true
      }
    }, 300) // Wait for dialog animation
  }
})
</script>