<template>
  <div class="simple-chat-container">
    <div class="chat-header">
      <h3>Terminal Chat</h3>
      <div class="connection-status" :class="{ connected: terminalStore.connectionState.isConnected }">
        {{ terminalStore.connectionState.isConnected ? 'Connected' : 'Disconnected' }}
      </div>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div v-for="message in messages" :key="message.id" class="message" :class="message.type">
        <div class="message-header">
          <span class="username">{{ message.username }}</span>
          <span class="timestamp">{{ formatTime(message.timestamp) }}</span>
        </div>
        <div class="message-content">{{ message.content }}</div>
      </div>
      
      <div v-if="messages.length === 0" class="no-messages">
        <p>No messages yet. Start a conversation!</p>
      </div>
    </div>

    <div class="chat-input">
      <textarea
        v-model="newMessage"
        @keydown.ctrl.enter="sendMessage"
        @keydown.meta.enter="sendMessage"
        placeholder="Type a message... (Ctrl+Enter to send)"
        :disabled="!terminalStore.connectionState.isConnected"
        class="message-input"
        rows="3"
        ref="messageTextarea"
      ></textarea>
      <div class="input-actions">
        <div class="input-help">
          <small>Ctrl+Enter to send</small>
        </div>
        <button 
          @click="sendMessage" 
          :disabled="!newMessage.trim() || !terminalStore.connectionState.isConnected"
          class="send-button"
        >
          Send
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useAetherTerminalServiceStore } from '../stores/aetherTerminalServiceStore'

interface ChatMessage {
  id: string
  username: string
  content: string
  timestamp: Date
  type: 'user' | 'system' | 'ai'
}

const terminalStore = useAetherTerminalServiceStore()
const messages = ref<ChatMessage[]>([])
const newMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const messageTextarea = ref<HTMLTextAreaElement | null>(null)

// Add welcome message
onMounted(() => {
  addMessage('System AI', 'Welcome to Terminal Chat! I am your System AI assistant. I can help you with terminal operations, troubleshooting, and provide guidance.', 'system')
  
  // Listen for chat messages from socket
  terminalStore.onChatMessage((data: any) => {
    console.log('Received chat message:', data)
    addMessage(data.username || 'Unknown User', data.message || data.content, 'user')
  })
})

onUnmounted(() => {
  terminalStore.offChatMessage()
})

const addMessage = (username: string, content: string, type: 'user' | 'system' | 'ai' = 'user') => {
  const message: ChatMessage = {
    id: Date.now().toString(),
    username,
    content,
    timestamp: new Date(),
    type
  }
  
  messages.value.push(message)
  
  // Auto-scroll to bottom
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const sendMessage = () => {
  if (!newMessage.value.trim() || !terminalStore.connectionState.isConnected) return
  
  const message = {
    username: 'You',
    message: newMessage.value.trim(),
    timestamp: new Date().toISOString()
  }
  
  // Add to local messages immediately
  addMessage(message.username, message.message, 'user')
  
  // Send via socket
  terminalStore.sendChatMessage(message)
  
  newMessage.value = ''
  
  // Focus back to textarea
  nextTick(() => {
    messageTextarea.value?.focus()
  })
}

const formatTime = (date: Date) => {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.simple-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #2d2d2d;
  color: #ffffff;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #444;
  background-color: #1e1e1e;
}

.chat-header h3 {
  margin: 0;
  color: #4caf50;
  font-size: 16px;
}

.connection-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
  background-color: #f44336;
  color: white;
}

.connection-status.connected {
  background-color: #4caf50;
}

.chat-messages {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
  min-height: 0; /* flexで縮小可能にする */
}

.message {
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 8px;
  background-color: #3d3d3d;
}

.message.system {
  background-color: #1976d2;
}

.message.ai {
  background-color: #9c27b0;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.username {
  font-weight: bold;
  color: #4caf50;
  font-size: 14px;
}

.timestamp {
  color: #ccc;
  font-size: 12px;
}

.message-content {
  line-height: 1.4;
  color: #e0e0e0;
}

.no-messages {
  text-align: center;
  color: #666;
  margin-top: 50px;
}

.chat-input {
  padding: 15px;
  border-top: 1px solid #444;
  background-color: #1e1e1e;
  box-sizing: border-box;
  overflow-x: hidden; /* 横スクロールを防ぐ */
}

.message-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #444;
  border-radius: 6px;
  background-color: #2d2d2d;
  color: #ffffff;
  font-size: 14px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.4;
  resize: vertical;
  min-height: 60px;
  max-height: 120px;
  box-sizing: border-box; /* パディングとボーダーを幅に含める */
}

.message-input:focus {
  outline: none;
  border-color: #4caf50;
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

.message-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.input-help {
  color: #666;
}

.input-help small {
  font-size: 12px;
}

.send-button {
  padding: 10px 24px;
  border: none;
  border-radius: 6px;
  background-color: #4caf50;
  color: white;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.send-button:hover:not(:disabled) {
  background-color: #45a049;
  transform: translateY(-1px);
}

.send-button:disabled {
  background-color: #666;
  cursor: not-allowed;
  transform: none;
}

/* Scrollbar styling */
.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #666;
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #888;
}
</style>