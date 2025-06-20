# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AetherTerm is a modular terminal system with AI integration capabilities, consisting of multiple components:

- **AgentServer**: Modern web-based terminal emulator (formerly Butterfly) with xterm-compatible functionality through browsers
- **AgentShell**: AI-integrated terminal wrapper with PTY monitoring and threat detection
- **ControlServer**: Central management system for coordinating multiple terminal sessions
- **LangChain Integration**: Advanced AI memory and retrieval system for enhanced terminal intelligence

Built with Python (FastAPI/Socket.IO) backend and Vue.js 3 + TypeScript frontend.

## Development Commands

### Initial Setup
```bash
# Install all dependencies (Python + Node.js)
make install

# Build frontend and deploy to static files
make build-frontend

# Start specific components:
# AgentServer (Web Terminal)
make run-agentserver
# Or with custom args:
make run-agentserver ARGS="--host=localhost --port=57575 --unsecure --debug"

# AgentShell (AI Terminal Wrapper)
make run-agentshell

# ControlServer (Central Management)
make run-controlserver
```

### Manual Development Workflow
```bash
# 1. Install Python dependencies
uv sync

# 2. Build and deploy frontend (for AgentServer)
cd frontend && npm install && npm run build
cd .. && make build-frontend

# 3. Start components directly:
# AgentServer (Web Terminal Server)
python src/aetherterm/agentserver/main.py --host=localhost --port=57575 --unsecure --debug

# AgentShell (AI Terminal Wrapper)
python src/aetherterm/agentshell/main.py

# ControlServer (Central Management)
python src/aetherterm/controlserver/main.py --port=8765
```

### Frontend Development
```bash
cd frontend/

# Install dependencies
npm install

# Development server with hot reload
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check

# Format code
npm run format
```

### Python Development
```bash
# Linting
make lint
# Or manually:
pytest --flake8 -m flake8 aetherterm
pytest --isort -m isort aetherterm

# Run tests
pytest

# Check for outdated packages
make check-outdated
```

## Architecture Overview

### System Architecture
```
┌─────────────────────┐
│   ControlServer     │ ← Central management & control
│  (port 8765)        │
└──────────┬──────────┘
           │ WebSocket
           │
┌──────────┴──────────┐
│   AgentServer       │ ← Web terminal server
│  (port 57575)       │   (formerly Butterfly)
│                     │
│ • control_integration
│ • auto_blocker      │
│ • log_analyzer      │
└──────────┬──────────┘
           │
┌──────────┴──────────┐
│   AgentShell        │ ← Terminal wrapper with AI
│                     │
│ • PTY monitoring    │
│ • AI analysis       │
│ • Input blocking    │
└─────────────────────┘
           │
┌──────────┴──────────┐
│   LangChain         │ ← AI memory & retrieval
│                     │
│ • Hierarchical mem  │
│ • Log summarization │
│ • RAG pipeline      │
└─────────────────────┘
```

### AgentServer (Web Terminal Server)
- **Entry Point**: `src/aetherterm/agentserver/main.py` - CLI interface with click
- **ASGI Server**: `src/aetherterm/agentserver/server.py` - FastAPI + Socket.IO integration
- **Routes**: `src/aetherterm/agentserver/routes.py` - HTTP endpoints
- **Socket Handlers**: `src/aetherterm/agentserver/socket_handlers.py` - WebSocket events
- **Control Integration**: `src/aetherterm/agentserver/control_integration.py` - ControlServer connection
- **Terminal Management**: `src/aetherterm/agentserver/terminals/` - PTY control with asyncio
- **Auto Blocker**: `src/aetherterm/agentserver/auto_blocker.py` - Automatic threat blocking
- **Log Analyzer**: `src/aetherterm/agentserver/log_analyzer.py` - Log analysis features

### AgentShell (AI Terminal Wrapper)
- **Entry Points**: 
  - `src/aetherterm/agentshell/main.py` - Primary entry point
  - `src/aetherterm/agentshell/main_new.py` - New implementation
  - `src/aetherterm/agentshell/main_sync.py` - Synchronous version
- **Terminal Controller**: `src/aetherterm/agentshell/controller/terminal_controller.py`
- **PTY Handling**: `src/aetherterm/agentshell/pty/` - Sync and async PTY implementations
- **PTY Monitor**: `src/aetherterm/agentshell/pty_monitor/` - Real-time monitoring
  - `ai_analyzer.py` - AI-based threat detection
  - `input_blocker.py` - Input blocking on threats
- **AI Service**: `src/aetherterm/agentshell/service/` - AI integration
  - `ai_service.py` - AI service interface
  - `shell_agent.py` - Shell agent implementation
  - `server_connector.py` - AgentServer connection

### ControlServer (Central Management)
- **Entry Point**: `src/aetherterm/controlserver/main.py` - CLI interface
- **Controller**: `src/aetherterm/controlserver/central_controller.py` - Core control logic
- **Status**: 🚧 Under development

### LangChain Integration (AI Memory)
- **Configuration**: `src/aetherterm/langchain/config/` - LangChain settings
- **Memory**: `src/aetherterm/langchain/memory/` - Memory implementations
  - `conversation_memory.py` - Conversation tracking
  - `hierarchical_memory.py` - Short/medium/long-term memory
  - `session_memory.py` - Session-based memory
- **Storage**: `src/aetherterm/langchain/storage/` - Storage adapters
  - `redis_adapter.py` - Redis storage
  - `sql_adapter.py` - SQL database storage
  - `vector_adapter.py` - Vector database storage
- **Dependency Injection**: `src/aetherterm/langchain/containers.py`

### Frontend (Vue.js + TypeScript)
- **Entry Point**: `frontend/src/main.ts`
- **Main Component**: `frontend/src/App.vue`
- **Terminal Component**: `frontend/src/components/TerminalComponent.vue`
- **State Management**: `frontend/src/stores/` - Pinia stores
- **Services**: `frontend/src/services/AetherTermService.ts` - Socket.IO client
- **Build Tool**: Vite 6.2 with Vue 3.5

### Key Technologies
- **Backend**: FastAPI, Socket.IO, asyncio, dependency-injector, Jinja2
- **Frontend**: Vue 3 Composition API, xterm.js, Pinia, Socket.IO client
- **Communication**: WebSocket via Socket.IO for real-time terminal I/O
- **Security**: SSL/TLS with auto-generated X.509 certificates

## Important Build Process

The frontend must be built and deployed to the AgentServer static directory:

1. Frontend builds to `frontend/dist/`
2. `make build-frontend` copies built assets to `src/aetherterm/agentserver/static/`
3. `index.html` moves to `src/aetherterm/agentserver/templates/index.html`
4. AgentServer serves static files and renders the template

**Critical**: Always run `make build-frontend` after frontend changes before testing AgentServer.

## Development Notes

### Terminal Features
- Full xterm compatibility with 16M colors
- Multi-session sharing with ownership control
- Real-time WebSocket communication
- Desktop notifications and geolocation support
- Configurable MOTD (Message of the Day)

### Security Features
- SSL/TLS encryption by default
- X.509 certificate authentication
- Optional PAM integration for system auth
- Session isolation and ownership

### Configuration
- **AgentServer Config**: `src/aetherterm/agentserver/aetherterm.conf.default`
- **Frontend Config**: `frontend/src/config/environment.ts`
- **Build Config**: `frontend/vite.config.ts`
- **LangChain Config**: `src/aetherterm/langchain/config/`

### Deployment Options
- Direct Python execution
- Docker container (`assets/Dockerfile`)
- Systemd socket activation (`assets/aetherterm.service`, `assets/aetherterm.socket`)

## Key File Locations

### Entry Points
- AgentServer CLI: `src/aetherterm/agentserver/main.py`
- AgentShell CLI: `src/aetherterm/agentshell/main.py`
- ControlServer CLI: `src/aetherterm/controlserver/main.py`
- ASGI App Factory: `src/aetherterm/agentserver/server.py:create_asgi_app`
- Frontend: `frontend/src/main.ts`

### Core Components
- Terminal Logic: `src/aetherterm/agentserver/terminals/asyncio_terminal.py`
- WebSocket Events: `src/aetherterm/agentserver/socket_handlers.py`
- PTY Monitor: `src/aetherterm/agentshell/pty_monitor/ai_analyzer.py`
- Vue Terminal: `frontend/src/components/TerminalComponent.vue`
- Service Layer: `frontend/src/services/AetherTermService.ts`

### Configuration Files
- Python: `pyproject.toml`
- Frontend: `frontend/package.json`, `frontend/vite.config.ts`
- Build: `Makefile`, `Makefile.config`

## Testing
```bash
# Run Python tests
pytest

# Frontend type checking
cd frontend && npm run type-check

# Lint checks
make lint
```

## Common Development Tasks

### Adding New Terminal Features (AgentServer)
1. Modify `src/aetherterm/agentserver/terminals/asyncio_terminal.py` for PTY logic
2. Update `src/aetherterm/agentserver/socket_handlers.py` for WebSocket events
3. Implement frontend changes in `frontend/src/components/TerminalComponent.vue`
4. Update service layer in `frontend/src/services/AetherTermService.ts`

### Adding AI Integration (AgentShell)
1. Implement AI analyzer in `src/aetherterm/agentshell/pty_monitor/ai_analyzer.py`
2. Configure input blocking in `src/aetherterm/agentshell/pty_monitor/input_blocker.py`
3. Update terminal controller in `src/aetherterm/agentshell/controller/terminal_controller.py`
4. Add AI service logic in `src/aetherterm/agentshell/service/ai_service.py`

### Implementing Central Control (ControlServer)
1. Add control logic in `src/aetherterm/controlserver/central_controller.py`
2. Update AgentServer integration in `src/aetherterm/agentserver/control_integration.py`
3. Configure WebSocket communication between components

### Configuring LangChain Memory
1. Set up memory type in `src/aetherterm/langchain/config/memory_config.py`
2. Choose storage adapter in `src/aetherterm/langchain/storage/`
3. Configure retrieval settings in `src/aetherterm/langchain/config/retrieval_config.py`

### Frontend Changes
1. Make changes in `frontend/src/`
2. Run `make build-frontend` to deploy
3. Test with `make run-debug`

### Adding New Dependencies
- Python: Add to `pyproject.toml` dependencies, run `uv sync`
- Frontend: Add to `frontend/package.json`, run `npm install`

## Component Communication

### AgentServer ↔ ControlServer
- Communication via WebSocket (port 8765)
- AgentServer connects to ControlServer for centralized management
- Emergency blocking and session control features

### AgentShell ↔ AgentServer
- AgentShell can connect to AgentServer for session management
- Uses `server_connector.py` for integration

### AI Integration Points
- AgentShell: Real-time PTY monitoring and threat detection
- LangChain: Can be integrated into any component for memory/retrieval
- ControlServer: Centralized AI decision making (planned)