# Socket.IO Tracing Implementation

## 概要

AetherTermプロジェクト固有のSocket.IOトラッキング実装です。Vue Frontend ↔ Python Backend間のSocket.IO通信をリアルタイムで監視し、OpenObserveへのエクスポートに対応しています。

## アーキテクチャ

### Vue Frontend Side

```
TrackedSocketService
├── SocketConnectionTracker (実装)
│   ├── Request-Response correlation
│   ├── Timeout detection
│   ├── Performance metrics
│   └── OpenObserve export
├── NoOpSocketConnectionTracker (Null Object)
└── SocketTrackingMonitor (UI Component)
```

### Python Backend Side

```
socket_tracking.py
├── SocketConnectionTracker
├── NoOpSocketConnectionTracker 
└── Global tracking functions
```

## 主要コンポーネント

### 1. ISocketConnectionTracker (Interface)

**ファイル**: `frontend/src/services/tracking/ISocketConnectionTracker.ts`

```typescript
interface ISocketConnectionTracker {
  trackRequest(eventName: string, data: any): string
  trackResponse(eventName: string, data: any, requestId?: string): void
  trackTimeout(requestId: string): void
  trackError(requestId: string, error: Error | string): void
  
  getPendingRequests(): PendingRequest[]
  getMetrics(): ConnectionMetrics
  
  onRequestTimeout(callback: (request: PendingRequest) => void): void
  onSlowResponse(callback: (request: PendingRequest, duration: number) => void): void
  onError(callback: (request: PendingRequest, error: string) => void): void
}
```

### 2. SocketConnectionTracker (Vue Implementation)

**ファイル**: `frontend/src/services/tracking/SocketConnectionTracker.ts`

**機能**:
- Request-Response correlation (requestId based)
- タイムアウト検出 (デフォルト5秒)
- 応答時間測定
- エラー追跡
- OpenObserve自動エクスポート

**主要メソッド**:
```typescript
// リクエスト追跡開始
trackRequest(eventName: string, data: any): string

// レスポンス追跡
trackResponse(eventName: string, data: any, requestId?: string): void

// タイムアウト処理
trackTimeout(requestId: string): void
```

### 3. TrackedSocketService (AetherTermService拡張)

**ファイル**: `frontend/src/services/tracking/TrackedSocketService.ts`

**機能**:
- 既存AetherTermServiceの拡張
- Socket.IOのemit/receiveを自動instrumentation
- 環境変数による有効/無効切り替え

**インスツルメンテーション**:
```typescript
// emit wrapper
socket.emit = (...args: any[]) => {
  const [eventName, data, ...rest] = args
  const requestId = this.tracker.trackRequest(eventName, data || {})
  
  // requestIdをdataに追加
  let trackedData = { ...data, _requestId: requestId }
  return originalEmit(eventName, trackedData, ...rest)
}

// receive tracking
trackedEvents.forEach(eventName => {
  this.socket.on(eventName, (data: any) => {
    this.tracker.trackResponse(eventName, data, data?._requestId)
  })
})
```

### 4. Python Backend Tracking

**ファイル**: `src/aetherterm/agentserver/socket_tracking.py`

**主要クラス**:
```python
class SocketConnectionTracker:
    def track_request(self, event_name: str, data: Dict[str, Any], client_id: Optional[str] = None) -> str
    def track_response(self, request_id: str, response_event: str, success: bool = True, error: Optional[str] = None) -> None
    def track_error(self, request_id: str, error: str) -> None
    def get_metrics(self) -> Dict[str, Any]
```

**統合例** (`socket_handlers.py`):
```python
async def terminal_create(sid, data):
    # リクエスト追跡開始
    request_id = track_socket_request('terminal:create', data, sid)
    
    try:
        # ターミナル作成処理
        # ...
        
        # 成功レスポンス追跡
        track_socket_response(request_id, 'terminal:created', success=True)
    except Exception as e:
        # エラーレスポンス追跡
        track_socket_response(request_id, 'terminal:created', success=False, error=str(e))
```

### 5. OpenObserve Integration

**ファイル**: `frontend/src/services/tracking/OpenObserveExporter.ts`

**機能**:
- OTLP準拠のトレースデータ生成
- バッチ処理による効率的な送信
- OpenObserve Cloud対応

**データ形式**:
```typescript
interface SocketTraceEvent {
  timestamp: number
  traceId: string
  spanId: string
  operationName: string  // "terminal:create -> terminal:created"
  duration?: number
  tags: Record<string, any>
  status: 'ok' | 'error' | 'timeout'
  level: 'info' | 'warn' | 'error'
}
```

### 6. SocketTrackingMonitor (UI Component)

**ファイル**: `frontend/src/components/SocketTrackingMonitor.vue`

**機能**:
- リアルタイム監視ダッシュボード
- 保留中リクエスト表示
- パフォーマンスメトリクス
- アクティビティログ
- データエクスポート

## 設定

### 環境変数

```bash
# トラッキング有効/無効
VITE_SOCKET_TRACKING_ENABLED=true
SOCKET_TRACKING_ENABLED=true

# OpenObserve Cloud設定
VITE_OPENOBSERVE_ENDPOINT=https://api.openobserve.ai/api/[ORG_ID]
VITE_OPENOBSERVE_USER=username
VITE_OPENOBSERVE_PASS=password
VITE_OPENOBSERVE_ORG=organization_id
```

### 初期化設定

**Vue Frontend** (`main.ts`):
```typescript
const trackedSocketService = TrackedSocketService.getInstance({
  defaultTimeout: 5000,
  slowResponseThreshold: 1000,
  enableDetailedLogging: true,
  enableMetrics: true
});
```

**Python Backend**:
環境変数 `SOCKET_TRACKING_ENABLED=true` で自動有効化

## 使用方法

### 1. リアルタイム監視

1. ブラウザで `http://localhost:5173` にアクセス
2. 右パネルの **「🔗 Socket Monitor」タブ** をクリック
3. Socket.IO通信をリアルタイム監視

### 2. プログラムからのアクセス

**Vue Frontend**:
```typescript
import TrackedSocketService from './services/tracking/TrackedSocketService'

const service = TrackedSocketService.getInstance()
const tracker = service.getTracker()

// メトリクス取得
const metrics = tracker.getMetrics()

// 保留中リクエスト取得
const pending = tracker.getPendingRequests()
```

**Python Backend**:
```python
from aetherterm.agentserver.socket_tracking import get_socket_tracker

tracker = get_socket_tracker()
metrics = tracker.get_metrics()
pending = tracker.get_pending_requests()
```

### 3. カスタムイベント追跡

**手動追跡**:
```typescript
// Vue側
const tracker = service.getTracker()
const requestId = tracker.trackRequest('custom:event', { data: 'test' })

// 後でレスポンス追跡
tracker.trackResponse('custom:response', { result: 'success' }, requestId)
```

## トラッキング対象イベント

### 自動追跡イベント

**接続関連**:
- `socket:connect`
- `socket:disconnect`  
- `socket:connect_error`

**ターミナル関連**:
- `terminal:create` ↔ `terminal:created`
- `terminal:input` ↔ `terminal:input_response`
- `terminal:resize`
- `terminal:close`
- `shell:output`

**セッション関連**:
- `session:init`
- `session:end`

**管理関連**:
- `chat_message`
- `command_approval`
- `admin_pause_terminal`
- `admin_resume_terminal`

## OpenObserve Cloud連携

### データ送信形式

```json
{
  "timestamp": 1640995200000000,
  "message": "Socket.IO Event: terminal:create -> terminal:created",
  "level": "INFO",
  "service": "aetherterm-frontend",
  "trace_id": "1234567890abcdef1234567890abcdef",
  "span_id": "1234567890abcdef",
  "operation_name": "terminal:create -> terminal:created",
  "duration_ms": 150,
  "status": "ok",
  "socket.request.event": "terminal:create",
  "socket.response.event": "terminal:created",
  "socket.success": true
}
```

### エンドポイント設定

- **Stream**: `socket-io-traces`
- **認証**: Basic認証
- **バッチサイズ**: 10イベント
- **送信間隔**: 5秒

## デバッグ

### ログ出力

**開発時**: `enableDetailedLogging: true`
```
🔗 Socket tracking enabled with OpenObserve Cloud
📤 Socket request tracked: terminal:create [req_1640995200_1]
📥 Socket response tracked: terminal:created ✅ [req_1640995200_1] (150ms)
✅ Exported 5 events to OpenObserve Cloud
```

### トラブルシューティング

1. **トラッキングが動作しない**:
   - 環境変数 `VITE_SOCKET_TRACKING_ENABLED` を確認
   - ブラウザコンソールでエラーチェック

2. **OpenObserve送信失敗**:
   - 認証情報確認
   - ネットワーク接続確認
   - CORS設定確認

3. **Socket Monitorが空**:
   - TrackedSocketServiceの初期化確認
   - Socket.IO接続状態確認

## パフォーマンス考慮事項

### 最適化

- **Null Object Pattern**: 本番環境での無効化
- **バッチ処理**: OpenObserve送信の効率化  
- **メモリ管理**: 古いレスポンスデータの自動削除
- **スロットリング**: 高頻度イベントの制御

### 推奨設定

**開発環境**:
- `enableDetailedLogging: true`
- `enableMetrics: true`
- `sampleRate: 1.0` (100%)

**本番環境**:
- `enableDetailedLogging: false`
- `enableMetrics: true`
- `sampleRate: 0.1` (10%)

## 拡張可能性

### OTLP対応サービス

現在の実装はOpenTelemetry Protocol (OTLP) 準拠のため、以下のサービスに切り替え可能：

- **Jaeger**: `http://localhost:14268/api/traces`
- **Zipkin**: `http://localhost:9411/api/v2/spans`
- **Grafana Tempo**: カスタムエンドポイント
- **DataDog**: `https://trace.agent.datadoghq.com/v1/trace`
- **AWS X-Ray**: OTLP Collector経由
- **Google Cloud Trace**: OTLP Collector経由

### カスタム拡張

1. **新しいイベント追加**:
   ```typescript
   // frontend/src/services/tracking/TrackedSocketService.ts
   const customEvents = ['custom:event1', 'custom:event2']
   customEvents.forEach(eventName => {
     this.socket.on(eventName, (data) => {
       this.tracker.trackResponse(eventName, data, data?._requestId)
     })
   })
   ```

2. **カスタムメトリクス**:
   ```typescript
   interface CustomMetrics extends ConnectionMetrics {
     customMetric: number
   }
   ```

3. **カスタムエクスポーター**:
   ```typescript
   interface ICustomExporter {
     export(events: SocketTraceEvent[]): Promise<void>
   }
   ```

## ライセンスと制限

- プロジェクト固有実装
- OpenTelemetry準拠
- MIT License (プロジェクトに準拠)
- 商用利用可能

## 関連ドキュメント

- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/)
- [Socket.IO Documentation](https://socket.io/docs/)
- [OpenObserve Documentation](https://openobserve.ai/docs/)
- [Vue 3 Composition API](https://vuejs.org/guide/composition-api/)

## 更新履歴

- **2025-01-20**: 初版作成
- **機能追加**: Request-Response correlation
- **機能追加**: OpenObserve Cloud連携
- **機能追加**: リアルタイム監視UI