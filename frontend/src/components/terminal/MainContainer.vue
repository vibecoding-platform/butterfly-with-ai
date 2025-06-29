<template>
  <div class="main-container" @contextmenu.prevent>
    <!-- Tab Bar -->
    <TerminalTabBar />

    <!-- Main Content Area -->
    <MainContentView 
      :is-terminal-paused="isTerminalPaused"
      :is-supervisor-locked="isSupervisorLocked"
      @terminal-initialized="onTerminalInitialized"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAetherTerminalServiceStore } from '../../stores/aetherTerminalServiceStore'
import TerminalTabBar from '../TabBarContainer.vue'
import MainContentView from '../MainContentView.vue'

const terminalStore = useAetherTerminalServiceStore()

// Terminal pause state
const isTerminalPaused = ref(false)

const isSupervisorLocked = computed(() => {
  return terminalStore.isSupervisorLocked
})

// Terminal pause/resume functions
const resumeTerminal = () => {
  isTerminalPaused.value = false
}

// Expose pause function globally (can be called from other components)
const pauseTerminal = () => {
  isTerminalPaused.value = true
}

const onTerminalInitialized = () => {
  console.log('Terminal initialized in container')
}

onMounted(async () => {
  console.log('MainContainer mounted')
  
  // Initialize connection after container is setup
  terminalStore.connect()
})

// Export functions for external use
defineExpose({
  pauseTerminal,
  resumeTerminal
})
</script>

<style scoped lang="scss">
@import '../../assets/styles/base.scss';

.main-container {
  @include terminal-container;
  position: relative;
}
</style>