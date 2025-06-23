"""
PTY Terminal Implementation
Provides direct PTY control with asyncio integration for workspace panes.
"""

import asyncio
import os
import pty
import signal
import struct
import termios
import fcntl
from logging import getLogger
from typing import Optional, Callable

log = getLogger("aetherterm.pty_terminal")


class PtyTerminal:
    """Direct PTY terminal implementation for workspace panes"""

    def __init__(
        self, terminal_id: str, socket_id: str, output_callback: Optional[Callable] = None
    ):
        """
        Initialize PTY terminal.

        Args:
            terminal_id: Unique identifier for this terminal
            socket_id: Initial socket ID for communication (can have multiple)
            output_callback: Function to call when output is received
        """
        self.terminal_id = terminal_id
        self.socket_ids = {socket_id} if socket_id else set()  # Support multiple socket IDs
        self.output_callbacks = (
            [output_callback] if output_callback else []
        )  # Support multiple callbacks

        # PTY state
        self.master_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self.reader_task: Optional[asyncio.Task] = None
        self.closed = False

        # Input control for multi-window
        self.primary_socket_id = socket_id  # Only this socket can send input
        self.input_lock = asyncio.Lock()  # Prevent concurrent input

        # Terminal settings
        self.cols = 80
        self.rows = 24

        log.info(f"PTY terminal created: {terminal_id} for socket {socket_id}")

    def add_socket(self, socket_id: str, output_callback: Optional[Callable] = None):
        """Add a socket to this terminal for multi-window support"""
        self.socket_ids.add(socket_id)
        # Only add callback if we don't have any callbacks yet (avoid duplicates)
        if output_callback and len(self.output_callbacks) == 0:
            self.output_callbacks.append(output_callback)
        log.info(
            f"Added socket {socket_id} to terminal {self.terminal_id} (total: {len(self.socket_ids)})"
        )

    def remove_socket(self, socket_id: str):
        """Remove a socket from this terminal"""
        self.socket_ids.discard(socket_id)

        # If removing the primary socket, assign a new primary
        if socket_id == self.primary_socket_id and self.socket_ids:
            new_primary = next(iter(self.socket_ids))
            self.primary_socket_id = new_primary
            log.info(
                f"Primary socket changed from {socket_id} to {new_primary} for terminal {self.terminal_id}"
            )

        # Note: We don't remove callbacks here as they might be shared
        log.info(
            f"Removed socket {socket_id} from terminal {self.terminal_id} (remaining: {len(self.socket_ids)})"
        )
        return len(self.socket_ids) == 0  # Return True if no sockets remain

    def has_socket(self, socket_id: str) -> bool:
        """Check if this terminal is connected to a socket"""
        return socket_id in self.socket_ids

    def set_primary_socket(self, socket_id: str):
        """Set which socket can send input"""
        if socket_id in self.socket_ids:
            self.primary_socket_id = socket_id
            log.info(f"Set primary socket for terminal {self.terminal_id}: {socket_id}")
        else:
            log.warning(
                f"Cannot set primary socket {socket_id} - not connected to terminal {self.terminal_id}"
            )

    def is_primary_socket(self, socket_id: str) -> bool:
        """Check if this is the primary socket for input"""
        return socket_id == self.primary_socket_id

    @property
    def socket_id(self) -> str:
        """Get first socket ID for compatibility"""
        return next(iter(self.socket_ids)) if self.socket_ids else ""

    async def start(self, cols: int = 80, rows: int = 24, shell: str = "/bin/bash") -> bool:
        """
        Start the PTY process.

        Args:
            cols: Terminal columns
            rows: Terminal rows
            shell: Shell to execute

        Returns:
            True if started successfully, False otherwise
        """
        if self.master_fd is not None:
            log.warning(f"PTY {self.terminal_id} already started")
            return False

        try:
            self.cols = cols
            self.rows = rows

            # Create PTY
            master_fd, slave_fd = pty.openpty()
            self.master_fd = master_fd

            # Set terminal size
            await self.resize(cols, rows)

            # Fork process
            pid = os.fork()

            if pid == 0:
                # Child process - execute shell
                try:
                    os.close(master_fd)  # Close master in child

                    # Make slave the controlling terminal
                    os.setsid()
                    os.dup2(slave_fd, 0)  # stdin
                    os.dup2(slave_fd, 1)  # stdout
                    os.dup2(slave_fd, 2)  # stderr
                    os.close(slave_fd)

                    # Set environment
                    env = os.environ.copy()
                    env.update(
                        {
                            "TERM": "xterm-256color",
                            "COLORTERM": "aetherterm",
                            "PS1": "\\u@\\h:\\w$ ",  # Basic prompt
                        }
                    )

                    # Execute shell
                    os.execvpe(shell, [shell, "-l"], env)

                except Exception as e:
                    log.error(f"Child process error: {e}")
                    os._exit(1)
            else:
                # Parent process
                self.pid = pid
                os.close(slave_fd)  # Close slave in parent

                # Set master fd to non-blocking
                fcntl.fcntl(master_fd, fcntl.F_SETFL, os.O_NONBLOCK)

                # Start reading from PTY
                self.reader_task = asyncio.create_task(self._read_output())

                log.info(f"PTY {self.terminal_id} started with PID {pid}")
                return True

        except Exception as e:
            log.error(f"Failed to start PTY {self.terminal_id}: {e}")
            await self.close()
            return False

    async def write(self, data: str, socket_id: Optional[str] = None) -> bool:
        """
        Write data to PTY.

        Args:
            data: Data to write
            socket_id: Socket ID sending the input (for validation)

        Returns:
            True if written successfully, False otherwise
        """
        if self.closed or self.master_fd is None:
            log.warning(f"Cannot write to closed PTY {self.terminal_id}")
            return False

        # Check if this socket is allowed to send input
        if socket_id and not self.is_primary_socket(socket_id):
            log.debug(
                f"Ignoring input from non-primary socket {socket_id} to terminal {self.terminal_id}"
            )
            return False

        async with self.input_lock:
            try:
                # Write to PTY in executor to avoid blocking
                await asyncio.get_event_loop().run_in_executor(
                    None, os.write, self.master_fd, data.encode("utf-8")
                )
                log.debug(f"PTY {self.terminal_id} wrote: {data!r} from socket {socket_id}")
                return True

            except Exception as e:
                log.error(f"Error writing to PTY {self.terminal_id}: {e}")
                await self.close()
                return False

    async def resize(self, cols: int, rows: int) -> bool:
        """
        Resize the PTY.

        Args:
            cols: Terminal columns
            rows: Terminal rows

        Returns:
            True if resized successfully, False otherwise
        """
        if self.closed or self.master_fd is None:
            return False

        try:
            self.cols = cols
            self.rows = rows

            # Set window size
            s = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, s)

            log.info(f"PTY {self.terminal_id} resized to ({cols}, {rows})")
            return True

        except Exception as e:
            log.error(f"Error resizing PTY {self.terminal_id}: {e}")
            return False

    async def close(self):
        """Close the PTY and clean up resources"""
        if self.closed:
            return

        self.closed = True
        log.info(f"Closing PTY {self.terminal_id}")

        # Cancel reader task
        if self.reader_task and not self.reader_task.done():
            self.reader_task.cancel()
            try:
                await self.reader_task
            except asyncio.CancelledError:
                pass

        # Close file descriptor
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except Exception as e:
                log.debug(f"Error closing PTY fd: {e}")
            self.master_fd = None

        # Terminate process
        if self.pid is not None:
            try:
                # Send SIGTERM first
                os.kill(self.pid, signal.SIGTERM)

                # Wait for graceful termination
                for _ in range(50):  # Wait up to 5 seconds
                    try:
                        pid, status = os.waitpid(self.pid, os.WNOHANG)
                        if pid != 0:  # Process has exited
                            log.info(f"PTY {self.terminal_id} process exited gracefully")
                            break
                    except OSError:
                        # Process doesn't exist anymore
                        break
                    await asyncio.sleep(0.1)
                else:
                    # Force kill if still alive
                    try:
                        log.warning(f"Force killing PTY {self.terminal_id} process")
                        os.kill(self.pid, signal.SIGKILL)
                        os.waitpid(self.pid, 0)
                    except OSError:
                        pass

            except Exception as e:
                log.error(f"Error terminating PTY {self.terminal_id} process: {e}")

            self.pid = None

    async def _read_output(self):
        """Continuously read from PTY and send to output callback"""
        try:
            while not self.closed and self.master_fd is not None:
                try:
                    # Check if child process is still alive
                    if self.pid is not None:
                        try:
                            pid, status = os.waitpid(self.pid, os.WNOHANG)
                            if pid != 0:  # Process has exited
                                log.info(
                                    f"PTY {self.terminal_id} child process exited with status {status}"
                                )
                                break
                        except OSError:
                            # Process doesn't exist anymore
                            break

                    # Read from PTY with timeout
                    data = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, self._read_pty_data),
                        timeout=0.1,
                    )

                    if data:
                        # Decode and send output
                        try:
                            text = data.decode("utf-8", "replace")
                            await self._safe_callbacks(text)
                            log.debug(f"PTY {self.terminal_id} output: {text!r}")
                        except Exception as e:
                            log.error(f"Error decoding PTY output: {e}")

                except asyncio.TimeoutError:
                    # No data available, continue
                    continue
                except Exception as e:
                    log.error(f"Error reading from PTY {self.terminal_id}: {e}")
                    break

        except Exception as e:
            log.error(f"PTY {self.terminal_id} reader task error: {e}")
        finally:
            await self.close()

    def _read_pty_data(self) -> bytes:
        """Read data from PTY (blocking operation for executor)"""
        try:
            return os.read(self.master_fd, 4096)
        except (OSError, IOError):
            return b""

    async def _safe_callbacks(self, data: str):
        """Safely call all output callbacks"""
        for callback in self.output_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                log.error(f"Error in output callback: {e}")

    @property
    def is_alive(self) -> bool:
        """Check if PTY is alive"""
        if self.closed or self.pid is None:
            return False

        try:
            # Send signal 0 to check if process exists
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False

    def get_status(self) -> dict:
        """Get PTY status information"""
        return {
            "terminal_id": self.terminal_id,
            "socket_ids": list(self.socket_ids),
            "socket_count": len(self.socket_ids),
            "primary_socket_id": self.primary_socket_id,
            "pid": self.pid,
            "master_fd": self.master_fd,
            "cols": self.cols,
            "rows": self.rows,
            "closed": self.closed,
            "alive": self.is_alive,
        }


class PtyTerminalManager:
    """Manager for multiple PTY terminals"""

    def __init__(self):
        self.terminals: dict[str, PtyTerminal] = {}
        self.socket_terminals: dict[str, set[str]] = {}  # socket_id -> terminal_ids

    async def create_terminal(
        self, terminal_id: str, socket_id: str, output_callback: Optional[Callable] = None
    ) -> Optional[PtyTerminal]:
        """Create a new PTY terminal or add socket to existing terminal"""
        if terminal_id in self.terminals:
            # Terminal exists, add this socket to it
            terminal = self.terminals[terminal_id]
            terminal.add_socket(socket_id, output_callback)

            # Track by socket
            if socket_id not in self.socket_terminals:
                self.socket_terminals[socket_id] = set()
            self.socket_terminals[socket_id].add(terminal_id)

            log.info(f"Added socket {socket_id} to existing PTY terminal {terminal_id}")
            return terminal

        # Create new terminal - only one callback needed for all sockets
        terminal = PtyTerminal(terminal_id, socket_id, output_callback)
        self.terminals[terminal_id] = terminal

        # Track by socket
        if socket_id not in self.socket_terminals:
            self.socket_terminals[socket_id] = set()
        self.socket_terminals[socket_id].add(terminal_id)

        log.info(f"Created new PTY terminal {terminal_id} for socket {socket_id}")
        return terminal

    async def remove_terminal(self, terminal_id: str):
        """Remove and close a PTY terminal"""
        if terminal_id not in self.terminals:
            return

        terminal = self.terminals[terminal_id]
        socket_ids = list(terminal.socket_ids)

        # Close terminal
        await terminal.close()

        # Remove from tracking
        del self.terminals[terminal_id]
        for socket_id in socket_ids:
            if socket_id in self.socket_terminals:
                self.socket_terminals[socket_id].discard(terminal_id)
                if not self.socket_terminals[socket_id]:
                    del self.socket_terminals[socket_id]

        log.info(f"Removed PTY terminal {terminal_id} (was connected to {len(socket_ids)} sockets)")

    async def remove_socket_from_terminal(self, terminal_id: str, socket_id: str):
        """Remove a socket from a terminal, close terminal if no sockets remain"""
        if terminal_id not in self.terminals:
            return

        terminal = self.terminals[terminal_id]
        no_sockets_remain = terminal.remove_socket(socket_id)

        # Remove from socket tracking
        if socket_id in self.socket_terminals:
            self.socket_terminals[socket_id].discard(terminal_id)
            if not self.socket_terminals[socket_id]:
                del self.socket_terminals[socket_id]

        # If no sockets remain, close the terminal
        if no_sockets_remain:
            await self.remove_terminal(terminal_id)
            log.info(f"Closed terminal {terminal_id} as no sockets remain")
        else:
            log.info(
                f"Removed socket {socket_id} from terminal {terminal_id} ({len(terminal.socket_ids)} sockets remain)"
            )

    async def cleanup_socket_terminals(self, socket_id: str):
        """Clean up all terminals for a socket"""
        if socket_id not in self.socket_terminals:
            return

        terminal_ids = list(self.socket_terminals[socket_id])
        for terminal_id in terminal_ids:
            await self.remove_socket_from_terminal(terminal_id, socket_id)

        log.info(f"Cleaned up {len(terminal_ids)} terminals for socket {socket_id}")

    def get_terminal(self, terminal_id: str) -> Optional[PtyTerminal]:
        """Get a PTY terminal by ID"""
        return self.terminals.get(terminal_id)

    def get_socket_terminals(self, socket_id: str) -> list[PtyTerminal]:
        """Get all terminals for a socket"""
        if socket_id not in self.socket_terminals:
            return []
        return [
            self.terminals[tid] for tid in self.socket_terminals[socket_id] if tid in self.terminals
        ]

    async def close_all(self):
        """Close all terminals"""
        terminal_ids = list(self.terminals.keys())
        for terminal_id in terminal_ids:
            await self.remove_terminal(terminal_id)

        log.info(f"Closed all {len(terminal_ids)} PTY terminals")


# Global PTY terminal manager instance
_pty_manager: Optional[PtyTerminalManager] = None


def get_pty_manager() -> PtyTerminalManager:
    """Get the global PTY terminal manager"""
    global _pty_manager
    if _pty_manager is None:
        _pty_manager = PtyTerminalManager()
    return _pty_manager
