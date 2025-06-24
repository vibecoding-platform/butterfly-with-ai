# src/aetherterm/agentserver/services/pane_coordinator.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import uuid
import logging

logger = logging.getLogger(__name__)

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
        self.progress_callbacks: Dict[str, Callable] = {}
        
    async def register_pane(
        self, 
        pane_info: PaneInfo
    ) -> bool:
        """Register a new pane for coordination"""
        try:
            self.panes[pane_info.pane_id] = pane_info
            self.task_queue[pane_info.pane_id] = []
            logger.info(f"Registered pane {pane_info.pane_id} with specialization {pane_info.specialization}")
            return True
        except Exception as e:
            logger.error(f"Failed to register pane {pane_info.pane_id}: {e}")
            return False
        
    async def create_pane_request(
        self,
        requester_agent: str,
        target_tab_id: str,
        pane_specification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new pane creation request"""
        try:
            pane_id = f"pane-{pane_specification.get('purpose', 'general')}-{uuid.uuid4().hex[:8]}"
            terminal_id = f"terminal-{pane_specification.get('purpose', 'general')}-{uuid.uuid4().hex[:8]}"
            
            pane_info = PaneInfo(
                pane_id=pane_id,
                terminal_id=terminal_id,
                agent_id=requester_agent,
                purpose=pane_specification.get('purpose', 'general'),
                specialization=pane_specification.get('specialization', 'general'),
                working_directory=pane_specification.get('workingDirectory', '/'),
                capabilities=[
                    PaneCapability(name=cap, version="1.0") 
                    for cap in pane_specification.get('tools', [])
                ]
            )
            
            await self.register_pane(pane_info)
            
            return {
                "success": True,
                "paneId": pane_id,
                "terminalId": terminal_id,
                "agentAssignment": requester_agent,
                "capabilities": ["command_execution", "file_monitoring", "progress_reporting"],
                "status": "ready"
            }
            
        except Exception as e:
            logger.error(f"Failed to create pane request: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
    async def create_work_order(
        self,
        requester_pane: str,
        target_pane: str, 
        task_type: str,
        task_details: Dict[str, Any]
    ) -> WorkOrder:
        """Create a work order between panes"""
        
        task_id = f"task-{uuid.uuid4().hex[:11]}"
        
        work_order = WorkOrder(
            task_id=task_id,
            task_type=task_type,
            requester_pane=requester_pane,
            target_pane=target_pane,
            priority=task_details.get("priority", "normal"),
            description=task_details.get("description", ""),
            input_artifacts=task_details.get("inputArtifacts", []),
            requirements=task_details.get("requirements", {}),
            deliverables=task_details.get("deliverables", []),
            deadline=task_details.get("deadline")
        )
        
        self.work_orders[task_id] = work_order
        
        # Add to target pane's queue
        if target_pane in self.task_queue:
            self.task_queue[target_pane].append(task_id)
        else:
            self.task_queue[target_pane] = [task_id]
            
        logger.info(f"Created work order {task_id} from {requester_pane} to {target_pane}")
        return work_order
        
    async def accept_work_order(
        self,
        task_id: str,
        pane_id: str,
        estimated_completion: Optional[datetime] = None
    ) -> bool:
        """Accept a work order"""
        
        if task_id not in self.work_orders:
            logger.error(f"Work order {task_id} not found")
            return False
            
        work_order = self.work_orders[task_id]
        if work_order.target_pane != pane_id:
            logger.error(f"Work order {task_id} not assigned to pane {pane_id}")
            return False
            
        work_order.status = TaskStatus.ACCEPTED
        
        # Update pane status
        if pane_id in self.panes:
            pane = self.panes[pane_id]
            pane.current_tasks.append(task_id)
            if len(pane.current_tasks) >= pane.max_concurrent_tasks:
                pane.status = PaneStatus.BUSY
                
        logger.info(f"Work order {task_id} accepted by pane {pane_id}")
        return True
        
    async def update_task_progress(
        self,
        task_id: str,
        pane_id: str,
        progress_data: Dict[str, Any]
    ) -> bool:
        """Update task progress"""
        try:
            if task_id not in self.work_orders:
                return False
                
            work_order = self.work_orders[task_id]
            work_order.status = TaskStatus.IN_PROGRESS
            
            # Store progress data
            if task_id not in self.reports:
                self.reports[task_id] = {}
            
            self.reports[task_id].update({
                "progress": progress_data,
                "last_updated": datetime.now().isoformat()
            })
            
            # Call progress callback if registered
            if task_id in self.progress_callbacks:
                await self.progress_callbacks[task_id](progress_data)
                
            logger.info(f"Updated progress for task {task_id}: {progress_data.get('percentage', 0)}%")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task progress {task_id}: {e}")
            return False
        
    async def complete_work_order(
        self,
        task_id: str,
        pane_id: str,
        completion_data: Dict[str, Any]
    ) -> bool:
        """Complete a work order with results"""
        
        if task_id not in self.work_orders:
            logger.error(f"Work order {task_id} not found")
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
        self.reports[task_id] = {
            **self.reports.get(task_id, {}),
            "completion": completion_data,
            "completed_at": datetime.now().isoformat()
        }
        
        logger.info(f"Work order {task_id} completed by pane {pane_id}")
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
                
        logger.info(f"Collected reports from {len(collected_reports)} panes for collector {collector_id}")
        
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
        try:
            start = datetime.fromisoformat(time_range["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(time_range["end"].replace("Z", "+00:00"))
            return start <= timestamp <= end
        except Exception as e:
            logger.error(f"Error parsing time range: {e}")
            return True
            
    async def get_pane_status(self, pane_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific pane"""
        if pane_id not in self.panes:
            return None
            
        pane = self.panes[pane_id]
        return {
            "paneId": pane.pane_id,
            "status": pane.status.value,
            "currentTasks": len(pane.current_tasks),
            "maxConcurrentTasks": pane.max_concurrent_tasks,
            "specialization": pane.specialization,
            "purpose": pane.purpose
        }
        
    async def register_progress_callback(
        self,
        task_id: str,
        callback: Callable
    ):
        """Register a callback for task progress updates"""
        self.progress_callbacks[task_id] = callback

# Global instance
_pane_coordinator_instance = None

def get_pane_coordinator() -> PaneCoordinator:
    """Get global PaneCoordinator instance"""
    global _pane_coordinator_instance
    if _pane_coordinator_instance is None:
        _pane_coordinator_instance = PaneCoordinator()
    return _pane_coordinator_instance