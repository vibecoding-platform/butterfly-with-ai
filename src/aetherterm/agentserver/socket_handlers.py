import logging
from uuid import uuid4
import asyncio
from typing import Dict, Any
from datetime import datetime

from dependency_injector.wiring import Provide, inject
from .socket_tracking import track_socket_request, track_socket_response, track_socket_error
from .telemetry.socket_instrumentation import instrument_socketio_handler

from aetherterm.agentserver import utils
from aetherterm.agentserver.auto_blocker import (
    BlockReason,
    get_auto_blocker,
    set_socket_io_instance,
)
from aetherterm.agentserver.containers import ApplicationContainer
from aetherterm.agentserver.log_analyzer import SeverityLevel, get_log_analyzer
from aetherterm.agentserver.terminals.asyncio_terminal import AsyncioTerminal
from aetherterm.agentserver.utils import User
from aetherterm.agentserver.ai_services import AIService, get_ai_service
from aetherterm.agentserver.services.workspace_manager import get_workspace_manager
from aetherterm.agentserver.terminals.terminal_factory import get_terminal_factory, TerminalType

log = logging.getLogger("aetherterm.socket_handlers")

# Global storage for socket.io server instance
sio_instance = None


def set_sio_instance(sio):
    """Set the global socket.io server instance."""
    global sio_instance
    sio_instance = sio
    # 自動ブロッカーにSocket.IOインスタンスを設定
    set_socket_io_instance(sio)


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


import jinja2


@inject
@instrument_socketio_handler("connect")
async def connect(
    sid,
    environ,
    config_motd: str = Provide[ApplicationContainer.config.motd],
):
    """Handle client connection."""
    log.info(f"Client connected: {sid}")
    await sio_instance.emit("connected", {"data": "Connected to Butterfly"}, room=sid)

    try:
        with open(config_motd, "r") as f:
            motd_content = f.read()

        # Jinja2 rendering
        template = jinja2.Template(motd_content)
        rendered_motd = template.render()

        await sio_instance.emit(
            "terminal_output", {"session": "motd", "data": rendered_motd}, room=sid
        )
    except FileNotFoundError:
        log.warning(f"MOTD file not found: {config_motd}")
    except Exception as e:
        log.error(f"Error reading MOTD file: {e}")


@instrument_socketio_handler("disconnect")
async def disconnect(sid, environ=None):
    """Handle client disconnection."""
    log.info(f"Client disconnected: {sid}")

    # Remove client from workspace manager
    try:
        workspace_manager = get_workspace_manager()
        await workspace_manager.remove_client(sid)
    except Exception as e:
        log.error(f"Error removing client from workspace: {e}")

    # Clean up terminals for this socket using factory
    try:
        factory = get_terminal_factory()

        # For multi-socket terminals, just remove this socket
        # The terminal will only be closed if no other sockets remain
        terminals_to_check = []
        for pane_id, terminal_id in list(pane_terminals.items()):
            terminal = factory.get_terminal(terminal_id)
            if terminal and hasattr(terminal, "has_socket") and terminal.has_socket(sid):
                terminals_to_check.append((pane_id, terminal_id))

        # Remove socket from terminals and clean up pane mappings if needed
        for pane_id, terminal_id in terminals_to_check:
            terminal = factory.get_terminal(terminal_id)
            if terminal and hasattr(terminal, "remove_socket"):
                no_sockets_remain = terminal.remove_socket(sid)
                if no_sockets_remain:
                    # Terminal will be closed, remove pane mapping
                    del pane_terminals[pane_id]
                    await factory.remove_terminal(terminal_id)
                    log.info(
                        f"Closed terminal {terminal_id} for pane {pane_id} (no sockets remain)"
                    )
                else:
                    log.info(f"Removed socket {sid} from terminal {terminal_id} for pane {pane_id}")

        if terminals_to_check:
            log.info(f"Processed {len(terminals_to_check)} terminals for disconnected client {sid}")

    except Exception as e:
        log.error(f"Error cleaning up factory terminals: {e}")

    # Remove client from any legacy AsyncioTerminal sessions and close if no clients remain
    for session_id, terminal in list(AsyncioTerminal.sessions.items()):
        if hasattr(terminal, "client_sids") and sid in terminal.client_sids:
            terminal.client_sids.discard(sid)
            log.info(f"Removed client {sid} from terminal session {session_id}")
            # If no clients remain, close the terminal
            if not terminal.client_sids:
                log.info(f"No clients remaining for session {session_id}, closing terminal")
                await terminal.close()


@inject
@instrument_socketio_handler("create_terminal")
async def create_terminal(
    sid,
    data,
    config_login: bool = Provide[ApplicationContainer.config.login],
    config_pam_profile: str = Provide[ApplicationContainer.config.pam_profile],
    config_uri_root_path: str = Provide[ApplicationContainer.config.uri_root_path],
):
    """Handle the creation of a new terminal session."""
    try:
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
                # Send terminal history to new client with buffer restore event
                if existing_terminal.history:
                    await sio_instance.emit(
                        "terminal_buffer_restore",
                        {
                            "session": session_id, 
                            "data": existing_terminal.history,
                            "buffer_size": len(existing_terminal.history),
                            "restore_timestamp": __import__("time").time()
                        },
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


# Legacy terminal_input function removed to avoid conflicts with the new implementation
# The new terminal_input function (line ~1533) handles modern terminal factory pattern


@instrument_socketio_handler("terminal_resize")
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
            # リアルタイムログ解析を実行
            log_analyzer = get_log_analyzer()
            auto_blocker = get_auto_blocker()

            detection_result = log_analyzer.analyze_output(session_id, message)

            if detection_result and detection_result.should_block:
                # 危険検出時の自動ブロック
                block_reason = (
                    BlockReason.CRITICAL_KEYWORD
                    if detection_result.severity == SeverityLevel.CRITICAL
                    else BlockReason.MULTIPLE_WARNINGS
                )

                success = auto_blocker.block_session(
                    session_id=session_id,
                    reason=block_reason,
                    message=detection_result.message,
                    alert_message=detection_result.alert_message,
                    detected_keywords=detection_result.detected_keywords,
                )

                if success:
                    log.warning(
                        f"Session {session_id} automatically blocked due to: {detection_result.message}"
                    )

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
        if hasattr(terminal, "history") and terminal.history:
            # Get last 1000 characters of terminal history to avoid overwhelming the AI
            recent_history = (
                terminal.history[-1000:] if len(terminal.history) > 1000 else terminal.history
            )
            context_parts.append(f"Recent terminal output:\n{recent_history}")

        # Add current working directory if available
        if hasattr(terminal, "path") and terminal.path:
            context_parts.append(f"Current directory: {terminal.path}")

        # Add user information if available
        if hasattr(terminal, "user") and terminal.user:
            context_parts.append(f"User: {terminal.user.name}")

        return "\n\n".join(context_parts) if context_parts else None

    return None


@instrument_socketio_handler("ai_chat_message")
async def ai_chat_message(sid, data):
    """Handle AI chat messages with terminal context."""
    try:
        message = data.get("message", "")
        message_id = data.get("message_id", "")
        terminal_session = data.get("terminal_session")

        if not message:
            log.warning("Empty message received for AI chat")
            return

        log.info(f"Processing AI chat message from {sid}: {message[:100]}...")

        # Get AI service
        ai_service = get_ai_service()

        if not await ai_service.is_available():
            await sio_instance.emit(
                "ai_chat_error",
                {"message_id": message_id, "error": "AI service is not available"},
                room=sid,
            )
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
                messages=messages, terminal_context=terminal_context, stream=True
            ):
                response_chunks.append(chunk)
                await sio_instance.emit(
                    "ai_chat_chunk", {"message_id": message_id, "chunk": chunk}, room=sid
                )

            # Send completion signal
            full_response = "".join(response_chunks)
            await sio_instance.emit(
                "ai_chat_complete",
                {"message_id": message_id, "full_response": full_response},
                room=sid,
            )

            log.info(f"AI chat completed for message_id: {message_id}")

        except Exception as e:
            log.error(f"Error during AI streaming: {e}")
            await sio_instance.emit(
                "ai_chat_error", {"message_id": message_id, "error": str(e)}, room=sid
            )

    except Exception as e:
        log.error(f"Error handling AI chat message: {e}")
        await sio_instance.emit(
            "ai_chat_error",
            {"message_id": data.get("message_id", ""), "error": "Internal server error"},
            room=sid,
        )


@instrument_socketio_handler("ai_terminal_analysis")
async def ai_terminal_analysis(sid, data):
    """Analyze terminal commands and provide AI suggestions."""
    try:
        command = data.get("command", "")
        terminal_session = data.get("terminal_session")
        analysis_id = data.get("analysis_id", "")

        if not command:
            log.warning("Empty command received for AI analysis")
            return

        log.info(f"Analyzing command for {sid}: {command}")

        # Get AI service
        ai_service = get_ai_service()

        if not await ai_service.is_available():
            await sio_instance.emit(
                "ai_analysis_error",
                {"analysis_id": analysis_id, "error": "AI service is not available"},
                room=sid,
            )
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
                messages=messages, terminal_context=terminal_context, stream=True
            ):
                response_chunks.append(chunk)
                await sio_instance.emit(
                    "ai_analysis_chunk", {"analysis_id": analysis_id, "chunk": chunk}, room=sid
                )

            # Send completion signal
            full_analysis = "".join(response_chunks)
            await sio_instance.emit(
                "ai_analysis_complete",
                {"analysis_id": analysis_id, "command": command, "analysis": full_analysis},
                room=sid,
            )

            log.info(f"AI command analysis completed for analysis_id: {analysis_id}")

        except Exception as e:
            log.error(f"Error during AI analysis: {e}")
            await sio_instance.emit(
                "ai_analysis_error", {"analysis_id": analysis_id, "error": str(e)}, room=sid
            )

    except Exception as e:
        log.error(f"Error handling AI terminal analysis: {e}")
        await sio_instance.emit(
            "ai_analysis_error",
            {"analysis_id": data.get("analysis_id", ""), "error": "Internal server error"},
            room=sid,
        )


@instrument_socketio_handler("ai_get_info")
async def ai_get_info(sid, data):
    """Get AI service information (model, provider, status)."""
    try:
        ai_service = get_ai_service()

        # Get AI service information
        provider = "unknown"
        model = "unknown"

        if hasattr(ai_service, "model"):
            model = ai_service.model
        if hasattr(ai_service, "__class__"):
            provider = ai_service.__class__.__name__.lower().replace("service", "")

        is_available = await ai_service.is_available()

        await sio_instance.emit(
            "ai_info_response",
            {
                "provider": provider,
                "model": model,
                "available": is_available,
                "status": "connected" if is_available else "disconnected",
            },
            room=sid,
        )

        log.info(
            f"AI info requested from {sid}: provider={provider}, model={model}, available={is_available}"
        )

    except Exception as e:
        log.error(f"Error getting AI info: {e}")
        await sio_instance.emit(
            "ai_info_response",
            {
                "provider": "error",
                "model": "error",
                "available": False,
                "status": "error",
                "error": str(e),
            },
            room=sid,
        )


# Session management socket handlers


@instrument_socketio_handler("session_create")
async def session_create(sid, data):
    """Handle session creation request from client"""
    try:
        from aetherterm.agentserver.services.session_manager import get_session_manager
        from aetherterm.agentserver.models.session import User, UserPermission, SessionSettings

        session_manager = get_session_manager()

        # Extract data
        name = data.get("name", "New Session")
        description = data.get("description", "")
        settings_data = data.get("settings", {})

        # TODO: Get actual user info from authentication
        user = User.create(
            user_id=f"user-{sid}",
            name=f"User {sid[:8]}",
            remote_addr="localhost",  # TODO: Get actual remote addr
            permission=UserPermission.OWNER,
        )

        # Create settings
        settings = SessionSettings(
            allow_observers=settings_data.get("allowObservers", True),
            allow_collaborators=settings_data.get("allowCollaborators", True),
            require_approval_for_join=settings_data.get("requireApprovalForJoin", False),
            auto_close_on_owner_disconnect=settings_data.get("autoCloseOnOwnerDisconnect", True),
            session_timeout=settings_data.get("sessionTimeout", 60),
        )

        # Create session
        session = await session_manager.create_session(
            name=name, owner=user, description=description, settings=settings
        )

        log.info(f"Session created: {session.id} for client {sid}")

        # Send session created event to client
        await sio_instance.emit("session:created", session.to_dict(), room=sid)

        # Broadcast to other clients if needed
        # await sio_instance.emit('session:available', {
        #     'session_id': session.id,
        #     'session': session.to_dict()
        # })

    except Exception as e:
        log.error(f"Error creating session: {e}")
        await sio_instance.emit(
            "session:error", {"error": str(e), "code": "session_create_failed"}, room=sid
        )


@instrument_socketio_handler("session_join")
async def session_join(sid, data):
    """Handle session join request from client"""
    try:
        from aetherterm.agentserver.services.session_manager import get_session_manager
        from aetherterm.agentserver.models.session import User, UserPermission

        session_manager = get_session_manager()

        session_id = data.get("sessionId")
        permission = data.get("permission", "observer")

        if not session_id:
            await sio_instance.emit(
                "session:error",
                {"error": "session_id required", "code": "missing_session_id"},
                room=sid,
            )
            return

        # TODO: Get actual user info from authentication
        user = User.create(
            user_id=f"user-{sid}",
            name=f"User {sid[:8]}",
            remote_addr="localhost",
            permission=UserPermission(permission)
            if permission in [p.value for p in UserPermission]
            else UserPermission.OBSERVER,
        )

        # Join session
        success = await session_manager.join_session(session_id, user, user.permission)

        if success:
            session = await session_manager.get_session(session_id)
            log.info(f"User {user.name} joined session {session_id}")

            # Send session state to joining user
            await sio_instance.emit(
                "session:joined",
                {
                    "session_id": session_id,
                    "session": session.to_dict() if session else None,
                    "user": {"id": user.id, "name": user.name, "permission": user.permission.value},
                },
                room=sid,
            )

            # Notify other users in session
            await sio_instance.emit(
                "user:joined",
                {
                    "session_id": session_id,
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "remoteAddr": user.remote_addr,
                        "joinedAt": user.joined_at.isoformat(),
                        "permission": user.permission.value,
                    },
                },
            )

        else:
            await sio_instance.emit(
                "session:error",
                {"error": "Failed to join session", "code": "session_join_failed"},
                room=sid,
            )

    except Exception as e:
        log.error(f"Error joining session: {e}")
        await sio_instance.emit(
            "session:error", {"error": str(e), "code": "session_join_error"}, room=sid
        )


@instrument_socketio_handler("session_leave")
async def session_leave(sid, data):
    """Handle session leave request from client"""
    try:
        from aetherterm.agentserver.services.session_manager import get_session_manager

        session_manager = get_session_manager()

        session_id = data.get("sessionId")
        user_id = f"user-{sid}"  # TODO: Get actual user ID

        if not session_id:
            return

        success = await session_manager.leave_session(session_id, user_id)

        if success:
            log.info(f"User {user_id} left session {session_id}")

            # Notify user
            await sio_instance.emit("session:left", {"session_id": session_id}, room=sid)

            # Notify other users in session
            await sio_instance.emit("user:left", {"session_id": session_id, "user_id": user_id})

    except Exception as e:
        log.error(f"Error leaving session: {e}")


@instrument_socketio_handler("tab_create")
async def tab_create(sid, data):
    """Handle tab creation request from client"""
    try:
        from aetherterm.agentserver.services.session_manager import get_session_manager
        from aetherterm.agentserver.models.session import TabType

        session_manager = get_session_manager()

        session_id = data.get("sessionId")
        tab_data = data.get("tabData", {})
        user_id = f"user-{sid}"  # TODO: Get actual user ID

        if not session_id:
            await sio_instance.emit(
                "session:error",
                {"error": "session_id required", "code": "missing_session_id"},
                room=sid,
            )
            return

        tab_type = TabType(tab_data.get("type", "terminal"))
        title = tab_data.get("title", "New Tab")

        tab = await session_manager.create_tab(
            session_id=session_id, tab_type=tab_type, title=title, user_id=user_id, **tab_data
        )

        if tab:
            log.info(f"Tab created: {tab.id} in session {session_id}")

            # Get updated session
            session = await session_manager.get_session(session_id)

            # Notify all users in session
            await sio_instance.emit(
                "tab:created",
                {"session_id": session_id, "tab": session._tab_to_dict(tab) if session else None},
            )

        else:
            await sio_instance.emit(
                "session:error",
                {"error": "Failed to create tab", "code": "tab_create_failed"},
                room=sid,
            )

    except Exception as e:
        log.error(f"Error creating tab: {e}")
        await sio_instance.emit(
            "session:error", {"error": str(e), "code": "tab_create_error"}, room=sid
        )


@instrument_socketio_handler("tab_switch")
async def tab_switch(sid, data):
    """Handle tab switch request from client"""
    try:
        from aetherterm.agentserver.services.session_manager import get_session_manager

        session_manager = get_session_manager()

        session_id = data.get("sessionId")
        tab_id = data.get("tabId")
        user_id = f"user-{sid}"  # TODO: Get actual user ID

        if not session_id or not tab_id:
            return

        success = await session_manager.switch_tab(session_id, tab_id, user_id)

        if success:
            # Notify all users in session
            await sio_instance.emit(
                "tab:switched", {"session_id": session_id, "tab_id": tab_id, "user_id": user_id}
            )

    except Exception as e:
        log.error(f"Error switching tab: {e}")


@instrument_socketio_handler("tab_close")
async def tab_close(sid, data):
    """Handle tab close request from client"""
    try:
        from aetherterm.agentserver.services.session_manager import get_session_manager

        session_manager = get_session_manager()

        session_id = data.get("sessionId")
        tab_id = data.get("tabId")
        user_id = f"user-{sid}"  # TODO: Get actual user ID

        if not session_id or not tab_id:
            return

        success = await session_manager.delete_tab(session_id, tab_id, user_id)

        if success:
            # Notify all users in session
            await sio_instance.emit("tab:deleted", {"session_id": session_id, "tab_id": tab_id})

    except Exception as e:
        log.error(f"Error closing tab: {e}")


@instrument_socketio_handler("pane_split")
async def pane_split(sid, data):
    """Handle pane split request from client"""
    try:
        from aetherterm.agentserver.services.session_manager import get_session_manager

        session_manager = get_session_manager()

        session_id = data.get("sessionId")
        tab_id = data.get("tabId")
        pane_id = data.get("paneId")
        direction = data.get("direction", "horizontal")
        user_id = f"user-{sid}"  # TODO: Get actual user ID

        if not all([session_id, tab_id, pane_id]):
            return

        new_pane = await session_manager.split_pane(
            session_id=session_id,
            tab_id=tab_id,
            pane_id=pane_id,
            direction=direction,
            user_id=user_id,
        )

        if new_pane:
            # Notify all users in session
            await sio_instance.emit(
                "pane:created",
                {
                    "session_id": session_id,
                    "tab_id": tab_id,
                    "pane": {
                        "id": new_pane.id,
                        "terminalId": new_pane.terminal_id,
                        "title": new_pane.title,
                        "shellType": new_pane.shell_type,
                        "workingDirectory": new_pane.working_directory,
                        "position": new_pane.position,
                        "isActive": new_pane.is_active,
                        "createdAt": new_pane.created_at.isoformat(),
                        "lastAccessedAt": new_pane.last_accessed_at.isoformat(),
                    },
                },
            )

    except Exception as e:
        log.error(f"Error splitting pane: {e}")


@instrument_socketio_handler("pane_close")
async def pane_close(sid, data):
    """Handle pane close request from client"""
    try:
        from aetherterm.agentserver.services.session_manager import get_session_manager

        session_manager = get_session_manager()

        session_id = data.get("sessionId")
        tab_id = data.get("tabId")
        pane_id = data.get("paneId")
        user_id = f"user-{sid}"  # TODO: Get actual user ID

        if not all([session_id, tab_id, pane_id]):
            return

        success = await session_manager.close_pane(session_id, tab_id, pane_id, user_id)

        if success:
            # Notify all users in session
            await sio_instance.emit(
                "pane:deleted", {"session_id": session_id, "tab_id": tab_id, "pane_id": pane_id}
            )

    except Exception as e:
        log.error(f"Error closing pane: {e}")


@instrument_socketio_handler("session_message_send")
async def session_message_send(sid, data):
    """Handle session message send request from client"""
    try:
        from aetherterm.agentserver.services.session_manager import get_session_manager
        from aetherterm.agentserver.models.session import (
            SessionMessage,
            MessageType,
            User,
            UserPermission,
        )

        session_manager = get_session_manager()

        # TODO: Get actual user info from authentication
        user = User.create(
            user_id=f"user-{sid}",
            name=f"User {sid[:8]}",
            remote_addr="localhost",
            permission=UserPermission.COLLABORATOR,
        )

        session_id = data.get("sessionId")
        content = data.get("content", "")
        message_type = MessageType(data.get("type", "text"))
        metadata = data.get("metadata")

        if not session_id or not content:
            return

        message = SessionMessage.create(
            session_id=session_id,
            user=user,
            message_type=message_type,
            content=content,
            metadata=metadata,
        )

        success = await session_manager.send_message(message)

        if success:
            # Broadcast message to all users in session
            await sio_instance.emit(
                "session:message:received",
                {
                    "id": message.id,
                    "sessionId": message.session_id,
                    "fromUserId": message.from_user_id,
                    "fromUserName": message.from_user_name,
                    "type": message.type.value,
                    "content": message.content,
                    "metadata": message.metadata,
                    "timestamp": message.timestamp.isoformat(),
                },
            )

    except Exception as e:
        log.error(f"Error sending session message: {e}")


async def session_sync_request(sid, data=None):
    """Handle session state sync request from client"""
    try:
        from aetherterm.agentserver.services.session_manager import get_session_manager

        session_manager = get_session_manager()

        user_id = f"user-{sid}"  # TODO: Get actual user ID
        sessions = await session_manager.list_sessions(user_id)

        # Send session state to client
        await sio_instance.emit(
            "session:sync:response",
            {"sessions": [session.to_dict() for session in sessions]},
            room=sid,
        )

    except Exception as e:
        log.error(f"Error syncing session state: {e}")


@instrument_socketio_handler("workspace_sync_request")
async def workspace_sync_request(sid, data=None):
    """Handle workspace state sync request from client - returns existing sessions and terminals"""
    print(f"[WORKSPACE SYNC] ===== REQUEST RECEIVED from {sid} =====", flush=True)
    log.info(f"[WORKSPACE SYNC] Request received from client {sid}")

    try:
        user_id = f"user-{sid}"

        # Check if workspace has been initialized - check for existing terminals
        existing_terminals = []
        for session_id, terminal in AsyncioTerminal.sessions.items():
            if not terminal.closed:
                existing_terminals.append(
                    {
                        "session_id": session_id,
                        "terminal_id": session_id,
                        "status": "active",
                        "created_at": getattr(terminal, "created_at", None),
                        "clients": len(getattr(terminal, "client_sids", set())),
                        "history_length": len(getattr(terminal, "history", "")),
                        "history": getattr(terminal, "history", "")  # Include history for buffer restore
                    }
                )
        
        workspace_initialized = len(existing_terminals) > 0

        if not workspace_initialized:
            print(f"[WORKSPACE SYNC] Workspace not initialized - returning empty state")
            response_data = {
                "sessions": [],
                "existingTerminals": [],
                "currentUser": {
                    "id": user_id,
                    "name": f"User {sid[:8]}",
                    "remote_addr": "localhost",
                },
                "workspace_initialized": False,
                "message": "Workspace not initialized - clean state",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            print(f"[WORKSPACE SYNC] Found {len(existing_terminals)} existing terminals")
            response_data = {
                "sessions": [],  # TODO: Get from session manager
                "existingTerminals": existing_terminals,
                "currentUser": {
                    "id": user_id,
                    "name": f"User {sid[:8]}",
                    "remote_addr": "localhost",
                },
                "workspace_initialized": True,
                "timestamp": datetime.now().isoformat(),
            }

        print(
            f"[WORKSPACE SYNC] Sending response: {len(response_data['sessions'])} sessions, {len(response_data['existingTerminals'])} terminals"
        )
        print(f"[WORKSPACE SYNC] ===== SENDING RESPONSE =====")

        # Send workspace state to client
        await sio_instance.emit("workspace:sync:response", response_data, room=sid)
        print(f"[WORKSPACE SYNC] Response sent successfully")

    except Exception as e:
        print(f"[WORKSPACE SYNC] ERROR: {e}")
        log.error(f"Error syncing workspace state: {e}")
        import traceback

        log.error(f"Traceback: {traceback.format_exc()}")

        # Send error response
        await sio_instance.emit(
            "workspace:sync:error", {"error": str(e), "code": "workspace_sync_failed"}, room=sid
        )
        print(f"[WORKSPACE SYNC] Error response sent")


# Auto-creation handlers for external integrations


async def auto_create_session_for_shell(
    shell_pid: int, shell_type: str = "bash", user_info: dict = None
):
    """Auto-create session when AgentShell connects"""
    try:
        from aetherterm.agentserver.services.session_manager import get_session_manager

        session_manager = get_session_manager()

        session = await session_manager.auto_create_session_for_shell(
            shell_pid=shell_pid, shell_type=shell_type, user_info=user_info or {}
        )

        # Broadcast new session to all connected clients
        await sio_instance.emit("server:session:create", session.to_dict())

        log.info(f"Auto-created session {session.id} for shell PID {shell_pid}")
        return session

    except Exception as e:
        log.error(f"Error auto-creating session for shell: {e}")
        return None


# Multi-window synchronization handlers


async def workspace_initialize(sid, data):
    """Initialize client with current workspace state"""
    log.info(f"🔧 workspace_initialize called for {sid}")
    try:
        workspace_manager = get_workspace_manager()

        # Create user from socket info
        from aetherterm.agentserver.models.session import User as SessionUser

        user_info = get_user_info_from_environ(data.get("environ", {}))
        user = SessionUser.create(
            user_id=f"user-{sid}",
            name=f"User {sid[:8]}",
            remote_addr=user_info.get("remote_addr", "localhost"),
        )

        # Add client and get full workspace state
        full_state = await workspace_manager.add_client(sid, user)

        # Send complete workspace state to client
        await sio_instance.emit("workspace:initialized", full_state, room=sid)

        log.info(f"Initialized workspace for client {sid}")

    except Exception as e:
        log.error(f"Error initializing workspace: {e}")
        await sio_instance.emit(
            "workspace:error", {"error": "Failed to initialize workspace"}, room=sid
        )


async def workspace_tab_create(sid, data):
    """Handle tab creation request"""
    log.info(f"🔧 workspace_tab_create called for {sid}")
    try:
        workspace_manager = get_workspace_manager()

        title = data.get("title")
        tab_type = data.get("type", "terminal")

        new_tab = await workspace_manager.create_tab(title, tab_type)

        # NOTE: workspace_manager.create_tab() already emits 'tab_created' event
        # No need to broadcast again here to avoid duplicate events

        log.info(f"Created tab {new_tab.id} from client {sid}")

    except Exception as e:
        log.error(f"Error creating tab: {e}")
        await sio_instance.emit("workspace:error", {"error": "Failed to create tab"}, room=sid)


async def workspace_tab_switch(sid, data):
    """Handle tab switch request"""
    log.info(f"🔄 workspace_tab_switch called for {sid} with data: {data}")
    try:
        workspace_manager = get_workspace_manager()

        tab_id = data.get("tabId")
        if not tab_id:
            log.warning(f"No tabId provided in switch request from {sid}")
            return

        log.info(f"Attempting to switch to tab {tab_id}")
        success = await workspace_manager.switch_tab(tab_id)

        if success:
            log.info(f"Successfully switched to tab {tab_id} from client {sid}")
            # Do not broadcast tab switches - each window should maintain its own active tab
        else:
            log.warning(f"Failed to switch to tab {tab_id} - tab not found")

    except Exception as e:
        log.error(f"Error switching tab: {e}")
        import traceback

        log.error(f"Traceback: {traceback.format_exc()}")


async def workspace_tab_close(sid, data):
    """Handle tab close request"""
    try:
        workspace_manager = get_workspace_manager()

        tab_id = data.get("tabId")
        if not tab_id:
            return

        success = await workspace_manager.close_tab(tab_id)

        if success:
            # Broadcast to all clients
            ui_state = workspace_manager.get_ui_state()
            await sio_instance.emit("workspace:tab_closed", {"tabId": tab_id, "uiState": ui_state})

            log.info(f"Closed tab {tab_id} from client {sid}")

    except Exception as e:
        log.error(f"Error closing tab: {e}")


async def workspace_pane_split(sid, data):
    """Handle pane split request"""
    try:
        workspace_manager = get_workspace_manager()

        tab_id = data.get("tabId")
        pane_id = data.get("paneId")
        direction = data.get("direction", "horizontal")

        if not all([tab_id, pane_id]):
            return

        new_pane = await workspace_manager.split_pane(tab_id, pane_id, direction)

        if new_pane:
            # Broadcast to all clients
            await sio_instance.emit(
                "workspace:pane_created",
                {"tabId": tab_id, "pane": new_pane.to_dict(), "direction": direction},
            )

            log.info(f"Split pane {pane_id} {direction}ly in tab {tab_id} from client {sid}")

    except Exception as e:
        log.error(f"Error splitting pane: {e}")


async def workspace_pane_close(sid, data):
    """Handle pane close request"""
    try:
        workspace_manager = get_workspace_manager()

        tab_id = data.get("tabId")
        pane_id = data.get("paneId")

        if not all([tab_id, pane_id]):
            return

        success = await workspace_manager.close_pane(tab_id, pane_id)

        if success:
            # Broadcast to all clients
            tab = workspace_manager.get_tab(tab_id)
            await sio_instance.emit(
                "workspace:pane_closed",
                {"tabId": tab_id, "paneId": pane_id, "tab": tab.to_dict() if tab else None},
            )

            log.info(f"Closed pane {pane_id} in tab {tab_id} from client {sid}")

    except Exception as e:
        log.error(f"Error closing pane: {e}")


async def workspace_ui_update(sid, data):
    """Handle UI state update request"""
    try:
        workspace_manager = get_workspace_manager()

        updates = data.get("updates", {})
        if not updates:
            return

        ui_state = await workspace_manager.update_ui_state(updates)

        # Broadcast to all other clients (exclude sender)
        await sio_instance.emit(
            "workspace:ui_updated", {"uiState": ui_state, "updates": updates}, skip_sid=sid
        )

        log.debug(f"Updated UI state from client {sid}: {updates}")

    except Exception as e:
        log.error(f"Error updating UI state: {e}")


# NOTE: Removed duplicate workspace_sync_request handler
# The main handler is at line 1026 which sends 'workspace:sync:response'


# Setup workspace event callbacks
def setup_workspace_callbacks():
    """Setup workspace manager event callbacks"""
    workspace_manager = get_workspace_manager()

    async def broadcast_workspace_event(event_type: str, data: Dict[str, Any]):
        """Broadcast workspace events to all clients"""
        if sio_instance:
            await sio_instance.emit(f"workspace:{event_type}", data)

    workspace_manager.add_event_callback(broadcast_workspace_event)


# Terminal sessions storage using factory
pane_terminals = {}  # pane_id -> terminal_id mapping


async def create_terminal_output_callback(terminal_id: str):
    """Create output callback for terminal that broadcasts to all connected sockets"""

    async def output_callback(data: str):
        if sio_instance:
            # Broadcast to all clients in the terminal room
            await sio_instance.emit("terminal:data", {"terminalId": terminal_id, "data": data})

    return output_callback


# Terminal handlers for panes
async def terminal_focus(sid, data):
    """Handle terminal focus - sets primary socket for input"""
    try:
        terminal_id = data.get("terminalId")

        if not terminal_id:
            return

        # Get terminal from factory
        factory = get_terminal_factory()
        terminal = factory.get_terminal(terminal_id)

        if terminal is None:
            log.warning(f"Terminal {terminal_id} not found for focus")
            return

        # Set this socket as primary for input
        if hasattr(terminal, "_pty_terminal") and terminal._pty_terminal:
            terminal._pty_terminal.set_primary_socket(sid)
            log.info(f"Set terminal {terminal_id} primary socket to {sid}")

    except Exception as e:
        log.error(f"Error handling terminal focus: {e}")


@instrument_socketio_handler("terminal:create")
async def terminal_create(sid, data):
    """Handle terminal creation for a pane"""
    # Track socket request
    request_id = track_socket_request("terminal:create", data, sid)

    try:
        pane_id = data.get("paneId")
        terminal_id = data.get("terminalId")
        log.info(f"🖥️ Terminal creation requested for {terminal_id} on {sid}")
        cols = data.get("cols", 80)
        rows = data.get("rows", 24)

        if not pane_id or not terminal_id:
            log.warning(f"Missing paneId or terminalId in terminal creation request")
            return

        # Get terminal factory
        factory = get_terminal_factory()

        # Create output callback
        output_callback = await create_terminal_output_callback(terminal_id)

        # Create or get existing terminal (factory handles socket addition automatically)
        # Force AsyncIO terminal type for debugging
        from aetherterm.agentserver.terminals.terminal_factory import TerminalType
        from aetherterm.agentserver.utils import ConnectionInfo, User

        # Create dummy socket and user for AsyncIO terminal
        dummy_socket = ConnectionInfo({"REMOTE_ADDR": "127.0.0.1"})
        dummy_user = User()

        # Create broadcast function that uses output_callback
        def broadcast_func(session_id, message):
            if message and output_callback:
                # Schedule the async output_callback to run in the event loop
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, schedule as a task
                        asyncio.create_task(output_callback(message))
                    else:
                        # If no loop is running, run it directly
                        loop.run_until_complete(output_callback(message))
                except Exception as e:
                    log.error(f"Error in broadcast_func for session {session_id}: {e}")
            elif message is None:
                log.info(f"Terminal {session_id} closed")
            else:
                log.warning(
                    f"No output_callback for session {session_id}, message: {repr(message)}"
                )

        # Check if terminal already exists for buffer restoration
        existing_terminal = factory.get_terminal(terminal_id)
        was_existing = existing_terminal is not None
        existing_history = None
        
        if was_existing and existing_terminal:
            # Get existing history for restoration
            if hasattr(existing_terminal, "_asyncio_terminal") and existing_terminal._asyncio_terminal:
                if hasattr(existing_terminal._asyncio_terminal, "history"):
                    existing_history = existing_terminal._asyncio_terminal.history
                    log.info(f"Found existing terminal {terminal_id} with {len(existing_history)} characters of history")

        try:
            terminal = await factory.create_terminal(
                terminal_id=terminal_id,
                socket_id=sid,
                terminal_type=TerminalType.ASYNCIO,  # Force AsyncIO for debugging
                output_callback=output_callback,
                user=dummy_user,
                path=None,
                socket=dummy_socket,
                uri=f"http://localhost:57575/?session={terminal_id}",
                render_string=None,
                broadcast=broadcast_func,
                login=False,
                pam_profile=None,
            )
            log.debug(f"Created terminal: {terminal} (type: {type(terminal)})")
        except Exception as e:
            log.error(f"Error creating terminal {terminal_id}: {e}")
            import traceback

            log.debug(f"Traceback: {traceback.format_exc()}")
            raise

        if terminal is None:
            log.error(f"Failed to create/get terminal {terminal_id}")
            return

        # Start the terminal only if it's newly created
        # Check for both PTY and AsyncIO terminal types
        should_start = False
        if hasattr(terminal, "_pty_terminal"):
            # PTY Terminal
            should_start = terminal._pty_terminal and not terminal._pty_terminal.is_alive
        elif hasattr(terminal, "_asyncio_terminal"):
            # AsyncIO Terminal - start if not initialized
            should_start = terminal._asyncio_terminal is None
        else:
            # Unknown terminal type, try to start anyway
            should_start = True

        print(
            f"[DEBUG] Terminal {terminal_id}: should_start={should_start}, type={type(terminal)}",
            flush=True,
        )

        if should_start:
            print(f"[DEBUG] Starting terminal {terminal_id}", flush=True)
            success = await terminal.start(cols=cols, rows=rows)
            if not success:
                log.error(f"Failed to start terminal {terminal_id}")
                await factory.remove_terminal(terminal_id)
                return
            print(f"[DEBUG] Successfully started terminal {terminal_id}", flush=True)

        # Store terminal mapping
        pane_terminals[pane_id] = terminal_id

        # Handle buffer restoration for existing terminals
        if was_existing and existing_history and len(existing_history) > 0:
            log.info(f"🔄 Sending buffer restoration for terminal {terminal_id}")
            
            # Prepare buffer restore event data
            buffer_restore_data = {
                "terminalId": terminal_id,
                "data": existing_history,
                "buffer_size": len(existing_history),
                "restore_timestamp": __import__("time").time(),
                "paneId": pane_id
            }
            
            # Send buffer restore event based on whether it's hierarchical or legacy
            if "tabId" in data and "paneId" in data:
                # Send hierarchical buffer restore event
                hierarchical_restore_event = (
                    f"workspace:tab:{data['tabId']}:pane:{data['paneId']}:terminal:buffer_restore"
                )
                await sio_instance.emit(hierarchical_restore_event, buffer_restore_data, room=sid)
                log.info(f"📤 Sent hierarchical buffer restore {hierarchical_restore_event} to {sid}")
            else:
                # Send legacy buffer restore event  
                await sio_instance.emit("terminal_buffer_restore", buffer_restore_data, room=sid)
                log.info(f"📤 Sent legacy terminal_buffer_restore to {sid}")

        response_data = {
            "terminalId": terminal_id,
            "paneId": pane_id,
            "cols": cols,
            "rows": rows,
            "status": "ready",
            "_requestId": request_id,  # Add request ID for tracking
        }

        # Send response - check if this is a hierarchical event
        if "tabId" in data and "paneId" in data:
            # Send hierarchical response
            hierarchical_event = (
                f"workspace:tab:{data['tabId']}:pane:{data['paneId']}:terminal:created"
            )
            await sio_instance.emit(hierarchical_event, response_data, room=sid)
            track_socket_response(request_id, hierarchical_event, success=True)
            log.info(f"📤 Sent hierarchical {hierarchical_event} to {sid}")
        else:
            # Send legacy response
            await sio_instance.emit("terminal:created", response_data, room=sid)
            track_socket_response(request_id, "terminal:created", success=True)
            log.info(f"📤 Sent legacy terminal:created to {sid}")

        # Send test message only for newly created terminals (not for existing ones)
        if terminal is not None and hasattr(terminal, "_pty_terminal") and terminal._pty_terminal:
            # This is a PTY terminal - check if it's newly created
            if not hasattr(terminal._pty_terminal, "_welcome_sent"):
                import asyncio

                await asyncio.sleep(0.2)  # Wait for terminal to be ready

                # Test if output callback is working
                if output_callback:
                    await output_callback("Welcome to AetherTerm!\r\n$ ")
                    terminal._pty_terminal._welcome_sent = True
        elif (
            terminal is not None
            and hasattr(terminal, "_asyncio_terminal")
            and terminal._asyncio_terminal
        ):
            # This is an AsyncIO terminal - check if it's newly created
            if not hasattr(terminal._asyncio_terminal, "_welcome_sent"):
                import asyncio

                await asyncio.sleep(0.2)  # Wait for terminal to be ready

                # Test if output callback is working
                if output_callback:
                    await output_callback("Welcome to AetherTerm!\r\n$ ")
                    terminal._asyncio_terminal._welcome_sent = True

        log.info(f"Created PTY terminal {terminal_id} for pane {pane_id}")

    except Exception as e:
        error_msg = str(e)
        log.error(f"Error creating terminal: {e}")
        import traceback

        log.error(f"Traceback: {traceback.format_exc()}")

        # Track error response
        track_socket_response(request_id, "terminal:created", success=False, error=error_msg)

        # Notify client of error
        await sio_instance.emit(
            "terminal:error",
            {"terminalId": data.get("terminalId"), "paneId": data.get("paneId"), "error": str(e)},
            room=sid,
        )


@instrument_socketio_handler("terminal:input")
async def terminal_input(sid, data):
    """Handle terminal input from client"""
    # Track socket request
    request_id = track_socket_request("terminal:input", data, sid)

    try:
        terminal_id = data.get("terminalId")
        input_data = data.get("data")

        if not terminal_id or input_data is None:
            return

        # Get terminal from factory
        factory = get_terminal_factory()
        terminal = factory.get_terminal(terminal_id)

        if terminal is None:
            log.warning(f"Terminal {terminal_id} not found")
            return

        # Send input to the terminal with socket ID for validation
        success = await terminal.write(input_data, socket_id=sid)
        if not success:
            log.debug(f"Input rejected for terminal {terminal_id} from socket {sid}")
            track_socket_response(
                request_id, "terminal:input_response", success=False, error="Input rejected"
            )
        else:
            log.debug(f"Sent input to terminal {terminal_id}: {repr(input_data)} from socket {sid}")
            track_socket_response(request_id, "terminal:input_response", success=True)

    except Exception as e:
        error_msg = str(e)
        log.error(f"Error handling terminal input: {e}")
        import traceback

        log.error(f"Traceback: {traceback.format_exc()}")
        track_socket_response(request_id, "terminal:input_response", success=False, error=error_msg)


async def terminal_resize(sid, data):
    """Handle terminal resize"""
    try:
        terminal_id = data.get("terminalId")
        cols = data.get("cols")
        rows = data.get("rows")

        if not terminal_id or not cols or not rows:
            return

        # Get terminal from factory
        factory = get_terminal_factory()
        terminal = factory.get_terminal(terminal_id)

        if terminal is None:
            log.warning(f"Terminal {terminal_id} not found for resize")
            return

        # Resize the terminal
        success = await terminal.resize(cols, rows)
        if not success:
            log.warning(f"Failed to resize terminal {terminal_id}")
        else:
            log.debug(f"Resized terminal {terminal_id} to {cols}x{rows}")

    except Exception as e:
        log.error(f"Error resizing terminal: {e}")
        import traceback

        log.error(f"Traceback: {traceback.format_exc()}")


async def terminal_close(sid, data):
    """Handle terminal close"""
    try:
        terminal_id = data.get("terminalId")

        if not terminal_id:
            return

        # Get terminal factory and close terminal
        factory = get_terminal_factory()
        await factory.remove_terminal(terminal_id)

        # Remove from pane mapping
        pane_id_to_remove = None
        for pid, tid in pane_terminals.items():
            if tid == terminal_id:
                pane_id_to_remove = pid
                break

        if pane_id_to_remove:
            del pane_terminals[pane_id_to_remove]
            log.info(f"Closed terminal {terminal_id} for pane {pane_id_to_remove}")

    except Exception as e:
        log.error(f"Error closing terminal: {e}")
        import traceback

        log.error(f"Traceback: {traceback.format_exc()}")


# Hierarchical Event Handlers for workspace:tab:{tabId}:pane:{paneId}:terminal:{operation}


async def hierarchical_terminal_create(sid, data, tab_id, pane_id):
    """Handle hierarchical terminal:create events"""
    # Track socket request
    request_id = track_socket_request(
        f"workspace:tab:{tab_id}:pane:{pane_id}:terminal:create", data, sid
    )

    print(
        f"[HIERARCHICAL DEBUG] terminal_create called! tabId={tab_id}, paneId={pane_id}, sid={sid}, data={data}",
        flush=True,
    )
    log.info(f"🖥️ hierarchical terminal_create called for tab {tab_id}, pane {pane_id}, sid {sid}")

    # Add tab_id and pane_id to data for processing
    enriched_data = {**data, "tabId": tab_id, "paneId": pane_id}

    # Call the original terminal_create function
    await terminal_create(sid, enriched_data)

    # Track response (terminal_create already handles response tracking)


async def hierarchical_terminal_input(sid, data, tab_id, pane_id):
    """Handle hierarchical terminal:input events"""
    # Track socket request
    request_id = track_socket_request(
        f"workspace:tab:{tab_id}:pane:{pane_id}:terminal:input", data, sid
    )

    log.debug(f"🖥️ hierarchical terminal_input called for tab {tab_id}, pane {pane_id}")

    # Add tab_id and pane_id to data for processing
    enriched_data = {**data, "tabId": tab_id, "paneId": pane_id}

    # Call the original terminal_input function
    await terminal_input(sid, enriched_data)


async def hierarchical_terminal_resize(sid, data, tab_id, pane_id):
    """Handle hierarchical terminal:resize events"""
    log.debug(f"🖥️ hierarchical terminal_resize called for tab {tab_id}, pane {pane_id}")

    # Add tab_id and pane_id to data for processing
    enriched_data = {**data, "tabId": tab_id, "paneId": pane_id}

    # Call the original terminal_resize function
    await terminal_resize(sid, enriched_data)


async def hierarchical_terminal_focus(sid, data, tab_id, pane_id):
    """Handle hierarchical terminal:focus events"""
    log.debug(f"🖥️ hierarchical terminal_focus called for tab {tab_id}, pane {pane_id}")

    # Add tab_id and pane_id to data for processing
    enriched_data = {**data, "tabId": tab_id, "paneId": pane_id}

    # Call the original terminal_focus function
    await terminal_focus(sid, enriched_data)


async def hierarchical_terminal_close(sid, data, tab_id, pane_id):
    """Handle hierarchical terminal:close events"""
    log.debug(f"🖥️ hierarchical terminal_close called for tab {tab_id}, pane {pane_id}")

    # Add tab_id and pane_id to data for processing
    enriched_data = {**data, "tabId": tab_id, "paneId": pane_id}

    # Call the original terminal_close function
    await terminal_close(sid, enriched_data)


# Dynamic event router for hierarchical events
async def handle_dynamic_terminal_event(sid, event_name, data):
    """Route hierarchical terminal events to appropriate handlers"""
    try:
        print(
            f"[DYNAMIC HANDLER] Called with event_name: {event_name}, sid: {sid}, data: {data}",
            flush=True,
        )
        log.info(f"🔀 handle_dynamic_terminal_event called: {event_name}")

        # Parse event name: workspace:tab:{tabId}:pane:{paneId}:terminal:{operation}
        parts = event_name.split(":")
        print(f"[DYNAMIC HANDLER] Event parts: {parts}", flush=True)

        if (
            len(parts) != 7
            or parts[0] != "workspace"
            or parts[1] != "tab"
            or parts[3] != "pane"
            or parts[5] != "terminal"
        ):
            print(
                f"[DYNAMIC HANDLER] Invalid format! Expected 7 parts, got {len(parts)}: {parts}",
                flush=True,
            )
            log.warning(f"Invalid hierarchical event format: {event_name}, parts: {parts}")
            return

        tab_id = parts[2]
        pane_id = parts[4]
        operation = parts[6]

        print(
            f"[DYNAMIC HANDLER] Parsed: tab_id={tab_id}, pane_id={pane_id}, operation={operation}",
            flush=True,
        )
        log.info(
            f"🔀 Routing hierarchical event: tab={tab_id}, pane={pane_id}, operation={operation}"
        )

        # Route to appropriate handler
        if operation == "create":
            print(f"[DYNAMIC HANDLER] Routing to hierarchical_terminal_create", flush=True)
            await hierarchical_terminal_create(sid, data, tab_id, pane_id)
        elif operation == "input":
            await hierarchical_terminal_input(sid, data, tab_id, pane_id)
        elif operation == "resize":
            await hierarchical_terminal_resize(sid, data, tab_id, pane_id)
        elif operation == "focus":
            await hierarchical_terminal_focus(sid, data, tab_id, pane_id)
        elif operation == "close":
            await hierarchical_terminal_close(sid, data, tab_id, pane_id)
        else:
            print(f"[DYNAMIC HANDLER] Unknown operation: {operation}", flush=True)
            log.warning(f"Unknown terminal operation: {operation}")

    except Exception as e:
        print(f"[DYNAMIC HANDLER] ERROR: {e}", flush=True)
        log.error(f"Error handling dynamic terminal event {event_name}: {e}")
        import traceback

        print(f"[DYNAMIC HANDLER] Traceback: {traceback.format_exc()}", flush=True)
        log.error(f"Traceback: {traceback.format_exc()}")


# Modified terminal_create to send hierarchical response events
async def send_hierarchical_terminal_created(
    terminal_id, tab_id, pane_id, cols, rows, sid, request_id=None
):
    """Send hierarchical terminal:created event"""
    try:
        event_name = f"workspace:tab:{tab_id}:pane:{pane_id}:terminal:created"
        response_data = {
            "terminalId": terminal_id,
            "tabId": tab_id,
            "paneId": pane_id,
            "cols": cols,
            "rows": rows,
            "status": "ready",
        }

        if request_id:
            response_data["_requestId"] = request_id

        await sio_instance.emit(event_name, response_data, room=sid)

        # Track successful response
        if request_id:
            track_socket_response(request_id, event_name, success=True)

        log.info(f"📤 Sent {event_name} to {sid}")

    except Exception as e:
        log.error(f"Error sending hierarchical terminal:created: {e}")
        if request_id:
            track_socket_response(
                request_id,
                f"workspace:tab:{tab_id}:pane:{pane_id}:terminal:created",
                success=False,
                error=str(e),
            )


# Workspace Management Handlers


async def workspace_tab_create(sid, data):
    """Handle workspace:tab:create events"""
    # Track socket request
    request_id = track_socket_request("workspace:tab:create", data, sid)

    try:
        log.info(f"📋 Creating new tab: {data}")
        print(f"[TAB CREATE] Received workspace:tab:create: {data}", flush=True)

        tab_title = data.get("title", "New Tab")
        tab_type = data.get("type", "terminal")
        session_id = data.get("sessionId")

        # Generate new tab ID
        import uuid

        tab_id = f"{tab_type}-{uuid.uuid4().hex[:11]}"

        # Notify client that tab was created
        response_data = {"tabId": tab_id, "title": tab_title, "type": tab_type, "status": "created"}

        if session_id:
            response_data["sessionId"] = session_id

        if request_id:
            response_data["_requestId"] = request_id

        await sio_instance.emit("workspace:tab:created", response_data, room=sid)

        # Track successful response
        track_socket_response(request_id, "workspace:tab:created", success=True)

        log.info(f"✅ Successfully created tab {tab_id} ({tab_title})")
        print(f"[TAB CREATE] Successfully created tab {tab_id}", flush=True)

    except Exception as e:
        error_msg = str(e)
        log.error(f"Error creating tab: {e}")
        import traceback

        log.error(f"Traceback: {traceback.format_exc()}")

        # Track error response
        track_socket_response(request_id, "workspace:tab:created", success=False, error=error_msg)

        # Notify client of error
        await sio_instance.emit(
            "workspace:tab:error", {"error": error_msg, "_requestId": request_id}, room=sid
        )


async def workspace_tab_close(sid, data):
    """Handle workspace:tab:close events"""
    # Track socket request
    request_id = track_socket_request("workspace:tab:close", data, sid)

    try:
        tab_id = data.get("tabId")
        log.info(f"📋 Closing tab: {tab_id}")

        # TODO: Clean up tab resources

        # Notify client that tab was closed
        response_data = {"tabId": tab_id, "status": "closed"}

        if request_id:
            response_data["_requestId"] = request_id

        await sio_instance.emit("workspace:tab:closed", response_data, room=sid)

        # Track successful response
        track_socket_response(request_id, "workspace:tab:closed", success=True)

        log.info(f"✅ Successfully closed tab {tab_id}")

    except Exception as e:
        error_msg = str(e)
        log.error(f"Error closing tab: {e}")
        import traceback

        log.error(f"Traceback: {traceback.format_exc()}")

        # Track error response
        track_socket_response(request_id, "workspace:tab:closed", success=False, error=error_msg)
