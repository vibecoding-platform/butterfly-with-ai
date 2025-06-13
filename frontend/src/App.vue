<script setup lang="ts">
import { onUnmounted, ref } from 'vue';
import AdminControlPanel from './components/AdminControlPanel.vue';
import ChatComponent from './components/ChatComponent.vue';
import TerminalComponent from './components/TerminalComponent.vue';

const showAdminPanel = ref(true);
const isAdminPanelFloating = ref(false);
const showChat = ref(true);

// Dragging functionality for floating panel
const isDragging = ref(false);
const dragOffset = ref({ x: 0, y: 0 });
const panelPosition = ref({ x: 20, y: 60 });

const startDrag = (event: MouseEvent) => {
  if (!isAdminPanelFloating.value) return;
  
  isDragging.value = true;
  const rect = (event.target as HTMLElement).closest('#admin-container')?.getBoundingClientRect();
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

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
});
</script>

<template>
  <div id="app-container">
    <!-- Main Content Area -->
    <div class="main-content">
      <!-- Terminal Container (Full Width) -->
      <div id="terminal-container">
        <TerminalComponent />
      </div>
    </div>
    
    <!-- Admin Control Panel (Fixed or Floating) -->
    <div
      v-if="showAdminPanel"
      id="admin-container"
      :class="{
        'admin-floating': isAdminPanelFloating,
        'admin-fixed': !isAdminPanelFloating,
        'dragging': isDragging
      }"
      :style="isAdminPanelFloating ? {
        top: panelPosition.y + 'px',
        right: 'auto',
        left: panelPosition.x + 'px'
      } : {}"
    >
      <div
        class="admin-header"
        @mousedown="startDrag"
        :style="{ cursor: isAdminPanelFloating ? 'move' : 'default' }"
      >
        <h3>Control Panel</h3>
        <div class="admin-controls">
          <button
            @click="isAdminPanelFloating = !isAdminPanelFloating"
            class="float-toggle-btn"
            :title="isAdminPanelFloating ? 'Dock Panel' : 'Float Panel'"
          >
            {{ isAdminPanelFloating ? '📌' : '🔓' }}
          </button>
          <button @click="showAdminPanel = false" class="close-btn">×</button>
        </div>
      </div>
      
      <!-- Admin Control Panel Content -->
      <div class="admin-content">
        <AdminControlPanel />
      </div>
      
      <!-- Chat Container (Bottom of Control Panel) -->
      <div v-if="showChat" id="chat-container">
        <div class="chat-header">
          <h3>Chat</h3>
          <button @click="showChat = false" class="close-btn">×</button>
        </div>
        <div class="chat-content">
          <ChatComponent />
        </div>
      </div>
    </div>
    
    <!-- Control Buttons -->
    <div class="control-buttons">
      <button
        v-if="!showAdminPanel"
        @click="showAdminPanel = true"
        class="control-btn admin-btn"
      >
        Admin
      </button>
      <button
        v-if="!showChat"
        @click="showChat = true"
        class="control-btn chat-btn"
      >
        Chat
      </button>
    </div>
  </div>
</template>

<style>
html, body, #app {
  height: 100%;
  margin: 0;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

#app-container {
  height: 100%;
  position: relative;
  display: flex;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
}

#terminal-container {
  flex: 1;
  overflow: hidden;
  background-color: #1e1e1e;
}

#chat-container {
  background-color: #f9f9f9;
  border-top: 1px solid #444;
  display: flex;
  flex-direction: column;
  height: 300px;
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

/* Admin Panel Styles */
#admin-container {
  background-color: #2d2d2d;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  z-index: 1000;
}

.admin-fixed {
  width: 350px;
  height: 100%;
  border-left: 1px solid #444;
  flex-shrink: 0;
}

.admin-floating {
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

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background-color: #1e1e1e;
  border-bottom: 1px solid #444;
  color: white;
  cursor: move; /* For floating panel dragging */
}

.admin-floating .admin-header {
  border-radius: 8px 8px 0 0;
}

.admin-header h3 {
  margin: 0;
  font-size: 16px;
  color: #4caf50;
}

.admin-controls {
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
  .admin-fixed {
    width: 300px;
  }
  
  .admin-floating {
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
  
  .admin-fixed {
    position: fixed;
    top: 0;
    right: 0;
    width: 100%;
    height: 100%;
    z-index: 1001;
  }
  
  .admin-floating {
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
.admin-floating .admin-header {
  user-select: none;
}

/* Scrollbar styling for admin panel */
.admin-floating {
  scrollbar-width: thin;
  scrollbar-color: #666 #2d2d2d;
}

.admin-floating::-webkit-scrollbar {
  width: 8px;
}

.admin-floating::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.admin-floating::-webkit-scrollbar-thumb {
  background: #666;
  border-radius: 4px;
}

.admin-floating::-webkit-scrollbar-thumb:hover {
  background: #888;
}
</style>

/* Draggable functionality enhancements */
.admin-floating .admin-header {
  user-select: none;
}

.admin-container.dragging {
  opacity: 0.9;
  transform: scale(1.02);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
  z-index: 1001;
}

.admin-floating.dragging {
  transition: none;
}

/* Admin content and chat content styles */
.admin-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.chat-content {
  flex: 1;
  overflow: hidden;
}

.admin-floating .admin-header {
  border-radius: 8px 8px 0 0;
}
