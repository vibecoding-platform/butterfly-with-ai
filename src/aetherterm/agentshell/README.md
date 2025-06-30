# AgentShell - エージェント協調プラットフォーム

OpenHandsやClaudeCodeなどの複数エージェントがWebSocket経由で協調作業を行うためのプラットフォーム

## ✨ 新機能: 階層的ターミナル起動システム

AgentShellは **AgentServer → AgentShell → 複数ターミナル** の階層的起動をサポート：

### 🏗️ アーキテクチャ
```
AgentServer (port:57575)
 ├── WebUI Terminal 1 (default shell)
 ├── WebUI Terminal 2 (AgentShell起動)
 │   ├── ClaudeCode Terminal (claude_frontend)
 │   ├── ClaudeCode Terminal (claude_backend)
 │   └── OpenHands Terminal (openhands_devops)
 └── WebUI Terminal 3 (直接エージェント起動)
```

### 🚀 起動フロー
1. **AgentServer起動**: Web UIでターミナルアクセス
2. **AgentShell起動**: 特定ターミナルでAgentShellを実行
3. **エージェント専用ターミナル生成**: 各コーディングエージェント用にターミナルを動的生成
4. **エージェント割り当て**: 生成されたターミナルに特定エージェントを割り当て

```bash
# AgentServerが必要（別ターミナルで起動）
uv run aetherterm-agentserver --host=localhost --port=57575 --unsecure --debug
```

## 起動方法

### 1. 基本的な起動

```bash
# デフォルト設定（ClaudeCodeのみ）
uv run python -m aetherterm.agentshell.main_websocket

# 特定のAgentServerに接続
uv run python -m aetherterm.agentshell.main_websocket --server http://localhost:57575

# 設定ファイルを使用
uv run python -m aetherterm.agentshell.main_websocket --config example_agentshell_config.toml
```

### 2. エージェント構成の指定

```bash
# ClaudeCodeエージェントのみ
uv run python -m aetherterm.agentshell.main_websocket -a claude_code:claude_001

# 複数のClaudeCodeエージェント
uv run python -m aetherterm.agentshell.main_websocket \
  -a claude_code:claude_frontend \
  -a claude_code:claude_backend \
  -a claude_code:claude_tests

# OpenHandsとClaudeCodeの混在
uv run python -m aetherterm.agentshell.main_websocket \
  -a openhands:openhands_001 \
  -a claude_code:claude_001 \
  -a claude_code:claude_002
```

### 3. 開発・デバッグモード

```bash
# デバッグログを有効化
uv run python -m aetherterm.agentshell.main_websocket --debug

# インタラクティブモード（キーボード入力で他エージェントに依頼）
uv run python -m aetherterm.agentshell.main_websocket --interactive

# 設定ファイルとインタラクティブモードの組み合わせ
uv run python -m aetherterm.agentshell.main_websocket --config example_agentshell_config.toml --interactive --debug
```

### 4. インタラクティブモードの使用

```bash
# インタラクティブモードで起動
uv run python -m aetherterm.agentshell.main_websocket --interactive

=== AgentShell インタラクティブモード ===
コマンド例:
  list                    - エージェント一覧表示
  status                  - システム状態表示
  terminals               - 生成済みターミナル一覧表示
  managed                 - 管理下のターミナル一覧表示
  spawn <agent_type> <agent_id> - 新しいターミナルを生成
  assign <terminal_id> <agent_type> <agent_id> - ターミナルにエージェントを割り当て
  kill <spawn_id>         - 生成されたターミナルを終了
  terminate <terminal_id> - 管理下のターミナルを終了
  @<agent_id> <message>   - 特定のエージェントにメッセージ送信
  @all <message>          - 全エージェントにブロードキャスト
  quit/exit               - 終了
========================================

> spawn claude_code claude_frontend /path/to/frontend
新しいターミナルを生成中: claude_code:claude_frontend...
ターミナルが生成されました: a1b2c3d4-...

> assign term_001 openhands openhands_backend /path/to/backend
エージェントを割り当て中: term_001 → openhands:openhands_backend...
エージェントが割り当てられました: e5f6g7h8-...

> managed
=== 管理下のターミナル ===
- term_001: ready
  エージェント: openhands:openhands_backend
  最終アクティビティ: 2025-01-29 12:34:56
  プロセスID: 12345
========================

> @claude_frontend please review the login component
claude_frontendからの応答: I'll review the login component now...
```

## 運用パターン

### パターン1: プロジェクト分散開発

```bash
# 端末1: フロントエンド専用
python -m aetherterm.agentshell.main_websocket -a claude_code:frontend_dev

# 端末2: バックエンド専用  
python -m aetherterm.agentshell.main_websocket -a openhands:backend_dev

# 端末3: テスト専用
python -m aetherterm.agentshell.main_websocket -a claude_code:test_engineer
```

### パターン2: 単一端末での複数エージェント

```bash
# 1つの端末で全エージェントを管理
python -m aetherterm.agentshell.main_websocket \
  -a claude_code:frontend \
  -a claude_code:backend \
  -a claude_code:tests \
  -a openhands:devops
```

### パターン3: 動的エージェント追加

```bash
# 基本エージェントを起動
python -m aetherterm.agentshell.main_websocket -a claude_code:main

# 別端末から追加エージェント投入
python -m aetherterm.agentshell.main_websocket -a claude_code:reviewer

# さらに別端末から
python -m aetherterm.agentshell.main_websocket -a openhands:deployer
```

## エージェント間通信

起動後、以下の方法でエージェント間通信が可能：

### 1. WebSocket経由の自動通信
- エージェントが自動的にAgentServerに登録
- 他のエージェントの存在を自動検出
- タスク結果を自動共有

### 2. インタラクティブ通信（キーボード入力）
```bash
# エージェント一覧表示
> list

# 特定エージェントにコードレビュー依頼
> @claude_reviewer code_review /path/to/file.py

# 特定エージェントにテスト生成依頼
> @claude_tester test_generation /path/to/module.py

# 全エージェントにブロードキャスト
> @all status_update Project phase 2 started
```

### 3. プログラマティック通信
エージェント内部から他のエージェントに依頼：

```python
# ClaudeCodeの出力内で他エージェントに依頼
# OUTPUT: "I've created the login form. REQUEST_REVIEW: src/components/LoginForm.tsx"
# OUTPUT: "Backend API is ready. REQUEST_TESTS: src/api/auth.py"
```

## 設定ファイル

### agentshell_config.toml

```toml
[server]
url = "http://localhost:57575"
reconnect_interval = 5.0
heartbeat_interval = 30.0

[agents.claude_code]
executable = "claude"
timeout = 120.0
max_retries = 3

[agents.openhands]
endpoint = "http://localhost:3000"
timeout = 300.0

[coordination]
enable_interactive = true
enable_auto_requests = true
```

## Docker Compose での起動

```yaml
version: '3.8'
services:
  agentserver:
    build: ../agentserver
    ports:
      - "57575:57575"
  
  agentshell-frontend:
    build: .
    command: python -m aetherterm.agentshell.main_websocket -a claude_code:frontend
    depends_on:
      - agentserver
    volumes:
      - ./workspace:/workspace
  
  agentshell-backend:
    build: .
    command: python -m aetherterm.agentshell.main_websocket -a openhands:backend
    depends_on:
      - agentserver
    volumes:
      - ./workspace:/workspace
```

## 監視・運用

AgentServerのWebダッシュボードで以下を監視可能：
- 接続中のエージェント一覧
- エージェント間メッセージフロー
- タスク実行状況
- システムリソース使用量

## トラブルシューティング

### よくある問題

1. **AgentServerに接続できない**
   ```bash
   # AgentServerが起動しているか確認
   curl http://localhost:57575/health
   
   # ポートが使用されているか確認
   ss -tulpn | grep 57575
   ```

2. **ClaudeCode CLIが見つからない**
   ```bash
   # ClaudeCLIの存在確認
   which claude
   claude --version
   ```

3. **エージェント間通信が機能しない**
   ```bash
   # デバッグモードで起動
   python -m aetherterm.agentshell.main_websocket --debug
   ```