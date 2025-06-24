<script setup lang="ts">
import 'normalize.css'; // インストールしたライブラリの場合
import { onMounted, onUnmounted, ref, watch, computed } from 'vue';
import SupervisorControlPanel from './components/SupervisorControlPanel.vue';
import ChatComponent from './components/ChatComponent.vue';
import SimpleChatComponent from './components/SimpleChatComponent.vue';
import TerminalComponent from './components/TerminalComponent.vue';
import WorkspaceManager from './components/WorkspaceManager.vue';
import WorkspaceDebugInfo from './components/WorkspaceDebugInfo.vue';
import NewArchitectureTest from './components/NewArchitectureTest.vue';
import DevJWTRegister from './components/DevJWTRegister.vue';
import SocketTrackingMonitor from './components/SocketTrackingMonitor.vue';
import ErrorScreen from './components/ErrorScreen.vue';
import LoadingScreen from './components/LoadingScreen.vue';
import TimeoutScreen from './components/TimeoutScreen.vue';
import FloatingControlPanel from './components/FloatingControlPanel.vue';
import { useChatStore } from './stores/chatStore';
import { enableJWTDevRegister } from './config/environment';
import { openTelemetryService } from './services/OpenTelemetryService';
import { getSocketManager, type ErrorEvent } from './services/AetherTermSocketManager';

const chatStore = useChatStore();

// Error state management
const showErrorScreen = ref(false);
const currentError = ref<ErrorEvent | null>(null);
const socketManager = getSocketManager();

// Loading state management
const isInitializing = ref(true);
const initializationTimeout = ref(false);
const initializationError = ref<string | null>(null);

// Utility function to get current user ID
const getCurrentUserId = (): string => {
  // For now, return a default user ID - this would be replaced with actual user management
  return localStorage.getItem('aetherterm-user-id') || 'anonymous-user';
};
const activeTab = ref('chat'); // 'supervisor', 'chat', 'debug', or 'dev-auth'
const isSupervisorPanelVisible = ref(true);

// Show main app only when not in error state and initialization is complete
const showMainApp = computed(() => !showErrorScreen.value && !isInitializing.value && !initializationTimeout.value);

// Show loading screen during initialization
const showLoadingScreen = computed(() => isInitializing.value && !showErrorScreen.value);

// Show initialization timeout screen
const showTimeoutScreen = computed(() => initializationTimeout.value && !showErrorScreen.value);

// Panel width management
const panelWidth = ref(320); // デフォルト幅
const isResizing = ref(false);
const resizeStartX = ref(0);
const resizeStartWidth = ref(0);


// Panel resize functionality with throttling
let resizeThrottleId = 0;

const startResize = (event: MouseEvent) => {
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

const handleSwitchTab = (tab: string) => {
  activeTab.value = tab;
};

// Error handling methods
const handleConnectionError = (error: ErrorEvent) => {
  console.error('🚨 Connection error detected:', error);
  
  // Only show error screen for non-recoverable errors or critical connection failures
  if (!error.recoverable || error.type === 'CONNECTION_ERROR') {
    currentError.value = error;
    showErrorScreen.value = true;
  }
};

const handleRetry = async () => {
  showErrorScreen.value = false;
  currentError.value = null;
  
  try {
    await socketManager.retry();
    console.log('✅ Connection retry successful');
  } catch (error) {
    console.error('❌ Connection retry failed:', error);
    // Error will be handled by the error handler
  }
};

const handleReload = () => {
  window.location.reload();
};

const checkConnectionStatus = async () => {
  try {
    const connectionState = socketManager.getConnectionState();
    
    // If connection is in error state and not recoverable, show error screen
    if (connectionState.value.status === 'error' && 
        connectionState.value.errorType && 
        !socketManager.isRecoverable()) {
      const lastError = socketManager.getLastError();
      if (lastError) {
        handleConnectionError(lastError);
      }
    }
  } catch (error) {
    console.error('Error checking connection status:', error);
  }
};

const handleInitializationComplete = () => {
  isInitializing.value = false;
  initializationTimeout.value = false;
  initializationError.value = null;
  console.log('✅ AetherTerm initialization completed');
};

const handleInitializationTimeout = () => {
  isInitializing.value = false;
  initializationTimeout.value = true;
  initializationError.value = 'Initialization timed out after 30 seconds';
  console.error('❌ AetherTerm initialization timed out');
};

const handleInitializationError = (error: string) => {
  isInitializing.value = false;
  initializationTimeout.value = true;
  initializationError.value = error;
  console.error('❌ AetherTerm initialization error:', error);
};

const retryInitialization = async () => {
  isInitializing.value = true;
  initializationTimeout.value = false;
  initializationError.value = null;
  
  try {
    // Try to reconnect socket manager
    await socketManager.retry();
    
    // Wait for connection to establish
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Connection timeout'));
      }, 15000);
      
      const checkConnection = () => {
        if (socketManager.isConnected()) {
          clearTimeout(timeout);
          resolve(void 0);
        } else {
          setTimeout(checkConnection, 500);
        }
      };
      
      checkConnection();
    });
    
    handleInitializationComplete();
  } catch (error) {
    handleInitializationError(error instanceof Error ? error.message : 'Unknown error');
  }
};

// 初期化時に保存された設定を読み込み
onMounted(async () => {
  loadPanelWidth();
  loadPanelVisibility();
  
  // Setup error handling
  const unsubscribeErrorHandler = socketManager.onError(handleConnectionError);
  
  // Set up initialization timeout (30 seconds)
  const initTimeoutHandle = setTimeout(handleInitializationTimeout, 30000);
  
  // Monitor socket connection for initialization completion
  const checkInitialization = () => {
    if (socketManager.isConnected()) {
      clearTimeout(initTimeoutHandle);
      handleInitializationComplete();
    } else {
      // Check again in 500ms if still initializing
      if (isInitializing.value) {
        setTimeout(checkInitialization, 500);
      }
    }
  };
  
  // Start monitoring initialization
  checkInitialization();
  
  // Check initial connection status
  await checkConnectionStatus();
  
  // Store unsubscribe function for cleanup
  onUnmounted(() => {
    unsubscribeErrorHandler();
    clearTimeout(initTimeoutHandle);
  });
  
  // Update OpenTelemetry context (initialization already done in main.ts)
  try {
    // Set App component context
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
    
    // Create test trace for telemetry verification
    const testSpan = openTelemetryService.createSpan('app_initialization', {
      'app.version': process.env.VUE_APP_VERSION || '1.0.0',
      'app.environment': process.env.NODE_ENV || 'development',
      'test.trace': true
    })
    
    if (testSpan) {
      testSpan.addEvent('Application started successfully')
      testSpan.end()
      console.log('🧪 Test trace sent to telemetry system')
    }
    
  } catch (error) {
    console.error('❌ Failed to update OpenTelemetry context:', error)
    // Don't block app startup if telemetry fails
  }
});

onUnmounted(() => {
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
    <!-- Loading Screen -->
    <LoadingScreen 
      v-if="showLoadingScreen"
      initial-message="🚀 Initializing AetherTerm services..."
      :timeout="30000"
      @timeout="handleInitializationTimeout"
    />

    <!-- Timeout Screen -->
    <TimeoutScreen 
      v-if="showTimeoutScreen"
      :error-message="initializationError || ''"
      :server-url="socketManager.getConnectionState().value.serverUrl || ''"
      :timestamp="new Date()"
      :duration="30000"
      @retry="retryInitialization"
      @reload="handleReload"
      @continue="handleInitializationComplete"
    />

    <!-- Error Screen Overlay -->
    <ErrorScreen 
      v-if="showErrorScreen && currentError"
      :error-type="currentError.type"
      :error-message="currentError.message"
      :error-code="currentError.code"
      :additional-info="currentError.details"
      :server-url="socketManager.getConnectionState().value.serverUrl || ''"
      :timestamp="currentError.timestamp"
      :show-retry="true"
      :auto-retry="false"
      @retry="handleRetry"
      @reload="handleReload"
    />

    <!-- Main App Content (hidden when error screen is shown) -->
    <div v-if="showMainApp" class="main-app-container">
      <!-- Main Content Area -->
      <div class="main-content">
        <!-- Session Manager Container (Full Width) -->
        <div id="workspace-container">
          <WorkspaceManager />
        </div>
      </div>

      <!-- Supervisor Control Panel (Fixed) -->
    <div
      v-if="isSupervisorPanelVisible"
      id="supervisor-container"
      class="supervisor-fixed"
      :class="{
        'resizing': isResizing
      }"
      :style="{
        width: panelWidth + 'px'
      }"
    >
      <!-- Resize Handle -->
      <div class="resize-handle-container">
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
          :class="{ 'active': activeTab === 'test' }"
          @click="activeTab = 'test'"
          class="test-tab"
        >
          🧪 New Architecture Test
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
      <div v-if="activeTab === 'test'" class="tab-content test-tab">
        <NewArchitectureTest />
      </div>
      <div v-if="activeTab === 'dev-auth'" class="tab-content dev-auth-tab">
        <DevJWTRegister />
      </div>

      <!-- Integrated Control Panel -->
      <FloatingControlPanel 
        :panel-visible="isSupervisorPanelVisible"
        :panel-width="panelWidth"
        @toggle-panel="togglePanelVisibility"
        @switch-tab="handleSwitchTab"
      />
    </div>

    
    </div> <!-- Close showMainApp div -->
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
  display: block;
}

.main-app-container {
  height: 100vh;
  display: flex;
  position: relative;
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


.supervisor-fixed {
  height: 100%;
  border-left: 1px solid #444;
  flex-shrink: 0;
  position: relative;
  min-width: 250px;
  max-width: 600px;
}

.supervisor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background-color: #1e1e1e;
  border-bottom: 1px solid #444;
  color: white;
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


</style>
