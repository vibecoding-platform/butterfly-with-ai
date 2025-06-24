"""
OpenHands Shell Integration

Provides shell command interface for controlling OpenHands agents
through AetherTerm's AgentShell.
"""

import asyncio
import json
import logging
import os
import shlex
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime

from .openhands_client import OpenHandsClient, OpenHandsConfig, OpenHandsTask

log = logging.getLogger("aetherterm.openhands.shell")


class OpenHandsShell:
    """
    Shell interface for OpenHands agent control
    """
    
    def __init__(self, config: Optional[OpenHandsConfig] = None):
        self.config = config or OpenHandsConfig()
        self.client: Optional[OpenHandsClient] = None
        self.current_task: Optional[OpenHandsTask] = None
        self.interactive_mode = False
        
    async def initialize(self):
        """Initialize OpenHands client connection"""
        try:
            self.client = OpenHandsClient(self.config)
            await self.client.connect()
            log.info("OpenHands shell interface initialized")
            
        except Exception as e:
            log.error(f"Failed to initialize OpenHands shell: {e}")
            raise
            
    async def cleanup(self):
        """Clean up resources"""
        if self.client:
            await self.client.disconnect()
            self.client = None
            
    async def execute_command(self, command_line: str) -> Dict[str, Any]:
        """
        Execute an OpenHands command
        
        Supported commands:
        - aether-openhands --task "description" [options]
        - aether-openhands --interactive
        - aether-openhands --status [task_id]
        - aether-openhands --stop [task_id]
        - aether-openhands --list
        - aether-openhands --workspace [task_id]
        """
        
        if not self.client:
            return {"error": "OpenHands client not initialized"}
            
        try:
            # Parse command
            args = shlex.split(command_line)
            if not args or args[0] != "aether-openhands":
                return {"error": "Invalid OpenHands command"}
                
            # Handle different command types
            if "--task" in args:
                return await self._handle_task_command(args)
            elif "--interactive" in args:
                return await self._handle_interactive_command(args)
            elif "--status" in args:
                return await self._handle_status_command(args)
            elif "--stop" in args:
                return await self._handle_stop_command(args)
            elif "--list" in args:
                return await self._handle_list_command(args)
            elif "--workspace" in args:
                return await self._handle_workspace_command(args)
            elif "--help" in args or "-h" in args:
                return self._get_help()
            else:
                return {"error": "Unknown command. Use --help for usage information."}
                
        except Exception as e:
            log.error(f"Error executing OpenHands command: {e}")
            return {"error": str(e)}
            
    async def _handle_task_command(self, args: List[str]) -> Dict[str, Any]:
        """Handle task creation and execution"""
        try:
            # Parse task arguments
            task_idx = args.index("--task") + 1
            if task_idx >= len(args):
                return {"error": "--task requires a description"}
                
            instruction = args[task_idx]
            
            # Parse additional options
            options = {}
            if "--model" in args:
                model_idx = args.index("--model") + 1
                if model_idx < len(args):
                    options["model"] = args[model_idx]
                    
            if "--workspace" in args:
                workspace_idx = args.index("--workspace") + 1
                if workspace_idx < len(args):
                    options["workspace_base"] = args[workspace_idx]
                    
            # Create and start task
            task = await self.client.create_task(instruction, **options)
            self.current_task = task
            
            await self.client.start_task(task)
            
            return {
                "success": True,
                "task_id": task.id,
                "message": f"Started task: {instruction}",
                "task": {
                    "id": task.id,
                    "instruction": task.instruction,
                    "status": task.status,
                    "created_at": task.created_at.isoformat()
                }
            }
            
        except Exception as e:
            return {"error": f"Failed to create task: {e}"}
            
    async def _handle_interactive_command(self, args: List[str]) -> Dict[str, Any]:
        """Handle interactive mode toggle"""
        self.interactive_mode = not self.interactive_mode
        
        if self.interactive_mode:
            return {
                "success": True,
                "message": "Entered interactive mode. Commands will be sent to OpenHands agent.",
                "interactive": True
            }
        else:
            return {
                "success": True,
                "message": "Exited interactive mode.",
                "interactive": False
            }
            
    async def _handle_status_command(self, args: List[str]) -> Dict[str, Any]:
        """Handle status query"""
        try:
            # Get task ID
            task_id = None
            if "--status" in args:
                status_idx = args.index("--status") + 1
                if status_idx < len(args):
                    task_id = args[status_idx]
                    
            if not task_id and self.current_task:
                task_id = self.current_task.id
                
            if not task_id:
                return {"error": "No task ID specified and no current task"}
                
            # Get status from client
            status = await self.client.get_task_status(task_id)
            
            # Get local task info if available
            local_task = self.client.get_task(task_id)
            
            result = {
                "success": True,
                "task_id": task_id,
                "status": status
            }
            
            if local_task:
                result["local_info"] = {
                    "instruction": local_task.instruction,
                    "created_at": local_task.created_at.isoformat(),
                    "started_at": local_task.started_at.isoformat() if local_task.started_at else None,
                    "completed_at": local_task.completed_at.isoformat() if local_task.completed_at else None,
                    "output_entries": len(local_task.output_log)
                }
                
            return result
            
        except Exception as e:
            return {"error": f"Failed to get status: {e}"}
            
    async def _handle_stop_command(self, args: List[str]) -> Dict[str, Any]:
        """Handle task termination"""
        try:
            # Get task ID
            task_id = None
            if "--stop" in args:
                stop_idx = args.index("--stop") + 1
                if stop_idx < len(args):
                    task_id = args[stop_idx]
                    
            if not task_id and self.current_task:
                task_id = self.current_task.id
                
            if not task_id:
                return {"error": "No task ID specified and no current task"}
                
            await self.client.stop_task(task_id)
            
            if self.current_task and self.current_task.id == task_id:
                self.current_task = None
                
            return {
                "success": True,
                "message": f"Stopped task {task_id}"
            }
            
        except Exception as e:
            return {"error": f"Failed to stop task: {e}"}
            
    async def _handle_list_command(self, args: List[str]) -> Dict[str, Any]:
        """Handle task listing"""
        try:
            active_tasks = self.client.get_active_tasks()
            
            task_list = []
            for task_id, task in active_tasks.items():
                task_info = {
                    "id": task_id,
                    "instruction": task.instruction[:80] + "..." if len(task.instruction) > 80 else task.instruction,
                    "status": task.status,
                    "created_at": task.created_at.isoformat(),
                    "started_at": task.started_at.isoformat() if task.started_at else None
                }
                task_list.append(task_info)
                
            return {
                "success": True,
                "tasks": task_list,
                "count": len(task_list),
                "current_task": self.current_task.id if self.current_task else None
            }
            
        except Exception as e:
            return {"error": f"Failed to list tasks: {e}"}
            
    async def _handle_workspace_command(self, args: List[str]) -> Dict[str, Any]:
        """Handle workspace file operations"""
        try:
            # Get task ID
            task_id = None
            if "--workspace" in args:
                workspace_idx = args.index("--workspace") + 1
                if workspace_idx < len(args):
                    task_id = args[workspace_idx]
                    
            if not task_id and self.current_task:
                task_id = self.current_task.id
                
            if not task_id:
                return {"error": "No task ID specified and no current task"}
                
            files = await self.client.get_workspace_files(task_id)
            
            return {
                "success": True,
                "task_id": task_id,
                "files": files,
                "file_count": len(files)
            }
            
        except Exception as e:
            return {"error": f"Failed to get workspace: {e}"}
            
    def _get_help(self) -> Dict[str, Any]:
        """Return help information"""
        help_text = """
OpenHands Agent Control Commands:

  aether-openhands --task "description" [options]
    Create and start a new coding task
    Options:
      --model MODEL       AI model to use (default: claude-3-5-sonnet-20241022)
      --workspace PATH    Workspace directory path

  aether-openhands --interactive
    Toggle interactive mode for direct agent communication

  aether-openhands --status [task_id]
    Show status of current or specified task

  aether-openhands --stop [task_id]
    Stop current or specified task

  aether-openhands --list
    List all active tasks

  aether-openhands --workspace [task_id]
    Show workspace files for current or specified task

  aether-openhands --help
    Show this help message

Examples:
  aether-openhands --task "Create a Python REST API with FastAPI"
  aether-openhands --task "Fix bug in main.py" --workspace /project
  aether-openhands --status
  aether-openhands --stop
        """
        
        return {
            "success": True,
            "help": help_text.strip()
        }
        
    async def handle_interactive_input(self, user_input: str) -> Dict[str, Any]:
        """Handle input in interactive mode"""
        if not self.interactive_mode:
            return {"error": "Not in interactive mode"}
            
        if not self.current_task:
            return {"error": "No active task for interactive communication"}
            
        try:
            result = await self.client.execute_interactive_command(
                self.current_task.id, 
                user_input
            )
            
            return {
                "success": True,
                "response": result,
                "task_id": self.current_task.id
            }
            
        except Exception as e:
            return {"error": f"Interactive command failed: {e}"}
            
    async def stream_output(self, task_id: Optional[str] = None) -> Any:
        """Stream output from a task"""
        if not task_id and self.current_task:
            task_id = self.current_task.id
            
        if not task_id:
            raise ValueError("No task ID specified")
            
        async for output in self.client.stream_task_output(task_id):
            yield output
            
    def is_interactive(self) -> bool:
        """Check if in interactive mode"""
        return self.interactive_mode
        
    def get_current_task(self) -> Optional[OpenHandsTask]:
        """Get current active task"""
        return self.current_task