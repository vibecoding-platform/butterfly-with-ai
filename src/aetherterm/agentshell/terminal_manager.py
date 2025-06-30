"""
ターミナル管理システム

AgentShellで生成されたターミナルとエージェントの割り当てを管理
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from .websocket.protocol import (
    TerminalSpawnRequest,
    TerminalAssignment,
    TerminalStatus,
    MessageType,
)

log = logging.getLogger("aetherterm.agentshell.terminal_manager")


class TerminalManager:
    """ターミナル管理システム"""

    def __init__(self, websocket_client):
        self.websocket_client = websocket_client
        self.terminals: Dict[str, TerminalStatus] = {}
        self.assignments: Dict[str, TerminalAssignment] = {}
        self.spawn_requests: Dict[str, TerminalSpawnRequest] = {}
        
    async def request_terminal_spawn(
        self,
        agent_type: str,
        agent_id: str,
        working_directory: Optional[str] = None,
        launch_mode: str = "agent",
        additional_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """新しいターミナルの生成を要求"""
        try:
            spawn_request = TerminalSpawnRequest(
                requester_agent_id="agentshell",
                agent_type=agent_type,
                agent_id=agent_id,
                working_directory=working_directory,
                launch_mode=launch_mode,
                additional_config=additional_config or {},
            )
            
            # 要求を記録
            request_id = str(spawn_request.request_id)
            self.spawn_requests[request_id] = spawn_request
            
            # AgentServerに要求を送信
            await self.websocket_client.send_message(
                "agentserver",
                MessageType.TERMINAL_SPAWN_REQUEST,
                spawn_request.to_dict()
            )
            
            log.info(f"Terminal spawn requested: {agent_type}:{agent_id}, request_id: {request_id}")
            return request_id
            
        except Exception as e:
            log.error(f"Failed to request terminal spawn: {e}")
            raise

    async def assign_agent_to_terminal(
        self,
        terminal_id: str,
        agent_type: str,
        agent_id: str,
        working_directory: Optional[str] = None,
        startup_command: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        capabilities_required: Optional[List[str]] = None,
    ) -> str:
        """ターミナルにエージェントを割り当て"""
        try:
            assignment = TerminalAssignment(
                terminal_id=terminal_id,
                agent_type=agent_type,
                agent_id=agent_id,
                working_directory=working_directory,
                startup_command=startup_command,
                environment_vars=environment_vars or {},
                capabilities_required=capabilities_required or [],
            )
            
            # 割り当てを記録
            assignment_id = str(assignment.assignment_id)
            self.assignments[assignment_id] = assignment
            
            # ターミナル状態を更新
            if terminal_id in self.terminals:
                self.terminals[terminal_id].agent_assignment = assignment
                self.terminals[terminal_id].status = "initializing"
            else:
                # 新しいターミナル状態を作成
                self.terminals[terminal_id] = TerminalStatus(
                    terminal_id=terminal_id,
                    status="initializing",
                    agent_assignment=assignment,
                )
            
            # AgentServerに割り当て要求を送信
            await self.websocket_client.send_message(
                "agentserver",
                MessageType.TERMINAL_ASSIGN_AGENT,
                assignment.to_dict()
            )
            
            log.info(f"Agent assigned to terminal: {terminal_id} -> {agent_type}:{agent_id}")
            return assignment_id
            
        except Exception as e:
            log.error(f"Failed to assign agent to terminal: {e}")
            raise

    async def update_terminal_status(
        self,
        terminal_id: str,
        status: str,
        process_id: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """ターミナル状態を更新"""
        try:
            if terminal_id not in self.terminals:
                # 新しいターミナル状態を作成
                self.terminals[terminal_id] = TerminalStatus(
                    terminal_id=terminal_id,
                    status=status,
                    process_id=process_id,
                    error_message=error_message,
                    metadata=metadata or {},
                )
            else:
                # 既存のターミナル状態を更新
                terminal_status = self.terminals[terminal_id]
                terminal_status.status = status
                terminal_status.last_activity = datetime.utcnow()
                
                if process_id is not None:
                    terminal_status.process_id = process_id
                if error_message is not None:
                    terminal_status.error_message = error_message
                if metadata:
                    terminal_status.metadata.update(metadata)
            
            log.info(f"Terminal status updated: {terminal_id} -> {status}")
            
        except Exception as e:
            log.error(f"Failed to update terminal status: {e}")

    async def handle_terminal_ready(self, terminal_id: str, metadata: Optional[Dict[str, Any]] = None):
        """ターミナル準備完了を処理"""
        await self.update_terminal_status(
            terminal_id=terminal_id,
            status="ready",
            metadata=metadata,
        )
        
        # 割り当てられたエージェントに通知
        terminal_status = self.terminals.get(terminal_id)
        if terminal_status and terminal_status.agent_assignment:
            await self.websocket_client.send_message(
                terminal_status.agent_assignment.agent_id,
                MessageType.TERMINAL_READY,
                {
                    "terminal_id": terminal_id,
                    "assignment": terminal_status.agent_assignment.to_dict(),
                    "metadata": metadata or {},
                }
            )

    async def handle_terminal_closed(self, terminal_id: str, reason: Optional[str] = None):
        """ターミナル終了を処理"""
        await self.update_terminal_status(
            terminal_id=terminal_id,
            status="closed",
            error_message=reason,
        )
        
        # 関連する割り当てを削除
        assignments_to_remove = [
            assignment_id for assignment_id, assignment in self.assignments.items()
            if assignment.terminal_id == terminal_id
        ]
        
        for assignment_id in assignments_to_remove:
            del self.assignments[assignment_id]
        
        log.info(f"Terminal closed: {terminal_id}, reason: {reason}")

    def get_terminal_status(self, terminal_id: str) -> Optional[TerminalStatus]:
        """ターミナル状態を取得"""
        return self.terminals.get(terminal_id)

    def get_all_terminals(self) -> Dict[str, TerminalStatus]:
        """全ターミナル状態を取得"""
        return self.terminals.copy()

    def get_terminals_by_agent(self, agent_id: str) -> List[TerminalStatus]:
        """特定エージェントが割り当てられたターミナルを取得"""
        result = []
        for terminal_status in self.terminals.values():
            if (terminal_status.agent_assignment and 
                terminal_status.agent_assignment.agent_id == agent_id):
                result.append(terminal_status)
        return result

    def get_terminals_by_type(self, agent_type: str) -> List[TerminalStatus]:
        """特定エージェントタイプのターミナルを取得"""
        result = []
        for terminal_status in self.terminals.values():
            if (terminal_status.agent_assignment and 
                terminal_status.agent_assignment.agent_type == agent_type):
                result.append(terminal_status)
        return result

    def get_active_terminals(self) -> List[TerminalStatus]:
        """アクティブなターミナルを取得"""
        return [
            terminal_status for terminal_status in self.terminals.values()
            if terminal_status.status in ["ready", "busy", "initializing"]
        ]

    async def cleanup_closed_terminals(self):
        """終了したターミナルをクリーンアップ"""
        closed_terminals = [
            terminal_id for terminal_id, status in self.terminals.items()
            if status.status == "closed"
        ]
        
        for terminal_id in closed_terminals:
            del self.terminals[terminal_id]
            log.debug(f"Cleaned up closed terminal: {terminal_id}")

    async def terminate_terminal(self, terminal_id: str, force: bool = False):
        """ターミナルを終了"""
        try:
            terminal_status = self.terminals.get(terminal_id)
            if not terminal_status:
                log.warning(f"Terminal not found for termination: {terminal_id}")
                return

            # AgentServerに終了要求を送信
            await self.websocket_client.send_message(
                "agentserver",
                "terminal_terminate",
                {
                    "terminal_id": terminal_id,
                    "force": force,
                }
            )
            
            # 状態を更新
            await self.update_terminal_status(
                terminal_id=terminal_id,
                status="closed",
                error_message="Terminated by user request" if not force else "Force terminated"
            )
            
            log.info(f"Terminal termination requested: {terminal_id}, force: {force}")
            
        except Exception as e:
            log.error(f"Failed to terminate terminal {terminal_id}: {e}")

    def get_terminal_statistics(self) -> Dict[str, Any]:
        """ターミナル統計情報を取得"""
        total_terminals = len(self.terminals)
        active_terminals = len(self.get_active_terminals())
        
        status_counts = {}
        agent_type_counts = {}
        
        for terminal_status in self.terminals.values():
            # ステータス別カウント
            status = terminal_status.status
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # エージェントタイプ別カウント
            if terminal_status.agent_assignment:
                agent_type = terminal_status.agent_assignment.agent_type
                agent_type_counts[agent_type] = agent_type_counts.get(agent_type, 0) + 1
        
        return {
            "total_terminals": total_terminals,
            "active_terminals": active_terminals,
            "status_distribution": status_counts,
            "agent_type_distribution": agent_type_counts,
            "spawn_requests": len(self.spawn_requests),
            "assignments": len(self.assignments),
        }