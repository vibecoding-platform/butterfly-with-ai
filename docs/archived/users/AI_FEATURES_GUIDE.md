# AetherTerm AI機能ガイド

**次世代AI支援ターミナルの全機能解説**

AetherTermは最先端のAI技術を統合し、従来のターミナル操作を革新的に向上させます。このガイドでは、AI機能の詳細な使用方法と活用例を説明します。

## 🎯 目次

1. [AI機能概要](#ai機能概要)
2. [リアルタイムコマンド分析](#リアルタイムコマンド分析)
3. [LangChain階層化メモリシステム](#langchain階層化メモリシステム)
4. [マルチエージェント協調](#マルチエージェント協調)
5. [AI支援機能の設定](#ai支援機能の設定)
6. [実用的な活用例](#実用的な活用例)
7. [トラブルシューティング](#トラブルシューティング)

## 🤖 AI機能概要

### 統合AI機能一覧

| 機能 | 説明 | 状態 |
|------|------|------|
| 🛡️ **コマンド分析** | リアルタイムでコマンドの安全性を評価 | ✅ 実装済み |
| 🧠 **階層化メモリ** | 短期・中期・長期メモリによるコンテキスト管理 | ✅ 実装済み |
| 🤝 **マルチエージェント** | 複数AIエージェントの協調動作 | ✅ 実装済み |
| 💬 **対話型支援** | 自然言語でのコマンド生成と説明 | ✅ 実装済み |
| 📊 **ログ分析** | AIによるログパターン分析と異常検知 | ✅ 実装済み |
| 🔍 **知識検索** | ベクトル検索による関連情報の取得 | ✅ 実装済み |

### サポートAI プロバイダー

- **OpenAI**: GPT-4, GPT-3.5-turbo
- **Anthropic**: Claude 3 Haiku, Sonnet, Opus
- **ローカルLLM**: Ollama対応（Phi-4, Llama等）
- **カスタムAPI**: 独自AIモデルの統合

## 🛡️ リアルタイムコマンド分析

### 4段階リスク評価システム

AetherTermは入力されたコマンドを瞬時に分析し、以下の4段階で評価します：

#### 🟢 SAFE（安全）
```bash
# 一般的な安全なコマンド
ls -la
cd /home/user
cat README.md
grep "pattern" file.txt
```

#### 🟡 CAUTION（注意）
```bash
# 注意が必要なコマンド（警告表示）
sudo apt update
chmod 755 script.sh
find / -name "*.log" -delete
```

#### 🟠 DANGEROUS（危険）
```bash
# 危険なコマンド（確認プロンプト表示）
rm -rf /var/log/*
dd if=/dev/zero of=/dev/sda
iptables -F
```

#### 🔴 CRITICAL（致命的）
```bash
# 致命的なコマンド（自動ブロック）
rm -rf /*
:(){ :|:& };:
chmod 777 /etc/passwd
```

### コマンドブロッキング機能

#### 自動ブロック
```bash
$ rm -rf /
🚫 CRITICAL: このコマンドは自動的にブロックされました
💡 安全な代替案: 特定のディレクトリを指定してください
   例: rm -rf /tmp/specific_folder
```

#### インタラクティブ確認
```bash
$ sudo iptables -F
⚠️  DANGEROUS: このコマンドは危険な可能性があります
📝 説明: 全てのファイアウォールルールが削除されます
🤔 続行しますか？ [y/N/詳細を表示(d)]
```

## 🧠 LangChain階層化メモリシステム

### 3層メモリアーキテクチャ

#### 短期メモリ（Redis）
- **保持期間**: 現在のセッション中
- **用途**: コマンド履歴、現在の作業コンテキスト
- **容量**: 直近100コマンド

```python
# 短期メモリの例
{
  "session_id": "sess_2025_01_15_001",
  "commands": ["ls", "cd project", "git status"],
  "current_directory": "/home/user/project",
  "active_processes": ["vim", "node"]
}
```

#### 中期メモリ（PostgreSQL）
- **保持期間**: 30日間
- **用途**: セッション要約、パターン学習
- **容量**: セッション要約データ

```json
{
  "date": "2025-01-15",
  "session_summary": "Docker環境のセットアップを実行。nginx設定を変更し、テスト環境を構築。",
  "key_achievements": ["Docker構成完了", "nginx設定変更"],
  "issues_encountered": ["ポート競合", "権限エラー"]
}
```

#### 長期メモリ（Vector Store）
- **保持期間**: 永続
- **用途**: 知識ベース、専門的なノウハウ
- **容量**: 無制限（ベクトル検索）

```python
# ベクトル化された知識の例
{
  "content": "Docker Composeでnginxを設定する際は、ポート80/443の競合に注意",
  "embedding": [0.1, 0.3, -0.2, ...],  # 1536次元ベクトル
  "metadata": {
    "topic": "docker-nginx",
    "complexity": "intermediate",
    "last_accessed": "2025-01-15"
  }
}
```

### メモリ統合による支援

#### コンテキスト認識
```bash
$ docker-compose up nginx
🤖 AI: 前回のセッションでポート80の競合が発生していました。
    今回は異なるポート設定を使用しますか？

💡 提案: docker-compose -f docker-compose.alt.yml up nginx
```

#### パターン学習
```bash
$ git commit -m "fix bug"
🤖 AI: 通常、あなたは詳細なコミットメッセージを書かれますね。
💡 提案: git commit -m "fix: resolve nginx configuration port conflict"
```

## 🤝 マルチエージェント協調

### エージェント役割分担

#### 🛡️ セキュリティエージェント
- **役割**: コマンドの安全性評価
- **判断基準**: システムへの影響度、データ破損リスク
- **動作**: リアルタイム監視、自動ブロック

#### 🧠 ナレッジエージェント
- **役割**: 技術的な知識提供と文脈理解
- **判断基準**: 過去の履歴、ベストプラクティス
- **動作**: 提案生成、ドキュメント検索

#### 🔄 ワークフローエージェント
- **役割**: タスクの最適化と自動化
- **判断基準**: 効率性、繰り返しパターン
- **動作**: スクリプト生成、プロセス改善提案

#### ⚖️ 調整エージェント
- **役割**: エージェント間の衝突解決
- **判断基準**: ユーザーの意図、優先順位
- **動作**: 最終決定、コンフリクト解決

### エージェント協調の実例

#### シナリオ: 危険なファイル削除
```bash
$ rm -rf /var/log/*

🛡️ セキュリティ: DANGEROUS - ログファイルの一括削除
🧠 ナレッジ: システム監査に影響する可能性があります
🔄 ワークフロー: ログローテーションの設定を推奨
⚖️ 調整: ユーザー確認後、安全な代替案を提示

💡 最終提案:
1. sudo logrotate -f /etc/logrotate.conf  # 安全なログローテーション
2. find /var/log -name "*.log" -mtime +30 -delete  # 古いログのみ削除
```

#### シナリオ: 複雑なセットアップ
```bash
$ docker run -d nginx

🧠 ナレッジ: nginxの設定ファイルが不明です
🔄 ワークフロー: 設定の永続化を推奨
⚖️ 調整: 包括的なセットアップを提案

💡 改善提案:
docker run -d \
  --name nginx-server \
  -p 8080:80 \
  -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:alpine
```

## ⚙️ AI支援機能の設定

### 基本設定ファイル

#### `aetherterm.conf`
```toml
[ai]
# AI機能の有効/無効
enabled = true
default_provider = "openai"
safety_level = "standard"  # strict, standard, relaxed

[command_analysis]
# コマンド分析設定
auto_block_critical = true
show_suggestions = true
learn_from_history = true

[memory]
# メモリ設定
enable_longterm = true
vector_store = "chromadb"  # chromadb, faiss
session_retention_days = 30

[agents]
# エージェント設定
security_agent = true
knowledge_agent = true
workflow_agent = true
coordinator_agent = true
```

### API キー設定

#### 環境変数
```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# ローカルLLM (Ollama)
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="phi4"
```

#### 設定ファイル経由
```toml
[providers.openai]
api_key_file = "/etc/aetherterm/openai.key"
model = "gpt-4"
temperature = 0.3

[providers.anthropic]
api_key_file = "/etc/aetherterm/anthropic.key"
model = "claude-3-haiku-20240307"
temperature = 0.3

[providers.ollama]
base_url = "http://localhost:11434"
model = "phi4"
temperature = 0.5
```

### カスタマイズ設定

#### セキュリティレベル調整
```toml
[security_rules]
# カスタムルール定義
custom_dangerous_commands = [
    "curl.*|sh",
    "wget.*|bash",
    "eval.*"
]

custom_safe_commands = [
    "ls.*",
    "cat.*",
    "grep.*"
]

# 組織固有のルール
organization_rules = "/etc/aetherterm/org_rules.json"
```

#### 学習設定
```toml
[learning]
# ユーザー固有の学習
personal_learning = true
share_anonymous_data = false

# 組織レベルの学習
organization_learning = true
knowledge_sharing = true
```

## 💼 実用的な活用例

### 1. 開発環境セットアップ

#### 通常の手動作業
```bash
# 従来の手動セットアップ
mkdir project
cd project
git init
npm init -y
npm install express
touch app.js
# ... 20分の作業
```

#### AI支援による効率化
```bash
$ "Node.js Express プロジェクトをセットアップしたい"

🤖 AI: Express プロジェクトのセットアップを自動化します

📋 実行プラン:
1. プロジェクトディレクトリ作成
2. Git初期化とdefault設定
3. package.json生成（推奨設定）
4. Express + 開発依存関係インストール
5. 基本的なサーバーコード生成
6. 環境設定ファイル作成

🚀 実行しますか？ [Y/n/カスタマイズ(c)]

# 'Y'選択後、自動実行
✅ プロジェクト 'express-app' 作成完了
✅ Git初期化完了 (main branch)
✅ package.json生成完了
✅ 依存関係インストール完了
✅ app.js サーバーファイル作成完了
✅ .env, .gitignore 作成完了

💡 次のステップ: npm run dev でサーバー起動
```

### 2. システム監視とトラブルシューティング

#### 自動問題検出
```bash
$ systemctl status nginx
● nginx.service - A high performance web server
   Loaded: loaded
   Active: failed (Result: exit-code)
   
🤖 AI: nginx サービスの失敗を検出しました

🔍 分析結果:
- ポート80が他のプロセスで使用中
- 設定ファイルに構文エラーの可能性

🛠️ 修復提案:
1. sudo lsof -i :80  # ポート使用状況確認
2. sudo nginx -t     # 設定ファイル検証
3. sudo journalctl -u nginx -n 50  # 詳細ログ確認

📋 自動修復を実行しますか？
```

#### パフォーマンス監視
```bash
$ htop
# htop起動後、AIが自動分析

🤖 AI: システムリソース分析

⚠️  検出された問題:
- CPU使用率: 95% (プロセス: node)
- メモリ使用率: 87%
- I/O待機: 高

💡 最適化提案:
1. Node.jsプロセスのプロファイリング
2. メモリリーク調査
3. データベース接続プール最適化

🔧 詳細分析を実行しますか？
```

### 3. セキュリティ監査

#### 自動脆弱性チェック
```bash
$ sudo nmap -sS localhost

🛡️ セキュリティ: ネットワークスキャンを検出

📊 分析結果:
- 開放ポート: 22, 80, 443, 3000
- 不要なサービス: telnet (23)
- 推奨事項: ファイアウォール設定の見直し

🔒 セキュリティ強化提案:
1. sudo ufw enable
2. sudo ufw deny 23
3. sudo systemctl disable telnet

⚠️  実行前に管理者承認が必要です
```

### 4. データベース操作支援

#### 安全なデータベース操作
```bash
$ mysql -u root -p
mysql> DROP DATABASE production;

🚨 CRITICAL: 本番データベースの削除が検出されました！

🛡️ 自動ブロック: このコマンドは実行されませんでした

🤖 AI分析:
- 影響: 本番データの完全削除
- リスク: データ復旧不可能な損失
- 推奨: バックアップ確認後の段階的削除

💡 安全な代替案:
1. mysqldump production > backup_$(date +%Y%m%d).sql
2. mysql> CREATE DATABASE production_backup LIKE production;
3. 段階的なテーブル削除

📋 バックアップ作成から開始しますか？
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### AI機能が応答しない
```bash
# 症状
$ ls
# AI応答なし、分析機能停止

# 診断コマンド
$ aetherterm-shell-monitor --status
AI Services Status:
  ❌ LangChain Service: Connection failed
  ❌ Command Analyzer: Service down
  ✅ Memory Store: Connected

# 解決手順
1. サービス再起動
$ sudo systemctl restart aetherterm-agentshell

2. 設定確認
$ aetherterm config validate

3. ログ確認
$ tail -f ~/.aetherterm/logs/agent.log
```

#### メモリ使用量が高い
```bash
# 症状: システムが重い

🤖 AI: メモリ使用量の増加を検出

📊 分析:
- AetherTerm プロセス: 2.3GB
- 原因: ベクトルストアのメモリキャッシュ
- 推奨: キャッシュサイズの調整

🛠️ 最適化オプション:
1. キャッシュサイズ縮小 (推奨)
2. ディスクベースストレージに変更
3. メモリ使用量制限設定

📋 設定調整を実行しますか？
```

#### API制限エラー
```bash
# エラーメッセージ
🚫 OpenAI API: Rate limit exceeded

🤖 AI: API制限に達しました

💡 対処法:
1. ローカルLLMに一時切り替え
2. API使用量制限の設定
3. 複数プロバイダーの負荷分散

⚙️ 自動対処:
- Ollamaローカルモデルに切り替え中...
- ✅ phi4モデルで継続

📈 使用量監視とアラート設定を推奨
```

### デバッグモード

#### 詳細ログ有効化
```bash
# デバッグモード起動
$ aetherterm-agentserver --debug --log-level=DEBUG

# AI分析詳細表示
$ export AETHERTERM_AI_DEBUG=1

# メモリ操作のトレース
$ export AETHERTERM_MEMORY_TRACE=1
```

#### 分析結果の詳細表示
```bash
$ rm important_file.txt

🤖 AI分析詳細:
Command: "rm important_file.txt"
Risk Score: 7.2/10 (DANGEROUS)
Factors:
  ✅ Single file deletion (lower risk)
  ⚠️  No backup detected
  ⚠️  File contains recent changes
  ✅ User has write permissions

Confidence: 87%
Processing Time: 0.23s
Model: gpt-4 (temperature: 0.3)

💡 提案生成理由:
- 履歴パターン: バックアップ作成習慣あり
- ファイル重要度: 高 (recent modifications)
- 代替案: mv to trash directory
```

## 📈 AI機能の効果測定

### 使用統計の確認
```bash
$ aetherterm stats --ai-features

📊 AI機能使用統計 (過去30日)
════════════════════════════════════

🛡️ コマンド分析:
  - 分析済みコマンド: 2,847
  - ブロック済み: 23 (0.8%)
  - 警告表示: 156 (5.5%)
  - 提案採用率: 67%

🧠 メモリシステム:
  - 保存済み知識: 1,234件
  - 検索クエリ: 456回
  - 的中率: 82%

🤝 エージェント協調:
  - 調整実行: 89回
  - 成功率: 94%
  - 時間短縮: 平均18分

💡 生産性向上:
  - エラー削減: 34%
  - 作業時間短縮: 23%
  - 学習効率: +45%
```

---

**次のステップ**: [開発者向けガイド](../developers/DEVELOPER_GUIDE.md)で内部実装を学ぶ

💡 **ヒント**: AI機能は継続的に学習し、あなたの作業パターンに最適化されます。積極的に使用してカスタマイズを進めてください。