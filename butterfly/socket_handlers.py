import logging
from uuid import uuid4

from dependency_injector.wiring import Provide, inject

from butterfly import utils
from butterfly.containers import ApplicationContainer
from butterfly.terminals.asyncio_terminal import AsyncioTerminal
from butterfly.utils import User

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

    # Remove client from any terminal sessions and close if no clients remain
    for session_id, terminal in list(AsyncioTerminal.sessions.items()):
        if hasattr(terminal, "client_sids") and sid in terminal.client_sids:
            terminal.client_sids.discard(sid)
            log.info(f"Removed client {sid} from terminal session {session_id}")
            # If no clients remain, close the terminal
            if not terminal.client_sids:
                log.info(f"No clients remaining for session {session_id}, closing terminal")
                await terminal.close()


@inject
async def create_terminal(
    sid,
    data,
    config_login: bool=Provide[ApplicationContainer.config.login],
    config_pam_profile: str=Provide[ApplicationContainer.config.pam_profile],
    config_uri_root_path: str=Provide[ApplicationContainer.config.uri_root_path],
):
    """Handle the creation of a new terminal session."""
    try:
        session_id = data.get("session", str(uuid4()))
        user_name = data.get("user", "")
        path = data.get("path", "")

        log.info(f"Creating terminal session {session_id} for client {sid}")
        log.debug(f"Terminal data: user={user_name}, path={path}")

        # Check if session already exists and is still active
        if session_id in AsyncioTerminal.sessions:
            existing_terminal = AsyncioTerminal.sessions[session_id]
            if not existing_terminal.closed:
                log.info(f"Reusing existing terminal session {session_id}")
                # Add this client to the existing terminal's client set
                existing_terminal.client_sids.add(sid)
                # Send terminal history to new client
                if existing_terminal.history:
                    await sio_instance.emit(
                        "terminal_output",
                        {"session": session_id, "data": existing_terminal.history},
                        room=sid
                    )
                # Notify client that terminal is ready
                await sio_instance.emit(
                    "terminal_ready", {"session": session_id, "status": "ready"}, room=sid
                )
                return

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
        terminal_user = None
        if user_name:
            try:
                terminal_user = User(name=user_name)
                log.debug(f"Using user: {terminal_user}")
            except LookupError:
                log.warning(f"Invalid user: {user_name}, falling back to default user.")
                terminal_user = User()  # Fallback to current user

        # Create terminal instance directly (not using factory since it has issues)
        log.debug("Creating AsyncioTerminal instance")
        terminal_instance = AsyncioTerminal(
            user=terminal_user,
            path=path,
            session=session_id,
            socket=socket,
            uri=f"http://{socket.local_addr}:{socket.local_port}{config_uri_root_path.rstrip('/') if config_uri_root_path else ''}/?session={session_id}",  # Full sharing URL with root path
            render_string=None,  # Not used in asyncio_terminal directly for MOTD rendering
            broadcast=lambda s, m: broadcast_to_session(s, m),
            login=config_login,
            pam_profile=config_pam_profile
        )

        # Associate terminal with client using the new client set
        terminal_instance.client_sids.add(sid)

        # Start the PTY
        log.debug("Starting PTY")
        await terminal_instance.start_pty()
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
        
        # Get the terminal to find connected clients
        terminal = AsyncioTerminal.sessions.get(session_id)
        if terminal and hasattr(terminal, 'client_sids'):
            client_sids = list(terminal.client_sids)
        else:
            client_sids = []
        
        if message is not None:
            # Terminal output - broadcast to all clients in this session
            log.debug(f"Broadcasting terminal output for session {session_id} to {len(client_sids)} clients: {repr(message)}")
            for client_sid in client_sids:
                asyncio.create_task(
                    sio_instance.emit(
                        "terminal_output", {"session": session_id, "data": message}, room=client_sid
                    )
                )
        else:
            # Terminal closed - notify all clients in this session
            log.info(f"Broadcasting terminal closed for session {session_id} to {len(client_sids)} clients")
            for client_sid in client_sids:
                asyncio.create_task(
                    sio_instance.emit("terminal_closed", {"session": session_id}, room=client_sid)
                )
    else:
        log.warning("sio_instance is None, cannot broadcast message")
