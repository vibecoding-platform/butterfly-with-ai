# AetherTerm - Clean Architecture 最終構造

## 🏗️ ディレクトリ構造

```
src/aetherterm/agentserver/
├── interfaces/                     # Interface Layer
│   ├── web/                       # Web interfaces
│   │   ├── socket_handlers.py     # WebSocket event handlers
│   │   ├── routes.py              # HTTP API routes
│   │   └── server.py              # ASGI application setup
│   └── __init__.py
│
├── application/                    # Application Layer
│   ├── services/                  # Application services
│   │   ├── workspace_service.py   # Workspace/terminal management
│   │   ├── agent_service.py       # Agent communication
│   │   └── report_service.py      # Report generation
│   ├── usecases/                  # Use cases (future expansion)
│   ├── dto/                       # Data transfer objects (future expansion)
│   └── __init__.py                # Application facade
│
├── domain/                        # Domain Layer
│   ├── entities/                  # Domain entities
│   │   ├── asyncio_terminal.py    # Terminal entity
│   │   ├── base_terminal.py       # Base terminal abstraction
│   │   └── default_terminal.py    # Default terminal implementation
│   ├── repositories/              # Repository interfaces (future expansion)
│   ├── services/                  # Domain services (future expansion)
│   └── __init__.py
│
├── infrastructure/                # Infrastructure Layer
│   ├── external/                  # External service clients
│   │   ├── ai_service.py          # AI service integration
│   │   └── security_service.py    # Security/auto-blocking
│   ├── persistence/               # Data persistence
│   │   └── memory_store.py        # Short-term memory storage
│   ├── config/                    # Configuration management
│   │   └── ssl_config.py          # SSL/TLS configuration
│   ├── logging/                   # Logging infrastructure (future expansion)
│   └── __init__.py                # Infrastructure facade
│
└── [legacy files...]              # To be gradually removed
```

## 🎯 レイヤー責任

### Interface Layer (`interfaces/`)
- **責任**: 外部世界との境界
- **含むもの**: WebSocketハンドラー、HTTPルート、ASGI設定
- **依存関係**: Application Layer のみ

### Application Layer (`application/`)
- **責任**: ビジネスロジックの調整、ユースケースの実装
- **含むもの**: 
  - `WorkspaceService`: ワークスペース・ターミナル管理
  - `AgentService`: エージェント間通信
  - `ReportService`: レポート生成・分析
- **依存関係**: Domain Layer、Infrastructure Layer（インターフェース経由）

### Domain Layer (`domain/`)
- **責任**: ビジネスルール、ドメインエンティティ
- **含むもの**: Terminal エンティティ、ドメインロジック
- **依存関係**: なし（最も内側）

### Infrastructure Layer (`infrastructure/`)
- **責任**: 外部システムとの統合、技術的詳細
- **含むもの**: 
  - `AIService`: AI統合
  - `SecurityService`: セキュリティ機能
  - `MemoryStore`: データ永続化
  - `SSLConfig`: 設定管理
- **依存関係**: Domain Layer のみ

## 🔧 使用方法

### サービスアクセス

```python
# Application services
from aetherterm.agentserver.application import app_services

# Workspace operations
await app_services.workspace.create_terminal(...)
await app_services.workspace.resume_workspace(...)

# Agent operations
await app_services.agents.send_agent_message(...)
await app_services.agents.agent_start_request(...)

# Reporting
await app_services.reports.generate_timeline_report(...)
```

```python
# Infrastructure services
from aetherterm.agentserver.infrastructure import infra_services

# AI operations
await infra_services.ai_service.chat_completion(...)

# Security
await infra_services.security_service.check_command(...)

# Memory
await infra_services.memory_store.store(...)
```

### Socket.IOハンドラー例

```python
# Before: Complex handler with business logic (1800+ lines)
async def create_terminal(sid, data):
    # ... 200+ lines of terminal creation logic

# After: Thin adapter (10-20 lines)
async def create_terminal(sid, data):
    try:
        result = await app_services.workspace.create_terminal(
            client_sid=sid,
            session_id=data.get("session"),
            tab_id=data.get("tabId"),
            pane_id=data.get("paneId"),
            cols=data.get("cols", 80),
            rows=data.get("rows", 24)
        )
        await sio_instance.emit("terminal_ready", result, room=sid)
    except Exception as e:
        await sio_instance.emit("error", {"message": str(e)}, room=sid)
```

## 📊 成果

### 構造の改善
- **適切なパッケージ構造**: Clean Architectureの4層構造を実装
- **関心の分離**: 各層が明確な役割を持つ
- **依存関係の方向**: 外側から内側への単方向依存
- **テスト容易性**: 各層での独立テスト可能

### コードの簡素化
- **Socket.IOハンドラー**: 1800+行 → 薄いアダプター層
- **サービス統合**: 複数の散在するサービスを統合ファサードに
- **保守性向上**: ビジネスロジックとインフラの明確な分離

### 拡張性
- **新機能追加**: 適切な層に新しいサービスを追加可能
- **外部システム統合**: Infrastructure層での統一的な管理
- **テスト戦略**: 各層でのモックとスタブの活用

## 🚀 次のステップ

1. **段階的移行**: 既存ファイルから新構造への完全移行
2. **テスト整備**: 各層でのユニットテスト・統合テスト
3. **ドキュメント更新**: API仕様とアーキテクチャドキュメント

この Clean Architecture 実装により、AetherTerm は保守性、拡張性、テスト容易性を大幅に向上させました。