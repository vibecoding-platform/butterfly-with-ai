import logging
from uuid import uuid4

from butterfly import utils
from butterfly.terminals.asyncio_terminal import AsyncioTerminal

log = logging.getLogger("butterfly.socket_handlers")

# Global storage for socket.io server instance
sio_instance = None


def set_sio_instance(sio):
    """Set the global socket.io server instance."""
    global sio_instance
    sio_instance = sio


async def connect(sid, environ):
    """Handle client connection."""
    log.info(f"Client connected: {sid}")
    await sio_instance.emit("connected", {"data": "Connected to Butterfly"}, room=sid)


async def disconnect(sid):
    """Handle client disconnection."""
    log.info(f"Client disconnected: {sid}")

    # Close any terminal sessions associated with this client
    # Note: In a full implementation, you'd track which terminals belong to which clients
    for session_id, terminal in list(AsyncioTerminal.sessions.items()):
        # For now, we'll close terminals when clients disconnect
        # In production, you might want more sophisticated session management
        if hasattr(terminal, "client_sid") and terminal.client_sid == sid:
            await terminal.close()


async def create_terminal(sid, data):
    """Create a new terminal session."""
    try:
        session_id = data.get("session", str(uuid4()))
        user_name = data.get("user", "")
        path = data.get("path", "")

        log.info(f"Creating terminal session {session_id} for client {sid}")
        log.debug(f"Terminal data: user={user_name}, path={path}")

        # Create connection info for Socket.IO
        # Get environ from Socket.IO if available, otherwise use defaults
        environ = getattr(sio_instance, 'environ', {}) if sio_instance else {}
        
        # Try to get more accurate socket information from the session
        # For Socket.IO, we need to extract the real client information
        socket_remote_addr = None
        if hasattr(sio_instance, 'manager') and hasattr(sio_instance.manager, 'get_session'):
            try:
                session = sio_instance.manager.get_session(sid)
                if session and 'transport' in session:
                    transport = session['transport']
                    if hasattr(transport, 'socket') and hasattr(transport.socket, 'getpeername'):
                        try:
                            peer = transport.socket.getpeername()
                            socket_remote_addr = peer[0]
                            # Update environ with real remote port
                            environ['REMOTE_PORT'] = str(peer[1])
                        except:
                            pass
            except:
                pass
        
        socket = utils.ConnectionInfo(environ, socket_remote_addr)

        # Determine user
        user = None
        if user_name:
            try:
                user = utils.User(name=user_name)
                log.debug(f"Using user: {user}")
            except LookupError:
                log.warning(f"Invalid user: {user_name}")
                user = None

        # Create terminal instance
        log.debug("Creating AsyncioTerminal instance")
        terminal = AsyncioTerminal(
            user=user,
            path=path,
            session=session_id,
            socket=socket,
            uri=f"ws://localhost/{session_id}",  # Simplified URI
            render_string=lambda template, **kwargs: template.encode(
                "utf-8"
            ),  # Simplified
            broadcast=lambda session, message: broadcast_to_session(session, message),
        )

        # Associate terminal with client
        terminal.client_sid = sid

        # Start the PTY
        log.debug("Starting PTY")
        await terminal.start_pty()
        log.info(f"PTY started successfully for session {session_id}")

        # Notify client that terminal is ready
        await sio_instance.emit(
            "terminal_ready", {"session": session_id, "status": "ready"}, room=sid
        )
        log.debug(f"Sent terminal_ready event to client {sid}")

    except Exception as e:
        log.error(f"Error creating terminal: {e}", exc_info=True)
        await sio_instance.emit("terminal_error", {"error": str(e)}, room=sid)


async def terminal_input(sid, data):
    """Handle input from client to terminal."""
    try:
        session_id = data.get("session")
        input_data = data.get("data", "")

        if session_id in AsyncioTerminal.sessions:
            terminal = AsyncioTerminal.sessions[session_id]
            await terminal.write(input_data)
        else:
            log.warning(f"Terminal session {session_id} not found")

    except Exception as e:
        log.error(f"Error handling terminal input: {e}")


async def terminal_resize(sid, data):
    """Handle terminal resize from client."""
    try:
        session_id = data.get("session")
        cols = data.get("cols", 80)
        rows = data.get("rows", 24)

        if session_id in AsyncioTerminal.sessions:
            terminal = AsyncioTerminal.sessions[session_id]
            await terminal.resize(cols, rows)
        else:
            log.warning(f"Terminal session {session_id} not found")

    except Exception as e:
        log.error(f"Error handling terminal resize: {e}")


def broadcast_to_session(session_id, message):
    """Broadcast message to all clients connected to a session."""
    if sio_instance:
        import asyncio
        
        if message is not None:
            # Terminal output - broadcast to all clients
            log.debug(f"Broadcasting terminal output for session {session_id}: {repr(message)}")
            asyncio.create_task(
                sio_instance.emit(
                    "terminal_output", {"session": session_id, "data": message}
                )
            )
        else:
            # Terminal closed
            log.info(f"Broadcasting terminal closed for session {session_id}")
            asyncio.create_task(
                sio_instance.emit("terminal_closed", {"session": session_id})
            )
    else:
        log.warning("sio_instance is None, cannot broadcast message")
