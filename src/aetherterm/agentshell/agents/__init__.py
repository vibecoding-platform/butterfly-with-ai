"""
AIエージェント統合モジュール

WebSocket経由でのエージェント間協調作業を支援
"""

from .base import AgentInterface, AgentCapability, AgentTask, AgentResult
from .claude_code import ClaudeCodeAgent
from .langchain_agent import LangChainAgent
from .manager import AgentManager
from .openhands import OpenHandsAgent

__all__ = [
    "AgentInterface",
    "AgentCapability", 
    "AgentTask",
    "AgentResult",
    "ClaudeCodeAgent",
    "LangChainAgent",
    "AgentManager",
    "OpenHandsAgent",
]
