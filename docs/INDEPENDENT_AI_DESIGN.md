# AetherTerm 独立AI設計

AetherTermプロジェクトの設計を修正し、AetherTermサーバーに依存しない独立したAIシェルシステムを構築しました。

## 主要設計変更：AI機能の独立性確保

### 1. アーキテクチャの修正

#### A. AI機能の独立化
**以前の問題**：
- AI連携がAetherTermサーバーに依存
- サーバーがないとAI機能が使用不可

**修正後**：
- AI機能を完全に独立させる
- 直接AIサービス（OpenAI、Claude等）と通信
- AetherTermサーバーはオプショナルな拡張機能として位置づけ

#### B. 新しいクラス設計
```
src/aetherterm/shell/service/
├── ai_providers.py (AIプロバイダーの抽象化)
├── ai_service.py (独立したAIサービス)
├── server_connector.py (オプショナルなサーバー連携)
├── shell_agent.py (統合エージェント)
└── session_service.py (セッション管理)
```

### 2. AI機能の独立実装

#### A. 独立したAIサービス (`ai_service.py`)
**機能**：
- 直接AIプロバイダー（OpenAI、Anthropic等）と通信
- ターミナル出力の解析
- エラー検出と解決提案
- コマンド提案
- AetherTermサーバーに依存しない

**設定例**：
```toml
[ai_service]
provider = "openai"  # openai, anthropic, local
api_key = "your-api-key"
model = "gpt-4"
endpoint = ""  # カスタムエンドポイント対応
```

#### B. AIプロバイダーの抽象化 (`ai_providers.py`)
- `AIProvider`インターフェース
- `OpenAIProvider`, `AnthropicProvider`, `LocalProvider`実装
- プロバイダーの動的切り替え

### 3. オプショナルなサーバー連携

#### A. サーバーコネクター (`server_connector.py`)
**役割**：
- AetherTermサーバーとの連携（オプション）
- セッション情報の同期
- フロントエンドとの連携
- サーバーがない場合は無効化

**動作モード**：
1. **スタンドアロンモード**: サーバーなし、AI機能のみ
2. **連携モード**: サーバーあり、フロントエンド連携も可能

#### B. 設定による切り替え
```toml
[server_connection]
enabled = false  # デフォルトは無効
endpoint = "ws://localhost:57575"
auto_connect = true
retry_interval = 5
```

### 4. ShellAgent（統合エージェント）の設計

#### A. 責任の明確化
**主要責任**：
1. **ローカルセッション管理**: PID追跡、状態管理
2. **AI連携調整**: AIサービスとの連携
3. **オプショナルサーバー連携**: サーバーがある場合のみ

#### B. 依存関係の整理
```python
class AetherTermShellAgent:
    def __init__(self, ai_service: IndependentAIService, server_connector: Optional[ServerConnector] = None):
        self.ai_service = ai_service  # 必須
        self.server_connector = server_connector  # オプション
```

### 5. 設定システムの拡張

#### A. 動作モードの設定
```toml
[shell]
mode = "standalone"  # standalone, connected
ai_enabled = true
server_enabled = false

[ai_service]
provider = "openai"
# ... AI設定

[server_connection]
enabled = false
# ... サーバー設定（オプション）
```

#### B. 環境変数による制御
```bash
# スタンドアロンモード
AETHERTERM_MODE=standalone
AETHERTERM_AI_PROVIDER=openai
AETHERTERM_AI_API_KEY=your-key

# 連携モード
AETHERTERM_MODE=connected
AETHERTERM_SERVER_ENABLED=true
AETHERTERM_SERVER_URL=ws://localhost:57575
```

## 使用方法

### A. スタンドアロンモード（AIのみ）
```bash
# 設定ファイル使用
uv run aetherterm-shell --config standalone.toml

# 環境変数使用
AETHERTERM_MODE=standalone AETHERTERM_AI_PROVIDER=openai uv run aetherterm-shell

# コマンドライン引数使用
uv run aetherterm-shell --mode standalone --ai-provider openai --api-key your-key
```

### B. 連携モード（AI + サーバー）
```bash
# 設定ファイル使用
uv run aetherterm-shell --config connected.toml

# 環境変数使用
AETHERTERM_MODE=connected AETHERTERM_SERVER_ENABLED=true uv run aetherterm-shell

# コマンドライン引数使用
uv run aetherterm-shell --mode connected --server-url http://localhost:57575
```

## 設定ファイル

### スタンドアロンモード設定 (`standalone.toml`)
```toml
mode = "standalone"
enable_ai = true

[ai_service]
provider = "openai"
api_key = ""
model = "gpt-4"

[server_connection]
enabled = false
```

### 連携モード設定 (`connected.toml`)
```toml
mode = "connected"
enable_ai = true

[ai_service]
provider = "openai"
api_key = ""
model = "gpt-4"

[server_connection]
enabled = true
server_url = "http://localhost:57575"
```

## AIプロバイダー

### OpenAI
```bash
AETHERTERM_AI_PROVIDER=openai
AETHERTERM_AI_API_KEY=sk-...
AETHERTERM_AI_MODEL=gpt-4
```

### Anthropic Claude
```bash
AETHERTERM_AI_PROVIDER=anthropic
AETHERTERM_AI_API_KEY=sk-ant-...
AETHERTERM_AI_MODEL=claude-3-sonnet-20240229
```

### ローカルAI (Ollama)
```bash
AETHERTERM_AI_PROVIDER=local
AETHERTERM_AI_ENDPOINT=http://localhost:11434
AETHERTERM_AI_MODEL=llama2
```

## 利点

この設計により、AetherTermシェルは：

1. **独立したAIシェル**として単体で価値を提供
2. **AetherTermサーバーとの連携**でさらなる機能を提供
3. **柔軟な設定**で様々な環境に対応
4. **プロバイダー選択**でコストと性能を最適化
5. **段階的導入**でリスクを最小化

## トラブルシューティング

### AI機能が動作しない
1. APIキーが正しく設定されているか確認
2. プロバイダーのエンドポイントが正しいか確認
3. ネットワーク接続を確認

### サーバー連携が動作しない
1. サーバーが起動しているか確認
2. サーバーURLが正しいか確認
3. ファイアウォール設定を確認

### 設定が反映されない
1. 環境変数の優先順位を確認
2. 設定ファイルのパスが正しいか確認
3. デバッグモードで詳細ログを確認