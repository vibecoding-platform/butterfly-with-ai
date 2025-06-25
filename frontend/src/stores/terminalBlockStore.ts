import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export interface BlockState {
  sessionId: string
  isBlocked: boolean
  reason: string
  message: string
  alertMessage: string
  detectedKeywords: string[]
  blockedAt: number
  unlockKey: string
}

export interface BlockAlert {
  id: string
  sessionId: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  message: string
  alertMessage: string
  detectedKeywords: string[]
  timestamp: number
  isActive: boolean
}

export const useTerminalBlockStore = defineStore('terminalBlock', () => {
  // ブロック状態管理
  const blockedSessions = ref<Map<string, BlockState>>(new Map())
  const activeAlerts = ref<Map<string, BlockAlert>>(new Map())

  // キー入力監視状態
  const isListeningForUnlock = ref<Map<string, boolean>>(new Map())
  const keySequence = ref<Map<string, string[]>>(new Map())

  // Getters
  const isSessionBlocked = computed(() => (sessionId: string) => {
    return blockedSessions.value.has(sessionId)
  })

  const getBlockState = computed(() => (sessionId: string) => {
    return blockedSessions.value.get(sessionId) || null
  })

  const getActiveAlert = computed(() => (sessionId: string) => {
    return activeAlerts.value.get(sessionId) || null
  })

  const hasActiveAlerts = computed(() => {
    return activeAlerts.value.size > 0
  })

  const criticalAlertsCount = computed(() => {
    let count = 0
    for (const alert of activeAlerts.value.values()) {
      if (alert.severity === 'critical' && alert.isActive) {
        count++
      }
    }
    return count
  })

  // Actions
  const blockSession = (blockData: {
    session_id: string
    severity: string
    message: string
    detected_keywords: string[]
    alert_message: string
    unlock_key?: string
    timestamp: number
  }) => {
    const blockState: BlockState = {
      sessionId: blockData.session_id,
      isBlocked: true,
      reason: blockData.severity,
      message: blockData.message,
      alertMessage: blockData.alert_message,
      detectedKeywords: blockData.detected_keywords,
      blockedAt: blockData.timestamp,
      unlockKey: blockData.unlock_key || 'ctrl_d',
    }

    blockedSessions.value.set(blockData.session_id, blockState)

    // アラートを作成
    const alertId = `alert_${blockData.session_id}_${Date.now()}`
    const alert: BlockAlert = {
      id: alertId,
      sessionId: blockData.session_id,
      severity: blockData.severity as any,
      message: blockData.message,
      alertMessage: blockData.alert_message,
      detectedKeywords: blockData.detected_keywords,
      timestamp: blockData.timestamp,
      isActive: true,
    }

    activeAlerts.value.set(alertId, alert)

    // キー入力監視を開始
    startUnlockListening(blockData.session_id)

    console.log(`Session ${blockData.session_id} blocked:`, blockState)
  }

  const unblockSession = (sessionId: string) => {
    blockedSessions.value.delete(sessionId)

    // 関連するアラートを非アクティブ化
    for (const [alertId, alert] of activeAlerts.value.entries()) {
      if (alert.sessionId === sessionId) {
        alert.isActive = false
        // 5秒後にアラートを削除
        setTimeout(() => {
          activeAlerts.value.delete(alertId)
        }, 5000)
      }
    }

    // キー入力監視を停止
    stopUnlockListening(sessionId)

    console.log(`Session ${sessionId} unblocked`)
  }

  const startUnlockListening = (sessionId: string) => {
    isListeningForUnlock.value.set(sessionId, true)
    keySequence.value.set(sessionId, [])

    console.log(`Started unlock listening for session ${sessionId}`)
  }

  const stopUnlockListening = (sessionId: string) => {
    isListeningForUnlock.value.delete(sessionId)
    keySequence.value.delete(sessionId)

    console.log(`Stopped unlock listening for session ${sessionId}`)
  }

  const handleKeyPress = (sessionId: string, key: string, ctrlKey: boolean): boolean => {
    if (!isListeningForUnlock.value.get(sessionId)) {
      return false
    }

    const blockState = blockedSessions.value.get(sessionId)
    if (!blockState) {
      return false
    }

    // Ctrl+D の検出
    if (ctrlKey && key.toLowerCase() === 'd') {
      console.log(`Ctrl+D detected for session ${sessionId}`)
      return true // ブロック解除をトリガー
    }

    return false
  }

  const dismissAlert = (alertId: string) => {
    const alert = activeAlerts.value.get(alertId)
    if (alert) {
      alert.isActive = false
      setTimeout(() => {
        activeAlerts.value.delete(alertId)
      }, 1000)
    }
  }

  const clearAllAlerts = () => {
    activeAlerts.value.clear()
  }

  const getSessionStatistics = (sessionId: string) => {
    const alerts = Array.from(activeAlerts.value.values()).filter(
      (alert) => alert.sessionId === sessionId
    )

    return {
      totalAlerts: alerts.length,
      criticalCount: alerts.filter((a) => a.severity === 'critical').length,
      highCount: alerts.filter((a) => a.severity === 'high').length,
      mediumCount: alerts.filter((a) => a.severity === 'medium').length,
      lastAlert: alerts.length > 0 ? Math.max(...alerts.map((a) => a.timestamp)) : null,
    }
  }

  const getAllBlockedSessions = () => {
    return Array.from(blockedSessions.value.keys())
  }

  const forceUnblockSession = (sessionId: string) => {
    // 管理者による強制ブロック解除
    unblockSession(sessionId)
    console.log(`Force unblocked session ${sessionId}`)
  }

  return {
    // State
    blockedSessions,
    activeAlerts,
    isListeningForUnlock,
    keySequence,

    // Getters
    isSessionBlocked,
    getBlockState,
    getActiveAlert,
    hasActiveAlerts,
    criticalAlertsCount,

    // Actions
    blockSession,
    unblockSession,
    startUnlockListening,
    stopUnlockListening,
    handleKeyPress,
    dismissAlert,
    clearAllAlerts,
    getSessionStatistics,
    getAllBlockedSessions,
    forceUnblockSession,
  }
})
