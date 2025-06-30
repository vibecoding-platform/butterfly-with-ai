# 中央制御機能テスト手順

## フェーズ1実装完了: 中央での監督ユーザーからの制御

### 実装されたコンポーネント

#### 1. ControlServer (中央制御サーバー)
- **ファイル**: `src/aetherterm/controlserver/`
- **機能**: 管理者からの制御指示を受信し、全AgentServerに一括指示を送信
- **コマンド**: `aetherterm-control`

#### 2. AgentServer統合機能
- **ファイル**: `src/aetherterm/agentserver/control_integration.py`
- **機能**: ControlServerからの制御指示を受信し、セッション制御を実行

#### 3. CentralController
- **ファイル**: `src/aetherterm/controlserver/central_controller.py`
- **機能**: WebSocket通信による双方向制御

---

## テスト環境セットアップ

### 1. 依存関係インストール
```bash
# プロジェクトルートで実行
uv pip install -e .

# WebSocket依存関係を追加インストール
uv pip install websockets
```

### 2. 必要なポート確認
- **ControlServer**: 8765 (WebSocket)
- **AgentServer**: 57575 (HTTP/WebSocket)
- **Frontend**: 5173 (開発サーバー)

---

## 基本動作テスト

### Step 1: ControlServer起動
```bash
# ターミナル1でControlServer起動
uv run aetherterm-control --debug

# 期待される出力:
# INFO - Starting CentralController on localhost:8765
# INFO - CentralController started on ws://localhost:8765
```

### Step 2: AgentServer起動（制御統合有効）
```bash
# ターミナル2でAgentServer起動
uv run aetherterm --debug --host localhost --port 57575

# 注意: 現在はAgentServerにControlServer統合機能を手動で有効化する必要があります
```

### Step 3: フロントエンド起動
```bash
# ターミナル3でフロントエンド起動
cd frontend
pnpm run dev

# ブラウザで http://localhost:5173 にアクセス
```

### Step 4: 複数ターミナルセッション作成
1. ブラウザで複数タブを開く
2. 各タブでターミナルセッションを作成
3. 各ターミナルで簡単なコマンドを実行（例: `ls`, `pwd`）

---

## 制御機能テスト

### テスト1: WebSocket接続確認
```bash
# WebSocketクライアントでControlServerに接続テスト
# Python WebSocketクライアントの例:

import asyncio
import websockets
import json

async def test_control_connection():
    uri = "ws://localhost:8765/admin"
    async with websockets.connect(uri) as websocket:
        # 状態取得
        await websocket.send(json.dumps({"type": "get_status"}))
        response = await websocket.recv()
        print(f"Status: {response}")

asyncio.run(test_control_connection())
```

### テスト2: 管理者制御API（手動テスト）
```bash
# ControlServerに直接WebSocketで接続して制御指示を送信

# 全セッション一括ブロック
{
  "type": "block_all_sessions",
  "reason": "テスト用緊急ブロック",
  "admin_user": "test_admin"
}

# 個別セッションブロック
{
  "type": "block_session",
  "session_id": "session_id_here",
  "reason": "個別テスト",
  "admin_user": "test_admin"
}

# セッションブロック解除
{
  "type": "unblock_session",
  "session_id": "session_id_here",
  "admin_user": "test_admin"
}
```

### テスト3: Ctrl+D解除機能
1. セッションがブロックされた状態で
2. ターミナルで `Ctrl+D` を入力
3. ブロックが解除されることを確認

---

## 期待される動作

### 正常動作パターン

#### 1. 接続確立
- ControlServer起動後、AgentServerが自動接続
- 接続確認メッセージがログに出力
- 管理者クライアント接続時に現在状態を受信

#### 2. 一括ブロック実行
- 管理者からの一括ブロック指示
- 全AgentServerに緊急ブロック指示を送信
- 各ターミナルクライアントにブロック通知表示
- ユーザー入力が無効化される

#### 3. 個別解除
- ユーザーがCtrl+Dを入力
- AgentServerがControlServerに解除要求を送信
- ControlServerが解除を承認
- 該当セッションのブロックが解除される

### ログ出力例

#### ControlServer
```
INFO - Starting CentralController on localhost:8765
INFO - CentralController started on ws://localhost:8765
INFO - New connection from 127.0.0.1:xxxxx on path /agent
INFO - AgentServer registered: agentserver_main
WARNING - Executing block all sessions: テスト用緊急ブロック (ID: block_uuid)
INFO - Broadcast sent to 1/1 AgentServers
```

#### AgentServer
```
INFO - Starting ControlIntegration with ControlServer: ws://localhost:8765
INFO - Connected to ControlServer
INFO - Sent agent registration: agentserver_main
WARNING - Received emergency block: block_uuid - テスト用緊急ブロック
INFO - Blocked 2 sessions
```

---

## トラブルシューティング

### 問題1: ControlServerに接続できない
**症状**: AgentServerがControlServerに接続できない
**解決策**:
1. ControlServerが起動しているか確認
2. ポート8765が使用可能か確認
3. ファイアウォール設定を確認

### 問題2: ブロック指示が届かない
**症状**: 管理者からの指示がターミナルに反映されない
**解決策**:
1. AgentServerとControlServerの接続状態を確認
2. WebSocketメッセージのJSON形式を確認
3. セッションIDが正しいか確認

### 問題3: Ctrl+D解除が動作しない
**症状**: Ctrl+Dを押してもブロックが解除されない
**解決策**:
1. ターミナルの入力処理が正常か確認
2. AgentServerのブロック状態管理を確認
3. ControlServerとの通信状態を確認

---

## 次フェーズへの準備

### データ収集基盤の準備
現在の実装では基本的な制御機能のみ実装されています。次のフェーズ（ビッグデータデータレイクからの判定）に向けて、以下の準備が必要です：

1. **ログ収集機能の実装**
   - 全ターミナルログの構造化
   - 永続化ストレージへの保存

2. **メトリクス収集の開始**
   - セッション活動の記録
   - コマンド実行パターンの分析

3. **分析用データパイプライン構築**
   - ログデータの前処理
   - 異常検知アルゴリズムの準備

### 運用監視の改善
1. **管理ダッシュボードの実装**
   - リアルタイム状態監視
   - ブロック履歴の可視化

2. **アラート機能の追加**
   - 緊急事態の自動通知
   - 管理者への即座の連絡

3. **監査ログの強化**
   - 全制御操作の記録
   - セキュリティ監査対応

---

## 実装完了確認チェックリスト

- [ ] ControlServer起動確認
- [ ] AgentServerとの接続確認
- [ ] 複数セッション作成確認
- [ ] 一括ブロック機能動作確認
- [ ] 個別ブロック機能動作確認
- [ ] Ctrl+D解除機能動作確認
- [ ] WebSocket通信ログ確認
- [ ] エラーハンドリング動作確認

フェーズ1の基本制御機能が正常に動作することを確認後、フェーズ2（ビッグデータ解析）の実装に進みます。