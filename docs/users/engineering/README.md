# 👨‍💻 エンジニアレベル - 技術活用・実装

**対象読者**: システム利用者・技術者・運用エンジニア・開発者

AetherTermの実際の利用方法、設定、カスタマイズ、技術的活用について説明します。

## 📋 ドキュメント構成

### 🚀 セットアップ・基本操作
- **[NEXT_SESSION_STARTUP_GUIDE.md](./NEXT_SESSION_STARTUP_GUIDE.md)** 🟢 Ready
  - 環境構築・初期設定手順
  - セッション開始・基本操作
  - トラブルシューティング

- **[BASIC_OPERATION_TEST.md](./BASIC_OPERATION_TEST.md)** 🟢 Ready
  - 基本機能の動作確認テスト
  - 設定検証・接続テスト
  - パフォーマンス確認

### ⚙️ 設定・カスタマイズ
- **[AGENTSERVER_MODES_AND_CONFIG.md](./AGENTSERVER_MODES_AND_CONFIG.md)** 🟢 Ready
  - AgentServerの動作モード設定
  - 機能のOn/Off制御
  - TOML設定ファイル詳細

- **[AETHERTERM_SHELL_MODES.md](./AETHERTERM_SHELL_MODES.md)** 🟢 Ready
  - シェルモード・ターミナル設定
  - 環境変数・パス設定
  - カスタムコマンド設定

### 🤖 AI機能活用 *(計画中)*
- **AI支援開発環境** 🔴 TODO
  - AIペアプログラミング設定
  - コード補完・提案機能
  - 自動テスト・デバッグ支援

### 📡 API・統合 *(計画中)*
- **外部システム連携** 🔴 TODO
  - REST API活用方法
  - WebSocket統合
  - 既存ツールとの連携

## 🛠️ 技術スタック

### 💻 フロントエンド
```
Vue.js 3 + TypeScript + Vite
    ↓
Pinia (状態管理) + xterm.js (ターミナル)
    ↓
Socket.IO (リアルタイム通信)
```

### 🔧 バックエンド
```
Python FastAPI + Socket.IO
    ↓
AsyncIO (非同期処理) + PTY (擬似端末)
    ↓
依存性注入 + モジュラー設計
```

### 🤖 AI統合
```
Anthropic Claude / OpenAI
    ↓
LangChain (AI記憶・検索)
    ↓
Vector DB (埋め込み・検索)
```

## 🚀 クイックスタート

### 1️⃣ 環境準備
```bash
# リポジトリクローン
git clone https://github.com/aether-platform/aetherterm.git
cd aetherterm

# 依存関係インストール
make install

# フロントエンドビルド
make build-frontend
```

### 2️⃣ 設定ファイル作成
```bash
# デフォルト設定をコピー
cp src/aetherterm/aetherterm.toml.default src/aetherterm/aetherterm.toml

# 必要に応じて編集
vim src/aetherterm/aetherterm.toml
```

### 3️⃣ サーバー起動
```bash
# 開発モード起動
make run-debug

# または手動起動
python src/aetherterm/agentserver/main.py --host=localhost --port=57575 --debug
```

### 4️⃣ ブラウザアクセス
```
http://localhost:57575
```

## ⚙️ 設定カスタマイズ

### 🔧 TOML設定の主要項目

```toml
[features]
ai_enabled = true                    # AI機能全体のON/OFF
multi_tab_enabled = true             # 複数タブ機能
supervisor_panel_enabled = true      # 管理パネル

[ai.chat]
enabled = true                       # AIチャット機能
provider = "anthropic"               # AIプロバイダー
model = "claude-3-5-sonnet-20241022" # 使用モデル

[ui]
theme = "dark"                       # UIテーマ
panel_position = "right"             # パネル位置
panel_width = 320                    # パネル幅
```

### 🌍 環境変数による制御
```bash
# AI機能制御
export AETHERTERM_AI_ENABLED=true
export ANTHROPIC_API_KEY="your-api-key"

# サーバー設定
export AETHERTERM_HOST=localhost
export AETHERTERM_PORT=57575
export AETHERTERM_DEBUG=true
```

## 🤖 AI機能活用

### 💬 AIチャット
```
機能: ターミナル操作のAI支援
用途: 
- コマンド提案・説明
- エラー解決支援  
- コード生成・レビュー
- 技術質問・相談
```

### 📊 AI自動セッション管理
```
機能: AIによる自動タブ作成・管理
用途:
- 目的別セッション自動分類
- 時系列でのタスク追跡
- 関連作業のグルーピング
- 作業履歴の可視化
```

### 🔍 AgentShell統合
```
機能: AI自動実行エンジン
用途:
- 繰り返し作業の自動化
- バックグラウンドタスク実行
- システム監視・メンテナンス
- デプロイ・テスト自動化
```

## 🔌 統合・拡張

### 📡 API利用例
```javascript
// WebSocket接続
const socket = io('ws://localhost:57575');

// ターミナル出力の監視
socket.on('terminal_output', (data) => {
  console.log('Output:', data);
});

// コマンド送信
socket.emit('terminal_input', {
  session_id: 'session-123',
  data: 'ls -la\n'
});
```

### 🛠️ カスタムプラグイン
```python
# カスタムAIハンドラー例
from aetherterm.agentserver.ai_services import AIService

class CustomAIService(AIService):
    async def process_message(self, message: str) -> str:
        # カスタムAI処理
        return f"Custom response: {message}"
```

## 🧪 テスト・検証

### ✅ 基本機能テスト
```bash
# 接続テスト
curl http://localhost:57575/health

# WebSocket接続テスト  
wscat -c ws://localhost:57575/socket.io/

# AI機能テスト
python -m pytest tests/ai/
```

### 📊 パフォーマンステスト
```bash
# 負荷テスト
ab -n 1000 -c 10 http://localhost:57575/

# メモリ・CPU使用量監視
htop
iostat -x 1
```

## 🐛 トラブルシューティング

### ❌ よくある問題と解決方法

| 問題 | 原因 | 解決方法 |
|------|------|----------|
| **起動しない** | ポート競合 | `--port` オプションで変更 |
| **AIが動かない** | API Key未設定 | 環境変数 `ANTHROPIC_API_KEY` 設定 |
| **画面が表示されない** | フロントエンド未ビルド | `make build-frontend` 実行 |
| **WebSocket接続エラー** | CORS設定 | 設定ファイルの `cors_allowed_origins` 確認 |

### 🔍 デバッグ方法
```bash
# デバッグモード起動
python src/aetherterm/agentserver/main.py --debug --more

# ログレベル変更
export AETHERTERM_LOG_LEVEL=DEBUG

# 詳細ログ出力
tail -f logs/aetherterm.log
```

## 🔄 アップグレード・メンテナンス

### 📦 バージョンアップ
```bash
# 最新版取得
git pull origin main

# 依存関係更新
make install

# フロントエンド再ビルド
make build-frontend

# 設定ファイル確認
diff src/aetherterm/aetherterm.toml.default src/aetherterm/aetherterm.toml
```

### 🧹 定期メンテナンス
```bash
# ログローテーション
logrotate /etc/logrotate.d/aetherterm

# データベースクリーンアップ
python scripts/cleanup_old_sessions.py

# パフォーマンス分析
python scripts/performance_report.py
```

---

📈 **次に読むべきドキュメント**:
- システム管理・運用 → [🛡️ 情シス・管理レベル](../operations/)
- ビジネス価値・戦略 → [🏢 ビジネスレベル](../business/)
- 内部開発・貢献 → [🔧 開発者向けドキュメント](../../developers/)