"""
エージェント登録フロー

AgentServerへのエージェント登録プロセスを管理
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from ..websocket.client import WebSocketClient
from ..agents.base import AgentStatus
from ..agents.claude_code import ClaudeCodeAgent
# from ..agents.openhands import OpenHandsAgent  # Import when needed

logger = logging.getLogger(__name__)


class RegistrationFlow:
    """エージェント登録フロー管理"""
    
    def __init__(self):
        self.registered_agents: Dict[str, Any] = {}
        self.registration_timeout = 30.0
        
    async def register_all_agents(
        self,
        websocket_client: WebSocketClient,
        agent_configs: List[Dict[str, str]]
    ) -> Tuple[bool, str]:
        """すべてのエージェントを登録"""
        try:
            registration_tasks = []
            
            for config in agent_configs:
                task = asyncio.create_task(
                    self._register_single_agent(websocket_client, config)
                )
                registration_tasks.append(task)
            
            # 並行登録の実行
            results = await asyncio.gather(*registration_tasks, return_exceptions=True)
            
            # 結果を検証
            failed_registrations = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    agent_spec = agent_configs[i]['spec']
                    failed_registrations.append(f"{agent_spec}: {result}")
                elif not result[0]:  # success flag
                    agent_spec = agent_configs[i]['spec']
                    failed_registrations.append(f"{agent_spec}: {result[1]}")
            
            if failed_registrations:
                error_msg = "エージェント登録に失敗: " + ", ".join(failed_registrations)
                return False, error_msg
            
            logger.info(f"{len(agent_configs)}個のエージェントを正常に登録しました")
            return True, ""
            
        except Exception as e:
            logger.error(f"エージェント登録プロセスでエラー: {e}")
            return False, str(e)
    
    async def _register_single_agent(
        self,
        websocket_client: WebSocketClient,
        config: Dict[str, str]
    ) -> Tuple[bool, str]:
        """単一エージェントを登録"""
        agent_type = config['agent_type']
        agent_id = config['agent_id']
        
        try:
            # エージェントインスタンスを作成
            agent = await self._create_agent_instance(agent_type, agent_id)
            if not agent:
                return False, f"エージェントタイプ {agent_type} の作成に失敗"
            
            # エージェントを初期化
            init_success = await agent.initialize()
            if not init_success:
                return False, f"エージェント {agent_id} の初期化に失敗"
            
            # WebSocketクライアントを設定
            agent.set_websocket_client(websocket_client)
            
            # AgentServerに登録
            registration_data = {
                'agent_id': agent_id,
                'agent_type': agent_type,
                'capabilities': [cap.value for cap in agent.get_capabilities()],
                'status': agent.get_status().value,
                'metadata': {
                    'version': '1.0.0',
                    'description': f'{agent_type} agent instance'
                }
            }
            
            success = await websocket_client.register_agent(
                agent_id,
                agent_type,
                registration_data
            )
            
            if success:
                self.registered_agents[agent_id] = agent
                logger.info(f"エージェント {agent_id} ({agent_type}) を登録しました")
                return True, ""
            else:
                return False, f"AgentServerへの登録に失敗: {agent_id}"
                
        except Exception as e:
            logger.error(f"エージェント {agent_id} の登録でエラー: {e}")
            return False, str(e)
    
    async def _create_agent_instance(self, agent_type: str, agent_id: str) -> Optional[Any]:
        """エージェントインスタンスを作成"""
        try:
            if agent_type == "claude_code":
                return ClaudeCodeAgent(agent_id)
            elif agent_type == "openhands":
                # Dynamic import to avoid circular dependencies
                from ..agents.openhands import OpenHandsAgent
                return OpenHandsAgent(agent_id)
            else:
                logger.error(f"未知のエージェントタイプ: {agent_type}")
                return None
                
        except Exception as e:
            logger.error(f"エージェントインスタンス作成エラー: {e}")
            return None
    
    async def unregister_agent(self, websocket_client: WebSocketClient, agent_id: str) -> bool:
        """エージェントの登録を解除"""
        try:
            if agent_id not in self.registered_agents:
                logger.warning(f"未登録のエージェントです: {agent_id}")
                return False
            
            agent = self.registered_agents[agent_id]
            
            # エージェントをシャットダウン
            await agent.shutdown()
            
            # AgentServerから登録解除
            success = await websocket_client.unregister_agent(agent_id)
            
            if success:
                del self.registered_agents[agent_id]
                logger.info(f"エージェント {agent_id} の登録を解除しました")
                return True
            else:
                logger.error(f"AgentServerからの登録解除に失敗: {agent_id}")
                return False
                
        except Exception as e:
            logger.error(f"エージェント登録解除エラー: {e}")
            return False
    
    async def unregister_all_agents(self, websocket_client: WebSocketClient) -> bool:
        """すべてのエージェントの登録を解除"""
        try:
            unregister_tasks = []
            
            for agent_id in list(self.registered_agents.keys()):
                task = asyncio.create_task(
                    self.unregister_agent(websocket_client, agent_id)
                )
                unregister_tasks.append(task)
            
            if unregister_tasks:
                results = await asyncio.gather(*unregister_tasks, return_exceptions=True)
                
                failed_count = sum(1 for result in results if not result or isinstance(result, Exception))
                if failed_count > 0:
                    logger.warning(f"{failed_count}個のエージェントの登録解除に失敗しました")
                    return False
            
            logger.info("すべてのエージェントの登録を解除しました")
            return True
            
        except Exception as e:
            logger.error(f"全エージェント登録解除エラー: {e}")
            return False
    
    def get_registered_agents(self) -> Dict[str, Dict[str, Any]]:
        """登録済みエージェントの情報を取得"""
        result = {}
        
        for agent_id, agent in self.registered_agents.items():
            result[agent_id] = {
                'agent_type': getattr(agent, 'agent_type', 'unknown'),
                'status': agent.get_status().value,
                'capabilities': [cap.value for cap in agent.get_capabilities()],
                'current_task': getattr(agent, 'current_task', None)
            }
        
        return result
    
    async def health_check_agents(self) -> Dict[str, bool]:
        """登録済みエージェントのヘルスチェック"""
        health_status = {}
        
        for agent_id, agent in self.registered_agents.items():
            try:
                # エージェントの状態を確認
                status = agent.get_status()
                health_status[agent_id] = status != AgentStatus.ERROR and status != AgentStatus.OFFLINE
                
            except Exception as e:
                logger.error(f"エージェント {agent_id} のヘルスチェックエラー: {e}")
                health_status[agent_id] = False
        
        return health_status
    
    async def restart_failed_agents(self, websocket_client: WebSocketClient) -> Tuple[int, int]:
        """失敗したエージェントを再起動"""
        health_status = await self.health_check_agents()
        failed_agents = [agent_id for agent_id, healthy in health_status.items() if not healthy]
        
        if not failed_agents:
            logger.info("再起動が必要なエージェントはありません")
            return 0, 0
        
        logger.info(f"{len(failed_agents)}個のエージェントを再起動します")
        
        restart_tasks = []
        for agent_id in failed_agents:
            task = asyncio.create_task(
                self._restart_single_agent(websocket_client, agent_id)
            )
            restart_tasks.append(task)
        
        results = await asyncio.gather(*restart_tasks, return_exceptions=True)
        
        success_count = sum(1 for result in results if result and not isinstance(result, Exception))
        failed_count = len(failed_agents) - success_count
        
        logger.info(f"エージェント再起動完了: 成功={success_count}, 失敗={failed_count}")
        return success_count, failed_count
    
    async def _restart_single_agent(self, websocket_client: WebSocketClient, agent_id: str) -> bool:
        """単一エージェントを再起動"""
        try:
            if agent_id not in self.registered_agents:
                logger.error(f"再起動対象のエージェントが見つかりません: {agent_id}")
                return False
            
            agent = self.registered_agents[agent_id]
            
            # エージェントをシャットダウン
            await agent.shutdown()
            
            # 再初期化
            init_success = await agent.initialize()
            if not init_success:
                logger.error(f"エージェント {agent_id} の再初期化に失敗")
                return False
            
            # WebSocketクライアントを再設定
            agent.set_websocket_client(websocket_client)
            
            # AgentServerに再登録
            registration_data = {
                'agent_id': agent_id,
                'agent_type': getattr(agent, 'agent_type', 'unknown'),
                'capabilities': [cap.value for cap in agent.get_capabilities()],
                'status': agent.get_status().value,
                'metadata': {
                    'version': '1.0.0',
                    'description': f'Restarted agent instance'
                }
            }
            
            success = await websocket_client.register_agent(
                agent_id,
                getattr(agent, 'agent_type', 'unknown'),
                registration_data
            )
            
            if success:
                logger.info(f"エージェント {agent_id} を再起動しました")
                return True
            else:
                logger.error(f"エージェント {agent_id} の再登録に失敗")
                return False
                
        except Exception as e:
            logger.error(f"エージェント {agent_id} の再起動エラー: {e}")
            return False
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """エージェント統計情報を取得"""
        stats = {
            'total_agents': len(self.registered_agents),
            'agent_types': {},
            'status_distribution': {},
            'agents_by_status': {}
        }
        
        for agent_id, agent in self.registered_agents.items():
            # エージェントタイプ別統計
            agent_type = getattr(agent, 'agent_type', 'unknown')
            stats['agent_types'][agent_type] = stats['agent_types'].get(agent_type, 0) + 1
            
            # ステータス別統計
            status = agent.get_status().value
            stats['status_distribution'][status] = stats['status_distribution'].get(status, 0) + 1
            
            # ステータス別エージェント一覧
            if status not in stats['agents_by_status']:
                stats['agents_by_status'][status] = []
            stats['agents_by_status'][status].append(agent_id)
        
        return stats