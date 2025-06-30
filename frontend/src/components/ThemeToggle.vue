<template>
  <div class="theme-toggle">
    <!-- Quick theme mode toggle -->
    <v-btn-toggle
      v-model="themeMode"
      mandatory
      variant="outlined"
      density="compact"
      class="mr-2"
    >
      <v-btn value="light" size="small" icon>
        <v-icon>mdi-white-balance-sunny</v-icon>
        <v-tooltip activator="parent" location="bottom">Light Mode</v-tooltip>
      </v-btn>
      <v-btn value="dark" size="small" icon>
        <v-icon>mdi-moon-waning-crescent</v-icon>
        <v-tooltip activator="parent" location="bottom">Dark Mode</v-tooltip>
      </v-btn>
      <v-btn value="auto" size="small" icon>
        <v-icon>mdi-brightness-auto</v-icon>
        <v-tooltip activator="parent" location="bottom">Auto Mode</v-tooltip>
      </v-btn>
    </v-btn-toggle>

    <!-- Theme settings button -->
    <v-btn
      icon="mdi-palette"
      variant="outlined"
      density="compact"
      size="small"
      @click="showSettings = true"
    >
      <v-tooltip activator="parent" location="bottom">Theme Settings</v-tooltip>
    </v-btn>

    <!-- Theme settings dialog -->
    <v-dialog v-model="showSettings" max-width="600">
      <ThemeSelector @close="showSettings = false" />
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTheme } from '@/composables/useTheme'
import ThemeSelector from './ThemeSelector.vue'

const { config, setDarkMode, setLightMode, setAutoMode } = useTheme()
const showSettings = ref(false)

const themeMode = computed({
  get: () => config.value.mode,
  set: (value: 'light' | 'dark' | 'auto') => {
    switch (value) {
      case 'light': setLightMode(); break
      case 'dark': setDarkMode(); break
      case 'auto': setAutoMode(); break
    }
  }
})
</script>

<style scoped>
.theme-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>