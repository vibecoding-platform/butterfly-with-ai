/**
 * AetherTerminal統一ストア
 * 
 * WebSocket通信とセッション管理を単純化
 * レガシーコードを削除し、クリーンなアーキテクチャで再構築
 */

import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { io, type Socket } from 'socket.io-client'

// 型定義
interface ConnectionState {
  isConnected: boolean
  isConnecting: boolean
  error?: string
  lastConnected?: Date
}

interface TerminalSession {
  id: string
  type: 'tab' | 'pane'
  terminalId: string
  isActive: boolean
  createdAt: Date
}

interface OutputCallback {
  sessionId: string
  callback: (data: string) => void
}

export const useAetherTerminalStore = defineStore('aetherTerminal', () => {
  // 接続状態
  const connectionState = reactive<ConnectionState>({
    isConnected: false,
    isConnecting: false
  })

  // WebSocket
  const socket = ref<Socket | null>(null)

  // セッション管理
  const sessions = ref<Map<string, TerminalSession>>(new Map())

  // 出力コールバック管理（シンプルな1対1マッピング）
  const outputCallbacks = ref<Map<string, (data: string) => void>>(new Map())

  // 接続管理
  const connect = async (): Promise<boolean> => {
    if (connectionState.isConnected || connectionState.isConnecting) {
      return connectionState.isConnected
    }

    console.log('🔌 AETHER_TERMINAL: Connecting to socket...')
    connectionState.isConnecting = true
    connectionState.error = undefined

    try {
      // Socket.IO接続を作成
      socket.value = io('ws://localhost:57575', {
        transports: ['websocket', 'polling'],
        timeout: 10000,
        forceNew: true
      })

      // 接続イベントのセットアップ
      setupSocketEvents()

      // 接続完了を待機
      return new Promise((resolve) => {
        const timeout = setTimeout(() => {
          connectionState.isConnecting = false
          connectionState.error = 'Connection timeout'
          resolve(false)
        }, 10000)

        socket.value?.on('connect', () => {
          clearTimeout(timeout)
          connectionState.isConnected = true
          connectionState.isConnecting = false
          connectionState.lastConnected = new Date()
          console.log('✅ AETHER_TERMINAL: Connected successfully')
          resolve(true)
        })

        socket.value?.on('connect_error', (error) => {
          clearTimeout(timeout)
          connectionState.isConnecting = false
          connectionState.error = error.message
          console.error('❌ AETHER_TERMINAL: Connection error:', error)
          resolve(false)
        })
      })
    } catch (error) {
      connectionState.isConnecting = false
      connectionState.error = error instanceof Error ? error.message : 'Unknown error'
      console.error('❌ AETHER_TERMINAL: Failed to connect:', error)
      return false
    }
  }

  // WebSocketイベントセットアップ（最小限）
  const setupSocketEvents = () => {
    if (!socket.value) return

    // 切断イベント
    socket.value.on('disconnect', (reason) => {
      connectionState.isConnected = false
      connectionState.error = reason
      console.log('🔌 AETHER_TERMINAL: Disconnected:', reason)
    })

    // ターミナル出力イベント（統一）
    socket.value.on('terminal_output', (data: any) => {
      if (data?.session && data?.data) {
        const callback = outputCallbacks.value.get(data.session)
        if (callback) {
          callback(data.data)
        }
      }
    })

    // セッション作成イベント
    socket.value.on('session_created', (data: any) => {
      if (data?.session_id) {
        console.log('✅ AETHER_TERMINAL: Session created:', data.session_id)
        // セッション管理は各コンポーネントが個別に処理
      }
    })
  }

  // セッション管理
  const requestSession = async (
    terminalId: string, 
    mode: 'tab' | 'pane', 
    subType: string = 'pure'
  ): Promise<string | null> => {
    if (!socket.value?.connected) {
      console.error('❌ AETHER_TERMINAL: Cannot request session - no connection')
      return null
    }

    const sessionId = `aether_${mode}_${terminalId}_${Date.now()}`
    
    console.log('🔄 AETHER_TERMINAL: Requesting session:', sessionId)

    return new Promise((resolve) => {
      const handleSessionCreated = (data: any) => {
        const targetId = mode === 'pane' ? data.pane_id : data.tab_id
        if (data.session_id && targetId === terminalId) {
          // セッション登録
          sessions.value.set(data.session_id, {
            id: data.session_id,
            type: mode,
            terminalId,
            isActive: true,
            createdAt: new Date()
          })

          socket.value?.off('session_created', handleSessionCreated)
          resolve(data.session_id)
        }
      }

      socket.value?.on('session_created', handleSessionCreated)
      socket.value?.emit('request_terminal_session', {
        session_id: sessionId,
        tab_type: 'terminal',
        tab_sub_type: subType,
        [mode === 'pane' ? 'pane_id' : 'tab_id']: terminalId
      })

      // タイムアウト処理
      setTimeout(() => {
        socket.value?.off('session_created', handleSessionCreated)
        resolve(null)
      }, 5000)
    })
  }

  // 入力送信（統一）
  const sendInput = (sessionId: string, data: string) => {
    if (!socket.value?.connected) {
      console.warn('⚠️ AETHER_TERMINAL: Cannot send input - no connection')
      return
    }

    socket.value.emit('terminal_input', {
      session: sessionId,
      data
    })
  }

  // 出力コールバック管理（シンプル）
  const registerOutputCallback = (sessionId: string, callback: (data: string) => void) => {
    outputCallbacks.value.set(sessionId, callback)
    console.log('📺 AETHER_TERMINAL: Registered output callback for session:', sessionId)
  }

  const unregisterOutputCallback = (sessionId: string) => {
    outputCallbacks.value.delete(sessionId)
    console.log('🗑️ AETHER_TERMINAL: Unregistered output callback for session:', sessionId)
  }

  // セッション終了
  const closeSession = (sessionId: string) => {
    sessions.value.delete(sessionId)
    unregisterOutputCallback(sessionId)
    console.log('🗑️ AETHER_TERMINAL: Closed session:', sessionId)
  }

  // 切断
  const disconnect = () => {
    if (socket.value) {
      socket.value.disconnect()
      socket.value = null
    }
    connectionState.isConnected = false
    sessions.value.clear()
    outputCallbacks.value.clear()
    console.log('🔌 AETHER_TERMINAL: Disconnected and cleaned up')
  }

  return {
    // 状態
    connectionState,
    socket,
    sessions,

    // 接続管理
    connect,
    disconnect,

    // セッション管理
    requestSession,
    closeSession,

    // 通信
    sendInput,
    registerOutputCallback,
    unregisterOutputCallback
  }
})