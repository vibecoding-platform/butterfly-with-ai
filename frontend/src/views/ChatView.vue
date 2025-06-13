<template>
  <div class="chat-view">
    <h1>Chat</h1>
    <ChatComponent />
  </div>
</template>

<script setup lang="ts">
import ChatComponent from '../components/ChatComponent.vue';
</script>

<style scoped>
.chat-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.chat-view h1 {
  margin: 0;
  padding: 1rem;
  background-color: #f5f5f5;
  border-bottom: 1px solid #ddd;
}

.chat-view .chat-container {
  flex: 1;
}
</style>