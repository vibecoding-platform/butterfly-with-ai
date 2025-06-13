<template>
  <div class="chat-container">
    <vue-advanced-chat
      :current-user-id="currentUserId"
      :rooms="rooms"
      :messages="messages"
      :messages-loaded="messagesLoaded"
      :room-id="roomId"
      @send-message="sendMessage"
      @fetch-messages="fetchMessages"
      @fetch-more-messages="fetchMoreMessages"
      @add-room="addRoom"
      @room-action-handler="roomActionHandler"
      @message-action-handler="messageActionHandler"
      @menu-action-handler="menuActionHandler"
      @message-selection-action-handler="messageSelectionActionHandler"
      @typing-message="typingMessage"
      @textarea-action-handler="textareaActionHandler"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useAetherTerminalServiceStore } from '../stores/aetherTerminalServiceStore'
import { useChatStore } from '../stores/chatStore'

// Store integration
const terminalStore = useAetherTerminalServiceStore()
const chatStore = useChatStore()

// Chat state
const currentUserId = ref('1')
const roomId = ref('1')
const messagesLoaded = ref(false)

// Sample data - you can replace this with real data from your backend
const rooms = ref([
  {
    roomId: '1',
    roomName: 'General Chat',
    avatar: '',
    unreadCount: 0,
    index: 0,
    lastMessage: {
      content: 'Welcome to the chat!',
      timestamp: new Date().toISOString(),
      saved: true,
      distributed: true,
      seen: true,
      new: false
    },
    users: [
      {
        _id: '1',
        username: 'User 1',
        avatar: '',
        status: {
          state: 'online',
          lastChanged: new Date().toISOString()
        }
      },
      {
        _id: '2',
        username: 'User 2',
        avatar: '',
        status: {
          state: 'online',
          lastChanged: new Date().toISOString()
        }
      }
    ]
  }
])

const messages = ref([
  {
    _id: '1',
    content: 'Welcome to vue-advanced-chat!',
    senderId: '2',
    username: 'System',
    avatar: '',
    date: new Date().toISOString().split('T')[0],
    timestamp: new Date().toISOString(),
    system: false,
    saved: true,
    distributed: true,
    seen: true,
    deleted: false
  }
])

// Event handlers
const sendMessage = (message: any) => {
  console.log('Send message:', message)
  
  // Add the message to the messages array
  const newMessage = {
    _id: Date.now().toString(),
    content: message.content,
    senderId: currentUserId.value,
    username: 'You',
    avatar: '',
    date: new Date().toISOString().split('T')[0],
    timestamp: new Date().toISOString(),
    system: false,
    saved: true,
    distributed: true,
    seen: true,
    deleted: false,
    files: message.files || []
  }
  
  messages.value.push(newMessage)
  
  // Send the message via terminal store
  terminalStore.sendChatMessage({
    id: newMessage._id,
    content: newMessage.content,
    senderId: newMessage.senderId,
    username: newMessage.username,
    timestamp: newMessage.timestamp,
    roomId: roomId.value
  })
}

const fetchMessages = ({ room, options }: any) => {
  console.log('Fetch messages for room:', room.roomId)
  messagesLoaded.value = true
}

const fetchMoreMessages = ({ room, options }: any) => {
  console.log('Fetch more messages for room:', room.roomId)
}

const addRoom = () => {
  console.log('Add room')
}

const roomActionHandler = ({ action, roomId }: any) => {
  console.log('Room action:', action, roomId)
}

const messageActionHandler = ({ action, message, roomId }: any) => {
  console.log('Message action:', action, message, roomId)
}

const menuActionHandler = ({ action, message, roomId }: any) => {
  console.log('Menu action:', action, message, roomId)
}

const messageSelectionActionHandler = ({ action, messages, roomId }: any) => {
  console.log('Message selection action:', action, messages, roomId)
}

const typingMessage = ({ message, roomId }: any) => {
  console.log('Typing message:', message, roomId)
}

const textareaActionHandler = ({ message, roomId }: any) => {
  console.log('Textarea action:', message, roomId)
}

onMounted(() => {
  // Listen for chat messages via terminal store
  terminalStore.onChatMessage((data: any) => {
    console.log('Received chat message:', data);
    const newMessage = {
      _id: data.id || Date.now().toString(),
      content: data.content,
      senderId: data.senderId,
      username: data.username || 'Unknown',
      avatar: data.avatar || '',
      date: new Date().toISOString().split('T')[0],
      timestamp: data.timestamp || new Date().toISOString(),
      system: false,
      saved: true,
      distributed: true,
      seen: true,
      deleted: false
    };
    messages.value.push(newMessage);
  });
  
  // Initialize chat data
  messagesLoaded.value = true
})

onUnmounted(() => {
  // Clean up chat message listener
  terminalStore.offChatMessage();
})
</script>

<style scoped>
.chat-container {
  height: 100%;
  width: 100%;
}
</style>