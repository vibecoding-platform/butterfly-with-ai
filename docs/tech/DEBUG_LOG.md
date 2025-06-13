# Debug Log

This file contains debugging information and implementation notes for the Butterfly terminal emulator.

## Recent Implementation: MOTD (Message of the Day) Feature

### Date: 2025-06-13

#### Overview
Implemented MOTD (Message of the Day) functionality that displays a welcome message with connection information when users connect to the terminal.

#### Changes Made

1. **Template System**
   - Renamed `butterfly/templates/motd` to `butterfly/templates/motd.j2`
   - Fixed Jinja2 template syntax (`{% end %}` → `{% endif %}`)
   - Added proxy address display support
   - Updated `pyproject.toml` package data configuration

2. **Core Implementation**
   - Added `render_motd()` function in `butterfly/utils.py`
   - Implemented Jinja2 template rendering with context variables:
     - `colors`: ANSI color codes
     - `version`: Butterfly version
     - `butterfly.socket`: Connection information
     - `opts`: Configuration options
     - `uri`: Connection URI

3. **Terminal Integration**
   - Added `_send_motd_direct()` method to `AsyncioTerminal` class
   - MOTD sent via socket (not PTY) before shell starts
   - Proper line ending handling (`\r\n` format)
   - Reconnection detection to avoid duplicate MOTD display

4. **Development Improvements**
   - Added hot reload support in debug mode (uvicorn `--reload`)
   - Enhanced socket information extraction for accurate client details

#### Technical Details

**Template Context Variables:**
```python
context = {
    'colors': ansi_colors,           # ANSI color codes
    'version': __version__,          # Butterfly version
    'butterfly': butterfly_obj,      # Socket connection info
    'opts': opts,                    # Configuration options
    'uri': uri                       # Connection URI
}
```

**Socket Information:**
- Local address and port
- Remote address and port
- Proxy address (if applicable)
- Security status (secure/unsecure)

#### Issues Resolved
- MOTD not displaying colors → Fixed by sending via socket instead of PTY
- Line breaks not working → Fixed with `\r\n` line endings
- Duplicate MOTD on reconnect → Added session tracking
- Missing proxy information → Added proxy_addr support
- Development workflow → Added hot reload in debug mode

#### Files Modified
- `butterfly/templates/motd.j2` (renamed and updated)
- `butterfly/utils.py` (added render_motd function)
- `butterfly/terminals/asyncio_terminal.py` (added MOTD display logic)
- `butterfly/server.py` (added reload option)
- `butterfly/socket_handlers.py` (improved socket info extraction)
- `pyproject.toml` (updated package data)

## Current Issues

- Remote port sometimes shows as 0 (Socket.IO limitation)
- Hot reload may not work perfectly with Socket.IO connections

## Implementation Notes

- Using FastAPI with Socket.IO for real-time communication
- Terminal sessions managed through AsyncioTerminal class
- Dependency injection implemented using dependency-injector
- MOTD rendered server-side and sent to client via socket