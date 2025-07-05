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
import { ref, onMounted, onBeforeUnmount, computed, watch, watchEffect, nextTick } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { SearchAddon } from '@xterm/addon-search'
import { WebLinksAddon } from '@xterm/addon-web-links'
import { useAetherTerminalStore } from '../../stores/aetherTerminalStore'
import { useTerminalTabStore } from '../../stores/terminalTabStore'
import { useTerminalPaneStore } from '../../stores/terminalPaneStore'
import { useThemeStore } from '../../stores/themeStore'
import { useScreenBufferStore } from '../../stores/screenBufferStore'
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
const searchAddon = ref<SearchAddon | null>(null)
const webLinksAddon = ref<WebLinksAddon | null>(null)

// Store references（新しいクリーンなストア）
const aetherStore = useAetherTerminalStore()
const tabStore = useTerminalTabStore()
const paneStore = useTerminalPaneStore()
const themeStore = useThemeStore()
const screenBufferStore = useScreenBufferStore()

// State
const sessionId = ref<string | null>(null)
const isInitialized = ref(false)

// Computed
const terminalElementId = computed(() => `aether-${props.mode}-${props.id}`)

// Terminal theme configuration
const terminalTheme = computed(() => {
  const colors = themeStore.currentColors
  if (!colors) {
    // Fallback theme
    return {
      background: '#1e1e1e',
      foreground: '#d4d4d4',
      cursor: '#ffffff',
      selection: '#264f78',
      black: '#000000',
      red: '#cd3131',
      green: '#0dbc79',
      yellow: '#e5e510',
      blue: '#2472c8',
      magenta: '#bc3fbc',
      cyan: '#11a8cd',
      white: '#e5e5e5',
      brightBlack: '#666666',
      brightRed: '#f14c4c',
      brightGreen: '#23d18b',
      brightYellow: '#f5f543',
      brightBlue: '#3b8eea',
      brightMagenta: '#d670d6',
      brightCyan: '#29b8db',
      brightWhite: '#e5e5e5'
    }
  }
  
  return {
    background: colors.background,
    foreground: colors.foreground,
    cursor: colors.cursor,
    selection: colors.selection,
    black: colors.black,
    red: colors.red,
    green: colors.green,
    yellow: colors.yellow,
    blue: colors.blue,
    magenta: colors.magenta,
    cyan: colors.cyan,
    white: colors.white,
    brightBlack: colors.bright_black,
    brightRed: colors.bright_red,
    brightGreen: colors.bright_green,
    brightYellow: colors.bright_yellow,
    brightBlue: colors.bright_blue,
    brightMagenta: colors.bright_magenta,
    brightCyan: colors.bright_cyan,
    brightWhite: colors.bright_white
  }
})

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

  // xterm.js作成 - パフォーマンス最適化
  terminal.value = new Terminal({
    cursorBlink: false, // パフォーマンス向上のため無効化
    theme: terminalTheme.value,
    fontSize: themeStore.themeConfig.fontSize,
    fontFamily: themeStore.themeConfig.fontFamily,
    // 固定サイズを削除 - FitAddonに任せる
    scrollback: 500, // メモリ使用量削減
    fastScrollModifier: 'shift', // 高速スクロール有効化
    rightClickSelectsWord: false, // 選択処理オーバーヘッド削減
    // rendererType: 'canvas' // xterm.js 5.x では廃止されたオプション
  })

  // Load addons
  fitAddon.value = new FitAddon()
  searchAddon.value = new SearchAddon()
  webLinksAddon.value = new WebLinksAddon()
  
  terminal.value.loadAddon(fitAddon.value)
  terminal.value.loadAddon(searchAddon.value)
  terminal.value.loadAddon(webLinksAddon.value)

  // ターミナルをDOMに追加
  terminal.value.open(terminalRef.value)
  
  // ResizeObserverでfitを最適化
  let fitTimeout: number | null = null
  const debouncedFit = () => {
    if (fitTimeout) clearTimeout(fitTimeout)
    fitTimeout = setTimeout(() => {
      fitAddon.value?.fit()
      fitTimeout = null
    }, 100)
  }
  
  // 初回サイズ調整
  debouncedFit()

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
      // Add input to screen buffer
      screenBufferStore.addLine(sessionId.value, data, 'input')
      aetherStore.sendInput(sessionId.value, data)
    } else {
      console.warn(`⚠️ AETHER_TERMINAL: No session for ${props.mode}:`, props.id)
    }
  })

  // Keyboard shortcuts
  terminal.value.attachCustomKeyEventHandler((event) => {
    // Ctrl+Shift+F for search
    if (event.ctrlKey && event.shiftKey && event.key === 'F') {
      event.preventDefault()
      openSearch()
      return false
    }
    
    // Ctrl+Shift+C for copy
    if (event.ctrlKey && event.shiftKey && event.key === 'C') {
      event.preventDefault()
      copySelection()
      return false
    }
    
    // Ctrl+Shift+V for paste
    if (event.ctrlKey && event.shiftKey && event.key === 'V') {
      event.preventDefault()
      pasteFromClipboard()
      return false
    }
    
    return true
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

  // 出力バッファリングでパフォーマンス最適化
  let outputBuffer = ''
  let flushTimeout: number | null = null
  
  const outputCallback = (data: string) => {
    outputBuffer += data
    
    if (flushTimeout) clearTimeout(flushTimeout)
    
    flushTimeout = setTimeout(() => {
      if (outputBuffer && terminal.value && sessionId.value) {
        terminal.value.write(outputBuffer)
        // Add output to screen buffer
        screenBufferStore.addLine(sessionId.value, outputBuffer, 'output')
        outputBuffer = ''
      }
      flushTimeout = null
    }, 16) // ~60fps でフラッシュ
  }

  aetherStore.registerOutputCallback(sessionId.value, outputCallback)
  console.log(`📺 AETHER_TERMINAL: Output setup for ${props.mode}:`, props.id)
}

// テーマ更新
const updateTerminalTheme = () => {
  if (!terminal.value) return
  
  console.log(`🎨 AETHER_TERMINAL: Updating theme for ${props.mode}:`, props.id, themeStore.themeConfig.colorScheme)
  
  // Update terminal theme
  terminal.value.options.theme = terminalTheme.value
  terminal.value.options.fontSize = themeStore.themeConfig.fontSize
  terminal.value.options.fontFamily = themeStore.themeConfig.fontFamily
  terminal.value.options.cursorBlink = themeStore.themeConfig.cursorBlink
  
  // Refresh terminal to apply changes
  terminal.value.refresh(0, terminal.value.rows - 1)
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

// テーマ変更監視 - 統合・debounce最適化
let themeUpdateTimeout: number | null = null
const debouncedThemeUpdate = () => {
  if (themeUpdateTimeout) clearTimeout(themeUpdateTimeout)
  themeUpdateTimeout = setTimeout(() => {
    updateTerminalTheme()
    // レイアウト変更が必要な場合のみfit実行
    if (fitAddon.value) {
      fitAddon.value.fit()
    }
    themeUpdateTimeout = null
  }, 50) // 50msでdebounce
}

// 統合されたテーマwatcher
watchEffect(() => {
  // currentColors, fontSize, fontFamilyの変更を監視
  themeStore.currentColors
  themeStore.themeConfig.fontSize
  themeStore.themeConfig.fontFamily
  
  if (terminal.value) {
    debouncedThemeUpdate()
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

// Screen buffer API
const clearScreenBuffer = () => {
  if (sessionId.value) {
    screenBufferStore.clearBuffer(sessionId.value)
    terminal.value?.clear()
  }
}

const saveBufferState = (stateName: string) => {
  if (sessionId.value) {
    screenBufferStore.saveBufferState(sessionId.value, stateName)
  }
}

const restoreBufferState = (stateName: string) => {
  if (sessionId.value) {
    const restored = screenBufferStore.restoreBufferState(sessionId.value, stateName)
    if (restored && terminal.value) {
      terminal.value.clear()
      const lines = screenBufferStore.getBufferLines(sessionId.value)
      lines.forEach(line => {
        terminal.value?.write(line.content)
      })
    }
    return restored
  }
  return false
}

const exportBuffer = (format: 'text' | 'json' = 'text') => {
  if (sessionId.value) {
    return screenBufferStore.exportBuffer(sessionId.value, format)
  }
  return ''
}

const getBufferStats = () => {
  if (sessionId.value) {
    return screenBufferStore.getBufferStats(sessionId.value)
  }
  return { totalLines: 0, currentLine: 0, maxLines: 0 }
}

// Search functionality
const openSearch = () => {
  if (!searchAddon.value) return
  
  const searchTerm = prompt('Search terminal:')
  if (searchTerm) {
    searchAddon.value.findNext(searchTerm)
  }
}

const searchNext = (term: string) => {
  if (searchAddon.value) {
    searchAddon.value.findNext(term)
  }
}

const searchPrevious = (term: string) => {
  if (searchAddon.value) {
    searchAddon.value.findPrevious(term)
  }
}

// Copy/Paste functionality
const copySelection = () => {
  if (!terminal.value) return
  
  const selection = terminal.value.getSelection()
  if (selection) {
    navigator.clipboard.writeText(selection).then(() => {
      console.log('📋 TERMINAL: Text copied to clipboard')
    }).catch((err) => {
      console.error('❌ TERMINAL: Failed to copy text', err)
    })
  }
}

const pasteFromClipboard = async () => {
  if (!terminal.value || !sessionId.value) return
  
  try {
    const text = await navigator.clipboard.readText()
    if (text) {
      aetherStore.sendInput(sessionId.value, text)
      console.log('📋 TERMINAL: Text pasted from clipboard')
    }
  } catch (err) {
    console.error('❌ TERMINAL: Failed to paste text', err)
  }
}

// Selection utilities
const selectAll = () => {
  if (terminal.value) {
    terminal.value.selectAll()
  }
}

const clearSelection = () => {
  if (terminal.value) {
    terminal.value.clearSelection()
  }
}

// 外部API
defineExpose({
  terminal,
  sessionId,
  focus: () => terminal.value?.focus(),
  fit: () => fitAddon.value?.fit(),
  clear: () => terminal.value?.clear(),
  write: (data: string) => terminal.value?.write(data),
  // Screen buffer API
  clearScreenBuffer,
  saveBufferState,
  restoreBufferState,
  exportBuffer,
  getBufferStats,
  // Search API
  openSearch,
  searchNext,
  searchPrevious,
  // Copy/Paste API
  copySelection,
  pasteFromClipboard,
  selectAll,
  clearSelection
})
</script>

<style scoped lang="scss">
.aether-terminal-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--terminal-background, #1e1e1e);
  position: relative;
  overflow: hidden;
  font-family: var(--terminal-font-family);
  font-size: var(--terminal-font-size);
  
  // Smooth transitions for theme changes
  transition: background-color 0.3s ease;
}

.aether-terminal {
  flex: 1;
  width: 100%;
  height: 100%;
  
  :deep(.xterm) {
    height: 100% !important;
    width: 100% !important;
    font-family: var(--terminal-font-family) !important;
    font-size: var(--terminal-font-size) !important;
  }
  
  :deep(.xterm-viewport) {
    background-color: var(--terminal-background, #1e1e1e) !important;
  }
  
  :deep(.xterm-screen) {
    background-color: var(--terminal-background, #1e1e1e) !important;
  }
  
  :deep(.xterm-cursor-layer) {
    .xterm-cursor {
      background-color: var(--terminal-cursor, #ffffff) !important;
    }
  }
  
  :deep(.xterm-selection) {
    background-color: var(--terminal-selection, #264f78) !important;
  }
  
  // Scrollbar theming
  :deep(.xterm-viewport)::-webkit-scrollbar {
    width: 8px;
  }
  
  :deep(.xterm-viewport)::-webkit-scrollbar-track {
    background: var(--terminal-background, #1e1e1e);
  }
  
  :deep(.xterm-viewport)::-webkit-scrollbar-thumb {
    background: var(--terminal-bright-black, #666666);
    border-radius: 4px;
    
    &:hover {
      background: var(--terminal-white, #e5e5e5);
    }
  }
}
</style>