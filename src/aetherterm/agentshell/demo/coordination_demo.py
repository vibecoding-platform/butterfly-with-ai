"""
エージェント間調整のデモンストレーション

複数のエージェントが協調して作業する際の
親エージェントによる調整機能を示します。
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from ..agents.base import AgentCapability, AgentTask, InterventionType, UserIntervention
from ..service.agent_coordinator import CoordinationStrategy
from ..service.agent_orchestrator import AgentOrchestrator
from ..service.server_connector import ServerConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoordinationDemo:
    """エージェント間調整のデモ"""

    def __init__(self):
        # サーバーコネクターをモック
        self.server_connector = ServerConnector()
        self.orchestrator = AgentOrchestrator(self.server_connector)

        # 介入処理のコールバックを登録
        self.orchestrator.register_intervention_callback(self.handle_intervention_with_coordination)

    async def run_demo(self):
        """デモを実行"""
        logger.info("=== エージェント間調整デモ開始 ===")

        # シナリオ1: ファイル編集の競合
        await self.demo_file_conflict()

        # シナリオ2: リソース競合
        await self.demo_resource_conflict()

        # シナリオ3: 協調作業
        await self.demo_collaborative_work()

        logger.info("=== デモ完了 ===")

    async def demo_file_conflict(self):
        """ファイル編集の競合デモ"""
        logger.info("\n--- シナリオ1: ファイル編集の競合 ---")

        # 2つのエージェントが同じファイルを編集しようとする
        agents = [
            {
                "type": "openhands",
                "task_type": "code_editing",
                "description": "auth.pyのユーザー認証部分を実装",
                "capabilities": [AgentCapability.CODE_EDITING],
                "resources": ["app/auth/auth.py"],
            },
            {
                "type": "openhands",
                "task_type": "code_editing",
                "description": "auth.pyの権限チェック部分を実装",
                "capabilities": [AgentCapability.CODE_EDITING],
                "resources": ["app/auth/auth.py"],
            },
        ]

        # 協調エージェントを作成
        handles = await self.orchestrator.create_collaborative_agents(
            agents=agents,
            shared_goal="認証システムの実装",
            strategy=CoordinationStrategy.COLLABORATIVE,
        )

        logger.info(f"作成されたエージェント: {list(handles.keys())}")

        # 最初のエージェントが介入を要求
        agent1_id = list(handles.keys())[0]
        intervention1 = UserIntervention(
            type=InterventionType.APPROVAL,
            message="auth.pyファイルに以下の関数を追加してよろしいですか？\n- authenticate_user()\n- check_credentials()",
            options=["承認", "修正", "キャンセル"],
        )

        # 少し遅れて2番目のエージェントも介入を要求
        await asyncio.sleep(0.1)
        agent2_id = list(handles.keys())[1]
        intervention2 = UserIntervention(
            type=InterventionType.APPROVAL,
            message="auth.pyファイルに以下の関数を追加してよろしいですか？\n- check_permissions()\n- has_role()",
            options=["承認", "修正", "キャンセル"],
        )

        # 親エージェントが調整して応答
        response1 = await self.orchestrator.handle_intervention_request(agent1_id, intervention1)
        logger.info(f"エージェント1への応答: {response1}")

        response2 = await self.orchestrator.handle_intervention_request(agent2_id, intervention2)
        logger.info(f"エージェント2への応答: {response2}")

    async def demo_resource_conflict(self):
        """リソース競合のデモ"""
        logger.info("\n--- シナリオ2: リソース競合 ---")

        # データベース接続という限定リソースを複数エージェントが使用
        agents = [
            {
                "type": "openhands",
                "task_type": "data_migration",
                "description": "ユーザーデータの移行",
                "capabilities": [AgentCapability.SYSTEM_ADMINISTRATION],
                "resources": ["database_connection", "users_table"],
            },
            {
                "type": "openhands",
                "task_type": "data_analysis",
                "description": "ユーザー統計の分析",
                "capabilities": [AgentCapability.DATA_ANALYSIS],
                "resources": ["database_connection", "users_table"],
            },
        ]

        # 順次実行戦略で調整
        handles = await self.orchestrator.create_collaborative_agents(
            agents=agents, shared_goal="データベース操作", strategy=CoordinationStrategy.SEQUENTIAL
        )

        logger.info("リソース競合を順次実行で解決")

    async def demo_collaborative_work(self):
        """協調作業のデモ"""
        logger.info("\n--- シナリオ3: 協調作業 ---")

        # Webアプリケーションの実装を複数エージェントで分担
        agents = [
            {
                "type": "openhands",
                "task_type": "backend",
                "description": "REST APIエンドポイントの実装",
                "capabilities": [AgentCapability.CODE_GENERATION],
                "resources": ["app/api/", "app/models/"],
            },
            {
                "type": "openhands",
                "task_type": "frontend",
                "description": "Reactコンポーネントの実装",
                "capabilities": [AgentCapability.CODE_GENERATION],
                "resources": ["frontend/src/components/"],
            },
            {
                "type": "openhands",
                "task_type": "testing",
                "description": "統合テストの作成",
                "capabilities": [AgentCapability.TESTING],
                "resources": ["tests/"],
            },
        ]

        # 協調作業を設定
        handles = await self.orchestrator.create_collaborative_agents(
            agents=agents,
            shared_goal="Webアプリケーションの実装",
            strategy=CoordinationStrategy.COLLABORATIVE,
        )

        # エージェント間の依頼をシミュレート
        backend_agent = list(handles.keys())[0]
        frontend_agent = list(handles.keys())[1]

        # バックエンドからフロントエンドへAPIスキーマを共有
        request_id = await self.orchestrator.request_inter_agent_collaboration(
            from_agent=backend_agent,
            to_agent=frontend_agent,
            request_type="share_schema",
            payload={
                "schema": {
                    "endpoints": [
                        {"path": "/api/users", "method": "GET"},
                        {"path": "/api/users/{id}", "method": "GET"},
                        {"path": "/api/users", "method": "POST"},
                    ]
                }
            },
        )

        logger.info(f"エージェント間協力リクエスト送信: {request_id}")

    async def handle_intervention_with_coordination(self, intervention: UserIntervention) -> Any:
        """親エージェントによる介入処理（調整機能付き）"""
        logger.info(f"\n[親エージェント] 介入要求を受信: {intervention.message}")

        # ファイル関連の介入を自動的に調整
        if "auth.py" in intervention.message:
            # 複数のエージェントが同じファイルを編集する場合
            if "authenticate_user" in intervention.message:
                logger.info("[親エージェント] ファイルの上部セクションの編集を承認")
                return "承認"
            elif "check_permissions" in intervention.message:
                logger.info(
                    "[親エージェント] ファイルの下部セクションの編集を承認（上部の編集完了待ち）"
                )
                await asyncio.sleep(1)  # 待機をシミュレート
                return "承認"

        # データベース関連の介入
        if "database" in intervention.message.lower():
            logger.info("[親エージェント] データベースアクセスを調整")
            return "承認"

        # その他は通常の承認
        logger.info("[親エージェント] 通常の承認処理")
        return "承認"


async def main():
    """メイン関数"""
    demo = CoordinationDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
