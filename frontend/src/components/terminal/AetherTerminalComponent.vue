<template>
  <div class="aether-terminal-container" @click="handleClick" ref="containerRef">
    <div 
      :id="terminalElementId"
      class="aether-terminal"
      ref="terminalRef"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, watch, nextTick } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { useAetherTerminalStore } from '../../stores/aetherTerminalStore'
import { useTerminalTabStore } from '../../stores/terminalTabStore'
import { useTerminalPaneStore } from '../../stores/terminalPaneStore'
import '@xterm/xterm/css/xterm.css'

interface Props {
  id: string // ターミナルのID（tabId または paneId）
  mode?: 'tab' | 'pane' // モード指定
  subType?: 'pure' | 'inventory' | 'agent' | 'main-agent'
}

interface Emits {
  (e: 'click'): void
  (e: 'terminal-initialized'): void
}

const props = withDefaults(defineProps<Props>(), {
  mode: 'pane',
  subType: 'pure'
})

const emit = defineEmits<Emits>()

// Component refs
const containerRef = ref<HTMLElement | null>(null)
const terminalRef = ref<HTMLElement | null>(null)
const terminal = ref<Terminal | null>(null)
const fitAddon = ref<FitAddon | null>(null)

// Store references（新しいクリーンなストア）
const aetherStore = useAetherTerminalStore()
const tabStore = useTerminalTabStore()
const paneStore = useTerminalPaneStore()

// State
const sessionId = ref<string | null>(null)
const isInitialized = ref(false)

// Computed
const terminalElementId = computed(() => `aether-${props.mode}-${props.id}`)

// セッション管理（統一）
const getCurrentSession = () => {
  return props.mode === 'pane' 
    ? paneStore.getPaneSession(props.id)
    : tabStore.getTabSession(props.id)
}

const setCurrentSession = (newSessionId: string) => {
  if (props.mode === 'pane') {
    paneStore.setPaneSession(props.id, newSessionId)
  } else {
    tabStore.setTabSession(props.id, newSessionId)
  }
  sessionId.value = newSessionId
}

// ターミナル初期化（シンプル化）
const initializeTerminal = async () => {
  console.log(`🎬 AETHER_TERMINAL: Initializing ${props.mode}:`, props.id)
  
  await nextTick()
  
  if (!terminalRef.value) {
    console.error('❌ AETHER_TERMINAL: Terminal ref not found')
    return
  }

  // xterm.js作成
  terminal.value = new Terminal({
    cursorBlink: true,
    theme: {
      background: '#1e1e1e',
      foreground: '#d4d4d4',
      cursor: '#ffffff'
    },
    fontSize: 14,
    fontFamily: '"Cascadia Code", "Fira Code", monospace',
    rows: 30,
    cols: 120,
    scrollback: 1000
  })

  // Fit addon
  fitAddon.value = new FitAddon()
  terminal.value.loadAddon(fitAddon.value)

  // ターミナルをDOMに追加
  terminal.value.open(terminalRef.value)
  
  // サイズ調整
  setTimeout(() => fitAddon.value?.fit(), 100)

  // 入力処理セットアップ
  setupInput()

  // セッション要求
  await requestSession()

  isInitialized.value = true
  emit('terminal-initialized')
  
  console.log(`✅ AETHER_TERMINAL: Initialized ${props.mode}:`, props.id)
}

// 入力処理（シンプル化）
const setupInput = () => {
  if (!terminal.value) return

  terminal.value.onData((data) => {
    if (sessionId.value) {
      aetherStore.sendInput(sessionId.value, data)
    } else {
      console.warn(`⚠️ AETHER_TERMINAL: No session for ${props.mode}:`, props.id)
    }
  })
}

// セッション要求（統一）
const requestSession = async () => {
  // 既存セッションをチェック
  const existingSession = getCurrentSession()
  if (existingSession) {
    console.log(`📋 AETHER_TERMINAL: Using existing session for ${props.mode}:`, props.id)
    sessionId.value = existingSession
    setupOutput()
    return
  }

  // 新しいセッションを要求
  console.log(`🔄 AETHER_TERMINAL: Requesting new session for ${props.mode}:`, props.id)
  
  const newSessionId = await aetherStore.requestSession(props.id, props.mode, props.subType)
  
  if (newSessionId) {
    setCurrentSession(newSessionId)
    setupOutput()
    console.log(`✅ AETHER_TERMINAL: Session created for ${props.mode}:`, props.id, newSessionId)
  } else {
    console.error(`❌ AETHER_TERMINAL: Failed to create session for ${props.mode}:`, props.id)
  }
}

// 出力処理（シンプル化）
const setupOutput = () => {
  if (!sessionId.value || !terminal.value) return

  const outputCallback = (data: string) => {
    terminal.value?.write(data)
  }

  aetherStore.registerOutputCallback(sessionId.value, outputCallback)
  console.log(`📺 AETHER_TERMINAL: Output setup for ${props.mode}:`, props.id)
}

// クリック処理
const handleClick = () => {
  emit('click')
  terminal.value?.focus()
}

// 接続状態監視
watch(() => aetherStore.connectionState.isConnected, (connected) => {
  if (connected && !sessionId.value) {
    console.log(`🔌 AETHER_TERMINAL: Connection restored, requesting session for ${props.mode}:`, props.id)
    requestSession()
  }
})

// ライフサイクル
onMounted(async () => {
  console.log(`🎬 AETHER_TERMINAL: Mounted ${props.mode}:`, props.id)
  
  // 接続確保
  if (!aetherStore.connectionState.isConnected) {
    await aetherStore.connect()
  }
  
  initializeTerminal()
})

onBeforeUnmount(() => {
  console.log(`🗑️ AETHER_TERMINAL: Unmounting ${props.mode}:`, props.id)
  
  // クリーンアップ
  if (sessionId.value) {
    aetherStore.unregisterOutputCallback(sessionId.value)
  }
  
  terminal.value?.dispose()
})

// 外部API
defineExpose({
  terminal,
  sessionId,
  focus: () => terminal.value?.focus(),
  fit: () => fitAddon.value?.fit(),
  clear: () => terminal.value?.clear(),
  write: (data: string) => terminal.value?.write(data)
})
</script>

<style scoped lang="scss">
.aether-terminal-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #1e1e1e;
  position: relative;
  overflow: hidden;
}

.aether-terminal {
  flex: 1;
  width: 100%;
  height: 100%;
  
  :deep(.xterm) {
    height: 100% !important;
    width: 100% !important;
  }
  
  :deep(.xterm-viewport) {
    background-color: #1e1e1e;
  }
  
  :deep(.xterm-screen) {
    background-color: #1e1e1e;
  }
}
</style>