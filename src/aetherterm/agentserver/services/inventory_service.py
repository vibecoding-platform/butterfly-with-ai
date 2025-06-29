#!/usr/bin/env python3
"""
AetherTerm Inventory Service

Production-ready inventory management service using SteampipeClient for cloud and on-premises resources.
Provides unified inventory access across AWS, Azure, GCP, VMware, and Kubernetes environments.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from .steampipe_client import SteampipeClient, QueryResult

log = logging.getLogger("aetherterm.inventory")


@dataclass
class InventoryItem:
    """Represents a single inventory item from any provider"""

    provider: str
    resource_type: str
    resource_id: str
    name: str
    status: str
    location: str
    metadata: Dict[str, Any]
    last_updated: datetime


@dataclass
class ConnectionConfig:
    """Configuration for adding a new inventory connection"""

    provider: str
    name: str
    credentials: Dict[str, str]
    enabled: bool = True


class HybridInventoryService:
    """Production-ready hybrid inventory service using SteampipeClient"""

    def __init__(self, steampipe_host: str = "localhost", steampipe_port: int = 9193):
        """Initialize the inventory service with SteampipeClient"""
        self.steampipe_client = SteampipeClient(db_host=steampipe_host, db_port=steampipe_port)
        self.initialized = False
        self.inventory_cache: Dict[str, List[InventoryItem]] = {}
        self.last_sync: Optional[datetime] = None

    async def initialize(self) -> bool:
        """Initialize the inventory service and establish database connections"""
        try:
            log.info("Initializing Hybrid Inventory Service")

            # Initialize the SteampipeClient database pool
            success = await self.steampipe_client.initialize()
            if not success:
                log.error("Failed to initialize Steampipe database connection")
                return False

            self.initialized = True
            log.info("Inventory service initialized successfully")
            return True

        except Exception as e:
            log.error(f"Failed to initialize inventory service: {e}")
            return False

    async def close(self):
        """Clean up resources and close connections"""
        try:
            if self.steampipe_client:
                await self.steampipe_client.close()
            log.info("Inventory service closed successfully")
        except Exception as e:
            log.error(f"Error closing inventory service: {e}")

    async def add_connection(self, config: ConnectionConfig) -> bool:
        """Add a new inventory connection configuration"""
        if not self.initialized:
            log.error("Service not initialized")
            return False

        try:
            log.info(f"Adding {config.provider} connection: {config.name}")

            success = False
            provider = config.provider.lower()

            if provider == "aws":
                success = self.steampipe_client.add_aws_connection(
                    name=config.name,
                    region=config.credentials.get("region", "us-east-1"),
                    access_key=config.credentials.get("access_key"),
                    secret_key=config.credentials.get("secret_key"),
                    profile=config.credentials.get("profile"),
                )

            elif provider == "azure":
                success = self.steampipe_client.add_azure_connection(
                    name=config.name,
                    subscription_id=config.credentials.get("subscription_id", ""),
                    tenant_id=config.credentials.get("tenant_id"),
                    client_id=config.credentials.get("client_id"),
                    client_secret=config.credentials.get("client_secret"),
                )

            elif provider == "gcp":
                success = self.steampipe_client.add_gcp_connection(
                    name=config.name,
                    project=config.credentials.get("project_id", ""),
                    credentials_file=config.credentials.get("service_account_file"),
                )

            elif provider == "kubernetes":
                success = self.steampipe_client.add_kubernetes_connection(
                    name=config.name,
                    config_path=config.credentials.get("kubeconfig_file"),
                    context=config.credentials.get("context"),
                )

            else:
                log.error(f"Unsupported provider: {config.provider}")
                return False

            if success:
                log.info(f"Successfully added connection: {config.name}")
                # Clear cache to ensure fresh data on next query
                self.inventory_cache.clear()
            else:
                log.error(f"Failed to add connection: {config.name}")

            return success

        except Exception as e:
            log.error(f"Error adding connection {config.name}: {e}")
            return False

    async def test_connection(self, connection_name: str) -> bool:
        """Test a specific connection to verify it's working"""
        if not self.initialized:
            log.error("Service not initialized")
            return False

        try:
            return await self.steampipe_client.test_connection(connection_name)
        except Exception as e:
            log.error(f"Error testing connection {connection_name}: {e}")
            return False

    async def list_connections(self) -> Dict[str, Any]:
        """List all configured connections with their status"""
        if not self.initialized:
            return {"connections": [], "error": "Service not initialized"}

        try:
            connections = await self.steampipe_client.get_connections()

            return {
                "connections": connections,
                "total_count": len(connections),
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            log.error(f"Error listing connections: {e}")
            return {"connections": [], "error": str(e)}

    async def remove_connection(self, connection_name: str) -> bool:
        """Remove a connection configuration"""
        if not self.initialized:
            log.error("Service not initialized")
            return False

        try:
            success = await self.steampipe_client.remove_connection(connection_name)
            if success:
                # Clear cache to reflect the removal
                self.inventory_cache.clear()
                log.info(f"Removed connection: {connection_name}")
            return success

        except Exception as e:
            log.error(f"Error removing connection {connection_name}: {e}")
            return False

    async def get_unified_inventory(self, use_cache: bool = True) -> List[InventoryItem]:
        """Get unified inventory from all configured sources"""
        if not self.initialized:
            log.error("Service not initialized")
            return []

        cache_key = "unified_inventory"

        # Return cached results if available and not expired
        if use_cache and cache_key in self.inventory_cache:
            if self.last_sync and (datetime.now() - self.last_sync).seconds < 300:  # 5 minute cache
                log.debug("Returning cached inventory data")
                return self.inventory_cache[cache_key]

        try:
            log.info("Fetching unified inventory from all sources")
            all_items = []

            # Query for AWS resources
            await self._fetch_aws_resources(all_items)

            # Query for Azure resources
            await self._fetch_azure_resources(all_items)

            # Query for GCP resources
            await self._fetch_gcp_resources(all_items)

            # Query for Kubernetes resources
            await self._fetch_kubernetes_resources(all_items)

            # Update cache
            self.inventory_cache[cache_key] = all_items
            self.last_sync = datetime.now()

            log.info(f"Retrieved {len(all_items)} total inventory items")
            return all_items

        except Exception as e:
            log.error(f"Error getting unified inventory: {e}")
            return []

    async def _fetch_aws_resources(self, items: List[InventoryItem]):
        """Fetch AWS resources and add to items list"""
        try:
            # EC2 Instances
            query = """
            SELECT 'AWS' as provider, 'EC2' as resource_type, 
                   instance_id as resource_id, 
                   COALESCE(tags->>'Name', instance_id) as name,
                   instance_state->>'Name' as status, 
                   availability_zone as location,
                   row_to_json(aws_ec2_instance.*) as metadata
            FROM aws_ec2_instance
            ORDER BY launch_time DESC
            LIMIT 1000
            """

            result = await self.steampipe_client.query(query)
            for row in result.data:
                items.append(self._create_inventory_item(row))

            # S3 Buckets
            query = """
            SELECT 'AWS' as provider, 'S3' as resource_type,
                   name as resource_id, name,
                   'active' as status, region as location,
                   row_to_json(aws_s3_bucket.*) as metadata
            FROM aws_s3_bucket
            ORDER BY creation_date DESC
            LIMIT 1000
            """

            result = await self.steampipe_client.query(query)
            for row in result.data:
                items.append(self._create_inventory_item(row))

        except Exception as e:
            log.warning(f"Failed to fetch AWS resources: {e}")

    async def _fetch_azure_resources(self, items: List[InventoryItem]):
        """Fetch Azure resources and add to items list"""
        try:
            # Virtual Machines
            query = """
            SELECT 'Azure' as provider, 'VM' as resource_type,
                   vm_id as resource_id, name,
                   power_state as status, location,
                   row_to_json(azure_compute_virtual_machine.*) as metadata  
            FROM azure_compute_virtual_machine
            ORDER BY time_created DESC
            LIMIT 1000
            """

            result = await self.steampipe_client.query(query)
            for row in result.data:
                items.append(self._create_inventory_item(row))

        except Exception as e:
            log.warning(f"Failed to fetch Azure resources: {e}")

    async def _fetch_gcp_resources(self, items: List[InventoryItem]):
        """Fetch GCP resources and add to items list"""
        try:
            # Compute Instances
            query = """
            SELECT 'GCP' as provider, 'Instance' as resource_type,
                   name as resource_id, name,
                   status, zone as location,
                   row_to_json(gcp_compute_instance.*) as metadata
            FROM gcp_compute_instance
            ORDER BY creation_timestamp DESC
            LIMIT 1000
            """

            result = await self.steampipe_client.query(query)
            for row in result.data:
                items.append(self._create_inventory_item(row))

        except Exception as e:
            log.warning(f"Failed to fetch GCP resources: {e}")

    async def _fetch_kubernetes_resources(self, items: List[InventoryItem]):
        """Fetch Kubernetes resources and add to items list"""
        try:
            # Pods
            query = """
            SELECT 'Kubernetes' as provider, 'Pod' as resource_type,
                   namespace || '/' || name as resource_id, name,
                   phase as status, 
                   COALESCE(cluster_name, 'default') as location,
                   row_to_json(kubernetes_pod.*) as metadata
            FROM kubernetes_pod
            ORDER BY creation_timestamp DESC
            LIMIT 1000
            """

            result = await self.steampipe_client.query(query)
            for row in result.data:
                items.append(self._create_inventory_item(row))

            # Services
            query = """
            SELECT 'Kubernetes' as provider, 'Service' as resource_type,
                   namespace || '/' || name as resource_id, name,
                   'active' as status,
                   COALESCE(cluster_name, 'default') as location,
                   row_to_json(kubernetes_service.*) as metadata
            FROM kubernetes_service
            ORDER BY creation_timestamp DESC
            LIMIT 1000
            """

            result = await self.steampipe_client.query(query)
            for row in result.data:
                items.append(self._create_inventory_item(row))

        except Exception as e:
            log.warning(f"Failed to fetch Kubernetes resources: {e}")

    def _create_inventory_item(self, row: Dict[str, Any]) -> InventoryItem:
        """Create an InventoryItem from a query result row"""
        return InventoryItem(
            provider=row.get("provider", "unknown"),
            resource_type=row.get("resource_type", "unknown"),
            resource_id=row.get("resource_id", ""),
            name=row.get("name", "N/A"),
            status=row.get("status", "unknown"),
            location=row.get("location", "unknown"),
            metadata=row.get("metadata", {}),
            last_updated=datetime.now(),
        )

    async def search_resources(
        self,
        search_term: str,
        provider_filter: Optional[str] = None,
        resource_type_filter: Optional[str] = None,
    ) -> List[InventoryItem]:
        """Search inventory resources with optional filters"""
        if not self.initialized:
            log.error("Service not initialized")
            return []

        try:
            log.info(f"Searching resources for term: {search_term}")

            # Use SteampipeClient's search functionality for better performance
            search_results = await self.steampipe_client.search_resources(search_term)

            items = []
            search_lower = search_term.lower()

            for result in search_results:
                # Apply provider filter
                if (
                    provider_filter
                    and result.get("provider", "").lower() != provider_filter.lower()
                ):
                    continue

                # Apply resource type filter
                if (
                    resource_type_filter
                    and result.get("type", "").lower() != resource_type_filter.lower()
                ):
                    continue

                # Convert to InventoryItem
                item = InventoryItem(
                    provider=result.get("provider", "unknown"),
                    resource_type=result.get("type", "unknown"),
                    resource_id=result.get("instance_id", ""),
                    name=result.get("name", "N/A"),
                    status=result.get("status", "unknown"),
                    location=result.get("location", "unknown"),
                    metadata={},
                    last_updated=datetime.now(),
                )
                items.append(item)

            # Fallback to local search if SteampipeClient search doesn't work
            if not items:
                log.debug("Falling back to local inventory search")
                all_items = await self.get_unified_inventory()

                for item in all_items:
                    # Provider filter
                    if provider_filter and item.provider.lower() != provider_filter.lower():
                        continue

                    # Resource type filter
                    if (
                        resource_type_filter
                        and item.resource_type.lower() != resource_type_filter.lower()
                    ):
                        continue

                    # Search in name, resource_id, and location
                    if (
                        search_lower in item.name.lower()
                        or search_lower in item.resource_id.lower()
                        or search_lower in item.location.lower()
                    ):
                        items.append(item)

            log.info(f"Found {len(items)} matching resources")
            return items

        except Exception as e:
            log.error(f"Error searching resources: {e}")
            return []

    async def get_summary(self) -> Dict[str, Any]:
        """Get inventory summary statistics"""
        if not self.initialized:
            return {"error": "Service not initialized"}

        try:
            log.info("Generating inventory summary")

            # Get resource counts from SteampipeClient
            resource_counts = await self.steampipe_client.get_resource_counts()

            # Get detailed inventory for additional statistics
            all_items = await self.get_unified_inventory()

            summary = {
                "total_resources": len(all_items),
                "resource_counts": resource_counts,
                "by_provider": {},
                "by_resource_type": {},
                "by_status": {},
                "by_location": {},
                "last_updated": datetime.now().isoformat(),
                "cache_status": {
                    "last_sync": self.last_sync.isoformat() if self.last_sync else None,
                    "cached_items": len(self.inventory_cache.get("unified_inventory", [])),
                },
            }

            # Calculate statistics from inventory items
            for item in all_items:
                # By provider
                provider = item.provider
                if provider not in summary["by_provider"]:
                    summary["by_provider"][provider] = 0
                summary["by_provider"][provider] += 1

                # By resource type
                resource_key = f"{provider}:{item.resource_type}"
                if resource_key not in summary["by_resource_type"]:
                    summary["by_resource_type"][resource_key] = 0
                summary["by_resource_type"][resource_key] += 1

                # By status
                status = item.status
                if status not in summary["by_status"]:
                    summary["by_status"][status] = 0
                summary["by_status"][status] += 1

                # By location
                location = item.location
                if location not in summary["by_location"]:
                    summary["by_location"][location] = 0
                summary["by_location"][location] += 1

            log.info("Inventory summary generated successfully")
            return summary

        except Exception as e:
            log.error(f"Error generating inventory summary: {e}")
            return {"error": str(e)}

    async def refresh_cache(self) -> bool:
        """Force refresh of inventory cache"""
        try:
            log.info("Refreshing inventory cache")
            self.inventory_cache.clear()
            await self.get_unified_inventory(use_cache=False)
            return True
        except Exception as e:
            log.error(f"Error refreshing cache: {e}")
            return False

    async def query_raw(self, query: str) -> QueryResult:
        """Execute a raw SQL query against the Steampipe database"""
        if not self.initialized:
            raise RuntimeError("Service not initialized")

        try:
            log.debug(f"Executing raw query: {query[:100]}...")
            return await self.steampipe_client.query(query)
        except Exception as e:
            log.error(f"Raw query execution failed: {e}")
            raise

    async def get_connection_status(self) -> Dict[str, Any]:
        """Get status of all connections"""
        if not self.initialized:
            return {"error": "Service not initialized"}

        try:
            connections = await self.steampipe_client.get_connections()
            status_info = {"total_connections": len(connections), "connections": []}

            for conn in connections:
                conn_status = {
                    "name": conn["name"],
                    "plugin": conn["plugin"],
                    "enabled": conn["enabled"],
                    "created_at": conn["created_at"],
                    "test_result": await self.test_connection(conn["name"]),
                }
                status_info["connections"].append(conn_status)

            return status_info

        except Exception as e:
            log.error(f"Error getting connection status: {e}")
            return {"error": str(e)}


# Global service instance
inventory_service = HybridInventoryService()
