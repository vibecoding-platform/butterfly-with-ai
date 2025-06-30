import logging
from uuid import uuid4
import asyncio
from datetime import datetime

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
    """Handle the creation of a new terminal session with optional agent configuration."""
    try:
        session_id = data.get("session", str(uuid4()))
        user_name = data.get("user", "")
        path = data.get("path", "")
        
        # P0 緊急対応: エージェント起動設定
        launch_mode = data.get("launch_mode", "default")  # default, agent
        agent_config = data.get("agent_config", {})
        agent_type = agent_config.get("agent_type")  # developer, reviewer, tester, architect, researcher
        requester_agent_id = data.get("requester_agent_id")  # MainAgentからの要請の場合

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

        # Create terminal instance with agent configuration
        log.debug(f"Creating AsyncioTerminal instance with launch_mode: {launch_mode}")
        
        # P0 緊急対応: エージェント起動コマンドの準備
        startup_command = None
        if launch_mode == "agent" and agent_type:
            # 特定エージェント起動コマンド
            startup_command = _build_agent_command(agent_type, agent_config)
        
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
        
        # Store agent configuration for tracking
        if launch_mode in ["agentshell", "agent"]:
            terminal_instance.agent_config = {
                "launch_mode": launch_mode,
                "agent_type": agent_type,
                "agent_config": agent_config,
                "requester_agent_id": requester_agent_id,
                "startup_command": startup_command,
                "agent_hierarchy": "sub" if requester_agent_id else "main",
                "parent_agent_id": requester_agent_id
            }

        # Associate terminal with client using the new client set
        terminal_instance.client_sids.add(sid)

        # Start the PTY
        log.debug("Starting PTY")
        await terminal_instance.start_pty()
        log.info(f"PTY started successfully for session {session_id}")

        # P0 緊急対応: エージェント自動起動
        if startup_command and launch_mode in ["agentshell", "agent"]:
            try:
                log.info(f"Auto-starting {launch_mode} with command: {startup_command}")
                await asyncio.sleep(1)  # PTY初期化待ち
                await terminal_instance.write(startup_command + "\n")
                
                # MainAgentに通知（ブロードキャスト形式）
                if requester_agent_id:
                    await sio_instance.emit(
                        "agent_message",
                        {
                            "message_type": "agent_start_response",
                            "requester_agent_id": requester_agent_id,
                            "session_id": session_id,
                            "agent_type": agent_type,
                            "agent_id": agent_config.get("agent_id"),
                            "status": "started",
                            "launch_mode": launch_mode,
                            "hierarchy": "sub",
                            "parent_agent_id": requester_agent_id,
                            "working_directory": agent_config.get("working_directory"),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                
                # 新しく起動したエージェントに初期情報を送信
                await asyncio.sleep(2)  # エージェントの初期化待ち
                await sio_instance.emit(
                    "agent_message",
                    {
                        "message_type": "agent_initialization",
                        "to_agent_id": agent_config.get("agent_id"),
                        "agent_info": {
                            "agent_id": agent_config.get("agent_id"),
                            "agent_type": agent_type,
                            "role": "sub_agent",
                            "hierarchy": "sub" if requester_agent_id else "main",
                            "parent_agent_id": requester_agent_id,
                            "working_directory": agent_config.get("working_directory"),
                            "session_id": session_id,
                            "launch_mode": launch_mode,
                            "server_info": {
                                "websocket_url": "ws://localhost:57575",
                                "rest_api_base": "http://localhost:57575/api/v1"
                            },
                            "capabilities": _get_agent_capabilities(agent_type),
                            "instructions": _get_agent_instructions(agent_type, requester_agent_id)
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            except Exception as e:
                log.error(f"Failed to auto-start agent: {e}")

        # Initialize log capture for this terminal
        if log_processing_manager:
            try:
                await log_processing_manager.initialize_terminal_capture(session_id)
                log.debug(f"Log capture initialized for session {session_id}")
            except Exception as e:
                log.error(f"Failed to initialize log capture for session {session_id}: {e}")

        # Notify client that terminal is ready
        response_data = {"session": session_id, "status": "ready"}
        if launch_mode in ["agentshell", "agent"]:
            response_data.update({
                "launch_mode": launch_mode,
                "agent_type": agent_type,
                "agent_config": agent_config
            })
            
        await sio_instance.emit("terminal_ready", response_data, room=sid)
        log.debug(f"Sent terminal_ready event to client {sid}")

    except Exception as e:
        log.error(f"Error creating terminal: {e}", exc_info=True)
        await sio_instance.emit("terminal_error", {"error": str(e)}, room=sid)


async def resume_terminal(sid, data):
    """Handle resuming an existing terminal session or create new if not found."""
    try:
        session_id = data.get("sessionId")
        tab_id = data.get("tabId")
        sub_type = data.get("subType")
        cols = data.get("cols", 80)
        rows = data.get("rows", 24)
        
        log.info(f"Resume terminal request for session {session_id} from client {sid}")
        
        if not session_id:
            log.warning("Resume terminal request without sessionId")
            await sio_instance.emit("terminal_error", {"error": "sessionId required for resume"}, room=sid)
            return
        
        # Check if session exists and is active
        if session_id in AsyncioTerminal.sessions:
            existing_terminal = AsyncioTerminal.sessions[session_id]
            if not existing_terminal.closed:
                log.info(f"Resuming existing active terminal session {session_id}")
                
                # Add this client to the existing terminal's client set
                existing_terminal.client_sids.add(sid)
                
                # Send terminal history to client if available
                if existing_terminal.history:
                    await sio_instance.emit(
                        "terminal_output",
                        {"session": session_id, "data": existing_terminal.history},
                        room=sid,
                    )
                
                # Notify client that terminal is ready (resumed)
                await sio_instance.emit(
                    "terminal_ready", 
                    {
                        "session": session_id, 
                        "status": "resumed",
                        "tabId": tab_id,
                        "subType": sub_type
                    }, 
                    room=sid
                )
                log.info(f"Terminal session {session_id} successfully resumed for client {sid}")
                return
            else:
                log.info(f"Session {session_id} exists but is closed, will create new terminal")
        else:
            log.info(f"Session {session_id} not found, will create new terminal")
        
        # Session doesn't exist or is closed - create new terminal with the provided session ID
        log.info(f"Creating new terminal session with ID {session_id}")
        
        # Use create_terminal to create new session with specified session_id
        await create_terminal(
            sid,
            {
                "session": session_id,
                "tabId": tab_id,
                "subType": sub_type,
                "cols": cols,
                "rows": rows,
                "user": "",
                "path": ""
            }
        )
        
    except Exception as e:
        log.error(f"Error resuming terminal: {e}", exc_info=True)
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


def _build_agent_command(agent_type: str, agent_config: dict) -> str:
    """
    MainAgentの指示に基づいて起動コマンドを構築
    
    Args:
        agent_type: エージェントタイプ (developer, reviewer, tester, architect, researcher)
        agent_config: エージェント設定
    
    Returns:
        起動コマンド文字列
    """
    agent_id = agent_config.get("agent_id", f"{agent_type}_agent")
    working_dir = agent_config.get("working_directory", ".")
    requester_agent_id = agent_config.get("requester_agent_id")
    startup_method = agent_config.get("startup_method", "claude_cli")
    custom_startup_command = agent_config.get("custom_startup_command")
    custom_env_vars = agent_config.get("custom_environment_vars", {})
    
    # 共通の環境変数設定
    base_env_vars = [
        f"AGENT_ID={agent_id}",
        f"AGENT_TYPE={agent_type}",
        f"AGENT_ROLE=sub_agent",
        f"AETHERTERM_SERVER=ws://localhost:57575",
    ]
    
    # 要求元エージェントがある場合は追加
    if requester_agent_id:
        base_env_vars.append(f"PARENT_AGENT_ID={requester_agent_id}")
        base_env_vars.append(f"AGENT_HIERARCHY=sub")
    else:
        base_env_vars.append(f"AGENT_HIERARCHY=main")
    
    # MainAgentが指定したカスタム環境変数を追加
    for key, value in custom_env_vars.items():
        base_env_vars.append(f"{key}={value}")
    
    env_vars_str = " ".join(base_env_vars)
    
    # MainAgentがカスタム起動コマンドを指定している場合
    if custom_startup_command:
        # プレースホルダーを置換
        command = custom_startup_command.format(
            agent_id=agent_id,
            agent_type=agent_type,
            working_directory=working_dir,
            parent_agent_id=requester_agent_id or ""
        )
        return f"cd {working_dir} && {env_vars_str} {command}"
    
    # 起動メソッド別のコマンド構築
    if startup_method == "docker":
        # Dockerコンテナでエージェントを起動
        docker_image = agent_config.get("docker_image", f"aether-agent-{agent_type}:latest")
        return f"cd {working_dir} && {env_vars_str} docker run --rm -v $(pwd):/workspace -e AGENT_ID={agent_id} -e AGENT_TYPE={agent_type} {docker_image}"
    
    elif startup_method == "custom_script":
        # カスタムスクリプトで起動
        script_path = agent_config.get("script_path", f"./scripts/start-{agent_type}-agent.sh")
        return f"cd {working_dir} && {env_vars_str} {script_path} {agent_id}"
    
    else:  # startup_method == "claude_cli" or default
        # エージェントタイプ別のClaude CLIコマンド構築
        if agent_type == "developer":
            return f"cd {working_dir} && {env_vars_str} claude --name {agent_id} --role developer --sub-agent"
        elif agent_type == "reviewer":
            return f"cd {working_dir} && {env_vars_str} claude --name {agent_id} --role reviewer --mode review --sub-agent"
        elif agent_type == "tester":
            return f"cd {working_dir} && {env_vars_str} claude --name {agent_id} --role tester --mode test --sub-agent"
        elif agent_type == "architect":
            return f"cd {working_dir} && {env_vars_str} claude --name {agent_id} --role architect --mode design --sub-agent"
        elif agent_type == "researcher":
            return f"cd {working_dir} && {env_vars_str} claude --name {agent_id} --role researcher --mode analyze --sub-agent"
        else:
            return f"cd {working_dir} && {env_vars_str} claude --name {agent_id} --sub-agent"


# P0 緊急対応: MainAgent-SubAgent通信ハンドラー
async def response_request(sid, data):
    """
    【廃止予定】SubAgentからMainAgentへの応答要請を処理
    
    注意: この関数は廃止予定です。代わりに agent_message イベントを直接使用してください。
    現在は後方互換性のため agent_message にリダイレクトしています。
    
    メッセージフォーマット:
    {
        "from_agent_id": "claude_tester_001",
        "to_agent_id": "claude_main_001", 
        "request_type": "code_review",
        "content": "Please review this implementation",
        "data": {
            "file_path": "src/components/Login.vue",
            "changes": "..."
        },
        "priority": "high",
        "timeout": 300
    }
    """
    try:
        # 廃止警告ログ
        log.warning("DEPRECATED: response_request event is deprecated. Use agent_message with message_type='response_request' instead.")
        
        from_agent_id = data.get("from_agent_id")
        to_agent_id = data.get("to_agent_id")
        request_type = data.get("request_type")
        content = data.get("content", "")
        request_data = data.get("data", {})
        priority = data.get("priority", "medium")
        timeout = data.get("timeout", 120)
        
        log.info(f"Response request from {from_agent_id} to {to_agent_id}: {request_type}")
        
        # 全エージェントにブロードキャスト（メッセージタイプで区別）
        await sio_instance.emit(
            "agent_message",
            {
                "message_type": "response_request",
                "message_id": data.get("message_id", str(uuid4())),
                "from_agent_id": from_agent_id,
                "to_agent_id": to_agent_id,
                "request_type": request_type,
                "content": content,
                "data": request_data,
                "priority": priority,
                "timeout": timeout,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        log.error(f"Error handling response request: {e}")
        await sio_instance.emit("error", {"message": f"Response request failed: {str(e)}"}, room=sid)


async def response_reply(sid, data):
    """
    【廃止予定】MainAgentからSubAgentへの応答返信を処理
    
    注意: この関数は廃止予定です。代わりに agent_message イベントを直接使用してください。
    現在は後方互換性のため agent_message にリダイレクトしています。
    
    メッセージフォーマット:
    {
        "message_id": "uuid-of-original-request",
        "from_agent_id": "claude_main_001",
        "to_agent_id": "claude_tester_001",
        "status": "completed",
        "response": "The code looks good, but please add error handling",
        "data": {
            "suggestions": [...],
            "modified_files": [...]
        }
    }
    """
    try:
        # 廃止警告ログ
        log.warning("DEPRECATED: response_reply event is deprecated. Use agent_message with message_type='response_reply' instead.")
        
        message_id = data.get("message_id")
        from_agent_id = data.get("from_agent_id")
        to_agent_id = data.get("to_agent_id")
        status = data.get("status", "completed")
        response = data.get("response", "")
        response_data = data.get("data", {})
        
        log.info(f"Response reply from {from_agent_id} to {to_agent_id} for request {message_id}")
        
        # 全エージェントにブロードキャスト（メッセージタイプで区別）
        await sio_instance.emit(
            "agent_message",
            {
                "message_type": "response_reply",
                "message_id": message_id,
                "from_agent_id": from_agent_id,
                "to_agent_id": to_agent_id,
                "status": status,
                "response": response,
                "data": response_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        log.error(f"Error handling response reply: {e}")
        await sio_instance.emit("error", {"message": f"Response reply failed: {str(e)}"}, room=sid)


async def agent_start_request(sid, data):
    """
    エージェント起動要請を処理
    
    メッセージフォーマット:
    {
        "requester_agent_id": "claude_main_001",
        "agent_type": "tester",
        "agent_id": "claude_tester_002",
        "working_directory": "/workspace/project",
        "launch_mode": "agent",
        "startup_method": "claude_cli",  # claude_cli, docker, custom_script
        "startup_command": "claude --name {agent_id} --role {agent_type} --sub-agent",  # MainAgentが指定
        "environment_vars": {  # MainAgentが指定する環境変数
            "CUSTOM_VAR": "value",
            "PROJECT_NAME": "myproject"
        },
        "config": {
            "role": "tester",
            "mode": "test"
        }
    }
    """
    try:
        requester_agent_id = data.get("requester_agent_id")
        agent_type = data.get("agent_type")
        agent_id = data.get("agent_id", f"{agent_type}_agent")
        working_directory = data.get("working_directory", ".")
        launch_mode = data.get("launch_mode", "agent")
        
        # MainAgentが指定する起動方法
        startup_method = data.get("startup_method", "claude_cli")  # デフォルトはClaude CLI
        custom_startup_command = data.get("startup_command")  # MainAgentが指定するコマンド
        custom_env_vars = data.get("environment_vars", {})  # 追加環境変数
        
        config = data.get("config", {})
        
        log.info(f"Agent start request from {requester_agent_id}: {agent_type}:{agent_id} via {startup_method}")
        
        # 新しいターミナルセッションを作成
        session_id = str(uuid4())
        
        # エージェント設定に起動情報を追加
        agent_config = {
            "agent_type": agent_type,
            "agent_id": agent_id,
            "working_directory": working_directory,
            "startup_method": startup_method,
            "custom_startup_command": custom_startup_command,
            "custom_environment_vars": custom_env_vars,
            "requester_agent_id": requester_agent_id,
            **config
        }
        
        # create_terminal関数を呼び出してエージェント用ターミナルを作成
        await create_terminal(
            sid,
            {
                "session": session_id,
                "path": working_directory,
                "launch_mode": launch_mode,
                "agent_config": agent_config,
                "requester_agent_id": requester_agent_id
            }
        )
        
        log.info(f"Agent start request processed: session {session_id} created for {agent_type}:{agent_id}")
        
    except Exception as e:
        log.error(f"Error handling agent start request: {e}")
        await sio_instance.emit(
            "agent_message",
            {
                "message_type": "agent_start_response",
                "requester_agent_id": data.get("requester_agent_id"),
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


async def spec_upload(sid, data):
    """
    エージェント向け仕様ドキュメントのアップロード・配信
    
    メッセージフォーマット:
    {
        "from_agent_id": "claude_main_001",
        "spec_type": "project_requirements",  # project_requirements, api_spec, design_doc, user_story
        "title": "ユーザー認証システム仕様",
        "content": "...",  # 仕様内容
        "target_agents": ["claude_dev_001", "claude_test_001"],  # 対象エージェント（空の場合は全員）
        "priority": "high",
        "format": "markdown",  # markdown, json, yaml, plain
        "metadata": {
            "version": "1.0",
            "author": "Product Manager",
            "last_updated": "2025-01-29"
        }
    }
    """
    try:
        from_agent_id = data.get("from_agent_id")
        spec_type = data.get("spec_type")
        title = data.get("title")
        content = data.get("content")
        target_agents = data.get("target_agents", [])  # 空の場合は全エージェント
        priority = data.get("priority", "medium")
        format_type = data.get("format", "markdown")
        metadata = data.get("metadata", {})
        
        log.info(f"Spec upload from {from_agent_id}: {spec_type} - {title}")
        
        # 仕様ドキュメントをベクトルストレージに保存（検索可能にする）
        try:
            from aetherterm.langchain.storage.vector_adapter import VectorStorageAdapter
            # TODO: VectorStorageAdapterへの保存実装
        except ImportError:
            log.warning("VectorStorageAdapter not available for spec storage")
        
        # 全エージェントまたは指定エージェントに配信
        await sio_instance.emit(
            "agent_message",
            {
                "message_type": "spec_document",
                "from_agent_id": from_agent_id,
                "target_agents": target_agents,
                "spec_type": spec_type,
                "title": title,
                "content": content,
                "priority": priority,
                "format": format_type,
                "metadata": metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        log.info(f"Spec document '{title}' distributed to {len(target_agents) if target_agents else 'all'} agents")
        
    except Exception as e:
        log.error(f"Error handling spec upload: {e}")
        await sio_instance.emit("error", {"message": f"Spec upload failed: {str(e)}"}, room=sid)


async def spec_query(sid, data):
    """
    エージェントによる仕様問い合わせ
    
    メッセージフォーマット:
    {
        "from_agent_id": "claude_dev_001",
        "query": "ユーザー認証のAPIエンドポイント仕様は？",
        "spec_types": ["api_spec", "project_requirements"],  # 検索対象の仕様タイプ
        "context": "現在LoginForm.vueの実装中"
    }
    """
    try:
        from_agent_id = data.get("from_agent_id")
        query = data.get("query")
        spec_types = data.get("spec_types", [])
        context = data.get("context", "")
        
        log.info(f"Spec query from {from_agent_id}: {query}")
        
        # TODO: ベクトル検索で関連仕様を取得
        # 現在はモックレスポンス
        search_results = [
            {
                "title": "ユーザー認証API仕様",
                "spec_type": "api_spec",
                "content": "POST /api/auth/login - ユーザーログイン処理...",
                "relevance_score": 0.95
            }
        ]
        
        # 検索結果を返信
        await sio_instance.emit(
            "agent_message",
            {
                "message_type": "spec_query_response",
                "to_agent_id": from_agent_id,
                "query": query,
                "results": search_results,
                "total_results": len(search_results),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        log.error(f"Error handling spec query: {e}")
        await sio_instance.emit("error", {"message": f"Spec query failed: {str(e)}"}, room=sid)


async def control_message(sid, data):
    """
    システム制御メッセージを処理
    
    メッセージフォーマット:
    {
        "from_agent_id": "claude_main_001",
        "control_type": "pause_all",  # pause_all, resume_all, shutdown_agent, restart_agent
        "target_agent_id": "claude_tester_001",  # 特定エージェント対象の場合
        "data": {}
    }
    """
    try:
        from_agent_id = data.get("from_agent_id")
        control_type = data.get("control_type")
        target_agent_id = data.get("target_agent_id")
        control_data = data.get("data", {})
        
        log.info(f"Control message from {from_agent_id}: {control_type} -> {target_agent_id or 'all'}")
        
        # システム制御メッセージをブロードキャスト
        await sio_instance.emit(
            "agent_message",
            {
                "message_type": "control_message",
                "from_agent_id": from_agent_id,
                "control_type": control_type,
                "target_agent_id": target_agent_id,
                "data": control_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        log.error(f"Error handling control message: {e}")
        await sio_instance.emit("error", {"message": f"Control message failed: {str(e)}"}, room=sid)


def _get_agent_capabilities(agent_type: str) -> list:
    """
    エージェントタイプ別の能力一覧を取得
    """
    capabilities_map = {
        "developer": [
            "code_generation",
            "debugging",
            "refactoring",
            "api_implementation",
            "frontend_development",
            "backend_development",
            "git_operations"
        ],
        "reviewer": [
            "code_review",
            "security_analysis",
            "performance_analysis",
            "best_practices_check",
            "documentation_review",
            "test_coverage_analysis"
        ],
        "tester": [
            "test_generation",
            "unit_testing",
            "integration_testing",
            "e2e_testing",
            "test_automation",
            "bug_reporting",
            "test_coverage_measurement"
        ],
        "architect": [
            "system_design",
            "architecture_analysis",
            "technology_selection",
            "scalability_planning",
            "database_design",
            "api_design",
            "documentation_generation"
        ],
        "researcher": [
            "information_gathering",
            "technology_research",
            "best_practices_research",
            "competitive_analysis",
            "documentation_analysis",
            "trend_analysis"
        ]
    }
    
    return capabilities_map.get(agent_type, ["general_assistance"])


def _get_agent_instructions(agent_type: str, parent_agent_id: str = None) -> dict:
    """
    エージェントタイプ別の初期指示を取得
    """
    base_instructions = {
        "role_description": f"You are a {agent_type} agent in the AetherTerm platform.",
        "hierarchy_info": "You are a sub-agent" if parent_agent_id else "You are a main agent",
        "communication_protocol": {
            "websocket_events": [
                "agent_message",
                "response_request",
                "response_reply",
                "spec_query",
                "control_message"
            ],
            "message_filtering": "Filter messages by to_agent_id or process broadcasts",
            "parent_communication": f"Report to parent agent: {parent_agent_id}" if parent_agent_id else None
        },
        "server_integration": {
            "websocket_url": "ws://localhost:57575",
            "api_base": "http://localhost:57575/api/v1",
            "spec_query_endpoint": "/api/v1/specs/query",
            "agent_status_endpoint": "/api/v1/agents/status"
        }
    }
    
    type_specific_instructions = {
        "developer": {
            "primary_tasks": [
                "Implement features based on specifications",
                "Write clean, maintainable code",
                "Follow coding standards and best practices",
                "Collaborate with other agents for reviews and testing"
            ],
            "collaboration_pattern": [
                "Request code reviews from reviewer agents",
                "Coordinate with tester agents for test cases",
                "Consult architect agents for design decisions"
            ]
        },
        "reviewer": {
            "primary_tasks": [
                "Review code for quality and security",
                "Provide constructive feedback",
                "Ensure compliance with standards",
                "Identify potential issues and improvements"
            ],
            "collaboration_pattern": [
                "Respond to review requests from developer agents",
                "Coordinate with architect agents for design reviews",
                "Work with tester agents on test strategy"
            ]
        },
        "tester": {
            "primary_tasks": [
                "Generate comprehensive test cases",
                "Execute automated and manual tests",
                "Report bugs and issues",
                "Measure and improve test coverage"
            ],
            "collaboration_pattern": [
                "Coordinate with developer agents for test requirements",
                "Work with reviewer agents on test strategies",
                "Report findings to all relevant agents"
            ]
        },
        "architect": {
            "primary_tasks": [
                "Design system architecture",
                "Make technology decisions",
                "Create technical documentation",
                "Guide implementation decisions"
            ],
            "collaboration_pattern": [
                "Provide guidance to developer agents",
                "Collaborate with reviewer agents on design reviews",
                "Work with researcher agents on technology selection"
            ]
        },
        "researcher": {
            "primary_tasks": [
                "Research technologies and best practices",
                "Analyze requirements and constraints",
                "Provide recommendations",
                "Gather relevant documentation"
            ],
            "collaboration_pattern": [
                "Provide research findings to all agent types",
                "Support architect agents with technology analysis",
                "Assist developer agents with implementation research"
            ]
        }
    }
    
    base_instructions.update(type_specific_instructions.get(agent_type, {}))
    
    # 親エージェントがいる場合の追加指示
    if parent_agent_id:
        base_instructions["parent_agent_communication"] = {
            "reporting_schedule": "Report progress regularly to parent agent",
            "escalation_rules": "Escalate blocking issues to parent agent",
            "completion_notification": "Notify parent agent when tasks are completed",
            "parent_agent_id": parent_agent_id
        }
    
    return base_instructions


async def agent_hello(sid, data):
    """
    エージェントからの初期接続メッセージを処理
    
    メッセージフォーマット:
    {
        "agent_id": "claude_dev_001",
        "agent_type": "developer",
        "version": "1.0.0",
        "capabilities": [...],
        "request_initialization": true
    }
    """
    try:
        agent_id = data.get("agent_id")
        agent_type = data.get("agent_type")
        version = data.get("version", "unknown")
        capabilities = data.get("capabilities", [])
        
        log.info(f"Agent hello from {agent_id} ({agent_type}) version {version}")
        
        # エージェント情報を登録/更新
        agent_info = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "version": version,
            "capabilities": capabilities,
            "status": "connected",
            "connected_at": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat()
        }
        
        # エージェント情報をグローバルストレージに保存（TODO: 実装）
        # store_agent_info(agent_id, agent_info)
        
        # 既存のターミナルセッションからエージェント情報を取得
        parent_agent_id = None
        agent_hierarchy = "main"
        
        # ターミナルセッションからエージェント設定を検索
        from aetherterm.agentserver.terminals.asyncio_terminal import AsyncioTerminal
        for session_id, terminal in AsyncioTerminal.sessions.items():
            if hasattr(terminal, 'agent_config') and terminal.agent_config:
                agent_config = terminal.agent_config.get("agent_config", {})
                if agent_config.get("agent_id") == agent_id:
                    parent_agent_id = terminal.agent_config.get("parent_agent_id")
                    agent_hierarchy = terminal.agent_config.get("agent_hierarchy", "main")
                    break
        
        # エージェントに初期化情報を送信
        await sio_instance.emit(
            "agent_message",
            {
                "message_type": "agent_initialization",
                "to_agent_id": agent_id,
                "agent_info": {
                    "agent_id": agent_id,
                    "agent_type": agent_type,
                    "role": "sub_agent" if parent_agent_id else "main_agent",
                    "hierarchy": agent_hierarchy,
                    "parent_agent_id": parent_agent_id,
                    "server_info": {
                        "websocket_url": "ws://localhost:57575",
                        "rest_api_base": "http://localhost:57575/api/v1"
                    },
                    "capabilities": _get_agent_capabilities(agent_type),
                    "instructions": _get_agent_instructions(agent_type, parent_agent_id)
                },
                "welcome_message": f"Welcome {agent_id}! You are a {agent_hierarchy} {agent_type} agent.",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # 他のエージェントに新しいエージェントの参加を通知
        await sio_instance.emit(
            "agent_message",
            {
                "message_type": "agent_joined",
                "agent_info": {
                    "agent_id": agent_id,
                    "agent_type": agent_type,
                    "hierarchy": agent_hierarchy,
                    "capabilities": capabilities
                },
                "announcement": f"Agent {agent_id} ({agent_type}) has joined the workspace.",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        log.error(f"Error handling agent hello: {e}")
        await sio_instance.emit("error", {"message": f"Agent hello failed: {str(e)}"}, room=sid)


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
