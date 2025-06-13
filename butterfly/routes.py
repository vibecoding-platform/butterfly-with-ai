# *-* coding: utf-8 *-*
# This file is part of butterfly
#
# butterfly Copyright(C) 2015-2017 Florian Mounier
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
from uuid import uuid4

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from butterfly.containers import ApplicationContainer

# Initialize FastAPI router
router = APIRouter()

# Setup Jinja2Templates for HTML rendering
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)

log = logging.getLogger("butterfly.routes")


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
):
    """Main index route that serves the terminal interface."""
    # Check for session parameter in query string, otherwise generate new session
    query_session = request.query_params.get("session")
    session = query_session or str(uuid4())
    return templates.TemplateResponse(
        "index.html", {"request": request, "session": session}
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
    themes_dir = os.path.join(os.path.expanduser("~"), ".config", "butterfly", "themes")
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
    themes_dir = os.path.join(os.path.expanduser("~"), ".config", "butterfly", "themes")
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
    unsecure=Provide[ApplicationContainer.config.unsecure]
):
    """Get the list of active sessions."""
    # Check if remote authentication is being used
    is_remote_authentication = bool(
        request.headers.get("authorization") or
        request.headers.get("x-forwarded-proto") == "https" or
        request.headers.get("x-forwarded-for") or
        request.cookies.get("session") or
        request.cookies.get("auth_token")
    )
    
    # Allow access if not unsecure, or if unsecure but with remote authentication
    if unsecure and not is_remote_authentication:
        raise HTTPException(status_code=403, detail="Not available in unsecure mode without remote authentication")

    # TODO: Implement proper session listing when terminal sessions are implemented
    # For now, return empty list
    return JSONResponse({"sessions": [], "user": "unknown"})


@router.get("/themes/list.json")
async def themes_list():
    """Get the list of available themes."""
    themes_dir = os.path.join(os.path.expanduser("~"), ".config", "butterfly", "themes")
    builtin_themes_dir = os.path.join(os.path.dirname(__file__), "themes")

    themes = []
    if os.path.exists(themes_dir):
        themes = [
            theme
            for theme in os.listdir(themes_dir)
            if os.path.isdir(os.path.join(themes_dir, theme))
            and not theme.startswith(".")
        ]

    builtin_themes = []
    if os.path.exists(builtin_themes_dir):
        builtin_themes = [
            f"built-in-{theme}"
            for theme in os.listdir(builtin_themes_dir)
            if os.path.isdir(os.path.join(builtin_themes_dir, theme))
            and not theme.startswith(".")
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
    local_js_dir = os.path.join(
        os.path.expanduser("~"), ".config", "butterfly", "local.js"
    )

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
