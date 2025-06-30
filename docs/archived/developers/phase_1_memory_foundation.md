# Phase 1: メモリ基盤構築 - 詳細設計仕様

## 1. 概要

LangChain統合の第1フェーズとして、メモリ管理の基盤を構築します。
既存のAetherTermアーキテクチャとの統合を重視し、依存性注入パターンを活用します。

## 2. コンポーネント詳細設計

### 2.1 設定管理 (`config.py`)

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path
import os

@dataclass
class LangChainConfig:
    """LangChain統合設定"""
    
    # 基本設定
    enabled: bool = True
    debug: bool = False
    log_level: str = "INFO"
    
    # メモリ設定
    retention_days: int = 30
    max_conversations_per_session: int = 100
    vector_store_type: str = "chroma"  # chroma, faiss, pinecone
    
    # データベース設定
    sql_database_url: Optional[str] = None
    redis_url: Optional[str] = None
    vector_store_path: str = "./data/vector_store"
    
    # 要約設定
    realtime_interval_minutes: int = 5
    max_log_entries_per_summary: int = 1000
    summarization_model: str = "gpt-3.5-turbo"
    summary_max_tokens: int = 500
    
    # 検索設定
    similarity_threshold: float = 0.7
    max_context_entries: int = 5
    embedding_model: str = "text-embedding-ada-002"
    search_timeout_seconds: int = 10
    
    # AIプロバイダー設定
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_provider: str = "openai"
    
    @classmethod
    def from_env(cls) -> 'LangChainConfig':
        """環境変数から設定を読み込み"""
        return cls(
            enabled=os.getenv('LANGCHAIN_ENABLED', 'true').lower() == 'true',
            debug=os.getenv('LANGCHAIN_DEBUG', 'false').lower() == 'true',
            log_level=os.getenv('LANGCHAIN_LOG_LEVEL', 'INFO'),
            
            retention_days=int(os.getenv('LANGCHAIN_RETENTION_DAYS', '30')),
            max_conversations_per_session=int(os.getenv('LANGCHAIN_MAX_CONVERSATIONS', '100')),
            vector_store_type=os.getenv('LANGCHAIN_VECTOR_STORE_TYPE', 'chroma'),
            
            sql_database_url=os.getenv('DATABASE_URL'),
            redis_url=os.getenv('REDIS_URL'),
            vector_store_path=os.getenv('LANGCHAIN_VECTOR_STORE_PATH', './data/vector_store'),
            
            realtime_interval_minutes=int(os.getenv('LANGCHAIN_REALTIME_INTERVAL', '5')),
            max_log_entries_per_summary=int(os.getenv('LANGCHAIN_MAX_LOG_ENTRIES', '1000')),
            summarization_model=os.getenv('LANGCHAIN_SUMMARIZATION_MODEL', 'gpt-3.5-turbo'),
            summary_max_tokens=int(os.getenv('LANGCHAIN_SUMMARY_MAX_TOKENS', '500')),
            
            similarity_threshold=float(os.getenv('LANGCHAIN_SIMILARITY_THRESHOLD', '0.7')),
            max_context_entries=int(os.getenv('LANGCHAIN_MAX_CONTEXT_ENTRIES', '5')),
            embedding_model=os.getenv('LANGCHAIN_EMBEDDING_MODEL', 'text-embedding-ada-002'),
            search_timeout_seconds=int(os.getenv('LANGCHAIN_SEARCH_TIMEOUT', '10')),
            
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
            default_provider=os.getenv('LANGCHAIN_DEFAULT_PROVIDER', 'openai'),
        )
    
    def validate(self) -> None:
        """設定値の検証"""
        if self.enabled:
            if not self.openai_api_key and not self.anthropic_api_key:
                raise ValueError("AIプロバイダーのAPIキーが設定されていません")
            
            if self.retention_days <= 0:
                raise ValueError("retention_daysは正の値である必要があります")
            
            if self.vector_store_type not in ['chroma', 'faiss', 'pinecone']:
                raise ValueError(f"サポートされていないvector_store_type: {self.vector_store_type}")
```

### 2.2 依存性注入設定 (`containers.py`)

```python
from dependency_injector import containers, providers
from .config import LangChainConfig
from .memory.conversation_memory import ConversationMemoryManager
from .memory.session_memory import SessionMemoryManager
from .memory.storage_adapters import (
    VectorStoreAdapter,
    SQLStorageAdapter,
    RedisStorageAdapter
)
from .summarization.log_summarizer import LogSummarizationService
from .retrieval.context_retriever import ContextRetrievalService

class LangChainContainer(containers.DeclarativeContainer):
    """LangChain統合用DIコンテナ"""
    
    # 設定
    config = providers.Singleton(LangChainConfig.from_env)
    
    # ストレージアダプター
    vector_store_adapter = providers.Singleton(
        VectorStoreAdapter,
        config=config.provided.vector_store_type,
        store_path=config.provided.vector_store_path,
        embedding_model=config.provided.embedding_model
    )
    
    sql_storage_adapter = providers.Singleton(
        SQLStorageAdapter,
        database_url=config.provided.sql_database_url
    )
    
    redis_storage_adapter = providers.Singleton(
        RedisStorageAdapter,
        redis_url=config.provided.redis_url
    )
    
    # メモリ管理サービス
    conversation_memory_manager = providers.Singleton(
        ConversationMemoryManager,
        vector_store=vector_store_adapter,
        sql_storage=sql_storage_adapter,
        redis_storage=redis_storage_adapter,
        config=config
    )
    
    session_memory_manager = providers.Singleton(
        SessionMemoryManager,
        conversation_memory=conversation_memory_manager,
        config=config
    )
    
    # 要約サービス
    log_summarization_service = providers.Singleton(
        LogSummarizationService,
        config=config,
        memory_manager=conversation_memory_manager
    )
    
    # 検索サービス
    context_retrieval_service = providers.Singleton(
        ContextRetrievalService,
        vector_store=vector_store_adapter,
        memory_manager=conversation_memory_manager,
        config=config
    )
```

### 2.3 データモデル (`memory/models.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from enum import Enum

class ConversationType(Enum):
    """会話タイプ"""
    USER_INPUT = "user_input"
    AI_RESPONSE = "ai_response"
    COMMAND_EXECUTION = "command_execution"
    SYSTEM_MESSAGE = "system_message"

class MessageRole(Enum):
    """メッセージロール"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class ConversationEntry:
    """会話エントリ"""
    id: UUID = field(default_factory=uuid4)
    session_id: str = ""
    conversation_type: ConversationType = ConversationType.USER_INPUT
    role: MessageRole = MessageRole.USER
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': str(self.id),
            'session_id': self.session_id,
            'conversation_type': self.conversation_type.value,
            'role': self.role.value,
            'content': self.content,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'embedding': self.embedding
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationEntry':
        """辞書から復元"""
        return cls(
            id=UUID(data['id']),
            session_id=data['session_id'],
            conversation_type=ConversationType(data['conversation_type']),
            role=MessageRole(data['role']),
            content=data['content'],
            metadata=data.get('metadata', {}),
            timestamp=datetime.fromisoformat(data['timestamp']),
            embedding=data.get('embedding')
        )

@dataclass
class SessionContext:
    """セッションコンテキスト"""
    session_id: str
    user_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    conversation_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self) -> None:
        """最終アクティビティ時刻を更新"""
        self.last_activity = datetime.utcnow()
        self.conversation_count += 1

@dataclass
class LogSummary:
    """ログ要約"""
    id: UUID = field(default_factory=uuid4)
    session_id: str = ""
    summary_type: str = "realtime"  # realtime, session, daily
    content: str = ""
    log_count: int = 0
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ContextEntry:
    """コンテキストエントリ"""
    content: str
    source: str  # conversation, summary, command
    relevance_score: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 2.4 ストレージアダプター基底クラス (`memory/base.py`)

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .models import ConversationEntry, SessionContext, LogSummary

class MemoryStorageAdapter(ABC):
    """メモリストレージアダプターの抽象基底クラス"""
    
    @abstractmethod
    async def store_conversation(self, entry: ConversationEntry) -> str:
        """会話エントリを保存"""
        pass
    
    @abstractmethod
    async def retrieve_conversations(
        self, 
        session_id: str, 
        limit: int = 10,
        offset: int = 0
    ) -> List[ConversationEntry]:
        """会話履歴を取得"""
        pass
    
    @abstractmethod
    async def search_conversations(
        self, 
        query: str, 
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[ConversationEntry]:
        """会話を検索"""
        pass
    
    @abstractmethod
    async def delete_old_conversations(self, days: int) -> int:
        """古い会話を削除"""
        pass

class SessionStorageAdapter(ABC):
    """セッションストレージアダプターの抽象基底クラス"""
    
    @abstractmethod
    async def store_session_context(self, context: SessionContext) -> None:
        """セッションコンテキストを保存"""
        pass
    
    @abstractmethod
    async def retrieve_session_context(self, session_id: str) -> Optional[SessionContext]:
        """セッションコンテキストを取得"""
        pass
    
    @abstractmethod
    async def update_session_activity(self, session_id: str) -> None:
        """セッションアクティビティを更新"""
        pass

class SummaryStorageAdapter(ABC):
    """要約ストレージアダプターの抽象基底クラス"""
    
    @abstractmethod
    async def store_summary(self, summary: LogSummary) -> str:
        """要約を保存"""
        pass
    
    @abstractmethod
    async def retrieve_summaries(
        self, 
        session_id: str, 
        summary_type: str = None
    ) -> List[LogSummary]:
        """要約を取得"""
        pass
    
    @abstractmethod
    async def search_summaries(
        self, 
        query: str, 
        limit: int = 10
    ) -> List[LogSummary]:
        """要約を検索"""
        pass
```

### 2.5 会話メモリ管理 (`memory/conversation_memory.py`)

```python
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from .base import MemoryStorageAdapter
from .models import ConversationEntry, ConversationType, MessageRole
from .storage_adapters import VectorStoreAdapter, SQLStorageAdapter, RedisStorageAdapter
from ..config import LangChainConfig

logger = logging.getLogger(__name__)

class ConversationMemoryManager:
    """会話メモリ管理クラス"""
    
    def __init__(
        self,
        vector_store: VectorStoreAdapter,
        sql_storage: SQLStorageAdapter,
        redis_storage: RedisStorageAdapter,
        config: LangChainConfig
    ):
        self.vector_store = vector_store
        self.sql_storage = sql_storage
        self.redis_storage = redis_storage
        self.config = config
        self._logger = logger
    
    async def store_conversation(
        self, 
        session_id: str, 
        content: str,
        conversation_type: ConversationType = ConversationType.USER_INPUT,
        role: MessageRole = MessageRole.USER,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        会話エントリを保存
        
        Args:
            session_id: セッションID
            content: 会話内容
            conversation_type: 会話タイプ
            role: メッセージロール
            metadata: メタデータ
            
        Returns:
            str: 保存されたエントリのID
        """
        try:
            entry = ConversationEntry(
                session_id=session_id,
                conversation_type=conversation_type,
                role=role,
                content=content,
                metadata=metadata or {}
            )
            
            # 埋め込みベクトルを生成
            entry.embedding = await self.vector_store.generate_embedding(content)
            
            # 複数のストレージに保存
            tasks = [
                self.vector_store.store_conversation(entry),
                self.sql_storage.store_conversation(entry),
                self.redis_storage.cache_recent_conversation(entry)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # エラーハンドリング
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    storage_names = ['vector_store', 'sql_storage', 'redis_storage']
                    self._logger.error(f"{storage_names[i]}への保存に失敗: {result}")
            
            self._logger.info(f"会話エントリを保存しました: {entry.id}")
            return str(entry.id)
            
        except Exception as e:
            self._logger.error(f"会話保存中にエラーが発生: {e}")
            raise
    
    async def retrieve_conversation_history(
        self, 
        session_id: str, 
        limit: int = 10,
        include_embeddings: bool = False
    ) -> List[ConversationEntry]:
        """
        会話履歴を取得
        
        Args:
            session_id: セッションID
            limit: 取得件数制限
            include_embeddings: 埋め込みベクトルを含めるか
            
        Returns:
            List[ConversationEntry]: 会話履歴
        """
        try:
            # まずRedisキャッシュから取得を試行
            cached_conversations = await self.redis_storage.get_recent_conversations(
                session_id, limit
            )
            
            if cached_conversations and len(cached_conversations) >= limit:
                self._logger.debug(f"キャッシュから会話履歴を取得: {len(cached_conversations)}件")
                return cached_conversations[:limit]
            
            # キャッシュにない場合はSQLから取得
            conversations = await self.sql_storage.retrieve_conversations(
                session_id, limit, offset=0
            )
            
            # 埋め込みが必要な場合はVector Storeから取得
            if include_embeddings:
                for conv in conversations:
                    if not conv.embedding:
                        conv.embedding = await self.vector_store.get_embedding(str(conv.id))
            
            self._logger.info(f"会話履歴を取得しました: {len(conversations)}件")
            return conversations
            
        except Exception as e:
            self._logger.error(f"会話履歴取得中にエラーが発生: {e}")
            raise
    
    async def search_similar_conversations(
        self, 
        query: str, 
        session_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = None
    ) -> List[ConversationEntry]:
        """
        類似会話を検索
        
        Args:
            query: 検索クエリ
            session_id: セッションID（指定時はセッション内検索）
            limit: 取得件数制限
            threshold: 類似度閾値
            
        Returns:
            List[ConversationEntry]: 類似会話リスト
        """
        try:
            threshold = threshold or self.config.similarity_threshold
            
            # Vector Storeで類似性検索
            similar_conversations = await self.vector_store.similarity_search(
                query=query,
                session_id=session_id,
                limit=limit,
                threshold=threshold
            )
            
            self._logger.info(f"類似会話検索結果: {len(similar_conversations)}件")
            return similar_conversations
            
        except Exception as e:
            self._logger.error(f"類似会話検索中にエラーが発生: {e}")
            raise
    
    async def cleanup_old_conversations(self) -> int:
        """
        古い会話データをクリーンアップ
        
        Returns:
            int: 削除された件数
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.config.retention_days)
            
            # 各ストレージから古いデータを削除
            tasks = [
                self.vector_store.delete_old_conversations(self.config.retention_days),
                self.sql_storage.delete_old_conversations(self.config.retention_days),
                self.redis_storage.cleanup_old_cache()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_deleted = 0
            for result in results:
                if isinstance(result, int):
                    total_deleted += result
                elif isinstance(result, Exception):
                    self._logger.error(f"クリーンアップ中にエラー: {result}")
            
            self._logger.info(f"古い会話データを削除しました: {total_deleted}件")
            return total_deleted
            
        except Exception as e:
            self._logger.error(f"クリーンアップ中にエラーが発生: {e}")
            raise
    
    async def get_conversation_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        会話統計情報を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            stats = await self.sql_storage.get_conversation_statistics(session_id)
            return stats
            
        except Exception as e:
            self._logger.error(f"統計情報取得中にエラーが発生: {e}")
            raise
```

## 3. TDDテスト設計

### 3.1 設定管理テスト (`tests/langchain/test_config.py`)

```python
import pytest
import os
from unittest.mock import patch
from src.aetherterm.langchain.config import LangChainConfig

class TestLangChainConfig:
    """LangChain設定テストクラス"""
    
    def test_default_config_values(self):
        """デフォルト設定値のテスト"""
        config = LangChainConfig()
        
        assert config.enabled is True
        assert config.debug is False
        assert config.retention_days == 30
        assert config.vector_store_type == "chroma"
        assert config.similarity_threshold == 0.7
    
    @patch.dict(os.environ, {
        'LANGCHAIN_ENABLED': 'false',
        'LANGCHAIN_DEBUG': 'true',
        'LANGCHAIN_RETENTION_DAYS': '60',
        'OPENAI_API_KEY': 'test-key'
    })
    def test_config_from_env(self):
        """環境変数からの設定読み込みテスト"""
        config = LangChainConfig.from_env()
        
        assert config.enabled is False
        assert config.debug is True
        assert config.retention_days == 60
        assert config.openai_api_key == 'test-key'
    
    def test_config_validation_success(self):
        """設定検証成功テスト"""
        config = LangChainConfig(
            enabled=True,
            openai_api_key='test-key',
            retention_days=30
        )
        
        # 例外が発生しないことを確認
        config.validate()
    
    def test_config_validation_no_api_key(self):
        """APIキー未設定時の検証エラーテスト"""
        config = LangChainConfig(enabled=True)
        
        with pytest.raises(ValueError, match="AIプロバイダーのAPIキーが設定されていません"):
            config.validate()
    
    def test_config_validation_invalid_retention_days(self):
        """不正な保持日数の検証エラーテスト"""
        config = LangChainConfig(
            enabled=True,
            openai_api_key='test-key',
            retention_days=0
        )
        
        with pytest.raises(ValueError, match="retention_daysは正の値である必要があります"):
            config.validate()
```

### 3.2 会話メモリ管理テスト (`tests/langchain/memory/test_conversation_memory.py`)

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from src.aetherterm.langchain.memory.conversation_memory import ConversationMemoryManager
from src.aetherterm.langchain.memory.models import ConversationEntry, ConversationType, MessageRole
from src.aetherterm.langchain.config import LangChainConfig

@pytest.fixture
def mock_storage_adapters():
    """モックストレージアダプターのフィクスチャ"""
    vector_store = AsyncMock()
    sql_storage = AsyncMock()
    redis_storage = AsyncMock()
    
    return vector_store, sql_storage, redis_storage

@pytest.fixture
def config():
    """テスト用設定のフィクスチャ"""
    return LangChainConfig(
        enabled=True,
        openai_api_key='test-key',
        retention_days=30,
        similarity_threshold=0.7
    )

@pytest.fixture
def memory_manager(mock_storage_adapters, config):
    """メモリ管理クラスのフィクスチャ"""
    vector_store, sql_storage, redis_storage = mock_storage_adapters
    return ConversationMemoryManager(vector_store, sql_storage, redis_storage, config)

class TestConversationMemoryManager:
    """会話メモリ管理テストクラス"""
    
    @pytest.mark.asyncio
    async def test_store_conversation_success(self, memory_manager, mock_storage_adapters):
        """会話保存成功テスト"""
        vector_store, sql_storage, redis_storage = mock_storage_adapters
        
        # モックの戻り値を設定
        vector_store.generate_embedding.return_value = [0.1, 0.2, 0.3]
        vector_store.store_conversation.return_value = "vector-id"
        sql_storage.store_conversation.return_value = "sql-id"
        redis_storage.cache_recent_conversation.return_value = None
        
        # テスト実行
        result = await memory_manager.store_conversation(
            session_id="test-session",
            content="テストメッセージ",
            conversation_type=ConversationType.USER_INPUT,
            role=MessageRole.USER
        )
        
        # 検証
        assert result is not None
        vector_store.generate_embedding.assert_called_once_with("テストメッセージ")
        vector_store.store_conversation.assert_called_once()
        sql_storage.store_conversation.assert_called_once()
        redis_storage.cache_recent_conversation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retrieve_conversation_history_from_cache(self, memory_manager, mock_storage_adapters):
        """キャッシュからの会話履歴取得テスト"""
        vector_store, sql_storage, redis_storage = mock_storage_adapters
        
        # モックデータ
        cached_conversations = [
            ConversationEntry(
                session_id="test-session",
                content="キャッシュされたメッセージ",
                conversation_type=ConversationType.USER_INPUT
            )
        ]
        redis_storage.get_recent_conversations.return_value = cached_conversations
        
        # テスト実行
        result = await memory_manager.retrieve_conversation_history("test-session", limit=10)
        
        # 検証
        assert len(result) == 1
        assert result[0].content == "キャッシュされたメッセージ"
        redis_storage.get_recent_conversations.assert_called_once_with("test-session", 10)
        sql_storage.retrieve_conversations.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_search_similar_conversations(self, memory_manager, mock_storage_adapters):
        """類似会話検索テスト"""
        vector_store, sql_storage, redis_storage = mock_storage_adapters
        
        # モックデータ
        similar_conversations = [
            ConversationEntry(
                session_id="test-session",
                content="類似メッセージ",
                conversation_type=ConversationType.USER_INPUT
            )
        ]
        vector_store.similarity_search.return_value = similar_conversations
        
        # テスト実行
        result = await memory_manager.search_similar_conversations(
            query="検索クエリ",
            session_id="test-session",
            limit=5
        )
        
        # 検証
        assert len(result) == 1
        assert result[0].content == "類似メッセージ"
        vector_store.similarity_search.assert_called_once_with(
            query="検索クエリ",
            session_id="test-session",
            limit=5,
            threshold=0.7
        )
    
    @pytest.mark.asyncio
    async def test_cleanup_old_conversations(self, memory_manager, mock_storage_adapters):
        """古い会話クリーンアップテスト"""
        vector_store, sql_storage, redis_storage = mock_storage_adapters
        
        # モックの戻り値を設定
        vector_store.delete_old_conversations.return_value = 10
        sql_storage.delete_old_conversations.return_value = 15
        redis_storage.cleanup_old_cache.return_value = 5
        
        # テスト実行
        result = await memory_manager.cleanup_old_conversations()
        
        # 検証
        assert result == 30  # 10 + 15 + 5
        vector_store.delete_old_conversations.assert_called_once_with(30)
        sql_storage.delete_old_conversations.assert_called_once_with(30)
        redis_storage.cleanup_old_cache.assert_called_once()
```

## 4. 実装チェックリスト

### 4.1 Phase 1 完了条件
- [ ] 設定管理クラスの実装と検証
- [ ] 依存性注入コンテナの設定
- [ ] データモデルの定義
- [ ] ストレージアダプター基底クラスの実装
- [ ] 会話メモリ管理クラスの実装
- [ ] 単体テストの実装（カバレッジ80%以上）
- [ ] 統合テストの実装
- [ ] ドキュメントの整備

### 4.2 品質基準
- **テストカバレッジ**: 80%以上
- **型ヒント**: 全メソッドに型ヒント付与
- **ドキュメント**: 全パブリックメソッドにdocstring
- **エラーハンドリング**: 適切な例外処理とログ出力
- **パフォーマンス**: メモリ保存 < 100ms、検索 < 200ms

この詳細設計に基づいて、