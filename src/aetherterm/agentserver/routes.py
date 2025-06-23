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


@router.get("/api/terminal/status")
async def terminal_status():
    """Get terminal configuration and status information."""
    try:
        from aetherterm.agentserver.config.terminal_config import get_terminal_status

        return JSONResponse(get_terminal_status())
    except Exception as e:
        log.error(f"Error getting terminal status: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/terminal/config")
async def set_terminal_config(request: Request):
    """Set terminal configuration."""
    try:
        from aetherterm.agentserver.config.terminal_config import get_terminal_config
        from aetherterm.agentserver.terminals.terminal_factory import (
            get_terminal_factory,
            TerminalType,
        )

        data = await request.json()
        terminal_type_str = data.get("default_type")

        if not terminal_type_str:
            return JSONResponse({"error": "default_type is required"}, status_code=400)

        # Validate terminal type
        try:
            terminal_type = TerminalType(terminal_type_str)
        except ValueError:
            available_types = [t.value for t in TerminalType]
            return JSONResponse(
                {"error": f"Invalid terminal type. Available types: {available_types}"},
                status_code=400,
            )

        # Update configuration
        config = get_terminal_config()
        if not config.is_type_available(terminal_type):
            return JSONResponse(
                {"error": f"Terminal type '{terminal_type.value}' is not available"},
                status_code=400,
            )

        config.set_default_type(terminal_type)

        # Update factory
        factory = get_terminal_factory()
        factory.set_default_type(terminal_type)

        log.info(f"Terminal configuration updated to use {terminal_type.value} by default")

        return JSONResponse(
            {
                "success": True,
                "default_type": terminal_type.value,
                "message": f"Default terminal type set to {terminal_type.value}",
            }
        )

    except Exception as e:
        log.error(f"Error setting terminal config: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
