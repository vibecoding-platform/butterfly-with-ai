<template>
  <div
    v-if="show"
    class="selection-popup"
    :style="{ top: position.y + 'px', left: position.x + 'px' }"
    @click.stop
  >
    <div class="popup-content">
      <button class="action-btn copy-btn" @click="copyToClipboard">
        <span class="icon">📋</span>
        Copy
      </button>
      <button class="action-btn ai-btn" @click="sendToAI">
        <span class="icon">🤖</span>
        Send to AI
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  show: boolean
  position: { x: number; y: number }
  selectedText: string
}

interface Emits {
  (e: 'copy'): void
  (e: 'send-to-ai', text: string): void
  (e: 'hide'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(props.selectedText)
    console.log('Text copied to clipboard:', props.selectedText)
    emit('copy')
    emit('hide')
  } catch (err) {
    console.error('Failed to copy text to clipboard:', err)
    // Fallback for older browsers
    const textArea = document.createElement('textarea')
    textArea.value = props.selectedText
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    emit('copy')
    emit('hide')
  }
}

const sendToAI = () => {
  console.log('Sending text to AI:', props.selectedText)
  emit('send-to-ai', props.selectedText)
  emit('hide')
}
</script>

<style scoped>
.selection-popup {
  position: fixed;
  z-index: 1000;
  background: #2d2d2d;
  border: 1px solid #444;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  padding: 8px;
  min-width: 160px;
  user-select: none;
}

.popup-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  color: #ffffff;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.2s ease;
  font-size: 14px;
  text-align: left;
  white-space: nowrap;
}

.action-btn:hover {
  background: #404040;
}

.action-btn:active {
  background: #505050;
}

.copy-btn:hover {
  background: #1e7e34;
}

.ai-btn:hover {
  background: #0056b3;
}

.icon {
  font-size: 16px;
  line-height: 1;
}
</style>