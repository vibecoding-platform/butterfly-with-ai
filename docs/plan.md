### Revised Project Goals

The primary goals are now to:
1.  Utilize `uv` for efficient Python dependency management.
2.  Implement `dependency-injector` for better modularity and testability in `butterfly/server.py` and `butterfly/containers.py`.
3.  Replace `tornado` with `asyncio` as the core asynchronous framework.
4.  Use `python-socketio` as the main server for handling both HTTP requests (including serving static files) and real-time communication.

### Revised Detailed Plan

#### 1. Dependency Management with `uv`

*   **Objective:** Ensure `uv` is the primary tool for managing Python dependencies and update the project's environment.
*   **Steps:**
    1.  **Update `requirements.txt`**: Remove `tornado` (if it's explicitly listed as a top-level dependency) and ensure `dependency-injector`, `python-socketio`, and `uvicorn` are present.
    2.  **Install/Update Dependencies**: Run `uv pip install -r requirements.txt` to install or update all project dependencies.
    3.  **Generate `uv.lock`**: Create or update the `uv.lock` file to lock the exact versions of all dependencies, ensuring reproducible environments.

#### 2. Dependency Injection with `dependency-injector`

*   **Objective:** Refactor `butterfly/server.py` and `butterfly/containers.py` to leverage `dependency-injector` for managing component dependencies.
*   **Steps:**
    1.  **Analyze `butterfly/containers.py`**: Read the existing `butterfly/containers.py` file to understand its current structure and identify components that can be managed by `dependency-injector`.
    2.  **Define Containers in `butterfly/containers.py`**:
        *   Create a `dependency-injector` container class (e.g., `ApplicationContainer`) in `butterfly/containers.py`.
        *   Define providers within this container for core components such as application settings, logging configurations, and the `socketio.AsyncServer` instance.
        *   Consider abstracting other services or utilities that are currently directly instantiated.
    3.  **Refactor `butterfly/server.py`**:
        *   Import the `ApplicationContainer` from `butterfly/containers.py`.
        *   Modify the `start_server` function to initialize and wire the container.
        *   Replace direct instantiations of dependencies with injections from the container. This will involve accessing providers from the `ApplicationContainer` instance.

#### 3. Core Server with `asyncio` and `python-socketio`

*   **Objective:** Replace `tornado` with `asyncio` as the core asynchronous framework and use `python-socketio` as the main server.
*   **Steps:**
    1.  **Remove `tornado` imports and usage**: Go through `src/butterfly/server.py` and remove all `tornado` related imports and code, including `tornado.ioloop`, `tornado.httpserver`, `tornado.web.Application`, and `HTTPServer`.
    2.  **Initialize `socketio.AsyncServer`**:
        *   In `src/butterfly/server.py`, import `socketio` and `asyncio`.
        *   Create a `socketio.AsyncServer` instance.
        *   Create an `ASGI` application instance using `socketio.ASGIApp` to wrap the `socketio` server. This will allow `python-socketio` to handle both Socket.IO and regular HTTP requests.
    3.  **Serve Static Files and HTTP Routes**:
        *   `python-socketio`'s `ASGIApp` can take an existing ASGI application for handling HTTP requests. We will need to integrate a lightweight ASGI framework (like `Starlette` or `FastAPI`) to serve static files and any other HTTP routes that were previously handled by `tornado`.
        *   Configure this ASGI framework to serve static files from the `static_path` (e.g., `os.path.join(os.path.dirname(__file__), "static")`).
        *   Mount the `socketio.ASGIApp` onto this new ASGI framework.
    4.  **Start the Server**:
        *   Use `uvicorn.run` to run the main ASGI application (which now includes both HTTP and Socket.IO handling). This will replace `tornado.ioloop.IOLoop.start()`.
        *   Configure the host and port for the `uvicorn` server.

#### 4. Real-time Communication with `python-socketio`

*   **Objective:** Implement `python-socketio` for real-time communication.
*   **Steps:**
    1.  **Define Socket.IO Event Handlers**:
        *   In `src/butterfly/server.py` (or a new dedicated file like `butterfly/socket_handlers.py`), define `socketio.on` decorators for various Socket.IO events (e.g., `connect`, `disconnect`, custom messages).
        *   Implement the logic for handling these events.
    2.  **Integrate with Application Logic**: Ensure that the Socket.IO event handlers can interact with the application's core logic, potentially through dependency injection.

### Revised Plan Flow Diagram

```mermaid
graph TD
    A[Start] --> B{Understand User Request};
    B --> C[Read src/butterfly/server.py];
    C --> D{Clarify Websockets Usage};
    D -- User Input --> E[Formulate Detailed Plan];
    E --> F[Present Plan to User];
    F -- User Approval --> G[Write Plan to Markdown (Optional)];
    G --> H[Switch to Code Mode];
    H --> I[Implement Solution];

## Completed Features

### MOTD (Message of the Day) Implementation - 2025-06-13

**Status:** ✅ Completed

**Objective:** Implement a welcome message system that displays connection information and branding when users connect to the terminal.

**Implementation Details:**

1. **Template System**
   - Created Jinja2 template system for MOTD rendering
   - Template file: `butterfly/templates/motd.j2`
   - Supports dynamic content with variables and conditional logic

2. **Core Components**
   - `render_motd()` function in `butterfly/utils.py`
   - Template context includes colors, version, socket info, configuration
   - Dependency injection for configuration values

3. **Display Logic**
   - MOTD sent via Socket.IO (not PTY) for proper formatting
   - Displays before shell prompt appears
   - Reconnection detection to avoid duplicate display
   - Proper terminal line ending handling (`\r\n`)

4. **Information Displayed**
   - Butterfly ASCII art logo with colors
   - Version information
   - Connection details (local/remote addresses and ports)
   - Proxy information (if applicable)
   - Security warnings for unsecure connections
   - Session sharing URI

**Technical Architecture:**
```
Client Connection → Socket.IO → AsyncioTerminal → render_motd() → Jinja2 Template → MOTD Display
```

**Files Modified:**
- `butterfly/templates/motd.j2` (template)
- `butterfly/utils.py` (rendering logic)
- `butterfly/terminals/asyncio_terminal.py` (display logic)
- `butterfly/server.py` (hot reload support)
- `butterfly/socket_handlers.py` (socket info extraction)
- `pyproject.toml` (package configuration)

**Benefits:**
- Enhanced user experience with branded welcome message
- Clear connection information for security awareness
- Professional appearance matching terminal emulator standards
- Configurable through template system