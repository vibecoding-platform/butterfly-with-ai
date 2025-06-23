# Workspace Initialization Flow

## 概要

AetherTermプロジェクト固有のワークスペース初期化フローです。Vue Frontend ↔ Python Backend間でWorkspaceの状態を同期し、適切に再現します。

## Workspaceアーキテクチャ

### Workspace概念
**Workspace**は、AetherTermにおけるユーザーの作業環境全体を表す概念です。

```
Workspace
├── Session 1 (セッション)
│   ├── Tab 1 (ターミナルタブ)
│   │   ├── Pane 1.1 (ターミナルペーン)
│   │   └── Pane 1.2 (ターミナルペーン)
│   ├── Tab 2 (AIアシスタントタブ)
│   └── Tab 3 (ターミナルタブ)
│       └── Pane 3.1 (ターミナルペーン)
└── Session 2 (セッション)
    └── Tab 1 (ターミナルタブ)
        └── Pane 1.1 (ターミナルペーン)
```

### 構成要素

1. **Workspace**: ユーザーの作業環境全体
2. **Session**: 独立した作業セッション（プロジェクト単位）
3. **Tab**: セッション内のタブ（ターミナル、AIアシスタント等）
4. **Pane**: タブ内の分割されたペーン（複数ターミナル表示）

### Workspace状態管理

Workspaceは以下の状態を持ちます：

- **Sessions**: アクティブなセッション一覧
- **Active Session**: 現在フォーカスされているセッション
- **Tabs**: 各セッション内のタブ構成
- **Active Tab**: 各セッションでアクティブなタブ
- **Panes**: 各タブ内のペーン構成と分割状態
- **Terminal State**: 各ペーンのターミナル状態（履歴、プロセス等）

## 初期化の重要性

Workspace初期化では、以下を正しい順序で行う必要があります：

1. **既存Workspace状態の取得**: サーバーから現在のWorkspace構成を取得
2. **Session復元**: 既存のセッション状態を復元
3. **Tab構成復元**: 各セッションのタブレイアウトを復元
4. **Pane構成復元**: 各タブ内のペーン分割状態を復元
5. **Terminal復元**: 各ペーンのターミナル接続と履歴を復元
6. **UI同期**: フロントエンドUIを復元された状態に同期

**不適切な初期化**: 既存状態を無視して新しいターミナルを作成すると、Workspace構成が破綻し、プロンプト表示問題等が発生します。

## Workspace同期・再現フロー

### 🚀 Workspace初期化シーケンス

AetherTermにおけるWorkspace同期・再現は以下の順序で実行されます：

```
1. アプリケーション起動 (main.ts)
   ├── Socket通信サービス初期化（接続は保留）
   ├── Workspace状態管理Store初期化
   └── Vue Appマウント
   ↓
2. SessionManager起動
   ├── AgentServerへSocket.IO接続開始
   └── Workspace同期プロセス開始
   ↓  
3. Socket.IO接続確立
   ├── 通信チャネル確立
   └── 新規Workspace作成は行わない
   ↓
4. Workspace状態同期要求
   ├── workspace:sync:request送信
   ├── 既存Session情報要求
   ├── 既存Tab構成要求
   ├── 既存Pane構成要求
   ├── アクティブTerminal状態要求
   └── ユーザー情報要求
   ↓
5. Workspace状態同期応答処理
   ├── workspace:sync:response受信
   ├── Session構成復元
   ├── Tab構成復元
   ├── Pane分割状態復元
   ├── Terminal接続復元
   ├── 履歴データ復元
   └── ユーザーUI状態復元
   ↓
6. Workspace状態確認・補完
   ├── 既存Workspaceがある場合：復元完了
   └── 空Workspaceの場合：初期Session/Tab/Pane作成
   ↓
7. ユーザー操作駆動のWorkspace拡張
   ├── 新規Tab作成（ユーザー操作時）
   ├── Pane分割（ユーザー操作時）
   ├── Terminal作成（タブ・ペーン作成に連動）
   └── Workspace状態サーバー同期
```

### Workspace同期プロトコル

#### 同期対象データ
```json
{
  "workspace": {
    "sessions": [
      {
        "id": "session-001",
        "name": "Project Alpha",
        "tabs": [
          {
            "id": "tab-001", 
            "type": "terminal",
            "title": "Main Terminal",
            "panes": [
              {
                "id": "pane-001",
                "terminalId": "term-001",
                "position": {"x": 0, "y": 0, "width": 50, "height": 100},
                "workingDirectory": "/home/user/project",
                "shellType": "bash"
              },
              {
                "id": "pane-002", 
                "terminalId": "term-002",
                "position": {"x": 50, "y": 0, "width": 50, "height": 100},
                "workingDirectory": "/home/user/logs",
                "shellType": "bash"
              }
            ]
          }
        ]
      }
    ],
    "activeSessionId": "session-001",
    "uiState": {
      "sidebarVisible": true,
      "chatPanelVisible": false
    }
  }
}
```

## コードレベル実装

### 1. Frontend初期化 (main.ts)

```typescript
// 修正前：即座に接続・セッション作成
const socket = trackedSocketService.connect();
terminalStore.setSocket(socket);
terminalStore.initializeSession(`session_${Date.now()}`);

// 修正後：接続とセッション作成を延期
const trackedSocketService = TrackedSocketService.getInstance({
  defaultTimeout: 5000,
  slowResponseThreshold: 1000,
  enableDetailedLogging: true,
  enableMetrics: true
});
// 接続はSessionManagerが行う
```

### 2. SessionManager初期化

```typescript
onMounted(async () => {
  try {
    // Step 1: Socket接続
    await sessionSocketService.connect('http://localhost:57575')
    
    // Step 2: ワークスペース同期要求
    await sessionSocketService.requestWorkspaceSync()
    
    // Step 3: 復元完了待ち後、必要時のみ新セッション作成
    setTimeout(() => {
      if (sessionStore.sessions.length === 0) {
        createNewSession()
      }
    }, 1000)
    
  } catch (error) {
    createNewSession() // フォールバック
  }
})
```

### 3. ワークスペース同期プロトコル

#### Frontend Request
```typescript
async requestWorkspaceSync(): Promise<void> {
  return new Promise((resolve, reject) => {
    this.socket!.once('workspace:sync:response', (data) => {
      // セッション復元
      data.sessions.forEach(session => {
        this.sessionStore.addSession(session)
      })
      
      // アクティブセッション設定
      if (data.sessions.length > 0) {
        this.sessionStore.setActiveSession(data.sessions[0].id)
      }
      
      resolve()
    })

    this.socket!.emit('workspace:sync:request', {
      requestId: Date.now(),
      includeTerminals: true,
      includeHistory: false
    })
  })
}
```

#### Backend Response
```python
async def workspace_sync_request(sid, data=None):
    # 既存セッション取得
    sessions = await session_manager.list_sessions(user_id)
    
    # 既存ターミナル取得
    existing_terminals = []
    for session_id, terminal in AsyncioTerminal.sessions.items():
        if not terminal.closed:
            existing_terminals.append({...})
    
    # 応答送信
    await sio_instance.emit('workspace:sync:response', {
        'sessions': [session.to_dict() for session in sessions],
        'existingTerminals': existing_terminals,
        'currentUser': {...},
        'timestamp': datetime.now().isoformat()
    }, room=sid)
```

### 4. ターミナル作成タイミング制御

#### 修正前：接続後即座作成
```typescript
socketInstance.on('connect', () => {
  // 即座にターミナル作成（問題）
  socketInstance.emit('create_terminal', {
    session: session.value.id || '',
    user: '',
    path: ''
  });
})
```

#### 修正後：セッション管理後に作成
```typescript
socketInstance.on('connect', () => {
  // ターミナル作成はしない
  // セッション管理層が適切なタイミングで作成
})

// TabManagerでユーザー操作時に作成
const createTerminalTab = () => {
  const newTab = sessionStore.createTerminalTab(...)
  sessionStore.addTab(props.session.id, newTab)
  
  // サーバーに通知
  sessionSocketService.requestTabCreation(props.session.id, newTab)
}
```

## イベントフロー

### Socket.IO Events

#### Frontend → Backend
- `workspace:sync:request` - ワークスペース同期要求
- `session:create` - 新セッション作成
- `tab:create` - 新タブ作成
- `terminal:create` - 新ターミナル作成

#### Backend → Frontend  
- `workspace:sync:response` - ワークスペース状態応答
- `session:created` - セッション作成完了
- `tab:created` - タブ作成完了
- `terminal:created` - ターミナル作成完了

## ファイル構成

### Frontend
- `frontend/src/main.ts` - アプリ初期化
- `frontend/src/components/SessionManager.vue` - セッション管理・初期化
- `frontend/src/components/TabManager.vue` - タブ管理
- `frontend/src/services/SessionSocketService.ts` - Socket通信
- `frontend/src/stores/sessionStore.ts` - セッション状態管理

### Backend
- `src/aetherterm/agentserver/socket_handlers.py` - Socket.IOハンドラー
- `src/aetherterm/agentserver/server.py` - イベント登録
- `src/aetherterm/agentserver/services/session_manager.py` - セッション管理

## デバッグ

### フロントエンド
```typescript
// SessionManager.vue
console.log('SessionManager: Starting workspace initialization...')
console.log('SessionManager: Connecting to AgentServer...')
console.log('SessionManager: Requesting workspace sync...')
console.log(`SessionManager: Workspace restored with ${sessionStore.sessions.length} existing sessions`)
```

### バックエンド
```python
# socket_handlers.py
log.info(f"Workspace sync requested by client {sid}")
log.info(f"Sending workspace sync response: {len(sessions)} sessions, {len(existing_terminals)} terminals")
```

## トラブルシューティング

### 1. ワークスペース同期が失敗する
- Socket.IO接続状態を確認
- `workspace:sync:request`イベントが送信されているか確認
- バックエンドで`workspace_sync_request`ハンドラーが登録されているか確認

### 2. セッションが復元されない
- `session_manager.list_sessions()`が正しいデータを返しているか確認
- `sessionStore.addSession()`が呼ばれているか確認

### 3. ターミナルが作成されない
- TabManagerでタブ作成が正しく行われているか確認
- `terminal:create`イベントが送信されているか確認
- バックエンドでターミナル作成ハンドラーが動作しているか確認

## パフォーマンス考慮事項

### 最適化
- **段階的初期化**: 必要最小限の情報から順次拡張
- **タイムアウト処理**: ワークスペース同期の10秒タイムアウト
- **フォールバック**: 同期失敗時の新セッション作成
- **非同期処理**: 複数の初期化処理を並行実行

### 推奨設定
- ワークスペース同期タイムアウト: 10秒
- 復元確認待ち時間: 1秒
- セッション作成リトライ: 3回

## 関連ドキュメント

- [Socket.IO Tracing Implementation](./SOCKET_IO_TRACING.md)
- [Session Management Architecture](./SESSION_MANAGEMENT.md)
- [Terminal Factory Pattern](./TERMINAL_FACTORY.md)

## 更新履歴

- **2025-01-22**: 初版作成
- **修正内容**: ワークスペース初期化フロー修正
- **解決問題**: プロンプト表示問題、セッション復元問題