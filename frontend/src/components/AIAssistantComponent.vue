<template>
  <div class="ai-assistant">
    <!-- AI Assistant Header -->
    <div class="ai-header">
      <div class="ai-info">
        <div class="ai-avatar">🤖</div>
        <div class="ai-details">
          <h3>{{ tab.title }}</h3>
          <span class="ai-type">{{ assistantTypeLabel }}</span>
        </div>
      </div>
      <div class="ai-status">
        <span class="status-indicator" :class="connectionStatus">
          {{ connectionStatusText }}
        </span>
      </div>
    </div>

    <!-- Conversation History -->
    <div class="conversation-area" ref="conversationArea">
      <div 
        v-for="(message, index) in (tab.conversationHistory || [])" 
        :key="index"
        class="message"
        :class="message.role"
      >
        <div class="message-avatar">
          <span v-if="message.role === 'user'">👤</span>
          <span v-else>🤖</span>
        </div>
        <div class="message-content">
          <div class="message-text">{{ message.content }}</div>
          <div class="message-time">{{ formatTime(message.timestamp) }}</div>
        </div>
      </div>
      
      <!-- Empty state -->
      <div v-if="(tab.conversationHistory || []).length === 0" class="empty-conversation">
        <div class="welcome-ai">
          <h4>{{ assistantWelcomeTitle }}</h4>
          <p>{{ assistantWelcomeMessage }}</p>
          <div class="quick-actions">
            <button 
              v-for="action in quickActions" 
              :key="action.text"
              @click="sendQuickAction(action.text)"
              class="quick-action-btn"
            >
              {{ action.icon }} {{ action.text }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="input-area">
      <div class="input-container">
        <textarea
          v-model="currentMessage"
          @keydown.enter.prevent="handleEnterKey"
          @keydown.ctrl.enter="sendMessage"
          placeholder="Type your message... (Ctrl+Enter to send)"
          class="message-input"
          ref="messageInput"
          rows="1"
        ></textarea>
        <button 
          @click="sendMessage" 
          :disabled="!currentMessage.trim() || isSending"
          class="send-btn"
        >
          <span v-if="isSending">⏳</span>
          <span v-else>📤</span>
        </button>
      </div>
      
      <!-- Context Information -->
      <div v-if="tab.contextSessionId" class="context-info">
        <span class="context-label">Context:</span>
        <span class="context-session">Session {{ tab.contextSessionId }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, nextTick, onMounted } from 'vue'
import type { AIAssistantTab } from '@/types/session'

interface Props {
  tab: AIAssistantTab
  sessionId: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface QuickAction {
  icon: string
  text: string
}

const props = defineProps<Props>()

// Reactive state
const currentMessage = ref('')
const isSending = ref(false)
const connectionStatus = ref<'connected' | 'connecting' | 'disconnected'>('connected')
const conversationArea = ref<HTMLElement>()
const messageInput = ref<HTMLTextAreaElement>()

// Computed properties
const assistantTypeLabel = computed(() => {
  const labels = {
    code: 'Code Assistant',
    operations: 'Operations Assistant',
    general: 'General Assistant'
  }
  return labels[props.tab.assistantType]
})

const connectionStatusText = computed(() => {
  const texts = {
    connected: 'Online',
    connecting: 'Connecting...',
    disconnected: 'Offline'
  }
  return texts[connectionStatus.value]
})

const assistantWelcomeTitle = computed(() => {
  const titles = {
    code: 'Ready to help with your code!',
    operations: 'Ready to assist with operations!',
    general: 'How can I help you today?'
  }
  return titles[props.tab.assistantType]
})

const assistantWelcomeMessage = computed(() => {
  const messages = {
    code: 'I can help you with code review, debugging, refactoring, and more.',
    operations: 'I can assist with system administration, monitoring, and DevOps tasks.',
    general: 'Ask me anything! I can help with various tasks and questions.'
  }
  return messages[props.tab.assistantType]
})

const quickActions = computed((): QuickAction[] => {
  const actions = {
    code: [
      { icon: '🔍', text: 'Review current code' },
      { icon: '🐛', text: 'Help debug an issue' },
      { icon: '⚡', text: 'Optimize performance' },
      { icon: '📝', text: 'Generate documentation' }
    ],
    operations: [
      { icon: '📊', text: 'Check system status' },
      { icon: '🔧', text: 'Troubleshoot issue' },
      { icon: '📋', text: 'Create deployment plan' },
      { icon: '🛡️', text: 'Security analysis' }
    ],
    general: [
      { icon: '💡', text: 'Give me suggestions' },
      { icon: '📚', text: 'Explain a concept' },
      { icon: '🎯', text: 'Help me plan' },
      { icon: '🤔', text: 'Answer a question' }
    ]
  }
  return actions[props.tab.assistantType]
})

// Message handling
const sendMessage = async () => {
  if (!currentMessage.value.trim() || isSending.value) return

  const message = currentMessage.value.trim()
  currentMessage.value = ''
  isSending.value = true

  // Add user message to conversation
  const userMessage: Message = {
    role: 'user',
    content: message,
    timestamp: new Date()
  }
  
  if (!props.tab.conversationHistory) props.tab.conversationHistory = []
  props.tab.conversationHistory.push(userMessage)
  await scrollToBottom()

  try {
    // TODO: Send message to AI service
    // For now, simulate AI response
    setTimeout(async () => {
      const aiResponse: Message = {
        role: 'assistant',
        content: generateMockResponse(message),
        timestamp: new Date()
      }
      
      if (!props.tab.conversationHistory) props.tab.conversationHistory = []
      props.tab.conversationHistory.push(aiResponse)
      await scrollToBottom()
      isSending.value = false
    }, 1000)
    
  } catch (error) {
    console.error('Failed to send message:', error)
    isSending.value = false
  }
}

const sendQuickAction = (actionText: string) => {
  currentMessage.value = actionText
  sendMessage()
}

const handleEnterKey = (event: KeyboardEvent) => {
  if (event.ctrlKey) {
    sendMessage()
  } else {
    // Allow normal enter for new lines
    return
  }
}

// Mock AI response generator
const generateMockResponse = (message: string): string => {
  const responses = {
    code: [
      "I'd be happy to help with your code! Could you share the specific code you'd like me to review?",
      "For debugging, let's start by understanding the issue. What error are you encountering?",
      "To optimize performance, I'll need to see the code. Can you share the relevant sections?",
      "I can help generate documentation. What part of your codebase needs documentation?"
    ],
    operations: [
      "I can help check your system status. What specific metrics or services would you like me to monitor?",
      "For troubleshooting, let's gather some information first. What symptoms are you observing?",
      "I'll help create a deployment plan. What application or service are you planning to deploy?",
      "For security analysis, what specific area would you like me to focus on?"
    ],
    general: [
      "I'm here to help! Could you provide more details about what you'd like assistance with?",
      "That's an interesting question. Let me provide you with a comprehensive explanation.",
      "I'd be glad to help you plan. What's the goal you're trying to achieve?",
      "Great question! Let me break this down for you step by step."
    ]
  }
  
  const typeResponses = responses[props.tab.assistantType]
  return typeResponses[Math.floor(Math.random() * typeResponses.length)]
}

// Utility functions
const formatTime = (timestamp: Date): string => {
  return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const scrollToBottom = async () => {
  await nextTick()
  if (conversationArea.value) {
    conversationArea.value.scrollTop = conversationArea.value.scrollHeight
  }
}

// Focus input on mount
onMounted(() => {
  messageInput.value?.focus()
})
</script>

<style scoped>
.ai-assistant {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #1e1e1e;
}

.ai-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background-color: #2d2d2d;
  border-bottom: 1px solid #444;
}

.ai-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ai-avatar {
  font-size: 24px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #7b1fa2;
  border-radius: 50%;
}

.ai-details h3 {
  margin: 0;
  color: #fff;
  font-size: 16px;
}

.ai-type {
  color: #9c27b0;
  font-size: 12px;
  text-transform: uppercase;
  font-weight: 500;
}

.ai-status {
  display: flex;
  align-items: center;
}

.status-indicator {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.status-indicator.connected {
  background-color: #4caf50;
  color: white;
}

.status-indicator.connecting {
  background-color: #ff9800;
  color: white;
}

.status-indicator.disconnected {
  background-color: #f44336;
  color: white;
}

.conversation-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 80%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-avatar {
  font-size: 20px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background-color: #2196f3;
}

.message.assistant .message-avatar {
  background-color: #7b1fa2;
}

.message-content {
  flex: 1;
}

.message-text {
  background-color: #2d2d2d;
  padding: 12px 16px;
  border-radius: 16px;
  color: #fff;
  line-height: 1.4;
}

.message.user .message-text {
  background-color: #2196f3;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-text {
  background-color: #7b1fa2;
  border-bottom-left-radius: 4px;
}

.message-time {
  font-size: 11px;
  color: #888;
  margin-top: 4px;
  text-align: right;
}

.message.assistant .message-time {
  text-align: left;
}

.empty-conversation {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.welcome-ai {
  text-align: center;
  color: #ccc;
  max-width: 400px;
}

.welcome-ai h4 {
  color: #9c27b0;
  margin-bottom: 8px;
  font-size: 18px;
}

.welcome-ai p {
  margin-bottom: 20px;
  font-size: 14px;
  line-height: 1.5;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.quick-action-btn {
  background-color: #3d3d3d;
  color: #ccc;
  border: 1px solid #555;
  padding: 8px 12px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s ease;
}

.quick-action-btn:hover {
  background-color: #7b1fa2;
  color: white;
  border-color: #9c27b0;
}

.input-area {
  padding: 16px;
  background-color: #2d2d2d;
  border-top: 1px solid #444;
}

.input-container {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.message-input {
  flex: 1;
  background-color: #1e1e1e;
  border: 1px solid #555;
  border-radius: 20px;
  padding: 12px 16px;
  color: #fff;
  font-size: 14px;
  resize: none;
  min-height: 20px;
  max-height: 120px;
  overflow-y: auto;
}

.message-input:focus {
  outline: none;
  border-color: #9c27b0;
}

.message-input::placeholder {
  color: #888;
}

.send-btn {
  background-color: #7b1fa2;
  color: white;
  border: none;
  border-radius: 50%;
  width: 44px;
  height: 44px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: background-color 0.2s ease;
}

.send-btn:hover:not(:disabled) {
  background-color: #9c27b0;
}

.send-btn:disabled {
  background-color: #555;
  cursor: not-allowed;
}

.context-info {
  margin-top: 8px;
  font-size: 12px;
  color: #888;
}

.context-label {
  font-weight: 500;
}

.context-session {
  color: #9c27b0;
  margin-left: 4px;
}

/* Scrollbar styling */
.conversation-area::-webkit-scrollbar {
  width: 6px;
}

.conversation-area::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.conversation-area::-webkit-scrollbar-thumb {
  background: #666;
  border-radius: 3px;
}

.conversation-area::-webkit-scrollbar-thumb:hover {
  background: #888;
}
</style>