# OpenHands Integration with AetherTerm

## Architecture Overview

```
AetherTerm Frontend (AIエージェントタブ)
    ↓ Socket.IO
AetherTerm AgentServer
    ↓ Shell Commands
AetherTerm AgentShell
    ↓ Python API / CLI
OpenHands Agent System
    ↓ Tool Execution
Target Environment
```

## Integration Components

### 1. OpenHands Shell Interface
- **Location**: `src/aetherterm/agentshell/openhands/`
- **Purpose**: OpenHandsエージェントとの通信インターフェース
- **Components**:
  - `openhands_client.py`: OpenHands API client
  - `openhands_shell.py`: Shell command wrapper
  - `openhands_monitor.py`: Agent execution monitoring

### 2. AgentShell OpenHands Integration
- **Location**: `src/aetherterm/agentshell/integrations/`
- **Purpose**: AgentShellからOpenHandsを制御
- **Features**:
  - Task delegation to OpenHands agents
  - Progress monitoring and reporting
  - Error handling and recovery

### 3. Frontend OpenHands Control
- **Location**: `frontend/src/components/OpenHandsControl.vue`
- **Purpose**: OpenHands操作用UI
- **Features**:
  - Agent task configuration
  - Real-time progress visualization
  - Agent interaction interface

## Communication Flow

### Task Execution Flow
1. **Frontend**: User creates AI agent tab with OpenHands configuration
2. **AgentServer**: Creates AI agent terminal with OpenHands shell
3. **AgentShell**: Initializes OpenHands client connection
4. **OpenHands**: Receives task and begins execution
5. **Monitoring**: Real-time progress reporting back to frontend

### Command Interface
```bash
# OpenHands task execution via AgentShell
aether-openhands --task "Create a Python web scraper" --model "claude-3-5-sonnet"
aether-openhands --interactive  # Interactive mode
aether-openhands --status       # Check agent status
aether-openhands --stop         # Stop current task
```

## Technical Specifications

### OpenHands Client Configuration
```python
class OpenHandsConfig:
    api_endpoint: str = "http://localhost:3000"
    model: str = "claude-3-5-sonnet-20241022"
    max_iterations: int = 100
    workspace_dir: str = "/workspace"
    sandbox_type: str = "local"
```

### AgentShell Integration Points
1. **Startup Hook**: Initialize OpenHands client on AI agent shell startup
2. **Command Processing**: Intercept and route OpenHands commands
3. **Output Streaming**: Stream OpenHands output to terminal
4. **State Management**: Track agent execution state

### Frontend Integration
1. **OpenHands Tab Type**: Specialized AI agent tab for OpenHands
2. **Task Configuration UI**: Form for task input and model selection  
3. **Progress Visualization**: Real-time execution progress display
4. **Agent Interaction**: Chat interface for agent communication

## Implementation Plan

### Phase 1: Core Integration
- [ ] OpenHands client wrapper
- [ ] AgentShell command routing
- [ ] Basic task execution

### Phase 2: UI Integration  
- [ ] Frontend OpenHands controls
- [ ] Progress visualization
- [ ] Task configuration interface

### Phase 3: Advanced Features
- [ ] Interactive agent communication
- [ ] Workspace file management
- [ ] Multi-agent coordination

## Benefits

1. **Unified Interface**: Control OpenHands through familiar terminal
2. **Progress Tracking**: Real-time visibility into agent execution
3. **Integration**: Seamless workflow with other AetherTerm features
4. **Scalability**: Support for multiple concurrent OpenHands agents