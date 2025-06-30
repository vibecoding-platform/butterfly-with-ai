# This file is part of aetherterm
#
# aetherterm Copyright(C) 2015-2017 Florian Mounier
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
from mimetypes import guess_type

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import uuid4
from datetime import datetime

from aetherterm.agentserver.containers import ApplicationContainer
from aetherterm.agentserver.api.log_processing_api import router as log_processing_router
from aetherterm.agentserver.api.inventory_api import inventory_router

# Initialize FastAPI router
router = APIRouter()

# Include inventory API routes
router.include_router(inventory_router)

# Include log processing API routes
router.include_router(log_processing_router)

# Include JupyterHub management API routes
from aetherterm.agentserver.jupyterhub_management import router as jupyterhub_router

router.include_router(jupyterhub_router)

log = logging.getLogger("aetherterm.routes")


async def _create_agent_terminal_via_rest(
    session_id: str,
    agent_id: str,
    agent_type: str,
    working_directory: str,
    launch_mode: str,
    agent_config: dict,
    requester_agent_id: str,
    startup_command: str
) -> bool:
    """
    REST API経由でエージェント用ターミナルを作成する専用関数
    
    Returns:
        bool: ターミナル作成の成功・失敗
    """
    try:
        from aetherterm.agentserver.socket_handlers import sio_instance
        from aetherterm.agentserver.terminals.asyncio_terminal import AsyncioTerminal
        from aetherterm.agentserver import utils
        import asyncio
        
        if not sio_instance:
            log.error("Socket.IO instance not available")
            return False
        
        # REST API用の仮想接続情報を作成
        virtual_environ = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": f"AetherTerm-RestAPI/{agent_type}",
            "HTTP_X_REMOTE_USER": f"agent_{agent_id}",
            "REQUEST_METHOD": "POST",
            "PATH_INFO": f"/api/v1/agents/start"
        }
        
        socket = utils.ConnectionInfo(virtual_environ)
        
        # ターミナルインスタンスを作成
        terminal_instance = AsyncioTerminal(
            user=None,  # エージェント用なのでユーザーはNone
            path=working_directory,
            session=session_id,
            socket=socket,
            uri=f"http://127.0.0.1:57575/?session={session_id}",
            render_string=None,
            broadcast=lambda s, m: _rest_api_broadcast(s, m),
            login=False,  # エージェント用なのでログイン不要
            pam_profile="",
        )
        
        # エージェント設定を保存
        terminal_instance.agent_config = {
            "launch_mode": launch_mode,
            "agent_type": agent_type,
            "agent_config": agent_config,
            "requester_agent_id": requester_agent_id,
            "startup_command": startup_command,
            "agent_hierarchy": "sub" if requester_agent_id else "main",
            "parent_agent_id": requester_agent_id,
            "created_via": "rest_api"
        }
        
        # REST API専用のクライアントセットを初期化
        terminal_instance.client_sids = set()
        
        # PTYを開始
        await terminal_instance.start_pty()
        log.info(f"REST API: PTY started successfully for session {session_id}")
        
        # エージェント自動起動
        if startup_command and launch_mode in ["agentshell", "agent"]:
            await asyncio.sleep(1)  # PTY初期化待ち
            await terminal_instance.write(startup_command + "\n")
            
            # MainAgentに通知
            if requester_agent_id and sio_instance:
                await sio_instance.emit(
                    "agent_message",
                    {
                        "message_type": "agent_start_response",
                        "requester_agent_id": requester_agent_id,
                        "session_id": session_id,
                        "agent_type": agent_type,
                        "agent_id": agent_id,
                        "status": "started",
                        "launch_mode": launch_mode,
                        "hierarchy": "sub",
                        "parent_agent_id": requester_agent_id,
                        "working_directory": working_directory,
                        "created_via": "rest_api",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            
            log.info(f"REST API: Agent {agent_type}:{agent_id} started successfully")
        
        return True
        
    except Exception as e:
        log.error(f"REST API terminal creation failed: {e}")
        return False


def _rest_api_broadcast(session_id: str, message: str):
    """
    REST API経由で作成されたターミナル用のブロードキャスト関数
    WebSocketクライアントがいない場合でも動作する
    """
    try:
        from aetherterm.agentserver.socket_handlers import sio_instance
        from aetherterm.agentserver.terminals.asyncio_terminal import AsyncioTerminal
        import asyncio
        
        # 通常のブロードキャストロジックを実行（WebSocketクライアント向け）
        terminal = AsyncioTerminal.sessions.get(session_id)
        if terminal and hasattr(terminal, "client_sids") and terminal.client_sids:
            # WebSocketクライアントがいる場合は通常通りブロードキャスト
            for client_sid in list(terminal.client_sids):
                if sio_instance:
                    asyncio.create_task(
                        sio_instance.emit(
                            "terminal_output", 
                            {"session": session_id, "data": message}, 
                            room=client_sid
                        )
                    )
        
        # REST API用のログ記録（デバッグ用）
        if message and len(message.strip()) > 0:
            log.debug(f"REST API Terminal {session_id}: {message.strip()[:100]}")
            
    except Exception as e:
        log.error(f"REST API broadcast error: {e}")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Mount static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir) and os.listdir(static_dir):
    router.mount("/static", StaticFiles(directory=static_dir), name="static")


@router.get("/", response_class=HTMLResponse)
@inject
async def index(
    request: Request,
    config=Provide[ApplicationContainer.config],
):
    """Main index route that serves the terminal interface."""
    # Dynamically find the hashed asset filenames
    assets_dir = os.path.join(os.path.dirname(__file__), "static", "assets")
    js_bundle = ""
    css_bundle = ""
    # Get root path from configuration
    root_path = config.get("uri_root_path", "")

    for filename in os.listdir(assets_dir):
        if filename.startswith("index.") and filename.endswith(".js"):
            js_bundle = f"{root_path}/static/assets/{filename}"
        elif filename.startswith("index.") and filename.endswith(".css"):
            css_bundle = f"{root_path}/static/assets/{filename}"

    if not js_bundle or not css_bundle:
        raise HTTPException(status_code=500, detail="Could not find hashed JS or CSS files")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "js_bundle": js_bundle,
            "css_bundle": css_bundle,
            "favicon_path": f"{root_path}/static/favicon.ico",
            "uri_root_path": root_path,
        },
    )


@router.get("/theme/{theme}/style.css")
async def theme_style(theme: str):
    """Serve theme CSS files."""
    try:
        import sass
    except ImportError:
        log.error("You must install libsass to use sass (pip install libsass)")
        raise HTTPException(status_code=500, detail="Sass compiler not available")

    # Get theme directory
    themes_dir = os.path.join(os.path.expanduser("~"), ".config", "aetherterm", "themes")
    builtin_themes_dir = os.path.join(os.path.dirname(__file__), "themes")

    base_dir = None
    if theme.startswith("built-in-"):
        theme_name = theme[9:]  # Remove 'built-in-' prefix
        base_dir = os.path.join(builtin_themes_dir, theme_name)
    else:
        base_dir = os.path.join(themes_dir, theme)

    if not os.path.exists(base_dir):
        raise HTTPException(status_code=404, detail="Theme not found")

    # Look for style file
    style = None
    for ext in ["css", "scss", "sass"]:
        probable_style = os.path.join(base_dir, f"style.{ext}")
        if os.path.exists(probable_style):
            style = probable_style
            break

    if not style:
        raise HTTPException(status_code=404, detail="Style file not found")

    # Compile sass if needed
    sass_path = os.path.join(os.path.dirname(__file__), "sass")

    try:
        css = sass.compile(filename=style, include_paths=[base_dir, sass_path])
        return Response(content=css, media_type="text/css")
    except Exception as e:
        log.error(f"Unable to compile style: {e}")
        raise HTTPException(status_code=500, detail="Style compilation failed")


@router.get("/theme/{theme}/{filename:path}")
async def theme_static(theme: str, filename: str):
    """Serve static theme files."""
    if ".." in filename:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get theme directory
    themes_dir = os.path.join(os.path.expanduser("~"), ".config", "aetherterm", "themes")
    builtin_themes_dir = os.path.join(os.path.dirname(__file__), "themes")

    base_dir = None
    if theme.startswith("built-in-"):
        theme_name = theme[9:]  # Remove 'built-in-' prefix
        base_dir = os.path.join(builtin_themes_dir, theme_name)
    else:
        base_dir = os.path.join(themes_dir, theme)

    file_path = os.path.normpath(os.path.join(base_dir, filename))

    # Security check
    if not file_path.startswith(base_dir):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Determine content type
    content_type = guess_type(file_path)[0]
    if content_type is None:
        # Fallback content types
        ext = filename.split(".")[-1].lower()
        content_type = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "woff": "application/font-woff",
            "ttf": "application/x-font-ttf",
        }.get(ext, "text/plain")

    return FileResponse(file_path, media_type=content_type)


@router.get("/sessions/list.json")
@inject
async def sessions_list(
    request: Request,
    config=Provide[ApplicationContainer.config],
):
    """Get the list of active sessions."""
    # Check if remote authentication is being used
    is_remote_authentication = bool(
        request.headers.get("authorization")
        or request.headers.get("x-forwarded-proto") == "https"
        or request.headers.get("x-forwarded-for")
        or request.cookies.get("session")
        or request.cookies.get("auth_token")
    )

    # Security check: prevent access in unsecure mode without remote authentication
    unsecure = config.get("unsecure", False)
    if unsecure and not is_remote_authentication:
        raise HTTPException(
            status_code=403, detail="Not available in unsecure mode without remote authentication"
        )

    # TODO: Implement proper session listing when terminal sessions are implemented
    # For now, return empty list
    return JSONResponse({"sessions": [], "user": "unknown"})


@router.get("/themes/list.json")
async def themes_list():
    """Get the list of available themes."""
    themes_dir = os.path.join(os.path.expanduser("~"), ".config", "aetherterm", "themes")
    builtin_themes_dir = os.path.join(os.path.dirname(__file__), "themes")

    themes = []
    if os.path.exists(themes_dir):
        themes = [
            theme
            for theme in os.listdir(themes_dir)
            if os.path.isdir(os.path.join(themes_dir, theme)) and not theme.startswith(".")
        ]

    builtin_themes = []
    if os.path.exists(builtin_themes_dir):
        builtin_themes = [
            f"built-in-{theme}"
            for theme in os.listdir(builtin_themes_dir)
            if os.path.isdir(os.path.join(builtin_themes_dir, theme)) and not theme.startswith(".")
        ]

    return JSONResponse(
        {
            "themes": sorted(themes),
            "builtin_themes": sorted(builtin_themes),
            "dir": themes_dir,
        }
    )


@router.get("/local.js")
async def local_js():
    """Serve local JavaScript files."""
    local_js_dir = os.path.join(os.path.expanduser("~"), ".config", "aetherterm", "local.js")

    js_content = ""
    if os.path.exists(local_js_dir):
        for filename in os.listdir(local_js_dir):
            if not filename.endswith(".js"):
                continue
            file_path = os.path.join(local_js_dir, filename)
            try:
                with open(file_path, encoding="utf-8") as f:
                    js_content += f.read() + ";\n"
            except Exception as e:
                log.warning(f"Could not read {file_path}: {e}")

    return Response(content=js_content, media_type="application/javascript")


# P0 緊急対応: エージェント起動API
class AgentStartRequest(BaseModel):
    """Agent startup request model"""
    requester_agent_id: str
    agent_type: str  # developer, reviewer, tester, architect, researcher
    agent_id: Optional[str] = None
    working_directory: Optional[str] = "."
    launch_mode: str = "agent"
    startup_method: str = "claude_cli"  # claude_cli, docker, custom_script
    startup_command: Optional[str] = None  # MainAgentが指定するカスタムコマンド
    environment_vars: Dict[str, str] = {}  # 追加環境変数
    config: Dict[str, Any] = {}


class AgentStartResponse(BaseModel):
    """Agent startup response model"""
    session_id: str
    agent_id: str
    agent_type: str
    status: str  # started, failed
    working_directory: str
    startup_command: Optional[str] = None
    error: Optional[str] = None


@router.post("/api/v1/agents/start", response_model=AgentStartResponse)
async def start_agent(request: AgentStartRequest):
    """
    P0 緊急対応: エージェント動的起動API
    
    MainAgentが他のSubAgentを起動するためのREST APIエンドポイント
    
    Examples:
        # テストエージェントを起動
        POST /api/v1/agents/start
        {
            "requester_agent_id": "claude_main_001",
            "agent_type": "tester",
            "agent_id": "claude_tester_002",
            "working_directory": "/workspace/project",
            "config": {
                "role": "tester",
                "mode": "test"
            }
        }
        
        # レビューエージェントを起動
        POST /api/v1/agents/start
        {
            "requester_agent_id": "claude_main_001",
            "agent_type": "reviewer",
            "working_directory": "/workspace/frontend",
            "config": {
                "focus": "frontend",
                "standards": "vue3"
            }
        }
    """
    try:
        from aetherterm.agentserver.socket_handlers import _build_agent_command, create_terminal, sio_instance
        from aetherterm.agentserver.terminals.asyncio_terminal import AsyncioTerminal
        from aetherterm.agentserver import utils
        
        # Generate session and agent IDs
        session_id = str(uuid4())
        agent_id = request.agent_id or f"{request.agent_type}_{str(uuid4())[:8]}"
        
        # Build agent configuration with MainAgent's startup instructions
        agent_config = {
            "agent_type": request.agent_type,
            "agent_id": agent_id,
            "working_directory": request.working_directory,
            "startup_method": request.startup_method,
            "custom_startup_command": request.startup_command,
            "custom_environment_vars": request.environment_vars,
            "requester_agent_id": request.requester_agent_id,
            **request.config
        }
        
        # Build startup command
        startup_command = _build_agent_command(request.agent_type, agent_config)
        
        log.info(f"REST API agent start: {request.agent_type}:{agent_id} for {request.requester_agent_id}")
        
        # REST API経由でも実際にターミナルを作成する
        if sio_instance:
            try:
                # Socket.IOインスタンスが利用可能な場合、実際にターミナルを作成
                terminal_created = await _create_agent_terminal_via_rest(
                    session_id=session_id,
                    agent_id=agent_id,
                    agent_type=request.agent_type,
                    working_directory=request.working_directory,
                    launch_mode=request.launch_mode,
                    agent_config=agent_config,
                    requester_agent_id=request.requester_agent_id,
                    startup_command=startup_command
                )
                
                if terminal_created:
                    # ターミナル作成が成功した場合
                    return AgentStartResponse(
                        session_id=session_id,
                        agent_id=agent_id,
                        agent_type=request.agent_type,
                        status="started",  # 実際に起動した
                        working_directory=request.working_directory,
                        startup_command=startup_command
                    )
                else:
                    # ターミナル作成に失敗した場合
                    return AgentStartResponse(
                        session_id=session_id,
                        agent_id=agent_id,
                        agent_type=request.agent_type,
                        status="failed",
                        working_directory=request.working_directory,
                        startup_command=startup_command,
                        error="Terminal creation failed"
                    )
            except Exception as terminal_error:
                log.error(f"Terminal creation failed: {terminal_error}")
                # エラーが発生した場合でも起動情報は返す
                return AgentStartResponse(
                    session_id=session_id,
                    agent_id=agent_id,
                    agent_type=request.agent_type,
                    status="ready",  # 起動準備完了（手動でWebSocket接続が必要）
                    working_directory=request.working_directory,
                    startup_command=startup_command,
                    error=f"Auto-terminal creation failed: {str(terminal_error)}"
                )
        else:
            # Socket.IOインスタンスが利用できない場合、起動情報のみを返す
            return AgentStartResponse(
                session_id=session_id,
                agent_id=agent_id,
                agent_type=request.agent_type,
                status="ready",  # 起動準備完了（WebSocket接続が必要）
                working_directory=request.working_directory,
                startup_command=startup_command,
                error="Socket.IO not available - manual WebSocket connection required"
            )
        
    except Exception as e:
        log.error(f"Error in agent start API: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Agent startup failed",
                "message": str(e),
                "requester_agent_id": request.requester_agent_id
            }
        )


@router.get("/api/v1/agents/status")
async def get_agents_status():
    """
    アクティブなエージェントの状態を取得
    
    Returns:
        {
            "agents": [
                {
                    "session_id": "uuid",
                    "agent_id": "claude_tester_001",
                    "agent_type": "tester",
                    "status": "ready",
                    "working_directory": "/workspace",
                    "last_activity": "2025-01-29T12:34:56Z"
                }
            ],
            "total_agents": 3
        }
    """
    try:
        from aetherterm.agentserver.terminals.asyncio_terminal import AsyncioTerminal
        
        agents = []
        for session_id, terminal in AsyncioTerminal.sessions.items():
            if hasattr(terminal, 'agent_config') and terminal.agent_config:
                agent_config = terminal.agent_config
                agents.append({
                    "session_id": session_id,
                    "agent_id": agent_config.get("agent_config", {}).get("agent_id"),
                    "agent_type": agent_config.get("agent_type"),
                    "status": "ready" if not terminal.closed else "closed",
                    "working_directory": agent_config.get("agent_config", {}).get("working_directory"),
                    "launch_mode": agent_config.get("launch_mode"),
                    "requester_agent_id": agent_config.get("requester_agent_id")
                })
        
        return JSONResponse({
            "agents": agents,
            "total_agents": len(agents)
        })
        
    except Exception as e:
        log.error(f"Error getting agents status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agents status: {str(e)}")


# 仕様ドキュメント管理API
class SpecDocument(BaseModel):
    """Specification document model"""
    spec_type: str  # project_requirements, api_spec, design_doc, user_story
    title: str
    content: str
    target_agents: List[str] = []  # 空の場合は全エージェント
    priority: str = "medium"
    format: str = "markdown"  # markdown, json, yaml, plain
    metadata: Dict[str, Any] = {}


class SpecQuery(BaseModel):
    """Specification query model"""
    query: str
    spec_types: List[str] = []  # 検索対象の仕様タイプ
    context: str = ""


@router.post("/api/v1/specs/upload")
async def upload_specification(request: SpecDocument):
    """
    仕様ドキュメントをアップロードし、全エージェントに配信
    
    Examples:
        # プロジェクト要件をアップロード
        POST /api/v1/specs/upload
        {
            "spec_type": "project_requirements",
            "title": "ユーザー認証システム要件",
            "content": "# ユーザー認証\\n- OAuth 2.0対応\\n- JWTトークン...",
            "target_agents": ["claude_dev_001", "claude_test_001"],
            "priority": "high",
            "format": "markdown"
        }
        
        # API仕様をアップロード
        POST /api/v1/specs/upload
        {
            "spec_type": "api_spec",
            "title": "認証API仕様",
            "content": "...",
            "target_agents": [],  // 全エージェント
            "format": "yaml"
        }
    """
    try:
        # 仕様ドキュメントIDを生成
        spec_id = str(uuid4())
        
        # TODO: ベクトルストレージに保存して検索可能にする
        
        log.info(f"Spec upload: {request.spec_type} - {request.title}")
        
        return JSONResponse({
            "spec_id": spec_id,
            "status": "uploaded",
            "title": request.title,
            "spec_type": request.spec_type,
            "target_agents": request.target_agents,
            "distributed_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        log.error(f"Error uploading specification: {e}")
        raise HTTPException(status_code=500, detail=f"Specification upload failed: {str(e)}")


@router.post("/api/v1/specs/query")
async def query_specifications(request: SpecQuery):
    """
    仕様ドキュメントを検索
    
    Examples:
        POST /api/v1/specs/query
        {
            "query": "ユーザー認証のAPIエンドポイント仕様は？",
            "spec_types": ["api_spec"],
            "context": "現在LoginForm.vueの実装中"
        }
    """
    try:
        log.info(f"Spec query: {request.query}")
        
        # TODO: ベクトル検索で関連仕様を取得
        # 現在はモックレスポンス
        search_results = [
            {
                "spec_id": "spec-001",
                "title": "ユーザー認証API仕様",
                "spec_type": "api_spec",
                "content": "POST /api/auth/login - ユーザーログイン処理...",
                "relevance_score": 0.95,
                "updated_at": "2025-01-29T12:00:00Z"
            }
        ]
        
        return JSONResponse({
            "query": request.query,
            "results": search_results,
            "total_results": len(search_results),
            "search_time": "0.05s"
        })
        
    except Exception as e:
        log.error(f"Error querying specifications: {e}")
        raise HTTPException(status_code=500, detail=f"Specification query failed: {str(e)}")


@router.get("/api/v1/specs/list")
async def list_specifications(spec_type: Optional[str] = None):
    """
    仕様ドキュメント一覧を取得
    
    Args:
        spec_type: フィルターする仕様タイプ (optional)
    
    Examples:
        GET /api/v1/specs/list
        GET /api/v1/specs/list?spec_type=api_spec
    """
    try:
        # TODO: ストレージから仕様一覧を取得
        # 現在はモックデータ
        specs = [
            {
                "spec_id": "spec-001",
                "title": "ユーザー認証API仕様",
                "spec_type": "api_spec",
                "priority": "high",
                "format": "yaml",
                "created_at": "2025-01-29T10:00:00Z",
                "updated_at": "2025-01-29T12:00:00Z",
                "target_agents": ["claude_dev_001", "claude_test_001"]
            },
            {
                "spec_id": "spec-002",
                "title": "プロジェクト要件定義",
                "spec_type": "project_requirements",
                "priority": "medium",
                "format": "markdown",
                "created_at": "2025-01-29T09:00:00Z",
                "updated_at": "2025-01-29T11:00:00Z",
                "target_agents": []
            }
        ]
        
        # spec_typeでフィルター
        if spec_type:
            specs = [spec for spec in specs if spec["spec_type"] == spec_type]
        
        return JSONResponse({
            "specifications": specs,
            "total_count": len(specs),
            "spec_types": list(set(spec["spec_type"] for spec in specs))
        })
        
    except Exception as e:
        log.error(f"Error listing specifications: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list specifications: {str(e)}")
