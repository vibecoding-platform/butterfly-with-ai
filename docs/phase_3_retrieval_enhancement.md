# Phase 3: 検索・強化機能 - 詳細設計仕様

## 1. 概要

LangChain統合の第3フェーズとして、コンテキスト検索と問い合わせ強化機能を実装します。
Vector Store、セマンティック検索、RAG（Retrieval-Augmented Generation）パターンを活用し、
過去の会話履歴と要約を基にした高度な問い合わせ支援を実現します。

## 2. 検索・強化アーキテクチャ

### 2.1 RAGパイプライン構造
```
┌─────────────────────────────────────────────────────────────┐
│                RAG (Retrieval-Augmented Generation)         │
├─────────────────────────────────────────────────────────────┤
│  Query Processing                                           │
│  ├── Query Analysis & Intent Detection                     │
│  ├── Query Expansion & Reformulation                       │
│  └── Context Extraction                                    │
├─────────────────────────────────────────────────────────────┤
│  Multi-Source Retrieval                                    │
│  ├── Vector Store Search (Semantic)                        │
│  ├── SQL Database Search (Structured)                      │
│  ├── Summary Search (Hierarchical)                         │
│  └── Command History Search (Pattern)                      │
├─────────────────────────────────────────────────────────────┤
│  Context Fusion & Ranking                                  │
│  ├── Relevance Scoring                                     │
│  ├── Temporal Weighting                                    │
│  ├── Source Diversity                                      │
│  └── Context Deduplication                                 │
├─────────────────────────────────────────────────────────────┤
│  Response Generation                                        │
│  ├── Context-Aware Prompting                              │
│  ├── Multi-Turn Conversation                              │
│  └── Follow-up Suggestions                                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 検索戦略
```python
# 複数検索戦略の組み合わせ
search_strategies = {
    "semantic": VectorStoreRetriever,      # 意味的類似性
    "keyword": BM25Retriever,              # キーワードマッチング  
    "temporal": TimeBasedRetriever,        # 時系列検索
    "pattern": CommandPatternRetriever,    # コマンドパターン
    "hybrid": EnsembleRetriever           # ハイブリッド検索
}
```

## 3. コンポーネント詳細設計

### 3.1 クエリ分析・拡張 (`retrieval/query_analyzer.py`)

```python
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms.base import BaseLLM

logger = logging.getLogger(__name__)

class QueryIntent(Enum):
    """クエリ意図"""
    COMMAND_HELP = "command_help"           # コマンドの使い方
    ERROR_RESOLUTION = "error_resolution"   # エラー解決
    WORKFLOW_GUIDANCE = "workflow_guidance" # ワークフロー案内
    INFORMATION_LOOKUP = "information_lookup" # 情報検索
    COMPARISON = "comparison"               # 比較・選択
    TROUBLESHOOTING = "troubleshooting"     # トラブルシューティング

@dataclass
class QueryAnalysis:
    """クエリ分析結果"""
    original_query: str
    intent: QueryIntent
    entities: List[str]                    # 抽出されたエンティティ
    keywords: List[str]                    # キーワード
    expanded_queries: List[str]            # 拡張クエリ
    context_requirements: Dict[str, Any]   # コンテキスト要件
    confidence: float                      # 分析信頼度

class QueryAnalyzer:
    """クエリ分析・拡張クラス"""
    
    def __init__(self, llm: BaseLLM):
        self.llm = llm
        self._setup_patterns()
        self._setup_chains()
    
    def _setup_patterns(self) -> None:
        """パターンマッチング用の正規表現を設定"""
        self.command_patterns = [
            r'\b(how to|howto)\s+(\w+)',
            r'\b(\w+)\s+(command|cmd)',
            r'\b(use|using)\s+(\w+)',
            r'\b(\w+)\s+(usage|example)'
        ]
        
        self.error_patterns = [
            r'\b(error|failed|failure)\b',
            r'\b(not working|doesn\'t work)\b',
            r'\b(permission denied|access denied)\b',
            r'\b(command not found|no such file)\b'
        ]
        
        self.entity_patterns = {
            'commands': r'\b(ls|cd|grep|find|awk|sed|git|docker|npm|pip|sudo)\b',
            'files': r'\b[\w\-\.]+\.(py|js|json|txt|log|conf|yml|yaml)\b',
            'paths': r'\b(/[\w\-\./]+|~/[\w\-\./]*|\./[\w\-\./]+)\b',
            'options': r'\b(-{1,2}[\w\-]+)\b'
        }
    
    def _setup_chains(self) -> None:
        """LangChainチェーンを設定"""
        
        # 意図分析チェーン
        intent_prompt = PromptTemplate(
            template="""以下のクエリの意図を分析してください：

クエリ: {query}

以下の意図カテゴリから最も適切なものを選択してください：
- command_help: コマンドの使い方を知りたい
- error_resolution: エラーを解決したい
- workflow_guidance: 作業手順を知りたい
- information_lookup: 情報を検索したい
- comparison: 選択肢を比較したい
- troubleshooting: 問題を診断したい

回答形式:
{{
    "intent": "選択した意図",
    "confidence": 0.0-1.0の信頼度,
    "reasoning": "判断理由"
}}""",
            input_variables=["query"]
        )
        
        self.intent_chain = LLMChain(
            llm=self.llm,
            prompt=intent_prompt,
            verbose=False
        )
        
        # クエリ拡張チェーン
        expansion_prompt = PromptTemplate(
            template="""以下のクエリを、より効果的な検索のために拡張してください：

元のクエリ: {query}
意図: {intent}
抽出されたエンティティ: {entities}

以下の観点でクエリを拡張してください：
1. 同義語・関連語の追加
2. より具体的な表現
3. 異なる表現方法

拡張クエリを3-5個生成してください（JSON配列形式）：
["拡張クエリ1", "拡張クエリ2", "拡張クエリ3"]""",
            input_variables=["query", "intent", "entities"]
        )
        
        self.expansion_chain = LLMChain(
            llm=self.llm,
            prompt=expansion_prompt,
            verbose=False
        )
    
    async def analyze_query(self, query: str) -> QueryAnalysis:
        """
        クエリを分析し、拡張する
        
        Args:
            query: 入力クエリ
            
        Returns:
            QueryAnalysis: 分析結果
        """
        try:
            # エンティティ抽出
            entities = self._extract_entities(query)
            
            # キーワード抽出
            keywords = self._extract_keywords(query)
            
            # 意図分析
            intent_result = await self.intent_chain.arun(query=query)
            intent_data = self._parse_intent_result(intent_result)
            
            # クエリ拡張
            expanded_queries = await self._expand_query(
                query, intent_data["intent"], entities
            )
            
            # コンテキスト要件を決定
            context_requirements = self._determine_context_requirements(
                intent_data["intent"], entities
            )
            
            return QueryAnalysis(
                original_query=query,
                intent=QueryIntent(intent_data["intent"]),
                entities=entities,
                keywords=keywords,
                expanded_queries=expanded_queries,
                context_requirements=context_requirements,
                confidence=intent_data["confidence"]
            )
            
        except Exception as e:
            logger.error(f"クエリ分析中にエラー: {e}")
            # フォールバック分析
            return self._fallback_analysis(query)
    
    def _extract_entities(self, query: str) -> List[str]:
        """エンティティを抽出"""
        entities = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities.extend(matches)
        
        return list(set(entities))  # 重複除去
    
    def _extract_keywords(self, query: str) -> List[str]:
        """キーワードを抽出"""
        # 簡単なキーワード抽出（実際にはより高度な手法を使用）
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'how', 'what', 'when', 'where', 'why', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can'}
        
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords
    
    async def _expand_query(self, query: str, intent: str, entities: List[str]) -> List[str]:
        """クエリを拡張"""
        try:
            expansion_result = await self.expansion_chain.arun(
                query=query,
                intent=intent,
                entities=", ".join(entities)
            )
            
            # JSON解析
            import json
            expanded_queries = json.loads(expansion_result)
            return expanded_queries
            
        except Exception as e:
            logger.error(f"クエリ拡張中にエラー: {e}")
            # フォールバック拡張
            return [query, f"how to {query}", f"{query} example"]
    
    def _parse_intent_result(self, result: str) -> Dict[str, Any]:
        """意図分析結果をパース"""
        try:
            import json
            return json.loads(result)
        except:
            # フォールバック
            return {
                "intent": "information_lookup",
                "confidence": 0.5,
                "reasoning": "パース失敗によるフォールバック"
            }
    
    def _determine_context_requirements(self, intent: str, entities: List[str]) -> Dict[str, Any]:
        """コンテキスト要件を決定"""
        requirements = {
            "max_results": 5,
            "time_range_days": 30,
            "include_summaries": True,
            "include_commands": True,
            "min_relevance_score": 0.7
        }
        
        # 意図に基づく調整
        if intent == "command_help":
            requirements.update({
                "max_results": 10,
                "include_commands": True,
                "focus_on": "command_examples"
            })
        elif intent == "error_resolution":
            requirements.update({
                "max_results": 8,
                "include_errors": True,
                "focus_on": "error_solutions"
            })
        elif intent == "workflow_guidance":
            requirements.update({
                "max_results": 15,
                "include_summaries": True,
                "focus_on": "workflows"
            })
        
        return requirements
    
    def _fallback_analysis(self, query: str) -> QueryAnalysis:
        """フォールバック分析"""
        return QueryAnalysis(
            original_query=query,
            intent=QueryIntent.INFORMATION_LOOKUP,
            entities=self._extract_entities(query),
            keywords=self._extract_keywords(query),
            expanded_queries=[query],
            context_requirements={"max_results": 5},
            confidence=0.3
        )
```

### 3.2 コンテキスト検索 (`retrieval/context_retriever.py`)

```python
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from langchain.vectorstores.base import VectorStore
from langchain.schema import Document
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain.retrievers.multi_vector import MultiVectorRetriever

from .query_analyzer import QueryAnalyzer, QueryAnalysis
from ..memory.models import ConversationEntry, LogSummary, ContextEntry
from ..config import LangChainConfig

logger = logging.getLogger(__name__)

@dataclass
class RetrievalResult:
    """検索結果"""
    contexts: List[ContextEntry]
    total_found: int
    search_time_ms: float
    sources_used: List[str]
    metadata: Dict[str, Any]

class ContextRetrievalService:
    """コンテキスト検索サービス"""
    
    def __init__(
        self,
        vector_store: VectorStore,
        memory_manager,
        config: LangChainConfig,
        query_analyzer: QueryAnalyzer
    ):
        self.vector_store = vector_store
        self.memory_manager = memory_manager
        self.config = config
        self.query_analyzer = query_analyzer
        
        # 検索器の初期化
        self._setup_retrievers()
    
    def _setup_retrievers(self) -> None:
        """各種検索器を設定"""
        
        # Vector Store検索器
        self.vector_retriever = self.vector_store.as_retriever(
            search_kwargs={
                "k": self.config.max_context_entries,
                "score_threshold": self.config.similarity_threshold
            }
        )
        
        # BM25検索器（キーワードベース）
        # 実際の実装では、事前にドキュメントを準備する必要がある
        self.bm25_retriever = None  # 後で初期化
        
        # アンサンブル検索器
        self.ensemble_retriever = None  # 後で初期化
    
    async def retrieve_relevant_context(
        self,
        query: str,
        session_id: Optional[str] = None,
        max_results: Optional[int] = None
    ) -> RetrievalResult:
        """
        関連コンテキストを検索
        
        Args:
            query: 検索クエリ
            session_id: セッションID（指定時はセッション内検索も実行）
            max_results: 最大結果数
            
        Returns:
            RetrievalResult: 検索結果
        """
        start_time = datetime.utcnow()
        
        try:
            # クエリ分析
            query_analysis = await self.query_analyzer.analyze_query(query)
            
            # 検索戦略を決定
            search_strategies = self._determine_search_strategies(query_analysis)
            
            # 並列検索実行
            search_tasks = []
            for strategy_name, strategy_config in search_strategies.items():
                task = self._execute_search_strategy(
                    strategy_name, strategy_config, query_analysis, session_id
                )
                search_tasks.append(task)
            
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # 結果を統合・ランキング
            contexts = await self._merge_and_rank_results(
                search_results, query_analysis, max_results
            )
            
            # 検索時間を計算
            search_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return RetrievalResult(
                contexts=contexts,
                total_found=len(contexts),
                search_time_ms=search_time,
                sources_used=list(search_strategies.keys()),
                metadata={
                    "query_analysis": query_analysis.__dict__,
                    "search_strategies": search_strategies
                }
            )
            
        except Exception as e:
            logger.error(f"コンテキスト検索中にエラー: {e}")
            raise
    
    def _determine_search_strategies(self, query_analysis: QueryAnalysis) -> Dict[str, Dict[str, Any]]:
        """検索戦略を決定"""
        strategies = {}
        
        # 意図に基づく戦略選択
        if query_analysis.intent.value in ["command_help", "error_resolution"]:
            strategies["semantic"] = {
                "weight": 0.6,
                "focus": "commands_and_errors"
            }
            strategies["keyword"] = {
                "weight": 0.4,
                "focus": "exact_matches"
            }
        elif query_analysis.intent.value == "workflow_guidance":
            strategies["semantic"] = {
                "weight": 0.5,
                "focus": "workflows"
            }
            strategies["temporal"] = {
                "weight": 0.3,
                "focus": "recent_sessions"
            }
            strategies["summary"] = {
                "weight": 0.2,
                "focus": "session_summaries"
            }
        else:
            # デフォルト戦略
            strategies["semantic"] = {"weight": 0.7}
            strategies["keyword"] = {"weight": 0.3}
        
        return strategies
    
    async def _execute_search_strategy(
        self,
        strategy_name: str,
        strategy_config: Dict[str, Any],
        query_analysis: QueryAnalysis,
        session_id: Optional[str]
    ) -> List[ContextEntry]:
        """検索戦略を実行"""
        
        try:
            if strategy_name == "semantic":
                return await self._semantic_search(query_analysis, session_id)
            elif strategy_name == "keyword":
                return await self._keyword_search(query_analysis, session_id)
            elif strategy_name == "temporal":
                return await self._temporal_search(query_analysis, session_id)
            elif strategy_name == "summary":
                return await self._summary_search(query_analysis, session_id)
            else:
                logger.warning(f"未知の検索戦略: {strategy_name}")
                return []
                
        except Exception as e:
            logger.error(f"検索戦略 {strategy_name} でエラー: {e}")
            return []
    
    async def _semantic_search(
        self, 
        query_analysis: QueryAnalysis, 
        session_id: Optional[str]
    ) -> List[ContextEntry]:
        """セマンティック検索"""
        
        contexts = []
        
        # 元のクエリで検索
        docs = await self.vector_retriever.aget_relevant_documents(
            query_analysis.original_query
        )
        
        for doc in docs:
            context = ContextEntry(
                content=doc.page_content,
                source="conversation",
                relevance_score=doc.metadata.get("score", 0.8),
                timestamp=datetime.fromisoformat(doc.metadata.get("timestamp", datetime.utcnow().isoformat())),
                metadata=doc.metadata
            )
            contexts.append(context)
        
        # 拡張クエリでも検索
        for expanded_query in query_analysis.expanded_queries[:2]:  # 上位2つ
            try:
                expanded_docs = await self.vector_retriever.aget_relevant_documents(
                    expanded_query
                )
                
                for doc in expanded_docs:
                    # 重複チェック
                    if not any(ctx.content == doc.page_content for ctx in contexts):
                        context = ContextEntry(
                            content=doc.page_content,
                            source="conversation_expanded",
                            relevance_score=doc.metadata.get("score", 0.7),
                            timestamp=datetime.fromisoformat(doc.metadata.get("timestamp", datetime.utcnow().isoformat())),
                            metadata=doc.metadata
                        )
                        contexts.append(context)
                        
            except Exception as e:
                logger.error(f"拡張クエリ検索でエラー: {e}")
        
        return contexts
    
    async def _keyword_search(
        self, 
        query_analysis: QueryAnalysis, 
        session_id: Optional[str]
    ) -> List[ContextEntry]:
        """キーワード検索"""
        
        contexts = []
        
        # SQLベースのキーワード検索
        keyword_results = await self.memory_manager.search_by_keywords(
            keywords=query_analysis.keywords,
            session_id=session_id,
            limit=self.config.max_context_entries
        )
        
        for result in keyword_results:
            context = ContextEntry(
                content=result.content,
                source="keyword_search",
                relevance_score=0.6,  # キーワード検索は固定スコア
                timestamp=result.timestamp,
                metadata=result.metadata
            )
            contexts.append(context)
        
        return contexts
    
    async def _temporal_search(
        self, 
        query_analysis: QueryAnalysis, 
        session_id: Optional[str]
    ) -> List[ContextEntry]:
        """時系列検索"""
        
        contexts = []
        
        # 最近の会話履歴を取得
        recent_conversations = await self.memory_manager.get_recent_conversations(
            session_id=session_id,
            hours=24,  # 過去24時間
            limit=self.config.max_context_entries
        )
        
        for conv in recent_conversations:
            # クエリとの関連性を簡易評価
            relevance = self._calculate_simple_relevance(
                query_analysis.original_query, conv.content
            )
            
            if relevance > 0.3:  # 閾値以上の場合のみ追加
                context = ContextEntry(
                    content=conv.content,
                    source="recent_conversation",
                    relevance_score=relevance,
                    timestamp=conv.timestamp,
                    metadata=conv.metadata
                )
                contexts.append(context)
        
        return contexts
    
    async def _summary_search(
        self, 
        query_analysis: QueryAnalysis, 
        session_id: Optional[str]
    ) -> List[ContextEntry]:
        """要約検索"""
        
        contexts = []
        
        # セッション要約を検索
        summaries = await self.memory_manager.search_summaries(
            query=query_analysis.original_query,
            session_id=session_id,
            summary_types=["session", "daily"],
            limit=5
        )
        
        for summary in summaries:
            context = ContextEntry(
                content=summary.content,
                source=f"summary_{summary.summary_type}",
                relevance_score=0.7,
                timestamp=summary.created_at,
                metadata=summary.metadata
            )
            contexts.append(context)
        
        return contexts
    
    async def _merge_and_rank_results(
        self,
        search_results: List[List[ContextEntry]],
        query_analysis: QueryAnalysis,
        max_results: Optional[int]
    ) -> List[ContextEntry]:
        """検索結果を統合・ランキング"""
        
        all_contexts = []
        
        # 結果を統合
        for result in search_results:
            if isinstance(result, list):
                all_contexts.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"検索結果にエラー: {result}")
        
        # 重複除去
        unique_contexts = self._deduplicate_contexts(all_contexts)
        
        # スコアリング・ランキング
        ranked_contexts = self._rank_contexts(unique_contexts, query_analysis)
        
        # 結果数制限
        max_results = max_results or self.config.max_context_entries
        return ranked_contexts[:max_results]
    
    def _deduplicate_contexts(self, contexts: List[ContextEntry]) -> List[ContextEntry]:
        """コンテキストの重複除去"""
        seen_content = set()
        unique_contexts = []
        
        for context in contexts:
            # 内容の最初の100文字で重複判定
            content_key = context.content[:100]
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_contexts.append(context)
        
        return unique_contexts
    
    def _rank_contexts(
        self, 
        contexts: List[ContextEntry], 
        query_analysis: QueryAnalysis
    ) -> List[ContextEntry]:
        """コンテキストをランキング"""
        
        for context in contexts:
            # 複合スコアを計算
            relevance_score = context.relevance_score
            
            # 時間的重み（新しいほど高スコア）
            time_weight = self._calculate_time_weight(context.timestamp)
            
            # ソース重み
            source_weight = self._calculate_source_weight(context.source, query_analysis.intent.value)
            
            # 最終スコア
            context.relevance_score = (
                relevance_score * 0.6 +
                time_weight * 0.2 +
                source_weight * 0.2
            )
        
        # スコア順でソート
        return sorted(contexts, key=lambda x: x.relevance_score, reverse=True)
    
    def _calculate_time_weight(self, timestamp: datetime) -> float:
        """時間重みを計算"""
        now = datetime.utcnow()
        time_diff = now - timestamp
        
        # 24時間以内は1.0、それ以降は指数的に減衰
        if time_diff.total_seconds() < 86400:  # 24時間
            return 1.0
        else:
            days = time_diff.days
            return max(0.1, 0.9 ** days)
    
    def _calculate_source_weight(self, source: str, intent: str) -> float:
        """ソース重みを計算"""
        source_weights = {
            "conversation": 0.8,
            "conversation_expanded": 0.7,
            "keyword_search": 0.6,
            "recent_conversation": 0.9,
            "summary_session": 0.7,
            "summary_daily": 0.5
        }
        
        # 意図に基づく調整
        if intent == "command_help" and "conversation" in source:
            return source_weights.get(source, 0.5) * 1.2
        elif intent == "workflow_guidance" and "summary" in source:
            return source_weights.get(source, 0.5) * 1.3
        
        return source_weights.get(source, 0.5)
    
    def _calculate_simple_relevance(self, query: str, content: str) -> float:
        """簡易関連性計算"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        intersection = query_words.intersection(content_words)
        return len(intersection) / len(query_words)
```

### 3.3 問い合わせ強化 (`retrieval/query_enhancer.py`)

```python
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.llms.base import BaseLLM

from .context_retriever import ContextRetrievalService, RetrievalResult
from .query_analyzer import QueryAnalyzer, QueryAnalysis
from ..memory.models import ContextEntry

logger = logging.getLogger(__name__)

@dataclass
class EnhancedQuery:
    """強化されたクエリ"""
    original_query: str
    enhanced_prompt: str
    context_summary: str
    relevant_contexts: List[ContextEntry]
    follow_up_suggestions: List[str]
    confidence: float

class QueryEnhancementService:
    """問い合わせ強化サービス"""
    
    def __init__(
        self,
        llm: BaseLLM,
        context_retriever: ContextRetrievalService,
        query_analyzer: QueryAnalyzer
    ):
        self.llm = llm
        self.context_retriever = context_retriever
        self.query_analyzer = query_analyzer
        
        self._setup_chains()
    
    def _setup_chains(self) -> None:
        """LangChainチェーンを設定"""
        
        # コンテキスト統合プロンプト
        self.context_integration_prompt = ChatPromptTemplate.from_messages([
            ("system", """あなたはターミナル操作の専門家です。
ユーザーの質問に対して、過去の会話履歴や要約を参考にして、
より具体的で有用な回答を提供してください。

コンテキスト情報を活用して：
1. 具体的な例やコマンドを提示
2. 過去の類似ケースを参照
3. 段階的