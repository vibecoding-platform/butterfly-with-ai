# PTY Monitor - ログ監視とAI解析による自動ブロック機能

AgentShell内で完結するスタンドアローンのPTYログ監視システムです。

## 機能概要

- **PTY制御**: pty master/slaveによるリアルタイムログ監視
- **AI解析**: 簡易キーワードベース + WebSocket AI解析による危険度判定
- **自動ブロック**: 危険検出時のユーザー入力ブロック
- **Ctrl+D解除**: ブロック解除機能

## アーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  PTY Controller │───▶│   AI Analyzer   │───▶│  Input Blocker  │
│                 │    │                 │    │                 │
│ • pty master/   │    │ • キーワード解析 │    │ • 入力ブロック  │
│   slave制御     │    │ • WebSocket AI  │    │ • Ctrl+D検出   │
│ • tail -f監視   │    │ • 脅威レベル判定 │    │ • 確認プロセス  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## インストール

```bash
# 依存関係インストール
uv pip install -e .

# または直接実行
uv run python -m src.aetherterm.agentshell.pty_monitor.main --help
```

## 使用方法

### 1. ダミーAIサーバー起動

```bash
# ダミーAIサーバー起動（別ターミナル）
uv run aetherterm-dummy-ai --host localhost --port 8765 --debug

# または直接実行
uv run python src/aetherterm/agentshell/pty_monitor/dummy_ai_server.py --debug
```

### 2. テストログファイル作成

```bash
# テストログファイル作成
uv run aetherterm-shell-monitor --log-file /tmp/test.log --create-test-log

# または直接実行
uv run python src/aetherterm/agentshell/pty_monitor/main.py --log-file /tmp/test.log --create-test-log
```

### 3. PTYログ監視開始

```bash
# PTYログ監視開始
uv run aetherterm-shell-monitor --log-file /tmp/test.log --debug

# または直接実行
uv run python src/aetherterm/agentshell/pty_monitor/main.py --log-file /tmp/test.log --debug
```

### 4. テスト手順

1. **別ターミナルでログに危険コマンドを追記**:
   ```bash
   echo "2025-06-18 12:30:00 CRITICAL: Command executed: sudo rm -rf /" >> /tmp/test.log
   ```

2. **自動ブロック確認**: 監視ターミナルで入力がブロックされることを確認

3. **Ctrl+D解除**: `Ctrl+D`を2回押してブロック解除

## コマンドオプション

### PTY Monitor (`aetherterm-shell-monitor`)

```bash
uv run aetherterm-shell-monitor [OPTIONS]

Options:
  --log-file PATH          監視するログファイルのパス [必須]
  --ai-server-url URL      AIサーバーのWebSocket URL [デフォルト: ws://localhost:8765]
  --debug                  デバッグログを有効化
  --create-test-log        テストログファイルを作成
  --help                   ヘルプを表示
```

### Dummy AI Server (`aetherterm-dummy-ai`)

```bash
uv run aetherterm-dummy-ai [OPTIONS]

Options:
  --host HOST              サーバーホスト [デフォルト: localhost]
  --port PORT              サーバーポート [デフォルト: 8765]
  --debug                  デバッグログを有効化
  --help                   ヘルプを表示
```

## 脅威レベル

### CRITICAL（自動ブロック）
- `rm -rf /` - システム全体削除
- `dd if=/dev/zero` - ディスク破壊
- `mkfs.*` - ファイルシステム破壊
- `chmod 777 /` - ルート権限変更
- `nc.*-e /bin/sh` - リバースシェル

### HIGH（自動ブロック）
- `sudo su -` - root権限昇格
- `passwd root` - rootパスワード変更
- `systemctl stop/disable` - システムサービス停止
- `iptables -F` - ファイアウォール削除
- `wget.*|sh` - 不明スクリプト実行

### MEDIUM（警告のみ）
- `sudo.*` - 管理者権限実行
- `ps aux|grep` - プロセス監視
- `netstat -.*` - ネットワーク調査
- `find /.*-name` - システム検索

## ファイル構成

```
src/aetherterm/agentshell/pty_monitor/
├── __init__.py              # パッケージ初期化
├── main.py                  # メインエントリーポイント
├── pty_controller.py        # PTY制御
├── ai_analyzer.py           # AI解析
├── input_blocker.py         # 入力制御
├── dummy_ai_server.py       # テスト用AIサーバー
└── README.md               # このファイル
```

## 動作フロー

1. **通常時**: pty slaveで`tail -f`によりログ読み取り、pty masterで表示
2. **監視**: ログデータをAI解析サーバーに送信
3. **検出**: 危険キーワード検出時に入力ブロック
4. **ブロック**: 「!!!CRITICAL ALERT!!! Ctrl+Dを押して確認してください」表示
5. **解除**: Ctrl+D検出でブロック解除

## トラブルシューティング

### AIサーバーに接続できない
```bash
# AIサーバーが起動しているか確認
ps aux | grep dummy_ai_server

# ポートが使用中か確認
netstat -an | grep 8765

# ファイアウォール設定確認
sudo ufw status
```

### ログファイルが見つからない
```bash
# ログファイル存在確認
ls -la /tmp/test.log

# テストログファイル再作成
uv run aetherterm-shell-monitor --log-file /tmp/test.log --create-test-log
```

### 入力ブロックが解除されない
- `Ctrl+D`を2回押す（1回目で確認モード、2回目で解除）
- プロセスを強制終了: `Ctrl+C`または`kill -9 <PID>`

## 開発・デバッグ

### ログレベル設定
```bash
# デバッグモードで実行
uv run aetherterm-shell-monitor --log-file /tmp/test.log --debug

# AIサーバーもデバッグモード
uv run aetherterm-dummy-ai --debug
```

### カスタムパターン追加
[`ai_analyzer.py`](ai_analyzer.py:1)の`critical_patterns`、`high_patterns`、`medium_patterns`を編集してください。

### 統計情報
監視中に60秒間隔で統計情報が表示されます：
- 処理済みログ行数
- 脅威レベル別の検出数
- ブロック回数
- 現在のブロック状態

## 制限事項

- 現在は単一ログファイルのみ対応
- PTY制御はLinux環境でのみ動作
- WebSocket接続が切断された場合、簡易解析のみ実行
- 入力ブロック中は他のターミナル操作に影響する可能性

## 今後の拡張予定

- 複数ログファイル同時監視
- 設定ファイルによるパターンカスタマイズ
- より高度なAI解析モデル統合
- Web UIによる監視状況表示
- ログローテーション対応