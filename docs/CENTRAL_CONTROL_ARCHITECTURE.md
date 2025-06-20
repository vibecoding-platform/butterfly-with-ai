# 中央制御アーキテクチャ設計

## フェーズ1: 中央での監督ユーザーからの制御

### アーキテクチャ概要
```
AdminControlPanel (Frontend) 
    ↓ HTTP/WebSocket
AgentServer (Control API)
    ↓ WebSocket
ControlServer (Central Control)
    ↓ WebSocket Broadcast
AgentServer (Session Management)
    ↓ Socket.IO
Multiple Terminal Sessions
```

### 主要コンポーネント

#### 1. AdminControlPanel拡張
**ファイル**: `frontend/src/components/AdminControlPanel.vue`

**機能**:
- アクティブセッション一覧表示
- 緊急ブロックボタン
- 個別セッション制御
- ブロック解除機能
- リアルタイム状態更新

**API**:
```typescript
interface SessionControl {
  blockAllSessions(reason: string): Promise<void>
  blockSession(sessionId: string, reason: string): Promise<void>
  unblockSession(sessionId: string): Promise<void>
  getActiveSessions(): Promise<SessionInfo[]>
}
```

#### 2. ControlServer基本実装
**ファイル**: `src/aetherterm/controlserver/`

**機能**:
- 管理者制御指示の受信・処理
- AgentServerとの双方向通信
- セッション状態の一元管理
- ブロック履歴の記録

**WebSocket API**:
```json
// 管理者からの一括ブロック指示
{
  "type": "admin_block_all",
  "reason": "緊急メンテナンス",
  "admin_user": "admin@example.com",
  "timestamp": "2025-06-17T20:39:00+09:00"
}

// AgentServerへの一括ブロック指示
{
  "type": "emergency_block",
  "severity": "admin_initiated",
  "message": "管理者による緊急ブロック: 緊急メンテナンス",
  "action": "block_all_sessions",
  "block_id": "block_20250617_203900"
}
```

#### 3. AgentServer制御機能拡張
**ファイル**: `src/aetherterm/agentserver/`

**機能**:
- ControlServerからの制御指示受信
- 全セッションへの一括通知
- 入力ブロック制御
- Ctrl+D解除機能

**Socket.IO Events**:
```javascript
// クライアントへのブロック通知
socket.emit('input_block', {
  message: '!!!管理者による緊急ブロック!!! Ctrl+Dで確認',
  block_reason: '緊急メンテナンス',
  block_id: 'block_20250617_203900',
  unblock_key: 'Ctrl+D'
})

// ブロック解除通知
socket.emit('input_unblock', {
  message: 'ブロックが解除されました',
  block_id: 'block_20250617_203900'
})
```

### データフロー

#### 1. 緊急ブロックフロー
```
1. 管理者がAdminControlPanelで「緊急ブロック」ボタンをクリック
2. フロントエンドがAgentServerのControl APIを呼び出し
3. AgentServerがControlServerに管理者指示を転送
4. ControlServerが全AgentServerに一括ブロック指示を送信
5. 各AgentServerが配下の全セッションをブロック
6. 各ターミナルクライアントにブロック通知を表示
```

#### 2. 個別解除フロー
```
1. ユーザーがターミナルでCtrl+Dを入力
2. AgentServerがブロック解除をControlServerに通知
3. ControlServerが解除を承認
4. 該当セッションのブロックを解除
5. ユーザーに解除完了を通知
```

### セキュリティ考慮事項

#### 認証・認可
- 管理者権限の厳格な検証
- セッション管理とCSRF対策
- 監査ログの記録

#### 誤操作防止
- 確認ダイアログの実装
- ブロック理由の必須入力
- 段階的エスカレーション

#### 可用性確保
- ControlServerの冗長化対応
- 通信障害時のフォールバック
- 緊急時の手動解除手順

### 実装優先順位

#### Phase 1.1: 基本制御機能
1. ControlServer基本実装
2. AgentServerブロック機能
3. AdminControlPanel基本UI

#### Phase 1.2: 高度制御機能
1. 個別セッション制御
2. ブロック履歴管理
3. 状態監視ダッシュボード

#### Phase 1.3: 運用機能
1. 監査ログ機能
2. 通知システム統合
3. 緊急時手順の自動化

### 次フェーズへの準備

#### データ収集基盤
- 全ターミナルログの構造化
- メトリクス収集の開始
- 分析用データパイプライン構築

#### 解析準備
- ログパターンの分類
- 異常検知アルゴリズムの検討
- 機械学習モデルの設計

この設計により、段階的に高度な制御システムを構築していきます。