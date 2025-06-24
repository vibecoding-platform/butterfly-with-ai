"""
OpenHands Client for AetherTerm Integration

Provides a Python client interface to communicate with OpenHands agents
through HTTP API and WebSocket connections.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, AsyncGenerator
from datetime import datetime
import aiohttp
import websockets

log = logging.getLogger("aetherterm.openhands.client")


@dataclass
class OpenHandsConfig:
    """Configuration for OpenHands client"""
    
    # API Configuration
    api_endpoint: str = "http://localhost:3000"
    ws_endpoint: str = "ws://localhost:3001"
    
    # Agent Configuration
    model: str = "claude-3-5-sonnet-20241022"
    max_iterations: int = 100
    workspace_dir: str = "/workspace"
    sandbox_type: str = "local"
    
    # Authentication
    api_key: Optional[str] = None
    
    # Timeouts
    request_timeout: int = 30
    task_timeout: int = 3600  # 1 hour
    
    # Advanced Options
    temperature: float = 0.0
    enable_auto_lint: bool = True
    enable_auto_test: bool = True
    github_token: Optional[str] = None


@dataclass
class OpenHandsTask:
    """Represents a task for OpenHands agent"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    instruction: str = ""
    model: Optional[str] = None
    workspace_base: Optional[str] = None
    files: Dict[str, str] = field(default_factory=dict)
    
    # Execution state
    status: str = "pending"  # pending, running, completed, failed, cancelled
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    output_log: list = field(default_factory=list)


class OpenHandsClient:
    """
    Async client for communicating with OpenHands agents
    """
    
    def __init__(self, config: Optional[OpenHandsConfig] = None):
        self.config = config or OpenHandsConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection: Optional[websockets.WebSocketServerProtocol] = None
        self.active_tasks: Dict[str, OpenHandsTask] = {}
        self.message_handlers: Dict[str, Callable] = {}
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        
    async def connect(self):
        """Initialize connection to OpenHands"""
        try:
            # Create HTTP session
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"Content-Type": "application/json"}
            )
            
            # Test API connection
            await self._test_connection()
            
            log.info(f"Connected to OpenHands at {self.config.api_endpoint}")
            
        except Exception as e:
            log.error(f"Failed to connect to OpenHands: {e}")
            raise
            
    async def disconnect(self):
        """Close connections to OpenHands"""
        if self.ws_connection:
            await self.ws_connection.close()
            self.ws_connection = None
            
        if self.session:
            await self.session.close()
            self.session = None
            
        log.info("Disconnected from OpenHands")
        
    async def _test_connection(self):
        """Test API connection to OpenHands"""
        if not self.session:
            raise RuntimeError("Session not initialized")
            
        try:
            async with self.session.get(f"{self.config.api_endpoint}/api/health") as response:
                if response.status != 200:
                    raise RuntimeError(f"OpenHands API returned status {response.status}")
                    
                data = await response.json()
                log.info(f"OpenHands health check: {data}")
                
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Failed to connect to OpenHands API: {e}")
            
    async def create_task(self, instruction: str, **kwargs) -> OpenHandsTask:
        """Create a new task for OpenHands agent"""
        task = OpenHandsTask(
            instruction=instruction,
            model=kwargs.get('model', self.config.model),
            workspace_base=kwargs.get('workspace_base', self.config.workspace_dir),
            files=kwargs.get('files', {})
        )
        
        self.active_tasks[task.id] = task
        log.info(f"Created task {task.id}: {instruction[:100]}...")
        
        return task
        
    async def start_task(self, task: OpenHandsTask) -> None:
        """Start execution of a task"""
        if not self.session:
            raise RuntimeError("Client not connected")
            
        task.status = "running"
        task.started_at = datetime.now()
        
        payload = {
            "instruction": task.instruction,
            "model": task.model or self.config.model,
            "max_iterations": self.config.max_iterations,
            "workspace_base": task.workspace_base,
            "task_id": task.id,
            "config": {
                "sandbox_type": self.config.sandbox_type,
                "enable_auto_lint": self.config.enable_auto_lint,
                "enable_auto_test": self.config.enable_auto_test,
                "temperature": self.config.temperature
            }
        }
        
        try:
            async with self.session.post(
                f"{self.config.api_endpoint}/api/agent/start",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Failed to start task: {error_text}")
                    
                result = await response.json()
                log.info(f"Started task {task.id}")
                
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now()
            log.error(f"Failed to start task {task.id}: {e}")
            raise
            
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get current status of a task"""
        if not self.session:
            raise RuntimeError("Client not connected")
            
        try:
            async with self.session.get(
                f"{self.config.api_endpoint}/api/agent/status/{task_id}"
            ) as response:
                if response.status == 404:
                    return {"status": "not_found"}
                elif response.status != 200:
                    raise RuntimeError(f"Status request failed: {response.status}")
                    
                return await response.json()
                
        except Exception as e:
            log.error(f"Failed to get task status {task_id}: {e}")
            raise
            
    async def stop_task(self, task_id: str) -> None:
        """Stop execution of a task"""
        if not self.session:
            raise RuntimeError("Client not connected")
            
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = "cancelled"
            task.completed_at = datetime.now()
            
        try:
            async with self.session.post(
                f"{self.config.api_endpoint}/api/agent/stop/{task_id}"
            ) as response:
                if response.status != 200:
                    log.warning(f"Stop request returned status {response.status}")
                    
                log.info(f"Stopped task {task_id}")
                
        except Exception as e:
            log.error(f"Failed to stop task {task_id}: {e}")
            raise
            
    async def stream_task_output(self, task_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream real-time output from a task"""
        try:
            ws_url = f"{self.config.ws_endpoint}/ws/agent/{task_id}"
            
            async with websockets.connect(ws_url) as websocket:
                self.ws_connection = websocket
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        
                        # Update task status if available
                        if task_id in self.active_tasks:
                            task = self.active_tasks[task_id]
                            task.output_log.append({
                                "timestamp": datetime.now().isoformat(),
                                "data": data
                            })
                            
                            if "status" in data:
                                task.status = data["status"]
                                if data["status"] in ["completed", "failed"]:
                                    task.completed_at = datetime.now()
                                    
                        yield data
                        
                    except json.JSONDecodeError as e:
                        log.warning(f"Invalid JSON from WebSocket: {e}")
                        continue
                        
        except Exception as e:
            log.error(f"WebSocket streaming failed for task {task_id}: {e}")
            raise
            
    async def get_workspace_files(self, task_id: str) -> Dict[str, str]:
        """Get files from task workspace"""
        if not self.session:
            raise RuntimeError("Client not connected")
            
        try:
            async with self.session.get(
                f"{self.config.api_endpoint}/api/workspace/{task_id}/files"
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Workspace request failed: {response.status}")
                    
                return await response.json()
                
        except Exception as e:
            log.error(f"Failed to get workspace files for task {task_id}: {e}")
            raise
            
    async def execute_interactive_command(self, task_id: str, command: str) -> Dict[str, Any]:
        """Execute an interactive command in the task environment"""
        if not self.session:
            raise RuntimeError("Client not connected")
            
        payload = {
            "command": command,
            "task_id": task_id
        }
        
        try:
            async with self.session.post(
                f"{self.config.api_endpoint}/api/agent/execute",
                json=payload
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Command execution failed: {response.status}")
                    
                return await response.json()
                
        except Exception as e:
            log.error(f"Failed to execute command for task {task_id}: {e}")
            raise
            
    def get_active_tasks(self) -> Dict[str, OpenHandsTask]:
        """Get all currently active tasks"""
        return self.active_tasks.copy()
        
    def get_task(self, task_id: str) -> Optional[OpenHandsTask]:
        """Get a specific task by ID"""
        return self.active_tasks.get(task_id)