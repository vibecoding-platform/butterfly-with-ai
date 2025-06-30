# AetherTerm Documentation

## 📖 Current Documentation

### Core Integration
- **[AGENT_INTEGRATION.md](../AGENT_INTEGRATION.md)** - MainAgent制御によるエージェント統合システム
  - P0 Priority Features - Agent Communication Protocol  
  - MainAgent-Controlled Startup Methods
  - 仕様インプットシステム
  - Max Plan環境連携

### Quick Start
- **[CLAUDE.md](../CLAUDE.md)** - プロジェクト設定とコマンド
- **[README.md](../README.md)** - 基本情報

### Archived Documentation
- **[archived/](./archived/)** - 廃止されたAgentShell関連の古いドキュメント

## 🚀 Quick Reference

### Development Commands
```bash
# Backend setup  
uv sync && make build-frontend
make run-agentserver ARGS="--host=localhost --port=57575 --unsecure --debug"

# Frontend development
cd frontend && pnpm install && pnpm dev
```

### Architecture
**Flow**: ControlServer (8765) → AgentServer (57575) → MainAgent → SubAgents  
**Key**: MainAgent controls all startup methods and agent coordination

For detailed implementation and usage, see [AGENT_INTEGRATION.md](../AGENT_INTEGRATION.md).