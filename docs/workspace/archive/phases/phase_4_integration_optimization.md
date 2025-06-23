# Phase 4: 統合・最適化 - 詳細設計仕様

## 1. 概要

LangChain統合の最終フェーズとして、全コンポーネントの統合、パフォーマンス最適化、
エラーハンドリング強化、および既存のAetherTermアーキテクチャとの完全統合を実現します。

## 2. 統合アーキテクチャ

### 2.1 全体統合図
```
┌─────────────────────────────────────────────────────────────┐
│                    AetherTerm + LangChain                   │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Vue.js)                                         │
│  ├── Chat Interface (Enhanced)                             │
│  ├── Memory Visualization                                  │
│  ├── Summary Dashboard                                     │
│  └── Context Search UI                                     │
├─────────────────────────────────────────────────────────────┤
│  AgentServer (FastAPI + SocketIO)                          │
│  ├── LangChain Integration Plugin                          │
│  ├── Memory Management API                                 │
│  ├── Summarization API                                     │
│  └── Enhanced Query API                                    │
├─────────────────────────────────────────────────────────────┤
│  AgentShell (Terminal Integration)                         │
│  ├── Memory Context Collector                              │
│  ├── Real-time Log Processor                              │
│  └── AI Service Bridge                                     │
├─────────────────────────────────────────────────────────────┤
│  LangChain Core Services                                   │
│  ├── Memory Management (Phase 1)                          │
│  ├── Log Summarization (Phase 2)                          │
│  ├── Context Retrieval (Phase 3)                          │
│  └── Query Enhancement (Phase 3)                          │
├─────────────────────────────────────────────────────────────┤
│  Storage Layer                                             │
│  ├── Vector Store (Chroma/FAISS)                          │
│  ├── SQL Database (PostgreSQL)                            │
│  ├── Cache Layer (Redis)                                  │
│  └── File Storage (Summaries/Logs)                        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 データフロー図
```
User Input → Query Analysis → Multi-Source Retrieval → Context Fusion
    ↓              ↓                    ↓                    ↓
Terminal ←── Enhanced Response ←── AI Generation ←── Ranked Context
    ↓
Log Capture → Real-time Processing → Summarization → Memory Storage
    ↓              ↓                    ↓              ↓
Background ←── Batch Processing ←── Daily Summary ←── Vector Index
```

## 3. 統合コンポーネント設計

### 3.1 LangChain統合プラグイン (`integration/langchain_plugin.py`)

```python
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..containers import LangChainContainer
from ..memory.conversation_memory import ConversationMemoryManager
from ..summarization.log_summarizer import LogSummarizationService
from ..retrieval.context_retriever import ContextRetrievalService
from ..retrieval.query_enhancer import QueryEnhancementService

logger = logging.getLogger(__name__)

# APIモデル
class ChatRequest(BaseModel):
    message: str
    session_id: str
    context_limit: Optional[int] = 5

class ChatResponse(BaseModel):
    response: str
    context_used: List[Dict[str, Any]]
    suggestions: List[str]
    metadata: Dict[str, Any]

class SummaryRequest(BaseModel):
    session_id: str
    summary_type: str = "session"  # realtime, session, daily

class SummaryResponse(BaseModel):
    summary: str
    log_count: int
    time_range: Dict[str, str]
    metadata: Dict[str, Any]

class LangChainIntegrationPlugin:
    """LangChain統合プラグイン"""
    
    def __init__(self):
        self.router = APIRouter(prefix="/api/langchain", tags=["langchain"])
        self._setup_routes()
        self._is_initialized = False
    
    @inject
    async def initialize(
        self,
        memory_manager: ConversationMemoryManager = Provide[LangChainContainer.conversation_memory_manager],
        summarization_service: LogSummarizationService = Provide[LangChainContainer.log_summarization_service],
        context_retriever: ContextRetrievalService = Provide[LangChainContainer.context_retrieval_service],
        query_enhancer: QueryEnhancementService = Provide[LangChainContainer.query_enhancement_service]
    ):
        """プラグインを初期化"""
        self.memory_manager = memory_manager
        self.summarization_service = summarization_service
        self.context_retriever = context_retriever
        self.query_enhancer = query_enhancer
        
        self._is_initialized = True
        logger.info("LangChain統合プラグインが初期化されました")
    
    def _setup_routes(self):
        """APIルートを設定"""
        
        @self.router.post("/chat", response_model=ChatResponse)
        async def enhanced_chat(request: ChatRequest):
            """強化されたチャット機能"""
            if not self._is_initialized:
                raise HTTPException(status_code=503, detail="プラグインが初期化されていません")
            
            try:
                # コンテキスト検索
                retrieval_result = await self.context_retriever.retrieve_relevant_context(
                    query=request.message,
                    session_id=request.session_id,
                    max_results=request.context_limit
                )
                
                # クエリ強化
                enhanced_query = await self.query_enhancer.enhance_query_with_context(
                    query=request.message,
                    contexts=retrieval_result.contexts,
                    session_id=request.session_id
                )
                
                # 会話を保存
                await self.memory_manager.store_conversation(
                    session_id=request.session_id,
                    content=request.message,
                    conversation_type="user_input",
                    role="user"
                )
                
                # AI応答を保存
                await self.memory_manager.store_conversation(
                    session_id=request.session_id,
                    content=enhanced_query.enhanced_prompt,
                    conversation_type="ai_response",
                    role="assistant"
                )
                
                return ChatResponse(
                    response=enhanced_query.enhanced_prompt,
                    context_used=[ctx.__dict__ for ctx in retrieval_result.contexts],
                    suggestions=enhanced_query.follow_up_suggestions,
                    metadata={
                        "search_time_ms": retrieval_result.search_time_ms,
                        "sources_used": retrieval_result.sources_used,
                        "confidence": enhanced_query.confidence
                    }
                )
                
            except Exception as e:
                logger.error(f"強化チャット処理中にエラー: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/summarize", response_model=SummaryResponse)
        async def create_summary(request: SummaryRequest):
            """要約作成"""
            if not self._is_initialized:
                raise HTTPException(status_code=503, detail="プラグインが初期化されていません")
            
            try:
                if request.summary_type == "session":
                    summary = await self.summarization_service.create_session_summary(
                        request.session_id
                    )
                elif request.summary_type == "daily":
                    summary = await self.summarization_service.create_daily_summary(
                        datetime.utcnow().date()
                    )
                else:
                    raise HTTPException(status_code=400, detail="無効な要約タイプ")
                
                return SummaryResponse(
                    summary=summary.content,
                    log_count=summary.log_count,
                    time_range={
                        "start": summary.start_time.isoformat(),
                        "end": summary.end_time.isoformat()
                    },
                    metadata=summary.metadata
                )
                
            except Exception as e:
                logger.error(f"要約作成中にエラー: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/memory/stats/{session_id}")
        async def get_memory_stats(session_id: str):
            """メモリ統計取得"""
            if not self._is_initialized:
                raise HTTPException(status_code=503, detail="プラグインが初期化されていません")
            
            try:
                stats = await self.memory_manager.get_conversation_statistics(session_id)
                return stats
                
            except Exception as e:
                logger.error(f"メモリ統計取得中にエラー: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/memory/cleanup")
        async def cleanup_old_data():
            """古いデータのクリーンアップ"""
            if not self._is_initialized:
                raise HTTPException(status_code=503, detail="プラグインが初期化されていません")
            
            try:
                deleted_count = await self.memory_manager.cleanup_old_conversations()
                return {"deleted_count": deleted_count}
                
            except Exception as e:
                logger.error(f"データクリーンアップ中にエラー: {e}")
                raise HTTPException(status_code=500, detail=str(e))
```

### 3.2 AgentServer統合 (`integration/agentserver_integration.py`)

```python
import logging
from typing import Dict, Any, Optional
import socketio

from ..agentserver.socket_handlers import SocketHandlers
from .langchain_plugin import LangChainIntegrationPlugin

logger = logging.getLogger(__name__)

class AgentServerLangChainIntegration:
    """AgentServerとLangChainの統合"""
    
    def __init__(self, sio: socketio.AsyncServer, langchain_plugin: LangChainIntegrationPlugin):
        self.sio = sio
        self.langchain_plugin = langchain_plugin
        self._setup_socket_handlers()
    
    def _setup_socket_handlers(self):
        """SocketIOハンドラーを設定"""
        
        @self.sio.event
        async def langchain_chat(sid, data):
            """LangChain強化チャット"""
            try:
                session_id = data.get('session_id', sid)
                message = data.get('message', '')
                
                if not message:
                    await self.sio.emit('langchain_error', {
                        'error': 'メッセージが空です'
                    }, room=sid)
                    return
                
                # LangChainプラグインで処理
                from ..integration.langchain_plugin import ChatRequest
                request = ChatRequest(
                    message=message,
                    session_id=session_id,
                    context_limit=data.get('context_limit', 5)
                )
                
                # 非同期処理開始の通知
                await self.sio.emit('langchain_processing', {
                    'status': 'processing',
                    'message': 'AI処理中...'
                }, room=sid)
                
                # 強化チャット実行
                response = await self.langchain_plugin.enhanced_chat(request)
                
                # 結果を送信
                await self.sio.emit('langchain_response', {
                    'response': response.response,
                    'context_used': response.context_used,
                    'suggestions': response.suggestions,
                    'metadata': response.metadata
                }, room=sid)
                
            except Exception as e:
                logger.error(f"LangChainチャット処理中にエラー: {e}")
                await self.sio.emit('langchain_error', {
                    'error': str(e)
                }, room=sid)
        
        @self.sio.event
        async def request_summary(sid, data):
            """要約リクエスト"""
            try:
                session_id = data.get('session_id', sid)
                summary_type = data.get('summary_type', 'session')
                
                from ..integration.langchain_plugin import SummaryRequest
                request = SummaryRequest(
                    session_id=session_id,
                    summary_type=summary_type
                )
                
                # 要約作成
                summary_response = await self.langchain_plugin.create_summary(request)
                
                # 結果を送信
                await self.sio.emit('summary_response', {
                    'summary': summary_response.summary,
                    'log_count': summary_response.log_count,
                    'time_range': summary_response.time_range,
                    'metadata': summary_response.metadata
                }, room=sid)
                
            except Exception as e:
                logger.error(f"要約作成中にエラー: {e}")
                await self.sio.emit('summary_error', {
                    'error': str(e)
                }, room=sid)
        
        @self.sio.event
        async def get_context_suggestions(sid, data):
            """コンテキスト提案取得"""
            try:
                session_id = data.get('session_id', sid)
                query = data.get('query', '')
                
                if not query:
                    await self.sio.emit('context_error', {
                        'error': 'クエリが空です'
                    }, room=sid)
                    return
                
                # コンテキスト検索
                retrieval_result = await self.langchain_plugin.context_retriever.retrieve_relevant_context(
                    query=query,
                    session_id=session_id,
                    max_results=5
                )
                
                # 結果を送信
                await self.sio.emit('context_suggestions', {
                    'contexts': [ctx.__dict__ for ctx in retrieval_result.contexts],
                    'total_found': retrieval_result.total_found,
                    'search_time_ms': retrieval_result.search_time_ms,
                    'sources_used': retrieval_result.sources_used
                }, room=sid)
                
            except Exception as e:
                logger.error(f"コンテキスト提案取得中にエラー: {e}")
                await self.sio.emit('context_error', {
                    'error': str(e)
                }, room=sid)
```

### 3.3 パフォーマンス最適化 (`optimization/performance_optimizer.py`)

```python
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """パフォーマンスメトリクス"""
    operation: str
    duration_ms: float
    memory_usage_mb: float
    timestamp: datetime
    metadata: Dict[str, Any]

class PerformanceOptimizer:
    """パフォーマンス最適化クラス"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self._cache = {}
        self._cache_ttl = {}
        self._batch_operations = []
        self._batch_size = 100
        self._batch_timeout = 30  # seconds
    
    async def optimize_vector_search(self, vector_store, query: str, **kwargs):
        """Vector Store検索の最適化"""
        start_time = time.time()
        
        try:
            # キャッシュチェック
            cache_key = f"vector_search:{hash(query)}"
            if self._is_cache_valid(cache_key):
                logger.debug(f"キャッシュヒット: {cache_key}")
                return self._cache[cache_key]
            
            # 検索実行
            results = await vector_store.asimilarity_search(query, **kwargs)
            
            # キャッシュに保存
            self._cache[cache_key] = results
            self._cache_ttl[cache_key] = datetime.utcnow() + timedelta(minutes=10)
            
            # メトリクス記録
            duration = (time.time() - start_time) * 1000
            self._record_metrics("vector_search", duration, {"query_length": len(query)})
            
            return results
            
        except Exception as e:
            logger.error(f"Vector検索最適化中にエラー: {e}")
            raise
    
    async def batch_memory_operations(self, operations: List[Dict[str, Any]]):
        """メモリ操作のバッチ処理"""
        self._batch_operations.extend(operations)
        
        if len(self._batch_operations) >= self._batch_size:
            await self._flush_batch_operations()
    
    async def _flush_batch_operations(self):
        """バッチ操作をフラッシュ"""
        if not self._batch_operations:
            return
        
        start_time = time.time()
        
        try:
            # 操作タイプ別にグループ化
            grouped_ops = {}
            for op in self._batch_operations:
                op_type = op.get('type', 'unknown')
                if op_type not in grouped_ops:
                    grouped_ops[op_type] = []
                grouped_ops[op_type].append(op)
            
            # 並列実行
            tasks = []
            for op_type, ops in grouped_ops.items():
                if op_type == 'store_conversation':
                    tasks.append(self._batch_store_conversations(ops))
                elif op_type == 'update_embeddings':
                    tasks.append(self._batch_update_embeddings(ops))
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # バッチをクリア
            processed_count = len(self._batch_operations)
            self._batch_operations.clear()
            
            # メトリクス記録
            duration = (time.time() - start_time) * 1000
            self._record_metrics("batch_operations", duration, {
                "operations_count": processed_count,
                "operation_types": list(grouped_ops.keys())
            })
            
            logger.info(f"バッチ操作を完了: {processed_count}件")
            
        except Exception as e:
            logger.error(f"バッチ操作中にエラー: {e}")
            raise
    
    async def _batch_store_conversations(self, operations: List[Dict[str, Any]]):
        """会話保存のバッチ処理"""
        # 実際の実装では、複数の会話を一度にデータベースに保存
        logger.info(f"会話保存バッチ処理: {len(operations)}件")
    
    async def _batch_update_embeddings(self, operations: List[Dict[str, Any]]):
        """埋め込み更新のバッチ処理"""
        # 実際の実装では、複数の埋め込みを一度に計算・更新
        logger.info(f"埋め込み更新バッチ処理: {len(operations)}件")
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """キャッシュの有効性をチェック"""
        if cache_key not in self._cache:
            return False
        
        ttl = self._cache_ttl.get(cache_key)
        if not ttl or datetime.utcnow() > ttl:
            # 期限切れキャッシュを削除
            self._cache.pop(cache_key, None)
            self._cache_ttl.pop(cache_key, None)
            return False
        
        return True
    
    def _record_metrics(self, operation: str, duration_ms: float, metadata: Dict[str, Any] = None):
        """メトリクスを記録"""
        import psutil
        
        metrics = PerformanceMetrics(
            operation=operation,
            duration_ms=duration_ms,
            memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.metrics.append(metrics)
        
        # メトリクス数を制限
        if len(self.metrics) > 1000:
            self.metrics = self.metrics[-500:]  # 最新500件を保持
    
    def get_performance_report(self) -> Dict[str, Any]:
        """パフォーマンスレポートを取得"""
        if not self.metrics:
            return {"message": "メトリクスがありません"}
        
        # 操作別統計
        operation_stats = {}
        for metric in self.metrics:
            op = metric.operation
            if op not in operation_stats:
                operation_stats[op] = {
                    "count": 0,
                    "total_duration": 0,
                    "max_duration": 0,
                    "min_duration": float('inf'),
                    "avg_memory": 0
                }
            
            stats = operation_stats[op]
            stats["count"] += 1
            stats["total_duration"] += metric.duration_ms
            stats["max_duration"] = max(stats["max_duration"], metric.duration_ms)
            stats["min_duration"] = min(stats["min_duration"], metric.duration_ms)
            stats["avg_memory"] += metric.memory_usage_mb
        
        # 平均値を計算
        for stats in operation_stats.values():
            stats["avg_duration"] = stats["total_duration"] / stats["count"]
            stats["avg_memory"] = stats["avg_memory"] / stats["count"]
            if stats["min_duration"] == float('inf'):
                stats["min_duration"] = 0
        
        return {
            "total_operations": len(self.metrics),
            "time_range": {
                "start": min(m.timestamp for m in self.metrics).isoformat(),
                "end": max(m.timestamp for m in self.metrics).isoformat()
            },
            "operation_statistics": operation_stats,
            "cache_statistics": {
                "cache_size": len(self._cache),
                "cache_hit_rate": self._calculate_cache_hit_rate()
            }
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """キャッシュヒット率を計算"""
        # 簡易実装（実際にはより詳細な追跡が必要）
        return 0.75  # プレースホルダー
```

### 3.4 エラーハンドリング強化 (`error_handling/error_manager.py`)

```python
import logging
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """エラー重要度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """エラーカテゴリ"""
    MEMORY_OPERATION = "memory_operation"
    VECTOR_SEARCH = "vector_search"
    SUMMARIZATION = "summarization"
    API_CALL = "api_call"
    DATABASE = "database"
    NETWORK = "network"
    CONFIGURATION = "configuration"

@dataclass
class ErrorRecord:
    """エラー記録"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    traceback: str
    context: Dict[str, Any]
    timestamp: datetime
    resolved: bool = False

class LangChainErrorManager:
    """LangChainエラー管理クラス"""
    
    def __init__(self):
        self.error_records: List[ErrorRecord] = []
        self.error_handlers = {}
        self.recovery_strategies = {}
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """デフォルトエラーハンドラーを設定"""
        
        # メモリ操作エラー
        self.register_error_handler(
            ErrorCategory.MEMORY_OPERATION,
            self._handle_memory_error
        )
        
        # Vector検索エラー
        self.register_error_handler(
            ErrorCategory.VECTOR_SEARCH,
            self._handle_vector_search_error
        )
        
        # 要約エラー
        self.register_error_handler(
            ErrorCategory.SUMMARIZATION,
            self._handle_summarization_error
        )
        
        # API呼び出しエラー
        self.register_error_handler(
            ErrorCategory.API_CALL,
            self._handle_api_error
        )
    
    def register_error_handler(self, category: ErrorCategory, handler):
        """エラーハンドラーを登録"""
        self.error_handlers[category] = handler
    
    async def handle_error(
        self,
        error: Exception,
        category: ErrorCategory,
        context: Dict[str, Any] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> Optional[Any]:
        """
        エラーを処理
        
        Args:
            error: 発生したエラー
            category: エラーカテゴリ
            context: エラーコンテキスト
            severity: エラー重要度
            
        Returns:
            Optional[Any]: 回復処理の結果
        """
        
        # エラー記録を作成
        error_record = ErrorRecord(
            error_id=f"{category.value}_{datetime.utcnow().timestamp()}",
            category=category,
            severity=severity,
            message=str(error),
            traceback=traceback.format_exc(),
            context=context or {},
            timestamp=datetime.utcnow()
        )
        
        self.error_records.append(error_record)
        
        # ログ出力
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }[severity]
        
        logger.log(log_level, f"LangChainエラー [{category.value}]: {error}")
        
        # エラーハンドラーを実行
        handler = self.error_handlers.get(category)
        if handler:
            try:
                result = await handler(error, error_record)
                if result is not None:
                    error_record.resolved = True
                    logger.info(f"エラーが回復されました: {error_record.error_id}")
                return result
            except Exception as handler_error:
                logger.error(f"エラーハンドラー実行中にエラー: {handler_error}")
        
        # 重要度が高い場合は通知
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            await self._send_error_notification(error_record)
        
        return None
    
    async def _handle_memory_error(self, error: Exception, record: ErrorRecord) -> Optional[Any]:
        """メモリ操作エラーの処理"""
        logger.info("メモリ操作エラーの回復を試行中...")
        
        # 回復戦略
        if "connection" in str(error).lower():
            # 接続エラーの場合は再接続を試行
            return await self._retry_with_backoff(record.context.get('operation'))
        elif "timeout" in str(error).lower():
            # タイムアウトの場合は設定を調整
            return await self._adjust_timeout_and_retry(record.context.get('operation'))
        
        return None
    
    async def _handle_vector_search_error(self, error: Exception, record: ErrorRecord) -> Optional[Any]:
        """Vector検索エラーの処理"""
        logger.info("Vector検索エラーの回復を試行中...")
        
        # フォールバック検索を実行
        if "embedding" in str(error).lower():
            return await self._fallback_to_keyword_search(record.context)
        
        return None
    
    async def _handle_summarization_error(self, error: Exception, record: ErrorRecord) -> Optional[Any]:
        """要約エラーの処理"""
        logger.info("要約エラーの回復を試行中...")
        
        # 簡易要約にフォールバック
        if "token" in str(error).lower() or "length" in str(error).lower():
            return await self._create_simple_summary(record.context)
        
        return None
    
    async def _handle_api_error(self, error: Exception, record: ErrorRecord) -> Optional[Any]:
        """API呼び出しエラーの処理"""
        logger.info("API呼び出しエラーの回復を試行中...")
        
        # レート制限エラーの場合は待機後再試行
        if "rate limit" in str(error).lower():
            await asyncio.sleep(60)  # 1分待機
            return await self._retry_api_call(record.context)
        
        return None
    
    async def _retry_with_backoff(self, operation, max_retries: int = 3):
        """指数バックオフで再試行"""
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(2 ** attempt)  # 1, 2, 4秒
                # 実際の操作を再実行（実装依存）
                logger.info(f"再試行 {attempt + 1}/{max_retries}")
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
        return None
    
    async def _adjust_timeout_and_retry(self, operation):
        """タイムアウト調整後再試行"""