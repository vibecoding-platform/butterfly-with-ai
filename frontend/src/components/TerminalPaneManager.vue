<template>
  <div class="pane-manager">
    <!-- Pane Controls Toolbar -->
    <div class="pane-toolbar">
      <div class="pane-info">
        <span class="pane-count">{{ terminalTab.panes.length }} panes</span>
        <span class="layout-type">{{ terminalTab.layout }}</span>
      </div>
      
      <div class="pane-controls">
        <!-- Split buttons -->
        <button 
          @click="splitHorizontal"
          :disabled="!activePane"
          class="split-btn"
          title="Split horizontally (Ctrl+B, %)"
        >
          ⫽
        </button>
        <button 
          @click="splitVertical"
          :disabled="!activePane"
          class="split-btn"
          title="Split vertically (Ctrl+B, &quot;)"
        >
          ⫾
        </button>
        
        <!-- Layout buttons -->
        <div class="layout-controls">
          <button 
            @click="setLayout('horizontal')"
            :class="{ active: terminalTab.layout === 'horizontal' }"
            class="layout-btn"
            title="Horizontal layout"
          >
            ═
          </button>
          <button 
            @click="setLayout('vertical')"
            :class="{ active: terminalTab.layout === 'vertical' }"
            class="layout-btn"
            title="Vertical layout"
          >
            ║
          </button>
          <button 
            @click="setLayout('grid')"
            :class="{ active: terminalTab.layout === 'grid' }"
            class="layout-btn"
            title="Grid layout"
          >
            ⊞
          </button>
        </div>

        <!-- Close pane -->
        <button 
          @click="closeActivePane"
          :disabled="terminalTab.panes.length <= 1"
          class="close-pane-btn"
          title="Close pane (Ctrl+B, X)"
        >
          ✕
        </button>
      </div>
    </div>

    <!-- Pane Container -->
    <div 
      class="pane-container"
      :class="`layout-${terminalTab.layout}`"
      ref="paneContainer"
    >
      <div 
        v-for="pane in terminalTab.panes" 
        :key="pane.id"
        class="terminal-pane"
        :class="{ 
          'active': pane.id === terminalTab.activePaneId,
          'dragging': isDragging && draggedPaneId === pane.id
        }"
        :style="getPaneStyle(pane)"
        @click="switchPane(pane.id)"
        @mousedown.stop="startPaneDrag(pane.id, $event)"
      >
        <!-- Pane Header -->
        <div class="pane-header">
          <div class="pane-title">
            <span class="pane-name">{{ pane.title || `Pane ${pane.id.slice(-6)}` }}</span>
            <span class="pane-id">{{ pane.terminalId?.slice(-6) || 'N/A' }}</span>
          </div>
          <div class="pane-controls-mini">
            <button 
              @click.stop="closePane(pane.id)"
              :disabled="terminalTab.panes.length <= 1"
              class="mini-close-btn"
            >
              ×
            </button>
          </div>
        </div>

        <!-- Terminal Content -->
        <div class="pane-content">
          <PaneTerminal 
            :key="pane.id"
            :ref="(el) => setPaneTerminalRef(pane.id, el)"
            :tab-id="terminalTab.id"
            :pane-id="pane.id"
            :terminal-id="pane.terminalId || `terminal-${pane.id}`"
          />
        </div>

        <!-- Resize handles -->
        <div 
          v-if="pane.id !== terminalTab.panes[terminalTab.panes.length - 1].id"
          class="resize-handle vertical"
          @mousedown.stop="(event) => startResize(pane.id, 'vertical', event)"
        ></div>
        <div 
          v-if="terminalTab.layout === 'vertical' && pane.id !== terminalTab.panes[terminalTab.panes.length - 1].id"
          class="resize-handle horizontal" 
          @mousedown.stop="(event) => startResize(pane.id, 'horizontal', event)"
        ></div>
      </div>
    </div>

    <!-- Pane Navigator (tmux-style window list) -->
    <div class="pane-navigator">
      <div class="pane-list">
        <button
          v-for="(pane, index) in terminalTab.panes"
          :key="pane.id"
          @click="switchPane(pane.id)"
          :class="{ 
            'active': pane.id === terminalTab.activePaneId 
          }"
          class="pane-nav-btn"
          :title="`${pane.title || `Pane ${pane.id.slice(-6)}`} (${pane.terminalId || 'N/A'})`"
        >
          {{ index + 1 }}{{ pane.id === terminalTab.activePaneId ? '*' : '' }}
        </button>
      </div>
      <div class="keyboard-shortcuts">
        <span class="shortcut">Ctrl+B then % (split-h) | " (split-v) | X (close)</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import PaneTerminal from './PaneTerminal.vue'
import type { TerminalTab } from '@/types/session'

interface Props {
  terminalTab: TerminalTab
  sessionId: string
  tabId: string
}

const props = defineProps<Props>()

// PaneTerminal refs management
const paneTerminalRefs = ref<Map<string, any>>(new Map())
const terminalCreationTimers = ref<Map<string, NodeJS.Timeout>>(new Map())

// Function to set PaneTerminal ref
const setPaneTerminalRef = (paneId: string, el: any) => {
  if (el) {
    // Only set ref and create timer if this pane doesn't already have them
    if (!paneTerminalRefs.value.has(paneId)) {
      console.log(`📌 Setting PaneTerminal ref for pane ${paneId}`)
      paneTerminalRefs.value.set(paneId, el)
      
      // Schedule delayed terminal creation only once
      const timer = setTimeout(() => {
        console.log(`⏰ Starting delayed terminal creation for pane ${paneId}`)
        if (paneTerminalRefs.value.has(paneId)) {
          const paneTerminalComponent = paneTerminalRefs.value.get(paneId)
          if (paneTerminalComponent && paneTerminalComponent.requestTerminalCreation) {
            paneTerminalComponent.requestTerminalCreation()
          } else {
            console.warn(`⚠️ PaneTerminal component for pane ${paneId} does not have requestTerminalCreation method`)
          }
        }
        // Clean up timer after execution - use nextTick to avoid reactive trigger during render
        setTimeout(() => {
          terminalCreationTimers.value.delete(paneId)
        }, 0)
      }, 1000) // 1秒後に実行
      
      terminalCreationTimers.value.set(paneId, timer)
    } else {
      // Just update the ref if pane already exists
      console.log(`🔄 Updating existing PaneTerminal ref for pane ${paneId}`)
      paneTerminalRefs.value.set(paneId, el)
    }
  } else {
    console.log(`🗑️ Clearing PaneTerminal ref for pane ${paneId}`)
    paneTerminalRefs.value.delete(paneId)
    
    // Clear timer if exists
    const existingTimer = terminalCreationTimers.value.get(paneId)
    if (existingTimer) {
      clearTimeout(existingTimer)
      terminalCreationTimers.value.delete(paneId)
    }
  }
}

// State for drag and resize
const isDragging = ref(false)
const isResizing = ref(false)
const draggedPaneId = ref<string | null>(null)
const resizeData = ref<{
  paneId: string
  direction: 'horizontal' | 'vertical'
  startX: number
  startY: number
  startWidth: number
  startHeight: number
} | null>(null)

const paneContainer = ref<HTMLElement>()

// Computed
const activePane = computed(() => 
  props.terminalTab.panes.find(p => p.id === props.terminalTab.activePaneId)
)

// Emit events for parent components to handle
const emit = defineEmits<{
  switchPane: [paneId: string]
  splitPane: [paneId: string, direction: 'horizontal' | 'vertical']
  closePane: [paneId: string]
  updateLayout: [layout: 'horizontal' | 'vertical' | 'grid']
  updatePanePosition: [paneId: string, position: { x: number, y: number, width: number, height: number }]
}>()

// Pane management functions
const switchPane = (paneId: string) => {
  emit('switchPane', paneId)
}

const splitHorizontal = () => {
  if (activePane.value) {
    emit('splitPane', activePane.value.id, 'horizontal')
  }
}

const splitVertical = () => {
  if (activePane.value) {
    emit('splitPane', activePane.value.id, 'vertical')
  }
}

const closePane = (paneId: string) => {
  if (props.terminalTab.panes.length > 1) {
    emit('closePane', paneId)
  }
}

const closeActivePane = () => {
  if (activePane.value && props.terminalTab.panes.length > 1) {
    closePane(activePane.value.id)
  }
}

const setLayout = (layout: 'horizontal' | 'vertical' | 'grid') => {
  emit('updateLayout', layout)
  recalculateLayout()
}

// Layout calculation
const getPaneStyle = (pane: import('@/types/session').TerminalPane) => {
  if (!pane.position) {
    return {}
  }
  return {
    left: `${pane.position.x}%`,
    top: `${pane.position.y}%`,
    width: `${pane.position.width}%`,
    height: `${pane.position.height}%`
  }
}

const recalculateLayout = () => {
  const panes = props.terminalTab.panes
  const layout = props.terminalTab.layout
  
  if (layout === 'horizontal') {
    // Arrange panes side by side
    const paneWidth = 100 / panes.length
    panes.forEach((pane, index) => {
      emit('updatePanePosition', pane.id, {
        x: index * paneWidth,
        y: 0,
        width: paneWidth,
        height: 100
      })
    })
  } else if (layout === 'vertical') {
    // Arrange panes top to bottom
    const paneHeight = 100 / panes.length
    panes.forEach((pane, index) => {
      emit('updatePanePosition', pane.id, {
        x: 0,
        y: index * paneHeight,
        width: 100,
        height: paneHeight
      })
    })
  } else if (layout === 'grid') {
    // Arrange panes in a grid
    const cols = Math.ceil(Math.sqrt(panes.length))
    const rows = Math.ceil(panes.length / cols)
    const paneWidth = 100 / cols
    const paneHeight = 100 / rows
    
    panes.forEach((pane, index) => {
      const col = index % cols
      const row = Math.floor(index / cols)
      emit('updatePanePosition', pane.id, {
        x: col * paneWidth,
        y: row * paneHeight,
        width: paneWidth,
        height: paneHeight
      })
    })
  }
}

// Drag and resize functionality
const startPaneDrag = (paneId: string, event: MouseEvent) => {
  isDragging.value = true
  draggedPaneId.value = paneId
  event.preventDefault()
}

const startResize = (paneId: string, direction: 'horizontal' | 'vertical', event: MouseEvent) => {
  const pane = props.terminalTab.panes.find(p => p.id === paneId)
  if (!pane || !pane.position) return

  isResizing.value = true
  resizeData.value = {
    paneId,
    direction,
    startX: event.clientX,
    startY: event.clientY,
    startWidth: pane.position.width,
    startHeight: pane.position.height
  }
  event.preventDefault()
}

const handleMouseMove = (event: MouseEvent) => {
  if (isResizing.value && resizeData.value) {
    const deltaX = event.clientX - resizeData.value.startX
    const deltaY = event.clientY - resizeData.value.startY
    const containerRect = paneContainer.value?.getBoundingClientRect()
    
    if (!containerRect) return

    if (resizeData.value.direction === 'horizontal') {
      const deltaPercent = (deltaX / containerRect.width) * 100
      const newWidth = Math.max(10, Math.min(90, resizeData.value.startWidth + deltaPercent))
      
      const pane = props.terminalTab.panes.find(p => p.id === resizeData.value!.paneId)
      if (pane && pane.position) {
        emit('updatePanePosition', pane.id, {
          ...pane.position,
          width: newWidth
        })
      }
    } else {
      const deltaPercent = (deltaY / containerRect.height) * 100
      const newHeight = Math.max(10, Math.min(90, resizeData.value.startHeight + deltaPercent))
      
      const pane = props.terminalTab.panes.find(p => p.id === resizeData.value!.paneId)
      if (pane && pane.position) {
        emit('updatePanePosition', pane.id, {
          ...pane.position,
          height: newHeight
        })
      }
    }
  }
}

const handleMouseUp = () => {
  isDragging.value = false
  isResizing.value = false
  draggedPaneId.value = null
  resizeData.value = null
}

// Keyboard shortcuts (tmux-style)
const handleKeydown = (event: KeyboardEvent) => {
  // Ctrl+B prefix for tmux-style shortcuts
  if (event.ctrlKey && event.key === 'b') {
    event.preventDefault()
    // Next keypress will be the command
    document.addEventListener('keydown', handleTmuxCommand, { once: true })
  }
}

const handleTmuxCommand = (event: KeyboardEvent) => {
  event.preventDefault()
  
  switch (event.key) {
    case '%':
      splitHorizontal()
      break
    case '"':
      splitVertical()
      break
    case 'x':
      closeActivePane()
      break
    case 'o':
      // Switch to next pane
      const currentIndex = props.terminalTab.panes.findIndex(p => p.id === props.terminalTab.activePaneId)
      const nextIndex = (currentIndex + 1) % props.terminalTab.panes.length
      switchPane(props.terminalTab.panes[nextIndex].id)
      break
  }
}

onMounted(() => {
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
  document.addEventListener('keydown', handleKeydown)
  
  // Initial layout calculation
  if (props.terminalTab.panes.length > 1) {
    recalculateLayout()
  }
})

onUnmounted(() => {
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
  document.removeEventListener('keydown', handleKeydown)
  
  // Clear all terminal creation timers
  terminalCreationTimers.value.forEach((timer) => {
    clearTimeout(timer)
  })
  terminalCreationTimers.value.clear()
  paneTerminalRefs.value.clear()
})
</script>

<style scoped>
.pane-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #1e1e1e;
}

.pane-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  background-color: #2a2a2a;
  border-bottom: 1px solid #444;
  font-size: 12px;
}

.pane-info {
  display: flex;
  gap: 12px;
  color: #888;
}

.pane-count {
  color: #4caf50;
  font-weight: 500;
}

.layout-type {
  text-transform: uppercase;
  color: #2196f3;
}

.pane-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.split-btn, .layout-btn, .close-pane-btn {
  background-color: #3d3d3d;
  color: #ccc;
  border: 1px solid #555;
  padding: 4px 8px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  /* Transition removed to prevent hover-like effects */
  /* transition: all 0.2s ease; */
  /* Remove click/focus effects */
  outline: none;
  -webkit-tap-highlight-color: transparent;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

.split-btn:focus,
.split-btn:active,
.split-btn:focus-visible,
.layout-btn:focus,
.layout-btn:active,
.layout-btn:focus-visible,
.close-pane-btn:focus,
.close-pane-btn:active,
.close-pane-btn:focus-visible {
  outline: none !important;
  background-color: #3d3d3d !important;
  border-color: #555 !important;
}

/* Hover states removed per user request */
/* .split-btn:hover, .layout-btn:hover, .close-pane-btn:hover {
  background-color: #4d4d4d;
  color: #fff;
} */

.split-btn:disabled, .close-pane-btn:disabled {
  background-color: #2a2a2a;
  color: #666;
  cursor: not-allowed;
  border-color: #3a3a3a;
}

.layout-controls {
  display: flex;
  gap: 2px;
}

.layout-btn.active {
  background-color: #2196f3;
  color: white;
  border-color: #1976d2;
}

.close-pane-btn {
  background-color: #d32f2f;
  border-color: #b71c1c;
  color: white;
}

/* Hover states removed per user request */
/* .close-pane-btn:hover:not(:disabled) {
  background-color: #f44336;
} */

.pane-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.terminal-pane {
  position: absolute;
  border: 2px solid transparent;
  background-color: #1e1e1e;
  display: flex;
  flex-direction: column;
  /* Transition removed to prevent hover-like effects */
  /* transition: border-color 0.2s ease; */
  /* Remove click/focus effects */
  outline: none;
  -webkit-tap-highlight-color: transparent;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

.terminal-pane:focus,
.terminal-pane:active,
.terminal-pane:focus-visible {
  outline: none !important;
  border-color: transparent !important;
}

.terminal-pane.active {
  border-color: #4caf50;
  z-index: 10;
}

/* Dragging effects removed per user request */
/* .terminal-pane.dragging {
  opacity: 0.8;
  transform: scale(0.98);
  z-index: 20;
} */

.pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  background-color: #2a2a2a;
  border-bottom: 1px solid #444;
  font-size: 11px;
}

.pane-title {
  display: flex;
  gap: 6px;
  align-items: center;
}

.pane-name {
  color: #fff;
  font-weight: 500;
}

.pane-id {
  color: #888;
  font-family: monospace;
}

.mini-close-btn {
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 14px;
  padding: 0 4px;
  /* Transition removed to prevent hover-like effects */
  /* transition: color 0.2s ease; */
  /* Remove click/focus effects */
  outline: none;
  -webkit-tap-highlight-color: transparent;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

.mini-close-btn:focus,
.mini-close-btn:active,
.mini-close-btn:focus-visible {
  outline: none !important;
  color: #888 !important;
}

/* Hover states removed per user request */
/* .mini-close-btn:hover:not(:disabled) {
  color: #f44336;
} */

.mini-close-btn:disabled {
  color: #555;
  cursor: not-allowed;
}

.pane-content {
  flex: 1;
  overflow: hidden;
}

.resize-handle {
  position: absolute;
  background-color: #4caf50;
  opacity: 0;
  /* Transition removed to prevent hover-like effects */
  /* transition: opacity 0.2s ease; */
  z-index: 15;
}

.resize-handle.vertical {
  right: -2px;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: col-resize;
}

.resize-handle.horizontal {
  bottom: -2px;
  left: 0;
  right: 0;
  height: 4px;
  cursor: row-resize;
}

/* Hover states removed per user request */
/* .terminal-pane:hover .resize-handle {
  opacity: 0.6;
} */

/* Hover states removed per user request */
/* .resize-handle:hover {
  opacity: 1 !important;
} */

.pane-navigator {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  background-color: #2a2a2a;
  border-top: 1px solid #444;
  font-size: 10px;
}

.pane-list {
  display: flex;
  gap: 4px;
}

.pane-nav-btn {
  background-color: #3d3d3d;
  color: #ccc;
  border: 1px solid #555;
  padding: 2px 6px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 10px;
  font-family: monospace;
  min-width: 20px;
  /* Transition removed to prevent hover-like effects */
  /* transition: all 0.2s ease; */
  /* Remove click/focus effects */
  outline: none;
  -webkit-tap-highlight-color: transparent;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

.pane-nav-btn:focus,
.pane-nav-btn:active,
.pane-nav-btn:focus-visible {
  outline: none !important;
  background-color: #3d3d3d !important;
  border-color: #555 !important;
}

/* Hover states removed per user request */
/* .pane-nav-btn:hover {
  background-color: #4d4d4d;
  color: #fff;
} */

.pane-nav-btn.active {
  background-color: #4caf50;
  color: white;
  border-color: #45a049;
}

.keyboard-shortcuts {
  color: #666;
  font-size: 9px;
}

.shortcut {
  font-family: monospace;
}
</style>