# AetherTerm 開発ロードマップ

## 📅 開発計画概要

AetherTermの機能拡張・改善計画を段階的に整理した開発ロードマップです。
設定制御機能、権限管理、AI統合機能、マルチタブ機能を中心とした計画を策定します。

## 🎯 開発優先順位

### 🔥 最優先 (P0)
1. **設定による機能制御** - AI機能のOn/Off、モード切り替え
2. **TOML設定管理** - 階層化された設定システム
3. **権限管理機能** - 参照者/Administrator権限制御

### ⚡ 高優先 (P1)  
4. **マルチタブ基盤** - ユーザータブ管理機能
5. **AI自動セッション管理** - AIによるタブ作成・階層化
6. **AgentShell統合強化** - AgentServerとの連携改善

### 📈 中優先 (P2)
7. **UI/UX改善** - タブインターフェース、階層表示
8. **監査・ログ強化** - PTY監査機能の拡張
9. **パフォーマンス最適化** - 大量セッション対応

## 🗓️ フェーズ別開発計画

### 📋 Phase 1: 設定制御基盤 (2-3週間)

#### 🎯 目標
- TOML設定による機能制御システム確立
- AI機能のOn/Off制御実装
- フロントエンドでの設定反映

#### 📦 実装内容

**Week 1: バックエンド設定管理**
- [ ] TOML設定管理クラス実装
- [ ] 環境変数・CLI引数の優先順位制御
- [ ] 設定検証・デフォルト値適用
- [ ] 設定API エンドポイント作成

**Week 2: フロントエンド設定連携**
- [ ] 設定取得・反映機能
- [ ] UI表示制御ロジック
- [ ] 設定変更のリアルタイム反映
- [ ] 設定画面UI（開発モード）

**Week 3: テスト・統合**
- [ ] 設定機能の統合テスト
- [ ] 各モードでの動作確認
- [ ] ドキュメント更新・サンプル作成

#### ✅ 完了条件
- [ ] TOML設定ファイルによる全機能制御
- [ ] 環境変数による上書き制御
- [ ] フロントエンドでの設定依存UI制御
- [ ] 設定変更の即座反映

---

### 🔐 Phase 1.5: 権限管理機能 (2週間)

#### 🎯 目標
- シングルユーザー環境での権限レベル制御
- 参照者/Administrator権限の実装
- 権限に応じたUI・機能制限

#### 📦 実装内容

**Week 1: 権限システム設計・実装**
- [ ] 権限レベル定義・管理クラス
- [ ] 権限設定（TOML/環境変数）
- [ ] 権限チェック機能・ミドルウェア
- [ ] 権限変更API（Administrator用）

**Week 2: UI権限制御・統合**
- [ ] 権限依存UI表示制御
- [ ] 操作権限チェック・無効化
- [ ] 権限変更UI（設定画面）
- [ ] 権限関連テスト・検証

#### 🔐 権限レベル詳細

**👀 参照者 (Viewer)**
```
✅ 許可される操作:
- ターミナル出力の閲覧
- AIチャット履歴の閲覧
- セッション状況の監視
- ログ・監査情報の閲覧
- 統計・レポートの確認

❌ 制限される操作:
- ターミナルへのコマンド入力
- 新規セッション・タブ作成
- 設定変更・管理操作
- AI機能の実行・操作
- システム管理機能
```

**👑 Administrator**
```
✅ 全機能利用可能:
- 全ターミナル操作
- セッション・タブ管理
- AI機能フル活用
- 設定・システム管理
- 権限変更・ユーザー管理
- 監査・ログ管理
```

#### ⚙️ 権限設定例
```toml
[auth]
# 権限レベル設定
permission_level = "administrator"  # "viewer" または "administrator"
allow_permission_change = true      # 権限変更の許可
session_timeout = 3600              # セッションタイムアウト（秒）

[auth.viewer]
# 参照者モード設定
read_only_mode = true               # 読み取り専用モード
hide_admin_features = true          # 管理機能UIを非表示
terminal_input_disabled = true      # ターミナル入力無効

[auth.administrator] 
# 管理者モード設定
full_access = true                  # フルアクセス
audit_all_actions = true            # 全操作監査
require_confirmation = false        # 危険操作の確認要求
```

#### 🔧 実装アーキテクチャ
```
設定ファイル → 権限管理 → ミドルウェア → API/UI制御
     ↓           ↓          ↓           ↓
   権限レベル    権限チェック  操作制限    表示制御
```

#### ✅ 完了条件
- [ ] 権限レベルによる機能制限の完全実装
- [ ] UI/APIの権限依存制御
- [ ] 権限設定の動的変更機能
- [ ] セキュリティテスト・検証完了

---

### 📊 Phase 2: マルチタブ基盤 (3-4週間)

#### 🎯 目標
- ユーザー作成タブの管理機能
- タブ切り替え・操作UI
- セッション状態管理
- **権限に応じたタブ操作制限**

#### 📦 実装内容

**Week 1: バックエンドセッション管理**
- [ ] セッション管理クラス設計・実装
- [ ] タブ作成・削除・更新API（権限チェック付き）
- [ ] WebSocketセッション関連付け
- [ ] セッション永続化機能

**Week 2: フロントエンドタブUI**
- [ ] タブコンポーネント設計・実装
- [ ] **権限依存タブ操作UI**（参照者は閲覧のみ）
- [ ] ドラッグ&ドロップ並び替え（Administrator専用）
- [ ] タブコンテキストメニュー（権限制御）

**Week 3: セッション統合**
- [ ] ターミナルとタブの連携
- [ ] セッション復元機能
- [ ] タブ間データ共有
- [ ] **権限レベル毎の監視・管理**

**Week 4: 高度機能・最適化**
- [ ] タブ履歴・ナビゲーション
- [ ] パフォーマンス最適化
- [ ] メモリ使用量最適化
- [ ] 権限制御のエラーハンドリング強化

#### 🔐 権限統合機能
```
参照者: タブ閲覧のみ、新規作成・削除・編集不可
Administrator: 全タブ操作、管理機能、設定変更可能
```

#### ✅ 完了条件
- [ ] 複数ターミナルタブの作成・管理（権限制御付き）
- [ ] スムーズなタブ切り替え
- [ ] セッション状態の永続化・復元
- [ ] 権限レベル毎の適切な機能制限

### 🤖 Phase 3: AI自動セッション管理 (4-5週間)

#### 🎯 目標
- AIによる自動タブ作成・管理
- 目的・時系列での階層化表示
- AgentShell統合によるAI実行履歴
- **権限に応じたAI機能制限**

#### 📦 実装内容

**Week 1: AI セッション管理設計**
- [ ] AIセッション分類・階層化ロジック
- [ ] 目的検出・自動分類アルゴリズム
- [ ] セッション関連性分析
- [ ] **AI機能の権限チェック統合**

**Week 2: AgentShell統合**
- [ ] AgentServer ↔ AgentShell通信強化
- [ ] AI実行タスクの追跡・監視
- [ ] **Administrator権限でのAI実行制御**
- [ ] 参照者向けAI実行状況表示

**Week 3: フロントエンド階層表示**
- [ ] 階層ツリーコンポーネント
- [ ] 時系列表示・フィルタリング
- [ ] **権限レベル毎のAI情報表示**
- [ ] セッション詳細・履歴表示

**Week 4: AI分析・最適化**
- [ ] セッション使用パターン分析
- [ ] AI学習・改善機能
- [ ] 予測的セッション作成（Administrator用）
- [ ] 権限レベル毎のAI機能最適化

**Week 5: 統合・テスト**
- [ ] 全体統合テスト
- [ ] 権限制御テスト
- [ ] パフォーマンス・負荷テスト
- [ ] セキュリティ・権限テスト

#### 🔐 AI機能権限制御
```
参照者: AI履歴閲覧、状況監視のみ
Administrator: AI実行、設定変更、学習制御、全権限
```

#### ✅ 完了条件
- [ ] AIによる自動セッション作成・分類（権限制御付き）
- [ ] 階層化された AI セッション表示
- [ ] AgentShell統合による実行履歴追跡
- [ ] 権限レベル毎の適切なAI機能制限

### 🔧 Phase 4: 高度機能・最適化 (継続開発)

#### 🎯 目標
- システム全体の安定性・パフォーマンス向上
- 運用機能・監視機能強化
- 権限管理の高度化・セキュリティ強化

## 🛠️ 技術実装詳細

### 🔐 権限管理アーキテクチャ
```
TOML設定 → 権限管理 → 認証・認可 → ミドルウェア → API/UI制御
    ↓        ↓         ↓         ↓          ↓
 権限レベル  権限チェック  セッション管理  操作制限   表示制御
```

### 📋 設定統合アーキテクチャ
```
TOML設定ファイル → 設定+権限管理 → 依存性注入 → 各コンポーネント
        ↓              ↓              ↓           ↓
   階層化設定+権限    検証・変換+権限   設定+権限提供  機能・権限制御
```

### 📊 セッション・権限統合アーキテクチャ  
```
フロントエンド → 権限チェック → WebSocket → AgentServer → セッション管理
      ↓           ↓            ↓           ↓            ↓
   タブUI      権限依存UI    リアルタイム   API制御+権限   状態管理+権限
```

## 📊 進捗管理・品質保証

### 🔐 セキュリティ・権限テスト
- **権限昇格テスト**: 不正な権限取得の防止確認
- **API権限テスト**: 全APIエンドポイントの権限チェック
- **UI権限テスト**: 権限レベル毎の適切なUI表示
- **セッション権限テスト**: セッション毎の権限維持・切り替え

### ✅ 品質基準（権限追加）
- **セキュリティ**: 権限昇格攻撃の防止100%
- **権限制御**: 全機能の権限チェック実装100%
- **UI一貫性**: 権限レベル毎の一貫したUI表示
- **パフォーマンス**: 権限チェックによる性能影響 < 10ms

---

🎯 **次のアクション**: Phase 1の設定制御機能実装後、Phase 1.5の権限管理機能の詳細設計・実装を開始