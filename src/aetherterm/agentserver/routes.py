# *-* coding: utf-8 *-*
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

from aetherterm.agentserver.containers import ApplicationContainer
from aetherterm.config import get_config_manager

# Initialize FastAPI router
router = APIRouter()

log = logging.getLogger("aetherterm.routes")

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
                with open(file_path, "r", encoding="utf-8") as f:
                    js_content += f.read() + ";\n"
            except Exception as e:
                log.warning(f"Could not read {file_path}: {e}")

    return Response(content=js_content, media_type="application/javascript")


@router.get("/api/config")
@inject
async def get_config(
    request: Request,
    config=Provide[ApplicationContainer.config],
):
    """Get configuration for frontend."""
    try:
        config_manager = get_config_manager()
        
        # フロントエンドに送信する設定を準備
        frontend_config = {
            "version": {
                "schema": config_manager.get_schema_version(),
                "product": "0.1.0"
            },
            "features": {
                "ai_enabled": config_manager.is_feature_enabled("ai_enabled"),
                "multi_tab_enabled": config_manager.is_feature_enabled("multi_tab_enabled"),
                "supervisor_panel_enabled": config_manager.is_feature_enabled("supervisor_panel_enabled"),
                "dev_tools_enabled": config_manager.is_feature_enabled("dev_tools_enabled"),
            },
            "ui": {
                "theme": config_manager.get_value("ui.theme", "dark"),
                "panel_position": config_manager.get_value("ui.panel_position", "right"),
                "panel_width": config_manager.get_value("ui.panel_width", 320),
                "remember_layout": config_manager.get_value("ui.remember_layout", True),
            },
            "ai": {
                "provider": config_manager.get_value("ai.chat.provider", "anthropic"),
                "model": config_manager.get_value("ai.chat.model", "claude-3-5-sonnet-20241022"),
                "max_messages": config_manager.get_value("ai.chat.max_messages", 100),
                "auto_context": config_manager.get_value("ai.chat.auto_context", True),
            },
            "terminal": {
                "shell": config_manager.get_value("terminal.shell", "auto"),
                "force_unicode_width": config_manager.get_value("terminal.force_unicode_width", False),
            },
            "server": {
                "host": config_manager.get_value("server.host", "localhost"),
                "port": config_manager.get_value("server.port", 57575),
                "debug": config_manager.get_value("server.debug", False),
            }
        }
        
        return JSONResponse(frontend_config)
        
    except Exception as e:
        log.error(f"Error getting config for frontend: {e}")
        return JSONResponse(
            {"error": "Failed to load configuration", "details": str(e)},
            status_code=500
        )


@router.get("/api/config/summary")
@inject 
async def get_config_summary(
    request: Request,
    config=Provide[ApplicationContainer.config],
):
    """Get configuration summary for admin/debug purposes."""
    try:
        config_manager = get_config_manager()
        summary = config_manager.get_config_summary()
        
        return JSONResponse(summary)
        
    except Exception as e:
        log.error(f"Error getting config summary: {e}")
        return JSONResponse(
            {"error": "Failed to load configuration summary", "details": str(e)},
            status_code=500
        )
