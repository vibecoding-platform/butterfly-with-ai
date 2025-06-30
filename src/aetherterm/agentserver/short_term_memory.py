"""
短期記憶管理システム - AgentServer側

ターミナル活動を短期記憶として蓄積し、ControlServerに送信する
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class ShortTermMemoryEntry:
    """短期記憶エントリ"""
    
    memory_id: str
    session_id: str
    memory_type: str  # command_execution, user_interaction, error_event, performance_metric
    content: str
    metadata: Dict
    timestamp: str
    severity: str = "info"  # debug, info, warning, error, critical


class ShortTermMemoryManager:
    """短期記憶管理システム"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        # 短期記憶ストレージ
        self.memories: List[ShortTermMemoryEntry] = []
        
        # 設定
        self.max_memories = 1000  # 最大保持メモリ数
        self.send_interval = 60  # 1分間隔でControlServerに送信
        self.memory_retention_hours = 2  # 2時間で短期記憶をクリア
        
        # ControlServer通信
        self.control_server_websocket = None
        self.send_queue = []
        
        # バックグラウンドタスク
        self.send_task = None
        self.cleanup_task = None
        
    async def start(self, control_server_websocket=None):
        """短期記憶管理開始"""
        logger.info(f"Starting ShortTermMemoryManager for agent {self.agent_id}")
        
        self.control_server_websocket = control_server_websocket
        
        # バックグラウンドタスクを開始
        self.send_task = asyncio.create_task(self._send_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
    async def stop(self):
        """短期記憶管理停止"""
        logger.info(f"Stopping ShortTermMemoryManager for agent {self.agent_id}")
        
        if self.send_task:
            self.send_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
            
        try:
            await asyncio.gather(self.send_task, self.cleanup_task, return_exceptions=True)
        except Exception:
            pass
    
    def record_command_execution(
        self, 
        session_id: str, 
        command: str, 
        exit_code: int = None,
        execution_time: float = None,
        output_lines: int = None
    ):
        """コマンド実行を記録"""
        
        # 重要度判定
        severity = "info"
        if exit_code is not None and exit_code != 0:
            severity = "warning" if exit_code < 128 else "error"
        
        metadata = {
            "command": command[:100],  # 最初の100文字のみ
            "exit_code": exit_code,
            "execution_time": execution_time,
            "output_lines": output_lines
        }
        
        content = f"Command executed: {command[:50]}"
        if exit_code is not None:
            content += f" (exit: {exit_code})"
        if execution_time is not None:
            content += f" (time: {execution_time:.2f}s)"
            
        self._add_memory(
            session_id=session_id,
            memory_type="command_execution",
            content=content,
            metadata=metadata,
            severity=severity
        )
    
    def record_user_interaction(
        self, 
        session_id: str, 
        interaction_type: str,  # input, resize, click, etc.
        details: str = None
    ):
        """ユーザーインタラクションを記録"""
        
        metadata = {
            "interaction_type": interaction_type,
            "details": details
        }
        
        content = f"User interaction: {interaction_type}"
        if details:
            content += f" - {details[:50]}"
            
        self._add_memory(
            session_id=session_id,
            memory_type="user_interaction",
            content=content,
            metadata=metadata,
            severity="debug"
        )
    
    def record_error_event(
        self, 
        session_id: str, 
        error_type: str,
        error_message: str,
        stack_trace: str = None
    ):
        """エラーイベントを記録"""
        
        # エラーの重要度判定
        severity = "error"
        if "critical" in error_message.lower() or "fatal" in error_message.lower():
            severity = "critical"
        elif "warning" in error_message.lower():
            severity = "warning"
        
        metadata = {
            "error_type": error_type,
            "error_message": error_message[:200],
            "has_stack_trace": stack_trace is not None,
            "stack_trace_lines": len(stack_trace.split('\n')) if stack_trace else 0
        }
        
        content = f"Error: {error_type} - {error_message[:100]}"
        
        self._add_memory(
            session_id=session_id,
            memory_type="error_event",
            content=content,
            metadata=metadata,
            severity=severity
        )
    
    def record_performance_metric(
        self, 
        session_id: str, 
        metric_name: str,
        value: float,
        unit: str = None,
        threshold_exceeded: bool = False
    ):
        """パフォーマンスメトリクスを記録"""
        
        severity = "info"
        if threshold_exceeded:
            severity = "warning"
        
        metadata = {
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
            "threshold_exceeded": threshold_exceeded
        }
        
        content = f"Performance: {metric_name} = {value}"
        if unit:
            content += f" {unit}"
        if threshold_exceeded:
            content += " (threshold exceeded)"
            
        self._add_memory(
            session_id=session_id,
            memory_type="performance_metric",
            content=content,
            metadata=metadata,
            severity=severity
        )
    
    def _add_memory(
        self, 
        session_id: str, 
        memory_type: str, 
        content: str, 
        metadata: Dict,
        severity: str = "info"
    ):
        """メモリを追加"""
        
        memory = ShortTermMemoryEntry(
            memory_id=str(uuid4()),
            session_id=session_id,
            memory_type=memory_type,
            content=content,
            metadata=metadata,
            timestamp=datetime.utcnow().isoformat(),
            severity=severity
        )
        
        self.memories.append(memory)
        
        # 送信キューに追加
        self.send_queue.append(memory)
        
        # メモリ数制限
        if len(self.memories) > self.max_memories:
            self.memories = self.memories[-self.max_memories:]
        
        logger.debug(f"Added memory: {memory_type} for session {session_id}")
        
        # 緊急度が高い場合は即座に送信を試行
        if severity in ["error", "critical"] and self.control_server_websocket:
            asyncio.create_task(self._send_immediate(memory))
    
    async def _send_loop(self):
        """定期送信ループ"""
        while True:
            try:
                await asyncio.sleep(self.send_interval)
                await self._send_queued_memories()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory send loop: {e}")
    
    async def _cleanup_loop(self):
        """定期クリーンアップループ"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1時間間隔
                await self._cleanup_old_memories()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory cleanup loop: {e}")
    
    async def _send_queued_memories(self):
        """キューに溜まったメモリを送信"""
        if not self.send_queue or not self.control_server_websocket:
            return
            
        try:
            # バッチで送信
            memories_to_send = self.send_queue.copy()
            self.send_queue.clear()
            
            if memories_to_send:
                await self._send_memories_batch(memories_to_send)
                logger.debug(f"Sent {len(memories_to_send)} memories to ControlServer")
                
        except Exception as e:
            logger.error(f"Error sending queued memories: {e}")
            # 送信失敗したメモリを再キューに追加
            self.send_queue.extend(memories_to_send)
    
    async def _send_immediate(self, memory: ShortTermMemoryEntry):
        """緊急メモリの即座送信"""
        if not self.control_server_websocket:
            return
            
        try:
            await self._send_memories_batch([memory])
            logger.info(f"Sent immediate memory: {memory.memory_type} ({memory.severity})")
            
        except Exception as e:
            logger.error(f"Error sending immediate memory: {e}")
    
    async def _send_memories_batch(self, memories: List[ShortTermMemoryEntry]):
        """メモリバッチをControlServerに送信"""
        if not self.control_server_websocket:
            return
            
        for memory in memories:
            message = {
                "type": "short_term_memory",
                "memory": asdict(memory),
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            try:
                await self.control_server_websocket.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending memory {memory.memory_id}: {e}")
                raise
    
    async def _cleanup_old_memories(self):
        """古いメモリのクリーンアップ"""
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(hours=self.memory_retention_hours)
        
        original_count = len(self.memories)
        
        # 期限切れのメモリを削除
        self.memories = [
            memory for memory in self.memories
            if datetime.fromisoformat(memory.timestamp.replace('Z', '+00:00')) >= cutoff_time
        ]
        
        cleaned_count = original_count - len(self.memories)
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old memories")
    
    def set_control_server_websocket(self, websocket):
        """ControlServer WebSocketを設定"""
        self.control_server_websocket = websocket
        logger.info(f"ControlServer WebSocket connection set for agent {self.agent_id}")
    
    def get_memory_summary(self) -> Dict:
        """メモリサマリを取得"""
        
        # タイプ別集計
        type_counts = {}
        severity_counts = {}
        
        for memory in self.memories:
            type_counts[memory.memory_type] = type_counts.get(memory.memory_type, 0) + 1
            severity_counts[memory.severity] = severity_counts.get(memory.severity, 0) + 1
        
        return {
            "agent_id": self.agent_id,
            "total_memories": len(self.memories),
            "queued_for_send": len(self.send_queue),
            "type_distribution": type_counts,
            "severity_distribution": severity_counts,
            "oldest_memory": min([m.timestamp for m in self.memories]) if self.memories else None,
            "newest_memory": max([m.timestamp for m in self.memories]) if self.memories else None,
            "control_server_connected": self.control_server_websocket is not None
        }