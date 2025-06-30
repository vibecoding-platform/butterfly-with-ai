"""
Theme Routes - Theme Management Endpoints

Provides theme-related routes for CSS serving and theme management.
"""

import logging
import os
from mimetypes import guess_type

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response

# Initialize router
router = APIRouter()
log = logging.getLogger("aetherterm.routes.theme")


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
    builtin_themes_dir = os.path.join(os.path.dirname(__file__), "..", "themes")

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
    sass_path = os.path.join(os.path.dirname(__file__), "..", "sass")

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
    builtin_themes_dir = os.path.join(os.path.dirname(__file__), "..", "themes")

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


@router.get("/themes/list.json")
async def themes_list():
    """Get the list of available themes."""
    themes_dir = os.path.join(os.path.expanduser("~"), ".config", "aetherterm", "themes")
    builtin_themes_dir = os.path.join(os.path.dirname(__file__), "..", "themes")

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
