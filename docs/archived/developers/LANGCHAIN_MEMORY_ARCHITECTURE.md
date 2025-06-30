# LangChain メモリ保存・ログ要約・再問い合わせアーキテクチャ仕様書

## 1. プロジェクト概要

### 1.1 目的
AetherTermプロジェクトにLangChainを統合し、以下の機能を提供する：
- 会話履歴のメモリ保存機能
- ターミナルログの要約機能
- 保存されたメモリと要約を活用した再問い合わせ機能

### 1.2 設計原則
- **モジュラー設計**: 既存のAgentShell/AgentServerアーキテクチャとの独立性
- **テスト可能性**: 各コンポーネントの単体テスト・統合テスト対応
- **設定外部化**: 環境変数のハードコーディング禁止
- **依存性注入**: dependency-injectorとの統合

## 2. アーキテクチャ概要

### 2.1 システム構成図
```
┌─────────────────────────────────────────────────────────────┐
│                    AetherTerm Core                          │
├─────────────────────────────────────────────────────────────┤
│  AgentServer (FastAPI + SocketIO)                          │
│  ├── LangChain Memory Service                              │
│  ├── Log Summarization Service                             │
│  └── Query Enhancement Service                             │
├─────────────────────────────────────────────────────────────┤
│  AgentShell (Terminal Integration)                         │
│  ├── Memory Context Collector                              │
│  ├── Log Stream Processor                                  │
│  └── AI Service Integration                                │
├─────────────────────────────────────────────────────────────┤
│  LangChain Integration Layer                               │
│  ├── Memory Stores (Vector/SQL/Redis)                     │
│  ├── Summarization Chains                                 │
│  ├── Retrieval Chains                                     │
│  └── Context Enhancement                                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 主要コンポーネント
1. **Memory Management Service**: 会話履歴の保存・検索
2. **Log Summarization Service**: ターミナルログの要約処理
3. **Query Enhancement Service**: 過去のコンテキストを活用した問い合わせ強化
4. **Context Collector**: セッション情報とコンテキストの収集
5. **Storage Adapters**: 複数のストレージバックエンドへの対応

## 3. 機能仕様

### 3.1 メモリ保存機能

#### 3.1.1 会話履歴管理
- **対象データ**: ユーザー入力、AI応答、コマンド実行結果
- **保存形式**: 構造化データ（JSON + メタデータ）
- **保存先**: Vector Store（Chroma/FAISS）+ SQL Database
- **保持期間**: 設定可能（デフォルト30日）

#### 3.1.2 セッション管理
- **セッション識別**: UUID-based session tracking
- **コンテキスト継続**: セッション間でのメモリ共有
- **プライバシー**: ユーザー別データ分離

### 3.2 ログ要約機能

#### 3.2.1 要約対象
- **ターミナル出力**: コマンド実行結果、エラーメッセージ
- **システムログ**: アプリケーションログ、デバッグ情報
- **AI解析結果**: 既存のAI分析データ

#### 3.2.2 要約レベル
- **リアルタイム要約**: 短期間（5分間隔）の要約
- **セッション要約**: セッション終了時の全体要約
- **日次要約**: 1日分のアクティビティ要約

### 3.3 再問い合わせ機能

#### 3.3.1 コンテキスト検索
- **セマンティック検索**: Vector Storeを使用した類似性検索
- **時系列検索**: 時間軸に基づく履歴検索
- **キーワード検索**: 従来の文字列マッチング

#### 3.3.2 問い合わせ強化
- **コンテキスト注入**: 関連する過去の会話を自動追加
- **要約情報活用**: 長期履歴の要約を参考情報として提供
- **パターン認識**: 類似の問題解決パターンの提案

## 4. コンポーネント設計

### 4.1 ディレクトリ構造
```
src/aetherterm/langchain/
├── __init__.py
├── config.py                    # 設定管理
├── containers.py                # 依存性注入設定
├── memory/
│   ├── __init__.py
│   ├── base.py                  # 抽象基底クラス
│   ├── conversation_memory.py   # 会話メモリ管理
│   ├── session_memory.py        # セッションメモリ管理
│   └── storage_adapters.py      # ストレージアダプター
├── summarization/
│   ├── __init__.py
│   ├── base.py                  # 抽象基底クラス
│   ├── log_summarizer.py        # ログ要約エンジン
│   ├── session_summarizer.py    # セッション要約
│   └── chain_builders.py        # LangChain構築
├── retrieval/
│   ├── __init__.py
│   ├── base.py                  # 抽象基底クラス
│   ├── context_retriever.py     # コンテキスト検索
│   ├── query_enhancer.py        # 問い合わせ強化
│   └── similarity_search.py     # 類似性検索
├── integration/
│   ├── __init__.py
│   ├── agentserver_plugin.py    # AgentServer統合
│   ├── agentshell_plugin.py     # AgentShell統合
│   └── ai_service_bridge.py     # 既存AI連携
└── utils/
    ├── __init__.py
    ├── text_processing.py       # テキスト処理
    ├── embedding_utils.py       # 埋め込み処理
    └── validation.py            # データ検証
```

### 4.2 主要クラス設計

#### 4.2.1 Memory Management
```python
class ConversationMemoryManager:
    """会話履歴管理クラス"""
    
    async def store_conversation(
        self, 
        session_id: str, 
        user_input: str, 
        ai_response: str, 
        metadata: Dict[str, Any]
    ) -> str
    
    async def retrieve_conversation_history(
        self, 
        session_id: str, 
        limit: int = 10
    ) -> List[ConversationEntry]
    
    async def search_similar_conversations(
        self, 
        query: str, 
        threshold: float = 0.7
    ) -> List[ConversationEntry]
```

#### 4.2.2 Log Summarization
```python
class LogSummarizationService:
    """ログ要約サービス"""
    
    async def summarize_terminal_logs(
        self, 
        logs: List[str], 
        time_window: timedelta
    ) -> LogSummary
    
    async def create_session_summary(
        self, 
        session_id: str
    ) -> SessionSummary
    
    async def generate_daily_summary(
        self, 
        date: datetime
    ) -> DailySummary
```

#### 4.2.3 Query Enhancement
```python
class QueryEnhancementService:
    """問い合わせ強化サービス"""
    
    async def enhance_query_with_context(
        self, 
        query: str, 
        session_id: str
    ) -> EnhancedQuery
    
    async def retrieve_relevant_context(
        self, 
        query: str, 
        max_results: int = 5
    ) -> List[ContextEntry]
    
    async def suggest_follow_up_questions(
        self, 
        conversation_history: List[ConversationEntry]
    ) -> List[str]
```

## 5. データフロー設計

### 5.1 メモリ保存フロー
```
User Input → Context Collector → Memory Manager → Vector Store
                                              → SQL Database
                                              → Cache (Redis)
```

### 5.2 ログ要約フロー
```
Terminal Logs → Log Processor → Summarization Chain → Summary Store
                             → Real-time Summary
                             → Session Summary
                             → Daily Summary
```

### 5.3 再問い合わせフロー
```
User Query → Query Enhancer → Context Retriever → Enhanced Query
                           → Memory Search
                           → Summary Search
                           → AI Provider
```

## 6. 設定管理

### 6.1 設定ファイル構造
```toml
[langchain]
# LangChain基本設定
enabled = true
debug = false
log_level = "INFO"

[langchain.memory]
# メモリ設定
retention_days = 30
max_conversations_per_session = 100
vector_store_type = "chroma"  # chroma, faiss, pinecone
sql_database_url = "${DATABASE_URL}"
redis_url = "${REDIS_URL}"

[langchain.summarization]
# 要約設定
realtime_interval_minutes = 5
max_log_entries_per_summary = 1000
summarization_model = "gpt-3.5-turbo"
summary_max_tokens = 500

[langchain.retrieval]
# 検索設定
similarity_threshold = 0.7
max_context_entries = 5
embedding_model = "text-embedding-ada-002"
search_timeout_seconds = 10

[langchain.providers]
# AIプロバイダー設定
openai_api_key = "${OPENAI_API_KEY}"
anthropic_api_key = "${ANTHROPIC_API_KEY}"
default_provider = "openai"
```

### 6.2 環境変数
```bash
# 必須環境変数
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# オプション環境変数
ANTHROPIC_API_KEY=sk-ant-...
PINECONE_API_KEY=...
LANGCHAIN_DEBUG=false
```

## 7. TDDアンカー（テスト観点）

### 7.1 単体テスト
```python
# tests/langchain/memory/test_conversation_memory.py
class TestConversationMemoryManager:
    async def test_store_conversation_success(self):
        """会話保存の正常系テスト"""
        pass
    
    async def test_retrieve_conversation_history_with_limit(self):
        """履歴取得の制限数テスト"""
        pass
    
    async def test_search_similar_conversations_threshold(self):
        """類似会話検索の閾値テスト"""
        pass

# tests/langchain/summarization/test_log_summarizer.py
class TestLogSummarizationService:
    async def test_summarize_terminal_logs_empty_input(self):
        """空ログの要約テスト"""
        pass
    
    async def test_create_session_summary_with_context(self):
        """セッション要約のコンテキストテスト"""
        pass
    
    async def test_generate_daily_summary_aggregation(self):
        """日次要約の集約テスト"""
        pass
```

### 7.2 統合テスト
```python
# tests/langchain/integration/test_end_to_end.py
class TestLangChainIntegration:
    async def test_full_conversation_flow(self):
        """会話→保存→検索→強化の全フローテスト"""
        pass
    
    async def test_log_summarization_pipeline(self):
        """ログ要約パイプラインテスト"""
        pass
    
    async def test_context_retrieval_accuracy(self):
        """コンテキスト検索精度テスト"""
        pass
```

### 7.3 パフォーマンステスト
```python
# tests/langchain/performance/test_scalability.py
class TestPerformance:
    async def test_memory_storage_performance(self):
        """メモリ保存性能テスト（1000件/秒）"""
        pass
    
    async def test_similarity_search_latency(self):
        """類似性検索レイテンシテスト（<100ms）"""
        pass
    
    async def test_concurrent_summarization(self):
        """並行要約処理テスト"""
        pass
```

## 8. 実装フェーズ

### 8.1 Phase 1: 基盤構築（2週間）
- [ ] 基本設定とコンテナ設定
- [ ] Memory Management基盤
- [ ] ストレージアダプター実装
- [ ] 基本的な単体テスト

### 8.2 Phase 2: 要約機能（2週間）
- [ ] Log Summarization Service
- [ ] LangChain統合
- [ ] リアルタイム要約機能
- [ ] 要約機能テスト

### 8.3 Phase 3: 検索・強化機能（2週間）
- [ ] Context Retrieval実装
- [ ] Query Enhancement機能
- [ ] 類似性検索最適化
- [ ] 統合テスト

### 8.4 Phase 4: 統合・最適化（1週間）
- [ ] AgentServer/AgentShell統合
- [ ] パフォーマンス最適化
- [ ] エラーハンドリング強化
- [ ] ドキュメント整備

## 9. 運用考慮事項

### 9.1 監視・ログ
- メモリ使用量監視
- 要約処理時間監視
- 検索精度メトリクス
- エラー率追跡

### 9.2 スケーラビリティ
- Vector Store分散化
- 要約処理の並列化
- キャッシュ戦略
- データベース最適化

### 9.3 セキュリティ
- データ暗号化
- アクセス制御
- 個人情報保護
- 監査ログ

## 10. 依存関係

### 10.1 新規依存関係
```toml
dependencies = [
    # 既存依存関係...
    "langchain>=0.1.0",
    "langchain-openai>=0.1.0",
    "langchain-anthropic>=0.1.0",
    "langchain-community>=0.1.0",
    "chromadb>=0.4.0",
    "faiss-cpu>=1.7.0",
    "redis>=4.5.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "sentence-transformers>=2.2.0",
]
```

### 10.2 開発依存関係
```toml
[project.optional-dependencies]
langchain-dev = [
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.11.0",
    "factory-boy>=3.3.0",
    "freezegun>=1.2.0",
]
```

この仕様書は、既存のAetherTermアーキテクチャとの統合を重視し、モジュラー設計とテスト可能性を確保したLangChain統合プランを提供します。