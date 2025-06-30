"""
WebSocket Handlers Package - Interface Layer

Organized handlers for different functionality areas.
"""

from .agent_handlers import (
    agent_hello,
    agent_start_request,
    control_message,
    spec_query,
    spec_upload,
)
from .terminal_handlers import (
    connect,
    create_terminal,
    disconnect,
    resume_workspace,
    terminal_input,
    terminal_resize,
)

__all__ = [
    # Terminal handlers
    "connect",
    "disconnect",
    "create_terminal",
    "resume_workspace",
    "terminal_input",
    "terminal_resize",
    # Agent handlers
    "agent_start_request",
    "agent_hello",
    "spec_upload",
    "spec_query",
    "control_message",
]
