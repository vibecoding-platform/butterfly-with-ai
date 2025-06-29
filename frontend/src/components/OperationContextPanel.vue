<template>
  <div class="operation-context-panel">
    <!-- ヘッダー -->
    <div class="panel-header">
      <h3 class="panel-title">
        <v-icon>mdi-brain</v-icon>
        オペレーション コンテキスト
      </h3>
      <v-chip 
        :color="connectionStatusColor" 
        size="small"
        variant="elevated"
      >
        {{ connectionStatus }}
      </v-chip>
    </div>

    <!-- メインコンテンツ -->
    <v-card class="mt-3" variant="outlined">
      <v-card-text>
        <div v-if="!selectedTerminal" class="text-center text-grey">
          <v-icon size="48" class="mb-2">mdi-monitor-off</v-icon>
          <p>ターミナルを選択してください</p>
        </div>

        <div v-else-if="isLoading" class="text-center">
          <v-progress-circular indeterminate color="primary" class="mb-2"></v-progress-circular>
          <p>コンテキストを推定中...</p>
        </div>

        <div v-else-if="currentContext">
          <!-- 現在のオペレーション -->
          <div class="operation-info mb-4">
            <div class="d-flex align-center mb-2">
              <v-icon :color="operationTypeColor" class="mr-2">
                {{ operationTypeIcon }}
              </v-icon>
              <span class="text-h6">{{ operationTypeName }}</span>
              <v-chip 
                :color="stageColor"
                size="small"
                class="ml-2"
              >
                {{ stageName }}
              </v-chip>
            </div>
            
            <!-- 信頼度 -->
            <div class="confidence-bar mb-2">
              <div class="d-flex justify-space-between align-center mb-1">
                <span class="text-caption">信頼度</span>
                <span class="text-caption">{{ Math.round(currentContext.confidence * 100) }}%</span>
              </div>
              <v-progress-linear
                :model-value="currentContext.confidence * 100"
                :color="confidenceColor"
                height="4"
              ></v-progress-linear>
            </div>

            <!-- 進捗 -->
            <div class="progress-bar mb-3" v-if="currentContext.progress_percentage > 0">
              <div class="d-flex justify-space-between align-center mb-1">
                <span class="text-caption">進捗</span>
                <span class="text-caption">{{ Math.round(currentContext.progress_percentage * 100) }}%</span>
              </div>
              <v-progress-linear
                :model-value="currentContext.progress_percentage * 100"
                color="success"
                height="6"
              ></v-progress-linear>
            </div>
          </div>

          <!-- 次の推奨コマンド -->
          <div v-if="nextCommands.length > 0" class="next-commands mb-4">
            <h4 class="text-subtitle-1 mb-2">
              <v-icon class="mr-1">mdi-arrow-right-circle</v-icon>
              次の推奨コマンド
            </h4>
            <v-chip-group>
              <v-chip
                v-for="(command, index) in nextCommands"
                :key="index"
                size="small"
                @click="copyCommand(command)"
                :prepend-icon="'mdi-content-copy'"
              >
                {{ command }}
              </v-chip>
            </v-chip-group>
          </div>

          <!-- 推奨事項 -->
          <div v-if="recommendations.length > 0" class="recommendations mb-4">
            <h4 class="text-subtitle-1 mb-2">
              <v-icon class="mr-1">mdi-lightbulb</v-icon>
              推奨事項
            </h4>
            <v-list dense>
              <v-list-item 
                v-for="(rec, index) in recommendations"
                :key="index"
                class="px-0"
              >
                <v-list-item-title class="text-caption">
                  <v-icon size="12" class="mr-1">mdi-chevron-right</v-icon>
                  {{ rec }}
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </div>

          <!-- 警告 -->
          <div v-if="warnings.length > 0" class="warnings mb-4">
            <h4 class="text-subtitle-1 mb-2 text-warning">
              <v-icon class="mr-1">mdi-alert</v-icon>
              注意事項
            </h4>
            <v-alert
              v-for="(warning, index) in warnings"
              :key="index"
              type="warning"
              variant="tonal"
              density="compact"
              class="mb-1"
            >
              {{ warning }}
            </v-alert>
          </div>
        </div>

        <div v-else class="text-center text-grey">
          <v-icon size="48" class="mb-2">mdi-help-circle</v-icon>
          <p>コンテキストを推定できませんでした</p>
          <v-btn 
            size="small" 
            @click="refreshContext"
            :loading="isLoading"
          >
            再試行
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <!-- コマンド履歴 -->
    <v-card class="mt-3" variant="outlined" v-if="currentContext?.command_sequence?.length">
      <v-card-title class="text-subtitle-1">
        <v-icon class="mr-1">mdi-history</v-icon>
        コマンド履歴
      </v-card-title>
      <v-card-text>
        <div class="command-history">
          <div 
            v-for="(command, index) in currentContext.command_sequence.slice(-5)"
            :key="index"
            class="command-item"
          >
            <v-chip 
              size="small" 
              variant="outlined"
              @click="copyCommand(command)"
            >
              <v-icon size="12" class="mr-1">mdi-console</v-icon>
              {{ command }}
            </v-chip>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- アクションボタン -->
    <div class="action-buttons mt-3">
      <v-btn
        size="small"
        @click="refreshContext"
        :loading="isLoading"
        prepend-icon="mdi-refresh"
      >
        更新
      </v-btn>
      
      <v-btn
        size="small"
        @click="showAnalytics = true"
        prepend-icon="mdi-chart-line"
        class="ml-2"
      >
        分析
      </v-btn>
    </div>

    <!-- 分析ダイアログ -->
    <v-dialog v-model="showAnalytics" width="600">
      <v-card>
        <v-card-title>オペレーション分析</v-card-title>
        <v-card-text>
          <!-- 分析コンテンツ -->
          <div v-if="analytics" class="analytics-content">
            <v-row>
              <v-col cols="6">
                <v-card variant="outlined">
                  <v-card-text class="text-center">
                    <div class="text-h4">{{ analytics.total_operations }}</div>
                    <div class="text-caption">総オペレーション数</div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="6">
                <v-card variant="outlined">
                  <v-card-text class="text-center">
                    <div class="text-h4">{{ Math.round(analytics.success_rate * 100) }}%</div>
                    <div class="text-caption">成功率</div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showAnalytics = false">閉じる</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- スナックバー -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color">
      {{ snackbar.message }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAetherTerminalServiceStore } from '../stores/aetherTerminalServiceStore'

const terminalStore = useAetherTerminalServiceStore()

// Reactive data
const selectedTerminal = ref(null)
const currentContext = ref(null)
const nextCommands = ref([])
const recommendations = ref([])
const warnings = ref([])
const isLoading = ref(false)
const connectionStatus = ref('未接続')
const showAnalytics = ref(false)
const analytics = ref(null)

const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})

// Computed properties
const connectionStatusColor = computed(() => {
  switch (connectionStatus.value) {
    case '接続済み': return 'success'
    case '接続中': return 'warning' 
    case '未接続': return 'error'
    default: return 'grey'
  }
})

const operationTypeName = computed(() => {
  if (!currentContext.value) return ''
  
  const typeNames = {
    'deployment': 'デプロイ',
    'debugging': 'デバッグ',
    'development': '開発',
    'testing': 'テスト',
    'maintenance': 'メンテナンス',
    'investigation': '調査',
    'setup': 'セットアップ',
    'unknown': '不明'
  }
  
  return typeNames[currentContext.value.operation_type] || currentContext.value.operation_type
})

const operationTypeIcon = computed(() => {
  if (!currentContext.value) return 'mdi-help'
  
  const typeIcons = {
    'deployment': 'mdi-rocket-launch',
    'debugging': 'mdi-bug',
    'development': 'mdi-code-braces',
    'testing': 'mdi-test-tube',
    'maintenance': 'mdi-wrench',
    'investigation': 'mdi-magnify',
    'setup': 'mdi-cog',
    'unknown': 'mdi-help'
  }
  
  return typeIcons[currentContext.value.operation_type] || 'mdi-help'
})

const operationTypeColor = computed(() => {
  if (!currentContext.value) return 'grey'
  
  const typeColors = {
    'deployment': 'orange',
    'debugging': 'red',
    'development': 'blue',
    'testing': 'green',
    'maintenance': 'purple',
    'investigation': 'indigo',
    'setup': 'teal',
    'unknown': 'grey'
  }
  
  return typeColors[currentContext.value.operation_type] || 'grey'
})

const stageName = computed(() => {
  if (!currentContext.value) return ''
  
  const stageNames = {
    'starting': '開始',
    'in_progress': '実行中',
    'validating': '検証中',
    'completing': '完了中',
    'completed': '完了',
    'failed': '失敗'
  }
  
  return stageNames[currentContext.value.stage] || currentContext.value.stage
})

const stageColor = computed(() => {
  if (!currentContext.value) return 'grey'
  
  const stageColors = {
    'starting': 'blue',
    'in_progress': 'orange',
    'validating': 'purple',
    'completing': 'green',
    'completed': 'success',
    'failed': 'error'
  }
  
  return stageColors[currentContext.value.stage] || 'grey'
})

const confidenceColor = computed(() => {
  if (!currentContext.value) return 'grey'
  
  const confidence = currentContext.value.confidence
  if (confidence >= 0.8) return 'success'
  if (confidence >= 0.6) return 'warning'
  return 'error'
})

// Methods
const setupWebSocketConnection = () => {
  if (!terminalStore.service || !terminalStore.service.socket) {
    console.warn('Socket.IO not available for context inference')
    return
  }

  const socket = terminalStore.service.socket

  // Context inference events
  socket.on('context_inference_result', (data) => {
    currentContext.value = data
    nextCommands.value = data.next_commands || []
    recommendations.value = data.recommendations || []
    warnings.value = data.warnings || []
    isLoading.value = false
  })

  socket.on('context_inference_error', (data) => {
    console.error('Context inference error:', data.error)
    showSnackbar(data.error, 'error')
    isLoading.value = false
  })

  socket.on('next_commands_prediction', (data) => {
    nextCommands.value = data.next_commands || []
  })

  socket.on('operation_analytics', (data) => {
    analytics.value = data
  })

  connectionStatus.value = '接続済み'
}

const refreshContext = async () => {
  if (!selectedTerminal.value || !terminalStore.service?.socket) return

  isLoading.value = true
  
  try {
    terminalStore.service.socket.emit('context_inference_subscribe', {
      terminal_id: selectedTerminal.value
    })
  } catch (error) {
    console.error('Failed to refresh context:', error)
    showSnackbar('コンテキスト更新に失敗しました', 'error')
    isLoading.value = false
  }
}

const copyCommand = async (command) => {
  try {
    await navigator.clipboard.writeText(command)
    showSnackbar('コマンドをコピーしました', 'success')
  } catch (error) {
    console.error('Failed to copy command:', error)
    showSnackbar('コピーに失敗しました', 'error')
  }
}

const showSnackbar = (message, color = 'success') => {
  snackbar.value = {
    show: true,
    message,
    color
  }
}

const loadAnalytics = () => {
  if (!selectedTerminal.value || !terminalStore.service?.socket) return
  
  terminalStore.service.socket.emit('get_operation_analytics', {
    terminal_id: selectedTerminal.value,
    days: 7
  })
}

// Watch for terminal selection changes
watch(() => terminalStore.selectedTerminalId, (newTerminalId) => {
  selectedTerminal.value = newTerminalId
  if (newTerminalId) {
    refreshContext()
  } else {
    currentContext.value = null
    nextCommands.value = []
    recommendations.value = []
    warnings.value = []
  }
})

watch(showAnalytics, (show) => {
  if (show) {
    loadAnalytics()
  }
})

// Lifecycle
onMounted(() => {
  setupWebSocketConnection()
  selectedTerminal.value = terminalStore.selectedTerminalId
  if (selectedTerminal.value) {
    refreshContext()
  }
})

onUnmounted(() => {
  if (terminalStore.service?.socket) {
    const socket = terminalStore.service.socket
    socket.off('context_inference_result')
    socket.off('context_inference_error')
    socket.off('next_commands_prediction')
    socket.off('operation_analytics')
  }
})
</script>

<style scoped>
.operation-context-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 1.1rem;
  font-weight: 500;
}

.confidence-bar, .progress-bar {
  margin-bottom: 8px;
}

.command-history {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.command-item {
  display: flex;
  align-items: center;
}

.action-buttons {
  display: flex;
  gap: 8px;
  margin-top: auto;
}

.analytics-content {
  padding: 16px 0;
}

.operation-info {
  border-left: 3px solid var(--v-theme-primary);
  padding-left: 12px;
}
</style>