"""
OpenHands Integration for AgentShell

Provides seamless integration between AetherTerm's AgentShell
and OpenHands autonomous coding agents.
"""

import asyncio
import json
import logging
import os
import re
from typing import Dict, Any, Optional, Callable

from ..openhands import OpenHandsClient, OpenHandsConfig, OpenHandsShell, OpenHandsMonitor

log = logging.getLogger("aetherterm.agentshell.openhands")


class OpenHandsIntegration:
    """
    Integration layer for OpenHands in AgentShell
    """
    
    def __init__(self, terminal_output_callback: Optional[Callable] = None):
        self.terminal_output_callback = terminal_output_callback
        self.config = self._load_config()
        self.shell: Optional[OpenHandsShell] = None
        self.monitor: Optional[OpenHandsMonitor] = None
        self.client: Optional[OpenHandsClient] = None
        self.initialized = False
        
        # Command patterns
        self.openhands_command_pattern = re.compile(r'^aether-openhands\s+')
        
    def _load_config(self) -> OpenHandsConfig:
        """Load OpenHands configuration from environment and defaults"""
        config = OpenHandsConfig()
        
        # Override with environment variables
        config.api_endpoint = os.getenv('OPENHANDS_API_ENDPOINT', config.api_endpoint)
        config.ws_endpoint = os.getenv('OPENHANDS_WS_ENDPOINT', config.ws_endpoint)
        config.model = os.getenv('OPENHANDS_MODEL', config.model)
        config.workspace_dir = os.getenv('OPENHANDS_WORKSPACE_DIR', config.workspace_dir)
        config.sandbox_type = os.getenv('OPENHANDS_SANDBOX_TYPE', config.sandbox_type)
        config.api_key = os.getenv('OPENHANDS_API_KEY', config.api_key)
        
        # Parse numeric values
        if 'OPENHANDS_MAX_ITERATIONS' in os.environ:
            try:
                config.max_iterations = int(os.getenv('OPENHANDS_MAX_ITERATIONS'))
            except ValueError:
                log.warning("Invalid OPENHANDS_MAX_ITERATIONS value, using default")
                
        if 'OPENHANDS_TEMPERATURE' in os.environ:
            try:
                config.temperature = float(os.getenv('OPENHANDS_TEMPERATURE'))
            except ValueError:
                log.warning("Invalid OPENHANDS_TEMPERATURE value, using default")
                
        return config
        
    async def initialize(self) -> bool:
        """Initialize OpenHands integration"""
        try:
            # Initialize shell interface
            self.shell = OpenHandsShell(self.config)
            await self.shell.initialize()
            
            # Initialize monitor
            self.client = self.shell.client
            self.monitor = OpenHandsMonitor(self.client)
            
            # Setup monitoring callbacks
            self.monitor.add_progress_callback(self._on_progress_update)
            self.monitor.add_status_callback(self._on_status_update)
            
            self.initialized = True
            
            # Send initialization message to terminal
            await self._send_output("🤖 OpenHands integration initialized")
            await self._send_output(f"   API Endpoint: {self.config.api_endpoint}")
            await self._send_output(f"   Model: {self.config.model}")
            await self._send_output(f"   Workspace: {self.config.workspace_dir}")
            await self._send_output("")
            await self._send_output("Type 'aether-openhands --help' for available commands")
            
            log.info("OpenHands integration initialized successfully")
            return True
            
        except Exception as e:
            log.error(f"Failed to initialize OpenHands integration: {e}")
            await self._send_output(f"❌ Failed to initialize OpenHands: {e}")
            return False
            
    async def cleanup(self) -> None:
        """Clean up OpenHands integration"""
        try:
            if self.monitor:
                await self.monitor.cleanup()
                self.monitor = None
                
            if self.shell:
                await self.shell.cleanup()
                self.shell = None
                
            self.client = None
            self.initialized = False
            
            log.info("OpenHands integration cleaned up")
            
        except Exception as e:
            log.error(f"Error during OpenHands cleanup: {e}")
            
    async def handle_command(self, command: str) -> bool:
        """
        Handle OpenHands commands
        
        Returns True if command was handled, False otherwise
        """
        if not self.initialized:
            await self._send_output("❌ OpenHands integration not initialized")
            return False
            
        # Check if this is an OpenHands command
        if not self.openhands_command_pattern.match(command):
            # Check if we're in interactive mode
            if self.shell and self.shell.is_interactive():
                return await self._handle_interactive_input(command)
            return False
            
        try:
            # Execute OpenHands command
            result = await self.shell.execute_command(command)
            
            # Handle result
            if result.get("success"):
                await self._handle_success_result(result)
            else:
                await self._handle_error_result(result)
                
            # Start monitoring if a new task was created
            if "task_id" in result:
                task_id = result["task_id"]
                await self.monitor.start_monitoring(task_id)
                
            return True
            
        except Exception as e:
            log.error(f"Error handling OpenHands command: {e}")
            await self._send_output(f"❌ Command failed: {e}")
            return True  # Command was handled, even if it failed
            
    async def _handle_interactive_input(self, user_input: str) -> bool:
        """Handle input in interactive mode"""
        try:
            result = await self.shell.handle_interactive_input(user_input)
            
            if result.get("success"):
                response = result.get("response", {})
                await self._send_output(f"🤖 Agent: {response}")
            else:
                await self._send_output(f"❌ {result.get('error', 'Unknown error')}")
                
            return True
            
        except Exception as e:
            log.error(f"Error in interactive mode: {e}")
            await self._send_output(f"❌ Interactive command failed: {e}")
            return True
            
    async def _handle_success_result(self, result: Dict[str, Any]) -> None:
        """Handle successful command result"""
        message = result.get("message", "")
        if message:
            await self._send_output(f"✅ {message}")
            
        # Handle specific result types
        if "task" in result:
            task = result["task"]
            await self._send_output(f"   Task ID: {task['id']}")
            await self._send_output(f"   Status: {task['status']}")
            
        if "tasks" in result:
            tasks = result["tasks"]
            await self._send_output(f"📋 Active tasks ({result.get('count', 0)}):")
            for task in tasks:
                status_emoji = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌", "cancelled": "🛑"}.get(task["status"], "❓")
                await self._send_output(f"   {status_emoji} {task['id'][:8]}... - {task['instruction']}")
                
        if "files" in result:
            files = result["files"]
            await self._send_output(f"📁 Workspace files ({result.get('file_count', 0)}):")
            for file_path in sorted(files.keys()):
                await self._send_output(f"   📄 {file_path}")
                
        if "help" in result:
            help_text = result["help"]
            await self._send_output(help_text)
            
        if "interactive" in result:
            if result["interactive"]:
                await self._send_output("🔄 Interactive mode: ON")
                await self._send_output("   Your messages will be sent directly to the OpenHands agent")
                await self._send_output("   Type 'aether-openhands --interactive' again to exit")
            else:
                await self._send_output("🔄 Interactive mode: OFF")
                
    async def _handle_error_result(self, result: Dict[str, Any]) -> None:
        """Handle error result"""
        error = result.get("error", "Unknown error")
        await self._send_output(f"❌ Error: {error}")
        
    async def _on_progress_update(self, task_id: str, metrics) -> None:
        """Handle progress updates from monitor"""
        try:
            progress_pct = metrics.get_progress_percentage()
            current_step = metrics.current_step
            
            if current_step:
                await self._send_output(f"🔄 Task {task_id[:8]}... [{progress_pct:.1f}%] {current_step}")
                
        except Exception as e:
            log.error(f"Error handling progress update: {e}")
            
    async def _on_status_update(self, task_id: str, output: Dict[str, Any]) -> None:
        """Handle status updates from monitor"""
        try:
            output_type = output.get("type", "")
            
            if output_type == "action":
                action_data = output.get("data", {})
                action = action_data.get("action", "")
                if action:
                    await self._send_output(f"🎯 Action: {action}")
                    
            elif output_type == "observation":
                obs_data = output.get("data", {})
                content = obs_data.get("content", "")
                if content and len(content) < 200:  # Only show short observations
                    await self._send_output(f"👁️  Observation: {content}")
                    
            elif output_type == "error":
                error_data = output.get("data", {})
                error_msg = error_data.get("message", "")
                await self._send_output(f"❌ Error: {error_msg}")
                
            elif output_type == "completion":
                completion_data = output.get("data", {})
                success = completion_data.get("success", False)
                if success:
                    await self._send_output(f"✅ Task {task_id[:8]}... completed successfully!")
                else:
                    await self._send_output(f"❌ Task {task_id[:8]}... failed to complete")
                    
        except Exception as e:
            log.error(f"Error handling status update: {e}")
            
    async def _send_output(self, text: str) -> None:
        """Send output to terminal"""
        if self.terminal_output_callback:
            try:
                formatted_text = f"{text}\r\n"
                if asyncio.iscoroutinefunction(self.terminal_output_callback):
                    await self.terminal_output_callback(formatted_text)
                else:
                    self.terminal_output_callback(formatted_text)
            except Exception as e:
                log.error(f"Error sending output to terminal: {e}")
                
    def is_initialized(self) -> bool:
        """Check if integration is initialized"""
        return self.initialized
        
    def get_current_task(self):
        """Get current active task"""
        if self.shell:
            return self.shell.get_current_task()
        return None
        
    async def get_progress_report(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Get progress report for a task"""
        if not self.monitor:
            return {"error": "Monitor not initialized"}
            
        if not task_id:
            current_task = self.get_current_task()
            if current_task:
                task_id = current_task.id
            else:
                return {"error": "No task specified and no current task"}
                
        return self.monitor.generate_progress_report(task_id)
        
    async def get_dashboard(self) -> Dict[str, Any]:
        """Get monitoring dashboard"""
        if not self.monitor:
            return {"error": "Monitor not initialized"}
            
        return self.monitor.generate_summary_dashboard()