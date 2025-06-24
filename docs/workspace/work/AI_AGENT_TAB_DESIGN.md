# AIエージェントタブ機能 設計仕様

**日付**: 2025-06-23 02:00 UTC  
**ステータス**: 🔄 設計中  
**目標**: tmux風ターミナルタブに加えて、AIエージェント対話専用タブを実装

## 設計概要

### タブタイプ拡張
```typescript
type TabType = 
  | "terminal"      // 既存: ターミナルタブ（PTY + shell）
  | "ai_assistant"  // 新規: AIエージェント対話タブ
```

### 既存仕様の活用
現在の`workspace:tab:create`イベントハンドラは既に`ai_assistant`タイプに対応：
- 基本的なイベント処理フローは維持
- タブオブジェクト構造は拡張可能
- Socket.IOイベントルーティングは共通化

## タブオブジェクト構造

### ターミナルタブ (既存)
```javascript
{
  id: "terminal-{uuid}",
  title: "Terminal 1",
  type: "terminal",
  isActive: true,
  isShared: false,
  connectedUsers: [],
  panes: [{
    id: "pane-{tabId}",
    terminalId: "term-{uuid}",
    isActive: true
  }],
  activePaneId: "pane-{tabId}",
  layout: "horizontal"
}
```

### AIエージェントタブ (新規拡張)
```javascript
{
  id: "ai_assistant-{uuid}",
  title: "AI Agent",
  type: "ai_assistant",
  isActive: true,
  isShared: false,
  connectedUsers: [],
  
  // AI専用フィールド
  assistantType: "general" | "code" | "terminal" | "system",
  contextSessionId: "session-{id}",
  conversationHistory: [
    {
      id: "msg-{uuid}",
      role: "user" | "assistant",
      content: string,
      timestamp: ISO8601,
      attachments?: any[]
    }
  ],
  
  // AI設定
  aiConfig: {
    model: "claude-3-sonnet" | "gpt-4" | "local",
    temperature: 0.7,
    maxTokens: 4096,
    systemPrompt?: string
  },
  
  // ターミナル連携
  linkedTerminalTabs: string[], // 関連ターミナルタブID配列
  terminalContext: {
    currentDirectory: string,
    shellHistory: string[],
    environment: Record<string, string>
  }
}
```

## Socket.IOイベント仕様

### 既存イベント拡張

#### 1. `workspace:tab:create`
```javascript
// リクエスト
{
  title: "AI Assistant",
  type: "ai_assistant",
  assistantType: "terminal", // optional
  sessionId: "session-123"   // optional
}

// レスポンス
{
  success: true,
  tabId: "ai_assistant-{uuid}",
  tab: { /* AIタブオブジェクト */ }
}
```

### 新規AIエージェント専用イベント

#### 2. `ai_agent:message:send`
```javascript
// ユーザーメッセージ送信
{
  tabId: "ai_assistant-{uuid}",
  message: {
    content: "ターミナルでpythonファイルを実行してください",
    attachments?: [{
      type: "terminal_context",
      terminalId: "term-{uuid}",
      lastCommands: ["ls", "cat app.py"]
    }]
  }
}
```

#### 3. `ai_agent:message:received`
```javascript
// AIエージェントレスポンス
{
  tabId: "ai_assistant-{uuid}",
  message: {
    id: "msg-{uuid}",
    role: "assistant",
    content: "pythonファイルを実行します。以下のコマンドを使用します：",
    timestamp: "2025-06-23T02:00:00Z",
    actions?: [{
      type: "terminal_command",
      command: "python app.py",
      targetTerminalId: "term-{uuid}"
    }]
  }
}
```

#### 4. `ai_agent:action:execute`
```javascript
// AIエージェントアクション実行
{
  tabId: "ai_assistant-{uuid}",
  action: {
    type: "terminal_command" | "file_read" | "file_write",
    parameters: {
      command?: string,
      terminalId?: string,
      filePath?: string,
      content?: string
    }
  }
}
```

#### 5. `ai_agent:context:sync`
```javascript
// ターミナルコンテキスト同期
{
  tabId: "ai_assistant-{uuid}",
  terminalId: "term-{uuid}",
  context: {
    currentDirectory: "/home/user/project",
    lastCommands: ["ls", "cat file.py"],
    output: "ファイル内容..."
  }
}
```

## バックエンド実装計画

### 1. socket_handlers.py 拡張
既存の`workspace_tab_create`に以下追加：
```python
# AI assistant specific fields (既存)
if tab_type == "ai_assistant":
    tab_object.update({
        "assistantType": data.get("assistantType", "general"),
        "contextSessionId": session_id,
        "conversationHistory": [],
        
        # 新規追加
        "aiConfig": {
            "model": data.get("model", "claude-3-sonnet"),
            "temperature": data.get("temperature", 0.7),
            "maxTokens": data.get("maxTokens", 4096)
        },
        "linkedTerminalTabs": [],
        "terminalContext": {
            "currentDirectory": "/home/user",
            "shellHistory": [],
            "environment": {}
        }
    })
```

### 2. 新規AIエージェントハンドラ
```python
@instrument_socketio_handler("ai_agent:message:send")
async def ai_agent_message_send(sid, data):
    """AIエージェントメッセージ送信処理"""
    
@instrument_socketio_handler("ai_agent:action:execute") 
async def ai_agent_action_execute(sid, data):
    """AIエージェントアクション実行処理"""
    
@instrument_socketio_handler("ai_agent:context:sync")
async def ai_agent_context_sync(sid, data):
    """ターミナルコンテキスト同期処理"""
```

## フロントエンド実装計画

### 1. AIAssistantComponent.vue
```vue
<template>
  <div class="ai-assistant-tab">
    <!-- チャット UI -->
    <div class="chat-container">
      <div class="messages">
        <div v-for="msg in messages" :key="msg.id" 
             :class="['message', msg.role]">
          <!-- メッセージ表示 -->
        </div>
      </div>
      
      <!-- 入力フィールド -->
      <div class="input-area">
        <textarea v-model="currentMessage" 
                  @keydown.ctrl.enter="sendMessage"
                  placeholder="AIエージェントに質問してください...">
        </textarea>
        <button @click="sendMessage">送信</button>
      </div>
    </div>
    
    <!-- サイドパネル: ターミナル連携 -->
    <div class="terminal-links">
      <h4>連携ターミナル</h4>
      <div v-for="terminalId in linkedTerminals" :key="terminalId">
        <!-- ターミナル状態表示 -->
      </div>
    </div>
  </div>
</template>
```

### 2. WorkspaceManager.vue 拡張
```vue
<!-- タブ作成ボタン拡張 -->
<div class="tab-creation">
  <button @click="createTab('terminal')">+ Terminal</button>
  <button @click="createTab('ai_assistant')">+ AI Agent</button>
</div>

<!-- タブ表示分岐 -->
<div class="tab-content">
  <TerminalPaneManager v-if="activeTab.type === 'terminal'" 
                       :terminal-tab="activeTab" />
  <AIAssistantComponent v-else-if="activeTab.type === 'ai_assistant'"
                        :ai-tab="activeTab" />
</div>
```

## 機能フロー

### 1. AIタブ作成フロー
```
1. ユーザーが "AI Agent" ボタンクリック
   ↓
2. workspace:tab:create event送信 (type: "ai_assistant")
   ↓  
3. バックエンドでAIタブオブジェクト作成
   ↓
4. workspace:tab:created event受信
   ↓
5. フロントエンドでAIAssistantComponent表示
```

### 2. AI対話フロー
```
1. ユーザーがメッセージ入力
   ↓
2. ai_agent:message:send event送信
   ↓
3. バックエンドでAI APIコール
   ↓
4. ai_agent:message:received event送信
   ↓
5. フロントエンドでAI応答表示
```

### 3. ターミナル連携フロー  
```
1. AIが「ターミナルでコマンド実行」を提案
   ↓
2. ai_agent:action:execute event送信
   ↓
3. バックエンドで関連ターミナルにコマンド送信
   ↓
4. ターミナル出力をAIコンテキストに追加
   ↓
5. ai_agent:context:sync event送信
```

## 技術スタック

### バックエンド
- **AI API**: Claude 3 Sonnet (primary), GPT-4 (fallback)
- **メッセージ管理**: In-memory + Redis (将来)
- **ターミナル連携**: 既存PTYターミナル統合

### フロントエンド  
- **UI**: Vue 3 Composition API
- **チャットUI**: カスタムコンポーネント
- **状態管理**: Pinia stores
- **Socket通信**: 既存AetherTermSocketManager

## 実装ステップ

1. ✅ 設計仕様策定 (このドキュメント)
2. 🔄 バックエンドSocket.IOイベントハンドラ実装
3. 🔄 フロントエンドAIAssistantComponent作成
4. 🔄 AI対話機能実装
5. 🔄 ターミナル連携機能実装
6. 🔄 テスト・デバッグ

## メリット

### 既存仕様活用
- イベントハンドラ基盤を再利用
- タブ管理システムを拡張
- Socket.IO通信パターンを踏襲

### ユーザー体験向上
- ターミナルとAIの統合ワークフロー
- コンテキスト保持によるスマートな対話
- tmux風のタブ切り替えでシームレスな操作

### 拡張性
- 複数AIモデル対応
- プラグイン形式のアクション拡張
- ターミナル以外のツール連携も可能