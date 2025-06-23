# 階層型イベント命名リファクタリング記録

**日付**: 2025-06-22  
**作業**: ターミナルイベントを階層型命名規則にリファクタリング

## 📋 **変更概要**

Socket.IOイベント名を平坦な構造から階層型に変更し、アーキテクチャ（Workspace → Tab → Pane）を反映した命名規則を実装。

## 🎯 **変更前後の対比**

### **変更前（平坦なイベント名）**
```javascript
// 送信イベント
terminal:create
terminal:input
terminal:resize
terminal:focus
terminal:close

// 受信イベント
terminal:created
terminal:data
terminal:error
```

### **変更後（階層型イベント名）**
```javascript
// 送信イベント
workspace:tab:{tabId}:pane:{paneId}:terminal:create
workspace:tab:{tabId}:pane:{paneId}:terminal:input
workspace:tab:{tabId}:pane:{paneId}:terminal:resize
workspace:tab:{tabId}:pane:{paneId}:terminal:focus
workspace:tab:{tabId}:pane:{paneId}:terminal:close

// 受信イベント
workspace:tab:{tabId}:pane:{paneId}:terminal:created
workspace:tab:{tabId}:pane:{paneId}:terminal:data
workspace:tab:{tabId}:pane:{paneId}:terminal:error
```

## 🔧 **実装されたファイル変更**

### **1. フロントエンド（frontend/src/components/）**

#### **TerminalPaneManager.vue**
- `PaneTerminal`コンポーネントにtabIdを渡すよう修正
```vue
<PaneTerminal 
  :key="pane.id"
  :tab-id="terminalTab.id"
  :pane-id="pane.id"
  :terminal-id="pane.terminalId"
/>
```

#### **PaneTerminal.vue**
- **Props interface拡張**: `tabId`を追加
```typescript
interface Props {
  tabId: string
  paneId: string
  terminalId: string
}
```

- **階層イベント名生成関数**: 
```typescript
const createEventName = (operation: string) => {
  return `workspace:tab:${props.tabId}:pane:${props.paneId}:terminal:${operation}`
}
```

- **全イベント送信の更新**:
  - `terminal:create` → `createEventName('create')`
  - `terminal:input` → `createEventName('input')`
  - `terminal:resize` → `createEventName('resize')`
  - `terminal:focus` → `createEventName('focus')`
  - `terminal:close` → `createEventName('close')`

- **全イベントリスナーの更新**:
  - `terminal:created` → `createEventName('created')`
  - `terminal:data` → `createEventName('data')`
  - `terminal:error` → `createEventName('error')`

### **2. バックエンド（src/aetherterm/agentserver/）**

#### **socket_handlers.py**
- **階層イベントハンドラー追加**:
  - `hierarchical_terminal_create()`
  - `hierarchical_terminal_input()`
  - `hierarchical_terminal_resize()`
  - `hierarchical_terminal_focus()`
  - `hierarchical_terminal_close()`

- **動的イベントルーター**:
```python
async def handle_dynamic_terminal_event(sid, event_name, data):
    """Route hierarchical terminal events to appropriate handlers"""
    # Parse: workspace:tab:{tabId}:pane:{paneId}:terminal:{operation}
    parts = event_name.split(':')
    if len(parts) != 7 or parts[0] != 'workspace' or parts[1] != 'tab' or parts[3] != 'pane' or parts[5] != 'terminal':
        return
    
    tab_id = parts[2]
    pane_id = parts[4] 
    operation = parts[6]
    
    # Route to appropriate handler...
```

- **階層レスポンス送信対応**:
```python
# dataにtabIdとpaneIdが含まれる場合は階層レスポンス送信
if 'tabId' in data and 'paneId' in data:
    hierarchical_event = f"workspace:tab:{data['tabId']}:pane:{data['paneId']}:terminal:created"
    await sio_instance.emit(hierarchical_event, response_data, room=sid)
```

#### **server.py**
- **動的イベントハンドリング設定**:
```python
# Socket.IOの_trigger_eventメソッドをオーバーライド
original_trigger_event = sio._trigger_event

async def enhanced_trigger_event(event, namespace, sid, data):
    if (event.startswith('workspace:tab:') and 
        ':pane:' in event and 
        ':terminal:' in event):
        await socket_handlers.handle_dynamic_terminal_event(sid, event, data)
        return True
    else:
        return await original_trigger_event(event, namespace, sid, data)

sio._trigger_event = enhanced_trigger_event
```

## 🎁 **利点・メリット**

### **1. 階層関係の明確化**
- イベント名からWorkspace → Tab → Paneの関係が一目瞭然
- デバッグ時の追跡が容易

### **2. スケーラビリティ向上**
- 複数Tab/Pane管理が簡潔
- 将来的な階層拡張に対応

### **3. 名前空間の整理**
- イベント衝突の回避
- 機能別の明確な分離

### **4. デバッグ効率の向上**
- どのTab/Paneの操作かが即座に分かる
- Socket.IOトラッキングでの詳細な監視が可能

## 🔄 **後方互換性**

- **レガシーイベント保持**: 既存の`terminal:*`イベントハンドラーも残存
- **段階的移行**: 新旧両方のイベント形式を同時にサポート
- **自動判定**: dataにtabId/paneIdが含まれる場合は階層レスポンス送信

## 🧪 **テスト要件**

1. **階層イベント送受信テスト**
   - フロントエンドからの階層イベント送信確認
   - バックエンドでの適切なルーティング確認
   - 階層レスポンスイベントの受信確認

2. **複数Tab/Pane環境テスト**
   - 複数タブで異なるターミナル作成
   - 正しいTab/Paneに対してのみイベント配信確認

3. **レガシー互換性テスト**
   - 従来の`terminal:*`イベントも正常動作確認

## 🚀 **次回作業項目**

1. **terminal:dataイベントの階層対応**
   - output_callbackでtab_id/pane_idを取得する仕組み
   - 階層型データ配信の実装

2. **完全階層移行**
   - レガシーイベントハンドラーの段階的削除
   - 全Workspaceイベントの階層命名統一

3. **パフォーマンス最適化**
   - 動的イベントルーティングの効率化
   - イベント名解析のキャッシュ化

## 📊 **変更統計**

- **変更ファイル数**: 3ファイル
- **追加行数**: ~120行
- **新規階層イベントハンドラー**: 5個
- **フロントエンドイベント変更**: 8個

---

**ステータス**: ✅ 基本実装完了、テスト・検証段階  
**最終更新**: 2025-06-22 17:30 JST