# AetherTerm - AI Terminal Platform

**Components**: AgentServer (web terminal + AI control), AgentShell (AI-assisted terminal), ControlServer (central mgmt)  
**Tech**: Python FastAPI + SocketIO, Vue 3 + TypeScript frontend, LangChain AI integration  
**Features**: Real-time command analysis, hierarchical memory, multi-agent coordination, comprehensive security

## Quick Start

```bash
# Backend setup
uv sync && make build-frontend
make run-agentserver ARGS="--host=localhost --port=57575 --unsecure --debug"

# Frontend development  
cd frontend && pnpm install && pnpm dev
```

## Key Files

**Entry Points**: `src/aetherterm/{agentserver,agentshell,controlserver}/main.py`  
**Frontend**: `frontend/src/main.ts`, `components/TerminalComponent.vue`  
**Config**: `pyproject.toml`, `frontend/package.json`

## Architecture

**Flow**: ControlServer (8765) → AgentServer (57575) → AgentShell → LangChain AI  
**Features**: PTY monitoring, AI analysis, hierarchical memory, log summarization

## Development Notes

**Build Process**: Frontend builds to `dist/` → copied to AgentServer `static/` → served by FastAPI  
**Communication**: WebSocket (Socket.IO) for real-time terminal I/O  
**Security**: SSL/TLS, X.509 certs, PAM integration, RBAC

## Common Tasks

**Frontend changes**: Edit `frontend/src/` → `make build-frontend` → test  
**Add dependencies**: Python (`pyproject.toml` + `uv sync`), Node (`package.json` + `pnpm install`)  
**Testing**: `pytest` (Python), `pnpm type-check` (frontend)
