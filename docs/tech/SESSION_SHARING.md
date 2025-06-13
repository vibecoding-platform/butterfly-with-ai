# Butterfly Terminal Session Sharing

This document describes the session sharing functionality implemented in Butterfly terminal.

## Overview

The Butterfly terminal now supports:
1. **Hidden WebSocket addresses** - MOTD no longer displays WebSocket connection details
2. **Session ID parameters** - Sessions can be accessed via URL parameters or path segments
3. **Session persistence** - Multiple clients can connect to the same terminal session
4. **Automatic cleanup** - Sessions are closed when all clients disconnect

## Usage

### 1. Accessing Sessions

#### Method 1: Query Parameter
```
http://localhost:57575/?session=my-session-id
```

#### Method 2: Auto-generated Session (Default)
```
http://localhost:57575/
```
This will generate a random UUID as the session ID.

### 2. Session Sharing

Multiple users can connect to the same session by using the same session ID:

**User 1 creates a session:**
```
http://localhost:57575/?session=shared-work-session
```

**User 2 joins the same session:**
```
http://localhost:57575/?session=shared-work-session
```

Both users will see the same terminal output and can interact with the same shell session.

### 3. Session Persistence

- Sessions remain active as long as at least one client is connected
- When all clients disconnect, the session is automatically terminated
- Terminal history is preserved and sent to new clients joining an existing session

## Implementation Details

### Backend Changes

1. **MOTD Template (`butterfly/templates/motd.j2`)**
   - Removed WebSocket URI display
   - Simplified security warnings

2. **Routes (`butterfly/routes.py`)**
   - Added support for session query parameters
   - Priority: query parameter > auto-generated

3. **Socket Handlers (`butterfly/socket_handlers.py`)**
   - Session reuse logic for existing active sessions
   - Multi-client support per session
   - Improved disconnect handling
   - Targeted broadcasting to session clients

4. **Terminal (`butterfly/terminals/asyncio_terminal.py`)**
   - Client set tracking instead of single client
   - Clean URI generation without WebSocket details

### Frontend Changes

1. **HTML Template (`butterfly/templates/index.html`)**
   - Removed session ID display in welcome message
   - Maintained session token passing to JavaScript

## Security Considerations

1. **Session ID Visibility**: Session IDs are visible in URLs, so avoid using sensitive information as session IDs
2. **Access Control**: Anyone with the session ID can join the session - implement additional authentication if needed
3. **Session Cleanup**: Sessions are automatically cleaned up when all clients disconnect

## Testing

Use the provided test script to verify functionality:

```bash
# Start Butterfly server
python -m butterfly.server

# Run tests (in another terminal)
python test_session_sharing.py
```

## Examples

### Example 1: Collaborative Debugging
```bash
# Developer 1 starts debugging session
http://localhost:57575/?session=debug-issue-123

# Developer 2 joins the same session
http://localhost:57575/?session=debug-issue-123
```

### Example 2: Training Session
```bash
# Instructor creates training session
http://localhost:57575/?session=training-2024-01-15

# Students join using the same URL
http://localhost:57575/?session=training-2024-01-15
```

### Example 3: Persistent Work Session
```bash
# Start work session on desktop
http://localhost:57575/?session=work-session

# Continue same session on laptop
http://localhost:57575/?session=work-session
```

## Troubleshooting

### Session Not Found
If you try to join a session that doesn't exist, a new session with that ID will be created.

### Connection Issues
- Ensure WebSocket connections are not blocked by firewalls
- Check that the Butterfly server is running and accessible
- Verify the session ID format (avoid special characters)

### Multiple Sessions
Each unique session ID creates a separate terminal session. Make sure all users use the exact same session ID to share the same terminal.