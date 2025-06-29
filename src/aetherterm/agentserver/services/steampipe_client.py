#!/usr/bin/env python3
"""
Steampipe Python Client

Pure Python implementation for Steampipe integration without CLI dependencies.
"""

import asyncio
import asyncpg
import boto3
import psutil
import logging
import json
import tempfile
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime

log = logging.getLogger("aetherterm.steampipe")


@dataclass
class SteampipeConnection:
    """Steampipe connection configuration"""

    name: str
    plugin: str
    config: Dict[str, Any]
    enabled: bool = True
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class QueryResult:
    """Steampipe query result"""

    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    execution_time: float


class SteampipeClient:
    """Pure Python Steampipe client using direct cloud provider APIs"""

    def __init__(
        self,
        db_host: str = "localhost",
        db_port: int = 9193,
        db_name: str = "steampipe",
        db_user: str = "steampipe",
    ):
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.connections: Dict[str, SteampipeConnection] = {}
        self.pool = None

    async def initialize(self) -> bool:
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                min_size=1,
                max_size=10,
            )
            log.info("Steampipe database connection pool initialized")
            return True
        except Exception as e:
            log.warning(f"Failed to connect to Steampipe database: {e}")
            return False

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()

    def add_aws_connection(
        self,
        name: str,
        region: str = "us-east-1",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        profile: Optional[str] = None,
    ) -> bool:
        """Add AWS connection configuration"""
        config = {
            "region": region,
            "profile": profile,
            "access_key": access_key,
            "secret_key": secret_key,
        }

        connection = SteampipeConnection(name=name, plugin="aws", config=config)

        self.connections[name] = connection
        log.info(f"Added AWS connection: {name}")
        return True

    def add_azure_connection(
        self,
        name: str,
        subscription_id: str,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> bool:
        """Add Azure connection configuration"""
        config = {
            "subscription_id": subscription_id,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        connection = SteampipeConnection(name=name, plugin="azure", config=config)

        self.connections[name] = connection
        log.info(f"Added Azure connection: {name}")
        return True

    def add_gcp_connection(
        self, name: str, project: str, credentials_file: Optional[str] = None
    ) -> bool:
        """Add GCP connection configuration"""
        config = {"project": project, "credentials": credentials_file}

        connection = SteampipeConnection(name=name, plugin="gcp", config=config)

        self.connections[name] = connection
        log.info(f"Added GCP connection: {name}")
        return True

    def add_kubernetes_connection(
        self, name: str, config_path: Optional[str] = None, context: Optional[str] = None
    ) -> bool:
        """Add Kubernetes connection configuration"""
        config = {"config_path": config_path or "~/.kube/config", "context": context}

        connection = SteampipeConnection(name=name, plugin="kubernetes", config=config)

        self.connections[name] = connection
        log.info(f"Added Kubernetes connection: {name}")
        return True

    async def test_connection(self, connection_name: str) -> bool:
        """Test a specific connection"""
        if connection_name not in self.connections:
            return False

        connection = self.connections[connection_name]

        try:
            if connection.plugin == "aws":
                return await self._test_aws_connection(connection)
            elif connection.plugin == "azure":
                return await self._test_azure_connection(connection)
            elif connection.plugin == "gcp":
                return await self._test_gcp_connection(connection)
            elif connection.plugin == "kubernetes":
                return await self._test_k8s_connection(connection)

        except Exception as e:
            log.error(f"Connection test failed for {connection_name}: {e}")
            return False

    async def _test_aws_connection(self, connection: SteampipeConnection) -> bool:
        """Test AWS connection"""
        try:
            if connection.config.get("profile"):
                session = boto3.Session(profile_name=connection.config["profile"])
            else:
                session = boto3.Session(
                    aws_access_key_id=connection.config.get("access_key"),
                    aws_secret_access_key=connection.config.get("secret_key"),
                    region_name=connection.config.get("region", "us-east-1"),
                )

            # Test with STS get-caller-identity
            sts = session.client("sts")
            sts.get_caller_identity()
            return True
        except Exception as e:
            log.error(f"AWS connection test failed: {e}")
            return False

    async def _test_azure_connection(self, connection: SteampipeConnection) -> bool:
        """Test Azure connection"""
        try:
            from azure.identity import DefaultAzureCredential, ClientSecretCredential
            from azure.core.credentials import TokenCredential

            if connection.config.get("client_id") and connection.config.get("client_secret"):
                credential = ClientSecretCredential(
                    tenant_id=connection.config["tenant_id"],
                    client_id=connection.config["client_id"],
                    client_secret=connection.config["client_secret"],
                )
            else:
                credential = DefaultAzureCredential()

            # Test credential by getting token
            token = credential.get_token("https://management.azure.com/.default")
            return token is not None
        except Exception as e:
            log.error(f"Azure connection test failed: {e}")
            return False

    async def _test_gcp_connection(self, connection: SteampipeConnection) -> bool:
        """Test GCP connection"""
        try:
            from google.cloud import resource_manager

            if connection.config.get("credentials"):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = connection.config["credentials"]

            client = resource_manager.Client(project=connection.config["project"])
            # Test by listing projects
            list(client.list_projects())
            return True
        except Exception as e:
            log.error(f"GCP connection test failed: {e}")
            return False

    async def _test_k8s_connection(self, connection: SteampipeConnection) -> bool:
        """Test Kubernetes connection"""
        try:
            from kubernetes import client, config

            config_path = connection.config.get("config_path", "~/.kube/config")
            config_path = os.path.expanduser(config_path)

            if os.path.exists(config_path):
                config.load_kube_config(
                    config_file=config_path, context=connection.config.get("context")
                )
            else:
                config.load_incluster_config()

            # Test by listing namespaces
            v1 = client.CoreV1Api()
            v1.list_namespace()
            return True
        except Exception as e:
            log.error(f"Kubernetes connection test failed: {e}")
            return False

    async def query(self, sql: str, connection: Optional[str] = None) -> QueryResult:
        """Execute SQL query against Steampipe database"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        start_time = datetime.now()

        async with self.pool.acquire() as conn:
            try:
                # Execute query
                rows = await conn.fetch(sql)

                # Convert rows to dictionaries
                data = [dict(row) for row in rows]
                columns = list(rows[0].keys()) if rows else []

                execution_time = (datetime.now() - start_time).total_seconds()

                result = QueryResult(
                    data=data, columns=columns, row_count=len(data), execution_time=execution_time
                )

                log.debug(f"Query executed: {len(data)} rows in {execution_time:.3f}s")
                return result

            except Exception as e:
                log.error(f"Query execution failed: {e}")
                raise

    async def get_connections(self) -> List[Dict[str, Any]]:
        """Get all configured connections"""
        return [
            {
                "name": name,
                "plugin": conn.plugin,
                "enabled": conn.enabled,
                "created_at": conn.created_at.isoformat(),
                "config": {
                    k: v
                    for k, v in conn.config.items()
                    if k not in ["access_key", "secret_key", "client_secret"]
                },
            }
            for name, conn in self.connections.items()
        ]

    async def remove_connection(self, name: str) -> bool:
        """Remove a connection"""
        if name in self.connections:
            del self.connections[name]
            log.info(f"Removed connection: {name}")
            return True
        return False

    async def get_resource_counts(self) -> Dict[str, int]:
        """Get resource counts across all connections"""
        try:
            # Example queries for common resources
            queries = {
                "aws_instances": "SELECT COUNT(*) FROM aws_ec2_instance",
                "aws_s3_buckets": "SELECT COUNT(*) FROM aws_s3_bucket",
                "azure_vms": "SELECT COUNT(*) FROM azure_compute_virtual_machine",
                "gcp_instances": "SELECT COUNT(*) FROM gcp_compute_instance",
                "k8s_pods": "SELECT COUNT(*) FROM kubernetes_pod",
                "k8s_services": "SELECT COUNT(*) FROM kubernetes_service",
            }

            counts = {}
            for name, query in queries.items():
                try:
                    result = await self.query(query)
                    counts[name] = result.data[0]["count"] if result.data else 0
                except Exception:
                    counts[name] = 0

            return counts
        except Exception as e:
            log.error(f"Failed to get resource counts: {e}")
            return {}

    async def search_resources(
        self, search_term: str, resource_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search resources across connections"""
        try:
            # Build search query based on resource types
            if not resource_types:
                resource_types = ["instance", "bucket", "database", "service"]

            results = []

            # Search AWS EC2 instances
            if "instance" in resource_types:
                query = f"""
                SELECT 'aws' as provider, 'ec2_instance' as type, 
                       instance_id, tags->>'Name' as name, instance_state->>'Name' as status,
                       availability_zone as location
                FROM aws_ec2_instance 
                WHERE instance_id ILIKE '%{search_term}%' 
                   OR tags->>'Name' ILIKE '%{search_term}%'
                LIMIT 50
                """
                try:
                    result = await self.query(query)
                    results.extend(result.data)
                except Exception:
                    pass

            # Search S3 buckets
            if "bucket" in resource_types:
                query = f"""
                SELECT 'aws' as provider, 's3_bucket' as type,
                       name as instance_id, name, 'active' as status, region as location
                FROM aws_s3_bucket
                WHERE name ILIKE '%{search_term}%'
                LIMIT 50
                """
                try:
                    result = await self.query(query)
                    results.extend(result.data)
                except Exception:
                    pass

            return results
        except Exception as e:
            log.error(f"Resource search failed: {e}")
            return []


# Factory function for creating client instances
def create_steampipe_client(**kwargs) -> SteampipeClient:
    """Create a new Steampipe client instance"""
    return SteampipeClient(**kwargs)
