<template>
  <div class="ai-agent-tab-container">
    <SimpleChatComponent :tab-id="tabId" />
  </div>
</template>

<script setup lang="ts">
import SimpleChatComponent from '../SimpleChatComponent.vue'

interface Props {
  tabId: string
}

defineProps<Props>()
</script>

<style scoped lang="scss">
@import '../../assets/styles/base.scss';

.ai-agent-tab-container {
  @include flex-column;
  flex: 1;
  overflow: hidden;
}
</style>