# AetherTermShell 動作モード マニュアル

## 概要

AetherTermShellは、ターミナル環境にAI機能を統合する独立したシェルシステムです。3つの動作モードを提供し、用途に応じて柔軟に設定できます。

## 前提条件

### 共通前提条件
- Python 3.9以上
- uv パッケージマネージャー

### モード別前提条件

| モード | 追加前提条件 |
|--------|-------------|
| **DoNothing** | なし |
| **StandAlone (ローカルLLM)** | Ollama等のローカルLLMサーバー |
| **StandAlone (クラウドAI)** | AIプロバイダーのAPIキー |
| **Connected** | AetherTerminalServer + OpenTelemetry（推奨） |

> **注意**: ConnectedモードではOpenTelemetryによるテレメトリー機能が有効になります。OTLPエンドポイント（デフォルト: `http://localhost:4317`）が利用できない場合でも動作しますが、テレメトリーデータは収集されません。

## 動作モード一覧

| モード | 説明 | AI機能 | サーバー連携 | 用途 |
|--------|------|--------|-------------|------|
| **DoNothing** | AI機能なし | ❌ | ❌ | 通常のシェル環境 |
| **StandAlone** | 独立AI機能 | ✅ | ❌ | AI支援のみ |
| **Connected** | AI + サーバー連携 | ✅ | ✅ | フル機能 |

---

## 1. DoNothingモード

### 概要と用途

DoNothingモードは、AI機能を無効にした通常のBashシェル環境を提供します。

**用途:**
- AI機能が不要な場合
- リソース消費を最小限に抑えたい場合
- デバッグやテスト環境
- プライバシーを重視する環境

### 設定方法

#### 設定ファイル例 (`do-nothing.toml`)

```toml
# AetherTerm Shell - DoNothingモード設定
# AI機能なし、通常のシェル環境

# 動作モード設定
mode = "standalone"
debug = false
enable_ai = false  # AI機能を無効化

# AI サービス設定（無効）
[ai_service]
provider = "openai"
api_key = ""
model = "gpt-4"
endpoint = ""
timeout = 30
max_retries = 3

# AI機能設定（すべて無効）
enable_command_analysis = false
enable_error_suggestions = false
enable_command_suggestions = false
max_command_history = 0

# サーバー接続設定（無効）
[server_connection]
enabled = false
server_url = "http://localhost:57575"
auto_connect = false

# ターミナル監視設定（最小限）
[monitor]
buffer_size = 1024
poll_interval = 1.0
max_history = 10
enable_output_capture = false
enable_input_capture = false

# セッション管理設定
[session]
session_timeout = 3600
max_sessions = 10
cleanup_interval = 600
enable_persistence = false

# ログ設定
[logging]
level = "WARNING"
format = "%(asctime)s - %(levelname)s - %(message)s"
file_path = ""

# テレメトリー設定（無効）
[telemetry]
service_name = "aetherterm-shell-minimal"
service_version = "1.0.0"
environment = "production"
enable_tracing = false
enable_metrics = false
enable_log_instrumentation = false
```

#### 環境変数設定

```bash
# AI機能を無効化
export AETHERTERM_ENABLE_AI=false
export AETHERTERM_MODE=standalone
export AETHERTERM_DEBUG=false
```

#### 起動コマンド

```bash
# 設定ファイル使用
uv run aetherterm-shell --config do-nothing.toml

# 環境変数使用
AETHERTERM_ENABLE_AI=false uv run aetherterm-shell

# コマンドライン引数使用
uv run aetherterm-shell --mode standalone
```

### 動作の詳細

- **AI機能**: 完全に無効
- **リソース使用量**: 最小限
- **ターミナル監視**: 基本的な監視のみ
- **ログ出力**: 警告レベル以上のみ
- **テレメトリー**: 無効

---

## 2. StandAloneモード

### 2-1. ローカルLLM連携

#### 概要と用途

ローカルで動作するLLM（Large Language Model）と連携し、プライベートなAI支援機能を提供します。

**用途:**
- プライバシーを重視する環境
- インターネット接続が制限された環境
- 自社データでファインチューニングしたモデルの使用
- コスト削減（API料金不要）

#### 対応するローカルLLM

| LLM | エンドポイント | モデル例 | 特徴 |
|-----|---------------|----------|------|
| **Ollama** | `http://localhost:11434` | `llama2`, `codellama`, `mistral` | 簡単セットアップ |
| **LM Studio** | `http://localhost:1234` | `TheBloke/CodeLlama-7B-Instruct-GGML` | GUI管理 |
| **Text Generation WebUI** | `http://localhost:7860` | 各種HuggingFaceモデル | 高度な設定 |
| **vLLM** | `http://localhost:8000` | `meta-llama/Llama-2-7b-chat-hf` | 高性能推論 |

#### 設定方法

##### Ollama使用例

```toml
# AetherTerm Shell - ローカルLLM（Ollama）設定

# 動作モード設定
mode = "standalone"
debug = false
enable_ai = true

# AI サービス設定（ローカルLLM）
[ai_service]
provider = "local"
api_key = ""  # ローカルLLMでは不要
model = "llama2"  # または codellama, mistral
endpoint = "http://localhost:11434"
timeout = 60  # ローカルLLMは応答が遅い場合がある
max_retries = 2

# AI機能設定
enable_command_analysis = true
enable_error_suggestions = true
enable_command_suggestions = true
max_command_history = 20  # ローカルLLMでは少なめに

# サーバー接続設定（無効）
[server_connection]
enabled = false

# ターミナル監視設定
[monitor]
buffer_size = 4096
poll_interval = 0.2
max_history = 500
enable_output_capture = true
enable_input_capture = false

# ログ設定
[logging]
level = "INFO"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
file_path = "/tmp/aetherterm-local.log"

# テレメトリー設定（無効）
[telemetry]
enable_tracing = false
enable_metrics = false
```

##### 環境変数設定

```bash
# ローカルLLM設定
export AETHERTERM_MODE=standalone
export AETHERTERM_AI_PROVIDER=local
export AETHERTERM_AI_ENDPOINT=http://localhost:11434
export AETHERTERM_AI_MODEL=llama2
export AETHERTERM_ENABLE_AI=true
```

##### 起動手順

> **重要**: Ollamaは事前に手動で起動する必要があります。AetherTermShellからの自動起動機能はありません。

1. **Ollamaのセットアップ**
```bash
# Ollamaのインストール
curl -fsSL https://ollama.ai/install.sh | sh

# モデルのダウンロード
ollama pull llama2
ollama pull codellama

# Ollamaサーバーの起動（必須）
ollama serve
```

2. **Ollamaの動作確認**
```bash
# Ollamaが正常に起動しているか確認
curl http://localhost:11434/api/tags

# 利用可能なモデルを確認
ollama list
```

3. **AetherTermShellの起動**
```bash
# 設定ファイル使用
uv run aetherterm-shell --config local-llm.toml

# 環境変数使用
AETHERTERM_AI_PROVIDER=local AETHERTERM_AI_ENDPOINT=http://localhost:11434 uv run aetherterm-shell
```

#### 使用例

```bash
# エラーが発生した場合、自動的にローカルLLMが解析
$ npm install non-existent-package
# → AI分析: "パッケージが存在しません。typoの可能性があります。"

# コマンド履歴に基づく提案
$ git add .
$ git commit -m "initial commit"
# → AI提案: "git push origin main を実行してリモートにプッシュしますか？"
```

### 2-2. サーバーサイドLLM連携

#### 概要と用途

OpenAI、Anthropic等のクラウドAIサービスと直接連携し、高性能なAI支援機能を提供します。

**用途:**
- 高品質なAI支援が必要な場合
- 最新のAI技術を活用したい場合
- 開発効率を最大化したい場合
- 複雑なコマンド解析が必要な場合

#### 対応するLLMプロバイダー

| プロバイダー | モデル例 | 特徴 | API料金 |
|-------------|----------|------|---------|
| **OpenAI** | `gpt-4`, `gpt-3.5-turbo` | 高品質、豊富な機能 | 従量課金 |
| **Anthropic** | `claude-3-sonnet`, `claude-3-haiku` | 安全性重視、長文対応 | 従量課金 |
| **Google** | `gemini-pro` | マルチモーダル対応 | 従量課金 |
| **Azure OpenAI** | `gpt-4`, `gpt-35-turbo` | エンタープライズ向け | 従量課金 |

#### 設定方法

##### OpenAI使用例

```toml
# AetherTerm Shell - OpenAI連携設定

# 動作モード設定
mode = "standalone"
debug = false
enable_ai = true

# AI サービス設定（OpenAI）
[ai_service]
provider = "openai"
api_key = ""  # 環境変数 AETHERTERM_AI_API_KEY で設定推奨
model = "gpt-4"
endpoint = ""  # デフォルトエンドポイント使用
timeout = 30
max_retries = 3

# AI機能設定
enable_command_analysis = true
enable_error_suggestions = true
enable_command_suggestions = true
max_command_history = 50

# サーバー接続設定（無効）
[server_connection]
enabled = false

# ターミナル監視設定
[monitor]
buffer_size = 8192
poll_interval = 0.1
max_history = 1000
enable_output_capture = true
enable_input_capture = false

# ログ設定
[logging]
level = "INFO"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
file_path = "/tmp/aetherterm-openai.log"

# テレメトリー設定
[telemetry]
service_name = "aetherterm-shell-openai"
enable_tracing = true
enable_metrics = true
```

##### Anthropic使用例

```toml
# AetherTerm Shell - Anthropic Claude連携設定

# AI サービス設定（Anthropic）
[ai_service]
provider = "anthropic"
api_key = ""  # 環境変数 AETHERTERM_AI_API_KEY で設定推奨
model = "claude-3-sonnet-20240229"
endpoint = ""  # デフォルトエンドポイント使用
timeout = 45  # Claudeは応答が遅い場合がある
max_retries = 3
```

##### 環境変数設定

```bash
# OpenAI設定
export AETHERTERM_MODE=standalone
export AETHERTERM_AI_PROVIDER=openai
export AETHERTERM_AI_API_KEY=sk-your-openai-api-key
export AETHERTERM_AI_MODEL=gpt-4
export AETHERTERM_ENABLE_AI=true

# Anthropic設定
export AETHERTERM_AI_PROVIDER=anthropic
export AETHERTERM_AI_API_KEY=your-anthropic-api-key
export AETHERTERM_AI_MODEL=claude-3-sonnet-20240229

# Azure OpenAI設定
export AETHERTERM_AI_PROVIDER=openai
export AETHERTERM_AI_ENDPOINT=https://your-resource.openai.azure.com/
export AETHERTERM_AI_API_KEY=your-azure-api-key
export AETHERTERM_AI_MODEL=gpt-4
```

#### 起動コマンド

```bash
# OpenAI使用
AETHERTERM_AI_PROVIDER=openai AETHERTERM_AI_API_KEY=sk-xxx uv run aetherterm-shell

# Anthropic使用
AETHERTERM_AI_PROVIDER=anthropic AETHERTERM_AI_API_KEY=your-key uv run aetherterm-shell

# 設定ファイル使用
uv run aetherterm-shell --config openai.toml
```

#### 使用例

```bash
# 複雑なエラーの解析
$ docker build -t myapp .
ERROR: failed to solve: failed to compute cache key: "/app/package.json" not found
# → AI分析: "Dockerfileでpackage.jsonをCOPYする前にWORKDIRを設定する必要があります"

# 高度なコマンド提案
$ find . -name "*.py" | head -5
# → AI提案: "Pythonファイルの静的解析を行いますか？ pylint や flake8 の実行を提案します"
```

---

## 3. AetherTerminalServer連携モード (Connected)

### 概要と用途

AetherTermShellとAetherTerminalServerが連携し、WebターミナルとAI機能を統合したフル機能を提供します。

**用途:**
- Webブラウザからのターミナルアクセス
- チーム開発での共有ターミナル環境
- リモート開発環境
- AI機能とWeb UIの統合利用

### 前提条件

#### 必須前提条件
- **AetherTerminalServer**: Webターミナル機能を提供
- **AIプロバイダー**: OpenAI、Anthropic等のAPIキー

#### 推奨前提条件
- **OpenTelemetry Collector**: テレメトリーデータ収集（`http://localhost:4317`）
- **Jaeger/Zipkin**: 分散トレーシング可視化
- **Prometheus**: メトリクス収集

> **注意**: OpenTelemetryエンドポイントが利用できない場合でも動作しますが、以下の警告が表示されます：
> ```
> WARNING - OTLPトレースエクスポーターの設定に失敗しました
> WARNING - OTLPメトリクスエクスポーターの設定に失敗しました
> ```

### Webターミナルとの統合

Connected モードでは以下の統合機能を提供します：

- **リアルタイム同期**: ターミナル出力とAI分析結果をWebUIに表示
- **セッション共有**: 複数のWebクライアント間でセッション共有
- **AI通知**: エラーや提案をWeb UIに通知
- **履歴同期**: コマンド履歴をサーバーと同期

### 設定方法

#### 設定ファイル例 (`connected.toml`)

```toml
# AetherTerm Shell - 連携モード設定
# AIシェル + AetherTermサーバー連携

# 動作モード設定
mode = "connected"
debug = false
enable_ai = true

# AI サービス設定（独立動作）
[ai_service]
provider = "openai"  # openai, anthropic, local
api_key = ""  # 環境変数 AETHERTERM_AI_API_KEY で設定推奨
model = "gpt-4"
endpoint = ""
timeout = 30
max_retries = 3

# AI機能設定
enable_command_analysis = true
enable_error_suggestions = true
enable_command_suggestions = true
max_command_history = 50

# サーバー接続設定（連携モードでは有効）
[server_connection]
enabled = true
server_url = "http://localhost:57575"
auto_connect = true
sync_interval = 30
reconnection_attempts = 5
reconnection_delay = 1

# 同期機能設定
sync_sessions = true
sync_ai_notifications = true
sync_command_history = false  # プライバシー考慮でデフォルトOFF

# ターミナル監視設定
[monitor]
buffer_size = 8192
poll_interval = 0.1
max_history = 1000
enable_output_capture = true
enable_input_capture = false

# セッション管理設定
[session]
session_timeout = 3600  # 1時間
max_sessions = 100
cleanup_interval = 300  # 5分
enable_persistence = true

# ログ設定
[logging]
level = "INFO"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
file_path = "/tmp/aetherterm-connected.log"

# OpenTelemetry設定
[telemetry]
service_name = "aetherterm-shell-connected"
service_version = "1.0.0"
environment = "development"
otlp_endpoint = "http://localhost:4317"
enable_tracing = true  # 連携モードではデフォルトON
enable_metrics = true
enable_log_instrumentation = true
trace_sample_rate = 1.0
metrics_export_interval = 30
```

#### 環境変数設定

```bash
# 連携モード設定
export AETHERTERM_MODE=connected
export AETHERTERM_AI_PROVIDER=openai
export AETHERTERM_AI_API_KEY=sk-your-api-key
export AETHERTERM_AI_MODEL=gpt-4
export AETHERTERM_ENABLE_AI=true

# サーバー連携設定
export AETHERTERM_SERVER_ENABLED=true
export AETHERTERM_SERVER_URL=http://localhost:57575

# テレメトリー設定
export AETHERTERM_OTLP_ENDPOINT=http://localhost:4317
export AETHERTERM_ENVIRONMENT=production
```

#### 起動手順

1. **OpenTelemetry Collector の起動（推奨）**
```bash
# Docker Composeを使用した例
cat > docker-compose.yml << EOF
version: '3.8'
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"   # OTLP gRPC receiver
      - "4318:4318"   # OTLP HTTP receiver
      - "8889:8889"   # Prometheus metrics
EOF

# 起動
docker-compose up -d otel-collector
```

2. **AetherTerminalServerの起動**
```bash
# サーバーを起動
uv run aetherterm --host localhost --port 57575 --debug
```

3. **AetherTermShellの起動**
```bash
# 連携モードで起動
uv run aetherterm-shell --config connected.toml

# または環境変数使用
AETHERTERM_MODE=connected AETHERTERM_SERVER_ENABLED=true uv run aetherterm-shell
```

4. **Webブラウザでアクセス**
```
http://localhost:57575
```

> **注意**: OpenTelemetry Collectorが起動していない場合でも、AetherTermShellは正常に動作します。テレメトリー機能のみが無効になります。

### 使用例

#### 基本的な使用フロー

1. **Webブラウザでターミナルにアクセス**
   - `http://localhost:57575` にアクセス
   - ターミナル画面とAIチャット画面が表示

2. **コマンド実行とAI分析**
```bash
# ターミナルでコマンド実行
$ ls -la /nonexistent
ls: cannot access '/nonexistent': No such file or directory

# AI分析結果がWebUIに表示:
# "指定されたディレクトリが存在しません。typoの可能性があります。"
# "修正提案: ls -la /home/user または ls -la . を試してください"
```

3. **AI機能の活用**
   - エラー発生時の自動解析と修正提案
   - コマンド履歴に基づく次のアクション提案
   - WebUIでのAIチャット機能

#### 高度な使用例

```bash
# 複雑な開発タスク
$ git clone https://github.com/user/project.git
$ cd project
$ npm install
# → AI提案: "package.jsonを確認しました。npm run dev でローカルサーバーを起動できます"

$ npm run dev
ERROR: Port 3000 is already in use
# → AI分析: "ポート3000が使用中です"
# → 修正提案: "lsof -ti:3000 | xargs kill でプロセスを終了するか、PORT=3001 npm run dev で別ポートを使用してください"
```

---

## 共通設定項目

### ログ設定

```toml
[logging]
level = "INFO"  # DEBUG, INFO, WARNING, ERROR
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
file_path = "/tmp/aetherterm.log"  # 空の場合はファイル出力なし
max_file_size = 10485760  # 10MB
backup_count = 5
```

### テレメトリー設定

```toml
[telemetry]
service_name = "aetherterm-shell"
service_version = "1.0.0"
environment = "development"  # development, staging, production
otlp_endpoint = "http://localhost:4317"
enable_tracing = true
enable_metrics = true
enable_log_instrumentation = true
trace_sample_rate = 1.0
metrics_export_interval = 30
```

### セッション管理設定

```toml
[session]
session_timeout = 3600  # セッションタイムアウト（秒）
max_sessions = 100      # 最大セッション数
cleanup_interval = 300  # クリーンアップ間隔（秒）
enable_persistence = true  # セッション永続化
```

---

## トラブルシューティング

### 一般的な問題

#### 1. AI機能が動作しない

**症状**: AIによる分析や提案が表示されない

**確認項目**:
```bash
# AI機能が有効か確認
echo $AETHERTERM_ENABLE_AI

# APIキーが設定されているか確認
echo $AETHERTERM_AI_API_KEY

# プロバイダー設定を確認
echo $AETHERTERM_AI_PROVIDER
```

**解決方法**:
```bash
# 環境変数を設定
export AETHERTERM_ENABLE_AI=true
export AETHERTERM_AI_API_KEY=your-api-key
export AETHERTERM_AI_PROVIDER=openai

# デバッグモードで起動
AETHERTERM_DEBUG=true uv run aetherterm-shell
```

#### 2. サーバー接続エラー

**症状**: Connected モードでサーバーに接続できない

**確認項目**:
```bash
# サーバーが起動しているか確認
curl http://localhost:57575/health

# ポートが使用中か確認
lsof -i :57575
```

**解決方法**:
```bash
# サーバーを起動
uv run aetherterm --host localhost --port 57575

# 別ポートを使用
export AETHERTERM_SERVER_URL=http://localhost:8080
```

#### 3. ローカルLLMエラー

**症状**: ローカルLLMに接続できない

**確認項目**:
```bash
# Ollamaが起動しているか確認
curl http://localhost:11434/api/tags

# モデルがダウンロードされているか確認
ollama list

# Ollamaプロセスが実行中か確認
ps aux | grep ollama
```

**解決方法**:
```bash
# Ollamaを手動で起動（バックグラウンド実行）
nohup ollama serve > /tmp/ollama.log 2>&1 &

# または、別ターミナルで起動
ollama serve

# モデルをダウンロード
ollama pull llama2

# エンドポイントを確認
export AETHERTERM_AI_ENDPOINT=http://localhost:11434

# 接続テスト
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "llama2", "prompt": "Hello", "stream": false}'
```

#### 4. OpenTelemetryエラー

**症状**: テレメトリー関連の警告が表示される

**確認項目**:
```bash
# OTLPエンドポイントが利用可能か確認
curl http://localhost:4317

# 環境変数を確認
echo $AETHERTERM_OTLP_ENDPOINT
```

**解決方法**:
```bash
# テレメトリーを無効化（警告を抑制）
export AETHERTERM_OTLP_ENDPOINT=""

# または設定ファイルで無効化
[telemetry]
enable_tracing = false
enable_metrics = false
enable_log_instrumentation = false

# OpenTelemetry Collectorを起動（推奨）
docker run -p 4317:4317 -p 4318:4318 \
  otel/opentelemetry-collector-contrib:latest
```

### ログ確認方法

```bash
# ログファイルを確認
tail -f /tmp/aetherterm.log

# デバッグログを有効化
AETHERTERM_DEBUG=true uv run aetherterm-shell

# 特定のモジュールのログレベルを変更
export PYTHONPATH=.
python -c "
import logging
logging.getLogger('aetherterm.shell').setLevel(logging.DEBUG)
"
```

### パフォーマンス最適化

#### リソース使用量の削減

```toml
# 最小限の設定
[monitor]
buffer_size = 1024
poll_interval = 1.0
max_history = 100

[ai_service]
max_command_history = 10
timeout = 15

[telemetry]
enable_tracing = false
enable_metrics = false
```

#### 応答速度の向上

```toml
# 高速化設定
[monitor]
poll_interval = 0.05

[ai_service]
timeout = 10
max_retries = 1

# ローカルLLM使用時
provider = "local"
model = "llama2:7b"  # 軽量モデル使用
```

---

## まとめ

AetherTermShellは3つの動作モードを提供し、様々な用途に対応できます：

- **DoNothing**: シンプルなシェル環境
- **StandAlone**: 独立したAI機能
- **Connected**: フル機能のWeb統合環境

適切なモードを選択し、設定を調整することで、効率的なターミナル環境を構築できます。