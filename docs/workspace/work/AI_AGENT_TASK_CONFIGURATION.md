# AIエージェントタスク設定仕様

**日付**: 2025-06-23 03:00 UTC  
**目的**: AIエージェントが実行可能なタスクの定義と設定システムの設計

## タスク分類と設定項目

### 1. 開発・デプロイメントタスク

#### Webアプリケーションデプロイ
```javascript
{
  taskType: "web_deployment",
  taskName: "Webアプリケーションのデプロイ",
  description: "アプリケーションのビルド、テスト、デプロイを自動実行",
  parameters: {
    projectPath: "/path/to/project",
    buildCommand: "npm run build",
    testCommand: "npm test", 
    deployTarget: "production | staging | development",
    environment: {
      NODE_ENV: "production",
      API_URL: "https://api.example.com"
    }
  },
  steps: [
    { action: "git_pull", description: "最新コードの取得" },
    { action: "dependency_install", description: "依存関係のインストール" },
    { action: "run_tests", description: "テストの実行" },
    { action: "build_application", description: "アプリケーションのビルド" },
    { action: "deploy_artifacts", description: "成果物のデプロイ" },
    { action: "health_check", description: "デプロイ後のヘルスチェック" }
  ],
  estimatedTime: "5-10分",
  prerequisites: ["git", "node", "npm", "docker"],
  outputs: ["build artifacts", "deployment logs", "health status"]
}
```

#### Docker環境構築
```javascript
{
  taskType: "docker_setup",
  taskName: "Docker環境の構築",
  description: "Dockerコンテナの作成、設定、起動",
  parameters: {
    dockerfile: "./Dockerfile",
    imageName: "my-app",
    containerName: "my-app-container",
    ports: ["3000:3000", "8080:8080"],
    volumes: ["/host/path:/container/path"],
    environment: {
      DATABASE_URL: "postgresql://localhost:5432/mydb"
    }
  },
  steps: [
    { action: "build_image", description: "Dockerイメージのビルド" },
    { action: "stop_existing", description: "既存コンテナの停止・削除" },
    { action: "run_container", description: "新しいコンテナの起動" },
    { action: "verify_health", description: "コンテナの健全性確認" }
  ]
}
```

### 2. システム管理タスク

#### ログ解析・監視
```javascript
{
  taskType: "log_monitoring",
  taskName: "システムログの監視・解析",
  description: "ログファイルの継続監視とエラー検出",
  parameters: {
    logFiles: ["/var/log/app.log", "/var/log/error.log"],
    errorPatterns: ["ERROR", "FATAL", "Exception"],
    alertThreshold: 5,
    timeWindow: "5m",
    notifications: {
      slack: "#alerts",
      email: "admin@example.com"
    }
  },
  steps: [
    { action: "tail_logs", description: "ログファイルの継続監視" },
    { action: "pattern_match", description: "エラーパターンの検出" },
    { action: "analyze_trends", description: "傾向分析" },
    { action: "send_alerts", description: "閾値超過時のアラート送信" }
  ]
}
```

#### リソース最適化
```javascript
{
  taskType: "resource_optimization",
  taskName: "システムリソースの最適化",
  description: "CPU、メモリ、ディスク使用量の監視と最適化",
  parameters: {
    cpu_threshold: 80,
    memory_threshold: 85,
    disk_threshold: 90,
    optimization_actions: ["cache_cleanup", "log_rotation", "process_restart"]
  },
  steps: [
    { action: "monitor_resources", description: "リソース使用量の監視" },
    { action: "identify_bottlenecks", description: "ボトルネックの特定" },
    { action: "execute_optimizations", description: "最適化アクションの実行" },
    { action: "verify_improvements", description: "改善効果の確認" }
  ]
}
```

### 3. データ処理タスク

#### データバックアップ
```javascript
{
  taskType: "data_backup",
  taskName: "データベースバックアップ",
  description: "データベースの定期バックアップと保存",
  parameters: {
    database_type: "postgresql | mysql | mongodb",
    connection_string: "postgresql://user:pass@localhost:5432/db",
    backup_path: "/backups",
    retention_days: 30,
    compression: true,
    encryption: {
      enabled: true,
      key_file: "/path/to/key"
    }
  },
  steps: [
    { action: "validate_connection", description: "データベース接続確認" },
    { action: "create_backup", description: "バックアップファイル作成" },
    { action: "compress_encrypt", description: "圧縮・暗号化" },
    { action: "upload_storage", description: "ストレージへのアップロード" },
    { action: "cleanup_old", description: "古いバックアップの削除" }
  ]
}
```

## タスク設定UI設計

### タスクテンプレート選択
```vue
<template>
  <div class="task-configuration">
    <!-- タスクカテゴリ選択 -->
    <div class="task-categories">
      <button 
        v-for="category in taskCategories" 
        :key="category.id"
        @click="selectCategory(category)"
        :class="{ active: selectedCategory?.id === category.id }"
      >
        {{ category.name }}
      </button>
    </div>
    
    <!-- タスクテンプレート一覧 -->
    <div class="task-templates">
      <div 
        v-for="template in availableTemplates" 
        :key="template.taskType"
        class="task-template-card"
        @click="selectTemplate(template)"
      >
        <h3>{{ template.taskName }}</h3>
        <p>{{ template.description }}</p>
        <div class="template-meta">
          <span class="estimated-time">⏱️ {{ template.estimatedTime }}</span>
          <span class="complexity">🔧 {{ template.complexity }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
```

### パラメータ設定フォーム
```vue
<template>
  <div class="task-parameter-form">
    <h2>{{ selectedTemplate.taskName }} の設定</h2>
    
    <!-- 動的パラメータフォーム -->
    <div v-for="param in templateParameters" :key="param.key" class="parameter-field">
      <label>{{ param.label }}</label>
      
      <!-- 文字列入力 -->
      <input 
        v-if="param.type === 'string'"
        v-model="taskConfig[param.key]"
        :placeholder="param.placeholder"
        :required="param.required"
      />
      
      <!-- 選択肢 -->
      <select 
        v-else-if="param.type === 'select'"
        v-model="taskConfig[param.key]"
      >
        <option v-for="option in param.options" :key="option" :value="option">
          {{ option }}
        </option>
      </select>
      
      <!-- 配列入力 -->
      <div v-else-if="param.type === 'array'" class="array-input">
        <div v-for="(item, index) in taskConfig[param.key]" :key="index" class="array-item">
          <input v-model="taskConfig[param.key][index]" />
          <button @click="removeArrayItem(param.key, index)">削除</button>
        </div>
        <button @click="addArrayItem(param.key)">追加</button>
      </div>
      
      <!-- オブジェクト入力 -->
      <div v-else-if="param.type === 'object'" class="object-input">
        <div v-for="(value, key) in taskConfig[param.key]" :key="key" class="key-value-pair">
          <input v-model="key" placeholder="キー" />
          <input v-model="taskConfig[param.key][key]" placeholder="値" />
        </div>
        <button @click="addObjectProperty(param.key)">プロパティ追加</button>
      </div>
    </div>
    
    <!-- 実行前プレビュー -->
    <div class="execution-preview">
      <h3>実行ステップ</h3>
      <ol>
        <li v-for="step in selectedTemplate.steps" :key="step.action">
          {{ step.description }}
        </li>
      </ol>
    </div>
    
    <!-- 設定完了・実行ボタン -->
    <div class="action-buttons">
      <button @click="saveTaskConfig" class="save-btn">設定を保存</button>
      <button @click="executeTask" class="execute-btn">タスクを実行</button>
    </div>
  </div>
</template>
```

## Socket.IOイベント拡張

### タスク設定関連イベント
```javascript
// タスクテンプレート取得
socket.emit("ai_agent:templates:get", {
  category: "development" // optional
})

socket.on("ai_agent:templates:list", (data) => {
  // { templates: [...], categories: [...] }
})

// タスク設定保存
socket.emit("ai_agent:task:configure", {
  tabId: "ai_agent-xxx",
  taskType: "web_deployment",
  parameters: { ... },
  schedule: {
    type: "immediate | scheduled | recurring",
    at: "2025-06-23T15:00:00Z", // scheduled用
    cron: "0 2 * * *" // recurring用
  }
})

socket.on("ai_agent:task:configured", (data) => {
  // { success: true, taskId: "task-xxx", config: {...} }
})

// タスク実行開始
socket.emit("ai_agent:task:execute", {
  taskId: "task-xxx",
  options: {
    dryRun: false,
    verbose: true,
    confirmSteps: false
  }
})
```

## バックエンド実装拡張

### タスクテンプレート管理
```python
# src/aetherterm/agentserver/models/task_templates.py
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

class TaskCategory(Enum):
    DEVELOPMENT = "development"
    SYSTEM_ADMIN = "system_admin"
    DATA_PROCESSING = "data_processing"
    MONITORING = "monitoring"

@dataclass
class TaskParameter:
    key: str
    label: str
    type: str  # string, select, array, object, boolean
    required: bool = True
    default: Any = None
    options: Optional[List[str]] = None
    validation: Optional[Dict[str, Any]] = None

@dataclass
class TaskStep:
    action: str
    description: str
    timeout: Optional[int] = None
    retries: int = 0
    conditions: Optional[Dict[str, Any]] = None

@dataclass
class TaskTemplate:
    task_type: str
    task_name: str
    description: str
    category: TaskCategory
    parameters: List[TaskParameter]
    steps: List[TaskStep]
    estimated_time: str
    prerequisites: List[str]
    complexity: str  # simple, medium, complex
```

### Socket.IOハンドラ拡張
```python
@instrument_socketio_handler("ai_agent:templates:get")
async def ai_agent_templates_get(sid, data):
    """Get available task templates"""
    try:
        from aetherterm.agentserver.services.task_template_manager import get_task_template_manager
        
        template_manager = get_task_template_manager()
        category = data.get("category")
        
        templates = await template_manager.get_templates(category=category)
        categories = await template_manager.get_categories()
        
        response_data = {
            "success": True,
            "templates": [template.to_dict() for template in templates],
            "categories": [cat.value for cat in categories]
        }
        
        await sio_instance.emit("ai_agent:templates:list", response_data, room=sid)
        
    except Exception as e:
        await sio_instance.emit("ai_agent:templates:error", {
            "error": str(e)
        }, room=sid)

@instrument_socketio_handler("ai_agent:task:configure")
async def ai_agent_task_configure(sid, data):
    """Configure task with parameters"""
    try:
        tab_id = data.get("tabId")
        task_type = data.get("taskType")
        parameters = data.get("parameters", {})
        schedule = data.get("schedule", {"type": "immediate"})
        
        # Validate parameters against template
        template_manager = get_task_template_manager()
        template = await template_manager.get_template(task_type)
        
        if not template:
            raise ValueError(f"Unknown task type: {task_type}")
        
        # Validate parameters
        validated_params = await template_manager.validate_parameters(template, parameters)
        
        # Create configured task
        task_id = f"task-{uuid4().hex[:11]}"
        configured_task = {
            "id": task_id,
            "tabId": tab_id,
            "taskType": task_type,
            "parameters": validated_params,
            "schedule": schedule,
            "status": "configured",
            "createdAt": datetime.now().isoformat()
        }
        
        # Store task configuration
        await template_manager.save_task_config(configured_task)
        
        response_data = {
            "success": True,
            "taskId": task_id,
            "config": configured_task
        }
        
        await sio_instance.emit("ai_agent:task:configured", response_data, room=sid)
        
    except Exception as e:
        await sio_instance.emit("ai_agent:task:error", {
            "error": str(e)
        }, room=sid)
```

この設定システムにより、ユーザーは：

1. **タスクテンプレート**から適切なタスクタイプを選択
2. **パラメータ設定**でタスクの詳細を指定
3. **実行前プレビュー**でステップを確認
4. **AIエージェント**にタスクを委任

という流れでAIエージェントの動作を明確に定義できます。

どのタスクカテゴリから実装を始めましょうか？