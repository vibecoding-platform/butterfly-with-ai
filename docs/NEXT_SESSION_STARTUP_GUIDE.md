# 次回セッション開始ガイド

## 📋 前回作業の概要

**実装完了**: リアルタイムAI解析による自動ブロック機能  
**現在の状態**: 基本実装完了、実動作テスト待ち  
**次回の焦点**: 実際のテスト実行と機能検証

## 🚀 クイックスタート手順

### 1. 環境確認 (5分)

```bash
# 作業ディレクトリに移動
cd /mnt/c/workspaces/vibecoding-platform/ide/terminal/butterfly-with-ai

# 依存関係確認
uv sync

# Pythonパッケージ確認
uv run python -c "import uvloop, websockets; print('Dependencies OK')"
```

### 2. サーバー起動 (5分)

**ターミナル1: AgentServer**
```bash
uv run aetherterm --debug --host localhost --port 57575 --unsecure
```

**ターミナル2: フロントエンド**
```bash
cd frontend && pnpm run dev
```

**ターミナル3: ControlServer（オプション）**
```bash
uv run aetherterm-control --debug
```

### 3. 基本動作確認 (5分)

1. ブラウザで `http://localhost:5173` にアクセス
2. ターミナルが正常に表示されることを確認
3. 基本コマンド実行: `ls`, `pwd`, `echo "hello"`
4. Socket.IO接続状態を開発者ツールで確認

## 🧪 実動作テスト手順

### Phase 1: 通常コマンドテスト (15分)

**目的**: 通常のコマンドが正常に動作することを確認

```bash
# 基本コマンド
ls -la
pwd
echo "Hello World"
date
whoami

# ディレクトリ操作
mkdir test_dir
cd test_dir
touch test_file.txt
ls
cd ..
rm -rf test_dir
```

**期待結果**: すべてのコマンドが正常実行され、ブロックされない

### Phase 2: 危険キーワード検出テスト (30分)

**目的**: 自動ブロック機能の動作確認

#### テストケース1: Critical系キーワード
```bash
echo "critical error detected"
echo "This is a critical situation"
echo "critical system failure"
```

#### テストケース2: 削除系キーワード
```bash
echo "rm -rf test"
echo "dangerous rm -rf command"
echo "rm -rf /"
```

#### テストケース3: セキュリティ系キーワード
```bash
echo "hack attempt detected"
echo "security hack in progress"
echo "hacking tools"
```

**期待結果**: 
- 各コマンドでブロック警告が表示される
- ターミナル入力がブロックされる
- フロントエンドに警告メッセージが表示される

### Phase 3: Ctrl+D解除機能テスト (15分)

**目的**: ブロック解除機能の動作確認

1. 危険キーワードでブロック状態にする
2. `Ctrl+D` キーを押下
3. ブロックが解除されることを確認
4. 通常コマンドが実行可能になることを確認

**期待結果**: 
- `Ctrl+D`でブロックが解除される
- 警告メッセージが消える
- 通常の入力が可能になる

### Phase 4: 複数セッションテスト (15分)

**目的**: 複数ターミナルでの動作確認

1. 複数のブラウザタブでターミナルを開く
2. 一つのセッションで危険キーワードを実行
3. 他のセッションの状態を確認
4. セッション間の独立性を確認

**期待結果**: 
- 各セッションが独立してブロック状態を管理
- 一つのセッションのブロックが他に影響しない

## 🔍 デバッグ・トラブルシューティング

### よくある問題と解決方法

#### 1. サーバー起動エラー
```bash
# ポート使用確認
lsof -i :57575
lsof -i :5173

# プロセス終了
kill -9 <PID>

# 再起動
uv run aetherterm --debug --host localhost --port 57575 --unsecure
```

#### 2. フロントエンド接続エラー
```bash
# Node.js依存関係再インストール
cd frontend
rm -rf node_modules
pnpm install
pnpm run dev
```

#### 3. Socket.IO通信エラー
- ブラウザ開発者ツールのNetworkタブを確認
- WebSocket接続状態をチェック
- サーバーログでエラーメッセージを確認

#### 4. 自動ブロック機能が動作しない
```bash
# ログ確認
tail -f /tmp/aetherterm.log

# モジュール確認
uv run python -c "from src.aetherterm.agentserver.log_analyzer import LogAnalyzer; print('LogAnalyzer OK')"
uv run python -c "from src.aetherterm.agentserver.auto_blocker import AutoBlocker; print('AutoBlocker OK')"
```

## 📊 テスト結果記録テンプレート

### 基本動作テスト
- [ ] AgentServer起動: ✅/❌
- [ ] フロントエンド起動: ✅/❌
- [ ] Socket.IO接続: ✅/❌
- [ ] 基本コマンド実行: ✅/❌

### 自動ブロック機能テスト
- [ ] Critical系キーワード検出: ✅/❌
- [ ] 削除系キーワード検出: ✅/❌
- [ ] セキュリティ系キーワード検出: ✅/❌
- [ ] ブロック警告表示: ✅/❌

### Ctrl+D解除機能テスト
- [ ] キー検出: ✅/❌
- [ ] ブロック解除: ✅/❌
- [ ] 警告メッセージ消去: ✅/❌
- [ ] 通常入力復帰: ✅/❌

### 複数セッションテスト
- [ ] セッション独立性: ✅/❌
- [ ] 同時接続: ✅/❌
- [ ] 状態管理: ✅/❌

## 🛠️ 改善・修正が必要な場合

### 優先度高: 即座に修正が必要
- 基本動作が動かない
- Socket.IO通信エラー
- サーバー起動エラー

### 優先度中: 機能改善
- ブロック検出精度の向上
- 警告メッセージの改善
- UI/UXの向上

### 優先度低: 将来的な改善
- パフォーマンス最適化
- 追加機能の実装
- コードリファクタリング

## 📁 重要ファイルの場所

### バックエンド
```
src/aetherterm/agentserver/
├── log_analyzer.py      # ログ解析エンジン
├── auto_blocker.py      # 自動ブロック機能
├── control_integration.py # 制御統合
└── socket_handlers.py   # WebSocketハンドラー
```

### フロントエンド
```
frontend/src/
├── components/BlockAlert.vue        # ブロック警告
├── components/TerminalComponent.vue # ターミナル統合
└── stores/terminalBlockStore.ts     # 状態管理
```

### 設定
```
├── pyproject.toml       # Python依存関係
└── frontend/package.json # Node.js依存関係
```

## 🔧 開発者ツール活用

### ブラウザ開発者ツール
1. **Console**: エラーメッセージ確認
2. **Network**: WebSocket通信確認
3. **Application**: ローカルストレージ確認

### サーバーログ
```bash
# AgentServerログ
tail -f /tmp/aetherterm.log

# リアルタイム監視
watch -n 1 'tail -10 /tmp/aetherterm.log'
```

## 📈 パフォーマンス監視

### メトリクス確認
- CPU使用率
- メモリ使用量
- WebSocket接続数
- 解析処理時間

### 監視コマンド
```bash
# システムリソース
top -p $(pgrep -f aetherterm)

# ネットワーク接続
netstat -an | grep :57575
```

## 🎯 次回セッションの目標

### 短期目標 (1-2時間)
1. ✅ 全テストケースの実行
2. ✅ 基本機能の動作確認
3. ✅ 問題点の特定と修正

### 中期目標 (半日)
1. エラーハンドリングの強化
2. パフォーマンス最適化
3. UI/UXの改善

### 長期目標 (1日以上)
1. 高度な解析ルールの実装
2. カスタマイズ機能の追加
3. 機械学習統合の検討

## 📞 サポート情報

### 参考ドキュメント
- [`docs/WORK_SESSION_2025-06-17.md`](./WORK_SESSION_2025-06-17.md) - 前回作業の詳細
- [`docs/CENTRAL_CONTROL_ARCHITECTURE.md`](./CENTRAL_CONTROL_ARCHITECTURE.md) - アーキテクチャ設計
- [`docs/BASIC_OPERATION_TEST.md`](./BASIC_OPERATION_TEST.md) - 基本動作テスト

### 緊急時の対応
1. 全サーバーを停止: `Ctrl+C` × 3
2. ポートを解放: `lsof -ti:57575,5173 | xargs kill -9`
3. 環境をリセット: `uv sync && cd frontend && pnpm install`

---

**🎉 準備完了！次回のセッションで素晴らしい成果を上げましょう！**