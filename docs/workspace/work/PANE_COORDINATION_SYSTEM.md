# ペーン間協調システム設計

**日付**: 2025-06-23 03:20 UTC  
**目的**: AIエージェントによるペーン（ターミナル）間の作業依頼・レポート回収・協調制御システム

## ペーン間協調の概念

### 基本構造
```
AIエージェントタブ
├── 親エージェント (統括制御)
│   ├── ペーン管理UI
│   └── 作業依頼・レポート統合
└── 制御下ペーン群
    ├── ペーンA (ビルド専用)
    ├── ペーンB (テスト専用) 
    ├── ペーンC (デプロイ専用)
    └── ペーンD (監視専用)
```

### ペーン制御パターン

#### 1. ペーン作成依頼
```javascript
// AIエージェント → 新規ペーン作成要求
{
  operation: "pane_create_request",
  requester: "ai_agent-parent-001",
  targetTab: "terminal-tab-001", 
  paneSpec: {
    purpose: "build_automation",
    workingDirectory: "/workspace/project",
    environment: {
      NODE_ENV: "production",
      BUILD_TARGET: "release"
    },
    tools: ["node", "npm", "docker"],
    initialCommands: ["cd /workspace/project", "npm install"]
  },
  coordination: {
    reportTo: "ai_agent-parent-001",
    collaborateWith: ["pane-test-002", "pane-deploy-003"]
  }
}
```

#### 2. ペーン間作業依頼
```javascript
// ペーンA → ペーンB への作業依頼
{
  operation: "work_request",
  fromPane: "pane-build-001",
  toPane: "pane-test-002",
  taskType: "test_execution",
  workDetails: {
    artifacts: "/build/output/app.tar.gz",
    testSuite: "integration",
    environment: "staging",
    expectedDuration: "5分"
  },
  deliverables: {
    testResults: "/reports/test-results.xml",
    coverageReport: "/reports/coverage.html",
    performanceMetrics: "/reports/performance.json"
  },
  dependencies: ["build_completion", "staging_ready"],
  deadline: "2025-06-23T15:30:00Z"
}
```

#### 3. レポート回収・統合
```javascript
// 親エージェント → 各ペーンからレポート回収
{
  operation: "report_collection",
  collector: "ai_agent-parent-001",
  targetPanes: [
    "pane-build-001",
    "pane-test-002", 
    "pane-deploy-003",
    "pane-monitor-004"
  ],
  reportTypes: [
    "execution_status",
    "performance_metrics", 
    "error_logs",
    "resource_usage"
  ],
  format: "json",
  aggregation: {
    enabled: true,
    template: "release_report",
    destination: "/reports/integrated/"
  }
}
```

## Socket.IOイベント設計

### ペーン制御イベント

#### ペーン作成系
```javascript
// AIエージェント → ペーン作成依頼
socket.emit("ai_agent:pane:create_request", {
  agentId: "ai_agent-parent-001",
  targetTabId: "terminal-tab-001",
  paneSpecification: {
    purpose: "build_automation",
    specialization: "nodejs_build",
    workingDirectory: "/workspace/app",
    environment: {
      NODE_ENV: "production",
      BUILD_TARGET: "release"
    },
    tools: ["node", "npm", "docker", "git"],
    initialSetup: [
      "cd /workspace/app",
      "git checkout release/v2.1.0", 
      "npm ci --production"
    ]
  },
  coordination: {
    reportingAgent: "ai_agent-parent-001",
    collaborationPanes: ["pane-test-002", "pane-deploy-003"]
  }
})

// システム → ペーン作成完了通知
socket.on("ai_agent:pane:created", (data) => {
  // {
  //   success: true,
  //   paneId: "pane-build-001",
  //   terminalId: "terminal-build-001", 
  //   agentAssignment: "ai_agent-parent-001",
  //   capabilities: ["command_execution", "file_monitoring", "progress_reporting"],
  //   status: "ready"
  // }
})
```

#### 作業依頼系
```javascript
// ペーン間作業依頼
socket.emit("ai_agent:pane:work_assign", {
  requesterId: "pane-build-001",
  targetPaneId: "pane-test-002", 
  workOrder: {
    taskId: "task-integration-test-001",
    taskType: "automated_testing",
    priority: "high",
    description: "ビルド成果物の統合テスト実行",
    inputArtifacts: [
      {
        type: "build_output",
        location: "/build/output/app.tar.gz",
        checksum: "sha256:abc123..."
      }
    ],
    requirements: {
      environment: "staging",
      testSuites: ["integration", "e2e"],
      timeout: "10分"
    },
    deliverables: [
      {
        type: "test_results",
        format: "junit_xml",
        location: "/reports/test-results.xml"
      },
      {
        type: "coverage_report", 
        format: "html",
        location: "/reports/coverage/"
      }
    ]
  },
  coordination: {
    parentAgent: "ai_agent-parent-001",
    notifyOnCompletion: true,
    escalateOnError: true
  }
})

// 作業受諾・拒否応答
socket.on("ai_agent:pane:work_response", (data) => {
  // {
  //   taskId: "task-integration-test-001",
  //   responderId: "pane-test-002",
  //   status: "accepted" | "rejected" | "queued",
  //   estimatedStartTime: "2025-06-23T15:15:00Z",
  //   estimatedCompletion: "2025-06-23T15:25:00Z",
  //   reason: "Ready to execute", // rejection時の理由等
  //   resourceRequirements: {
  //     cpu: "2 cores",
  //     memory: "4GB", 
  //     disk: "1GB"
  //   }
  // }
})
```

#### 進捗・レポート系
```javascript
// 作業進捗報告
socket.emit("ai_agent:pane:progress_report", {
  paneId: "pane-test-002",
  taskId: "task-integration-test-001",
  progress: {
    percentage: 65,
    currentStage: "e2e_testing",
    completedStages: ["setup", "unit_tests", "integration_tests"],
    remainingStages: ["e2e_tests", "report_generation"],
    estimatedTimeRemaining: "3分"
  },
  metrics: {
    testsRun: 245,
    testsPassed: 242,
    testsFailed: 3,
    averageExecutionTime: "1.2s"
  },
  issues: [
    {
      severity: "warning",
      message: "3 tests failed in payment module",
      details: "Non-critical UI timing issues"
    }
  ]
})

// レポート回収依頼
socket.emit("ai_agent:pane:report_request", {
  requesterId: "ai_agent-parent-001",
  targetPanes: [
    "pane-build-001",
    "pane-test-002",
    "pane-deploy-003"
  ],
  reportScope: {
    timeRange: {
      start: "2025-06-23T15:00:00Z",
      end: "2025-06-23T15:30:00Z"
    },
    includeMetrics: true,
    includeArtifacts: true,
    includeErrorLogs: true
  },
  aggregation: {
    format: "json",
    template: "release_summary",
    destination: "/reports/release-v2.1.0/"
  }
})

// レポート提出
socket.on("ai_agent:pane:report_submission", (data) => {
  // {
  //   paneId: "pane-test-002",
  //   reportId: "report-test-002-20250623", 
  //   reportData: {
  //     summary: {
  //       tasksCompleted: 3,
  //       totalExecutionTime: "8分32秒",
  //       successRate: 98.5
  //     },
  //     artifacts: [
  //       {
  //         type: "test_results",
  //         path: "/reports/test-results.xml",
  //         size: "245KB"
  //       }
  //     ],
  //     metrics: { ... },
  //     logs: { ... }
  //   }
  // }
})
```

#### ペーン間協調
```javascript
// ペーン間直接通信
socket.emit("ai_agent:pane:communicate", {
  fromPane: "pane-deploy-003",
  toPane: "pane-monitor-004",
  messageType: "deployment_notification",
  message: {
    event: "deployment_completed",
    deploymentId: "deploy-v2.1.0-001",
    environment: "production",
    endpoints: [
      "https://api.example.com/health",
      "https://app.example.com/status"
    ],
    expectedBehavior: {
      healthCheck: "HTTP 200",
      responseTime: "< 500ms",
      errorRate: "< 0.1%"
    },
    monitoringDuration: "30分"
  }
})

// ペーン間協調応答
socket.on("ai_agent:pane:communicate_response", (data) => {
  // {
  //   fromPane: "pane-monitor-004",
  //   toPane: "pane-deploy-003",
  //   responseType: "monitoring_confirmation",
  //   message: {
  //     status: "monitoring_started",
  //     monitoringId: "monitor-prod-v2.1.0",
  //     dashboardUrl: "https://grafana.example.com/d/app-monitoring",
  //     alertChannels: ["slack", "email", "parent_agent"]
  //   }
  // }
})
```

## バックエンド実装

### ペーン協調管理クラス
```python
# src/aetherterm/agentserver/services/pane_coordinator.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
import asyncio

class PaneStatus(Enum):
    IDLE = "idle"
    BUSY = "busy" 
    ERROR = "error"
    OFFLINE = "offline"

class TaskStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class PaneCapability:
    name: str
    version: str
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkOrder:
    task_id: str
    task_type: str
    requester_pane: str
    target_pane: str
    priority: str
    description: str
    input_artifacts: List[Dict[str, Any]]
    requirements: Dict[str, Any]
    deliverables: List[Dict[str, Any]]
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING

@dataclass
class PaneInfo:
    pane_id: str
    terminal_id: str
    agent_id: str
    purpose: str
    specialization: str
    working_directory: str
    capabilities: List[PaneCapability]
    status: PaneStatus = PaneStatus.IDLE
    current_tasks: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 3

class PaneCoordinator:
    def __init__(self):
        self.panes: Dict[str, PaneInfo] = {}
        self.work_orders: Dict[str, WorkOrder] = {}
        self.task_queue: Dict[str, List[str]] = {}  # pane_id -> [task_ids]
        self.reports: Dict[str, Dict[str, Any]] = {}
        
    async def register_pane(
        self, 
        pane_info: PaneInfo
    ) -> bool:
        """Register a new pane for coordination"""
        self.panes[pane_info.pane_id] = pane_info
        self.task_queue[pane_info.pane_id] = []
        return True
        
    async def create_work_order(
        self,
        requester_pane: str,
        target_pane: str, 
        task_type: str,
        task_details: Dict[str, Any]
    ) -> WorkOrder:
        """Create a work order between panes"""
        
        task_id = f"task-{uuid4().hex[:11]}"
        
        work_order = WorkOrder(
            task_id=task_id,
            task_type=task_type,
            requester_pane=requester_pane,
            target_pane=target_pane,
            priority=task_details.get("priority", "normal"),
            description=task_details.get("description", ""),
            input_artifacts=task_details.get("input_artifacts", []),
            requirements=task_details.get("requirements", {}),
            deliverables=task_details.get("deliverables", []),
            deadline=task_details.get("deadline")
        )
        
        self.work_orders[task_id] = work_order
        
        # Add to target pane's queue
        if target_pane in self.task_queue:
            self.task_queue[target_pane].append(task_id)
            
        return work_order
        
    async def accept_work_order(
        self,
        task_id: str,
        pane_id: str,
        estimated_completion: Optional[datetime] = None
    ) -> bool:
        """Accept a work order"""
        
        if task_id not in self.work_orders:
            return False
            
        work_order = self.work_orders[task_id]
        if work_order.target_pane != pane_id:
            return False
            
        work_order.status = TaskStatus.ACCEPTED
        
        # Update pane status
        if pane_id in self.panes:
            pane = self.panes[pane_id]
            pane.current_tasks.append(task_id)
            if len(pane.current_tasks) >= pane.max_concurrent_tasks:
                pane.status = PaneStatus.BUSY
                
        return True
        
    async def complete_work_order(
        self,
        task_id: str,
        pane_id: str,
        completion_data: Dict[str, Any]
    ) -> bool:
        """Complete a work order with results"""
        
        if task_id not in self.work_orders:
            return False
            
        work_order = self.work_orders[task_id]
        work_order.status = TaskStatus.COMPLETED
        
        # Update pane status
        if pane_id in self.panes:
            pane = self.panes[pane_id]
            if task_id in pane.current_tasks:
                pane.current_tasks.remove(task_id)
            if len(pane.current_tasks) < pane.max_concurrent_tasks:
                pane.status = PaneStatus.IDLE
                
        # Store completion data
        self.reports[task_id] = completion_data
        
        return True
        
    async def collect_reports(
        self,
        collector_id: str,
        target_panes: List[str],
        report_scope: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collect reports from multiple panes"""
        
        collected_reports = {}
        
        for pane_id in target_panes:
            if pane_id in self.panes:
                pane_reports = await self._get_pane_reports(
                    pane_id, report_scope
                )
                collected_reports[pane_id] = pane_reports
                
        return {
            "collector": collector_id,
            "collection_time": datetime.now().isoformat(),
            "scope": report_scope,
            "reports": collected_reports
        }
        
    async def _get_pane_reports(
        self,
        pane_id: str,
        scope: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get reports from a specific pane"""
        
        # Filter reports by time range if specified
        time_range = scope.get("timeRange")
        pane_reports = []
        
        for task_id, report in self.reports.items():
            work_order = self.work_orders.get(task_id)
            if work_order and work_order.target_pane == pane_id:
                if time_range:
                    # Filter by time range
                    if self._is_in_time_range(work_order.created_at, time_range):
                        pane_reports.append(report)
                else:
                    pane_reports.append(report)
                    
        return {
            "pane_id": pane_id,
            "report_count": len(pane_reports),
            "reports": pane_reports
        }
        
    def _is_in_time_range(
        self, 
        timestamp: datetime, 
        time_range: Dict[str, str]
    ) -> bool:
        """Check if timestamp is within specified range"""
        start = datetime.fromisoformat(time_range["start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(time_range["end"].replace("Z", "+00:00"))
        return start <= timestamp <= end
```

この設計により、AIエージェントは：

1. **ペーン作成**: 専用用途のペーンを動的作成
2. **作業依頼**: ペーン間での具体的なタスク配布
3. **進捗監視**: リアルタイムでの作業状況把握
4. **レポート統合**: 各ペーンからの結果収集・分析
5. **協調制御**: 複数ペーンの連携オーケストレーション

が可能になります。