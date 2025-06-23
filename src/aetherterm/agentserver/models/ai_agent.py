"""
AI Agent models for agent-to-agent conversation system
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from uuid import uuid4


class AgentType(Enum):
    """Types of AI agents with different specializations"""

    DEVOPS = "devops"
    CODE_REVIEW = "code_review"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    GENERAL = "general"


class AgentMessageType(Enum):
    """Types of messages in agent conversations"""

    STATEMENT = "statement"
    QUESTION = "question"
    SUGGESTION = "suggestion"
    ANALYSIS = "analysis"
    AGREEMENT = "agreement"
    DISAGREEMENT = "disagreement"


@dataclass
class AgentMemory:
    """Memory item for AI agents"""

    id: str = field(default_factory=lambda: f"memory-{uuid4().hex[:11]}")
    content: str = ""
    context: str = ""
    importance: float = 0.5  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)


@dataclass
class AIAgent:
    """AI Agent with personality and memory"""

    id: str = field(default_factory=lambda: f"agent-{uuid4().hex[:11]}")
    name: str = ""
    agent_type: AgentType = AgentType.GENERAL
    persona: str = ""
    is_active: bool = False
    current_context: str = ""
    memory: List[AgentMemory] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active_at: datetime = field(default_factory=datetime.now)

    # Agent configuration
    response_style: str = "professional"  # professional, casual, technical
    expertise_level: float = 0.8  # 0.0 to 1.0
    collaboration_preference: str = "cooperative"  # cooperative, challenging, supportive

    @classmethod
    def create_devops_agent(cls, name: str = "DevOps Agent") -> "AIAgent":
        """Create a DevOps specialized agent"""
        return cls(
            name=name,
            agent_type=AgentType.DEVOPS,
            persona="Experienced DevOps engineer focused on system reliability, automation, and operational excellence. "
            "Analyzes system performance, deployment pipelines, and infrastructure concerns.",
            response_style="technical",
            expertise_level=0.9,
        )

    @classmethod
    def create_security_agent(cls, name: str = "Security Agent") -> "AIAgent":
        """Create a Security specialized agent"""
        return cls(
            name=name,
            agent_type=AgentType.SECURITY,
            persona="Cybersecurity expert specialized in vulnerability assessment, secure coding practices, "
            "and threat analysis. Always considers security implications of system changes.",
            response_style="cautious",
            expertise_level=0.85,
            collaboration_preference="challenging",
        )

    @classmethod
    def create_code_review_agent(cls, name: str = "Code Review Agent") -> "AIAgent":
        """Create a Code Review specialized agent"""
        return cls(
            name=name,
            agent_type=AgentType.CODE_REVIEW,
            persona="Senior software engineer focused on code quality, best practices, and maintainability. "
            "Reviews code for bugs, performance issues, and adherence to standards.",
            response_style="constructive",
            expertise_level=0.88,
        )

    def add_memory(
        self, content: str, context: str = "", importance: float = 0.5, tags: List[str] = None
    ):
        """Add new memory to agent"""
        memory = AgentMemory(
            content=content, context=context, importance=importance, tags=tags or []
        )
        self.memory.append(memory)

        # Keep only most important/recent memories (limit to 100)
        if len(self.memory) > 100:
            self.memory.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
            self.memory = self.memory[:100]

    def get_relevant_memories(self, context: str, limit: int = 5) -> List[AgentMemory]:
        """Get memories relevant to current context"""
        # Simple relevance scoring based on keyword matching
        relevant = []
        context_words = set(context.lower().split())

        for memory in self.memory:
            memory_words = set(memory.content.lower().split())
            relevance = len(context_words.intersection(memory_words)) / len(
                context_words.union(memory_words)
            )
            if relevance > 0.1:  # Threshold for relevance
                relevant.append((memory, relevance))

        # Sort by relevance and importance
        relevant.sort(key=lambda x: (x[1], x[0].importance), reverse=True)
        return [mem for mem, _ in relevant[:limit]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "agentType": self.agent_type.value,
            "persona": self.persona,
            "isActive": self.is_active,
            "currentContext": self.current_context,
            "createdAt": self.created_at.isoformat(),
            "lastActiveAt": self.last_active_at.isoformat(),
            "responseStyle": self.response_style,
            "expertiseLevel": self.expertise_level,
            "collaborationPreference": self.collaboration_preference,
            "memoryCount": len(self.memory),
        }


@dataclass
class AgentMessage:
    """Message in agent-to-agent conversation"""

    id: str = field(default_factory=lambda: f"msg-{uuid4().hex[:11]}")
    conversation_id: str = ""
    agent_id: str = ""
    agent_name: str = ""
    content: str = ""
    message_type: AgentMessageType = AgentMessageType.STATEMENT
    references: List[str] = field(default_factory=list)  # terminal commands, files, etc.
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "id": self.id,
            "conversationId": self.conversation_id,
            "agentId": self.agent_id,
            "agentName": self.agent_name,
            "content": self.content,
            "messageType": self.message_type.value,
            "references": self.references,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class AgentConversation:
    """Conversation between multiple AI agents"""

    id: str = field(default_factory=lambda: f"conv-{uuid4().hex[:11]}")
    tab_id: str = ""
    title: str = ""
    topic: str = ""
    participants: List[AIAgent] = field(default_factory=list)
    messages: List[AgentMessage] = field(default_factory=list)
    is_active: bool = False
    user_observing: bool = True
    auto_continue: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_message_at: datetime = field(default_factory=datetime.now)

    def add_participant(self, agent: AIAgent):
        """Add agent to conversation"""
        if agent not in self.participants:
            self.participants.append(agent)
            agent.is_active = True
            agent.last_active_at = datetime.now()

    def remove_participant(self, agent_id: str):
        """Remove agent from conversation"""
        self.participants = [a for a in self.participants if a.id != agent_id]

    def add_message(self, message: AgentMessage):
        """Add message to conversation"""
        message.conversation_id = self.id
        self.messages.append(message)
        self.last_message_at = datetime.now()

    def get_recent_messages(self, limit: int = 10) -> List[AgentMessage]:
        """Get recent messages from conversation"""
        return self.messages[-limit:] if self.messages else []

    def get_conversation_context(self) -> str:
        """Get conversation context as string"""
        if not self.messages:
            return f"Topic: {self.topic}"

        recent_messages = self.get_recent_messages(5)
        context_parts = [f"Topic: {self.topic}"]

        for msg in recent_messages:
            context_parts.append(f"{msg.agent_name}: {msg.content}")

        return "\n".join(context_parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary"""
        return {
            "id": self.id,
            "tabId": self.tab_id,
            "title": self.title,
            "topic": self.topic,
            "participants": [agent.to_dict() for agent in self.participants],
            "messages": [msg.to_dict() for msg in self.messages],
            "isActive": self.is_active,
            "userObserving": self.user_observing,
            "autoContinue": self.auto_continue,
            "createdAt": self.created_at.isoformat(),
            "lastMessageAt": self.last_message_at.isoformat(),
            "messageCount": len(self.messages),
        }
