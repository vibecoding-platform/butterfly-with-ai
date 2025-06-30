# ベクトル最適化・容量管理 - 完全実装仕様

## 1. Layer 2: 選択的ベクトル化（続き）

### 1.1 スマートベクトル化マネージャー（完成版）

```python
# smart_vectorization/vector_manager.py (続き)

    async def process_content(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """コンテンツを処理してベクトル化戦略を決定"""
        try:
            self.stats['total_processed'] += 1
            
            # パターン分析実行
            analysis = await self.pattern_engine.analyze_content(content, metadata)
            
            # 高速キャッシュに保存
            pattern_names = [p.pattern_name for p in analysis.patterns]
            cache_key = await self.fast_cache.store(content, pattern_names, analysis.metadata)
            
            # ベクトル化戦略を決定
            strategy = await self._determine_vectorization_strategy(analysis, metadata)
            
            if strategy['action'] == 'immediate_vectorize':
                # 即座にベクトル化
                vector_result = await self._immediate_vectorize(content, analysis)
                self.stats['vectorized_count'] += 1
                return {
                    'status': 'vectorized',
                    'cache_key': cache_key,
                    'vector_id': vector_result['id'],
                    'strategy': strategy
                }
            
            elif strategy['action'] == 'queue_vectorize':
                # キューに追加
                candidate = VectorCandidate(
                    content=content,
                    analysis=analysis,
                    priority=strategy['priority'],
                    created_at=datetime.utcnow(),
                    metadata=metadata
                )
                self.priority_queues[strategy['priority']].append(candidate)
                return {
                    'status': 'queued',
                    'cache_key': cache_key,
                    'priority': strategy['priority'].value,
                    'strategy': strategy
                }
            
            elif strategy['action'] == 'temp_vectorize':
                # 一時ベクトル化
                temp_result = await self._create_temp_vector(content, analysis)
                self.stats['temp_vector_count'] += 1
                return {
                    'status': 'temp_vectorized',
                    'cache_key': cache_key,
                    'temp_vector_id': temp_result['id'],
                    'strategy': strategy
                }
            
            else:
                # キャッシュのみ
                self.stats['cached_count'] += 1
                return {
                    'status': 'cached_only',
                    'cache_key': cache_key,
                    'strategy': strategy
                }
                
        except Exception as e:
            logger.error(f"コンテンツ処理中にエラー: {e}")
            self.stats['skipped_count'] += 1
            return {'status': 'error', 'error': str(e)}
    
    async def _determine_vectorization_strategy(
        self, 
        analysis: ContentAnalysis, 
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """ベクトル化戦略を決定"""
        
        strategy = {
            'action': 'cache_only',
            'priority': VectorPriority.LOW,
            'reasoning': []
        }
        
        # 重要度・新規性による判定
        if analysis.importance_score >= 0.8 and analysis.novelty_score >= 0.7:
            strategy['action'] = 'immediate_vectorize'
            strategy['reasoning'].append('高重要度・高新規性')
        
        elif analysis.importance_score >= 0.7:
            strategy['action'] = 'queue_vectorize'
            strategy['priority'] = VectorPriority.HIGH
            strategy['reasoning'].append('高重要度')
        
        elif analysis.novelty_score >= 0.8:
            strategy['action'] = 'temp_vectorize'
            strategy['reasoning'].append('高新規性（一時保存）')
        
        # パターンベースの調整
        error_patterns = [p for p in analysis.patterns if p.pattern_type.value == 'error']
        if error_patterns:
            if strategy['action'] == 'cache_only':
                strategy['action'] = 'queue_vectorize'
                strategy['priority'] = VectorPriority.HIGH
            elif strategy['action'] == 'queue_vectorize' and strategy['priority'] != VectorPriority.CRITICAL:
                strategy['priority'] = VectorPriority.HIGH
            strategy['reasoning'].append('エラーパターン検出')
        
        workflow_patterns = [p for p in analysis.patterns if p.pattern_type.value == 'user_workflow']
        if workflow_patterns:
            if strategy['action'] == 'cache_only':
                strategy['action'] = 'queue_vectorize'
                strategy['priority'] = VectorPriority.MEDIUM
            strategy['reasoning'].append('ワークフローパターン検出')
        
        # メタデータによる調整
        if metadata:
            session_duration = metadata.get('session_duration_minutes', 0)
            if session_duration > 120:  # 2時間以上のセッション
                if strategy['priority'] == VectorPriority.LOW:
                    strategy['priority'] = VectorPriority.MEDIUM
                strategy['reasoning'].append('長時間セッション')
        
        # 容量制限チェック
        current_usage = await self._get_vector_store_usage()
        if current_usage['utilization'] > 0.9:  # 90%以上使用
            if strategy['action'] == 'immediate_vectorize':
                strategy['action'] = 'temp_vectorize'
                strategy['reasoning'].append('容量制限により一時保存')
            elif strategy['action'] == 'queue_vectorize':
                if strategy['priority'] not in [VectorPriority.CRITICAL, VectorPriority.HIGH]:
                    strategy['action'] = 'cache_only'
                    strategy['reasoning'].append('容量制限によりキャッシュのみ')
        
        return strategy
    
    async def _immediate_vectorize(self, content: str, analysis: ContentAnalysis) -> Dict[str, Any]:
        """即座にベクトル化"""
        try:
            # 埋め込みベクトルを生成
            embedding = await self._generate_embedding(content)
            
            # Vector Storeに保存
            doc_id = await self.vector_store.add_document(
                content=content,
                embedding=embedding,
                metadata={
                    **analysis.metadata,
                    'importance_score': analysis.importance_score,
                    'novelty_score': analysis.novelty_score,
                    'patterns': [p.pattern_name for p in analysis.patterns],
                    'vectorized_at': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"即座にベクトル化完了: {doc_id}")
            return {'id': doc_id, 'embedding_size': len(embedding)}
            
        except Exception as e:
            logger.error(f"即座ベクトル化中にエラー: {e}")
            raise
    
    async def _create_temp_vector(self, content: str, analysis: ContentAnalysis) -> Dict[str, Any]:
        """一時ベクトルを作成"""
        try:
            # 埋め込みベクトルを生成
            embedding = await self._generate_embedding(content)
            
            # 一時ストレージに保存
            temp_id = f"temp_{datetime.utcnow().timestamp()}"
            self.temp_vectors[temp_id] = {
                'content': content,
                'embedding': embedding,
                'analysis': analysis,
                'created_at': datetime.utcnow(),
                'access_count': 0
            }
            
            logger.debug(f"一時ベクトル作成: {temp_id}")
            return {'id': temp_id, 'embedding_size': len(embedding)}
            
        except Exception as e:
            logger.error(f"一時ベクトル作成中にエラー: {e}")
            raise
    
    async def _process_queues(self) -> None:
        """優先度キューを処理"""
        while True:
            try:
                # 優先度順に処理
                for priority in [VectorPriority.CRITICAL, VectorPriority.HIGH, VectorPriority.MEDIUM, VectorPriority.LOW]:
                    queue = self.priority_queues[priority]
                    
                    if queue:
                        candidate = queue.pop(0)
                        await self._process_candidate(candidate)
                
                # 処理間隔
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"キュー処理中にエラー: {e}")
                await asyncio.sleep(5)
    
    async def _process_candidate(self, candidate: VectorCandidate) -> None:
        """候補をベクトル化処理"""
        try:
            candidate.attempts += 1
            
            # 容量チェック
            usage = await self._get_vector_store_usage()
            if usage['utilization'] > 0.95:
                # 容量不足の場合は一時ベクトル化
                await self._create_temp_vector(candidate.content, candidate.analysis)
                return
            
            # 通常のベクトル化
            await self._immediate_vectorize(candidate.content, candidate.analysis)
            
        except Exception as e:
            logger.error(f"候補処理中にエラー: {e}")
            
            # 再試行制限
            if candidate.attempts < 3:
                # 低優先度キューに戻す
                self.priority_queues[VectorPriority.LOW].append(candidate)
    
    async def _cleanup_temp_vectors(self) -> None:
        """一時ベクトルのクリーンアップ"""
        while True:
            try:
                current_time = datetime.utcnow()
                expired_ids = []
                
                for temp_id, temp_data in self.temp_vectors.items():
                    if current_time - temp_data['created_at'] > self.temp_vector_ttl:
                        expired_ids.append(temp_id)
                
                # 期限切れ一時ベクトルを削除
                for temp_id in expired_ids:
                    del self.temp_vectors[temp_id]
                
                if expired_ids:
                    logger.info(f"期限切れ一時ベクトルを{len(expired_ids)}件削除")
                
                # 1時間ごとにクリーンアップ
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"一時ベクトルクリーンアップ中にエラー: {e}")
                await asyncio.sleep(300)
    
    async def search_temp_vectors(self, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """一時ベクトルを検索"""
        results = []
        
        for temp_id, temp_data in self.temp_vectors.items():
            # コサイン類似度を計算
            similarity = self._calculate_cosine_similarity(
                query_embedding, 
                temp_data['embedding']
            )
            
            if similarity > 0.7:  # 閾値
                temp_data['access_count'] += 1
                results.append({
                    'id': temp_id,
                    'content': temp_data['content'],
                    'similarity': similarity,
                    'metadata': temp_data['analysis'].metadata
                })
        
        # 類似度順でソート
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:limit]
    
    async def promote_temp_vector(self, temp_id: str) -> Optional[str]:
        """一時ベクトルを永続化"""
        if temp_id not in self.temp_vectors:
            return None
        
        temp_data = self.temp_vectors[temp_id]
        
        try:
            # 永続ベクトルストアに移動
            doc_id = await self.vector_store.add_document(
                content=temp_data['content'],
                embedding=temp_data['embedding'],
                metadata={
                    **temp_data['analysis'].metadata,
                    'promoted_from_temp': True,
                    'temp_access_count': temp_data['access_count'],
                    'promoted_at': datetime.utcnow().isoformat()
                }
            )
            
            # 一時ストレージから削除
            del self.temp_vectors[temp_id]
            
            logger.info(f"一時ベクトルを永続化: {temp_id} -> {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"一時ベクトル永続化中にエラー: {e}")
            return None
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """コサイン類似度を計算"""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def _generate_embedding(self, content: str) -> List[float]:
        """埋め込みベクトルを生成"""
        # 実際の実装では、OpenAI Embeddings APIやSentence Transformersを使用
        # ここではプレースホルダー
        return [0.1] * 1536  # OpenAI ada-002の次元数
    
    async def _get_vector_store_usage(self) -> Dict[str, Any]:
        """Vector Storeの使用状況を取得"""
        # 実際の実装では、Vector Storeの統計APIを使用
        return {
            'total_documents': 10000,
            'storage_size_mb': 500,
            'utilization': 0.75
        }
```

## 2. Layer 3: 永続化・圧縮

### 2.1 パターン統合・圧縮エンジン (`compression/pattern_compressor.py`)

```python
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import json
import gzip

logger = logging.getLogger(__name__)

@dataclass
class PatternCluster:
    """パターンクラスター"""
    cluster_id: str
    representative_content: str
    similar_contents: List[str]
    pattern_signature: str
    frequency: int
    importance_score: float
    created_at: datetime
    last_updated: datetime

class PatternCompressor:
    """パターン統合・圧縮エンジン"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.clusters: Dict[str, PatternCluster] = {}
        self.compression_stats = {
            'total_processed': 0,
            'clusters_created': 0,
            'compression_ratio': 0.0,
            'storage_saved_mb': 0.0
        }
    
    async def compress_patterns(self, contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """パターンを統合・圧縮"""
        
        logger.info(f"パターン圧縮開始: {len(contents)}件")
        
        # 類似コンテンツをクラスタリング
        clusters = await self._cluster_similar_contents(contents)
        
        # 各クラスターを圧縮
        compressed_clusters = []
        for cluster in clusters:
            compressed_cluster = await self._compress_cluster(cluster)
            compressed_clusters.append(compressed_cluster)
        
        # 圧縮統計を更新
        original_size = sum(len(c['content'].encode('utf-8')) for c in contents)
        compressed_size = sum(len(c.representative_content.encode('utf-8')) for c in compressed_clusters)
        
        self.compression_stats['total_processed'] += len(contents)
        self.compression_stats['clusters_created'] += len(compressed_clusters)
        self.compression_stats['compression_ratio'] = 1 - (compressed_size / original_size) if original_size > 0 else 0
        self.compression_stats['storage_saved_mb'] += (original_size - compressed_size) / (1024 * 1024)
        
        logger.info(f"パターン圧縮完了: {len(contents)}件 -> {len(compressed_clusters)}クラスター")
        
        return {
            'compressed_clusters': compressed_clusters,
            'original_count': len(contents),
            'compressed_count': len(compressed_clusters),
            'compression_ratio': self.compression_stats['compression_ratio'],
            'storage_saved_mb': (original_size - compressed_size) / (1024 * 1024)
        }
    
    async def _cluster_similar_contents(self, contents: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """類似コンテンツをクラスタリング"""
        
        clusters = []
        processed = set()
        
        for i, content in enumerate(contents):
            if i in processed:
                continue
            
            # 新しいクラスターを開始
            cluster = [content]
            processed.add(i)
            
            # 類似コンテンツを検索
            for j, other_content in enumerate(contents[i+1:], i+1):
                if j in processed:
                    continue
                
                similarity = await self._calculate_content_similarity(
                    content['content'], 
                    other_content['content']
                )
                
                if similarity >= self.similarity_threshold:
                    cluster.append(other_content)
                    processed.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    async def _compress_cluster(self, cluster: List[Dict[str, Any]]) -> PatternCluster:
        """クラスターを圧縮"""
        
        # 代表コンテンツを選択（最も重要度が高いもの）
        representative = max(cluster, key=lambda x: x.get('importance_score', 0.5))
        
        # パターンシグネチャを生成
        pattern_signature = await self._generate_pattern_signature(cluster)
        
        # 類似コンテンツリストを作成
        similar_contents = [c['content'] for c in cluster if c != representative]
        
        # 重要度スコアを統合
        avg_importance = sum(c.get('importance_score', 0.5) for c in cluster) / len(cluster)
        
        cluster_id = f"cluster_{datetime.utcnow().timestamp()}_{len(cluster)}"
        
        return PatternCluster(
            cluster_id=cluster_id,
            representative_content=representative['content'],
            similar_contents=similar_contents,
            pattern_signature=pattern_signature,
            frequency=len(cluster),
            importance_score=avg_importance,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow()
        )
    
    async def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """コンテンツ類似度を計算"""
        
        # 簡易的な類似度計算（実際にはより高度な手法を使用）
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        jaccard_similarity = len(intersection) / len(union)
        
        # 長さの類似性も考慮
        length_similarity = 1 - abs(len(content1) - len(content2)) / max(len(content1), len(content2))
        
        # 重み付き平均
        return jaccard_similarity * 0.7 + length_similarity * 0.3
    
    async def _generate_pattern_signature(self, cluster: List[Dict[str, Any]]) -> str:
        """パターンシグネチャを生成"""
        
        # 共通パターンを抽出
        all_patterns = []
        for content in cluster:
            patterns = content.get('patterns', [])
            all_patterns.extend(patterns)
        
        # 頻度の高いパターンを選択
        pattern_freq = defaultdict(int)
        for pattern in all_patterns:
            pattern_freq[pattern] += 1
        
        # 上位パターンでシグネチャを作成
        top_patterns = sorted(pattern_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        signature_parts = [f"{pattern}:{freq}" for pattern, freq in top_patterns]
        
        return "|".join(signature_parts)
    
    async def search_compressed_patterns(self, query: str, limit: int = 10) -> List[PatternCluster]:
        """圧縮されたパターンを検索"""
        
        results = []
        query_lower = query.lower()
        
        for cluster in self.clusters.values():
            # 代表コンテンツでの検索
            if query_lower in cluster.representative_content.lower():
                results.append(cluster)
                continue
            
            # パターンシグネチャでの検索
            if any(query_lower in part.lower() for part in cluster.pattern_signature.split('|')):
                results.append(cluster)
                continue
            
            # 類似コンテンツでの検索
            for similar_content in cluster.similar_contents:
                if query_lower in similar_content.lower():
                    results.append(cluster)
                    break
        
        # 重要度とアクセス頻度でソート
        results.sort(key=lambda x: (x.importance_score, x.frequency), reverse=True)
        
        return results[:limit]
    
    def get_compression_statistics(self) -> Dict[str, Any]:
        """圧縮統計を取得"""
        return {
            **self.compression_stats,
            'active_clusters': len(self.clusters),
            'average_cluster_size': sum(c.frequency for c in self.clusters.values()) / max(len(self.clusters), 1)
        }
```

### 2.2 動的容量管理システム (`capacity/capacity_manager.py`)

```python
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CapacityAction(Enum):
    """容量管理アクション"""
    ARCHIVE_OLD = "archive_old"
    COMPRESS_SIMILAR = "compress_similar"
    DELETE_LOW_PRIORITY = "delete_low_priority"
    PROMOTE_TEMP = "promote_temp"
    OPTIMIZE_INDEX = "optimize_index"

@dataclass
class CapacityAlert:
    """容量アラート"""
    alert_type: str
    current_usage: float
    threshold: float
    recommended_actions: List[CapacityAction]
    created_at: datetime

class DynamicCapacityManager:
    """動的容量管理システム"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.thresholds = {
            'warning': config.get('warning_threshold', 0.8),
            'critical': config.get('critical_threshold', 0.9),
            'emergency': config.get('emergency_threshold', 0.95)
        }
        
        self.alerts: List[CapacityAlert] = []
        self.auto_cleanup_enabled = config.get('auto_cleanup', True)
        self.monitoring_task = None
    
    async def start_monitoring(self) -> None:
        """容量監視を開始"""
        self.monitoring_task = asyncio.create_task(self._monitor_capacity())
        logger.info("動的容量管理システムを開始")
    
    async def stop_monitoring(self) -> None:
        """容量監視を停止"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
        logger.info("動的容量管理システムを停止")
    
    async def _monitor_capacity(self) -> None:
        """容量を監視"""
        while True:
            try:
                # 現在の使用状況を取得
                usage_stats = await self._get_usage_statistics()
                current_usage = usage_stats['utilization']
                
                # 閾値チェック
                if current_usage >= self.thresholds['emergency']:
                    await self._handle_emergency_capacity(usage_stats)
                elif current_usage >= self.thresholds['critical']:
                    await self._handle_critical_capacity(usage_stats)
                elif current_usage >= self.thresholds['warning']:
                    await self._handle_warning_capacity(usage_stats)
                
                # 監視間隔
                await asyncio.sleep(300)  # 5分間隔
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"容量監視中にエラー: {e}")
                await asyncio.sleep(60)
    
    async def _handle_emergency_capacity(self, usage_stats: Dict[str, Any]) -> None:
        """緊急容量対応"""
        logger.critical(f"緊急容量アラート: {usage_stats['utilization']:.2%}")
        
        # 緊急クリーンアップを実行
        actions_taken = []
        
        # 1. 低優先度データの削除
        deleted_count = await self._delete_low_priority_data()
        if deleted_count > 0:
            actions_taken.append(f"低優先度データ{deleted_count}件削除")
        
        # 2. 古いデータのアーカイブ
        archived_count = await self._archive_old_data(days=7)  # 7日以上古いデータ
        if archived_count > 0:
            actions_taken.append(f"古いデータ{archived_count}件アーカイブ")
        
        # 3. インデックス最適化
        await self._optimize_indexes()
        actions_taken.append("インデックス最適化実行")
        
        # アラートを記録
        alert = CapacityAlert(
            alert_type="emergency",
            current_usage=usage_stats['utilization'],
            threshold=self.thresholds['emergency'],
            recommended_actions=[CapacityAction.DELETE_LOW_PRIORITY, CapacityAction.ARCHIVE_OLD],
            created_at=datetime.utcnow()
        )
        self.alerts.append(alert)
        
        logger.info(f"緊急容量対応完了: {', '.join(actions_taken)}")
    
    async def _handle_critical_capacity(self, usage_stats: Dict[str, Any]) -> None:
        """重要容量対応"""
        logger.warning(f"重要容量アラート: {usage_stats['utilization']:.2%}")
        
        if self.auto_cleanup_enabled:
            # 自動クリーンアップを実行
            actions_taken = []
            
            # 1. 類似データの圧縮
            compressed_count = await self._compress_similar_data()
            if compressed_count > 0:
                actions_taken.append(f"類似データ{compressed_count}件圧縮")
            
            # 2. 一時ベクトルの永続化判定
            promoted_count = await self._evaluate_temp_vectors()
            if promoted_count > 0:
                actions_taken.append(f"一時ベクトル{promoted_count}件永続化")
            
            logger.info(f"重要容量対応完了: {', '.join(actions_taken)}")
    
    async def _handle_warning_capacity(self, usage_stats: Dict[str, Any]) -> None:
        """警告容量対応"""
        logger.info(f"容量警告: {usage_stats['utilization']:.2%}")
        
        # 予防的メンテナンスを実行
        await self._preventive_maintenance()
    
    async def _delete_low_priority_data(self) -> int:
        """低優先度データを削除"""
        # 実装例：重要度スコアが低く、アクセス頻度も低いデータを削除
        deleted_count = 0
        
        # Vector Storeから低優先度データを検索・削除
        # 実際の実装では、Vector Storeの削除APIを使用
        
        logger.info(f"低優先度データ{deleted_count}件を削除")
        return deleted_count
    
    async def _archive_old_data(self, days: int) -> int:
        """古いデータをアーカイブ"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        archived_count = 0
        
        # 古いデータを圧縮してアーカイブストレージに移動
        # 実際の実装では、S3やGCSなどのオブジェクトストレージを使用
        
        logger.info(f"{days}日以上古いデータ{archived_count}件をアーカイブ")
        return archived_count
    
    async def _compress_similar_data(self) -> int:
        """類似データを圧縮"""
        compressed_count = 0
        
        # 類似度の高いベクトルを検出して圧縮
        # PatternCompressorを使用
        
        logger.info(f"類