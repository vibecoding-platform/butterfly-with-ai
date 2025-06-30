"""
エージェント間通信プロトコル

WebSocket経由でのメッセージフォーマットを定義
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class MessageType(str, Enum):
    """メッセージタイプ"""
    
    # エージェント管理
    AGENT_REGISTER = "agent_register"
    AGENT_UNREGISTER = "agent_unregister"
    AGENT_HEARTBEAT = "agent_heartbeat"
    AGENT_STATUS_UPDATE = "agent_status_update"
    
    # タスク管理
    TASK_ASSIGNMENT = "task_assignment"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETION = "task_completion"
    TASK_ERROR = "task_error"
    
    # エージェント間通信
    AGENT_MESSAGE = "agent_message"
    BROADCAST = "broadcast"
    
    # 協調作業
    WORKSPACE_UPDATE = "workspace_update"
    COORDINATION_REQUEST = "coordination_request"
    
    # ターミナル管理
    TERMINAL_SPAWN_REQUEST = "terminal_spawn_request"
    TERMINAL_SPAWN_RESPONSE = "terminal_spawn_response"
    TERMINAL_ASSIGN_AGENT = "terminal_assign_agent"
    TERMINAL_READY = "terminal_ready"
    TERMINAL_CLOSED = "terminal_closed"


@dataclass
class AgentMessage:
    """エージェント間メッセージ"""
    
    message_id: UUID = field(default_factory=uuid4)
    message_type: MessageType = MessageType.AGENT_MESSAGE
    from_agent: str = ""
    to_agent: Optional[str] = None  # Noneの場合はブロードキャスト
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[UUID] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "message_id": str(self.message_id),
            "message_type": self.message_type.value,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """辞書形式から復元"""
        return cls(
            message_id=UUID(data["message_id"]),
            message_type=MessageType(data["message_type"]),
            from_agent=data["from_agent"],
            to_agent=data.get("to_agent"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            data=data.get("data", {}),
            correlation_id=UUID(data["correlation_id"]) if data.get("correlation_id") else None
        )


@dataclass
class AgentRegistration:
    """エージェント登録情報"""
    
    agent_id: str
    agent_type: str  # "openhands", "claude_code"
    capabilities: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "version": self.version,
            "metadata": self.metadata
        }


@dataclass
class TerminalSpawnRequest:
    """ターミナル生成要求"""
    
    request_id: UUID = field(default_factory=uuid4)
    requester_agent_id: str = ""
    agent_type: str = ""  # 生成するターミナルで実行するエージェントタイプ
    agent_id: str = ""
    working_directory: Optional[str] = None
    launch_mode: str = "agent"  # "agent", "shell", "agentshell"
    additional_config: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": str(self.request_id),
            "requester_agent_id": self.requester_agent_id,
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "working_directory": self.working_directory,
            "launch_mode": self.launch_mode,
            "additional_config": self.additional_config,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TerminalSpawnRequest":
        return cls(
            request_id=UUID(data["request_id"]),
            requester_agent_id=data["requester_agent_id"],
            agent_type=data["agent_type"],
            agent_id=data["agent_id"],
            working_directory=data.get("working_directory"),
            launch_mode=data.get("launch_mode", "agent"),
            additional_config=data.get("additional_config", {}),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


@dataclass
class TerminalAssignment:
    """ターミナルエージェント割り当て"""
    
    terminal_id: str
    agent_type: str
    agent_id: str
    assignment_id: UUID = field(default_factory=uuid4)
    working_directory: Optional[str] = None
    environment_vars: Dict[str, str] = field(default_factory=dict)
    startup_command: Optional[str] = None
    capabilities_required: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "terminal_id": self.terminal_id,
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "assignment_id": str(self.assignment_id),
            "working_directory": self.working_directory,
            "environment_vars": self.environment_vars,
            "startup_command": self.startup_command,
            "capabilities_required": self.capabilities_required,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TerminalAssignment":
        return cls(
            terminal_id=data["terminal_id"],
            agent_type=data["agent_type"],
            agent_id=data["agent_id"],
            assignment_id=UUID(data["assignment_id"]),
            working_directory=data.get("working_directory"),
            environment_vars=data.get("environment_vars", {}),
            startup_command=data.get("startup_command"),
            capabilities_required=data.get("capabilities_required", []),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


@dataclass
class TerminalStatus:
    """ターミナル状態"""
    
    terminal_id: str
    status: str  # "initializing", "ready", "busy", "error", "closed"
    agent_assignment: Optional[TerminalAssignment] = None
    process_id: Optional[int] = None
    last_activity: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "terminal_id": self.terminal_id,
            "status": self.status,
            "agent_assignment": self.agent_assignment.to_dict() if self.agent_assignment else None,
            "process_id": self.process_id,
            "last_activity": self.last_activity.isoformat(),
            "error_message": self.error_message,
            "metadata": self.metadata
        }