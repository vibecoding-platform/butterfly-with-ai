# AetherTerm Clean Architecture 分類

## 最終アーキテクチャ構成

### Interface Layer (インターフェース層)
**責任**: 外部からの入力を受け取り、アプリケーション層に渡す薄いアダプター

```
src/aetherterm/agentserver/
├── socket_handlers.py          # Socket.IO WebSocket handlers
├── routes.py                   # HTTP API routes  
└── server.py                   # ASGI application setup

frontend/src/
├── components/
│   ├── TerminalComponent.vue   # Terminal UI component
│   ├── ThemeSelector.vue       # Theme settings UI
│   └── ChatComponent.vue       # Chat interface
├── stores/
│   ├── themeStore.ts          # Theme state management
│   ├── terminalStore.ts       # Terminal state management
│   └── workspaceStore.ts      # Workspace state management
└── services/
    └── AetherTermService.ts   # Frontend API client
```

### Application Layer (アプリケーション層)
**責任**: ビジネスロジックとユースケースの実装

```
src/aetherterm/agentserver/services/
├── workspace_manager.py           # ワークスペース・ターミナル管理
├── agent_communication_service.py # エージェント通信・調整
├── report_service.py              # レポート生成・分析
└── theme_service.py               # テーマ・UI設定管理 (簡素化)

src/aetherterm/controlserver/
├── central_controller.py          # 中央制御サービス
└── log_summary_manager.py         # ログ要約管理
```

### Domain Layer (ドメイン層)
**責任**: ビジネスエンティティとドメインルール

```
src/aetherterm/common/
├── interfaces.py              # ドメインインターフェース
├── agent_protocol.py          # エージェント通信プロトコル
└── report_models.py           # レポートドメインモデル

src/aetherterm/agentserver/terminals/
├── base_terminal.py           # ターミナルエンティティ基底
└── default_terminal.py        # 標準ターミナル実装
```

### Infrastructure Layer (インフラストラクチャ層)
**責任**: 外部システムとの接続、永続化、技術的詳細

```
src/aetherterm/agentserver/
├── terminals/
│   └── asyncio_terminal.py        # ターミナル実装 (PTY, 非同期I/O)
├── short_term_memory.py           # 短期記憶 (Redis/メモリ永続化)
├── ai_services.py                 # AI サービス統合
├── auto_blocker.py                # 自動ブロック機能
├── ssl_setup.py                   # SSL/TLS設定
└── services/
    ├── inventory_service.py       # インベントリ外部API
    └── steampipe_client.py        # Steampipe クライアント

src/aetherterm/logprocessing/
├── log_processing_manager.py      # ログ処理マネージャー
├── log_processor.py               # ログプロセッサー
├── structured_extractor.py        # 構造化抽出
└── terminal_log_capture.py        # ターミナルログキャプチャ

src/aetherterm/langchain/
├── memory/                        # LangChain メモリ管理
├── storage/                       # ベクター・SQL・Redis ストレージ
└── config/                        # LangChain 設定
```

## 依存関係の方向

```
Interface Layer (socket_handlers.py, Vue components)
    ↓ (依存)
Application Layer (services/)
    ↓ (依存)  
Domain Layer (entities, protocols)
    ↑ (実装)
Infrastructure Layer (terminals/, storage/, external APIs)
```

## 主要な改善点

### 1. Socket.IO ハンドラの簡素化
**Before (1800+ lines)**:
```python
# socket_handlers.py
async def create_terminal(sid, data):
    # 200+ lines of business logic
    session_id = data.get("session")
    # Terminal creation logic
    # Session management logic  
    # Error handling logic
    # ...
```

**After (thin adapter)**:
```python
# socket_handlers.py  
async def create_terminal(sid, data):
    # 10-20 lines - delegating to service
    try:
        result = await workspace_manager.create_terminal(
            client_sid=sid,
            session_id=data.get("session"),
            # ... other params
        )
        await sio_instance.emit("terminal_ready", result, room=sid)
    except Exception as e:
        await sio_instance.emit("error", {"message": str(e)}, room=sid)
```

### 2. サービス層の責任分離

**WorkspaceManager**:
- ワークスペース/タブ/ペイン管理
- ターミナルセッション作成・復旧
- セッション所有権追跡

**AgentCommunicationService**:
- エージェント間メッセージング
- エージェント起動・初期化
- 仕様ドキュメント管理

**ReportService**:
- タイムラインレポート生成
- アクティビティ分析
- メトリクス収集・集約

**ThemeService** (簡素化):
- ローカルストレージベースのテーマ管理
- プリセット色スキーム提供

### 3. テーマシステムの統合

**Frontend Integration**:
```typescript
// themeStore.ts - Pinia store
const themeStore = useThemeStore()
await themeStore.setThemeMode('dark')
await themeStore.setColorScheme('dracula')
```

**CSS Variables**:
```css
.terminal {
  background-color: var(--terminal-background);
  color: var(--terminal-foreground);
  font-family: var(--terminal-font-family);
}
```

## 定量的な改善

- **Code Reduction**: socket_handlers.pyから500+行削除
- **Service Separation**: 4つの独立サービスクラスに分割
- **Testability**: 各サービス層が単体テスト可能
- **Maintainability**: 責任が明確に分離
- **Theme System**: 8色スキーム、設定永続化対応

## 次期改善案

1. **Socket.IO Handler完全リファクタリング**
   - 残りのハンドラ関数をサービス層委譲に変換
   
2. **エラーハンドリング標準化**
   - 統一したエラーレスポンス形式
   - ログ出力の標準化

3. **テスト追加**
   - サービス層のユニットテスト
   - 統合テストの拡充

4. **パフォーマンス最適化**
   - WebSocket イベントの選択的ブロードキャスト
   - セッション管理の最適化

この構成により、AetherTermプラットフォームはClean Architectureの原則に従った保守しやすい構造になりました。