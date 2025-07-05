# Local Short-Term Memory Analysis System

## 概要 (Overview)

短期記憶だけでできることを実装しました。このシステムはAgentServer内で完結する軽量な分析機能で、ControlServerとの通信無しでリアルタイムな洞察を提供します。

## 主要コンポーネント (Key Components)

### 1. LocalShortTermAnalyzer (`short_term_memory_local.py`)

AgentServer内で動作するローカル分析システム。以下の機能を提供：

- **リアルタイム分析**: 30秒間隔でパターン検出と洞察生成
- **軽量メモリ管理**: 最新データのみ保持（コマンド100件、エラー50件など）
- **即座の異常検出**: 遅いコマンド、エラースパイク、パフォーマンス劣化

### 2. Local Insights API (`interfaces/api/local_insights_api.py`)

RESTful APIエンドポイントを提供：

- `GET /api/v1/insights/current` - 現在のインサイト取得
- `GET /api/v1/insights/patterns` - 検出されたパターン取得  
- `GET /api/v1/insights/session/{session_id}` - セッション固有の分析
- `GET /api/v1/insights/agent/summary` - エージェント全体サマリ
- `GET /api/v1/insights/real-time/alerts` - リアルタイムアラート
- `GET /api/v1/insights/performance/metrics` - パフォーマンス分析
- `POST /api/v1/insights/demo/generate_test_data` - デモ用テストデータ生成

### 3. AsyncioTerminal Integration

ターミナル操作が自動的に記録され分析されます：

- **コマンド実行**: 実行時間、終了コード
- **エラーイベント**: PTY操作エラー、デコードエラー
- **パフォーマンス**: データサイズ、リサイズ時間
- **ユーザー操作**: 入力、リサイズ操作

## 短期記憶だけでできること (Local-Only Capabilities)

### 即座の検出 (Immediate Detection)

1. **遅いコマンド検出** - 2秒以上のコマンド実行
2. **連続エラー検出** - 3回連続のコマンドエラー
3. **エラースパイク** - 5分間で5件以上のエラー
4. **頻発エラー** - 同じエラーが3回以上
5. **パフォーマンス劣化** - 平均より50%以上の悪化

### パターン分析 (Pattern Analysis)

1. **コマンドシーケンス** - 頻出コマンドペアの検出
2. **エラーパターン** - エラータイプ別の頻度分析
3. **ユーザー行動** - 高エラー率セッションの特定

### 推奨事項生成 (Recommendation Generation)

- エラー率改善の提案
- パフォーマンス最適化の推奨
- 作業自動化の検討

## 使用方法 (Usage)

### 1. システム起動

AgentServerが起動すると自動的にローカル分析器が初期化されます。

### 2. API呼び出し例

```bash
# 現在のインサイト取得
curl http://localhost:57575/api/v1/insights/current

# デモデータ生成とテスト
curl -X POST http://localhost:57575/api/v1/insights/demo/generate_test_data

# リアルタイムアラート取得
curl http://localhost:57575/api/v1/insights/real-time/alerts?severity=high
```

### 3. フィルタリング

多くのエンドポイントでフィルタリングオプションを提供：

- `priority`: low, medium, high, urgent
- `insight_type`: performance, anomaly, pattern, trend
- `severity`: info, warning, error, critical

## アーキテクチャの利点 (Architecture Benefits)

### ControlServer不要 (No ControlServer Required)

- **独立動作**: ネットワーク接続やControlServerが不要
- **低レイテンシ**: ローカル処理により即座の応答
- **高可用性**: 外部依存性が最小限

### 軽量設計 (Lightweight Design)

- **メモリ効率**: 循環バッファーで最新データのみ保持
- **CPU効率**: 30秒間隔の軽量分析処理
- **自動クリーンアップ**: 古いデータの自動削除

### 拡張性 (Extensibility)

- **モジュラー設計**: 新しい分析タイプの簡単追加
- **API拡張**: RESTエンドポイントの柔軟な追加
- **統合しやすさ**: 既存のターミナルシステムとの自然な統合

## データフロー (Data Flow)

```
ターミナル操作 → AsyncioTerminal → LocalShortTermAnalyzer
                                         ↓
                                  パターン検出・分析
                                         ↓
                                  インサイト生成
                                         ↓
                              Local Insights API → フロントエンド
```

## 実装完了事項 (Implementation Status)

✅ **完全実装済み**
- LocalShortTermAnalyzer による軽量分析
- Local Insights API の全7エンドポイント
- AsyncioTerminal との自動統合
- 循環インポート問題の解決

✅ **動作確認済み**
- コマンド実行の自動記録
- エラーイベントの即座検出
- パフォーマンス指標の収集
- リアルタイムパターン分析

## 今後の拡張可能性 (Future Extensions)

1. **機械学習統合**: 異常検出モデルの追加
2. **可視化**: リアルタイムダッシュボード
3. **アラート**: WebSocket経由のプッシュ通知
4. **カスタマイズ**: ユーザー定義の分析ルール

## 技術的成果 (Technical Achievements)

### 循環インポート問題の解決

元々存在していた`ContextService`と`context_inference.api`間の循環インポートを解決：

- **問題**: `ContextService` → `context_inference` → `context_inference.api` → `ContextService`
- **解決**: TYPE_CHECKINGと依存性注入の適切な使用、未実装APIの簡素化

### アーキテクチャの改善

- **レガシーAPI**: 複雑な依存性を持つコンテキスト推論API → 非推奨化
- **新API**: 軽量なローカルインサイトAPI → 完全実装
- **統合**: 既存のターミナルシステムとの自然な統合

このシステムにより、短期記憶だけで即座の価値を提供し、ユーザーの操作効率向上とシステムの安定性確保に貢献します。