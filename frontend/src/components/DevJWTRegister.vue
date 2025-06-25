<template>
  <div class="dev-jwt-register">
    <div class="register-header">
      <h3>🔧 Development JWT Registration</h3>
      <div class="dev-notice">
        <small>⚠️ This is for development only and should be disabled in production</small>
      </div>
    </div>

    <div class="user-options">
      <div class="user-type-buttons">
        <button
          @click="registerUser('general')"
          class="register-btn general-user"
          :disabled="isRegistering"
        >
          👤 Register as General User
        </button>

        <button
          @click="registerUser('supervisor')"
          class="register-btn supervisor-user"
          :disabled="isRegistering"
        >
          👑 Register as Supervisor
        </button>
      </div>

      <div class="quick-actions">
        <button @click="clearAuth" class="clear-btn">🗑️ Clear Authentication</button>
        <button @click="showCurrentAuth" class="show-auth-btn">🔍 Show Current Auth</button>
      </div>
    </div>

    <!-- Current Authentication Status -->
    <div v-if="currentAuth" class="current-auth">
      <h4>Current Authentication</h4>
      <div class="auth-info">
        <div class="auth-field">
          <span class="label">Email:</span>
          <span class="value">{{ currentAuth.email || 'Not set' }}</span>
        </div>
        <div class="auth-field">
          <span class="label">User Type:</span>
          <span class="value" :class="{ supervisor: currentAuth.isSupervisor }">
            {{ currentAuth.isSupervisor ? 'Supervisor' : 'General User' }}
          </span>
        </div>
        <div class="auth-field">
          <span class="label">Roles:</span>
          <span class="value">{{ currentAuth.roles?.join(', ') || 'None' }}</span>
        </div>
        <div class="auth-field">
          <span class="label">Token Expires:</span>
          <span class="value">{{ formatExpiry(currentAuth.exp) }}</span>
        </div>
      </div>
    </div>

    <!-- Registration Success Message -->
    <div v-if="registrationMessage" class="registration-message" :class="messageType">
      {{ registrationMessage }}
    </div>

    <!-- Generated JWT Display -->
    <div v-if="generatedJWT" class="jwt-display">
      <h4>Generated JWT Token</h4>
      <div class="jwt-token">
        <textarea
          v-model="generatedJWT"
          readonly
          rows="8"
          class="jwt-textarea"
          @click="selectAll"
        ></textarea>
        <button @click="copyToClipboard" class="copy-btn">📋 Copy Token</button>
      </div>
      <div class="jwt-info">
        <small>This token has been automatically stored in localStorage as 'jwt_token'</small>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref, onMounted } from 'vue'
  import { getCurrentUser, getJWTToken, decodeJWT } from '../utils/auth'

  const isRegistering = ref(false)
  const registrationMessage = ref('')
  const messageType = ref<'success' | 'error'>('success')
  const generatedJWT = ref('')
  const currentAuth = ref<any>(null)

  // Development JWT creation function
  const createDevelopmentJWT = (userType: 'general' | 'supervisor') => {
    const header = {
      alg: 'HS256',
      typ: 'JWT',
    }

    const now = Math.floor(Date.now() / 1000)
    const expiry = now + 24 * 60 * 60 // 24 hours

    const payload =
      userType === 'supervisor'
        ? {
            sub: 'dev-supervisor-001',
            email: 'supervisor@aetherterm.dev',
            name: 'Development Supervisor',
            isSupervisor: true,
            roles: ['supervisor', 'admin'],
            permissions: ['terminal:supervise', 'admin:all'],
            iat: now,
            exp: expiry,
            iss: 'aetherterm-dev',
          }
        : {
            sub: 'dev-user-001',
            email: 'user@aetherterm.dev',
            name: 'Development User',
            isSupervisor: false,
            roles: ['user'],
            permissions: ['terminal:access'],
            iat: now,
            exp: expiry,
            iss: 'aetherterm-dev',
          }

    // Simple base64url encoding (for development only)
    const base64UrlEncode = (data: any) => {
      return btoa(JSON.stringify(data)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
    }

    const encodedHeader = base64UrlEncode(header)
    const encodedPayload = base64UrlEncode(payload)

    // For development, we'll use a dummy signature
    const signature = 'dev-signature-not-verified'

    return `${encodedHeader}.${encodedPayload}.${signature}`
  }

  const registerUser = async (userType: 'general' | 'supervisor') => {
    isRegistering.value = true
    registrationMessage.value = ''

    try {
      // Generate JWT token
      const jwt = createDevelopmentJWT(userType)

      // Store in localStorage
      localStorage.setItem('jwt_token', jwt)

      // Store generated JWT for display
      generatedJWT.value = jwt

      // Update current auth display
      loadCurrentAuth()

      registrationMessage.value = `Successfully registered as ${userType === 'supervisor' ? 'Supervisor' : 'General User'}! Token stored in localStorage.`
      messageType.value = 'success'

      // Refresh the page to update authentication state
      setTimeout(() => {
        window.location.reload()
      }, 2000)
    } catch (error) {
      console.error('Registration failed:', error)
      registrationMessage.value = 'Registration failed. Please try again.'
      messageType.value = 'error'
    } finally {
      isRegistering.value = false
    }
  }

  const clearAuth = () => {
    localStorage.removeItem('jwt_token')
    sessionStorage.removeItem('jwt_token')
    localStorage.removeItem('auth_token')
    sessionStorage.removeItem('auth_token')

    // Clear cookies
    document.cookie = 'jwt_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
    document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'

    generatedJWT.value = ''
    currentAuth.value = null
    registrationMessage.value = 'Authentication cleared. Page will refresh...'
    messageType.value = 'success'

    setTimeout(() => {
      window.location.reload()
    }, 1500)
  }

  const showCurrentAuth = () => {
    loadCurrentAuth()
  }

  const loadCurrentAuth = () => {
    const token = getJWTToken()
    if (token) {
      const payload = decodeJWT(token)
      if (payload) {
        currentAuth.value = payload
      }
    } else {
      currentAuth.value = null
    }
  }

  const formatExpiry = (exp?: number) => {
    if (!exp) return 'Not set'
    const date = new Date(exp * 1000)
    return date.toLocaleString()
  }

  const selectAll = (event: Event) => {
    const textarea = event.target as HTMLTextAreaElement
    textarea.select()
  }

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(generatedJWT.value)
      registrationMessage.value = 'JWT token copied to clipboard!'
      messageType.value = 'success'
      setTimeout(() => {
        registrationMessage.value = ''
      }, 3000)
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
      registrationMessage.value = 'Failed to copy to clipboard'
      messageType.value = 'error'
    }
  }

  onMounted(() => {
    loadCurrentAuth()
  })
</script>

<style scoped>
  .dev-jwt-register {
    background-color: #2d2d2d;
    color: #ffffff;
    padding: 20px;
    border-radius: 8px;
    border: 2px solid #ff9800;
    margin-bottom: 20px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  .register-header {
    margin-bottom: 20px;
    text-align: center;
  }

  .register-header h3 {
    margin: 0 0 10px 0;
    color: #ff9800;
    font-size: 18px;
  }

  .dev-notice {
    background-color: rgba(255, 152, 0, 0.1);
    padding: 8px 12px;
    border-radius: 4px;
    border: 1px solid #ff9800;
  }

  .dev-notice small {
    color: #ffcc80;
    font-size: 12px;
  }

  .user-options {
    display: flex;
    flex-direction: column;
    gap: 15px;
    margin-bottom: 20px;
  }

  .user-type-buttons {
    display: flex;
    gap: 15px;
    justify-content: center;
    flex-wrap: wrap;
  }

  .register-btn {
    padding: 12px 24px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.2s;
    min-width: 200px;
  }

  .general-user {
    background-color: #2196f3;
    color: white;
  }

  .general-user:hover:not(:disabled) {
    background-color: #1976d2;
    transform: translateY(-1px);
  }

  .supervisor-user {
    background-color: #4caf50;
    color: white;
  }

  .supervisor-user:hover:not(:disabled) {
    background-color: #45a049;
    transform: translateY(-1px);
  }

  .register-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .quick-actions {
    display: flex;
    gap: 10px;
    justify-content: center;
    flex-wrap: wrap;
  }

  .clear-btn,
  .show-auth-btn {
    padding: 8px 16px;
    border: 1px solid #666;
    border-radius: 4px;
    background-color: #444;
    color: white;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s;
  }

  .clear-btn:hover {
    background-color: #f44336;
    border-color: #f44336;
  }

  .show-auth-btn:hover {
    background-color: #666;
    border-color: #888;
  }

  .current-auth {
    background-color: #1e1e1e;
    padding: 15px;
    border-radius: 6px;
    border: 1px solid #444;
    margin-bottom: 15px;
  }

  .current-auth h4 {
    margin: 0 0 15px 0;
    color: #4caf50;
    font-size: 16px;
  }

  .auth-info {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .auth-field {
    display: flex;
    justify-content: space-between;
    padding: 8px;
    background-color: #333;
    border-radius: 4px;
  }

  .auth-field .label {
    color: #ccc;
    font-size: 12px;
    font-weight: bold;
  }

  .auth-field .value {
    color: #fff;
    font-size: 12px;
  }

  .auth-field .value.supervisor {
    color: #4caf50;
    font-weight: bold;
  }

  .registration-message {
    padding: 12px;
    border-radius: 4px;
    margin-bottom: 15px;
    font-size: 14px;
    font-weight: bold;
    text-align: center;
  }

  .registration-message.success {
    background-color: rgba(76, 175, 80, 0.2);
    border: 1px solid #4caf50;
    color: #81c784;
  }

  .registration-message.error {
    background-color: rgba(244, 67, 54, 0.2);
    border: 1px solid #f44336;
    color: #ef5350;
  }

  .jwt-display {
    background-color: #1e1e1e;
    padding: 15px;
    border-radius: 6px;
    border: 1px solid #444;
  }

  .jwt-display h4 {
    margin: 0 0 15px 0;
    color: #ff9800;
    font-size: 16px;
  }

  .jwt-token {
    position: relative;
  }

  .jwt-textarea {
    width: 100%;
    background-color: #333;
    color: #fff;
    border: 1px solid #666;
    border-radius: 4px;
    padding: 10px;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    resize: vertical;
    box-sizing: border-box;
  }

  .jwt-textarea:focus {
    outline: none;
    border-color: #4caf50;
  }

  .copy-btn {
    margin-top: 10px;
    padding: 8px 16px;
    background-color: #4caf50;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s;
  }

  .copy-btn:hover {
    background-color: #45a049;
  }

  .jwt-info {
    margin-top: 10px;
    padding: 8px;
    background-color: rgba(76, 175, 80, 0.1);
    border-radius: 4px;
    border: 1px solid #4caf50;
  }

  .jwt-info small {
    color: #81c784;
    font-size: 12px;
  }

  @media (max-width: 768px) {
    .user-type-buttons {
      flex-direction: column;
      align-items: center;
    }

    .auth-info {
      grid-template-columns: 1fr;
    }
  }
</style>
