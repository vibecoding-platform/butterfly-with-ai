import logging
from uuid import uuid4
import asyncio

from dependency_injector.wiring import Provide, inject

from aetherterm.agentserver import utils
from aetherterm.agentserver.auto_blocker import (
    BlockReason,
    get_auto_blocker,
    set_socket_io_instance,
)
from aetherterm.core.container import DIContainer, ApplicationContainer
from aetherterm.agentserver.log_analyzer import SeverityLevel, get_log_analyzer
from aetherterm.agentserver.terminals.asyncio_terminal import AsyncioTerminal
from aetherterm.agentserver.utils import User
from aetherterm.agentserver.ai_services import AIService, get_ai_service
from aetherterm.logprocessing.log_processing_manager import LogProcessingManager

log = logging.getLogger("aetherterm.socket_handlers")

# Global storage for socket.io server instance
sio_instance = None
log_processing_manager = None


def set_sio_instance(sio):
    """Set the global socket.io server instance."""
    global sio_instance, log_processing_manager
    sio_instance = sio
    
    # Get log manager directly from DI container
    try:
        log_processing_manager = DIContainer.get_log_processing_manager()
    except Exception as e:
        log.warning(f"Failed to get log processing manager: {e}")
        log_processing_manager = None
    
    # 自動ブロッカーにSocket.IOインスタンスを設定
    set_socket_io_instance(sio)
    log.info("Socket.IO instance configured")


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


async def connect(
    sid,
    environ,
):
    """Handle client connection."""
    log.info(f"Client connected: {sid}")
    await sio_instance.emit("connected", {"data": "Connected to Butterfly"}, room=sid)

    try:
        # Simple welcome message instead of file-based MOTD
        motd_content = "Welcome to AetherTerm - AI Terminal Platform\r\n"
        
        await sio_instance.emit(
            "terminal_output", {"session": "motd", "data": motd_content}, room=sid
        )
    except Exception as e:
        log.error(f"Error sending MOTD: {e}")


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

        # Initialize log capture for this terminal
        if log_processing_manager:
            try:
                await log_processing_manager.initialize_terminal_capture(session_id)
                log.debug(f"Log capture initialized for session {session_id}")
            except Exception as e:
                log.error(f"Failed to initialize log capture for session {session_id}: {e}")

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

        # Capture terminal output for log processing
        if log_processing_manager and message:
            try:
                asyncio.create_task(
                    log_processing_manager.capture_terminal_output(session_id, message)
                )
            except Exception as e:
                log.error(f"Failed to capture terminal output: {e}")

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


async def wrapper_session_sync(sid, data):
    """Handle session synchronization from wrapper programs."""
    try:
        action = data.get("action")
        wrapper_info = data.get("wrapper_info", {})

        log.info(f"Wrapper session sync received: {action} from PID {wrapper_info.get('pid')}")

        if action == "bulk_sync":
            # 複数セッションの一括同期
            sessions = data.get("sessions", [])
            log.info(f"Bulk sync: {len(sessions)} sessions from wrapper")

            # フロントエンドに同期情報を送信
            await sio_instance.emit(
                "wrapper_sessions_update",
                {
                    "action": "bulk_sync",
                    "sessions": sessions,
                    "wrapper_info": wrapper_info,
                    "timestamp": data.get("timestamp"),
                },
            )

        elif action in ["created", "updated", "closed"]:
            # 単一セッションの同期
            session = data.get("session", {})
            session_id = session.get("session_id")

            log.debug(f"Session {action}: {session_id}")

            # フロントエンドに同期情報を送信
            await sio_instance.emit(
                "wrapper_session_update",
                {
                    "action": action,
                    "session": session,
                    "wrapper_info": wrapper_info,
                    "timestamp": data.get("timestamp"),
                },
            )

        # 同期完了の応答を送信
        await sio_instance.emit(
            "wrapper_session_sync_response",
            {"status": "success", "action": action, "timestamp": data.get("timestamp")},
            room=sid,
        )

    except Exception as e:
        log.error(f"Error handling wrapper session sync: {e}")
        await sio_instance.emit(
            "wrapper_session_sync_response", {"status": "error", "error": str(e)}, room=sid
        )


async def get_wrapper_sessions(sid, data):
    """Handle request for wrapper session information."""
    try:
        # この機能は将来的にWrapperセッション情報を取得するために使用
        # 現在は基本的な応答のみ
        await sio_instance.emit(
            "wrapper_sessions_response",
            {"status": "success", "message": "Wrapper session information request received"},
            room=sid,
        )
    except Exception as e:
        log.error(f"Error getting wrapper sessions: {e}")
        await sio_instance.emit(
            "wrapper_sessions_response", {"status": "error", "error": str(e)}, room=sid
        )


async def log_monitor_subscribe(sid, data):
    """Subscribe to log monitoring updates."""
    try:
        terminal_id = data.get("terminal_id")
        log.info(f"Client {sid} subscribing to log monitor for terminal {terminal_id}")
        
        # Join log monitoring room
        await sio_instance.enter_room(sid, f"log_monitor_{terminal_id}")
        
        if log_processing_manager:
            # Get current statistics
            stats = await log_processing_manager.get_terminal_statistics(terminal_id)
            await sio_instance.emit(
                "log_monitor_stats",
                {"terminal_id": terminal_id, "stats": stats},
                room=sid
            )
        
        await sio_instance.emit(
            "log_monitor_subscribed",
            {"status": "success", "terminal_id": terminal_id},
            room=sid
        )
    except Exception as e:
        log.error(f"Error subscribing to log monitor: {e}")
        await sio_instance.emit(
            "log_monitor_error",
            {"error": str(e)},
            room=sid
        )


async def log_monitor_unsubscribe(sid, data):
    """Unsubscribe from log monitoring updates."""
    try:
        terminal_id = data.get("terminal_id")
        log.info(f"Client {sid} unsubscribing from log monitor for terminal {terminal_id}")
        
        # Leave log monitoring room
        await sio_instance.leave_room(sid, f"log_monitor_{terminal_id}")
        
        await sio_instance.emit(
            "log_monitor_unsubscribed",
            {"status": "success", "terminal_id": terminal_id},
            room=sid
        )
    except Exception as e:
        log.error(f"Error unsubscribing from log monitor: {e}")


async def log_monitor_search(sid, data):
    """Handle log search requests."""
    try:
        query = data.get("query", "")
        terminal_id = data.get("terminal_id")
        limit = data.get("limit", 100)
        
        if log_processing_manager:
            results = await log_processing_manager.search_logs(
                query=query,
                terminal_id=terminal_id,
                limit=limit
            )
            
            await sio_instance.emit(
                "log_search_results",
                {
                    "query": query,
                    "terminal_id": terminal_id,
                    "results": results,
                    "count": len(results)
                },
                room=sid
            )
        else:
            await sio_instance.emit(
                "log_search_results",
                {
                    "query": query,
                    "terminal_id": terminal_id,
                    "results": [],
                    "count": 0,
                    "error": "Log processing manager not available"
                },
                room=sid
            )
    except Exception as e:
        log.error(f"Error handling log search: {e}")
        await sio_instance.emit(
            "log_search_error",
            {"error": str(e)},
            room=sid
        )


# Background task to broadcast log statistics
async def broadcast_log_statistics():
    """Broadcast log statistics to all subscribed clients via Pub/Sub."""
    while True:
        try:
            # Skip log statistics for now to avoid DI issues
            if sio_instance:
                # Send empty stats to avoid errors
                system_stats = {
                    "total_logs": 0,
                    "error_count": 0,
                    "processing_active": False
                }
                
                # Broadcast to all log monitor subscribers
                await sio_instance.emit(
                    "log_system_stats",
                    {"stats": system_stats, "timestamp": asyncio.get_event_loop().time()},
                    namespace="/"
                )
                
                # Skip individual terminal statistics for now
                        
        except Exception as e:
            log.error(f"Error broadcasting log statistics: {e}")
        
        # Wait 5 seconds before next broadcast
        await asyncio.sleep(5)


def start_log_monitoring_background_task():
    """Start the background task for log monitoring with Pub/Sub."""
    if sio_instance:
        asyncio.create_task(broadcast_log_statistics())
        # Pub/Subリスナーも開始
        asyncio.create_task(start_redis_pubsub_listener())
        
async def start_redis_pubsub_listener():
    """
    Redis Pub/Subリスナーを開始してリアルタイムアップデートを受信
    """
    try:
        from aetherterm.logprocessing.log_processing_manager import get_log_processing_manager
        
        manager = get_log_processing_manager()
        if not manager or not manager.redis_storage:
            log.warning("Redis storage not available for Pub/Sub")
            return
            
        # リアルタイムイベント用チャンネル
        patterns = [
            "terminal:input:*",
            "terminal:output:*", 
            "terminal:error:*",
            "system:events"
        ]
        
        await manager.redis_storage.subscribe_with_pattern(
            patterns=patterns,
            callback=handle_realtime_log_event
        )
        
    except Exception as e:
        log.error(f"Failed to start Redis Pub/Sub listener: {e}")
        
async def handle_realtime_log_event(channel: str, message: str):
    """
    Redis Pub/SubメッセージをWebSocketクライアントにブロードキャスト
    """
    try:
        import json
        data = json.loads(message)
        
        # チャンネルによって処理を分岐
        if "terminal:error:" in channel:
            # エラーイベントを緊急通知
            await sio_instance.emit(
                "terminal_error_alert",
                {
                    "terminal_id": data.get("terminal_id"),
                    "error_data": data.get("data", {}),
                    "timestamp": data.get("timestamp"),
                    "severity": data.get("data", {}).get("processed_data", {}).get("severity", "unknown")
                }
            )
            
        elif "terminal:input:" in channel:
            # コマンド入力イベント
            await sio_instance.emit(
                "terminal_command_executed",
                {
                    "terminal_id": data.get("terminal_id"),
                    "command": data.get("data", {}).get("processed_data", {}).get("command", ""),
                    "timestamp": data.get("timestamp")
                }
            )
            
        elif "system:events" in channel:
            # システムイベント
            if data.get("type") == "error_detected":
                await sio_instance.emit(
                    "system_error_alert",
                    {
                        "terminal_id": data.get("terminal_id"),
                        "severity": data.get("severity"),
                        "timestamp": data.get("timestamp")
                    }
                )
        
        # 全体統計を更新
        await update_and_broadcast_statistics()
        
    except Exception as e:
        log.error(f"Error handling realtime log event: {e}")

async def update_and_broadcast_statistics():
    """統計情報を更新してブロードキャスト"""
    try:
        # Send empty stats for now to avoid DI issues
        stats = {
            "total_logs": 0,
            "error_count": 0,
            "processing_active": False
        }
        
        if sio_instance:
            await sio_instance.emit("log_system_stats", {"stats": stats})
            
    except Exception as e:
        log.error(f"Error updating statistics: {e}")


async def unblock_request(sid, data):
    """Handle unblock request from client."""
    try:
        session_id = data.get("session_id")
        unlock_key = data.get("unlock_key", "ctrl_d")

        if not session_id:
            log.warning("Unblock request without session_id")
            await sio_instance.emit(
                "unblock_response", {"status": "error", "error": "session_id required"}, room=sid
            )
            return

        auto_blocker = get_auto_blocker()
        success = auto_blocker.unblock_session(session_id, unlock_key)

        if success:
            await sio_instance.emit(
                "unblock_response",
                {
                    "status": "success",
                    "session_id": session_id,
                    "message": "ブロックが解除されました",
                },
                room=sid,
            )
            log.info(f"Session {session_id} unblocked by client {sid}")
        else:
            await sio_instance.emit(
                "unblock_response",
                {
                    "status": "error",
                    "session_id": session_id,
                    "error": "ブロック解除に失敗しました",
                },
                room=sid,
            )

    except Exception as e:
        log.error(f"Error handling unblock request: {e}")
        await sio_instance.emit("unblock_response", {"status": "error", "error": str(e)}, room=sid)


async def get_block_status(sid, data):
    """Handle block status request from client."""
    try:
        session_id = data.get("session_id")

        if not session_id:
            log.warning("Block status request without session_id")
            await sio_instance.emit(
                "block_status_response",
                {"status": "error", "error": "session_id required"},
                room=sid,
            )
            return

        auto_blocker = get_auto_blocker()
        is_blocked = auto_blocker.is_session_blocked(session_id)
        block_state = auto_blocker.get_block_state(session_id)

        response_data = {"status": "success", "session_id": session_id, "is_blocked": is_blocked}

        if block_state:
            response_data.update(
                {
                    "reason": block_state.reason.value,
                    "message": block_state.message,
                    "alert_message": block_state.alert_message,
                    "detected_keywords": block_state.detected_keywords,
                    "blocked_at": block_state.blocked_at,
                }
            )

        await sio_instance.emit("block_status_response", response_data, room=sid)

    except Exception as e:
        log.error(f"Error handling block status request: {e}")
        await sio_instance.emit(
            "block_status_response", {"status": "error", "error": str(e)}, room=sid
        )


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


# Context Inference WebSocket Handlers

async def context_inference_subscribe(sid, data):
    """Subscribe to context inference updates for a terminal."""
    try:
        terminal_id = data.get("terminal_id")
        if not terminal_id:
            await sio_instance.emit(
                "context_inference_error",
                {"error": "terminal_id is required"},
                room=sid
            )
            return
            
        log.info(f"Client {sid} subscribing to context inference for terminal {terminal_id}")
        
        # Join context inference room
        await sio_instance.enter_room(sid, f"context_inference_{terminal_id}")
        
        try:
            # Get context inference engine
            from aetherterm.agentserver.context_inference.api import inference_engine
            
            if inference_engine:
                # Perform immediate context inference
                result = await inference_engine.infer_current_operation(terminal_id)
                
                # Send current context to client
                await sio_instance.emit(
                    "context_inference_result",
                    {
                        "terminal_id": result.terminal_id,
                        "operation_type": result.primary_context.operation_type.value,
                        "stage": result.primary_context.stage.value,
                        "confidence": result.primary_context.confidence,
                        "progress_percentage": result.primary_context.progress_percentage,
                        "command_sequence": result.primary_context.command_sequence,
                        "next_commands": result.primary_context.next_likely_commands,
                        "recommendations": result.recommendations,
                        "warnings": result.warnings,
                        "timestamp": result.timestamp.isoformat()
                    },
                    room=sid
                )
            else:
                await sio_instance.emit(
                    "context_inference_error",
                    {"error": "Context inference engine not available"},
                    room=sid
                )
                
        except Exception as e:
            log.error(f"Error performing context inference: {e}")
            await sio_instance.emit(
                "context_inference_error",
                {"error": f"Context inference failed: {str(e)}"},
                room=sid
            )
            
    except Exception as e:
        log.error(f"Error subscribing to context inference: {e}")
        await sio_instance.emit(
            "context_inference_error",
            {"error": str(e)},
            room=sid
        )


async def predict_next_commands(sid, data):
    """Predict next commands for a terminal."""
    try:
        terminal_id = data.get("terminal_id")
        limit = data.get("limit", 5)
        
        if not terminal_id:
            await sio_instance.emit(
                "context_inference_error",
                {"error": "terminal_id is required"},
                room=sid
            )
            return
            
        log.info(f"Predicting next commands for terminal {terminal_id}")
        
        try:
            from aetherterm.agentserver.context_inference.api import inference_engine
            
            if inference_engine:
                # Get current context or infer it
                active_context = inference_engine.active_contexts.get(terminal_id)
                
                if not active_context:
                    result = await inference_engine.infer_current_operation(terminal_id)
                    active_context = result.primary_context
                
                # Send next command predictions
                await sio_instance.emit(
                    "next_commands_prediction",
                    {
                        "terminal_id": terminal_id,
                        "next_commands": active_context.next_likely_commands[:limit],
                        "confidence": active_context.confidence,
                        "operation_type": active_context.operation_type.value
                    },
                    room=sid
                )
            else:
                await sio_instance.emit(
                    "context_inference_error",
                    {"error": "Context inference engine not available"},
                    room=sid
                )
                
        except Exception as e:
            log.error(f"Error predicting next commands: {e}")
            await sio_instance.emit(
                "context_inference_error",  
                {"error": f"Command prediction failed: {str(e)}"},
                room=sid
            )
            
    except Exception as e:
        log.error(f"Error handling predict next commands: {e}")
        await sio_instance.emit(
            "context_inference_error",
            {"error": str(e)},
            room=sid
        )


async def get_operation_analytics(sid, data):
    """Get operation analytics for a terminal."""
    try:
        terminal_id = data.get("terminal_id")
        days = data.get("days", 7)
        
        if not terminal_id:
            await sio_instance.emit(
                "context_inference_error",
                {"error": "terminal_id is required"},
                room=sid
            )
            return
            
        log.info(f"Getting operation analytics for terminal {terminal_id}")
        
        try:
            # Simple mock analytics for now - would be replaced with real analysis
            analytics = {
                "terminal_id": terminal_id,
                "analysis_period_days": days,
                "total_operations": 25,
                "success_rate": 0.88,
                "most_common_operations": [
                    {"type": "development", "count": 12},
                    {"type": "testing", "count": 8},
                    {"type": "debugging", "count": 5}
                ],
                "average_duration_by_type": {
                    "development": 1800,  # 30 minutes
                    "testing": 900,      # 15 minutes
                    "debugging": 2400    # 40 minutes
                },
                "efficiency_trend": "improving"
            }
            
            await sio_instance.emit(
                "operation_analytics",
                analytics,
                room=sid
            )
                
        except Exception as e:
            log.error(f"Error getting operation analytics: {e}")
            await sio_instance.emit(
                "context_inference_error",
                {"error": f"Analytics retrieval failed: {str(e)}"},
                room=sid
            )
            
    except Exception as e:
        log.error(f"Error handling get operation analytics: {e}")
        await sio_instance.emit(
            "context_inference_error",
            {"error": str(e)},
            room=sid
        )
