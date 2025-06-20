# パターン分析・ベクトル最適化戦略 - 詳細設計仕様

## 1. 概要

ベクトル化前のパターン分析による効率化と、ベクトルデータベース容量最適化を実現する
階層化アプローチを設計します。これにより、コスト効率と検索精度の両立を図ります。

## 2. 階層化アーキテクチャ

### 2.1 3層パターン分析アーキテクチャ
```
┌─────────────────────────────────────────────────────────────┐
│                パターン分析・最適化システム                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: 高速パターン分析 (Pre-Vector)                    │
│  ├── 正規表現パターンマッチング                             │
│  ├── コマンド頻度分析                                       │
│  ├── エラーパターン分類                                     │
│  └── 重複検出・統合                                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 選択的ベクトル化 (Smart Vectorization)           │
│  ├── 重要度スコアリング                                     │
│  ├── 新規性判定                                             │
│  ├── 一時ベクトル保存                                       │
│  └── 動的容量管理                                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 永続化・圧縮 (Persistent Optimization)           │
│  ├── パターン統合・圧縮                                     │
│  ├── 古いデータのアーカイブ                                 │
│  ├── インデックス最適化                                     │
│  └── 容量監視・自動クリーンアップ                           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 データフロー最適化
```
Raw Data → Pattern Analysis → Importance Scoring → Selective Vectorization
    ↓              ↓                ↓                      ↓
Metadata    Fast Search Cache   Priority Queue      Vector Store
    ↓              ↓                ↓                      ↓
Archive ←── Pattern Compression ←── Batch Processing ←── Optimization
```

## 3. Layer 1: 高速パターン分析

### 3.1 パターン分析エンジン (`pattern_analysis/pattern_engine.py`)

```python
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from enum import Enum

logger = logging.getLogger(__name__)

class PatternType(Enum):
    """パターンタイプ"""
    COMMAND = "command"
    ERROR = "error"
    FILE_OPERATION = "file_operation"
    NETWORK = "network"
    SYSTEM = "system"
    USER_WORKFLOW = "user_workflow"

@dataclass
class PatternMatch:
    """パターンマッチ結果"""
    pattern_type: PatternType
    pattern_name: str
    confidence: float
    extracted_data: Dict[str, Any]
    frequency: int
    last_seen: datetime

@dataclass
class ContentAnalysis:
    """コンテンツ分析結果"""
    content: str
    patterns: List[PatternMatch]
    importance_score: float
    novelty_score: float
    should_vectorize: bool
    metadata: Dict[str, Any]

class PatternAnalysisEngine:
    """パターン分析エンジン"""
    
    def __init__(self):
        self.pattern_cache = {}
        self.frequency_tracker = defaultdict(int)
        self.pattern_history = defaultdict(list)
        self._setup_patterns()
    
    def _setup_patterns(self) -> None:
        """パターン定義を設定"""
        
        # コマンドパターン
        self.command_patterns = {
            'git_operations': [
                r'git\s+(add|commit|push|pull|clone|checkout|branch|merge|status)',
                r'git\s+\w+\s+[\w\-\.\/]+',
            ],
            'file_operations': [
                r'(ls|dir|find|locate)\s+[\w\-\.\/\*]*',
                r'(cp|mv|rm|mkdir|rmdir|chmod|chown)\s+[\w\-\.\/\s]+',
                r'(cat|less|more|head|tail|grep|awk|sed)\s+[\w\-\.\/\s]+',
            ],
            'system_operations': [
                r'(ps|top|htop|kill|killall)\s*[\w\-\s]*',
                r'(systemctl|service)\s+(start|stop|restart|status|enable|disable)\s+\w+',
                r'(sudo|su)\s+.*',
            ],
            'network_operations': [
                r'(ping|curl|wget|ssh|scp|rsync)\s+[\w\-\.\/\@\:]+',
                r'(netstat|ss|lsof|nmap)\s*[\w\-\s]*',
            ],
            'package_management': [
                r'(apt|yum|dnf|pip|npm|yarn)\s+(install|remove|update|upgrade)\s+[\w\-\s]+',
                r'(docker|podman)\s+(run|build|pull|push|ps|exec)\s*[\w\-\s]*',
            ]
        }
        
        # エラーパターン
        self.error_patterns = {
            'permission_errors': [
                r'permission denied',
                r'access denied',
                r'operation not permitted',
            ],
            'file_not_found': [
                r'no such file or directory',
                r'file not found',
                r'cannot access',
            ],
            'command_errors': [
                r'command not found',
                r'bad command or file name',
                r'is not recognized as an internal or external command',
            ],
            'network_errors': [
                r'connection refused',
                r'network unreachable',
                r'timeout',
                r'host not found',
            ],
            'syntax_errors': [
                r'syntax error',
                r'invalid syntax',
                r'unexpected token',
            ]
        }
        
        # ワークフローパターン
        self.workflow_patterns = {
            'development_workflow': [
                r'(git\s+\w+.*\n.*npm\s+(install|run|build))',
                r'(mkdir.*\n.*cd.*\n.*git\s+init)',
            ],
            'deployment_workflow': [
                r'(docker\s+build.*\n.*docker\s+run)',
                r'(git\s+pull.*\n.*systemctl\s+restart)',
            ],
            'troubleshooting_workflow': [
                r'(ps\s+aux.*\n.*kill)',
                r'(tail.*log.*\n.*grep)',
            ]
        }
    
    async def analyze_content(self, content: str, metadata: Dict[str, Any] = None) -> ContentAnalysis:
        """
        コンテンツを分析してパターンを抽出
        
        Args:
            content: 分析対象コンテンツ
            metadata: メタデータ
            
        Returns:
            ContentAnalysis: 分析結果
        """
        try:
            # パターンマッチング実行
            patterns = await self._extract_patterns(content)
            
            # 重要度スコア計算
            importance_score = self._calculate_importance_score(content, patterns, metadata)
            
            # 新規性スコア計算
            novelty_score = self._calculate_novelty_score(content, patterns)
            
            # ベクトル化判定
            should_vectorize = self._should_vectorize(importance_score, novelty_score, patterns)
            
            # 頻度情報を更新
            self._update_frequency_tracking(patterns)
            
            return ContentAnalysis(
                content=content,
                patterns=patterns,
                importance_score=importance_score,
                novelty_score=novelty_score,
                should_vectorize=should_vectorize,
                metadata={
                    **(metadata or {}),
                    'analysis_timestamp': datetime.utcnow().isoformat(),
                    'pattern_count': len(patterns),
                    'total_confidence': sum(p.confidence for p in patterns)
                }
            )
            
        except Exception as e:
            logger.error(f"パターン分析中にエラー: {e}")
            # フォールバック分析
            return self._fallback_analysis(content, metadata)
    
    async def _extract_patterns(self, content: str) -> List[PatternMatch]:
        """パターンを抽出"""
        patterns = []
        content_lower = content.lower()
        
        # コマンドパターンの抽出
        for category, pattern_list in self.command_patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, content_lower, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    patterns.append(PatternMatch(
                        pattern_type=PatternType.COMMAND,
                        pattern_name=f"{category}_{pattern[:20]}",
                        confidence=0.9,
                        extracted_data={
                            'match': match.group(),
                            'start': match.start(),
                            'end': match.end(),
                            'category': category
                        },
                        frequency=self.frequency_tracker[f"{category}_{match.group()}"],
                        last_seen=datetime.utcnow()
                    ))
        
        # エラーパターンの抽出
        for category, pattern_list in self.error_patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    patterns.append(PatternMatch(
                        pattern_type=PatternType.ERROR,
                        pattern_name=f"error_{category}",
                        confidence=0.95,
                        extracted_data={
                            'error_category': category,
                            'pattern': pattern
                        },
                        frequency=self.frequency_tracker[f"error_{category}"],
                        last_seen=datetime.utcnow()
                    ))
        
        # ワークフローパターンの抽出
        for workflow_name, pattern_list in self.workflow_patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                    patterns.append(PatternMatch(
                        pattern_type=PatternType.USER_WORKFLOW,
                        pattern_name=workflow_name,
                        confidence=0.8,
                        extracted_data={
                            'workflow_type': workflow_name,
                            'pattern': pattern
                        },
                        frequency=self.frequency_tracker[workflow_name],
                        last_seen=datetime.utcnow()
                    ))
        
        return patterns
    
    def _calculate_importance_score(
        self, 
        content: str, 
        patterns: List[PatternMatch], 
        metadata: Dict[str, Any] = None
    ) -> float:
        """重要度スコアを計算"""
        
        base_score = 0.5
        
        # パターンベースのスコア調整
        for pattern in patterns:
            if pattern.pattern_type == PatternType.ERROR:
                base_score += 0.3  # エラーは重要
            elif pattern.pattern_type == PatternType.USER_WORKFLOW:
                base_score += 0.2  # ワークフローも重要
            elif pattern.pattern_type == PatternType.COMMAND:
                base_score += 0.1  # コマンドは中程度
        
        # 頻度による調整（低頻度ほど重要）
        avg_frequency = sum(p.frequency for p in patterns) / max(len(patterns), 1)
        if avg_frequency < 5:
            base_score += 0.2  # 珍しいパターンは重要
        elif avg_frequency > 50:
            base_score -= 0.1  # 頻繁なパターンは重要度低下
        
        # コンテンツ長による調整
        if len(content) > 1000:
            base_score += 0.1  # 長いコンテンツは重要
        elif len(content) < 50:
            base_score -= 0.1  # 短すぎるコンテンツは重要度低下
        
        # メタデータによる調整
        if metadata:
            if metadata.get('session_duration_minutes', 0) > 60:
                base_score += 0.1  # 長時間セッションは重要
            if metadata.get('error_count', 0) > 0:
                base_score += 0.2  # エラーを含むセッションは重要
        
        return min(1.0, max(0.0, base_score))
    
    def _calculate_novelty_score(self, content: str, patterns: List[PatternMatch]) -> float:
        """新規性スコアを計算"""
        
        if not patterns:
            return 0.8  # パターンが見つからない場合は新規性が高い
        
        # パターンの新規性を評価
        novelty_scores = []
        for pattern in patterns:
            pattern_key = f"{pattern.pattern_type.value}_{pattern.pattern_name}"
            
            # 過去の出現履歴をチェック
            history = self.pattern_history[pattern_key]
            if not history:
                novelty_scores.append(1.0)  # 初回出現
            else:
                # 最後の出現からの時間を考慮
                last_occurrence = max(history)
                time_since_last = datetime.utcnow() - last_occurrence
                
                if time_since_last.days > 7:
                    novelty_scores.append(0.8)  # 1週間以上前
                elif time_since_last.days > 1:
                    novelty_scores.append(0.6)  # 1日以上前
                elif time_since_last.hours > 1:
                    novelty_scores.append(0.4)  # 1時間以上前
                else:
                    novelty_scores.append(0.2)  # 最近出現
        
        return sum(novelty_scores) / len(novelty_scores) if novelty_scores else 0.5
    
    def _should_vectorize(
        self, 
        importance_score: float, 
        novelty_score: float, 
        patterns: List[PatternMatch]
    ) -> bool:
        """ベクトル化すべきかを判定"""
        
        # 重要度と新規性の重み付き平均
        combined_score = importance_score * 0.6 + novelty_score * 0.4
        
        # 基本的な閾値判定
        if combined_score >= 0.7:
            return True
        
        # エラーパターンは優先的にベクトル化
        error_patterns = [p for p in patterns if p.pattern_type == PatternType.ERROR]
        if error_patterns:
            return True
        
        # ワークフローパターンも優先的にベクトル化
        workflow_patterns = [p for p in patterns if p.pattern_type == PatternType.USER_WORKFLOW]
        if workflow_patterns and combined_score >= 0.5:
            return True
        
        return False
    
    def _update_frequency_tracking(self, patterns: List[PatternMatch]) -> None:
        """頻度追跡情報を更新"""
        for pattern in patterns:
            pattern_key = f"{pattern.pattern_type.value}_{pattern.pattern_name}"
            self.frequency_tracker[pattern_key] += 1
            self.pattern_history[pattern_key].append(datetime.utcnow())
            
            # 履歴サイズを制限（最新100件まで）
            if len(self.pattern_history[pattern_key]) > 100:
                self.pattern_history[pattern_key] = self.pattern_history[pattern_key][-100:]
    
    def _fallback_analysis(self, content: str, metadata: Dict[str, Any] = None) -> ContentAnalysis:
        """フォールバック分析"""
        return ContentAnalysis(
            content=content,
            patterns=[],
            importance_score=0.5,
            novelty_score=0.5,
            should_vectorize=len(content) > 100,  # 長いコンテンツのみベクトル化
            metadata=metadata or {}
        )
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """パターン統計を取得"""
        return {
            'total_patterns_tracked': len(self.frequency_tracker),
            'most_frequent_patterns': dict(Counter(self.frequency_tracker).most_common(10)),
            'pattern_categories': {
                pattern_type.value: len([k for k in self.frequency_tracker.keys() if k.startswith(pattern_type.value)])
                for pattern_type in PatternType
            },
            'cache_size': len(self.pattern_cache)
        }
```

### 3.2 高速検索キャッシュ (`pattern_analysis/fast_search_cache.py`)

```python
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import hashlib
import json

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """キャッシュエントリ"""
    key: str
    content: str
    patterns: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    access_count: int
    last_accessed: datetime

class FastSearchCache:
    """高速検索キャッシュ"""
    
    def __init__(self, max_size: int = 10000, ttl_hours: int = 24):
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self.cache: Dict[str, CacheEntry] = {}
        self.pattern_index: Dict[str, List[str]] = {}  # パターン -> キーのマッピング
        self.access_order: List[str] = []  # LRU用
    
    async def store(self, content: str, patterns: List[str], metadata: Dict[str, Any] = None) -> str:
        """キャッシュにエントリを保存"""
        
        # キーを生成（コンテンツのハッシュ）
        key = self._generate_key(content)
        
        # 既存エントリがある場合は更新
        if key in self.cache:
            entry = self.cache[key]
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow()
            self._update_access_order(key)
            return key
        
        # 新規エントリを作成
        entry = CacheEntry(
            key=key,
            content=content,
            patterns=patterns,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            access_count=1,
            last_accessed=datetime.utcnow()
        )
        
        # キャッシュサイズ制限チェック
        if len(self.cache) >= self.max_size:
            await self._evict_old_entries()
        
        # キャッシュに保存
        self.cache[key] = entry
        self.access_order.append(key)
        
        # パターンインデックスを更新
        for pattern in patterns:
            if pattern not in self.pattern_index:
                self.pattern_index[pattern] = []
            self.pattern_index[pattern].append(key)
        
        logger.debug(f"キャッシュにエントリを保存: {key}")
        return key
    
    async def search_by_pattern(self, pattern: str, limit: int = 10) -> List[CacheEntry]:
        """パターンでキャッシュを検索"""
        
        # 期限切れエントリをクリーンアップ
        await self._cleanup_expired_entries()
        
        # パターンマッチング
        matching_keys = []
        
        # 完全一致
        if pattern in self.pattern_index:
            matching_keys.extend(self.pattern_index[pattern])
        
        # 部分一致
        for cached_pattern, keys in self.pattern_index.items():
            if pattern.lower() in cached_pattern.lower() and cached_pattern not in [pattern]:
                matching_keys.extend(keys)
        
        # 重複除去とアクセス時刻更新
        unique_keys = list(set(matching_keys))
        results = []
        
        for key in unique_keys[:limit]:
            if key in self.cache:
                entry = self.cache[key]
                entry.access_count += 1
                entry.last_accessed = datetime.utcnow()
                self._update_access_order(key)
                results.append(entry)
        
        # アクセス頻度順でソート
        results.sort(key=lambda x: x.access_count, reverse=True)
        
        logger.debug(f"パターン検索結果: {len(results)}件 (パターン: {pattern})")
        return results
    
    async def search_by_content(self, query: str, limit: int = 10) -> List[CacheEntry]:
        """コンテンツでキャッシュを検索"""
        
        await self._cleanup_expired_entries()
        
        results = []
        query_lower = query.lower()
        
        for entry in self.cache.values():
            if query_lower in entry.content.lower():
                entry.access_count += 1
                entry.last_accessed = datetime.utcnow()
                self._update_access_order(entry.key)
                results.append(entry)
        
        # 関連度でソート（簡易実装）
        results.sort(key=lambda x: (
            x.content.lower().count(query_lower),  # 出現回数
            x.access_count  # アクセス頻度
        ), reverse=True)
        
        return results[:limit]
    
    def _generate_key(self, content: str) -> str:
        """コンテンツからキーを生成"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _update_access_order(self, key: str) -> None:
        """アクセス順序を更新（LRU）"""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
    
    async def _evict_old_entries(self) -> None:
        """古いエントリを削除"""
        
        # LRUで削除対象を決定
        evict_count = max(1, self.max_size // 10)  # 10%を削除
        keys_to_evict = self.access_order[:evict_count]
        
        for key in keys_to_evict:
            if key in self.cache:
                entry = self.cache[key]
                
                # パターンインデックスからも削除
                for pattern in entry.patterns:
                    if pattern in self.pattern_index:
                        if key in self.pattern_index[pattern]:
                            self.pattern_index[pattern].remove(key)
                        if not self.pattern_index[pattern]:
                            del self.pattern_index[pattern]
                
                # キャッシュから削除
                del self.cache[key]
                self.access_order.remove(key)
        
        logger.info(f"キャッシュから{len(keys_to_evict)}件のエントリを削除")
    
    async def _cleanup_expired_entries(self) -> None:
        """期限切れエントリをクリーンアップ"""
        
        current_time = datetime.utcnow()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if current_time - entry.created_at > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            entry = self.cache[key]
            
            # パターンインデックスからも削除
            for pattern in entry.patterns:
                if pattern in self.pattern_index:
                    if key in self.pattern_index[pattern]:
                        self.pattern_index[pattern].remove(key)
                    if not self.pattern_index[pattern]:
                        del self.pattern_index[pattern]
            
            # キャッシュから削除
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)
        
        if expired_keys:
            logger.info(f"期限切れエントリを{len(expired_keys)}件削除")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        if not self.cache:
            return {"message": "キャッシュが空です"}
        
        total_access = sum(entry.access_count for entry in self.cache.values())
        avg_access = total_access / len(self.cache)
        
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "utilization": len(self.cache) / self.max_size,
            "pattern_index_size": len(self.pattern_index),
            "total_accesses": total_access,
            "average_accesses_per_entry": avg_access,
            "oldest_entry": min(entry.created_at for entry in self.cache.values()).isoformat(),
            "newest_entry": max(entry.created_at for entry in self.cache.values()).isoformat()
        }
```

## 4. Layer 2: 選択的ベクトル化

### 4.1 スマートベクトル化マネージャー (`smart_vectorization/vector_manager.py`)

```python
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np

from ..pattern_analysis.pattern_engine import PatternAnalysisEngine, ContentAnalysis
from ..pattern_analysis.fast_search_cache import FastSearchCache

logger = logging.getLogger(__name__)

class VectorPriority(Enum):
    """ベクトル化優先度"""
    CRITICAL = "critical"    # 即座にベクトル化
    HIGH = "high"           # 高優先度キューに追加
    MEDIUM = "medium"       # 通常キューに追加
    LOW = "low"            # 低優先度キューに追加
    SKIP = "skip"          # ベクトル化しない

@dataclass
class VectorCandidate:
    """ベクトル化候補"""
    content: str
    analysis: ContentAnalysis
    priority: VectorPriority
    created_at: datetime
    attempts: int = 0
    metadata: Dict[str, Any] = None

class SmartVectorizationManager:
    """スマートベクトル化マネージャー"""
    
    def __init__(
        self,
        pattern_engine: PatternAnalysisEngine,
        fast_cache: FastSearchCache,
        vector_store,
        config: Dict[str, Any]
    ):
        self.pattern_engine = pattern_engine
        self.fast_cache = fast_cache
        self.vector_store = vector_store
        self.config = config
        
        # 優先度別キュー
        self.priority_queues = {
            VectorPriority.CRITICAL: [],
            VectorPriority.HIGH: [],
            VectorPriority.MEDIUM: [],
            VectorPriority.LOW: []
        }
        
        # 一時ベクトルストレージ
        self.temp_vectors: Dict[str, Dict[str, Any]] = {}
        self.temp_vector_ttl = timedelta(hours=24)
        
        # 統計情報
        self.stats = {
            'total_processed': 0,
            'vectorized_count': 0,
            'cached_count': 0,
            'skipped_count': 0,
            'temp_vector_count': 0
        }
        
        # バックグラウンドタスク
        self._processing_task = None
        self._cleanup_task = None
    
    async def start(self) -> None:
        """バックグラウンド処理を開始"""
        self._processing_task = asyncio.create_task(self._process_queues())
        self._cleanup_task = asyncio.create_task(self._cleanup_temp_vectors())
        logger.info("スマートベクトル化マネージャーを開始")
    
    async def stop(self) -> None:
        """バックグラウンド処理を停止"""
        if self._processing_task:
            self._processing_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("スマートベクトル化マネージャーを停止")
    
    async def process_content(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        コンテンツを処理してベクトル化戦略を決定
        
        Args:
            content: 処理対象コンテンツ
            metadata: メタデータ
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            self.stats['total_processed'] += 1
            
            # パターン分析実行
            analysis = await self.pattern_engine.analyze_content(content, metadata)
            
            # 高速キャッシュに保存
            pattern_names = [p.pattern_name for p in analysis.patterns]
            cache_key = await self.fast_cache.store(content, pattern_names, analysis.metadata)
            
            # ベクトル化戦略を決定
            strategy = await