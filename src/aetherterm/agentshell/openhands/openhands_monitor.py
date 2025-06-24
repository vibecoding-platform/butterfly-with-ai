"""
OpenHands Monitoring and Progress Tracking

Provides real-time monitoring of OpenHands agent execution
with progress visualization and reporting capabilities.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .openhands_client import OpenHandsClient, OpenHandsTask

log = logging.getLogger("aetherterm.openhands.monitor")


@dataclass
class ExecutionMetrics:
    """Metrics for OpenHands execution monitoring"""
    
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    # Progress tracking
    total_iterations: int = 0
    completed_iterations: int = 0
    current_step: str = ""
    
    # Performance metrics
    actions_count: int = 0
    observations_count: int = 0
    errors_count: int = 0
    
    # Resource usage
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    
    # File operations
    files_created: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    
    def get_progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_iterations == 0:
            return 0.0
        return min((self.completed_iterations / self.total_iterations) * 100, 100.0)
        
    def get_elapsed_time(self) -> timedelta:
        """Get elapsed execution time"""
        return datetime.now() - self.start_time
        
    def get_time_since_activity(self) -> timedelta:
        """Get time since last activity"""
        return datetime.now() - self.last_activity


class OpenHandsMonitor:
    """
    Real-time monitoring for OpenHands agent execution
    """
    
    def __init__(self, client: OpenHandsClient):
        self.client = client
        self.metrics: Dict[str, ExecutionMetrics] = {}
        self.progress_callbacks: List[Callable] = []
        self.status_callbacks: List[Callable] = []
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
    def add_progress_callback(self, callback: Callable[[str, ExecutionMetrics], None]):
        """Add callback for progress updates"""
        self.progress_callbacks.append(callback)
        
    def add_status_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add callback for status updates"""
        self.status_callbacks.append(callback)
        
    async def start_monitoring(self, task_id: str) -> None:
        """Start monitoring a task"""
        if task_id in self.monitoring_tasks:
            log.warning(f"Already monitoring task {task_id}")
            return
            
        # Initialize metrics
        self.metrics[task_id] = ExecutionMetrics()
        
        # Start monitoring task
        monitor_task = asyncio.create_task(self._monitor_task(task_id))
        self.monitoring_tasks[task_id] = monitor_task
        
        log.info(f"Started monitoring task {task_id}")
        
    async def stop_monitoring(self, task_id: str) -> None:
        """Stop monitoring a task"""
        if task_id in self.monitoring_tasks:
            task = self.monitoring_tasks[task_id]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
                
            del self.monitoring_tasks[task_id]
            
        if task_id in self.metrics:
            del self.metrics[task_id]
            
        log.info(f"Stopped monitoring task {task_id}")
        
    async def _monitor_task(self, task_id: str) -> None:
        """Monitor a single task's execution"""
        try:
            metrics = self.metrics[task_id]
            
            async for output in self.client.stream_task_output(task_id):
                try:
                    # Update metrics based on output
                    self._update_metrics_from_output(task_id, output)
                    
                    # Notify callbacks
                    await self._notify_progress_callbacks(task_id, metrics)
                    await self._notify_status_callbacks(task_id, output)
                    
                    # Check for completion
                    if output.get("status") in ["completed", "failed", "cancelled"]:
                        break
                        
                except Exception as e:
                    log.error(f"Error processing output for task {task_id}: {e}")
                    
        except Exception as e:
            log.error(f"Monitoring failed for task {task_id}: {e}")
        finally:
            # Cleanup
            if task_id in self.monitoring_tasks:
                del self.monitoring_tasks[task_id]
                
    def _update_metrics_from_output(self, task_id: str, output: Dict[str, Any]) -> None:
        """Update metrics based on agent output"""
        if task_id not in self.metrics:
            return
            
        metrics = self.metrics[task_id]
        metrics.last_activity = datetime.now()
        
        # Parse different types of output
        output_type = output.get("type", "")
        
        if output_type == "action":
            metrics.actions_count += 1
            
            # Track current step
            action_data = output.get("data", {})
            if "action" in action_data:
                metrics.current_step = f"Executing: {action_data['action']}"
                
        elif output_type == "observation":
            metrics.observations_count += 1
            
        elif output_type == "error":
            metrics.errors_count += 1
            
        elif output_type == "progress":
            # Update progress information
            progress_data = output.get("data", {})
            if "iteration" in progress_data:
                metrics.completed_iterations = progress_data["iteration"]
            if "total_iterations" in progress_data:
                metrics.total_iterations = progress_data["total_iterations"]
            if "step" in progress_data:
                metrics.current_step = progress_data["step"]
                
        elif output_type == "file_operation":
            # Track file operations
            file_data = output.get("data", {})
            operation = file_data.get("operation", "")
            
            if operation == "create":
                metrics.files_created += 1
            elif operation == "modify":
                metrics.files_modified += 1
            elif operation == "delete":
                metrics.files_deleted += 1
                
        elif output_type == "resource_usage":
            # Update resource metrics
            resource_data = output.get("data", {})
            metrics.memory_usage = resource_data.get("memory", 0.0)
            metrics.cpu_usage = resource_data.get("cpu", 0.0)
            
    async def _notify_progress_callbacks(self, task_id: str, metrics: ExecutionMetrics) -> None:
        """Notify progress callbacks"""
        for callback in self.progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task_id, metrics)
                else:
                    callback(task_id, metrics)
            except Exception as e:
                log.error(f"Progress callback error: {e}")
                
    async def _notify_status_callbacks(self, task_id: str, output: Dict[str, Any]) -> None:
        """Notify status callbacks"""
        for callback in self.status_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task_id, output)
                else:
                    callback(task_id, output)
            except Exception as e:
                log.error(f"Status callback error: {e}")
                
    def get_metrics(self, task_id: str) -> Optional[ExecutionMetrics]:
        """Get metrics for a task"""
        return self.metrics.get(task_id)
        
    def get_all_metrics(self) -> Dict[str, ExecutionMetrics]:
        """Get metrics for all monitored tasks"""
        return self.metrics.copy()
        
    def generate_progress_report(self, task_id: str) -> Dict[str, Any]:
        """Generate a comprehensive progress report"""
        metrics = self.metrics.get(task_id)
        if not metrics:
            return {"error": f"No metrics found for task {task_id}"}
            
        elapsed = metrics.get_elapsed_time()
        progress_pct = metrics.get_progress_percentage()
        
        # Estimate completion time
        eta = None
        if progress_pct > 0 and progress_pct < 100:
            total_estimated = (elapsed.total_seconds() / progress_pct) * 100
            eta_seconds = total_estimated - elapsed.total_seconds()
            eta = str(timedelta(seconds=int(eta_seconds)))
            
        report = {
            "task_id": task_id,
            "progress": {
                "percentage": round(progress_pct, 1),
                "current_step": metrics.current_step,
                "iterations": {
                    "completed": metrics.completed_iterations,
                    "total": metrics.total_iterations
                }
            },
            "timing": {
                "elapsed": str(elapsed),
                "estimated_completion": eta,
                "last_activity": metrics.last_activity.isoformat()
            },
            "activity": {
                "actions": metrics.actions_count,
                "observations": metrics.observations_count,
                "errors": metrics.errors_count
            },
            "files": {
                "created": metrics.files_created,
                "modified": metrics.files_modified,
                "deleted": metrics.files_deleted,
                "total_operations": metrics.files_created + metrics.files_modified + metrics.files_deleted
            },
            "resources": {
                "memory_usage": metrics.memory_usage,
                "cpu_usage": metrics.cpu_usage
            }
        }
        
        return report
        
    def generate_summary_dashboard(self) -> Dict[str, Any]:
        """Generate a summary dashboard for all monitored tasks"""
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "total_tasks": len(self.metrics),
            "active_tasks": len(self.monitoring_tasks),
            "tasks": []
        }
        
        for task_id, metrics in self.metrics.items():
            task_summary = {
                "id": task_id,
                "progress": round(metrics.get_progress_percentage(), 1),
                "current_step": metrics.current_step,
                "elapsed": str(metrics.get_elapsed_time()),
                "status": "active" if task_id in self.monitoring_tasks else "inactive",
                "actions": metrics.actions_count,
                "errors": metrics.errors_count
            }
            dashboard["tasks"].append(task_summary)
            
        return dashboard
        
    async def cleanup(self) -> None:
        """Clean up all monitoring tasks"""
        for task_id in list(self.monitoring_tasks.keys()):
            await self.stop_monitoring(task_id)
            
        self.metrics.clear()
        log.info("OpenHands monitor cleanup completed")