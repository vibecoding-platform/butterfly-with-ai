<template>
  <div class="simple-chat-container">
    <div class="chat-header">
      <h3>Aether Assistant</h3>
      <div class="status-info">
        <div class="ai-info" v-if="aiInfo.provider && aiInfo.provider !== 'unknown'">
          <span class="provider">{{ aiInfo.provider }}</span>
          <span class="model" v-if="aiInfo.model && aiInfo.model !== 'unknown'">{{
            aiInfo.model
          }}</span>
        </div>
        <div
          class="connection-status"
          :class="{ connected: terminalStore.connectionState.isConnected && aiInfo.available }"
        >
          {{ getConnectionStatus() }}
        </div>
      </div>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div v-for="message in messages" :key="message.id" class="message" :class="message.type">
        <div class="message-header">
          <span class="username">{{ message.username }}</span>
          <span class="timestamp">{{ formatTime(message.timestamp) }}</span>
        </div>
        <div class="message-content">
          <span v-if="message.streaming" class="streaming-content"
            >{{ message.content }}<span class="cursor">|</span></span
          >
          <span v-else>{{ message.content }}</span>
        </div>
      </div>

      <!-- AI Typing Indicator -->
      <div v-if="isAITyping" class="ai-typing">
        <div class="typing-indicator">
          <span class="username">Aether AI</span>
          <div class="typing-dots"><span></span><span></span><span></span></div>
        </div>
      </div>

      <div v-if="messages.length === 0" class="no-messages">
        <p>No messages yet. Start a conversation with Aether AI!</p>
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
    streaming?: boolean
    messageId?: string
  }

  const terminalStore = useAetherTerminalServiceStore()
  const messages = ref<ChatMessage[]>([])
  const newMessage = ref('')
  const messagesContainer = ref<HTMLElement | null>(null)
  const messageTextarea = ref<HTMLTextAreaElement | null>(null)

  interface AIInfo {
    provider: string
    model: string
    available: boolean
    status: string
    error?: string
  }

  const aiInfo = ref<AIInfo>({
    provider: 'unknown',
    model: 'unknown',
    available: false,
    status: 'disconnected',
  })

  const addMessage = (
    username: string,
    content: string,
    type: 'user' | 'system' | 'ai' = 'user'
  ): ChatMessage => {
    const message: ChatMessage = {
      id: Date.now().toString(),
      username,
      content,
      timestamp: new Date(),
      type,
    }

    messages.value.push(message)

    // Auto-scroll to bottom
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })

    return message
  }

  const sendMessage = () => {
    if (!newMessage.value.trim() || !terminalStore.connectionState.isConnected) return

    const userMessage = newMessage.value.trim()

    // Add user message to local display
    addMessage('You', userMessage, 'user')

    // Send to AI for response
    sendAIMessage(userMessage)

    newMessage.value = ''

    // Focus back to textarea
    nextTick(() => {
      messageTextarea.value?.focus()
    })
  }

  const isAITyping = ref(false)
  const currentAIMessageId = ref('')

  const sendAIMessage = async (userMessage: string) => {
    if (!terminalStore.socket || !terminalStore.connectionState.isConnected) {
      console.warn('Socket not available for AI chat')
      return
    }

    // Generate unique message ID
    const messageId = Date.now().toString() + Math.random().toString(36).substr(2, 9)
    currentAIMessageId.value = messageId

    // Create placeholder AI message
    const aiMessage = addMessage('Aether AI', '', 'ai')
    aiMessage.streaming = true
    aiMessage.messageId = messageId

    isAITyping.value = true

    // Send to AI service with terminal context
    terminalStore.socket.emit('ai_chat_message', {
      message: userMessage,
      message_id: messageId,
      terminal_session: terminalStore.session.id,
    })
  }

  // Handle AI streaming responses
  onMounted(() => {
    // Add welcome message
    addMessage(
      'Aether AI',
      'Welcome to Aether Assistant! I am your AI assistant for terminal operations, troubleshooting, and guidance.',
      'system'
    )

    // Listen for chat messages from socket
    terminalStore.onChatMessage((data: any) => {
      console.log('Received chat message:', data)
      addMessage(data.username || 'Unknown User', data.message || data.content, 'user')
    })

    // Set up AI Event Listeners when socket becomes available
    const setupAIListeners = () => {
      if (!terminalStore.socket) return

      // Remove existing listeners first to prevent duplicates
      terminalStore.socket.off('ai_chat_typing')
      terminalStore.socket.off('ai_chat_chunk')
      terminalStore.socket.off('ai_chat_complete')
      terminalStore.socket.off('ai_chat_error')
      terminalStore.socket.off('ai_info_response')

      // AI typing indicator
      terminalStore.socket.on('ai_chat_typing', (data: any) => {
        isAITyping.value = data.typing
      })

      // AI response chunks
      terminalStore.socket.on('ai_chat_chunk', (data: any) => {
        const messageId = data.message_id
        const chunk = data.chunk

        // Find the AI message and append chunk
        const aiMessage = messages.value.find((m) => m.messageId === messageId)
        if (aiMessage) {
          aiMessage.content += chunk

          // Auto-scroll to bottom
          nextTick(() => {
            if (messagesContainer.value) {
              messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
            }
          })
        }
      })

      // AI response complete
      terminalStore.socket.on('ai_chat_complete', (data: any) => {
        const messageId = data.message_id
        const fullResponse = data.full_response

        // Find the AI message and finalize
        const aiMessage = messages.value.find((m) => m.messageId === messageId)
        if (aiMessage) {
          aiMessage.content = fullResponse
          aiMessage.streaming = false
        }

        isAITyping.value = false
        currentAIMessageId.value = ''
      })

      // AI error handling
      terminalStore.socket.on('ai_chat_error', (data: any) => {
        const messageId = data.message_id
        const error = data.error

        // Find the AI message and show error
        const aiMessage = messages.value.find((m) => m.messageId === messageId)
        if (aiMessage) {
          aiMessage.content = `Sorry, I encountered an error: ${error}`
          aiMessage.streaming = false
          aiMessage.type = 'system' // Mark as system message for error styling
        }

        isAITyping.value = false
        currentAIMessageId.value = ''
      })

      // AI info response
      terminalStore.socket.on('ai_info_response', (data: any) => {
        aiInfo.value = {
          provider: data.provider || 'unknown',
          model: data.model || 'unknown',
          available: data.available || false,
          status: data.status || 'disconnected',
          error: data.error,
        }

        console.log('AI Info received:', aiInfo.value)
      })
    }

    // Try to setup listeners immediately
    setupAIListeners()

    // Watch for connection state changes without using $subscribe
    let isListenersSetup = false
    const watchConnection = () => {
      if (terminalStore.connectionState.isConnected && terminalStore.socket && !isListenersSetup) {
        setupAIListeners()
        requestAIInfo() // Request AI info when connection is established
        isListenersSetup = true
      }
    }

    // Set up a simple interval check instead of reactive subscription
    const connectionWatcher = setInterval(watchConnection, 1000)

    // Clean up on unmount
    onUnmounted(() => {
      clearInterval(connectionWatcher)
      terminalStore.offChatMessage()

      // Clean up socket listeners
      if (terminalStore.socket) {
        terminalStore.socket.off('ai_chat_typing')
        terminalStore.socket.off('ai_chat_chunk')
        terminalStore.socket.off('ai_chat_complete')
        terminalStore.socket.off('ai_chat_error')
        terminalStore.socket.off('ai_info_response')
      }
    })
  })

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const getConnectionStatus = () => {
    if (!terminalStore.connectionState.isConnected) {
      return 'Terminal Disconnected'
    }
    if (!aiInfo.value.available) {
      return 'AI Unavailable'
    }
    return 'Connected'
  }

  const requestAIInfo = () => {
    if (terminalStore.socket && terminalStore.connectionState.isConnected) {
      terminalStore.socket.emit('ai_get_info', {})
    }
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

  .status-info {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
  }

  .ai-info {
    display: flex;
    gap: 6px;
    font-size: 11px;
    color: #888;
  }

  .ai-info .provider {
    background-color: #424242;
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: bold;
    text-transform: uppercase;
  }

  .ai-info .model {
    background-color: #616161;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: monospace;
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

  /* AI Typing Indicator */
  .ai-typing {
    padding: 15px;
    margin-bottom: 10px;
  }

  .typing-indicator {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .typing-indicator .username {
    font-weight: bold;
    color: #4caf50;
    font-size: 14px;
  }

  .typing-dots {
    display: flex;
    gap: 4px;
  }

  .typing-dots span {
    width: 6px;
    height: 6px;
    background-color: #4caf50;
    border-radius: 50%;
    opacity: 0.4;
    animation: typing 1.4s infinite;
  }

  .typing-dots span:nth-child(1) {
    animation-delay: 0s;
  }

  .typing-dots span:nth-child(2) {
    animation-delay: 0.2s;
  }

  .typing-dots span:nth-child(3) {
    animation-delay: 0.4s;
  }

  @keyframes typing {
    0%,
    60%,
    100% {
      opacity: 0.4;
      transform: translateY(0);
    }
    30% {
      opacity: 1;
      transform: translateY(-4px);
    }
  }

  /* Streaming Content */
  .streaming-content {
    position: relative;
  }

  .streaming-content .cursor {
    color: #4caf50;
    animation: blink 1s infinite;
    font-weight: bold;
  }

  @keyframes blink {
    0%,
    50% {
      opacity: 1;
    }
    51%,
    100% {
      opacity: 0;
    }
  }

  /* Enhanced AI message styling */
  .message.ai {
    background-color: #1976d2;
    border-left: 4px solid #4caf50;
  }

  .message.ai .username {
    color: #4caf50;
  }

  /* Enhanced system message styling */
  .message.system {
    background-color: #424242;
    border-left: 4px solid #ff9800;
  }

  .message.system .username {
    color: #ff9800;
  }
</style>
