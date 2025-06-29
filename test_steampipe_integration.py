#!/usr/bin/env python3
"""
Steampipe統合の総合テストスイート
"""

import asyncio
import sys
import os

# プロジェクトルートを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aetherterm.agentserver.services.inventory_service import (
    HybridInventoryService,
    ConnectionConfig,
)
from aetherterm.agentserver.services.steampipe_client import SteampipeClient


class TestSteampipeIntegration:
    """Steampipe統合テストクラス"""

    async def test_steampipe_client_creation(self):
        """SteampipeClientの作成テスト"""
        client = SteampipeClient()
        assert client is not None
        assert client.db_host == "localhost"
        assert client.db_port == 9193
        await client.close()

    async def test_aws_connection_config(self, steampipe_client):
        """AWS接続設定テスト"""
        success = steampipe_client.add_aws_connection(
            name="test-aws", region="us-east-1", profile="default"
        )
        assert success is True

        connections = await steampipe_client.get_connections()
        assert len(connections) >= 1

        aws_conn = next((c for c in connections if c["name"] == "test-aws"), None)
        assert aws_conn is not None
        assert aws_conn["plugin"] == "aws"

    async def test_azure_connection_config(self, steampipe_client):
        """Azure接続設定テスト"""
        success = steampipe_client.add_azure_connection(
            name="test-azure", subscription_id="test-subscription-id"
        )
        assert success is True

        connections = await steampipe_client.get_connections()
        azure_conn = next((c for c in connections if c["name"] == "test-azure"), None)
        assert azure_conn is not None
        assert azure_conn["plugin"] == "azure"

    async def test_gcp_connection_config(self, steampipe_client):
        """GCP接続設定テスト"""
        success = steampipe_client.add_gcp_connection(name="test-gcp", project="test-project")
        assert success is True

        connections = await steampipe_client.get_connections()
        gcp_conn = next((c for c in connections if c["name"] == "test-gcp"), None)
        assert gcp_conn is not None
        assert gcp_conn["plugin"] == "gcp"

    async def test_kubernetes_connection_config(self, steampipe_client):
        """Kubernetes接続設定テスト"""
        success = steampipe_client.add_kubernetes_connection(
            name="test-k8s", config_path="~/.kube/config"
        )
        assert success is True

        connections = await steampipe_client.get_connections()
        k8s_conn = next((c for c in connections if c["name"] == "test-k8s"), None)
        assert k8s_conn is not None
        assert k8s_conn["plugin"] == "kubernetes"

    async def test_connection_removal(self, steampipe_client):
        """接続削除テスト"""
        # 接続を追加
        steampipe_client.add_aws_connection("temp-connection", region="us-west-2")

        # 削除前の接続数を確認
        connections_before = await steampipe_client.get_connections()
        count_before = len(connections_before)

        # 接続を削除
        success = await steampipe_client.remove_connection("temp-connection")
        assert success is True

        # 削除後の接続数を確認
        connections_after = await steampipe_client.get_connections()
        assert len(connections_after) == count_before - 1

    async def test_inventory_service_initialization(self, inventory_service):
        """インベントリーサービス初期化テスト"""
        # 初期化はデータベース接続が必要なため、基本的な作成のみテスト
        assert inventory_service is not None
        assert inventory_service.steampipe_client is not None
        assert inventory_service.initialized is False

    async def test_inventory_service_connection_management(self, inventory_service):
        """インベントリーサービス接続管理テスト"""
        # 接続設定を作成
        config = ConnectionConfig(
            provider="aws",
            name="test-aws-service",
            credentials={"region": "us-east-1", "profile": "default"},
        )

        # 接続を追加
        success = await inventory_service.add_connection(config)
        assert success is True

        # 接続一覧を取得
        connections = await inventory_service.list_connections()
        assert len(connections) >= 1

        # 追加した接続が含まれているかチェック
        aws_conn = next((c for c in connections if c["name"] == "test-aws-service"), None)
        assert aws_conn is not None


def run_async_test():
    """非同期テストの実行"""

    async def run_tests():
        test_instance = TestSteampipeIntegration()

        print("=== Steampipe統合テストスイート実行 ===")

        # 1. SteampipeClient作成テスト
        print("1. SteampipeClient作成テスト...", end=" ")
        try:
            await test_instance.test_steampipe_client_creation()
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")

        # 2. AWS接続設定テスト
        print("2. AWS接続設定テスト...", end=" ")
        client = SteampipeClient()
        try:
            await test_instance.test_aws_connection_config(client)
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")
        finally:
            await client.close()

        # 3. Azure接続設定テスト
        print("3. Azure接続設定テスト...", end=" ")
        client = SteampipeClient()
        try:
            await test_instance.test_azure_connection_config(client)
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")
        finally:
            await client.close()

        # 4. GCP接続設定テスト
        print("4. GCP接続設定テスト...", end=" ")
        client = SteampipeClient()
        try:
            await test_instance.test_gcp_connection_config(client)
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")
        finally:
            await client.close()

        # 5. Kubernetes接続設定テスト
        print("5. Kubernetes接続設定テスト...", end=" ")
        client = SteampipeClient()
        try:
            await test_instance.test_kubernetes_connection_config(client)
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")
        finally:
            await client.close()

        # 6. 接続削除テスト
        print("6. 接続削除テスト...", end=" ")
        client = SteampipeClient()
        try:
            await test_instance.test_connection_removal(client)
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")
        finally:
            await client.close()

        # 7. インベントリーサービス初期化テスト
        print("7. インベントリーサービス初期化テスト...", end=" ")
        service = HybridInventoryService()
        try:
            await test_instance.test_inventory_service_initialization(service)
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")
        finally:
            await service.close()

        # 8. インベントリーサービス接続管理テスト
        print("8. インベントリーサービス接続管理テスト...", end=" ")
        service = HybridInventoryService()
        try:
            await test_instance.test_inventory_service_connection_management(service)
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")
        finally:
            await service.close()

        print("\n=== テストスイート完了 ===")

    # テスト実行
    asyncio.run(run_tests())


if __name__ == "__main__":
    run_async_test()
