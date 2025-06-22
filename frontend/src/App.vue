<script setup lang="ts">
import 'normalize.css'; // インストールしたライブラリの場合
import { onMounted, onUnmounted, ref, watch } from 'vue';
import SupervisorControlPanel from './components/SupervisorControlPanel.vue';
import ChatComponent from './components/ChatComponent.vue';
import SimpleChatComponent from './components/SimpleChatComponent.vue';
import TerminalComponent from './components/TerminalComponent.vue';
import WorkspaceManager from './components/WorkspaceManager.vue';
import WorkspaceDebugInfo from './components/WorkspaceDebugInfo.vue';
import DevJWTRegister from './components/DevJWTRegister.vue';
import SocketTrackingMonitor from './components/SocketTrackingMonitor.vue';
import { useChatStore } from './stores/chatStore';
import { enableJWTDevRegister } from './config/environment';
import { openTelemetryService } from './services/OpenTelemetryService';

const chatStore = useChatStore();

// Utility function to get current user ID
const getCurrentUserId = (): string => {
  // For now, return a default user ID - this would be replaced with actual user management
  return localStorage.getItem('aetherterm-user-id') || 'anonymous-user';
};
const activeTab = ref('chat'); // 'supervisor', 'chat', 'debug', or 'dev-auth'
const isSupervisorPanelFloating = ref(false);
const isSupervisorPanelVisible = ref(true);

// Panel width management
const panelWidth = ref(320); // デフォルト幅
const isResizing = ref(false);
const resizeStartX = ref(0);
const resizeStartWidth = ref(0);

// Dragging functionality for floating panel
const isDragging = ref(false);
const dragOffset = ref({ x: 0, y: 0 });
const panelPosition = ref({ x: 20, y: 60 });

const startDrag = (event: MouseEvent) => {
  if (!isSupervisorPanelFloating.value) return;

  isDragging.value = true;
  const rect = (event.target as HTMLElement).closest('#supervisor-container')?.getBoundingClientRect();
  if (rect) {
    dragOffset.value = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    };
  }

  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
  event.preventDefault();
};

const onDrag = (event: MouseEvent) => {
  if (!isDragging.value) return;

  const newX = event.clientX - dragOffset.value.x;
  const newY = event.clientY - dragOffset.value.y;

  // Constrain to viewport
  const maxX = window.innerWidth - 300; // min panel width
  const maxY = window.innerHeight - 400; // min panel height

  panelPosition.value = {
    x: Math.max(0, Math.min(newX, maxX)),
    y: Math.max(0, Math.min(newY, maxY))
  };
};

const stopDrag = () => {
  isDragging.value = false;
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
};

// Panel resize functionality with throttling
let resizeThrottleId = 0;

const startResize = (event: MouseEvent) => {
  if (isSupervisorPanelFloating.value) return; // リサイズはFixed時のみ
  
  isResizing.value = true;
  resizeStartX.value = event.clientX;
  resizeStartWidth.value = panelWidth.value;
  
  document.addEventListener('mousemove', onResize);
  document.addEventListener('mouseup', stopResize);
  event.preventDefault();
};

const onResize = (event: MouseEvent) => {
  if (!isResizing.value) return;
  
  // スロットル処理でパフォーマンス向上
  if (resizeThrottleId) {
    cancelAnimationFrame(resizeThrottleId);
  }
  
  resizeThrottleId = requestAnimationFrame(() => {
    const deltaX = resizeStartX.value - event.clientX; // 左に動かすとプラス
    const newWidth = resizeStartWidth.value + deltaX;
    
    // 最小幅と最大幅を制限
    const minWidth = 250;
    const maxWidth = Math.min(600, window.innerWidth * 0.4);
    
    panelWidth.value = Math.max(minWidth, Math.min(newWidth, maxWidth));
    resizeThrottleId = 0;
  });
};

const stopResize = () => {
  isResizing.value = false;
  document.removeEventListener('mousemove', onResize);
  document.removeEventListener('mouseup', stopResize);
  
  // 幅をlocalStorageに保存
  savePanelWidth();
};

// LocalStorage関連
const PANEL_WIDTH_KEY = 'aetherterm-panel-width';

const loadPanelWidth = () => {
  const saved = localStorage.getItem(PANEL_WIDTH_KEY);
  if (saved) {
    const width = parseInt(saved, 10);
    if (width >= 250 && width <= 600) {
      panelWidth.value = width;
    }
  }
};

const savePanelWidth = () => {
  localStorage.setItem(PANEL_WIDTH_KEY, panelWidth.value.toString());
};

// Panel visibility management
const PANEL_VISIBILITY_KEY = 'aetherterm-panel-visible';

const loadPanelVisibility = () => {
  const saved = localStorage.getItem(PANEL_VISIBILITY_KEY);
  if (saved !== null) {
    isSupervisorPanelVisible.value = saved === 'true';
  }
};

const savePanelVisibility = () => {
  localStorage.setItem(PANEL_VISIBILITY_KEY, isSupervisorPanelVisible.value.toString());
};

const togglePanelVisibility = () => {
  isSupervisorPanelVisible.value = !isSupervisorPanelVisible.value;
  savePanelVisibility();
};

// 初期化時に保存された設定を読み込み
onMounted(async () => {
  loadPanelWidth();
  loadPanelVisibility();
  
  // Initialize OpenTelemetry service
  try {
    console.log('🔍 Initializing OpenTelemetry...')
    await openTelemetryService.initialize()
    console.log('✅ OpenTelemetry initialized successfully')
    
    // Set initial context
    openTelemetryService.updateContext({
      userId: getCurrentUserId(),
      componentName: 'App'
    })
    
    // Log application startup
    openTelemetryService.logInfo('application_startup', {
      version: process.env.VUE_APP_VERSION || 'unknown',
      environment: process.env.NODE_ENV || 'unknown',
      user_agent: navigator.userAgent,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      }
    })
    
    // Create test trace for OpenObserve verification
    const testSpan = openTelemetryService.createSpan('app_initialization', {
      'app.version': process.env.VUE_APP_VERSION || '1.0.0',
      'app.environment': process.env.NODE_ENV || 'development',
      'test.trace': true
    })
    
    if (testSpan) {
      testSpan.addEvent('Application started successfully')
      testSpan.end()
      console.log('🧪 Test trace sent to OpenObserve')
    }
    
  } catch (error) {
    console.error('❌ Failed to initialize OpenTelemetry:', error)
    // Don't block app startup if telemetry fails
  }
});

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
  document.removeEventListener('mousemove', onResize);
  document.removeEventListener('mouseup', stopResize);
});

watch(chatStore.activeMessages, (newMessages) => {
  if (newMessages.length > 0 && activeTab.value !== 'chat') {
    activeTab.value = 'chat';
  }
});
</script>

<template>
  <div id="app-container">
    <!-- Main Content Area -->
    <div class="main-content">
      <!-- Session Manager Container (Full Width) -->
      <div id="workspace-container">
        <WorkspaceManager />
      </div>
    </div>

    <!-- Supervisor Control Panel (Fixed or Floating) -->
    <div
      v-if="isSupervisorPanelVisible"
      id="supervisor-container"
      :class="{
        'supervisor-floating': isSupervisorPanelFloating,
        'supervisor-fixed': !isSupervisorPanelFloating,
        'dragging': isDragging,
        'resizing': isResizing
      }"
      :style="isSupervisorPanelFloating ? {
        top: panelPosition.y + 'px',
        right: 'auto',
        left: panelPosition.x + 'px'
      } : {
        width: panelWidth + 'px'
      }"
    >
      <!-- Resize Handle (Fixed時のみ表示) -->
      <div v-if="!isSupervisorPanelFloating" class="resize-handle-container">
        <div 
          class="resize-handle-button" 
          @mousedown="startResize"
          :class="{ 'active': isResizing }"
        ></div>
      </div>
      <!-- Tab Navigation -->
      <div class="tab-navigation">
        <button
          :class="{ 'active': activeTab === 'chat' }"
          @click="activeTab = 'chat'"
        >
          Chat
        </button>
        <button
          :class="{ 'active': activeTab === 'supervisor' }"
          @click="activeTab = 'supervisor'"
        >
          Supervisor Control
        </button>
        <button
          :class="{ 'active': activeTab === 'debug' }"
          @click="activeTab = 'debug'"
        >
          Debug Info
        </button>
        <button
          :class="{ 'active': activeTab === 'socket-monitor' }"
          @click="activeTab = 'socket-monitor'"
          class="monitor-tab"
        >
          🔗 Socket Monitor
        </button>
        <button
          v-if="enableJWTDevRegister"
          :class="{ 'active': activeTab === 'dev-auth' }"
          @click="activeTab = 'dev-auth'"
          class="dev-tab"
        >
          🔧 Dev Auth
        </button>
      </div>

      <!-- Tab Content -->
      <div v-if="activeTab === 'chat'" class="tab-content chat-tab">
        <SimpleChatComponent />
      </div>
      <div v-if="activeTab === 'supervisor'" class="tab-content supervisor-tab">
        <SupervisorControlPanel />
      </div>
      <div v-if="activeTab === 'debug'" class="tab-content debug-tab">
        <WorkspaceDebugInfo />
      </div>
      <div v-if="activeTab === 'socket-monitor'" class="tab-content socket-monitor-tab">
        <SocketTrackingMonitor />
      </div>
      <div v-if="activeTab === 'dev-auth'" class="tab-content dev-auth-tab">
        <DevJWTRegister />
      </div>
    </div>

    <!-- Panel Toggle Button -->
    <div 
      class="panel-toggle-container"
      :style="{
        right: isSupervisorPanelVisible && !isSupervisorPanelFloating ? (panelWidth + 'px') : '0px'
      }"
    >
      <button 
        @click="togglePanelVisibility" 
        class="panel-toggle-btn"
        :class="{ 'panel-hidden': !isSupervisorPanelVisible }"
        :title="isSupervisorPanelVisible ? 'Hide Chat Panel' : 'Show Chat Panel'"
      >
        {{ isSupervisorPanelVisible ? '→' : '←' }}
      </button>
    </div>
    
  </div>
</template>

<style scoped>
/* Add "scoped" to limit the scope of these styles */

.tab-navigation {
  display: flex;
  background-color: #1e1e1e;
  border-bottom: 1px solid #444;
}

.tab-navigation button {
  background: none;
  border: none;
  color: #ccc;
  padding: 10px 15px;
  cursor: pointer;
  font-size: 14px;
}

.tab-navigation button.active {
  background-color: #4caf50;
  color: white;
}

.tab-navigation button.dev-tab {
  border-left: 1px solid #444;
  border-right: 1px solid #444;
  background-color: #2a2a2a;
  color: #ff9800;
  font-size: 12px;
}

.tab-navigation button.dev-tab:hover {
  background-color: #333;
}

.tab-navigation button.dev-tab.active {
  background-color: #ff9800;
  color: white;
}

.tab-content {
  padding: 15px;
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

/* チャット専用のレイアウト調整 */
.tab-content.chat-tab {
  padding: 0; /* チャットは独自のパディングを持つ */
}

.tab-content.supervisor-tab {
  /* Supervisorタブは通常のパディング */
}

.tab-content.dev-auth-tab {
  /* Development Authタブは通常のパディング */
  padding: 0; /* DevJWTRegisterコンポーネントが独自のパディングを持つ */
}

.tab-content.socket-monitor-tab {
  /* Socket Monitorタブはカスタムパディング */
  padding: 0; /* SocketTrackingMonitorコンポーネントが独自のパディングを持つ */
}

.tab-navigation button.monitor-tab {
  background-color: #2a2a2a;
  color: #00d4aa;
  font-size: 12px;
}

.tab-navigation button.monitor-tab:hover {
  background-color: #333;
}

.tab-navigation button.monitor-tab.active {
  background-color: #00d4aa;
  color: white;
}

html, body, #app {
  height: 100vh;
  margin: 0 !important;
  padding: 0 !important;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

#app-container {
  height: 100vh;
  position: relative;
  display: flex;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: row; /* Make main-content a flexbox */
  height: 100%; /* Ensure full vertical height */
  min-width: 0;
  position: relative;
}

#workspace-container {
  flex-grow: 1; /* Make workspace-container grow to fill space */
  overflow: hidden;
  background-color: #1e1e1e;
  transition: width 0.1s ease-out;
  width: 100%;
  height: 100%;
}

#chat-container {
  background-color: #f9f9f9;
  border-top: 1px solid #444;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}


.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 15px;
  background-color: #e0e0e0;
  border-bottom: 1px solid #ccc;
  color: #333;
}

.chat-header h3 {
  margin: 0;
  font-size: 14px;
  color: #2196f3;
}

/* Supervisor Panel Styles */
#supervisor-container {
  background-color: #2d2d2d;
  display: flex;
  flex-direction: column;
  transition: width 0.1s ease-out;
  z-index: 1000;
}

.supervisor-fixed {
  height: 100%;
  border-left: 1px solid #444;
  flex-shrink: 0;
  position: relative;
  min-width: 250px;
  max-width: 600px;
}

.supervisor-floating {
  position: fixed;
  top: 60px;
  right: 20px;
  width: 400px;
  height: 70vh;
  border: 1px solid #444;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  resize: both;
  overflow: auto;
  min-width: 300px;
  min-height: 400px;
  max-width: 90vw;
  max-height: 90vh;
}

.supervisor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background-color: #1e1e1e;
  border-bottom: 1px solid #444;
  color: white;
  cursor: move; /* For floating panel dragging */
}

.supervisor-floating .supervisor-header {
  border-radius: 8px 8px 0 0;
}

.supervisor-header h3 {
  margin: 0;
  font-size: 16px;
  color: #4caf50;
}

.supervisor-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.float-toggle-btn {
  background: none;
  border: none;
  color: #ccc;
  font-size: 16px;
  cursor: pointer;
  padding: 4px;
  border-radius: 3px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.float-toggle-btn:hover {
  background-color: #444;
  color: white;
}

.close-btn {
  background: none;
  border: none;
  color: #ccc;
  font-size: 20px;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
}

.close-btn:hover {
  background-color: #444;
  color: white;
}

/* Control Buttons */
.control-buttons {
  position: fixed;
  top: 20px;
  right: 20px;
  display: flex;
  gap: 10px;
  z-index: 999;
}

.control-btn {
  background-color: #4caf50;
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 12px;
  font-weight: bold;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  transition: all 0.2s ease;
}

.control-btn:hover {
  background-color: #45a049;
  transform: translateY(-1px);
}

.chat-btn {
  background-color: #2196f3;
}

.chat-btn:hover {
  background-color: #1976d2;
}

/* Responsive adjustments */
@media (max-width: 1200px) {
  .supervisor-fixed {
    width: 300px;
  }

  .supervisor-floating {
    width: 350px;
    right: 10px;
  }
}

@media (max-width: 900px) {
  .main-content {
    flex-direction: column;
  }

  #chat-container {
    height: 200px !important;
    border-top: 1px solid #444;
    border-left: none;
  }

  .supervisor-fixed {
    position: fixed;
    top: 0;
    right: 0;
    width: 100%;
    height: 100%;
    z-index: 1001;
  }

  .supervisor-floating {
    width: 90vw;
    height: 80vh;
    top: 10vh;
    right: 5vw;
  }

  .control-buttons {
    top: 10px;
    right: 10px;
  }

  .control-btn {
    padding: 6px 10px;
    font-size: 11px;
  }
}

/* Draggable functionality for floating panel */
.supervisor-floating .supervisor-header {
  user-select: none;
}

/* Scrollbar styling for admin panel */
.supervisor-floating {
  scrollbar-width: thin;
  scrollbar-color: #666 #2d2d2d;
}

.supervisor-floating::-webkit-scrollbar {
  width: 8px;
}

.supervisor-floating::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.supervisor-floating::-webkit-scrollbar-thumb {
  background: #666;
  border-radius: 4px;
}

.supervisor-floating::-webkit-scrollbar-thumb:hover {
  background: #888;
}

/* Draggable functionality enhancements */
.supervisor-floating .supervisor-header {
  user-select: none;
}

.supervisor-container.dragging {
  opacity: 0.9;
  transform: scale(1.02);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
  z-index: 1001;
}

.supervisor-floating.dragging {
  transition: none;
}

/* Resize handle styles */
.resize-handle-container {
  position: absolute;
  left: -8px;
  top: 0;
  bottom: 0;
  width: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  pointer-events: none; /* コンテナ自体はクリックできない */
}

.resize-handle-button {
  width: 10px;
  height: 80px;
  background-color: #666;
  border-radius: 5px;
  cursor: col-resize;
  transition: all 0.2s ease;
  position: relative;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  pointer-events: auto; /* ボタンのみクリック可能 */
}

.resize-handle-button::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 3px;
  height: 30px;
  background: repeating-linear-gradient(
    to bottom,
    #999 0px,
    #999 3px,
    transparent 3px,
    transparent 6px
  );
  border-radius: 1.5px;
}

.resize-handle-button:hover {
  background-color: #777;
  transform: scaleY(1.1);
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.4);
}

.resize-handle-button:hover::before {
  background: repeating-linear-gradient(
    to bottom,
    #bbb 0px,
    #bbb 3px,
    transparent 3px,
    transparent 6px
  );
}

.resize-handle-button.active {
  background-color: #4caf50;
  transform: scaleY(1.2);
  box-shadow: 0 0 8px rgba(76, 175, 80, 0.5);
}

.resize-handle-button.active::before {
  background: repeating-linear-gradient(
    to bottom,
    #fff 0px,
    #fff 3px,
    transparent 3px,
    transparent 6px
  );
}

/* Add visual feedback during resize */
.supervisor-container.resizing {
  user-select: none;
  transition: none; /* リサイズ中はトランジションを無効化 */
}

.supervisor-container.resizing * {
  user-select: none;
  pointer-events: none; /* リサイズ中は子要素のイベントを無効化 */
}

/* Admin content and chat content styles */
.supervisor-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.chat-content {
  flex: 1;
  overflow: hidden;
}

.supervisor-floating .supervisor-header {
  border-radius: 8px 8px 0 0;
}

/* Panel Toggle Button */
.panel-toggle-container {
  position: fixed;
  top: 20px;
  transform: none;
  z-index: 1001;
  transition: right 0.3s ease;
}

.panel-toggle-btn {
  background-color: #4caf50;
  color: white;
  border: none;
  width: 60px;
  height: 30px;
  border-radius: 0 0 0 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
  transform: translateY(0);
  writing-mode: initial;
  text-orientation: initial;
}

.panel-toggle-btn:hover {
  background-color: #45a049;
  transform: translateY(3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.panel-toggle-btn.panel-hidden {
  background-color: #2196f3;
  border-radius: 0 0 6px 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.panel-toggle-btn.panel-hidden:hover {
  background-color: #1976d2;
  transform: translateY(3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

/* モバイル画面での調整 */
@media (max-width: 900px) {
  .panel-toggle-container {
    top: 10px;
    right: 10px !important;
  }
  
  .panel-toggle-btn {
    width: 50px;
    height: 35px;
    border-radius: 0 0 6px 6px;
    font-size: 16px;
  }
  
  .panel-toggle-btn.panel-hidden {
    border-radius: 0 0 6px 6px;
  }
}
</style>
