# AgentServer 動作モード・設定制御 設計書

## 概要

AgentServerの動作モードと設定による機能制御について説明します。
AgentServerは、ControlServerとの連携有無によって異なる動作モードを持ち、
設定により各機能のOn/Offを細かく制御できます。

## AgentServerの動作モード

### 1. スタンドアロンモード（推奨・デフォルト）

```
┌─────────────────────────────────────┐
│            AgentServer              │
│          (単体動作)                  │
│                                     │
│  ┌─────────────────────────────┐    │
│  │        Frontend             │    │
│  │  ┌─────┐ ┌─────┐ ┌─────┐   │    │
│  │  │Tab1 │ │Tab2 │ │Tab3 │   │    │
│  │  └─────┘ └─────┘ └─────┘   │    │
│  │                             │    │
│  │  ┌─────────────────────┐   │    │
│  │  │    AI Chat Panel    │   │    │
│  │  └─────────────────────┘   │    │
│  └─────────────────────────────┘    │
│                                     │
│  ┌─────────────────────────────┐    │
│  │        AgentShell           │    │
│  │   AI自動実行エンジン          │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

**特徴**:
- 単一ユーザー向けのシンプルな構成
- 全機能をAgentServerが直接管理
- 設定ファイル1つで完結
- 開発・個人利用に最適

**有効な機能**:
- ユーザーターミナルタブ管理
- AIチャット機能
- AI自動セッション作成
- AgentShell統合
- ローカルAI処理

### 2. ControlServer連携モード（将来拡張）

```
┌─────────────────────────────────────┐
│           ControlServer             │
│        (統合管理・監視)              │
└─────────────────┬───────────────────┘
                  │ 管理・監視
                  ▼
┌─────────────────────────────────────┐
│            AgentServer              │
│         (個別ユーザー担当)           │
│                                     │
│  ┌─────────────────────────────┐    │
│  │        Frontend             │    │
│  │  ┌─────┐ ┌─────┐           │    │
│  │  │Tab1 │ │Tab2 │           │    │
│  │  └─────┘ └─────┘           │    │
│  │                             │    │
│  │  ┌─────────────────────┐   │    │
│  │  │ Supervisor Panel    │   │    │
│  │  │ (ControlServer連携) │   │    │
│  │  └─────────────────────┘   │    │
│  └─────────────────────────────┘    │
│                                     │
│  ┌─────────────────────────────┐    │
│  │        AgentShell           │    │
│  │  (ControlServer監視下)      │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

**特徴**:
- ControlServerによる上位管理
- AgentServerは個別ユーザー処理に特化
- 統合監視・制御が可能
- エンタープライズ利用に適している

**制限される機能**:
- 一部の管理機能はControlServerに委譲
- 設定の一部がControlServerにより制御
- 独立性が制限される

## 設定による機能制御

### 基本設定構造（TOML）

```toml
[mode]
# AgentServerの動作モード
standalone = true                    # スタンドアロンモード（デフォルト）
control_server_integration = false  # ControlServer連携

[features]
# 機能の大分類制御
ai_enabled = true                    # AI機能全体
ui_tabs_enabled = true               # タブ機能
supervisor_panel_enabled = true      # Supervisor Panel

[ai]
# AI機能の詳細制御
enabled = true                       # AI機能マスタースイッチ

[ai.chat]
enabled = true                       # AIチャット機能

[ai.sessions]
enabled = true                       # AI自動セッション管理

[ai.agent_shell]
enabled = true                       # AgentShell統合

[integrations]
# 外部連携設定
control_server_enabled = false      # ControlServer連携
control_server_url = ""              # ControlServer URL（連携時）
```

## 機能制御マトリックス

| 機能 | スタンドアロン | ControlServer連携 | 設定項目 |
|------|---------------|------------------|----------|
| ユーザータブ管理 | ✅ 完全制御 | ✅ 完全制御 | `features.ui_tabs_enabled` |
| AIチャット | ✅ 完全制御 | ✅ 完全制御 | `ai.chat.enabled` |
| AI自動セッション | ✅ 完全制御 | ⚠️ 制限あり | `ai.sessions.enabled` |
| AgentShell統合 | ✅ 完全制御 | ⚠️ 監視下 | `ai.agent_shell.enabled` |
| Supervisor Panel | ✅ ローカル制御 | ✅ ControlServer連携 | `features.supervisor_panel_enabled` |
| 統合監視 | ❌ 利用不可 | ✅ 利用可能 | `integrations.control_server_enabled` |

## 設定の適用優先順位

### 1. 環境変数による上書き
```bash
AETHERTERM_AI_ENABLED=false          # AI機能を無効化
AETHERTERM_STANDALONE=true           # スタンドアロンモード強制
AETHERTERM_CONTROL_SERVER_URL=...    # ControlServer URL指定
```

### 2. コマンドライン引数
```bash
aetherterm-agentserver --no-ai                    # AI機能無効
aetherterm-agentserver --control-server-url=...   # ControlServer連携
aetherterm-agentserver --standalone               # スタンドアロン強制
```

### 3. 設定ファイル（TOML）
```toml
# aetherterm.toml での設定
[features]
ai_enabled = false
```

### 4. デフォルト値
- 全機能有効
- スタンドアロンモード
- ControlServer連携無効

## フロントエンドでの設定反映

### 設定取得API
```
GET /api/config
```

**レスポンス例**:
```json
{
  "mode": {
    "standalone": true,
    "control_server_integration": false
  },
  "features": {
    "ai_enabled": true,
    "ui_tabs_enabled": true,
    "supervisor_panel_enabled": true
  },
  "ai": {
    "chat_enabled": true,
    "sessions_enabled": true,
    "agent_shell_enabled": true
  }
}
```

### UI表示制御
```vue
<template>
  <!-- AIチャット：ai.chat_enabled で制御 -->
  <div v-if="config.ai.chat_enabled" class="ai-chat-panel">
    <SimpleChatComponent />
  </div>
  
  <!-- AI自動セッション：ai.sessions_enabled で制御 -->
  <div v-if="config.ai.sessions_enabled" class="ai-sessions-tree">
    <AISessionsComponent />
  </div>
  
  <!-- Supervisor Panel：features.supervisor_panel_enabled で制御 -->
  <div v-if="config.features.supervisor_panel_enabled" class="supervisor-panel">
    <SupervisorControlPanel />
  </div>
</template>
```

## 実装時の考慮点

### 1. 設定変更の反映
- **リアルタイム反映**: WebSocket経由で設定変更を通知
- **再起動必要**: 一部の設定（サーバー設定等）は再起動が必要
- **部分再読み込み**: UI関連設定は動的に反映可能

### 2. 設定検証
- **起動時検証**: 設定ファイルの妥当性チェック
- **依存関係チェック**: 機能間の依存関係検証
- **フォールバック**: 無効な設定の場合はデフォルト値を使用

### 3. デバッグ支援
- **設定ダンプ**: 現在の有効設定をログ出力
- **設定源表示**: どの設定がどこから来たかを記録
- **設定変更履歴**: 設定変更のログ記録

## ユースケース例

### 1. 最小構成（AI機能無効）
```toml
[features]
ai_enabled = false
ui_tabs_enabled = true
supervisor_panel_enabled = false
```
→ シンプルなターミナルタブのみ

### 2. AIチャットのみ
```toml
[ai]
enabled = true

[ai.chat]
enabled = true

[ai.sessions]
enabled = false

[ai.agent_shell]
enabled = false
```
→ 手動タブ + AIチャット

### 3. 全機能有効（デフォルト）
```toml
[features]
ai_enabled = true
ui_tabs_enabled = true
supervisor_panel_enabled = true

[ai]
enabled = true

[ai.chat]
enabled = true

[ai.sessions]
enabled = true

[ai.agent_shell]
enabled = true
```
→ 全機能利用可能

## 将来の拡張性

### 1. プラグインシステム
- 機能をプラグイン化
- 設定によるプラグインの有効/無効制御

### 2. A/Bテスト機能
- 機能フラグによる段階的ロールアウト
- ユーザー毎の機能制御

### 3. リモート設定管理
- ControlServer経由での設定配信
- 設定の集中管理