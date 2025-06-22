# AetherTerm 開発環境起動手順

**このドキュメントは開発環境専用です。本番環境のデプロイ手順は別途ドキュメントを参照してください。**

## 推奨開発環境 (Supervisord プロセス管理)

### 事前準備
```bash
# Python環境の準備
uv sync

# フロントエンド依存関係のインストール
cd frontend/
pnpm install
cd ..

# ログディレクトリの作成
mkdir -p run/logs run/pids

# フロントエンドをビルドして静的ファイルにデプロイ
make build-frontend
```

### Supervisord でのマルチプロセス開発サーバー起動
```bash
# 全サービスを同時起動 (推奨)
supervisord -c supervisord.conf

# 各サービスの個別制御
supervisorctl -c supervisord.conf start agentserver  # AgentServer のみ起動
supervisorctl -c supervisord.conf start frontend     # フロントエンド開発サーバーのみ起動
supervisorctl -c supervisord.conf stop agentserver   # AgentServer 停止
supervisorctl -c supervisord.conf stop all          # 全サービス停止
supervisorctl -c supervisord.conf restart all       # 全サービス再起動

# 全体停止
supervisorctl -c supervisord.conf shutdown
```

### ログの確認

#### 従来の方法（直接ファイルアクセス）
```bash
# AgentServer のログ
tail -f run/logs/agentserver.stdout.log
tail -f run/logs/agentserver.stderr.log

# フロントエンド開発サーバーのログ
tail -f run/logs/frontend.stdout.log
tail -f run/logs/frontend.stderr.log

# 全ログの監視
tail -f run/logs/*.log
```

#### 推奨の方法（supervisord-mcp経由）
```bash
# AgentServer のログ（最新100行）
uv run supervisord-mcp logs agentserver

# フロントエンドのログ（最新100行）
uv run supervisord-mcp logs frontend

# エラーログの確認
uv run supervisord-mcp logs agentserver --stderr
uv run supervisord-mcp logs frontend --stderr

# 特定行数のログ取得
uv run supervisord-mcp logs agentserver --lines 200
```

## アクセス先
- **メインアプリケーション**: http://localhost:57575
- **フロントエンド開発サーバー**: http://localhost:5173 (Viteデフォルトポート)

## 開発ワークフロー

### セッション管理システムの開発・テスト
1. `supervisord -c supervisord.conf` でサービス起動
2. ブラウザで http://localhost:57575 にアクセス
3. セッション作成・参加機能をテスト
4. ペーン分割操作をテスト (Ctrl+B %, Ctrl+B ")
5. セッション間通信機能をテスト

### フロントエンド開発
1. `frontend/src/` でコード変更
2. ホットリロードで即座に反映確認
3. 統合テスト時は `make build-frontend` を実行

### デバッグ
- **AgentServer**: `uv run supervisord-mcp logs agentserver --stderr` または run/logs/agentserver.stderr.log を確認
- **フロントエンド**: ブラウザ開発者ツール + `uv run supervisord-mcp logs frontend --stderr`
- **Socket.IO**: ブラウザ開発者ツールのネットワークタブで WebSocket 通信確認
- **プロセス状態**: `supervisorctl -c supervisord.conf status` で全プロセス状況確認

## 注意事項
- **Supervisord 使用を強く推奨**: 複数サービスの協調開発が必要
- フロントエンド変更の統合テストは `make build-frontend` を実行
- 開発時はフロントエンド開発サーバー (http://localhost:5173) を使用してホットリロードを活用
- セッション管理機能は AgentServer と フロントエンド の両方が必要

<!-- 1. 最短コマンド:
  AetherTermプロジェクトのターミナル接続問題の調査を再開してください。

  まず「docs/workspace/RESTART_INSTRUCTIONS.md」を読んで、完全なコンテキストと指示を取得してください。
  2. 詳細な指示が必要な場合:
    - docs/workspace/RESTART_INSTRUCTIONS.md に完全な再開用指示
    - 技術的詳細は docs/workspace/work/TERMINAL_CONNECTION_DEBUG_STATUS.md -->