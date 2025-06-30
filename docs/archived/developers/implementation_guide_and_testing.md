# LangChain統合 - 実装ガイド & TDD戦略

## 1. 実装概要

本ドキュメントは、AetherTermプロジェクトへのLangChain統合における実装手順、
TDD（Test-Driven Development）戦略、および品質保証プロセスを定義します。

## 2. 実装フェーズ詳細

### 2.1 Phase 1: メモリ基盤構築（2週間）

#### Week 1: 基盤設計・実装
```bash
# Day 1-2: 環境セットアップ
uv add langchain langchain-openai langchain-anthropic langchain-community
uv add chromadb faiss-cpu redis sqlalchemy alembic
uv add sentence-transformers

# Day 3-4: 設定管理実装
touch src/aetherterm/langchain/__init__.py
touch src/aetherterm/langchain/config.py
touch src/aetherterm/langchain/containers.py

# Day 5-7: データモデル・ストレージアダプター実装
mkdir -p src/aetherterm/langchain/memory
touch src/aetherterm/langchain/memory/{__init__.py,models.py,base.py}
touch src/aetherterm/langchain/memory/{conversation_memory.py,storage_adapters.py}
```

#### Week 2: テスト・統合
```bash
# Day 8-10: 単体テスト実装
mkdir -p tests/langchain/memory
touch tests/langchain/{__init__.py,test_config.py}
touch tests/langchain/memory/{__init__.py,test_conversation_memory.py}
touch tests/langchain/memory/{test_storage_adapters.py,test_models.py}

# Day 11-14: 統合テスト・デバッグ
pytest tests/langchain/ -v --cov=src/aetherterm/langchain --cov-report=html
```

#### TDDサイクル例（設定管理）
```python
# 1. Red: テストを書く（失敗する）
def test_config_from_env_with_api_key():
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        config = LangChainConfig.from_env()
        assert config.openai_api_key == 'test-key'

# 2. Green: 最小限の実装（テストを通す）
@classmethod
def from_env(cls) -> 'LangChainConfig':
    return cls(openai_api_key=os.getenv('OPENAI_API_KEY'))

# 3. Refactor: リファクタリング
@classmethod
def from_env(cls) -> 'LangChainConfig':
    return cls(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
        # ... 他の設定項目
    )
```

### 2.2 Phase 2: ログ要約機能（2週間）

#### Week 3: 要約エンジン実装
```bash
# Day 15-17: ログ処理パイプライン
mkdir -p src/aetherterm/langchain/summarization
touch src/aetherterm/langchain/summarization/{__init__.py,log_processor.py}
touch src/aetherterm/langchain/summarization/{log_summarizer.py,chain_builders.py}

# Day 18-21: LangChainチェーン統合
# プロンプトテンプレート作成
# Map-Reduce要約チェーン実装
# リアルタイム要約機能実装
```

#### TDDサイクル例（ログ要約）
```python
# 1. Red: 要約機能のテスト
@pytest.mark.asyncio
async def test_create_realtime_summary_with_logs():
    logs = [create_sample_log_entry() for _ in range(5)]
    summary = await summarizer.create_realtime_summary(logs, "test-session")
    
    assert summary.session_id == "test-session"
    assert summary.summary_type == "realtime"
    assert len(summary.content) > 0
    assert summary.log_count == 5

# 2. Green: 基本実装
async def create_realtime_summary(self, logs, session_id):
    return LogSummary(
        session_id=session_id,
        summary_type="realtime",
        content="基本要約",
        log_count=len(logs)
    )

# 3. Refactor: AI統合
async def create_realtime_summary(self, logs, session_id):
    log_text = self._format_logs_for_summary(logs)
    ai_summary = await self.realtime_chain.arun(logs=log_text)
    
    return LogSummary(
        session_id=session_id,
        summary_type="realtime",
        content=ai_summary,
        log_count=len(logs),
        # ... メタデータ追加
    )
```

### 2.3 Phase 3: 検索・強化機能（2週間）

#### Week 5: 検索システム実装
```bash
# Day 29-31: クエリ分析・拡張
mkdir -p src/aetherterm/langchain/retrieval
touch src/aetherterm/langchain/retrieval/{__init__.py,query_analyzer.py}
touch src/aetherterm/langchain/retrieval/{context_retriever.py,query_enhancer.py}

# Day 32-35: マルチソース検索実装
# Vector Store検索
# キーワード検索
# 時系列検索
# ハイブリッド検索
```

#### TDDサイクル例（検索機能）
```python
# 1. Red: 検索機能のテスト
@pytest.mark.asyncio
async def test_retrieve_relevant_context():
    query = "git コマンドの使い方"
    result = await retriever.retrieve_relevant_context(query, "test-session")
    
    assert len(result.contexts) > 0
    assert result.search_time_ms > 0
    assert "semantic" in result.sources_used

# 2. Green: モック実装
async def retrieve_relevant_context(self, query, session_id):
    return RetrievalResult(
        contexts=[ContextEntry(content="モック結果", source="test", relevance_score=0.8, timestamp=datetime.utcnow())],
        total_found=1,
        search_time_ms=100.0,
        sources_used=["semantic"]
    )

# 3. Refactor: 実際の検索実装
async def retrieve_relevant_context(self, query, session_id):
    start_time = datetime.utcnow()
    query_analysis = await self.query_analyzer.analyze_query(query)
    
    # 並列検索実行
    search_tasks = [
        self._semantic_search(query_analysis, session_id),
        self._keyword_search(query_analysis, session_id)
    ]
    
    results = await asyncio.gather(*search_tasks)
    contexts = await self._merge_and_rank_results(results, query_analysis)
    
    return RetrievalResult(
        contexts=contexts,
        total_found=len(contexts),
        search_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
        sources_used=["semantic", "keyword"]
    )
```

### 2.4 Phase 4: 統合・最適化（1週間）

#### Week 7: 統合・最適化
```bash
# Day 36-38: AgentServer統合
mkdir -p src/aetherterm/langchain/integration
touch src/aetherterm/langchain/integration/{__init__.py,langchain_plugin.py}
touch src/aetherterm/langchain/integration/{agentserver_integration.py,agentshell_integration.py}

# Day 39-42: パフォーマンス最適化・エラーハンドリング
mkdir -p src/aetherterm/langchain/{optimization,error_handling}
touch src/aetherterm/langchain/optimization/{__init__.py,performance_optimizer.py}
touch src/aetherterm/langchain/error_handling/{__init__.py,error_manager.py}
```

## 3. TDD戦略詳細

### 3.1 テスト階層
```
┌─────────────────────────────────────────────────────────────┐
│                    テストピラミッド                          │
├─────────────────────────────────────────────────────────────┤
│  E2E Tests (5%)                                            │
│  ├── フルワークフローテスト                                 │
│  └── ユーザーシナリオテスト                                 │
├─────────────────────────────────────────────────────────────┤
│  Integration Tests (25%)                                   │
│  ├── コンポーネント間統合                                   │
│  ├── データベース統合                                       │
│  └── AI API統合                                            │
├─────────────────────────────────────────────────────────────┤
│  Unit Tests (70%)                                          │
│  ├── 各クラス・メソッドの単体テスト                         │
│  ├── モック・スタブを活用                                   │
│  └── エッジケース・エラーケース                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 テストカテゴリ別実装

#### 単体テスト（Unit Tests）
```python
# tests/langchain/memory/test_conversation_memory.py
class TestConversationMemoryManager:
    """会話メモリ管理の単体テスト"""
    
    @pytest.fixture
    def memory_manager(self, mock_storage_adapters, config):
        return ConversationMemoryManager(*mock_storage_adapters, config)
    
    @pytest.mark.asyncio
    async def test_store_conversation_success(self, memory_manager):
        """正常系: 会話保存成功"""
        result = await memory_manager.store_conversation(
            session_id="test-session",
            content="テストメッセージ"
        )
        assert result is not None
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_store_conversation_empty_content(self, memory_manager):
        """異常系: 空コンテンツ"""
        with pytest.raises(ValueError, match="コンテンツが空です"):
            await memory_manager.store_conversation(
                session_id="test-session",
                content=""
            )
    
    @pytest.mark.asyncio
    async def test_retrieve_conversation_history_limit(self, memory_manager):
        """境界値: 履歴取得制限"""
        result = await memory_manager.retrieve_conversation_history(
            session_id="test-session",
            limit=5
        )
        assert len(result) <= 5
```

#### 統合テスト（Integration Tests）
```python
# tests/langchain/integration/test_end_to_end.py
class TestLangChainIntegration:
    """エンドツーエンド統合テスト"""
    
    @pytest.mark.asyncio
    async def test_full_conversation_workflow(self, app_client):
        """完全な会話ワークフローテスト"""
        # 1. 会話を開始
        response = await app_client.post("/api/langchain/chat", json={
            "message": "git statusの使い方を教えて",
            "session_id": "integration-test"
        })
        assert response.status_code == 200
        
        # 2. コンテキストが保存されることを確認
        memory_response = await app_client.get(
            "/api/langchain/memory/stats/integration-test"
        )
        assert memory_response.status_code == 200
        stats = memory_response.json()
        assert stats["conversation_count"] > 0
        
        # 3. 関連する質問で検索が機能することを確認
        follow_up_response = await app_client.post("/api/langchain/chat", json={
            "message": "git addはどうやって使うの？",
            "session_id": "integration-test"
        })
        assert follow_up_response.status_code == 200
        
        # コンテキストが活用されていることを確認
        data = follow_up_response.json()
        assert len(data["context_used"]) > 0
```

#### パフォーマンステスト
```python
# tests/langchain/performance/test_scalability.py
class TestPerformance:
    """パフォーマンステスト"""
    
    @pytest.mark.asyncio
    async def test_memory_storage_performance(self, memory_manager):
        """メモリ保存性能テスト（目標: 1000件/秒）"""
        import time
        
        start_time = time.time()
        tasks = []
        
        for i in range(1000):
            task = memory_manager.store_conversation(
                session_id=f"perf-test-{i % 10}",
                content=f"パフォーマンステストメッセージ {i}"
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        elapsed_time = time.time() - start_time
        throughput = 1000 / elapsed_time
        
        assert throughput >= 1000, f"スループット不足: {throughput:.2f} ops/sec"
    
    @pytest.mark.asyncio
    async def test_similarity_search_latency(self, context_retriever):
        """類似性検索レイテンシテスト（目標: <100ms）"""
        import time
        
        queries = [
            "git コマンドの使い方",
            "エラーの解決方法",
            "ファイルの操作方法"
        ]
        
        for query in queries:
            start_time = time.time()
            
            result = await context_retriever.retrieve_relevant_context(
                query=query,
                session_id="latency-test"
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            assert elapsed_ms < 100, f"レイテンシ超過: {elapsed_ms:.2f}ms"
            assert len(result.contexts) > 0
```

### 3.3 モック・フィクスチャ戦略

#### 共通フィクスチャ
```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.aetherterm.langchain.config import LangChainConfig

@pytest.fixture
def config():
    """テスト用設定"""
    return LangChainConfig(
        enabled=True,
        openai_api_key='test-key',
        retention_days=30,
        similarity_threshold=0.7,
        max_context_entries=5
    )

@pytest.fixture
def mock_vector_store():
    """モックVector Store"""
    mock = AsyncMock()
    mock.asimilarity_search.return_value = [
        MagicMock(
            page_content="モック検索結果",
            metadata={"score": 0.8, "timestamp": "2023-01-01T00:00:00"}
        )
    ]
    return mock

@pytest.fixture
def mock_llm():
    """モックLLM"""
    mock = AsyncMock()
    mock.arun.return_value = "モックAI応答"
    return mock

@pytest.fixture
async def app_client():
    """テスト用アプリケーションクライアント"""
    from fastapi.testclient import TestClient
    from src.aetherterm.agentserver.server import create_app
    
    app = create_app(test_mode=True)
    return TestClient(app)
```

#### データファクトリー
```python
# tests/factories.py
import factory
from datetime import datetime
from src.aetherterm.langchain.memory.models import ConversationEntry, LogSummary

class ConversationEntryFactory(factory.Factory):
    class Meta:
        model = ConversationEntry
    
    session_id = factory.Sequence(lambda n: f"session-{n}")
    content = factory.Faker('text', max_nb_chars=200)
    timestamp = factory.LazyFunction(datetime.utcnow)
    metadata = factory.Dict({})

class LogSummaryFactory(factory.Factory):
    class Meta:
        model = LogSummary
    
    session_id = factory.Sequence(lambda n: f"session-{n}")
    summary_type = "realtime"
    content = factory.Faker('text', max_nb_chars=500)
    log_count = factory.Faker('random_int', min=1, max=100)
```

## 4. 品質保証プロセス

### 4.1 継続的インテグレーション
```yaml
# .github/workflows/langchain-tests.yml
name: LangChain Integration Tests

on:
  push:
    paths:
      - 'src/aetherterm/langchain/**'
      - 'tests/langchain/**'
  pull_request:
    paths:
      - 'src/aetherterm/langchain/**'
      - 'tests/langchain/**'

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:6
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install uv
      run: pip install uv
    
    - name: Install dependencies
      run: uv pip install -e .[langchain-dev]
    
    - name: Run unit tests
      run: |
        pytest tests/langchain/ \
          --cov=src/aetherterm/langchain \
          --cov-report=xml \
          --cov-report=html \
          --cov-fail-under=80
      env:
        DATABASE_URL: postgresql://postgres:test@localhost/test
        REDIS_URL: redis://localhost:6379
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    
    - name: Run integration tests
      run: |
        pytest tests/langchain/integration/ \
          --timeout=300
      env:
        DATABASE_URL: postgresql://postgres:test@localhost/test
        REDIS_URL: redis://localhost:6379
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### 4.2 コード品質チェック
```bash
# pre-commit設定
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        files: ^src/aetherterm/langchain/
  
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
        files: ^src/aetherterm/langchain/
  
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
        files: ^src/aetherterm/langchain/
        args: [--max-line-length=100]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v0.950
    hooks:
      - id: mypy
        files: ^src/aetherterm/langchain/
        additional_dependencies: [types-all]
```

### 4.3 パフォーマンス監視
```python
# tests/langchain/performance/benchmarks.py
import pytest
import asyncio
import time
from memory_profiler import profile

class PerformanceBenchmarks:
    """パフォーマンスベンチマーク"""
    
    @profile
    @pytest.mark.benchmark
    async def test_memory_usage_under_load(self, memory_manager):
        """負荷時のメモリ使用量テスト"""
        tasks = []
        for i in range(10000):
            task = memory_manager.store_conversation(
                session_id=f"bench-{i % 100}",
                content=f"ベンチマークテスト {i}"
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # メモリ使用量が閾値以下であることを確認
        import psutil
        memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        assert memory_mb < 500, f"メモリ使用量超過: {memory_mb:.2f}MB"
    
    @pytest.mark.benchmark
    async def test_concurrent_search_performance(self, context_retriever):
        """並行検索性能テスト"""
        queries = [f"テストクエリ {i}" for i in range(100)]
        
        start_time = time.time()
        
        tasks = [
            context_retriever.retrieve_relevant_context(query, f"session-{i}")
            for i, query in enumerate(queries)
        ]
        
        results = await asyncio.gather(*tasks)
        
        elapsed_time = time.time() - start_time
        throughput = len(queries) / elapsed_time
        
        assert throughput >= 50, f"検索スループット不足: {throughput:.2f} queries/sec"
        assert all(len(result.contexts) >= 0 for result in results)
```

## 5. デプロイメント戦略

### 5.1 段階的ロールアウト
```bash
# Phase 1: 開発環境デプロイ
export LANGCHAIN_ENABLED=true
export LANGCHAIN_DEBUG=true
uv run aetherterm --debug --langchain-mode=development

# Phase 2: ステージング環境デプロイ
export LANGCHAIN_ENABLED=true
export LANGCHAIN_DEBUG=false
uv run aetherterm --langchain-mode=staging

# Phase 3: 本番環境デプロイ（フィーチャーフラグ）
export LANGCHAIN_ENABLED=false  # 初期は無効
export LANGCHAIN_FEATURE_FLAG=beta_users_only
uv run aetherterm --langchain-mode=production
```

### 5.2 監視・アラート
```python
# monitoring/langchain_metrics.py
from prometheus_client import Counter, Histogram, Gauge

# メトリクス定義
langchain_operations_total = Counter(
    'langchain_operations_total',
    'Total LangChain operations',
    ['operation_type', 'status']
)

langchain_operation_duration = Histogram(
    'langchain_operation_duration_seconds',
    'LangChain operation duration',
    ['operation_type']
)

langchain_memory_usage = Gauge(
    'langchain_memory_usage_bytes',
    'LangChain memory usage'
)

# 使用例
@langchain_operation_duration.time()
async def store_conversation_with_metrics(*args, **kwargs):
    try:
        result = await store_conversation(*args, **kwargs)
        langchain_operations_total.labels(
            operation_type='store_conversation',
            status='success'
        ).inc()
        return result
    except Exception as e:
        langchain_operations_total.labels(
            operation_type='store_conversation',
            status='error'
        ).inc()
        raise
```

## 6. 実装チェックリスト

### 6.1 Phase 1 完了基準
- [ ] 設定管理クラス実装・テスト（カバレッジ90%以上）
- [ ] データモデル定義・バリデーション
- [ ] ストレージアダプター実装（Vector/SQL/Redis）
- [ ] 会話メモリ管理クラス実装・テスト
- [ ] 依存性注入コンテナ設定
- [ ] 統合テスト実装・実行
- [ ] パフォーマンステスト（目標値達成）
- [ ] ドキュメント整備

### 6.2 Phase 2 完了基準
- [ ] ログ処理パイプライン実装・テスト
- [ ] 要約エンジン実装（リアルタイム/セッション/日次）
- [ ] LangChainチェーン統合・テスト
- [ ] プロンプトテンプレート最適化
- [ ] バッチ処理機能実装
- [ ] エラーハンドリング実装
- [ ] パフォーマンス最適化
- [ ] 統合テスト実行

### 6.3 Phase 3 完了基準
- [ ] クエリ分析・拡張機能実装・テスト
- [ ] マルチソース検索実装（セマンティック/キーワード/時系列）
- [ ] コンテキスト統合・ランキング機能
- [ ] 問い合わせ強化機能実装
- [ ] 検索精度評価・改善
- [ ] レスポンス時間最適化
- [ ] 統合テスト・E2Eテスト実行
- [ ] ユーザビリティテスト

### 6.4 Phase 4 完了基準
- [ ] AgentServer/AgentShell統合完了
- [ ] APIエンドポイント実装・テスト
- [ ] WebSocket統合・リアルタイム機能
- [ ] パフォーマンス最適化・監視実装
- [ ] エラーハンドリング・回復機能
- [ ] セキュリティ監査・対策
- [ ] 本番環境デプロイ準備
- [ ] 運用ドキュメント整備

この実装ガイドに従って、段階的かつ品質を重視したLangChain統合を実現できます。