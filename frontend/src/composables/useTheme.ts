/**
 * Theme Composable - Easy theme access for any component
 * 
 * Provides a simple API for components to use theme functionality
 */

import { computed } from 'vue'
import { useThemeStore } from '@/stores/themeStore'

export function useTheme() {
  const themeStore = useThemeStore()

  // Reactive theme properties
  const isDark = computed(() => themeStore.isDarkMode)
  const colors = computed(() => themeStore.currentColors)
  const config = computed(() => themeStore.themeConfig)

  // Quick access to common colors
  const terminalColors = computed(() => ({
    background: colors.value?.background || '#1e1e1e',
    foreground: colors.value?.foreground || '#d4d4d4',
    cursor: colors.value?.cursor || '#ffffff',
    selection: colors.value?.selection || '#264f78'
  }))

  // UI colors (derived from terminal colors)
  const uiColors = computed(() => ({
    background: isDark.value ? colors.value?.background || '#1e1e1e' : '#ffffff',
    surface: isDark.value ? colors.value?.bright_black || '#333333' : '#f5f5f5',
    primary: colors.value?.blue || '#2472c8',
    text: isDark.value ? colors.value?.foreground || '#d4d4d4' : colors.value?.black || '#000000',
    textSecondary: isDark.value ? colors.value?.bright_black || '#666666' : colors.value?.bright_white || '#999999',
    border: isDark.value ? colors.value?.bright_black || '#333333' : '#e0e0e0'
  }))

  // Font settings
  const fontSettings = computed(() => ({
    fontFamily: config.value.fontFamily,
    fontSize: `${config.value.fontSize}px`,
    lineHeight: config.value.lineHeight
  }))

  // Terminal style object (ready to use in :style)
  const terminalStyle = computed(() => ({
    backgroundColor: terminalColors.value.background,
    color: terminalColors.value.foreground,
    fontFamily: fontSettings.value.fontFamily,
    fontSize: fontSettings.value.fontSize,
    lineHeight: fontSettings.value.lineHeight,
    cursor: config.value.cursorStyle === 'block' ? 'block' : 'text'
  }))

  // UI container style
  const containerStyle = computed(() => ({
    backgroundColor: uiColors.value.background,
    color: uiColors.value.text,
    borderColor: uiColors.value.border
  }))

  // Theme actions
  const toggleTheme = () => {
    const currentMode = config.value.mode
    if (currentMode === 'light') {
      themeStore.setThemeMode('dark')
    } else if (currentMode === 'dark') {
      themeStore.setThemeMode('auto')
    } else {
      themeStore.setThemeMode('light')
    }
  }

  const setDarkMode = () => themeStore.setThemeMode('dark')
  const setLightMode = () => themeStore.setThemeMode('light')
  const setAutoMode = () => themeStore.setThemeMode('auto')

  const changeColorScheme = (scheme: string) => {
    themeStore.setColorScheme(scheme as any)
  }

  const increaseFontSize = () => {
    themeStore.setFontSize(Math.min(72, config.value.fontSize + 1))
  }

  const decreaseFontSize = () => {
    themeStore.setFontSize(Math.max(8, config.value.fontSize - 1))
  }

  const resetFontSize = () => {
    themeStore.setFontSize(14)
  }

  // CSS custom properties string (for use in style attribute)
  const cssVariables = computed(() => themeStore.cssVariables)

  // Apply theme to document root
  const applyToDocument = () => {
    themeStore.applyTheme()
  }

  // Initialize theme (call this in App.vue or main component)
  const initialize = async () => {
    await themeStore.loadThemeConfig()
  }

  return {
    // State
    isDark,
    colors,
    config,
    terminalColors,
    uiColors,
    fontSettings,
    
    // Computed styles
    terminalStyle,
    containerStyle,
    cssVariables,
    
    // Actions
    toggleTheme,
    setDarkMode,
    setLightMode,
    setAutoMode,
    changeColorScheme,
    increaseFontSize,
    decreaseFontSize,
    resetFontSize,
    applyToDocument,
    initialize,
    
    // Store access (for advanced usage)
    store: themeStore
  }
}