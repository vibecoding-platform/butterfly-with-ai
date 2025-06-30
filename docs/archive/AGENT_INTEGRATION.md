# AetherTerm AgentServer - 統合エージェント連携ガイド

## 概要
AetherTerm AgentServerは、複数のコーディングエージェントが**ユーザーと同じ立ち位置**で参加できる統合プラットフォームです。エージェントは動的にターミナルを作成し、相互に通信し、ブラウザターミナル経由でユーザーからリアルタイムで仕様を受け取ることができます。

### 🎯 Max Plan環境との連携
Max Plan環境では以下の高度な機能が利用可能：
- **大規模コードベース**の一括処理
- **高精度な実装**と包括的レビュー  
- **インテリジェントな提案**と最適化
- **長時間の会話保持**と文脈理解
- **複雑なタスク**の自動分解・実行

## P0 Priority Features - Agent Communication Protocol

### Key Changes

#### 1. Unified Message Architecture
- **変更点**: すべてのエージェント間通信は`agent_message`イベントで統一
- **メッセージタイプ**: `message_type`フィールドでメッセージの種類を明示
- **ブロードキャスト**: チャンネル指定ではなく、全エージェントにブロードキャスト

#### 2. Agent Terminal Creation
エージェントはターミナル作成時にagent configurationを指定可能：

```javascript
// WebSocket経由でターミナル作成
socket.emit('create_terminal', {
    session: 'new_session_id',
    path: '/workspace/project',
    launch_mode: 'agent',
    agent_config: {
        agent_type: 'developer',    // developer, reviewer, tester, architect, researcher
        agent_id: 'claude_dev_001',
        working_directory: '/workspace/project'
    },
    requester_agent_id: 'claude_main_001'  // 要求元エージェントID
});
```

#### 3. MainAgent-Controlled Startup Methods
**重要**: エージェントの起動方法はMainAgentが指定します。AgentServerは自動で決定しません。

MainAgentが起動方法を指定する3つのオプション：

##### startup_method: "claude_cli" (デフォルト)
```bash
# 標準のClaude CLI起動
cd /workspace && claude --name claude_dev_001 --role developer --sub-agent \
  --parent-agent claude_main_001 --working-dir /workspace
```

##### startup_method: "docker"
```bash
# Docker環境での起動
docker run -v /workspace:/workspace claude-agent:latest \
  --name claude_tester_001 --role tester --mode test
```

##### startup_method: "custom_script"
```bash
# MainAgentが指定するカスタムコマンド
{custom_startup_command}
```

**環境変数の自動設定**:
- `AGENT_ID={agent_id}`
- `AGENT_TYPE={agent_type}`
- `PARENT_AGENT_ID={parent_agent_id}`
- `WORKING_DIRECTORY={working_directory}`
- `AGENT_HIERARCHY=sub` (SubAgentの場合)

### WebSocket Message Protocol

#### Message Types
すべてのエージェント間通信は`agent_message`イベントで送信され、`message_type`で区別：

```javascript
// メッセージ受信
socket.on('agent_message', (data) => {
    switch(data.message_type) {
        case 'response_request':
            handleResponseRequest(data);
            break;
        case 'response_reply':
            handleResponseReply(data);
            break;
        case 'agent_start_response':
            handleAgentStartResponse(data);
            break;
        case 'control_message':
            handleControlMessage(data);
            break;
        case 'spec_document':
            handleSpecDocument(data);
            break;
        case 'spec_query_response':
            handleSpecQueryResponse(data);
            break;
    }
});
```

#### 1. Response Request (SubAgent → MainAgent)
```javascript
socket.emit('response_request', {
    from_agent_id: 'claude_tester_001',
    to_agent_id: 'claude_main_001',
    request_type: 'code_review',
    content: 'Please review this implementation',
    data: {
        file_path: 'src/components/Login.vue',
        changes: '...'
    },
    priority: 'high',
    timeout: 300
});

// 受信側でのハンドリング
socket.on('agent_message', (data) => {
    if (data.message_type === 'response_request' && data.to_agent_id === myAgentId) {
        // 自分宛ての要請を処理
        processRequest(data);
    }
});
```

#### 2. Response Reply (MainAgent → SubAgent)
```javascript
socket.emit('response_reply', {
    message_id: 'uuid-of-original-request',
    from_agent_id: 'claude_main_001',
    to_agent_id: 'claude_tester_001',
    status: 'completed',
    response: 'The code looks good, but please add error handling',
    data: {
        suggestions: [...],
        modified_files: [...]
    }
});
```

#### 3. Agent Start Request (MainAgent控制)
```javascript
socket.emit('agent_start_request', {
    requester_agent_id: 'claude_main_001',
    agent_type: 'tester',
    agent_id: 'claude_tester_002',
    working_directory: '/workspace/project',
    launch_mode: 'agent',
    startup_method: 'claude_cli',  // MainAgentが起動方法を指定
    startup_command: 'cd {working_directory} && claude --name {agent_id} --role {agent_type} --sub-agent --parent-agent {parent_agent_id}',  // カスタムコマンド (optional)
    environment_vars: {  // 追加環境変数
        'PROJECT_TYPE': 'vue3',
        'TEST_FRAMEWORK': 'jest'
    },
    config: {
        role: 'tester',
        mode: 'test'
    }
});
```

**MainAgent起動指示の例**:
```javascript
// カスタムスクリプトでの起動
socket.emit('agent_start_request', {
    requester_agent_id: 'claude_main_001',
    agent_type: 'reviewer',
    startup_method: 'custom_script',
    startup_command: 'cd {working_directory} && python review-agent.py --agent-id {agent_id} --focus frontend',
    environment_vars: {
        'REVIEW_STANDARDS': 'vue3',
        'SEVERITY_LEVEL': 'strict'
    }
});
```

#### 4. Control Messages
```javascript
socket.emit('control_message', {
    from_agent_id: 'claude_main_001',
    control_type: 'pause_all',  // pause_all, resume_all, shutdown_agent, restart_agent
    target_agent_id: 'claude_tester_001',  // 特定エージェント対象の場合
    data: {}
});
```

### REST API Integration

#### Agent Dynamic Startup (MainAgent制御)
```bash
POST /api/v1/agents/start
Content-Type: application/json

{
    "requester_agent_id": "claude_main_001",
    "agent_type": "tester",
    "agent_id": "claude_tester_002",
    "working_directory": "/workspace/project",
    "launch_mode": "agent",
    "startup_method": "claude_cli",  # MainAgentが起動方法を指定
    "startup_command": "cd {working_directory} && claude --name {agent_id} --role {agent_type} --test-mode comprehensive",  # MainAgentの指示
    "environment_vars": {  # MainAgentが追加する環境変数
        "TEST_COVERAGE_TARGET": "90",
        "FRAMEWORK": "jest"
    },
    "config": {
        "role": "tester",
        "mode": "test"
    }
}

# Response:
{
    "session_id": "uuid-generated",
    "agent_id": "claude_tester_002",
    "agent_type": "tester",
    "status": "started",  # started(実際に起動), ready(起動準備完了), failed(失敗)
    "working_directory": "/workspace/project",
    "startup_command": "cd /workspace/project && TEST_COVERAGE_TARGET=90 FRAMEWORK=jest claude --name claude_tester_002 --role tester --test-mode comprehensive",
    "error": null
}
```

**MainAgentによる起動方法の完全制御**:
- `startup_method`: MainAgentが起動方法を決定
- `startup_command`: MainAgentがカスタムコマンドを指定可能
- `environment_vars`: MainAgentが必要な環境変数を追加
- **AgentServerは指示に従うのみ** - 自動判断しない

**重要な実装詳細:**
- REST APIは実際にターミナルセッションを作成し、エージェントを自動起動します
- Socket.IOインスタンスが利用可能な場合、完全なターミナル環境が構築されます
- WebSocketクライアントがなくても、バックグラウンドでエージェントが動作します
- 失敗時は `status: "failed"` または `status: "ready"` + `error` で詳細を返します

#### Agent Status Check
```bash
GET /api/v1/agents/status

Response:
{
    "agents": [
        {
            "session_id": "uuid",
            "agent_id": "claude_tester_001",
            "agent_type": "tester",
            "status": "ready",
            "working_directory": "/workspace",
            "last_activity": "2025-01-29T12:34:56Z"
        }
    ],
    "total_agents": 3
}
```

### Agent Implementation Requirements

#### 1. Message Filtering
エージェントは自分宛てのメッセージをフィルタリング：

```javascript
socket.on('agent_message', (data) => {
    // 自分宛て、またはブロードキャスト対象のメッセージのみ処理
    if (data.to_agent_id === myAgentId || !data.to_agent_id) {
        handleMessage(data);
    }
});
```

#### 2. Agent Registration
エージェント起動時に自身を登録：

```javascript
const myAgentId = 'claude_dev_001';
const myAgentType = 'developer';

// 自身の情報を保持
const agentInfo = {
    agent_id: myAgentId,
    agent_type: myAgentType,
    capabilities: ['code_generation', 'debugging', 'refactoring'],
    status: 'ready'
};
```

#### 3. Response Handling
要請に対する適切な応答：

```javascript
function handleResponseRequest(data) {
    if (data.to_agent_id !== myAgentId) return;
    
    // 要請を処理
    const result = processRequest(data.request_type, data.content, data.data);
    
    // 応答を送信
    socket.emit('response_reply', {
        message_id: data.message_id,
        from_agent_id: myAgentId,
        to_agent_id: data.from_agent_id,
        status: 'completed',
        response: result.message,
        data: result.data
    });
}
```

### Usage Examples

#### Example 1: Code Review Workflow
```javascript
// MainAgent: レビュー要請
socket.emit('response_request', {
    from_agent_id: 'claude_main_001',
    to_agent_id: 'claude_reviewer_001',
    request_type: 'code_review',
    content: 'Please review the login implementation',
    data: {
        files: ['src/components/LoginForm.vue', 'src/api/auth.js'],
        changes: 'Added OAuth integration'
    }
});

// ReviewerAgent: レビュー結果返信
socket.emit('response_reply', {
    message_id: 'original-request-id',
    from_agent_id: 'claude_reviewer_001',
    to_agent_id: 'claude_main_001',
    status: 'completed',
    response: 'Review completed with suggestions',
    data: {
        approved: true,
        suggestions: [
            'Add input validation',
            'Handle OAuth errors gracefully'
        ]
    }
});
```

#### Example 2: Test Generation Request
```javascript
// MainAgent: テスト生成要請
socket.emit('response_request', {
    from_agent_id: 'claude_main_001',
    to_agent_id: 'claude_tester_001',
    request_type: 'generate_tests',
    content: 'Generate unit tests for user authentication',
    data: {
        target_file: 'src/services/AuthService.js',
        test_framework: 'jest',
        coverage_target: 90
    }
});
```

### Migration Guide

#### For Existing Agents
1. **メッセージハンドリング更新**: 個別イベントから`agent_message`イベントに変更
2. **メッセージタイプ確認**: `message_type`フィールドでメッセージ種別を判定
3. **フィルタリング実装**: `to_agent_id`で自分宛てメッセージを識別
4. **ブロードキャスト対応**: チャンネル指定なしの全体通信に対応

#### Breaking Changes
- `response_request`、`response_reply`イベントは廃止
- すべて`agent_message`イベントに統一
- `message_type`フィールドが必須
- **重要**: AgentServerによる自動起動方法決定は廃止
- MainAgentが`startup_method`と`startup_command`を必ず指定
- `environment_vars`でMainAgentが環境変数を完全制御

### MainAgent起動制御の実装例

#### 1. プロジェクト固有の起動パターン
```javascript
// Vue.js プロジェクト用の開発エージェント起動
function startVueDevAgent(agentId, workingDir) {
    return {
        startup_method: 'claude_cli',
        startup_command: 'cd {working_directory} && claude --name {agent_id} --role developer --framework vue3 --linting-enabled',
        environment_vars: {
            'VUE_VERSION': '3.4.0',
            'LINTING_RULES': 'vue3-strict',
            'BUILD_TOOL': 'vite'
        }
    };
}

// Python FastAPI プロジェクト用のテストエージェント起動
function startPythonTestAgent(agentId, workingDir) {
    return {
        startup_method: 'custom_script',
        startup_command: 'cd {working_directory} && uv run pytest-agent.py --agent-id {agent_id} --coverage-target 90',
        environment_vars: {
            'PYTHON_VERSION': '3.11',
            'TEST_FRAMEWORK': 'pytest',
            'COVERAGE_TARGET': '90'
        }
    };
}
```

#### 2. 動的な起動決定ロジック
```javascript
class MainAgentStartupController {
    determineStartupMethod(projectType, agentType, requirements) {
        // プロジェクト解析に基づく起動方法決定
        const projectConfig = this.analyzeProject(projectType);
        const agentConfig = this.getAgentRequirements(agentType);
        
        if (requirements.needsIsolation) {
            return {
                startup_method: 'docker',
                startup_command: `docker run -v {working_directory}:/workspace ${projectConfig.dockerImage} claude --name {agent_id} --role {agent_type}`,
                environment_vars: {
                    'ISOLATION_MODE': 'docker',
                    'PROJECT_TYPE': projectType
                }
            };
        }
        
        if (requirements.customToolchain) {
            return {
                startup_method: 'custom_script',
                startup_command: requirements.customCommand,
                environment_vars: {
                    ...projectConfig.envVars,
                    ...requirements.customEnv
                }
            };
        }
        
        // デフォルト: Claude CLI
        return {
            startup_method: 'claude_cli',
            startup_command: `claude --name {agent_id} --role {agent_type} --project-type ${projectType}`,
            environment_vars: projectConfig.envVars
        };
    }
    
    startAgent(agentType, agentId, workingDir, requirements = {}) {
        const startupConfig = this.determineStartupMethod(
            this.currentProjectType, 
            agentType, 
            requirements
        );
        
        socket.emit('agent_start_request', {
            requester_agent_id: this.agentId,
            agent_type: agentType,
            agent_id: agentId,
            working_directory: workingDir,
            launch_mode: 'agent',
            ...startupConfig,
            config: {
                role: agentType,
                project_type: this.currentProjectType,
                requirements: requirements
            }
        });
    }
}
```

## 仕様インプットシステム

### WebSocket経由での仕様配信
```javascript
// 仕様アップロード
socket.emit('spec_upload', {
    from_agent_id: 'user_001',
    spec_type: 'project_requirements',  // project_requirements, api_spec, design_doc, user_story
    title: 'ユーザー認証システム仕様',
    content: `
# ユーザー認証システム仕様
## 要件
- OAuth 2.0 対応
- JWT トークン認証
- パスワードリセット機能
    `,
    target_agents: ['claude_dev_001', 'claude_test_001'], // 空の場合は全エージェント
    priority: 'high',
    format: 'markdown'
});

// エージェントによる仕様問い合わせ
socket.emit('spec_query', {
    from_agent_id: 'claude_dev_001',
    query: 'ユーザー認証のAPIエンドポイント仕様は？',
    spec_types: ['api_spec', 'project_requirements'],
    context: '現在LoginForm.vueの実装中'
});
```

### REST API経由での仕様管理
```bash
# 仕様アップロード
POST /api/v1/specs/upload
{
    "spec_type": "api_spec",
    "title": "認証API仕様書",
    "content": "openapi: 3.0.0\n...",
    "target_agents": ["claude_dev_001"],
    "priority": "high",
    "format": "yaml"
}

# 仕様検索
POST /api/v1/specs/query
{
    "query": "ログイン画面のバリデーション仕様",
    "spec_types": ["api_spec", "design_doc"]
}

# 仕様一覧
GET /api/v1/specs/list
GET /api/v1/specs/list?spec_type=api_spec
```

### ブラウザターミナル経由でのインタラクティブ仕様入力
```bash
# ターミナルで仕様ファイルを直接編集
vim specifications/auth-requirements.md

# エージェントに仕様を配信
claude --spec-file specifications/auth-requirements.md --distribute-to all

# エージェント起動時に仕様を指定
claude --name claude_dev_001 --role developer --spec-dir ./specifications
```

### Max Plan環境での高度な仕様処理
```bash
# Max Plan機能を活用した包括的仕様解析
uv run python examples/max_plan_demo.py --spec-analysis

# 大規模コードベースに対する仕様適用
claude --name claude_architect_001 --role architect --mode design \
  --spec-file large-system-requirements.md \
  --codebase-size large \
  --analysis-depth comprehensive
```

## エージェント協調パターン

### パターン1: ユーザー主導の仕様提供
1. ユーザーがブラウザターミナルで仕様を作成・編集
2. WebSocket経由でエージェントに仕様を配信
3. エージェントが仕様に基づいて作業開始
4. ユーザーがリアルタイムで進捗確認・介入

### パターン2: エージェント主導の仕様確認
1. エージェントが作業中に仕様の不明点を発見
2. `spec_query`でユーザーに質問
3. ユーザーがターミナルまたはWebUIで回答
4. エージェントが回答に基づいて作業継続

### パターン3: Max Plan環境での自動仕様最適化
1. エージェントが大規模コードベースを解析
2. 既存仕様との齟齬や改善点を自動検出
3. インテリジェントな提案をユーザーに送信
4. ユーザー承認後、最適化された仕様を全体配信

## メッセージハンドリング実装

### 仕様関連メッセージの処理
```javascript
// 仕様ドキュメント受信処理
function handleSpecDocument(data) {
    if (!data.target_agents.length || data.target_agents.includes(myAgentId)) {
        console.log(`新しい仕様: ${data.title} (${data.spec_type})`);
        // 仕様をエージェントのコンテキストに保存
        storeSpecification({
            spec_id: data.spec_id || generateSpecId(),
            title: data.title,
            content: data.content,
            spec_type: data.spec_type,
            priority: data.priority,
            format: data.format,
            metadata: data.metadata,
            received_at: new Date().toISOString()
        });
        
        // Max Plan環境では高度な仕様解析を実行
        if (isMaxPlanEnvironment()) {
            analyzeSpecificationComprehensively(data);
        }
    }
}

// 仕様問い合わせ結果処理
function handleSpecQueryResponse(data) {
    if (data.to_agent_id === myAgentId) {
        console.log(`仕様検索結果: ${data.total_results}件`);
        data.results.forEach(spec => {
            console.log(`- ${spec.title} (関連度: ${spec.relevance_score})`);
            // 高関連度の仕様を優先的にコンテキストに追加
            if (spec.relevance_score > 0.8) {
                addToActiveContext(spec);
            }
        });
    }
}

// Max Plan環境での包括的仕様解析
function analyzeSpecificationComprehensively(specData) {
    // 大規模コードベースとの整合性チェック
    const consistencyCheck = analyzeCodebaseConsistency(specData);
    
    // インテリジェントな改善提案生成
    const suggestions = generateIntelligentSuggestions(specData);
    
    // 長時間会話履歴からの文脈理解
    const contextualInsights = analyzeConversationHistory(specData);
    
    // 複雑なタスクの自動分解
    const taskBreakdown = decomposeComplexTasks(specData);
    
    // 結果をユーザーに報告
    socket.emit('response_request', {
        from_agent_id: myAgentId,
        to_agent_id: 'user_001',
        request_type: 'spec_analysis_result',
        content: 'Max Plan解析完了',
        data: {
            consistency: consistencyCheck,
            suggestions: suggestions,
            insights: contextualInsights,
            tasks: taskBreakdown
        },
        priority: 'high'
    });
}
```

### 統合アーキテクチャの利点

1. **ユーザーエージェント同等参加**: ブラウザターミナルでユーザーとエージェントが同じ立ち位置で作業
2. **MainAgent完全制御**: 起動方法、環境変数、コマンドをMainAgentが決定
3. **リアルタイム仕様配信**: WebSocket経由での即座な仕様共有・更新
4. **Max Plan高度機能**: 大規模処理、高精度実装、インテリジェント提案
5. **統一メッセージプロトコル**: `agent_message`による一貫したコミュニケーション
6. **多様な入力方法**: REST API、WebSocket、ターミナル経由での柔軟な仕様管理
7. **柔軟な起動戦略**: Docker、カスタムスクリプト、Claude CLIの選択可能

### 重要な設計原則

**MainAgent主導アーキテクチャ**:
- AgentServerは実行基盤として機能し、起動方法は決定しない
- MainAgentがプロジェクト状況を判断して最適な起動方法を指示
- 環境変数、コマンドライン引数はMainAgentが完全制御
- SubAgentは親エージェントの指示に従って起動・動作

このアーキテクチャにより、エージェントはユーザーと同等の立ち位置でターミナルにアクセスし、Max Plan環境の高度な機能を活用しながら、MainAgentの戦略的制御下でリアルタイムで仕様を受け取り、相互に協調して作業を行うことができます。