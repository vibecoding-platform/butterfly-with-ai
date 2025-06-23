"""
Terminal Factory
Provides switchable terminal implementations for different use cases.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Callable, Any, Dict

from .pty_terminal import PtyTerminal, get_pty_manager
from .asyncio_terminal import AsyncioTerminal

log = logging.getLogger("aetherterm.terminal_factory")


class TerminalType(Enum):
    """Available terminal implementation types"""

    PTY = "pty"  # Direct PTY implementation
    ASYNCIO = "asyncio"  # Original AsyncioTerminal implementation


class TerminalInterface(ABC):
    """Abstract interface for terminal implementations"""

    @abstractmethod
    async def start(self, cols: int = 80, rows: int = 24, **kwargs) -> bool:
        """Start the terminal"""
        pass

    @abstractmethod
    async def write(self, data: str) -> bool:
        """Write data to terminal"""
        pass

    @abstractmethod
    async def resize(self, cols: int, rows: int) -> bool:
        """Resize terminal"""
        pass

    @abstractmethod
    async def close(self):
        """Close terminal"""
        pass

    @abstractmethod
    def get_status(self) -> dict:
        """Get terminal status"""
        pass


class PtyTerminalWrapper(TerminalInterface):
    """Wrapper for PtyTerminal to implement TerminalInterface"""

    def __init__(
        self, terminal_id: str, socket_id: str, output_callback: Optional[Callable] = None
    ):
        self.terminal_id = terminal_id
        self.socket_id = socket_id
        self.output_callback = output_callback
        self._pty_terminal: Optional[PtyTerminal] = None

    def add_socket(self, socket_id: str, output_callback: Optional[Callable] = None):
        """Add a socket to this terminal for multi-window support"""
        if self._pty_terminal:
            self._pty_terminal.add_socket(socket_id, output_callback)

    def remove_socket(self, socket_id: str) -> bool:
        """Remove a socket from this terminal, return True if no sockets remain"""
        if self._pty_terminal:
            return self._pty_terminal.remove_socket(socket_id)
        return True

    def has_socket(self, socket_id: str) -> bool:
        """Check if this terminal is connected to a socket"""
        if self._pty_terminal:
            return self._pty_terminal.has_socket(socket_id)
        return False

    async def start(self, cols: int = 80, rows: int = 24, **kwargs) -> bool:
        """Start PTY terminal"""
        manager = get_pty_manager()
        self._pty_terminal = await manager.create_terminal(
            self.terminal_id, self.socket_id, self.output_callback
        )

        if self._pty_terminal:
            shell = kwargs.get("shell", "/bin/bash")
            return await self._pty_terminal.start(cols, rows, shell)
        return False

    async def write(self, data: str, socket_id: Optional[str] = None) -> bool:
        """Write data to PTY terminal"""
        if self._pty_terminal:
            return await self._pty_terminal.write(data, socket_id)
        return False

    async def resize(self, cols: int, rows: int) -> bool:
        """Resize PTY terminal"""
        if self._pty_terminal:
            return await self._pty_terminal.resize(cols, rows)
        return False

    async def close(self):
        """Close PTY terminal"""
        if self._pty_terminal:
            manager = get_pty_manager()
            await manager.remove_terminal(self.terminal_id)
            self._pty_terminal = None

    def get_status(self) -> dict:
        """Get PTY terminal status"""
        if self._pty_terminal:
            status = self._pty_terminal.get_status()
            status["type"] = "pty"
            return status
        return {"type": "pty", "status": "not_started"}


class AsyncioTerminalWrapper(TerminalInterface):
    """Wrapper for AsyncioTerminal to implement TerminalInterface"""

    def __init__(
        self,
        terminal_id: str,
        socket_id: str,
        output_callback: Optional[Callable] = None,
        user=None,
        path=None,
        socket=None,
        uri=None,
        render_string=None,
        broadcast=None,
        login=None,
        pam_profile=None,
    ):
        self.terminal_id = terminal_id
        self.socket_id = socket_id
        self.output_callback = output_callback

        # AsyncioTerminal parameters
        self.user = user
        self.path = path
        self.socket = socket
        self.uri = uri
        self.render_string = render_string
        self.broadcast = broadcast
        self.login = login
        self.pam_profile = pam_profile
        self._asyncio_terminal: Optional[AsyncioTerminal] = None

    async def start(self, cols: int = 80, rows: int = 24, **kwargs) -> bool:
        """Start AsyncioTerminal"""
        try:
            # Create AsyncioTerminal instance
            self._asyncio_terminal = AsyncioTerminal(
                user=self.user,
                path=self.path,
                session=self.terminal_id,
                socket=self.socket,
                uri=self.uri,
                render_string=self.render_string,
                broadcast=self.broadcast,
                login=self.login,
                pam_profile=self.pam_profile,
            )

            log.debug(f"AsyncioTerminalWrapper: Starting PTY for {self.terminal_id}")

            # Start PTY
            await self._asyncio_terminal.start_pty()

            log.debug(f"AsyncioTerminalWrapper: PTY started for {self.terminal_id}")

            # Resize to requested size
            await self._asyncio_terminal.resize(cols, rows)

            # Send initial prompt/welcome message to verify output is working
            import asyncio

            await asyncio.sleep(0.1)  # Give PTY time to initialize

            log.debug(f"AsyncioTerminalWrapper: Initialization complete for {self.terminal_id}")

            return True

        except Exception as e:
            log.error(f"Failed to start AsyncioTerminal {self.terminal_id}: {e}")
            return False

    async def write(self, data: str, socket_id: Optional[str] = None) -> bool:
        """Write data to AsyncioTerminal"""
        if self._asyncio_terminal:
            try:
                log.info(f"Writing to AsyncioTerminal {self.terminal_id}: {repr(data)}")
                await self._asyncio_terminal.write(data)
                return True
            except Exception as e:
                log.error(f"Error writing to AsyncioTerminal {self.terminal_id}: {e}")
                return False
        else:
            log.warning(f"No AsyncioTerminal instance for {self.terminal_id}")
        return False

    async def resize(self, cols: int, rows: int) -> bool:
        """Resize AsyncioTerminal"""
        if self._asyncio_terminal:
            try:
                await self._asyncio_terminal.resize(cols, rows)
                return True
            except Exception as e:
                log.error(f"Error resizing AsyncioTerminal {self.terminal_id}: {e}")
                return False
        return False

    async def close(self):
        """Close AsyncioTerminal"""
        if self._asyncio_terminal:
            try:
                await self._asyncio_terminal.close()
            except Exception as e:
                log.error(f"Error closing AsyncioTerminal {self.terminal_id}: {e}")
            self._asyncio_terminal = None

    def get_status(self) -> dict:
        """Get AsyncioTerminal status"""
        if self._asyncio_terminal:
            return {
                "type": "asyncio",
                "terminal_id": self.terminal_id,
                "socket_id": self.socket_id,
                "session": self._asyncio_terminal.session,
                "closed": self._asyncio_terminal.closed,
                "pid": getattr(self._asyncio_terminal, "pid", None),
                "fd": self._asyncio_terminal.fd,
            }
        return {"type": "asyncio", "status": "not_started"}


class TerminalFactory:
    """Factory for creating different types of terminals"""

    def __init__(self, default_type: TerminalType = TerminalType.PTY):
        self.default_type = default_type
        self.active_terminals: Dict[str, TerminalInterface] = {}

    async def create_terminal(
        self,
        terminal_id: str,
        socket_id: str,
        terminal_type: Optional[TerminalType] = None,
        output_callback: Optional[Callable] = None,
        **kwargs,
    ) -> Optional[TerminalInterface]:
        """
        Create a terminal of the specified type.

        Args:
            terminal_id: Unique terminal identifier
            socket_id: Socket identifier
            terminal_type: Type of terminal to create (defaults to factory default)
            output_callback: Callback for terminal output
            **kwargs: Additional arguments for terminal creation

        Returns:
            Terminal instance or None if creation failed
        """
        if terminal_id in self.active_terminals:
            # Terminal exists, add this socket to it
            existing_terminal = self.active_terminals[terminal_id]
            if hasattr(existing_terminal, "add_socket"):
                existing_terminal.add_socket(socket_id, output_callback)
                log.info(f"Added socket {socket_id} to existing terminal {terminal_id}")
            return existing_terminal

        terminal_type = terminal_type or self.default_type

        try:
            if terminal_type == TerminalType.PTY:
                terminal = PtyTerminalWrapper(terminal_id, socket_id, output_callback)
            elif terminal_type == TerminalType.ASYNCIO:
                terminal = AsyncioTerminalWrapper(terminal_id, socket_id, output_callback, **kwargs)
            else:
                log.error(f"Unknown terminal type: {terminal_type}")
                return None

            self.active_terminals[terminal_id] = terminal
            log.info(f"Created {terminal_type.value} terminal {terminal_id}")
            return terminal

        except Exception as e:
            log.error(f"Failed to create {terminal_type.value} terminal {terminal_id}: {e}")
            return None

    async def remove_terminal(self, terminal_id: str):
        """Remove and close a terminal"""
        if terminal_id not in self.active_terminals:
            return

        terminal = self.active_terminals[terminal_id]
        try:
            await terminal.close()
        except Exception as e:
            log.error(f"Error closing terminal {terminal_id}: {e}")

        del self.active_terminals[terminal_id]
        log.info(f"Removed terminal {terminal_id}")

    async def cleanup_socket_terminals(self, socket_id: str):
        """Clean up all terminals for a socket"""
        terminals_to_remove = [
            terminal_id
            for terminal_id, terminal in self.active_terminals.items()
            if terminal.socket_id == socket_id
        ]

        for terminal_id in terminals_to_remove:
            await self.remove_terminal(terminal_id)

        # Also cleanup PTY manager terminals
        manager = get_pty_manager()
        await manager.cleanup_socket_terminals(socket_id)

        log.info(f"Cleaned up {len(terminals_to_remove)} terminals for socket {socket_id}")

    def get_terminal(self, terminal_id: str) -> Optional[TerminalInterface]:
        """Get a terminal by ID"""
        return self.active_terminals.get(terminal_id)

    def get_socket_terminals(self, socket_id: str) -> list[TerminalInterface]:
        """Get all terminals for a socket"""
        return [
            terminal
            for terminal in self.active_terminals.values()
            if terminal.socket_id == socket_id
        ]

    async def close_all(self):
        """Close all active terminals"""
        terminal_ids = list(self.active_terminals.keys())
        for terminal_id in terminal_ids:
            await self.remove_terminal(terminal_id)

        # Also close PTY manager terminals
        manager = get_pty_manager()
        await manager.close_all()

        log.info(f"Closed all {len(terminal_ids)} terminals")

    def set_default_type(self, terminal_type: TerminalType):
        """Set the default terminal type"""
        self.default_type = terminal_type
        log.info(f"Set default terminal type to {terminal_type.value}")

    def get_stats(self) -> dict:
        """Get factory statistics"""
        terminal_types = {}
        for terminal in self.active_terminals.values():
            status = terminal.get_status()
            term_type = status.get("type", "unknown")
            terminal_types[term_type] = terminal_types.get(term_type, 0) + 1

        return {
            "total_terminals": len(self.active_terminals),
            "terminal_types": terminal_types,
            "default_type": self.default_type.value,
        }


# Global terminal factory instance
_terminal_factory: Optional[TerminalFactory] = None


def get_terminal_factory() -> TerminalFactory:
    """Get the global terminal factory"""
    global _terminal_factory
    if _terminal_factory is None:
        _terminal_factory = TerminalFactory()
    return _terminal_factory


def set_default_terminal_type(terminal_type: TerminalType):
    """Set the default terminal type globally"""
    factory = get_terminal_factory()
    factory.set_default_type(terminal_type)
