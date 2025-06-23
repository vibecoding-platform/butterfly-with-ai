"""
Terminal Configuration
Provides configuration options for terminal implementations.
"""

import os
from typing import Optional
from enum import Enum

from aetherterm.agentserver.terminals.terminal_factory import TerminalType


class TerminalConfig:
    """Configuration for terminal implementations"""

    def __init__(self):
        self._default_type = self._load_default_type()

    def _load_default_type(self) -> TerminalType:
        """Load default terminal type from environment or config"""
        # Check environment variable first
        env_type = os.environ.get("AETHERTERM_TERMINAL_TYPE", "").lower()

        if env_type == "pty":
            return TerminalType.PTY
        elif env_type == "asyncio":
            return TerminalType.ASYNCIO

        # Default to PTY for new installations
        return TerminalType.PTY

    def get_default_type(self) -> TerminalType:
        """Get the default terminal type"""
        return self._default_type

    def set_default_type(self, terminal_type: TerminalType):
        """Set the default terminal type"""
        self._default_type = terminal_type

    def get_terminal_config(self, terminal_type: Optional[TerminalType] = None) -> dict:
        """Get configuration for specific terminal type"""
        terminal_type = terminal_type or self._default_type

        base_config = {
            "type": terminal_type.value,
            "default_shell": os.environ.get("AETHERTERM_DEFAULT_SHELL", "/bin/bash"),
            "default_cols": int(os.environ.get("AETHERTERM_DEFAULT_COLS", "80")),
            "default_rows": int(os.environ.get("AETHERTERM_DEFAULT_ROWS", "24")),
        }

        if terminal_type == TerminalType.PTY:
            base_config.update(
                {
                    "shell_args": ["-l"],
                    "environment": {
                        "TERM": "xterm-256color",
                        "COLORTERM": "aetherterm",
                    },
                }
            )
        elif terminal_type == TerminalType.ASYNCIO:
            base_config.update(
                {
                    "login_required": os.environ.get("AETHERTERM_LOGIN_REQUIRED", "false").lower()
                    == "true",
                    "pam_profile": os.environ.get("AETHERTERM_PAM_PROFILE", ""),
                }
            )

        return base_config

    def is_type_available(self, terminal_type: TerminalType) -> bool:
        """Check if a terminal type is available"""
        if terminal_type == TerminalType.PTY:
            # PTY is always available on Unix systems
            return hasattr(os, "fork")
        elif terminal_type == TerminalType.ASYNCIO:
            # AsyncioTerminal requires additional dependencies
            try:
                from aetherterm.agentserver.terminals.asyncio_terminal import AsyncioTerminal

                return True
            except ImportError:
                return False
        return False

    def get_available_types(self) -> list[TerminalType]:
        """Get list of available terminal types"""
        available = []
        for terminal_type in TerminalType:
            if self.is_type_available(terminal_type):
                available.append(terminal_type)
        return available

    def validate_config(self) -> dict:
        """Validate current configuration and return status"""
        status = {
            "valid": True,
            "default_type": self._default_type.value,
            "available_types": [t.value for t in self.get_available_types()],
            "warnings": [],
            "errors": [],
        }

        # Check if default type is available
        if not self.is_type_available(self._default_type):
            status["valid"] = False
            status["errors"].append(
                f"Default terminal type '{self._default_type.value}' is not available"
            )

        # Check shell availability
        default_shell = os.environ.get("AETHERTERM_DEFAULT_SHELL", "/bin/bash")
        if not os.path.exists(default_shell):
            status["warnings"].append(f"Default shell '{default_shell}' not found")

        return status


# Global terminal config instance
_terminal_config: Optional[TerminalConfig] = None


def get_terminal_config() -> TerminalConfig:
    """Get the global terminal configuration"""
    global _terminal_config
    if _terminal_config is None:
        _terminal_config = TerminalConfig()
    return _terminal_config


def set_default_terminal_type_from_config():
    """Apply terminal configuration to factory"""
    from aetherterm.agentserver.terminals.terminal_factory import get_terminal_factory

    config = get_terminal_config()
    factory = get_terminal_factory()
    factory.set_default_type(config.get_default_type())


def get_terminal_status() -> dict:
    """Get comprehensive terminal status information"""
    config = get_terminal_config()

    from aetherterm.agentserver.terminals.terminal_factory import get_terminal_factory

    factory = get_terminal_factory()

    return {
        "config": config.validate_config(),
        "factory_stats": factory.get_stats(),
        "environment": {
            "AETHERTERM_TERMINAL_TYPE": os.environ.get("AETHERTERM_TERMINAL_TYPE", "unset"),
            "AETHERTERM_DEFAULT_SHELL": os.environ.get("AETHERTERM_DEFAULT_SHELL", "/bin/bash"),
            "AETHERTERM_DEFAULT_COLS": os.environ.get("AETHERTERM_DEFAULT_COLS", "80"),
            "AETHERTERM_DEFAULT_ROWS": os.environ.get("AETHERTERM_DEFAULT_ROWS", "24"),
        },
    }
