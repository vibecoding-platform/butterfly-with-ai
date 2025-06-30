"""
JupyterHub Management API
FastAPI integration for managing JupyterHub instances and user environments
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from tornado.httpclient import AsyncHTTPClient, HTTPError, HTTPRequest

# Database Models
Base = declarative_base()


class JupyterHubInstance(Base):
    __tablename__ = "jupyterhub_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    hub_url = Column(String, nullable=False)
    api_token = Column(String, nullable=False)
    namespace = Column(String, nullable=False)
    tenant_id = Column(String, nullable=False, index=True)

    # Configuration
    config = Column(Text)  # JSON
    spawner_class = Column(String, default="kubespawner.KubeSpawner")
    authenticator_class = Column(String, default="oauthenticator.generic.GenericOAuthenticator")

    # Status
    status = Column(String, default="active")  # active, maintenance, error
    version = Column(String)
    last_health_check = Column(DateTime, default=datetime.utcnow)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String)

    # Resource limits
    max_users = Column(Integer, default=100)
    max_concurrent_spawns = Column(Integer, default=10)

    # Features
    ai_enabled = Column(Boolean, default=True)
    auto_scaling_enabled = Column(Boolean, default=False)
    monitoring_enabled = Column(Boolean, default=True)


class UserServer(Base):
    __tablename__ = "user_servers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hub_instance_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    server_name = Column(String, default="")  # Named servers
    tenant_id = Column(String, nullable=False, index=True)

    # Server configuration
    image = Column(String)
    workspace_template = Column(String)
    resource_profile = Column(String)

    # Status
    status = Column(
        String, default="pending"
    )  # pending, spawning, running, stopping, stopped, error
    url = Column(String)
    internal_ip = Column(String)

    # Resource usage
    cpu_limit = Column(Float)
    memory_limit = Column(String)
    storage_capacity = Column(String)
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    stopped_at = Column(DateTime)
    last_activity = Column(DateTime, default=datetime.utcnow)

    # Configuration
    environment_vars = Column(Text)  # JSON
    volumes = Column(Text)  # JSON

    # Features
    ai_enabled = Column(Boolean, default=True)
    gpu_enabled = Column(Boolean, default=False)


# Pydantic Models for API
class JupyterHubInstanceModel(BaseModel):
    name: str = Field(description="Unique name for the hub instance")
    hub_url: str = Field(description="JupyterHub URL")
    api_token: str = Field(description="JupyterHub API token")
    namespace: str = Field(description="Kubernetes namespace")
    tenant_id: str = Field(description="Tenant identifier")
    config: Dict[str, Any] = Field(default_factory=dict, description="Hub configuration")
    spawner_class: str = Field(default="kubespawner.KubeSpawner", description="Spawner class")
    authenticator_class: str = Field(default="oauthenticator.generic.GenericOAuthenticator")
    max_users: int = Field(default=100, description="Maximum users")
    max_concurrent_spawns: int = Field(default=10, description="Max concurrent spawns")
    ai_enabled: bool = Field(default=True, description="Enable AI features")
    auto_scaling_enabled: bool = Field(default=False, description="Enable auto-scaling")


class UserServerModel(BaseModel):
    user_id: str = Field(description="User identifier")
    server_name: str = Field(default="", description="Named server (empty for default)")
    image: Optional[str] = Field(None, description="Container image")
    workspace_template: str = Field(default="python-dev", description="Workspace template")
    resource_profile: str = Field(default="medium", description="Resource profile")
    environment_vars: Dict[str, str] = Field(default_factory=dict)
    ai_enabled: bool = Field(default=True, description="Enable AI features")
    gpu_enabled: bool = Field(default=False, description="Enable GPU")


class SpawnServerRequest(BaseModel):
    hub_instance_name: str = Field(description="Hub instance name")
    server_config: UserServerModel


class ServerResponse(BaseModel):
    id: str
    hub_instance_id: str
    user_id: str
    server_name: str
    status: str
    url: Optional[str]
    workspace_template: str
    resource_profile: str
    created_at: str
    started_at: Optional[str]
    last_activity: Optional[str]
    cpu_usage: Optional[float]
    memory_usage: Optional[float]


class HubResponse(BaseModel):
    id: str
    name: str
    hub_url: str
    namespace: str
    tenant_id: str
    status: str
    version: Optional[str]
    max_users: int
    max_concurrent_spawns: int
    created_at: str
    last_health_check: Optional[str]


# Service Class
class JupyterHubManager:
    """Service for managing JupyterHub instances and user servers"""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db_session = Session()
        self.log = structlog.get_logger()
        self.http_client = AsyncHTTPClient()

    async def create_hub_instance(self, hub_config: JupyterHubInstanceModel) -> str:
        """Create a new JupyterHub instance"""
        try:
            # Check if name already exists
            existing = (
                self.db_session.query(JupyterHubInstance).filter_by(name=hub_config.name).first()
            )
            if existing:
                raise ValueError(f"Hub instance with name '{hub_config.name}' already exists")

            # Create database record
            hub_instance = JupyterHubInstance(
                name=hub_config.name,
                hub_url=hub_config.hub_url,
                api_token=hub_config.api_token,
                namespace=hub_config.namespace,
                tenant_id=hub_config.tenant_id,
                config=json.dumps(hub_config.config),
                spawner_class=hub_config.spawner_class,
                authenticator_class=hub_config.authenticator_class,
                max_users=hub_config.max_users,
                max_concurrent_spawns=hub_config.max_concurrent_spawns,
                ai_enabled=hub_config.ai_enabled,
                auto_scaling_enabled=hub_config.auto_scaling_enabled,
            )

            self.db_session.add(hub_instance)
            self.db_session.commit()

            # Verify connection to hub
            await self._health_check_hub(str(hub_instance.id))

            self.log.info(
                "JupyterHub instance created",
                hub_id=str(hub_instance.id),
                name=hub_config.name,
                tenant_id=hub_config.tenant_id,
            )

            return str(hub_instance.id)

        except Exception as e:
            self.log.error("Failed to create hub instance", error=str(e))
            self.db_session.rollback()
            raise

    async def spawn_user_server(
        self, hub_instance_name: str, server_config: UserServerModel
    ) -> str:
        """Spawn a user server on specified hub instance"""
        try:
            # Get hub instance
            hub_instance = (
                self.db_session.query(JupyterHubInstance).filter_by(name=hub_instance_name).first()
            )
            if not hub_instance:
                raise ValueError(f"Hub instance '{hub_instance_name}' not found")

            # Check if server already exists
            existing_server = (
                self.db_session.query(UserServer)
                .filter_by(
                    hub_instance_id=hub_instance.id,
                    user_id=server_config.user_id,
                    server_name=server_config.server_name,
                )
                .first()
            )

            if existing_server and existing_server.status in ["running", "spawning"]:
                raise ValueError(f"Server already exists for user {server_config.user_id}")

            # Create server record
            user_server = UserServer(
                hub_instance_id=hub_instance.id,
                user_id=server_config.user_id,
                server_name=server_config.server_name,
                tenant_id=hub_instance.tenant_id,
                image=server_config.image,
                workspace_template=server_config.workspace_template,
                resource_profile=server_config.resource_profile,
                environment_vars=json.dumps(server_config.environment_vars),
                ai_enabled=server_config.ai_enabled,
                gpu_enabled=server_config.gpu_enabled,
                status="spawning",
            )

            self.db_session.add(user_server)
            self.db_session.commit()

            # Spawn server via JupyterHub API
            await self._spawn_server_via_hub_api(hub_instance, user_server, server_config)

            self.log.info(
                "User server spawning initiated",
                server_id=str(user_server.id),
                user_id=server_config.user_id,
                hub_instance=hub_instance_name,
            )

            return str(user_server.id)

        except Exception as e:
            self.log.error("Failed to spawn user server", error=str(e))
            self.db_session.rollback()
            raise

    async def _spawn_server_via_hub_api(
        self,
        hub_instance: JupyterHubInstance,
        user_server: UserServer,
        server_config: UserServerModel,
    ):
        """Spawn server using JupyterHub API"""
        try:
            # Prepare spawn request
            spawn_data = {
                "image": server_config.image,
                "environment": server_config.environment_vars,
                "user_options": {
                    "workspace_template": server_config.workspace_template,
                    "resource_profile": server_config.resource_profile,
                    "ai_enabled": server_config.ai_enabled,
                    "gpu_enabled": server_config.gpu_enabled,
                },
            }

            # Build API URL
            api_url = f"{hub_instance.hub_url}/hub/api/users/{server_config.user_id}/server"
            if server_config.server_name:
                api_url += f"/{server_config.server_name}"

            # Make API request
            headers = {
                "Authorization": f"token {hub_instance.api_token}",
                "Content-Type": "application/json",
            }

            request = HTTPRequest(
                url=api_url,
                method="POST",
                headers=headers,
                body=json.dumps(spawn_data),
                request_timeout=60,
            )

            response = await self.http_client.fetch(request)

            if response.code in [201, 202]:
                user_server.status = "spawning"
                user_server.started_at = datetime.utcnow()
                self.db_session.commit()

                # Start monitoring task
                asyncio.create_task(self._monitor_server_spawn(str(user_server.id)))

            else:
                user_server.status = "error"
                self.db_session.commit()
                raise HTTPError(response.code, f"Hub API error: {response.body}")

        except HTTPError as e:
            self.log.error(
                "JupyterHub API error",
                server_id=str(user_server.id),
                status_code=e.code,
                response=e.response.body if e.response else None,
            )
            user_server.status = "error"
            self.db_session.commit()
            raise
        except Exception as e:
            self.log.error("Failed to spawn server via API", error=str(e))
            user_server.status = "error"
            self.db_session.commit()
            raise

    async def _monitor_server_spawn(self, server_id: str):
        """Monitor server spawning progress"""
        try:
            server = self.db_session.query(UserServer).filter_by(id=server_id).first()
            if not server:
                return

            hub_instance = (
                self.db_session.query(JupyterHubInstance)
                .filter_by(id=server.hub_instance_id)
                .first()
            )
            if not hub_instance:
                return

            # Poll server status
            timeout = 300  # 5 minutes
            start_time = time.time()

            while time.time() - start_time < timeout:
                try:
                    # Check server status via API
                    api_url = f"{hub_instance.hub_url}/hub/api/users/{server.user_id}"
                    headers = {"Authorization": f"token {hub_instance.api_token}"}

                    request = HTTPRequest(url=api_url, headers=headers)
                    response = await self.http_client.fetch(request)

                    if response.code == 200:
                        user_data = json.loads(response.body)
                        servers = user_data.get("servers", {})

                        server_key = server.server_name if server.server_name else ""
                        server_info = servers.get(server_key, {})

                        if server_info.get("ready", False):
                            # Server is ready
                            server.status = "running"
                            server.url = server_info.get("url", "")
                            server.last_activity = datetime.utcnow()
                            self.db_session.commit()

                            self.log.info(
                                "Server spawned successfully", server_id=server_id, url=server.url
                            )
                            return
                        if server_info.get("pending") == "spawn":
                            # Still spawning
                            server.status = "spawning"
                            self.db_session.commit()
                        else:
                            # Check for errors
                            if "error" in server_info:
                                server.status = "error"
                                self.db_session.commit()
                                self.log.error(
                                    "Server spawn failed",
                                    server_id=server_id,
                                    error=server_info.get("error"),
                                )
                                return

                    await asyncio.sleep(10)  # Check every 10 seconds

                except Exception as e:
                    self.log.warning("Error monitoring server spawn", error=str(e))
                    await asyncio.sleep(10)

            # Timeout reached
            server.status = "error"
            self.db_session.commit()
            self.log.error("Server spawn timeout", server_id=server_id)

        except Exception as e:
            self.log.error("Monitor server spawn failed", server_id=server_id, error=str(e))

    async def stop_user_server(self, server_id: str) -> bool:
        """Stop a user server"""
        try:
            server = self.db_session.query(UserServer).filter_by(id=server_id).first()
            if not server:
                raise ValueError(f"Server {server_id} not found")

            hub_instance = (
                self.db_session.query(JupyterHubInstance)
                .filter_by(id=server.hub_instance_id)
                .first()
            )
            if not hub_instance:
                raise ValueError("Hub instance not found")

            # Stop server via API
            api_url = f"{hub_instance.hub_url}/hub/api/users/{server.user_id}/server"
            if server.server_name:
                api_url += f"/{server.server_name}"

            headers = {"Authorization": f"token {hub_instance.api_token}"}

            request = HTTPRequest(url=api_url, method="DELETE", headers=headers, request_timeout=60)

            response = await self.http_client.fetch(request)

            if response.code in [202, 204]:
                server.status = "stopping"
                server.stopped_at = datetime.utcnow()
                self.db_session.commit()

                # Monitor stop process
                asyncio.create_task(self._monitor_server_stop(server_id))

                self.log.info("Server stop initiated", server_id=server_id)
                return True
            self.log.error("Failed to stop server", server_id=server_id, status_code=response.code)
            return False

        except Exception as e:
            self.log.error("Failed to stop server", server_id=server_id, error=str(e))
            return False

    async def _monitor_server_stop(self, server_id: str):
        """Monitor server stopping progress"""
        try:
            server = self.db_session.query(UserServer).filter_by(id=server_id).first()
            if not server:
                return

            # Wait for server to stop
            timeout = 120  # 2 minutes
            start_time = time.time()

            while time.time() - start_time < timeout:
                hub_instance = (
                    self.db_session.query(JupyterHubInstance)
                    .filter_by(id=server.hub_instance_id)
                    .first()
                )

                api_url = f"{hub_instance.hub_url}/hub/api/users/{server.user_id}"
                headers = {"Authorization": f"token {hub_instance.api_token}"}

                request = HTTPRequest(url=api_url, headers=headers)
                response = await self.http_client.fetch(request)

                if response.code == 200:
                    user_data = json.loads(response.body)
                    servers = user_data.get("servers", {})

                    server_key = server.server_name if server.server_name else ""
                    if server_key not in servers:
                        # Server stopped
                        server.status = "stopped"
                        server.stopped_at = datetime.utcnow()
                        self.db_session.commit()

                        self.log.info("Server stopped successfully", server_id=server_id)
                        return

                await asyncio.sleep(5)  # Check every 5 seconds

            # Timeout - force status update
            server.status = "stopped"
            self.db_session.commit()

        except Exception as e:
            self.log.error("Monitor server stop failed", server_id=server_id, error=str(e))

    async def _health_check_hub(self, hub_id: str):
        """Perform health check on hub instance"""
        try:
            hub_instance = self.db_session.query(JupyterHubInstance).filter_by(id=hub_id).first()
            if not hub_instance:
                return

            # Check hub API
            api_url = f"{hub_instance.hub_url}/hub/api/info"
            headers = {"Authorization": f"token {hub_instance.api_token}"}

            request = HTTPRequest(url=api_url, headers=headers, request_timeout=30)
            response = await self.http_client.fetch(request)

            if response.code == 200:
                info = json.loads(response.body)
                hub_instance.version = info.get("version", "unknown")
                hub_instance.status = "active"
                hub_instance.last_health_check = datetime.utcnow()
            else:
                hub_instance.status = "error"

            self.db_session.commit()

        except Exception as e:
            self.log.error("Health check failed", hub_id=hub_id, error=str(e))
            hub_instance.status = "error"
            self.db_session.commit()

    async def list_hub_instances(self, tenant_id: Optional[str] = None) -> List[Dict]:
        """List hub instances"""
        query = self.db_session.query(JupyterHubInstance)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)

        instances = query.all()

        result = []
        for instance in instances:
            result.append(
                {
                    "id": str(instance.id),
                    "name": instance.name,
                    "hub_url": instance.hub_url,
                    "namespace": instance.namespace,
                    "tenant_id": instance.tenant_id,
                    "status": instance.status,
                    "version": instance.version,
                    "max_users": instance.max_users,
                    "max_concurrent_spawns": instance.max_concurrent_spawns,
                    "created_at": instance.created_at.isoformat(),
                    "last_health_check": instance.last_health_check.isoformat()
                    if instance.last_health_check
                    else None,
                    "ai_enabled": instance.ai_enabled,
                    "auto_scaling_enabled": instance.auto_scaling_enabled,
                }
            )

        return result

    async def list_user_servers(
        self,
        hub_instance_name: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict]:
        """List user servers with filtering"""
        query = self.db_session.query(UserServer)

        if hub_instance_name:
            hub_instance = (
                self.db_session.query(JupyterHubInstance).filter_by(name=hub_instance_name).first()
            )
            if hub_instance:
                query = query.filter_by(hub_instance_id=hub_instance.id)

        if user_id:
            query = query.filter_by(user_id=user_id)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        if status:
            query = query.filter_by(status=status)

        servers = query.all()

        result = []
        for server in servers:
            result.append(
                {
                    "id": str(server.id),
                    "hub_instance_id": str(server.hub_instance_id),
                    "user_id": server.user_id,
                    "server_name": server.server_name,
                    "status": server.status,
                    "url": server.url,
                    "workspace_template": server.workspace_template,
                    "resource_profile": server.resource_profile,
                    "created_at": server.created_at.isoformat(),
                    "started_at": server.started_at.isoformat() if server.started_at else None,
                    "last_activity": server.last_activity.isoformat()
                    if server.last_activity
                    else None,
                    "cpu_usage": server.cpu_usage,
                    "memory_usage": server.memory_usage,
                    "ai_enabled": server.ai_enabled,
                    "gpu_enabled": server.gpu_enabled,
                }
            )

        return result

    async def get_server_details(self, server_id: str) -> Optional[Dict]:
        """Get detailed server information"""
        server = self.db_session.query(UserServer).filter_by(id=server_id).first()
        if not server:
            return None

        hub_instance = (
            self.db_session.query(JupyterHubInstance).filter_by(id=server.hub_instance_id).first()
        )

        return {
            "id": str(server.id),
            "hub_instance": {
                "id": str(hub_instance.id),
                "name": hub_instance.name,
                "hub_url": hub_instance.hub_url,
                "namespace": hub_instance.namespace,
            }
            if hub_instance
            else None,
            "user_id": server.user_id,
            "server_name": server.server_name,
            "tenant_id": server.tenant_id,
            "status": server.status,
            "url": server.url,
            "internal_ip": server.internal_ip,
            "image": server.image,
            "workspace_template": server.workspace_template,
            "resource_profile": server.resource_profile,
            "cpu_limit": server.cpu_limit,
            "memory_limit": server.memory_limit,
            "storage_capacity": server.storage_capacity,
            "cpu_usage": server.cpu_usage,
            "memory_usage": server.memory_usage,
            "environment_vars": json.loads(server.environment_vars)
            if server.environment_vars
            else {},
            "volumes": json.loads(server.volumes) if server.volumes else {},
            "created_at": server.created_at.isoformat(),
            "started_at": server.started_at.isoformat() if server.started_at else None,
            "stopped_at": server.stopped_at.isoformat() if server.stopped_at else None,
            "last_activity": server.last_activity.isoformat() if server.last_activity else None,
            "ai_enabled": server.ai_enabled,
            "gpu_enabled": server.gpu_enabled,
        }


# FastAPI Router
router = APIRouter(prefix="/api/jupyterhub", tags=["JupyterHub Management"])
log = structlog.get_logger()

# Global manager instance
hub_manager: Optional[JupyterHubManager] = None


def get_hub_manager() -> JupyterHubManager:
    """Dependency to get hub manager"""
    global hub_manager
    if hub_manager is None:
        import os

        database_url = os.environ.get("DATABASE_URL", "sqlite:///jupyterhub_management.db")
        hub_manager = JupyterHubManager(database_url)
    return hub_manager


# API Endpoints
@router.post("/hubs", response_model=Dict[str, str])
async def create_hub_instance(
    hub_config: JupyterHubInstanceModel, manager: JupyterHubManager = Depends(get_hub_manager)
):
    """Create a new JupyterHub instance"""
    try:
        hub_id = await manager.create_hub_instance(hub_config)
        return {"hub_id": hub_id, "message": "Hub instance created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error("Failed to create hub instance", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/hubs", response_model=List[HubResponse])
async def list_hub_instances(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    manager: JupyterHubManager = Depends(get_hub_manager),
):
    """List JupyterHub instances"""
    try:
        hubs = await manager.list_hub_instances(tenant_id=tenant_id)
        return [HubResponse(**hub) for hub in hubs]
    except Exception as e:
        log.error("Failed to list hub instances", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/servers", response_model=Dict[str, str])
async def spawn_user_server(
    request: SpawnServerRequest, manager: JupyterHubManager = Depends(get_hub_manager)
):
    """Spawn a user server"""
    try:
        server_id = await manager.spawn_user_server(
            request.hub_instance_name, request.server_config
        )
        return {"server_id": server_id, "message": "Server spawning initiated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error("Failed to spawn server", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/servers", response_model=List[ServerResponse])
async def list_user_servers(
    hub_instance_name: Optional[str] = Query(None, description="Filter by hub instance"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    manager: JupyterHubManager = Depends(get_hub_manager),
):
    """List user servers"""
    try:
        servers = await manager.list_user_servers(
            hub_instance_name=hub_instance_name, user_id=user_id, tenant_id=tenant_id, status=status
        )
        return [ServerResponse(**server) for server in servers]
    except Exception as e:
        log.error("Failed to list servers", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/servers/{server_id}")
async def get_server_details(
    server_id: str = Path(description="Server ID"),
    manager: JupyterHubManager = Depends(get_hub_manager),
):
    """Get detailed server information"""
    try:
        server = await manager.get_server_details(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        return server
    except HTTPException:
        raise
    except Exception as e:
        log.error("Failed to get server details", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/servers/{server_id}")
async def stop_user_server(
    server_id: str = Path(description="Server ID"),
    manager: JupyterHubManager = Depends(get_hub_manager),
):
    """Stop a user server"""
    try:
        success = await manager.stop_user_server(server_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to stop server")
        return {"message": "Server stop initiated"}
    except HTTPException:
        raise
    except Exception as e:
        log.error("Failed to stop server", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "jupyterhub-management",
        "timestamp": datetime.utcnow().isoformat(),
    }
