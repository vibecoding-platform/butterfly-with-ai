<template>
  <v-card class="theme-selector">
    <v-card-title>
      <v-icon class="mr-2">mdi-palette</v-icon>
      Theme Settings
    </v-card-title>
    
    <v-card-text>
      <!-- Theme Mode -->
      <v-row class="mb-4">
        <v-col cols="12">
          <v-label class="text-subtitle-2 mb-2">Theme Mode</v-label>
          <v-btn-toggle
            v-model="selectedMode"
            mandatory
            variant="outlined"
            divided
            class="w-100"
          >
            <v-btn value="light" size="small">
              <v-icon>mdi-white-balance-sunny</v-icon>
              <span class="ml-1">Light</span>
            </v-btn>
            <v-btn value="dark" size="small">
              <v-icon>mdi-moon-waning-crescent</v-icon>
              <span class="ml-1">Dark</span>
            </v-btn>
            <v-btn value="auto" size="small">
              <v-icon>mdi-brightness-auto</v-icon>
              <span class="ml-1">Auto</span>
            </v-btn>
          </v-btn-toggle>
        </v-col>
      </v-row>

      <!-- Color Scheme -->
      <v-row class="mb-4">
        <v-col cols="12">
          <v-label class="text-subtitle-2 mb-2">Color Scheme</v-label>
          <v-select
            v-model="selectedScheme"
            :items="schemeOptions"
            item-title="name"
            item-value="value"
            variant="outlined"
            density="compact"
          >
            <template #item="{ props, item }">
              <v-list-item v-bind="props">
                <template #prepend>
                  <div class="color-preview mr-3">
                    <div 
                      class="color-preview-bg"
                      :style="{ backgroundColor: item.raw.preview.background }"
                    >
                      <div 
                        class="color-preview-text"
                        :style="{ color: item.raw.preview.foreground }"
                      >
                        Aa
                      </div>
                    </div>
                  </div>
                </template>
              </v-list-item>
            </template>
          </v-select>
        </v-col>
      </v-row>

      <!-- Font Settings -->
      <v-row class="mb-4">
        <v-col cols="12">
          <v-label class="text-subtitle-2 mb-2">Font Settings</v-label>
        </v-col>
        <v-col cols="12" md="6">
          <v-select
            v-model="selectedFont"
            :items="fontOptions"
            label="Font Family"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="fontSize"
            label="Font Size"
            type="number"
            min="8"
            max="72"
            variant="outlined"
            density="compact"
            suffix="px"
          />
        </v-col>
      </v-row>

      <!-- Terminal Preview -->
      <v-row class="mb-4">
        <v-col cols="12">
          <v-label class="text-subtitle-2 mb-2">Preview</v-label>
          <div class="terminal-preview" :style="previewStyle">
            <div class="terminal-line">
              <span class="terminal-prompt">user@aetherterm:~$</span>
              <span class="terminal-command">ls -la</span>
            </div>
            <div class="terminal-line">
              <span class="terminal-output">drwxr-xr-x 10 user user 4096 Jan 01 12:00</span>
              <span class="terminal-filename">.</span>
            </div>
            <div class="terminal-line">
              <span class="terminal-output">-rw-r--r--  1 user user  123 Jan 01 12:00</span>
              <span class="terminal-filename">example.txt</span>
            </div>
            <div class="terminal-line">
              <span class="terminal-cursor">█</span>
            </div>
          </div>
        </v-col>
      </v-row>

      <!-- Actions -->
      <v-row>
        <v-col cols="12">
          <v-btn
            @click="resetTheme"
            variant="outlined"
            size="small"
            class="mr-2"
          >
            Reset to Default
          </v-btn>
          <v-btn
            @click="exportTheme"
            variant="outlined"
            size="small"
            class="mr-2"
          >
            Export
          </v-btn>
          <v-btn
            @click="showImportDialog = true"
            variant="outlined"
            size="small"
          >
            Import
          </v-btn>
        </v-col>
      </v-row>
    </v-card-text>

    <!-- Import Dialog -->
    <v-dialog v-model="showImportDialog" max-width="500">
      <v-card>
        <v-card-title>Import Theme</v-card-title>
        <v-card-text>
          <v-textarea
            v-model="importData"
            label="Paste theme JSON"
            rows="10"
            variant="outlined"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showImportDialog = false">Cancel</v-btn>
          <v-btn @click="importTheme" color="primary">Import</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useThemeStore, type ThemeMode, type ColorScheme } from '@/stores/themeStore'

const themeStore = useThemeStore()

// Local state
const showImportDialog = ref(false)
const importData = ref('')

// Computed properties bound to store
const selectedMode = computed({
  get: () => themeStore.themeConfig.mode,
  set: (value: ThemeMode) => themeStore.setThemeMode(value)
})

const selectedScheme = computed({
  get: () => themeStore.themeConfig.colorScheme,
  set: (value: ColorScheme) => themeStore.setColorScheme(value)
})

const selectedFont = computed({
  get: () => themeStore.themeConfig.fontFamily,
  set: (value: string) => themeStore.setFontFamily(value)
})

const fontSize = computed({
  get: () => themeStore.themeConfig.fontSize,
  set: (value: number) => themeStore.setFontSize(value)
})

// Options
const schemeOptions = computed(() => [
  {
    name: 'Default',
    value: 'default',
    preview: { background: '#1e1e1e', foreground: '#d4d4d4' }
  },
  {
    name: 'Solarized Dark',
    value: 'solarized-dark',
    preview: { background: '#002b36', foreground: '#839496' }
  },
  {
    name: 'Solarized Light',
    value: 'solarized-light',
    preview: { background: '#fdf6e3', foreground: '#657b83' }
  },
  {
    name: 'Dracula',
    value: 'dracula',
    preview: { background: '#282a36', foreground: '#f8f8f2' }
  },
  {
    name: 'Nord',
    value: 'nord',
    preview: { background: '#2e3440', foreground: '#d8dee9' }
  },
  {
    name: 'Monokai',
    value: 'monokai',
    preview: { background: '#272822', foreground: '#f8f8f2' }
  },
  {
    name: 'Gruvbox Dark',
    value: 'gruvbox-dark',
    preview: { background: '#282828', foreground: '#ebdbb2' }
  },
  {
    name: 'Gruvbox Light',
    value: 'gruvbox-light',
    preview: { background: '#fbf1c7', foreground: '#3c3836' }
  }
])

const fontOptions = [
  "Monaco, 'Courier New', monospace",
  "'Fira Code', 'Courier New', monospace",
  "'Source Code Pro', 'Courier New', monospace",
  "'JetBrains Mono', 'Courier New', monospace",
  "'Cascadia Code', 'Courier New', monospace",
  "'SF Mono', 'Courier New', monospace",
  "'Consolas', 'Courier New', monospace",
  "'Ubuntu Mono', 'Courier New', monospace"
]

// Preview style
const previewStyle = computed(() => {
  const colors = themeStore.currentColors
  if (!colors) return {}
  
  return {
    backgroundColor: colors.background,
    color: colors.foreground,
    fontFamily: themeStore.themeConfig.fontFamily,
    fontSize: `${themeStore.themeConfig.fontSize}px`,
    lineHeight: themeStore.themeConfig.lineHeight,
    border: `1px solid ${colors.bright_black}`,
    borderRadius: '4px',
    padding: '12px',
    fontWeight: 'normal'
  }
})

// Actions
const resetTheme = async () => {
  await themeStore.resetTheme()
}

const exportTheme = () => {
  const themeJson = JSON.stringify(themeStore.themeConfig, null, 2)
  const blob = new Blob([themeJson], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'aetherterm-theme.json'
  a.click()
  URL.revokeObjectURL(url)
}

const importTheme = async () => {
  try {
    const themeData = JSON.parse(importData.value)
    themeStore.themeConfig = { ...themeStore.themeConfig, ...themeData }
    await themeStore.saveThemeConfig()
    showImportDialog.value = false
    importData.value = ''
  } catch (error) {
    console.error('Failed to import theme:', error)
    // TODO: Show error message to user
  }
}

// Initialize theme
themeStore.loadThemeConfig()
</script>

<style scoped>
.theme-selector {
  min-width: 400px;
}

.color-preview {
  width: 32px;
  height: 20px;
  border-radius: 4px;
  overflow: hidden;
}

.color-preview-bg {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.color-preview-text {
  font-size: 12px;
  font-weight: bold;
  text-shadow: 0 0 2px rgba(0, 0, 0, 0.5);
}

.terminal-preview {
  font-family: monospace;
  white-space: pre;
  min-height: 100px;
  max-height: 150px;
  overflow: hidden;
}

.terminal-line {
  margin-bottom: 2px;
}

.terminal-prompt {
  color: var(--terminal-green, #00ff00);
}

.terminal-command {
  color: var(--terminal-foreground);
  margin-left: 8px;
}

.terminal-output {
  color: var(--terminal-bright-black, #666);
}

.terminal-filename {
  color: var(--terminal-blue, #0066ff);
  margin-left: 8px;
}

.terminal-cursor {
  color: var(--terminal-cursor, #ffffff);
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>