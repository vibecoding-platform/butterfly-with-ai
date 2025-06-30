/**
 * Theme Store - Vuex store for theme management
 * 
 * Handles theme switching, color schemes, and user preferences
 */

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'auto'
export type ColorScheme = 'default' | 'solarized-dark' | 'solarized-light' | 'monokai' | 'dracula' | 'nord' | 'gruvbox-dark' | 'gruvbox-light'

export interface ThemeConfig {
  mode: ThemeMode
  colorScheme: ColorScheme
  customColors: Record<string, string>
  fontFamily: string
  fontSize: number
  lineHeight: number
  cursorStyle: string
  cursorBlink: boolean
}

export interface ColorPalette {
  background: string
  foreground: string
  cursor: string
  selection: string
  black: string
  red: string
  green: string
  yellow: string
  blue: string
  magenta: string
  cyan: string
  white: string
  bright_black: string
  bright_red: string
  bright_green: string
  bright_yellow: string
  bright_blue: string
  bright_magenta: string
  bright_cyan: string
  bright_white: string
}

const DEFAULT_THEME_CONFIG: ThemeConfig = {
  mode: 'dark',
  colorScheme: 'default',
  customColors: {},
  fontFamily: "Monaco, 'Courier New', monospace",
  fontSize: 14,
  lineHeight: 1.2,
  cursorStyle: 'block',
  cursorBlink: true
}

export const useThemeStore = defineStore('theme', () => {
  // State
  const themeConfig = ref<ThemeConfig>({ ...DEFAULT_THEME_CONFIG })
  const availableThemes = ref<{
    modes: ThemeMode[]
    colorSchemes: ColorScheme[]
    schemePreviews: Record<string, { background: string; foreground: string; accent: string }>
  }>({
    modes: ['light', 'dark', 'auto'],
    colorSchemes: ['default', 'solarized-dark', 'dracula', 'nord'],
    schemePreviews: {}
  })
  const currentColors = ref<ColorPalette | null>(null)
  const isLoading = ref(false)

  // Computed
  const isDarkMode = computed(() => {
    if (themeConfig.value.mode === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return themeConfig.value.mode === 'dark'
  })

  const cssVariables = computed(() => {
    if (!currentColors.value) return ''
    
    const colors = currentColors.value
    const config = themeConfig.value
    
    const variables: Record<string, string> = {
      // Color variables
      '--terminal-background': colors.background,
      '--terminal-foreground': colors.foreground,
      '--terminal-cursor': colors.cursor,
      '--terminal-selection': colors.selection,
      '--terminal-black': colors.black,
      '--terminal-red': colors.red,
      '--terminal-green': colors.green,
      '--terminal-yellow': colors.yellow,
      '--terminal-blue': colors.blue,
      '--terminal-magenta': colors.magenta,
      '--terminal-cyan': colors.cyan,
      '--terminal-white': colors.white,
      '--terminal-bright-black': colors.bright_black,
      '--terminal-bright-red': colors.bright_red,
      '--terminal-bright-green': colors.bright_green,
      '--terminal-bright-yellow': colors.bright_yellow,
      '--terminal-bright-blue': colors.bright_blue,
      '--terminal-bright-magenta': colors.bright_magenta,
      '--terminal-bright-cyan': colors.bright_cyan,
      '--terminal-bright-white': colors.bright_white,
      
      // Font variables
      '--terminal-font-family': config.fontFamily,
      '--terminal-font-size': `${config.fontSize}px`,
      '--terminal-line-height': config.lineHeight.toString(),
      '--terminal-cursor-style': config.cursorStyle,
      
      // Theme mode
      '--theme-mode': config.mode,
      
      // UI theme colors (derived from terminal colors)
      '--ui-background': isDarkMode.value ? colors.background : '#ffffff',
      '--ui-surface': isDarkMode.value ? colors.bright_black : '#f5f5f5',
      '--ui-primary': colors.blue,
      '--ui-text': isDarkMode.value ? colors.foreground : colors.black,
      '--ui-text-secondary': isDarkMode.value ? colors.bright_black : colors.bright_white,
      '--ui-border': isDarkMode.value ? colors.bright_black : '#e0e0e0',
    }

    return Object.entries(variables)
      .map(([key, value]) => `${key}: ${value}`)
      .join('; ')
  })

  // Actions
  const loadThemeConfig = async () => {
    isLoading.value = true
    try {
      // Load from localStorage
      const saved = localStorage.getItem('aetherterm-theme-config')
      if (saved) {
        const parsed = JSON.parse(saved)
        themeConfig.value = { ...DEFAULT_THEME_CONFIG, ...parsed }
      }
      
      await loadColors()
    } catch (error) {
      console.error('Failed to load theme config:', error)
      // Fallback to default theme
      themeConfig.value = { ...DEFAULT_THEME_CONFIG }
      await loadColors()
    } finally {
      isLoading.value = false
    }
  }

  const saveThemeConfig = async () => {
    try {
      // Save to localStorage
      localStorage.setItem('aetherterm-theme-config', JSON.stringify(themeConfig.value))
      await loadColors()
    } catch (error) {
      console.error('Failed to save theme config:', error)
    }
  }

  const loadColors = async () => {
    try {
      // Use predefined color schemes (frontend-only implementation)
      const colorSchemes: Record<ColorScheme, ColorPalette> = {
        'default': {
          background: '#1e1e1e',
          foreground: '#d4d4d4',
          cursor: '#ffffff',
          selection: '#264f78',
          black: '#000000',
          red: '#cd3131',
          green: '#0dbc79',
          yellow: '#e5e510',
          blue: '#2472c8',
          magenta: '#bc3fbc',
          cyan: '#11a8cd',
          white: '#e5e5e5',
          bright_black: '#666666',
          bright_red: '#f14c4c',
          bright_green: '#23d18b',
          bright_yellow: '#f5f543',
          bright_blue: '#3b8eea',
          bright_magenta: '#d670d6',
          bright_cyan: '#29b8db',
          bright_white: '#e5e5e5'
        },
        'solarized-dark': {
          background: '#002b36',
          foreground: '#839496',
          cursor: '#93a1a1',
          selection: '#073642',
          black: '#073642',
          red: '#dc322f',
          green: '#859900',
          yellow: '#b58900',
          blue: '#268bd2',
          magenta: '#d33682',
          cyan: '#2aa198',
          white: '#eee8d5',
          bright_black: '#002b36',
          bright_red: '#cb4b16',
          bright_green: '#586e75',
          bright_yellow: '#657b83',
          bright_blue: '#839496',
          bright_magenta: '#6c71c4',
          bright_cyan: '#93a1a1',
          bright_white: '#fdf6e3'
        },
        'solarized-light': {
          background: '#fdf6e3',
          foreground: '#657b83',
          cursor: '#586e75',
          selection: '#eee8d5',
          black: '#073642',
          red: '#dc322f',
          green: '#859900',
          yellow: '#b58900',
          blue: '#268bd2',
          magenta: '#d33682',
          cyan: '#2aa198',
          white: '#eee8d5',
          bright_black: '#002b36',
          bright_red: '#cb4b16',
          bright_green: '#586e75',
          bright_yellow: '#657b83',
          bright_blue: '#839496',
          bright_magenta: '#6c71c4',
          bright_cyan: '#93a1a1',
          bright_white: '#fdf6e3'
        },
        'dracula': {
          background: '#282a36',
          foreground: '#f8f8f2',
          cursor: '#f8f8f0',
          selection: '#44475a',
          black: '#21222c',
          red: '#ff5555',
          green: '#50fa7b',
          yellow: '#f1fa8c',
          blue: '#bd93f9',
          magenta: '#ff79c6',
          cyan: '#8be9fd',
          white: '#f8f8f2',
          bright_black: '#6272a4',
          bright_red: '#ff6e6e',
          bright_green: '#69ff94',
          bright_yellow: '#ffffa5',
          bright_blue: '#d6acff',
          bright_magenta: '#ff92df',
          bright_cyan: '#a4ffff',
          bright_white: '#ffffff'
        },
        'nord': {
          background: '#2e3440',
          foreground: '#d8dee9',
          cursor: '#d8dee9',
          selection: '#4c566a',
          black: '#3b4252',
          red: '#bf616a',
          green: '#a3be8c',
          yellow: '#ebcb8b',
          blue: '#81a1c1',
          magenta: '#b48ead',
          cyan: '#88c0d0',
          white: '#e5e9f0',
          bright_black: '#4c566a',
          bright_red: '#bf616a',
          bright_green: '#a3be8c',
          bright_yellow: '#ebcb8b',
          bright_blue: '#81a1c1',
          bright_magenta: '#b48ead',
          bright_cyan: '#8fbcbb',
          bright_white: '#eceff4'
        },
        'monokai': {
          background: '#272822',
          foreground: '#f8f8f2',
          cursor: '#f8f8f0',
          selection: '#49483e',
          black: '#272822',
          red: '#f92672',
          green: '#a6e22e',
          yellow: '#f4bf75',
          blue: '#66d9ef',
          magenta: '#ae81ff',
          cyan: '#a1efe4',
          white: '#f8f8f2',
          bright_black: '#75715e',
          bright_red: '#f92672',
          bright_green: '#a6e22e',
          bright_yellow: '#f4bf75',
          bright_blue: '#66d9ef',
          bright_magenta: '#ae81ff',
          bright_cyan: '#a1efe4',
          bright_white: '#f9f8f5'
        },
        'gruvbox-dark': {
          background: '#282828',
          foreground: '#ebdbb2',
          cursor: '#ebdbb2',
          selection: '#3c3836',
          black: '#282828',
          red: '#cc241d',
          green: '#98971a',
          yellow: '#d79921',
          blue: '#458588',
          magenta: '#b16286',
          cyan: '#689d6a',
          white: '#a89984',
          bright_black: '#928374',
          bright_red: '#fb4934',
          bright_green: '#b8bb26',
          bright_yellow: '#fabd2f',
          bright_blue: '#83a598',
          bright_magenta: '#d3869b',
          bright_cyan: '#8ec07c',
          bright_white: '#ebdbb2'
        },
        'gruvbox-light': {
          background: '#fbf1c7',
          foreground: '#3c3836',
          cursor: '#3c3836',
          selection: '#ebdbb2',
          black: '#fbf1c7',
          red: '#cc241d',
          green: '#98971a',
          yellow: '#d79921',
          blue: '#458588',
          magenta: '#b16286',
          cyan: '#689d6a',
          white: '#7c6f64',
          bright_black: '#928374',
          bright_red: '#9d0006',
          bright_green: '#79740e',
          bright_yellow: '#b57614',
          bright_blue: '#076678',
          bright_magenta: '#8f3f71',
          bright_cyan: '#427b58',
          bright_white: '#3c3836'
        }
      }

      currentColors.value = colorSchemes[themeConfig.value.colorScheme] || colorSchemes.default
      
      // Apply custom color overrides
      if (themeConfig.value.customColors) {
        currentColors.value = {
          ...currentColors.value,
          ...themeConfig.value.customColors
        } as ColorPalette
      }
    } catch (error) {
      console.error('Failed to load colors:', error)
    }
  }

  const setThemeMode = async (mode: ThemeMode) => {
    themeConfig.value.mode = mode
    await saveThemeConfig()
  }

  const setColorScheme = async (scheme: ColorScheme) => {
    themeConfig.value.colorScheme = scheme
    await saveThemeConfig()
  }

  const setFontFamily = async (fontFamily: string) => {
    themeConfig.value.fontFamily = fontFamily
    await saveThemeConfig()
  }

  const setFontSize = async (fontSize: number) => {
    themeConfig.value.fontSize = Math.max(8, Math.min(72, fontSize))
    await saveThemeConfig()
  }

  const setCustomColor = async (colorName: string, colorValue: string) => {
    themeConfig.value.customColors[colorName] = colorValue
    await saveThemeConfig()
  }

  const resetTheme = async () => {
    themeConfig.value = { ...DEFAULT_THEME_CONFIG }
    await saveThemeConfig()
  }

  const applyTheme = () => {
    const root = document.documentElement
    const variables = cssVariables.value
    
    if (variables) {
      const pairs = variables.split('; ')
      pairs.forEach(pair => {
        const [key, value] = pair.split(': ')
        if (key && value) {
          root.style.setProperty(key.trim(), value.trim())
        }
      })
    }
    
    // Apply theme class
    document.body.className = document.body.className.replace(/theme-\w+/g, '')
    document.body.classList.add(`theme-${isDarkMode.value ? 'dark' : 'light'}`)
  }

  // Watchers
  watch(cssVariables, applyTheme, { immediate: true })
  watch(() => themeConfig.value.mode, () => {
    if (themeConfig.value.mode === 'auto') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaQuery.addListener(applyTheme)
    }
  })

  return {
    // State
    themeConfig,
    availableThemes,
    currentColors,
    isLoading,
    
    // Computed
    isDarkMode,
    cssVariables,
    
    // Actions
    loadThemeConfig,
    saveThemeConfig,
    loadColors,
    setThemeMode,
    setColorScheme,
    setFontFamily,
    setFontSize,
    setCustomColor,
    resetTheme,
    applyTheme
  }
})