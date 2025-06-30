# AetherTerm ユーザーガイド

**AI支援ターミナルプラットフォームの完全ガイド**

AetherTermは、AI技術を活用した次世代のWeb ターミナル環境です。このガイドでは、インストールから日常的な使用方法まで、すべてを詳しく説明します。

## 🎯 目次

1. [はじめに](#はじめに)
2. [システム要件](#システム要件)  
3. [インストール](#インストール)
4. [初期設定](#初期設定)
5. [基本的な使用方法](#基本的な使用方法)
6. [AI機能の活用](#ai機能の活用)
7. [高度な機能](#高度な機能)
8. [設定とカスタマイズ](#設定とカスタマイズ)
9. [トラブルシューティング](#トラブルシューティング)

## 🚀 はじめに

### AetherTermとは？

AetherTermは、従来のターミナルにAI支援機能を追加した革新的なプラットフォームです：

- **🌐 Web ベース**: ブラウザでアクセス可能な高機能ターミナル
- **🤖 AI 統合**: リアルタイムでのコマンド分析と支援
- **🛡️ セキュリティ**: 危険なコマンドの自動検出・防止
- **📊 学習機能**: ユーザーの作業パターンから継続的に学習
- **🔄 マルチセッション**: 複数のターミナルセッションを同時管理

### 主な利用シーン

- **開発作業**: コーディング、デバッグ、デプロイメント
- **システム管理**: サーバー監視、設定変更、トラブルシューティング
- **学習環境**: プログラミング学習、新技術の習得
- **チーム作業**: コードレビュー、ペアプログラミング

## 💻 システム要件

### 最小要件
- **OS**: Linux (Ubuntu 18.04+), macOS (10.15+), Windows (WSL2)
- **Python**: 3.12以上
- **Node.js**: 18以上
- **メモリ**: 4GB RAM
- **ストレージ**: 5GB 空き容量

### 推奨要件
- **OS**: Linux (Ubuntu 22.04+), macOS (13.0+)
- **Python**: 3.12最新版
- **Node.js**: 20 LTS
- **メモリ**: 8GB RAM (AI機能フル活用)
- **ストレージ**: 20GB 空き容量
- **ネットワーク**: インターネット接続 (AI API使用時)

### 追加コンポーネント（オプション）
- **Redis**: 高速メモリキャッシュ用
- **PostgreSQL**: 長期データ保存用
- **Docker**: コンテナ環境での実行用

## 📦 インストール

### 方法1: パッケージマネージャー使用（推奨）

#### Python環境の準備
```bash
# Python 3.12のインストール（Ubuntu）
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip

# uvパッケージマネージャーのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

#### AetherTermのインストール
```bash
# リポジトリのクローン
git clone https://github.com/aether-platform/aetherterm.git
cd aetherterm

# 依存関係のインストール
uv sync

# フロントエンドのセットアップ
cd frontend
npm install  # pnpmが利用可能な場合は pnpm install
npm run build
cd ..

# フロントエンドのデプロイ
make build-frontend
```

### 方法2: Docker使用

#### Docker Composeでの起動
```bash
# リポジトリのクローン
git clone https://github.com/aether-platform/aetherterm.git
cd aetherterm

# Docker環境での起動
docker-compose up -d

# ブラウザでアクセス
open http://localhost:57575
```

#### Dockerfileからのビルド
```bash
# イメージのビルド
docker build -t aetherterm .

# コンテナの実行
docker run -d \
  --name aetherterm \
  -p 57575:57575 \
  -v $(pwd)/data:/app/data \
  aetherterm
```

### 方法3: 開発版インストール

```bash
# 最新の開発版
git clone -b develop https://github.com/aether-platform/aetherterm.git
cd aetherterm

# 開発用依存関係も含めてインストール
uv sync --group dev

# 開発モードでの起動
make run-debug
```

## ⚙️ 初期設定

### 基本設定ファイルの作成

```bash
# 設定ディレクトリの作成
mkdir -p ~/.aetherterm/config

# 基本設定ファイルのコピー
cp src/aetherterm/aetherterm.conf.default ~/.aetherterm/config/aetherterm.conf
```

### 設定ファイルの編集

```toml
# ~/.aetherterm/config/aetherterm.conf

[server]
host = "localhost"
port = 57575
debug = false

[ai]
enabled = true
default_provider = "openai"  # openai, anthropic, ollama
safety_level = "standard"    # strict, standard, relaxed

[security]
auto_block_dangerous = true
command_logging = true
session_timeout = 3600  # 秒

[ui]
theme = "dark"  # dark, light, auto
language = "ja"  # ja, en
terminal_columns = 120
terminal_rows = 30
```

### AI プロバイダーの設定

#### OpenAI の設定
```bash
# API キーの設定
echo 'export OPENAI_API_KEY="sk-your-api-key-here"' >> ~/.bashrc
source ~/.bashrc

# または設定ファイルで指定
mkdir -p ~/.aetherterm/keys
echo "sk-your-api-key-here" > ~/.aetherterm/keys/openai.key
chmod 600 ~/.aetherterm/keys/openai.key
```

#### Anthropic Claude の設定
```bash
# API キーの設定
echo 'export ANTHROPIC_API_KEY="sk-ant-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

#### ローカルLLM (Ollama) の設定
```bash
# Ollamaのインストール
curl -fsSL https://ollama.ai/install.sh | sh

# モデルのダウンロード
ollama pull phi3
ollama pull llama2

# AetherTerm設定での指定
# aetherterm.conf に追加:
[providers.ollama]
base_url = "http://localhost:11434"
model = "phi3"
```

## 🖥️ 基本的な使用方法

### サーバーの起動

#### 標準モード
```bash
# AgentServer（Web ターミナル）の起動
uv run aetherterm-agentserver

# ブラウザでアクセス
# http://localhost:57575
```

#### デバッグモード
```bash
# 詳細ログ付きで起動
uv run aetherterm-agentserver --debug --log-level=DEBUG
```

#### カスタム設定での起動
```bash
# ポートとホストを指定
uv run aetherterm-agentserver --host=0.0.0.0 --port=8080

# 設定ファイルを指定
uv run aetherterm-agentserver --config=/path/to/custom.conf
```

### Web インターフェースの使用

#### ブラウザでのアクセス
1. ブラウザで `http://localhost:57575` にアクセス
2. ターミナル画面が表示される
3. 通常のターミナルと同様にコマンドを入力

#### 基本操作
```bash
# 通常のLinuxコマンドが使用可能
ls -la
cd /home/user
cat file.txt
grep "pattern" *.log

# タブ補完も利用可能
cd /h[TAB]  # /home/ に補完
```

#### AI支援機能の体験
```bash
# 危険なコマンドを試してみる（ブロックされます）
rm -rf /

# AIに質問する
$ "Dockerでnginxを起動する方法は？"

# コマンドの説明を求める
$ tar -xzvf archive.tar.gz
# AI が自動的にコマンドの説明を表示
```

### マルチセッション管理

#### 新しいセッションの作成
```bash
# Ctrl+Shift+T または UI の + ボタンクリック
# 新しいターミナルタブが開く
```

#### セッション間の切り替え
```bash
# Ctrl+Shift+[1-9] でタブ切り替え
# またはタブをクリック
```

#### セッションの設定
```bash
# セッション名の設定
export AETHERTERM_SESSION_NAME="development"

# セッション固有の設定
export AETHERTERM_AI_LEVEL="strict"
```

## 🤖 AI機能の活用

### コマンド支援

#### 安全性チェック
```bash
$ sudo rm -rf /var/log/*
⚠️  DANGEROUS: このコマンドは危険です
💡 提案: sudo find /var/log -name "*.log" -mtime +30 -delete
📝 理由: システムログを完全削除すると、トラブルシューティングが困難になります

実行しますか？ [y/N/代替案(a)]
```

#### コマンド生成
```bash
$ "ポート8080で動いているプロセスを停止したい"

🤖 AI: ポート8080のプロセスを停止します

📋 実行手順:
1. lsof -ti:8080  # プロセスID確認
2. kill $(lsof -ti:8080)  # プロセス停止

💡 安全のため、まずプロセス情報を確認します：
```

#### 履歴からの学習
```bash
# よく使うコマンドパターンを学習
$ docker-compose up -d nginx
🤖 通常この後に docker logs nginx を実行されますね
💡 実行しますか？ [y/N]
```

### 対話型ヘルプ

#### 技術的な質問
```bash
$ "Kubernetesでnginxを動かすには？"

🤖 AI: Kubernetes上でnginxを展開する方法をご説明します

📋 基本的な手順:
1. Deploymentの作成
2. Serviceでの公開
3. 設定の確認

詳細な設定ファイルを生成しますか？ [Y/n]

# 'Y' を選択すると、nginx-deployment.yaml が自動生成される
```

#### エラーの解析
```bash
$ docker run nginx
docker: Error response from daemon: pull access denied for nginx

🤖 AI: Docker pull エラーを検出しました

🔍 問題の分析:
- 原因: イメージプル権限の問題
- 解決策: 公式イメージの指定

💡 修正コマンド:
docker run nginx:latest
# または
docker run docker.io/nginx:alpine

🚀 自動修正を実行しますか？
```

### 学習とカスタマイズ

#### 個人設定の学習
```bash
# AIがユーザーの好みを学習
$ git commit -m "update"
🤖 AI: いつもより簡潔なコミットメッセージですね
💡 詳細な形式に変更しますか？
例: "feat: update user authentication system"
```

#### 組織ルールの適用
```bash
# 組織固有のベストプラクティス
$ curl https://api.example.com | bash
🚫 BLOCKED: 組織ポリシーにより、パイプ実行は禁止されています

✅ 安全な代替方法:
1. curl https://api.example.com > script.sh
2. cat script.sh  # 内容確認
3. chmod +x script.sh && ./script.sh
```

## 🔧 高度な機能

### AgentShell（AI支援シェル）

#### 起動方法
```bash
# 別ターミナルでAgentShellを起動
uv run aetherterm-agentshell

# AgentServerと連携してAI機能を提供
```

#### PTY監視機能
```bash
# リアルタイムコマンド監視が有効
$ vi important_file.txt
🤖 AI: 重要ファイルの編集を検出
💾 自動バックアップを作成しますか？ [Y/n]
```

### ControlServer（中央管理）

#### 起動と設定
```bash
# ControlServerの起動
uv run aetherterm-controlserver --port=8765

# AgentServerとの連携設定
# aetherterm.conf に追加:
[control]
enabled = true
server_url = "ws://localhost:8765"
```

#### 統合管理機能
```bash
# 複数セッションの一括管理
# Web UI: http://localhost:8765

# セッション統計
$ aetherterm-control stats
Active Sessions: 5
AI Interventions: 23
Blocked Commands: 2
Average Session Time: 45 minutes
```

### 高度なAI統合

#### カスタムエージェント
```python
# ~/.aetherterm/agents/custom_agent.py
from aetherterm.agents import BaseAgent

class MyCustomAgent(BaseAgent):
    def analyze_command(self, command):
        if "production" in command:
            return {
                "risk": "CRITICAL",
                "message": "本番環境での作業には承認が必要です"
            }
        return None
```

#### 外部システム連携
```bash
# Slack通知の設定
[integrations.slack]
webhook_url = "https://hooks.slack.com/..."
notify_dangerous = true
notify_errors = true

# Jira連携
[integrations.jira]
server_url = "https://company.atlassian.net"
auto_create_tickets = true
```

## 🎨 設定とカスタマイズ

### UI テーマのカスタマイズ

#### 組み込みテーマ
```toml
[ui]
theme = "dark"          # ダークテーマ
# theme = "light"       # ライトテーマ  
# theme = "auto"        # システム設定に従う
# theme = "terminal"    # 従来ターミナル風
```

#### カスタムテーマ
```css
/* ~/.aetherterm/themes/custom.css */
:root {
  --bg-color: #1a1a1a;
  --text-color: #00ff00;
  --accent-color: #ff6b6b;
  --warning-color: #ffd93d;
  --danger-color: #ff4757;
}
```

### キーボードショートカット

#### デフォルトショートカット
```bash
Ctrl+Shift+T    # 新しいタブ
Ctrl+Shift+W    # タブを閉じる
Ctrl+Shift+1-9  # タブ切り替え
Ctrl+Shift+C    # コピー
Ctrl+Shift+V    # ペースト
Ctrl+Shift+F    # 検索
F11             # 全画面表示
```

#### カスタムショートカット
```toml
[shortcuts]
new_tab = "Ctrl+T"
close_tab = "Ctrl+W"
ai_assist = "Ctrl+Space"
command_search = "Ctrl+R"
session_save = "Ctrl+S"
```

### AI設定の詳細調整

#### 応答レベルの調整
```toml
[ai.responses]
verbosity = "normal"        # quiet, normal, verbose
suggestions = true          # 提案表示
explanations = true         # 説明表示
learning = true            # 学習機能
auto_correction = false    # 自動修正（慎重に）
```

#### モデル固有設定
```toml
[providers.openai]
model = "gpt-4"
temperature = 0.3          # 0.0-1.0 (保守的-創造的)
max_tokens = 1000
context_window = 4000

[providers.anthropic]
model = "claude-3-haiku-20240307"
temperature = 0.2
max_tokens = 1000
```

## 🆘 トラブルシューティング

### よくある問題

#### 1. サーバーが起動しない

**症状**: `uv run aetherterm-agentserver` でエラー

**解決方法**:
```bash
# ポートの競合確認
sudo lsof -i :57575

# 依存関係の再インストール
uv sync --reinstall

# 設定ファイルの確認
uv run aetherterm-agentserver --config-check
```

#### 2. AI機能が応答しない

**症状**: コマンド分析やAI支援が働かない

**解決方法**:
```bash
# API キーの確認
echo $OPENAI_API_KEY

# AI サービスの状態確認
uv run aetherterm-agentshell --status

# ネットワーク接続テスト
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

#### 3. フロントエンドが表示されない

**症状**: ブラウザでアクセスしても画面が表示されない

**解決方法**:
```bash
# フロントエンドの再ビルド
cd frontend
npm run build
cd ..
make build-frontend

# 静的ファイルの確認
ls -la src/aetherterm/agentserver/static/

# ブラウザキャッシュのクリア
# Ctrl+Shift+R (ハードリロード)
```

#### 4. セッションが頻繁に切断される

**症状**: ターミナルセッションが予期せず終了する

**解決方法**:
```bash
# セッションタイムアウトの確認
grep session_timeout ~/.aetherterm/config/aetherterm.conf

# WebSocket接続の安定性確認
curl -I http://localhost:57575/socket.io/

# ログの確認
tail -f ~/.aetherterm/logs/agentserver.log
```

### デバッグツール

#### ログレベルの調整
```bash
# 詳細ログの有効化
export AETHERTERM_LOG_LEVEL=DEBUG
export AETHERTERM_AI_DEBUG=1

# 特定コンポーネントのデバッグ
export AETHERTERM_MEMORY_DEBUG=1
export AETHERTERM_COMMAND_DEBUG=1
```

#### 診断コマンド
```bash
# システム情報の表示
uv run aetherterm-agentserver --system-info

# 設定の確認
uv run aetherterm-agentserver --config-dump

# 接続テスト
uv run aetherterm-agentserver --connection-test
```

#### ログファイルの場所
```bash
# メインログ
~/.aetherterm/logs/agentserver.log

# AI関連ログ
~/.aetherterm/logs/ai.log

# セキュリティログ
~/.aetherterm/logs/security.log

# 監査ログ
~/.aetherterm/logs/audit.log
```

### パフォーマンス最適化

#### メモリ使用量の削減
```toml
[memory]
# キャッシュサイズの調整
vector_cache_size = 100      # MB
session_cache_size = 50      # MB
command_history_limit = 1000 # コマンド数

# 不要機能の無効化
enable_longterm_memory = false
enable_vector_search = false
```

#### レスポンス速度の改善
```toml
[ai]
# 応答速度優先設定
model_preference = "speed"   # speed, balanced, quality
cache_responses = true
parallel_processing = true
```

---

**次のステップ**: [AI機能ガイド](AI_FEATURES_GUIDE.md)でAI機能を詳しく学ぶ

💡 **ヒント**: AetherTermは使うほど学習し、あなたの作業スタイルに最適化されます。最初は基本機能から始めて、徐々に高度な機能を活用してください。