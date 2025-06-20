import logging
from uuid import uuid4
import asyncio

from dependency_injector.wiring import Provide, inject

from aetherterm import utils
from aetherterm.containers import ApplicationContainer
from aetherterm.terminals.asyncio_terminal import AsyncioTerminal
from aetherterm.utils import User
from aetherterm.ai_services import AIService, get_ai_service

log = logging.getLogger("aetherterm.socket_handlers")

# Global storage for socket.io server instance
sio_instance = None


def set_sio_instance(sio):
    """Set the global socket.io server instance."""
    global sio_instance
    sio_instance = sio


def get_user_info_from_environ(environ):
    """Extract user information from environment/headers."""
    user_info = {
        "remote_addr": environ.get("REMOTE_ADDR"),
        "remote_user": environ.get("HTTP_X_REMOTE_USER"),
        "forwarded_for": environ.get("HTTP_X_FORWARDED_FOR"),
        "user_agent": environ.get("HTTP_USER_AGENT"),
    }
    return user_info


def check_session_ownership(session_id, current_user_info):
    """Check if the current user is the owner of the session."""
    if session_id not in AsyncioTerminal.session_owners:
        return False

    owner_info = AsyncioTerminal.session_owners[session_id]

    # Check X-REMOTE-USER header (most reliable for authenticated users)
    if (
        current_user_info.get("remote_user")
        and owner_info.get("remote_user")
        and current_user_info["remote_user"] == owner_info["remote_user"]
    ):
        return True

    # Fallback to IP address comparison (less reliable but works for unsecure mode)
    if (
        current_user_info.get("remote_addr")
        and owner_info.get("remote_addr")
        and current_user_info["remote_addr"] == owner_info["remote_addr"]
    ):
        return True

    return False


async def connect(sid, environ):
    """Handle client connection."""
    log.info(f"Client connected: {sid}")
    await sio_instance.emit("connected", {"data": "Connected to Butterfly"}, room=sid)


async def disconnect(sid, environ=None):
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
    config = Provide[ApplicationContainer.config],
):
    """Handle the creation of a new terminal session."""
    try:
        # Get config values from injected config
        config_login = config.get("login", False) or False
        config_pam_profile = config.get("pam_profile", "") or ""
        config_uri_root_path = config.get("uri_root_path", "") or ""
        
        session_id = data.get("session", str(uuid4()))
        user_name = data.get("user", "")
        path = data.get("path", "")

        # Check if this is a request for a specific session (not a new random one)
        is_specific_session_request = "session" in data and data["session"] != ""

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
                        room=sid,
                    )
                # Notify client that terminal is ready
                await sio_instance.emit(
                    "terminal_ready", {"session": session_id, "status": "ready"}, room=sid
                )
                return
            else:
                # Session exists but is closed - check ownership and notify client
                log.info(f"Attempted to connect to closed session {session_id}")
                # Get environ for user info checking
                environ = getattr(sio_instance, "environ", {}) if sio_instance else {}
                current_user_info = get_user_info_from_environ(environ)
                is_owner = check_session_ownership(session_id, current_user_info)

                await sio_instance.emit(
                    "terminal_closed",
                    {
                        "session": session_id,
                        "reason": "session_already_closed",
                        "is_owner": is_owner,
                    },
                    room=sid,
                )
                return

        # Check if this is a request for a specific session that was previously closed
        if is_specific_session_request and session_id in AsyncioTerminal.closed_sessions:
            log.info(f"Attempted to connect to previously closed session {session_id}")
            # Get environ for user info checking
            environ = getattr(sio_instance, "environ", {}) if sio_instance else {}
            current_user_info = get_user_info_from_environ(environ)
            is_owner = check_session_ownership(session_id, current_user_info)

            await sio_instance.emit(
                "terminal_closed",
                {"session": session_id, "reason": "session_already_closed", "is_owner": is_owner},
                room=sid,
            )
            return

        # Create connection info for Socket.IO
        # Get environ from Socket.IO if available, otherwise use defaults
        environ = getattr(sio_instance, "environ", {}) if sio_instance else {}

        # Try to get more accurate socket information from the session
        # For Socket.IO, we need to extract the real client information
        socket_remote_addr = None
        if hasattr(sio_instance, "manager") and hasattr(sio_instance.manager, "get_session"):
            try:
                session = sio_instance.manager.get_session(sid)
                if session and "transport" in session:
                    transport = session["transport"]
                    if hasattr(transport, "socket") and hasattr(transport.socket, "getpeername"):
                        try:
                            peer = transport.socket.getpeername()
                            socket_remote_addr = peer[0]
                            # Update environ with real remote port
                            environ["REMOTE_PORT"] = str(peer[1])
                        except:
                            pass
            except:
                pass

        # Get current user info for ownership checking
        current_user_info = get_user_info_from_environ(environ)

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
            pam_profile=config_pam_profile,
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
        if terminal and hasattr(terminal, "client_sids"):
            client_sids = list(terminal.client_sids)
        else:
            client_sids = []

        if message is not None:
            # Terminal output - broadcast to all clients in this session
            log.debug(
                f"Broadcasting terminal output for session {session_id} to {len(client_sids)} clients: {repr(message)}"
            )
            for client_sid in client_sids:
                asyncio.create_task(
                    sio_instance.emit(
                        "terminal_output", {"session": session_id, "data": message}, room=client_sid
                    )
                )
        else:
            # Terminal closed - notify all clients in this session
            log.info(
                f"Broadcasting terminal closed for session {session_id} to {len(client_sids)} clients"
            )
            for client_sid in client_sids:
                asyncio.create_task(
                    sio_instance.emit("terminal_closed", {"session": session_id}, room=client_sid)
                )
    else:
        log.warning("sio_instance is None, cannot broadcast message")


def get_terminal_context(session_id):
    """Extract terminal context for AI assistance."""
    if session_id and session_id in AsyncioTerminal.sessions:
        terminal = AsyncioTerminal.sessions[session_id]
        context_parts = []
        
        # Add terminal history if available
        if hasattr(terminal, 'history') and terminal.history:
            # Get last 1000 characters of terminal history to avoid overwhelming the AI
            recent_history = terminal.history[-1000:] if len(terminal.history) > 1000 else terminal.history
            context_parts.append(f"Recent terminal output:\n{recent_history}")
        
        # Add current working directory if available
        if hasattr(terminal, 'path') and terminal.path:
            context_parts.append(f"Current directory: {terminal.path}")
        
        # Add user information if available
        if hasattr(terminal, 'user') and terminal.user:
            context_parts.append(f"User: {terminal.user.name}")
        
        return "\n\n".join(context_parts) if context_parts else None
    
    return None


async def ai_chat_message(sid, data):
    """Handle AI chat messages with terminal context."""
    try:
        message = data.get('message', '')
        message_id = data.get('message_id', '')
        terminal_session = data.get('terminal_session')
        
        if not message:
            log.warning("Empty message received for AI chat")
            return
        
        log.info(f"Processing AI chat message from {sid}: {message[:100]}...")
        
        # Get AI service
        ai_service = get_ai_service()
        
        if not await ai_service.is_available():
            await sio_instance.emit('ai_chat_error', {
                'message_id': message_id,
                'error': 'AI service is not available'
            }, room=sid)
            return
        
        # Get terminal context if session is provided
        terminal_context = None
        if terminal_session:
            terminal_context = get_terminal_context(terminal_session)
        
        # Build messages array
        messages = [{"role": "user", "content": message}]
        
        # Stream AI response
        try:
            response_chunks = []
            async for chunk in ai_service.chat_completion(
                messages=messages,
                terminal_context=terminal_context,
                stream=True
            ):
                response_chunks.append(chunk)
                await sio_instance.emit('ai_chat_chunk', {
                    'message_id': message_id,
                    'chunk': chunk
                }, room=sid)
            
            # Send completion signal
            full_response = ''.join(response_chunks)
            await sio_instance.emit('ai_chat_complete', {
                'message_id': message_id,
                'full_response': full_response
            }, room=sid)
            
            log.info(f"AI chat completed for message_id: {message_id}")
            
        except Exception as e:
            log.error(f"Error during AI streaming: {e}")
            await sio_instance.emit('ai_chat_error', {
                'message_id': message_id,
                'error': str(e)
            }, room=sid)
    
    except Exception as e:
        log.error(f"Error handling AI chat message: {e}")
        await sio_instance.emit('ai_chat_error', {
            'message_id': data.get('message_id', ''),
            'error': 'Internal server error'
        }, room=sid)


async def ai_terminal_analysis(sid, data):
    """Analyze terminal commands and provide AI suggestions."""
    try:
        command = data.get('command', '')
        terminal_session = data.get('terminal_session')
        analysis_id = data.get('analysis_id', '')
        
        if not command:
            log.warning("Empty command received for AI analysis")
            return
        
        log.info(f"Analyzing command for {sid}: {command}")
        
        # Get AI service
        ai_service = get_ai_service()
        
        if not await ai_service.is_available():
            await sio_instance.emit('ai_analysis_error', {
                'analysis_id': analysis_id,
                'error': 'AI service is not available'
            }, room=sid)
            return
        
        # Get terminal context
        terminal_context = get_terminal_context(terminal_session) if terminal_session else None
        
        # Build analysis prompt
        analysis_prompt = f"""Please analyze this terminal command and provide helpful information:

Command: {command}

Please provide:
1. What this command does
2. Any potential risks or considerations
3. Suggested improvements or alternatives if applicable
4. Expected output or behavior

Keep the response concise and practical."""
        
        messages = [{"role": "user", "content": analysis_prompt}]
        
        # Stream AI analysis
        try:
            response_chunks = []
            async for chunk in ai_service.chat_completion(
                messages=messages,
                terminal_context=terminal_context,
                stream=True
            ):
                response_chunks.append(chunk)
                await sio_instance.emit('ai_analysis_chunk', {
                    'analysis_id': analysis_id,
                    'chunk': chunk
                }, room=sid)
            
            # Send completion signal
            full_analysis = ''.join(response_chunks)
            await sio_instance.emit('ai_analysis_complete', {
                'analysis_id': analysis_id,
                'command': command,
                'analysis': full_analysis
            }, room=sid)
            
            log.info(f"AI command analysis completed for analysis_id: {analysis_id}")
            
        except Exception as e:
            log.error(f"Error during AI analysis: {e}")
            await sio_instance.emit('ai_analysis_error', {
                'analysis_id': analysis_id,
                'error': str(e)
            }, room=sid)
    
    except Exception as e:
        log.error(f"Error handling AI terminal analysis: {e}")
        await sio_instance.emit('ai_analysis_error', {
            'analysis_id': data.get('analysis_id', ''),
            'error': 'Internal server error'
        }, room=sid)


async def ai_get_info(sid, data):
    """Get AI service information (model, provider, status)."""
    try:
        ai_service = get_ai_service()
        
        # Get AI service information
        provider = "unknown"
        model = "unknown"
        
        if hasattr(ai_service, 'model'):
            model = ai_service.model
        if hasattr(ai_service, '__class__'):
            provider = ai_service.__class__.__name__.lower().replace('service', '')
        
        is_available = await ai_service.is_available()
        
        await sio_instance.emit('ai_info_response', {
            'provider': provider,
            'model': model,
            'available': is_available,
            'status': 'connected' if is_available else 'disconnected'
        }, room=sid)
        
        log.info(f"AI info requested from {sid}: provider={provider}, model={model}, available={is_available}")
        
    except Exception as e:
        log.error(f"Error getting AI info: {e}")
        await sio_instance.emit('ai_info_response', {
            'provider': 'error',
            'model': 'error',
            'available': False,
            'status': 'error',
            'error': str(e)
        }, room=sid)
