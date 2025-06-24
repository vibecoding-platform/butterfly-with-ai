<template>
  <div class="error-screen">
    <div class="error-container">
      <!-- エラーアイコンとタイトル -->
      <div class="error-header">
        <div class="error-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" stroke="#ef4444" stroke-width="2"/>
            <line x1="15" y1="9" x2="9" y2="15" stroke="#ef4444" stroke-width="2"/>
            <line x1="9" y1="9" x2="15" y2="15" stroke="#ef4444" stroke-width="2"/>
          </svg>
        </div>
        <h1 class="error-title">{{ errorTitle }}</h1>
        <p class="error-message">{{ errorMessage }}</p>
      </div>

      <!-- エラー詳細情報 -->
      <div class="error-details" v-if="showDetails">
        <details class="error-details-toggle">
          <summary>エラー詳細</summary>
          <div class="error-details-content">
            <div class="error-info">
              <h3>エラータイプ</h3>
              <p class="error-type">{{ errorType }}</p>
            </div>
            
            <div class="error-info" v-if="errorCode">
              <h3>エラーコード</h3>
              <p class="error-code">{{ errorCode }}</p>
            </div>
            
            <div class="error-info" v-if="timestamp">
              <h3>発生時刻</h3>
              <p class="error-timestamp">{{ formatTimestamp(timestamp) }}</p>
            </div>
            
            <div class="error-info" v-if="serverUrl">
              <h3>接続先サーバー</h3>
              <p class="error-server">{{ serverUrl }}</p>
            </div>
            
            <div class="error-info" v-if="additionalInfo">
              <h3>追加情報</h3>
              <pre class="error-additional">{{ formatAdditionalInfo(additionalInfo) }}</pre>
            </div>
          </div>
        </details>
      </div>

      <!-- アクションボタン -->
      <div class="error-actions">
        <button 
          class="btn btn-primary" 
          @click="handleRetry"
          :disabled="retrying"
        >
          <span v-if="retrying" class="loading-spinner"></span>
          {{ retrying ? '再接続中...' : '再接続' }}
        </button>
        
        <button 
          class="btn btn-secondary" 
          @click="handleReload"
        >
          ページを再読み込み
        </button>
        
        <button 
          class="btn btn-outline" 
          @click="toggleDetails"
          v-if="!showDetails"
        >
          詳細を表示
        </button>
      </div>

      <!-- 接続状態インジケーター -->
      <div class="connection-status">
        <div class="status-indicator" :class="connectionStatusClass">
          <div class="status-dot"></div>
          <span class="status-text">{{ connectionStatusText }}</span>
        </div>
      </div>

      <!-- サポート情報 -->
      <div class="support-info">
        <p class="support-text">
          問題が解決しない場合は、システム管理者にお問い合わせください。
        </p>
        <div class="support-links">
          <a href="#" @click="copyErrorInfo" class="support-link">
            エラー情報をコピー
          </a>
          <span class="separator">|</span>
          <a href="#" @click="downloadLogs" class="support-link">
            ログをダウンロード
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface ErrorScreenProps {
  errorType: 'CONNECTION_ERROR' | 'SERVER_ERROR' | 'NETWORK_ERROR' | 'TIMEOUT_ERROR' | 'UNKNOWN_ERROR'
  errorMessage?: string
  errorCode?: string
  additionalInfo?: any
  serverUrl?: string
  timestamp?: Date
  showRetry?: boolean
  autoRetry?: boolean
  autoRetryInterval?: number
}

const props = withDefaults(defineProps<ErrorScreenProps>(), {
  errorMessage: 'AgentServerへの接続に失敗しました',
  showRetry: true,
  autoRetry: false,
  autoRetryInterval: 5000
})

const emit = defineEmits<{
  retry: []
  reload: []
  close: []
}>()

const showDetails = ref(false)
const retrying = ref(false)
const connectionStatus = ref<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected')
const autoRetryTimer = ref<number | null>(null)
const autoRetryCountdown = ref(0)

// Computed properties
const errorTitle = computed(() => {
  switch (props.errorType) {
    case 'CONNECTION_ERROR':
      return 'サーバー接続エラー'
    case 'SERVER_ERROR':
      return 'サーバーエラー'
    case 'NETWORK_ERROR':
      return 'ネットワークエラー'
    case 'TIMEOUT_ERROR':
      return '接続タイムアウト'
    default:
      return '不明なエラー'
  }
})

const connectionStatusClass = computed(() => {
  return {
    'status-disconnected': connectionStatus.value === 'disconnected',
    'status-connecting': connectionStatus.value === 'connecting',
    'status-connected': connectionStatus.value === 'connected',
    'status-error': connectionStatus.value === 'error'
  }
})

const connectionStatusText = computed(() => {
  switch (connectionStatus.value) {
    case 'disconnected':
      return '切断中'
    case 'connecting':
      return '接続中...'
    case 'connected':
      return '接続済み'
    case 'error':
      return 'エラー'
    default:
      return '不明'
  }
})

// Methods
const handleRetry = async () => {
  retrying.value = true
  connectionStatus.value = 'connecting'
  
  try {
    emit('retry')
    
    // Wait for retry operation (simulated)
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    connectionStatus.value = 'connected'
  } catch (error) {
    connectionStatus.value = 'error'
    console.error('Retry failed:', error)
  } finally {
    retrying.value = false
  }
}

const handleReload = () => {
  emit('reload')
  window.location.reload()
}

const toggleDetails = () => {
  showDetails.value = !showDetails.value
}

const formatTimestamp = (timestamp: Date) => {
  return timestamp.toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const formatAdditionalInfo = (info: any) => {
  if (typeof info === 'string') {
    return info
  }
  return JSON.stringify(info, null, 2)
}

const copyErrorInfo = async () => {
  const errorInfo = {
    type: props.errorType,
    message: props.errorMessage,
    code: props.errorCode,
    timestamp: props.timestamp?.toISOString(),
    server: props.serverUrl,
    additionalInfo: props.additionalInfo,
    userAgent: navigator.userAgent,
    url: window.location.href
  }
  
  try {
    await navigator.clipboard.writeText(JSON.stringify(errorInfo, null, 2))
    alert('エラー情報をクリップボードにコピーしました')
  } catch (error) {
    console.error('Failed to copy error info:', error)
    alert('エラー情報のコピーに失敗しました')
  }
}

const downloadLogs = () => {
  // Implementation would depend on logging system
  console.log('Downloading logs...')
  alert('ログダウンロード機能は実装中です')
}

const startAutoRetry = () => {
  if (!props.autoRetry || autoRetryTimer.value) return
  
  autoRetryCountdown.value = props.autoRetryInterval / 1000
  
  const countdown = setInterval(() => {
    autoRetryCountdown.value--
    if (autoRetryCountdown.value <= 0) {
      clearInterval(countdown)
      handleRetry()
    }
  }, 1000)
  
  autoRetryTimer.value = window.setTimeout(() => {
    clearInterval(countdown)
    if (!retrying.value) {
      handleRetry()
    }
  }, props.autoRetryInterval)
}

const stopAutoRetry = () => {
  if (autoRetryTimer.value) {
    window.clearTimeout(autoRetryTimer.value)
    autoRetryTimer.value = null
    autoRetryCountdown.value = 0
  }
}

// Lifecycle
onMounted(() => {
  connectionStatus.value = 'error'
  if (props.autoRetry) {
    startAutoRetry()
  }
})

onUnmounted(() => {
  stopAutoRetry()
})
</script>

<style scoped>
.error-screen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.error-container {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  max-width: 600px;
  width: 100%;
  padding: 40px;
  text-align: center;
}

.error-header {
  margin-bottom: 32px;
}

.error-icon {
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
}

.error-title {
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 16px 0;
}

.error-message {
  font-size: 1.125rem;
  color: #6b7280;
  margin: 0;
  line-height: 1.6;
}

.error-details {
  margin: 24px 0;
  text-align: left;
}

.error-details-toggle {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
}

.error-details-toggle summary {
  cursor: pointer;
  font-weight: 600;
  color: #374151;
  outline: none;
}

.error-details-content {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
}

.error-info {
  margin-bottom: 16px;
}

.error-info h3 {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
  margin: 0 0 4px 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.error-info p {
  margin: 0;
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  background: #f9fafb;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 0.875rem;
  color: #1f2937;
}

.error-additional {
  background: #f9fafb;
  padding: 12px;
  border-radius: 4px;
  font-size: 0.875rem;
  color: #1f2937;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 32px;
}

.btn {
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
  justify-content: center;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-secondary {
  background: #6b7280;
  color: white;
}

.btn-secondary:hover {
  background: #4b5563;
}

.btn-outline {
  background: transparent;
  color: #3b82f6;
  border: 1px solid #3b82f6;
}

.btn-outline:hover {
  background: #3b82f6;
  color: white;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.connection-status {
  margin-bottom: 24px;
}

.status-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transition: background-color 0.2s ease;
}

.status-text {
  font-size: 0.875rem;
  font-weight: 500;
}

.status-disconnected .status-dot {
  background: #ef4444;
}

.status-disconnected .status-text {
  color: #ef4444;
}

.status-connecting .status-dot {
  background: #f59e0b;
  animation: pulse 2s infinite;
}

.status-connecting .status-text {
  color: #f59e0b;
}

.status-connected .status-dot {
  background: #10b981;
}

.status-connected .status-text {
  color: #10b981;
}

.status-error .status-dot {
  background: #ef4444;
}

.status-error .status-text {
  color: #ef4444;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.support-info {
  border-top: 1px solid #e5e7eb;
  padding-top: 24px;
}

.support-text {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0 0 12px 0;
}

.support-links {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.support-link {
  color: #3b82f6;
  text-decoration: none;
  font-size: 0.875rem;
  cursor: pointer;
}

.support-link:hover {
  text-decoration: underline;
}

.separator {
  color: #d1d5db;
}

/* Responsive */
@media (max-width: 640px) {
  .error-container {
    padding: 24px;
    margin: 20px;
  }
  
  .error-title {
    font-size: 1.5rem;
  }
  
  .error-actions {
    flex-direction: column;
    align-items: stretch;
  }
  
  .btn {
    width: 100%;
  }
}
</style>