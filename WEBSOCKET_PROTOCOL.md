# WebSocket Protocol Specification

## Core Events

### Terminal Management
- `create_terminal` - Create new terminal session
- `resume_workspace` - Resume workspace with tabs/panes  
- `resume_terminal` - Resume specific terminal session
- `terminal_input` - Send input to terminal
- `terminal_resize` - Resize terminal viewport
- `terminal_output` - Receive terminal output (broadcast)
- `terminal_ready` - Terminal creation confirmation
- `terminal_closed` - Terminal shutdown notification

### Agent Communication
- `agent_message` - Unified agent communication
  - `message_type`: `response_request`, `response_reply`, `agent_start_response`, `control_message`, `spec_document`, `agent_initialization`
- `agent_start_request` - Start new agent
- `agent_hello` - Agent greeting/handshake
- `spec_upload` - Upload specification document
- `spec_query` - Query specification content

### Monitoring
- `log_monitor_subscribe` - Subscribe to log monitoring
- `log_monitor_unsubscribe` - Unsubscribe from log monitoring  
- `log_monitor_search` - Search logs
- `context_inference_subscribe` - Subscribe to context inference
- `predict_next_commands` - Get command predictions
- `get_operation_analytics` - Get operation analytics

### Connection Lifecycle
- `connect` - Client connection established
- `disconnect` - Client disconnection

## Architecture Improvements Needed

### Clean Architecture Implementation
1. **Domain Layer**: Core business logic (terminal management, agent coordination)
2. **Application Layer**: Use cases (workspace management, agent communication)
3. **Infrastructure Layer**: Socket.IO handlers, external services
4. **Interface Layer**: WebSocket event contracts

### Proposed Refactoring
- Extract `WorkspaceManager` for workspace/terminal lifecycle
- Extract `AgentCommunicationService` for agent messaging
- Extract `MonitoringService` for log/analytics features
- Keep socket handlers as thin interface adapters

### Theme System
- Add theme configuration events
- Support light/dark mode switching
- Customizable terminal color schemes