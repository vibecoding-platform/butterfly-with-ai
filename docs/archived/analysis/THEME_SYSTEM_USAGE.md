# テーマシステム利用ガイド

## 概要
AetherTermのテーマシステムは、ユーザーがターミナルの外観を自由にカスタマイズできる機能です。

## 基本的な呼び出し方法

### 1. Vueコンポーネントでの利用

```vue
<template>
  <div>
    <!-- テーマセレクター呼び出し -->
    <ThemeSelector />
    
    <!-- テーマが適用されたターミナル -->
    <div class="terminal" :style="terminalStyle">
      <!-- ターミナルコンテンツ -->
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useThemeStore } from '@/stores/themeStore'
import ThemeSelector from '@/components/ThemeSelector.vue'

const themeStore = useThemeStore()

// テーマ色を利用したスタイル
const terminalStyle = computed(() => ({
  backgroundColor: themeStore.currentColors?.background || '#1e1e1e',
  color: themeStore.currentColors?.foreground || '#d4d4d4',
  fontFamily: themeStore.themeConfig.fontFamily,
  fontSize: \`\${themeStore.themeConfig.fontSize}px\`
}))

// テーマ初期化
themeStore.loadThemeConfig()
</script>
```

### 2. メインアプリケーションでの初期化

```vue
<!-- App.vue -->
<template>
  <div id="app">
    <!-- アプリケーションコンテンツ -->
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useThemeStore } from '@/stores/themeStore'

const themeStore = useThemeStore()

onMounted(async () => {
  // テーマ設定をロード
  await themeStore.loadThemeConfig()
})
</script>
```

### 3. ヘッダーやサイドバーでのテーマ切り替え

```vue
<template>
  <v-app-bar>
    <v-spacer />
    
    <!-- クイックテーマ切り替え -->
    <v-btn-toggle v-model="themeMode" mandatory variant="outlined" density="compact">
      <v-btn value="light" icon="mdi-white-balance-sunny" />
      <v-btn value="dark" icon="mdi-moon-waning-crescent" />
      <v-btn value="auto" icon="mdi-brightness-auto" />
    </v-btn-toggle>
    
    <!-- テーマ設定ダイアログ -->
    <v-btn icon="mdi-palette" @click="showThemeDialog = true" />
  </v-app-bar>
  
  <v-dialog v-model="showThemeDialog" max-width="600">
    <ThemeSelector />
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useThemeStore } from '@/stores/themeStore'

const themeStore = useThemeStore()
const showThemeDialog = ref(false)

const themeMode = computed({
  get: () => themeStore.themeConfig.mode,
  set: (value) => themeStore.setThemeMode(value)
})
</script>
```

## プログラマティックな利用

### テーマ設定の取得・変更

```typescript
import { useThemeStore } from '@/stores/themeStore'

const themeStore = useThemeStore()

// 現在のテーマモード取得
const currentMode = themeStore.themeConfig.mode

// テーマモード変更
await themeStore.setThemeMode('dark')

// 色スキーム変更
await themeStore.setColorScheme('dracula')

// フォント設定変更
await themeStore.setFontFamily("'JetBrains Mono', monospace")
await themeStore.setFontSize(16)

// カスタム色設定
await themeStore.setCustomColor('background', '#1a1a1a')

// 設定リセット
await themeStore.resetTheme()
```

### CSS変数の直接利用

```css
.my-component {
  background-color: var(--terminal-background);
  color: var(--terminal-foreground);
  border-color: var(--terminal-bright-black);
  font-family: var(--terminal-font-family);
  font-size: var(--terminal-font-size);
}

.ui-surface {
  background-color: var(--ui-surface);
  color: var(--ui-text);
  border: 1px solid var(--ui-border);
}
```

## 利用可能なCSS変数

### ターミナル色
- `--terminal-background`
- `--terminal-foreground`  
- `--terminal-cursor`
- `--terminal-selection`
- `--terminal-black`, `--terminal-red`, `--terminal-green`, etc.
- `--terminal-bright-black`, `--terminal-bright-red`, etc.

### フォント設定
- `--terminal-font-family`
- `--terminal-font-size`
- `--terminal-line-height`

### UI色（自動生成）
- `--ui-background`
- `--ui-surface`
- `--ui-primary`
- `--ui-text`
- `--ui-text-secondary`
- `--ui-border`

## 設定の永続化

テーマ設定は自動的にlocalStorageに保存されます：

```typescript
// 自動保存されるため、手動保存は不要
await themeStore.setThemeMode('dark')

// 必要に応じて手動保存
await themeStore.saveThemeConfig()
```

## 設定のエクスポート/インポート

```typescript
// 設定エクスポート
const themeJson = JSON.stringify(themeStore.themeConfig, null, 2)

// 設定インポート
const importedConfig = JSON.parse(themeJsonString)
themeStore.themeConfig = { ...themeStore.themeConfig, ...importedConfig }
await themeStore.saveThemeConfig()
```

## 既存コンポーネントへの統合

### TerminalComponentでの利用

```vue
<!-- TerminalComponent.vue -->
<template>
  <div class="terminal-container" :style="terminalContainerStyle">
    <div ref="terminalElement" class="terminal" :style="terminalStyle"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useThemeStore } from '@/stores/themeStore'

const themeStore = useThemeStore()

const terminalStyle = computed(() => ({
  backgroundColor: themeStore.currentColors?.background || '#1e1e1e',
  color: themeStore.currentColors?.foreground || '#d4d4d4',
  fontFamily: themeStore.themeConfig.fontFamily,
  fontSize: \`\${themeStore.themeConfig.fontSize}px\`,
  lineHeight: themeStore.themeConfig.lineHeight
}))

const terminalContainerStyle = computed(() => ({
  border: \`1px solid \${themeStore.currentColors?.bright_black || '#666'}\`
}))

onMounted(async () => {
  await themeStore.loadThemeConfig()
})
</script>
```

## 呼び出しの優先順位

1. **アプリケーション起動時**: `App.vue`でテーマ初期化
2. **コンポーネント内**: 必要に応じて`useThemeStore()`でアクセス
3. **設定画面**: `ThemeSelector`コンポーネントで詳細設定
4. **クイック切り替え**: ヘッダーなどでのワンクリック切り替え

## Architecture位置づけ

```
├── Infrastructure Layer
│   └── LocalStorage (テーマ設定永続化)
├── Application Layer  
│   └── ThemeService (バックエンド - 簡素化済み)
├── Interface Layer
│   ├── themeStore (Pinia store)
│   └── ThemeSelector (Vue component)
└── Domain Layer
    └── ThemeConfig (設定データ構造)
```

短期記憶（short_term_memory）はInfrastructure層に分類するのが正しいです。外部ストレージ（Redis等）への永続化を担当するためです。