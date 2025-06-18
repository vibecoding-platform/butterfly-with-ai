# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AetherTerm is a modern web-based terminal emulator providing xterm-compatible functionality through browsers. Built with Python (FastAPI/Socket.IO) backend and Vue.js 3 + TypeScript frontend.

## Development Commands

### Initial Setup
```bash
# Install all dependencies (Python + Node.js)
make install

# Build frontend and deploy to static files
make build-frontend

# Start development server
make run-debug
# Or with custom args:
make run-debug ARGS="--host=localhost --port=57575 --unsecure --debug"
```

### Manual Development Workflow
```bash
# 1. Install Python dependencies
uv sync

# 2. Build and deploy frontend
cd frontend && npm install && npm run build
cd .. && make build-frontend

# 3. Start server directly
python src/aetherterm/main.py --host=localhost --port=57575 --unsecure --debug
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

### Backend (Python)
- **Entry Point**: `src/aetherterm/main.py` - CLI interface with click
- **ASGI Server**: `src/aetherterm/server.py` - FastAPI + Socket.IO integration
- **Routes**: `src/aetherterm/routes.py` - HTTP endpoints
- **Socket Handlers**: `src/aetherterm/socket_handlers.py` - WebSocket events
- **Dependency Injection**: `src/aetherterm/containers.py` - Service container
- **Terminal Management**: `src/aetherterm/terminals/` - PTY control with asyncio

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

The frontend must be built and deployed to the Python static directory:

1. Frontend builds to `frontend/dist/`
2. `make build-frontend` copies built assets to `src/aetherterm/static/`
3. `index.html` moves to `src/aetherterm/templates/index.html`
4. Python serves static files and renders the template

**Critical**: Always run `make build-frontend` after frontend changes before testing.

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
- **Python Config**: `src/aetherterm/aetherterm.conf.default`
- **Frontend Config**: `frontend/src/config/environment.ts`
- **Build Config**: `frontend/vite.config.ts`

### Deployment Options
- Direct Python execution
- Docker container (`assets/Dockerfile`)
- Systemd socket activation (`assets/aetherterm.service`, `assets/aetherterm.socket`)

## Key File Locations

### Entry Points
- CLI: `src/aetherterm/main.py`
- ASGI App Factory: `src/aetherterm/server.py:create_asgi_app`
- Frontend: `frontend/src/main.ts`

### Core Components
- Terminal Logic: `src/aetherterm/terminals/asyncio_terminal.py`
- WebSocket Events: `src/aetherterm/socket_handlers.py`
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

### Adding New Terminal Features
1. Modify `src/aetherterm/terminals/asyncio_terminal.py` for PTY logic
2. Update `src/aetherterm/socket_handlers.py` for WebSocket events
3. Implement frontend changes in `frontend/src/components/TerminalComponent.vue`
4. Update service layer in `frontend/src/services/AetherTermService.ts`

### Frontend Changes
1. Make changes in `frontend/src/`
2. Run `make build-frontend` to deploy
3. Test with `make run-debug`

### Adding New Dependencies
- Python: Add to `pyproject.toml` dependencies, run `uv sync`
- Frontend: Add to `frontend/package.json`, run `npm install`