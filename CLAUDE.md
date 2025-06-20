# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context & Overview

### Project Aether
AetherTerm is a **product within Project Aether** - a comprehensive platform for AI-enhanced terminal operations, system management, and intelligent automation. Project Aether aims to revolutionize how organizations interact with their systems through AI-powered tools and interfaces.

### AetherTerm Product
AetherTerm is a **modular terminal system** that provides:
- Web-based terminal emulation with AI assistance
- Intelligent session management and automation  
- Advanced monitoring, audit, and compliance capabilities
- Multi-component architecture for enterprise scalability

## Business Context & Value Proposition

**For comprehensive business understanding, see**: [📊 Business Documentation](./docs/users/business/)

### Target Market
- **Enterprise IT departments** requiring secure, auditable terminal access
- **Financial institutions** needing compliance and risk management
- **Manufacturing/Construction** requiring supervised operations and workflow management
- **Technology companies** seeking AI-enhanced development and operations
- **Educational institutions** providing safe, monitored programming and system administration learning environments

### Key Business Value
- **Operational Efficiency**: 30-50% reduction in manual terminal operations
- **Risk Mitigation**: Complete audit trails and intelligent threat detection
- **Compliance**: Built-in regulatory reporting and approval workflows
- **Innovation**: AI-assisted operations and predictive automation
- **Educational Safety**: Supervised learning environments with real-time guidance and intervention

### Business Users
- **🏢 Executive Level**: Strategic value, ROI analysis, competitive advantage
- **🛡️ IT Management**: Security, compliance, governance, risk management
- **👨‍💻 Technical Users**: Implementation, configuration, daily operations
- **🎓 Educational**: Instructors, students, IT administrators in academic settings

### Educational Use Cases
- **Computer Science Education**: Safe terminal access for programming courses
- **System Administration Training**: Supervised learning with guidance
- **Cybersecurity Education**: Controlled environments for security training
- **Research Computing**: Monitored access to research systems and clusters

## Technical Architecture

AetherTerm consists of multiple integrated components:

- **AgentServer**: Control AI Agents and Shells, with browser-based xterm-compatible terminal
- **AgentShell**: AI-Assisted Terminal that can be directed by AgentServer and accepts user auxiliary operations, enabling automated task execution with human oversight
- **ControlServer**: Central management system for coordinating multiple terminal sessions
- **LangChain Integration**: Advanced AI memory and retrieval system for enhanced terminal intelligence

Built with Python (FastAPI/Socket.IO) backend and Vue.js 3 + TypeScript frontend.

## System Functions & Capabilities

**For detailed specifications, see**: [🔧 Component Functions](./docs/developers/COMPONENT_FUNCTIONS.md) | [📋 System Capabilities](./docs/developers/SYSTEM_CAPABILITIES.md)

### AgentServer Functions
- **🌐 Web Terminal**: Browser-based xterm-compatible terminal interface
- **🤖 AI Integration**: Chat interface, session management, AI-driven automation
- **🔌 Agent Control**: Command and control interface for AgentShell instances  
- **📊 Session Management**: Multi-tab terminals, session persistence, user management
- **🛡️ Security & Audit**: Complete operation logging, access control, compliance reporting
- **⚙️ Configuration**: TOML-based settings, feature toggles, permission management

### AgentShell Functions  
- **🖥️ Terminal Execution**: Native shell command execution with PTY control
- **📡 Remote Control**: Accepts commands from AgentServer for automated execution
- **👤 User Interaction**: Manual user input for auxiliary operations and oversight
- **📋 Command Monitoring**: Real-time command tracking and result reporting
- **🔄 Session Bridging**: Seamless integration between automated and manual operations

### ControlServer Functions
- **🎛️ Central Coordination**: Multi-instance AgentServer management
- **📈 System Monitoring**: Resource usage, performance metrics, health checks
- **🚨 Alert Management**: System-wide notifications and incident response
- **📊 Reporting**: Aggregate statistics, compliance reports, audit summaries

### LangChain Integration Functions
- **🧠 AI Memory**: Conversation history, context retention, learning from interactions
- **🔍 Intelligent Search**: Vector-based retrieval, semantic search, knowledge base
- **📝 Log Analysis**: AI-powered log summarization, pattern detection, anomaly identification
- **🎯 Predictive Assistance**: Proactive suggestions, workflow optimization, error prevention

### Cross-Component Functions
- **🔐 Authentication & Authorization**: User roles, permission enforcement, session security
- **📡 Real-time Communication**: WebSocket-based messaging, live updates, synchronization
- **📁 Data Persistence**: Session storage, configuration management, audit trails
- **🔄 Integration APIs**: REST endpoints, WebSocket events, plugin interfaces

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

### AgentServer (AI Control Center with Web Terminal)
- **Entry Point**: `src/aetherterm/agentserver/main.py` - CLI interface with click
- **ASGI Server**: `src/aetherterm/agentserver/server.py` - FastAPI + Socket.IO integration
- **Routes**: `src/aetherterm/agentserver/routes.py` - HTTP endpoints
- **Socket Handlers**: `src/aetherterm/agentserver/socket_handlers.py` - WebSocket events
- **Control Integration**: `src/aetherterm/agentserver/control_integration.py` - ControlServer connection
- **Terminal Management**: `src/aetherterm/agentserver/terminals/` - PTY control with asyncio
- **Auto Blocker**: `src/aetherterm/agentserver/auto_blocker.py` - Automatic threat blocking
- **Log Analyzer**: `src/aetherterm/agentserver/log_analyzer.py` - Log analysis features

### AgentShell (AI-Assisted Terminal)
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
- **Shared Config**: `src/aetherterm/config/aetherterm.toml.default` (AgentServer, AgentShell共通)
- **Frontend Config**: `frontend/src/config/environment.ts`
- **Build Config**: `frontend/vite.config.ts`
- **LangChain Config**: `src/aetherterm/langchain/config/`

### Configuration Schema Management
⚠️ **CRITICAL**: When modifying configuration files (`aetherterm.toml.default` or related TOML structures), you **MUST** update the schema version:
1. Update `schema_version = "X.X.X"` in `src/aetherterm/config/aetherterm.toml.default`
2. Update compatibility mapping in `src/aetherterm/config/version_manager.py`
3. Document changes in release notes and migration guides

This ensures configuration compatibility tracking between product versions and prevents runtime configuration errors.

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

### Configuration System Testing
```bash
# Test ConfigManager functionality
uv run python -c "
import sys; sys.path.insert(0, 'src')
from aetherterm.config import get_config_manager
config_manager = get_config_manager()
print('✅ Config loaded:', config_manager.get_schema_version())
print('✅ AI enabled:', config_manager.is_feature_enabled('ai_enabled'))
print('✅ Server port:', config_manager.get_value('server.port'))
"

# Test AgentServer DI integration
uv run python -c "
import sys; sys.path.insert(0, 'src')
from aetherterm.agentserver.containers import configure_container
container = configure_container()
config = container.config()
print('✅ DI integration successful')
print('✅ Host:', config['host'])
print('✅ Port:', config['port'])
"
```

### Python Tests
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