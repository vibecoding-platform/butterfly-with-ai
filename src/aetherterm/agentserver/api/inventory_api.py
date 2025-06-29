#!/usr/bin/env python3
"""
AetherTerm Inventory API

FastAPI routes for hybrid cloud + on-premises inventory management.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from aetherterm.agentserver.services.inventory_service import (
    inventory_service,
    ConnectionConfig,
    InventoryItem,
)

# Initialize router
inventory_router = APIRouter(prefix="/api/inventory", tags=["inventory"])
log = logging.getLogger("aetherterm.inventory.api")


# Pydantic models for API
class ConnectionConfigRequest(BaseModel):
    provider: str = Field(..., description="Provider type (aws, azure, gcp, vsphere, kubernetes)")
    name: str = Field(..., description="Connection name")
    credentials: Dict[str, str] = Field(..., description="Provider credentials")
    enabled: bool = Field(default=True, description="Enable connection")


class InventorySearchRequest(BaseModel):
    search_term: str = Field(..., description="Search term")
    provider_filter: Optional[str] = Field(None, description="Filter by provider")
    resource_type_filter: Optional[str] = Field(None, description="Filter by resource type")


class QueryRequest(BaseModel):
    sql: str = Field(..., description="SQL query to execute")
    limit: Optional[int] = Field(default=1000, description="Result limit")


class InventoryItemResponse(BaseModel):
    provider: str
    resource_type: str
    resource_id: str
    name: str
    status: str
    location: str
    metadata: Dict[str, Any]
    last_updated: datetime


class InventorySummaryResponse(BaseModel):
    total_resources: int
    by_provider: Dict[str, int]
    by_resource_type: Dict[str, int]
    by_status: Dict[str, int]
    last_updated: str


class ConnectionListResponse(BaseModel):
    connections: Dict[str, Dict[str, Any]]
    active_plugins: List[str]
    steampipe_status: str


# API Routes


@inventory_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "inventory", "timestamp": datetime.now().isoformat()}


@inventory_router.post("/connections")
async def add_connection(config: ConnectionConfigRequest):
    """Add new inventory connection"""
    try:
        connection_config = ConnectionConfig(
            provider=config.provider,
            name=config.name,
            credentials=config.credentials,
            enabled=config.enabled,
        )

        success = await inventory_service.add_connection(connection_config)

        if success:
            log.info(f"Connection added successfully: {config.name}")
            return {
                "status": "success",
                "message": f"Connection '{config.name}' added successfully",
                "connection": {
                    "name": config.name,
                    "provider": config.provider,
                    "enabled": config.enabled,
                },
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to add connection '{config.name}'")

    except Exception as e:
        log.error(f"Error adding connection: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@inventory_router.get("/connections", response_model=ConnectionListResponse)
async def list_connections():
    """List all configured connections"""
    try:
        connections_info = await inventory_service.list_connections()
        return ConnectionListResponse(**connections_info)

    except Exception as e:
        log.error(f"Error listing connections: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list connections: {str(e)}")


@inventory_router.delete("/connections/{connection_name}")
async def remove_connection(connection_name: str):
    """Remove inventory connection"""
    try:
        # Remove connection from steampipe manager
        if connection_name in inventory_service.steampipe_manager.connections:
            del inventory_service.steampipe_manager.connections[connection_name]

            # Restart service to apply changes
            await inventory_service.steampipe_manager.start_steampipe_service()

            log.info(f"Connection removed: {connection_name}")
            return {
                "status": "success",
                "message": f"Connection '{connection_name}' removed successfully",
            }
        else:
            raise HTTPException(status_code=404, detail=f"Connection '{connection_name}' not found")

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error removing connection: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@inventory_router.get("/summary", response_model=InventorySummaryResponse)
async def get_inventory_summary():
    """Get inventory summary statistics"""
    try:
        summary = await inventory_service.get_inventory_summary()
        return InventorySummaryResponse(**summary)

    except Exception as e:
        log.error(f"Error getting inventory summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")


@inventory_router.get("/resources", response_model=List[InventoryItemResponse])
async def get_all_resources(
    limit: int = Query(default=1000, description="Maximum number of resources to return"),
    provider: Optional[str] = Query(default=None, description="Filter by provider"),
    resource_type: Optional[str] = Query(default=None, description="Filter by resource type"),
):
    """Get all inventory resources"""
    try:
        all_items = await inventory_service.get_unified_inventory()

        # Apply filters
        filtered_items = all_items

        if provider:
            filtered_items = [
                item for item in filtered_items if item.provider.lower() == provider.lower()
            ]

        if resource_type:
            filtered_items = [
                item
                for item in filtered_items
                if item.resource_type.lower() == resource_type.lower()
            ]

        # Apply limit
        limited_items = filtered_items[:limit]

        # Convert to response model
        return [
            InventoryItemResponse(
                provider=item.provider,
                resource_type=item.resource_type,
                resource_id=item.resource_id,
                name=item.name,
                status=item.status,
                location=item.location,
                metadata=item.metadata,
                last_updated=item.last_updated,
            )
            for item in limited_items
        ]

    except Exception as e:
        log.error(f"Error getting resources: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get resources: {str(e)}")


@inventory_router.post("/search", response_model=List[InventoryItemResponse])
async def search_inventory(search_request: InventorySearchRequest):
    """Search inventory across all sources"""
    try:
        results = await inventory_service.search_inventory(
            search_term=search_request.search_term, provider_filter=search_request.provider_filter
        )

        # Apply resource type filter if specified
        if search_request.resource_type_filter:
            results = [
                item
                for item in results
                if item.resource_type.lower() == search_request.resource_type_filter.lower()
            ]

        return [
            InventoryItemResponse(
                provider=item.provider,
                resource_type=item.resource_type,
                resource_id=item.resource_id,
                name=item.name,
                status=item.status,
                location=item.location,
                metadata=item.metadata,
                last_updated=item.last_updated,
            )
            for item in results
        ]

    except Exception as e:
        log.error(f"Error searching inventory: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@inventory_router.post("/query")
async def execute_custom_query(query_request: QueryRequest):
    """Execute custom SQL query against inventory"""
    try:
        # Basic SQL injection protection
        if any(
            keyword in query_request.sql.upper()
            for keyword in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"]
        ):
            raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")

        # Add LIMIT if not present
        query = query_request.sql
        if "LIMIT" not in query.upper() and query_request.limit:
            query += f" LIMIT {query_request.limit}"

        results = await inventory_service.query_inventory(query)

        return {
            "status": "success",
            "query": query_request.sql,
            "results": results,
            "count": len(results),
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error executing query: {e}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@inventory_router.get("/providers")
async def get_supported_providers():
    """Get list of supported inventory providers"""
    return {
        "cloud_providers": [
            {
                "name": "aws",
                "display_name": "Amazon Web Services",
                "required_credentials": ["access_key", "secret_key"],
                "optional_credentials": ["region", "profile"],
            },
            {
                "name": "azure",
                "display_name": "Microsoft Azure",
                "required_credentials": [
                    "client_id",
                    "client_secret",
                    "tenant_id",
                    "subscription_id",
                ],
                "optional_credentials": [],
            },
            {
                "name": "gcp",
                "display_name": "Google Cloud Platform",
                "required_credentials": ["service_account_file", "project_id"],
                "optional_credentials": [],
            },
        ],
        "onpremise_providers": [
            {
                "name": "vsphere",
                "display_name": "VMware vSphere",
                "required_credentials": ["vcenter_server", "username", "password"],
                "optional_credentials": ["insecure_ssl"],
            },
            {
                "name": "kubernetes",
                "display_name": "Kubernetes",
                "required_credentials": ["kubeconfig_file"],
                "optional_credentials": ["context"],
            },
            {
                "name": "docker",
                "display_name": "Docker",
                "required_credentials": [],
                "optional_credentials": ["docker_host"],
            },
        ],
    }


@inventory_router.post("/sync")
async def sync_inventory():
    """Trigger manual inventory synchronization"""
    try:
        # Restart Steampipe service to refresh connections
        await inventory_service.steampipe_manager.start_steampipe_service()

        # Get fresh inventory count
        summary = await inventory_service.get_inventory_summary()

        log.info("Manual inventory sync completed")
        return {
            "status": "success",
            "message": "Inventory synchronized successfully",
            "summary": summary,
        }

    except Exception as e:
        log.error(f"Error during inventory sync: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


# Health check for service dependencies
@inventory_router.get("/status")
async def get_service_status():
    """Get detailed service status"""
    try:
        connections_info = await inventory_service.list_connections()

        return {
            "service_status": "healthy",
            "steampipe_status": connections_info.get("steampipe_status", "unknown"),
            "active_connections": len(connections_info.get("connections", {})),
            "active_plugins": connections_info.get("active_plugins", []),
            "last_check": datetime.now().isoformat(),
        }

    except Exception as e:
        log.error(f"Error getting service status: {e}")
        return {
            "service_status": "unhealthy",
            "error": str(e),
            "last_check": datetime.now().isoformat(),
        }
