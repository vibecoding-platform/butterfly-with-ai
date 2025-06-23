# 階層型セッション管理システム設計 (一時文書)

## 概要
AetherTermにおけるtmux風の階層型タブ・ペーン管理とセッション間通信機能の設計・実装状況

## アーキテクチャ

### 階層構造
```
Session (セッション)
├── Tab1 (ターミナルタブ)
│   ├── Pane1 (ペーン)
│   └── Pane2 (ペーン)
├── Tab2 (AIアシスタントタブ)
└── Tab3 (ターミナルタブ)
    ├── Pane1 (ペーン)
    ├── Pane2 (ペーン)
    └── Pane3 (ペーン)
```

### サーバー駆動アーキテクチャ
- **Frontend** → **AgentServer** に要求送信
- **AgentServer** が状態管理・更新配信
- サーバー側からもセッション作成可能（AgentShell連携時など）

## 実装済み機能

### 1. データモデル (`src/aetherterm/agentserver/models/session.py`)
```python
@dataclass
class Session:
    id: str
    name: str
    owner: User
    connected_users: List[User]
    tabs: List[BaseTab]
    active_tab_id: Optional[str]
    settings: SessionSettings

@dataclass
class TerminalTab(BaseTab):
    panes: List[TerminalPane]
    active_pane_id: Optional[str]
    layout: str  # horizontal, vertical, grid

@dataclass
class TerminalPane:
    id: str
    terminal_id: str
    position: Dict[str, float]  # x, y, width, height
    is_active: bool
```

### 2. セッション管理サービス (`src/aetherterm/agentserver/services/session_manager.py`)
```python
class SessionManager:
    async def create_session(name, owner, settings) -> Session
    async def join_session(session_id, user, permission) -> bool
    async def create_tab(session_id, tab_type, title) -> BaseTab
    async def split_pane(session_id, tab_id, pane_id, direction) -> TerminalPane
    async def send_message(message: SessionMessage) -> bool
    async def auto_create_session_for_shell(shell_pid, shell_type) -> Session
```

### 3. Socket.IO API (`src/aetherterm/agentserver/socket_handlers.py`)
#### セッション管理
- `session:create` - セッション作成
- `session:join` - セッション参加
- `session:leave` - セッション離脱

#### タブ管理  
- `tab:create` - タブ作成
- `tab:switch` - タブ切り替え
- `tab:close` - タブ削除

#### ペーン管理
- `pane:split` - ペーン分割 (horizontal/vertical)
- `pane:close` - ペーン削除

#### セッション間通信
- `session:message:send` - メッセージ送信
- `session:message:received` - メッセージ受信

### 4. フロントエンド (`frontend/src/`)
#### 型定義 (`types/session.ts`)
```typescript
interface Session {
  id: string
  name: string
  connectedUsers: User[]
  tabs: (TerminalTab | AIAssistantTab)[]
  activeTabId?: string
  settings: SessionSettings
}

interface TerminalPane {
  id: string
  terminalId: string
  title: string
  position: PanePosition
  isActive: boolean
}
```

#### 状態管理 (`stores/sessionStore.ts`)
```typescript
// サーバー要求メソッド
const requestSessionCreation = (sessionData: Partial<Session>)
const requestSessionJoin = (sessionId: string, permission: string)
const requestTabCreation = (sessionId: string, tabData: any)
const requestPaneSplit = (sessionId: string, tabId: string, paneId: string, direction: string)

// サーバーイベント処理
const handleSessionCreated = (session: Session)
const handleTabCreated = (sessionId: string, tab: any)
const handlePaneCreated = (sessionId: string, tabId: string, pane: TerminalPane)
```

#### コンポーネント
- `SessionManager.vue` - セッション管理UI
- `TerminalPaneManager.vue` - tmux風ペーン管理
- `SessionCommunication.vue` - セッション間通信

## tmux風ペーン操作

### キーボードショートカット
- `Ctrl+B %` - 水平分割
- `Ctrl+B "` - 垂直分割  
- `Ctrl+B x` - ペーン削除
- `Ctrl+B o` - ペーン切り替え

### ペーン分割ロジック
```typescript
// 水平分割: 既存ペーンを50%に縮小、新ペーンを右側に配置
if (direction === 'horizontal') {
  sourcePane.position.width = 50
  newPane.position = { x: 50, y: sourcePane.position.y, width: 50, height: sourcePane.position.height }
}

// 垂直分割: 既存ペーンを50%に縮小、新ペーンを下側に配置  
if (direction === 'vertical') {
  sourcePane.position.height = 50
  newPane.position = { x: sourcePane.position.x, y: 50, width: sourcePane.position.width, height: 50 }
}
```

## セッション間通信

### メッセージタイプ
```typescript
enum MessageType {
  TEXT = "text",           // テキストメッセージ
  COMMAND = "command",     // コマンド送信
  FILE = "file",          // ファイル共有
  NOTIFICATION = "notification"  // 通知
}
```

### 通信フロー
1. ユーザーがメッセージ送信
2. `session:message:send` イベント送信
3. AgentServerが全参加者に `session:message:received` 配信
4. リアルタイムでメッセージ表示

## 外部統合

### AgentShell自動セッション作成
```python
async def auto_create_session_for_shell(shell_pid: int, shell_type: str = "bash"):
    user = User.create(user_id=f"shell-{shell_pid}", name=f"Shell User {shell_pid}")
    session = await session_manager.create_session(
        name=f"Shell Session {shell_pid}",
        owner=user,
        auto_created=True,
        metadata={"shell_pid": shell_pid, "shell_type": shell_type}
    )
    # 全クライアントに新セッション通知
    await sio_instance.emit('server:session:create', session.to_dict())
```

## 権限管理

### ユーザー権限
```python
class UserPermission(Enum):
    OWNER = "owner"          # 全操作可能
    COLLABORATOR = "collaborator"  # タブ・ペーン操作可能
    OBSERVER = "observer"    # 閲覧のみ
```

### アクション権限マッピング
```python
permission_actions = {
    UserPermission.OWNER: ["create_tab", "delete_tab", "split_pane", "close_pane", "manage_users"],
    UserPermission.COLLABORATOR: ["create_tab", "split_pane", "close_pane"],
    UserPermission.OBSERVER: []
}
```

## 未実装・次回実装項目

### 1. 永続化レイヤー
- Redis/Database統合
- セッション状態の永続化
- 履歴の長期保存

### 2. 認証統合
- 実際のユーザー認証システム連携
- JWT/OAuth統合
- セッション所有者検証

### 3. 高度な機能
- セッションクローン
- セッション共有リンク生成
- タブ/ペーンのドラッグ&ドロップ
- カスタムレイアウト保存

## 開発・テスト手順

### 1. サーバー起動 (circus使用)
```bash
# ログディレクトリ作成
mkdir -p logs

# フロントエンドビルド
make build-frontend

# circusでプロセス管理
circusd circus.ini
```

### 2. 動作確認
- ブラウザで `http://localhost:57575` アクセス
- セッション作成・参加をテスト
- ペーン分割操作をテスト  
- セッション間通信をテスト

### 3. デバッグ
```bash
# AgentServerログ確認
tail -f logs/agentserver.stdout.log
tail -f logs/agentserver.stderr.log

# フロントエンドログ確認  
tail -f logs/frontend.stdout.log
```

## 設定ファイル

### circus.ini
```ini
[watcher:agentserver]
cmd = uv run aetherterm --host localhost --port 57575 --unsecure --debug --more
working_dir = .

[watcher:frontend]  
cmd = pnpm run dev
working_dir = ./frontend
```

## ファイル構成

### 重要な実装ファイル
```
src/aetherterm/agentserver/
├── models/session.py              # データモデル
├── services/session_manager.py    # セッション管理サービス  
├── socket_handlers.py            # Socket.IOイベントハンドラー
└── utils/ssl_certs.py            # SSL証明書管理

frontend/src/
├── types/session.ts              # TypeScript型定義
├── stores/sessionStore.ts        # Pinia状態管理
├── services/SessionSocketService.ts  # Socket.IOクライアント
├── components/
│   ├── SessionManager.vue        # セッション管理UI
│   ├── TerminalPaneManager.vue   # tmux風ペーン管理
│   └── SessionCommunication.vue  # セッション間通信
```

### 修正済みファイル
- `src/aetherterm/agentserver/terminals/asyncio_terminal.py` - インポート修正
- `src/aetherterm/agentserver/main.py` - SSL証明書インポート修正

---

**ステータス**: 
- ✅ データモデル実装完了
- ✅ SessionManagerサービス実装完了  
- ✅ フロントエンド型定義・状態管理完了
- ✅ Circus起動・プロセス管理完了
- ✅ Socket.IOハンドラー実装完了 - session:create, session:join, tab:create, pane:split等
- ✅ エンドツーエンドテスト完了
- ✅ セッション作成・参加機能動作確認済み
- ✅ tmux風ペーン分割機能動作確認済み（水平・垂直分割）
- ✅ セッション間通信機能動作確認済み（text/command/notification）

**テスト結果**:
- ✅ `test_session_api.py` - セッション作成、階層構造（Session→Tab→Pane→Terminal）
- ✅ `test_pane_splitting.py` - ペーン分割（Ctrl+B %/Ctrl+B "相当）
- ✅ `test_session_communication.py` - メッセージ送受信

**階層型タブ管理システム実装完了** 🎉