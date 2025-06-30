"""
AgentShell - エージェント協調プラットフォーム

OpenHandsやClaudeCodeなどの複数エージェントがWebSocket経由で
協調作業を行うためのプラットフォームを提供します。

主な機能:
- 複数エージェントの統合管理
- WebSocket経由のエージェント間通信
- 構造化された起動プロセス
- インタラクティブなエージェント制御
- リアルタイムなタスク調整

アーキテクチャ:
- Startup層: ブートストラップと依存関係管理
- Agent層: 各種エージェント実装
- Coordination層: エージェント間協調制御
- WebSocket層: 通信プロトコル実装
"""

__version__ = "0.3.0"
__author__ = "AetherTerm Team"

from .startup.bootstrap import BootstrapManager
from .agents.base import AgentInterface, AgentCapability, AgentStatus
from .websocket.client import WebSocketClient

__all__ = [
    "BootstrapManager",
    "AgentInterface", 
    "AgentCapability",
    "AgentStatus",
    "WebSocketClient",
]
