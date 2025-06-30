"""
AgentShell WebSocketクライアント メインエントリーポイント

複数エージェント（OpenHands、ClaudeCode）の協調作業を支援
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional

import click

from .startup.bootstrap import BootstrapManager
from .coordination.interactive_coordinator import InteractiveCoordinator
from .websocket.client import WebSocketClient
from .websocket.protocol import MessageType
from .agents.manager import AgentManager
from .terminal_spawner import TerminalSpawner
from .terminal_manager import TerminalManager

logger = logging.getLogger(__name__)


class AgentShellOrchestrator:
    """エージェント協調オーケストレーター"""
    
    def __init__(self, server_url: str = "http://localhost:57575"):
        self.server_url = server_url
        self.bootstrap_manager = BootstrapManager()
        self.websocket_client: Optional[WebSocketClient] = None
        self.agent_manager = AgentManager()
        self.agents: Dict[str, Any] = {}
        self.interactive_coordinator: Optional[InteractiveCoordinator] = None
        self.terminal_spawner: Optional[TerminalSpawner] = None
        self.terminal_manager: Optional[TerminalManager] = None
        self.running = False
        
    async def start(
        self, 
        agent_specs: List[str], 
        config_path: Optional[str] = None,
        debug: bool = False,
        interactive: bool = False
    ) -> bool:
        """エージェント協調システムを開始"""
        logger.info("AgentShell協調システムを開始します")
        
        try:
            # ブートストラップ実行
            success, error_msg = await self.bootstrap_manager.bootstrap(
                server_url=self.server_url,
                agent_specs=agent_specs,
                config_path=config_path,
                debug=debug
            )
            
            if not success:
                logger.error(f"ブートストラップ失敗: {error_msg}")
                return False
            
            # ブートストラップで作成されたリソースを取得
            self.websocket_client = self.bootstrap_manager.websocket_client
            self.agents = self.bootstrap_manager.registration_flow.registered_agents
            
            # ターミナル生成機能を初期化
            self.terminal_spawner = TerminalSpawner(self.websocket_client)
            self.terminal_manager = TerminalManager(self.websocket_client)
            
            # インタラクティブモードの設定
            if interactive:
                self.interactive_coordinator = InteractiveCoordinator(
                    self.websocket_client, 
                    "shell_coordinator"
                )
                # インタラクティブ入力タスクを開始
                interactive_task = asyncio.create_task(
                    self._handle_interactive_input()
                )
            else:
                interactive_task = None
            
            # メッセージハンドラを設定
            self._setup_message_handlers()
            
            self.running = True
            logger.info("AgentShell協調システムが開始されました")
            
            # メインループ
            try:
                await self._main_loop()
            finally:
                if interactive_task:
                    interactive_task.cancel()
                await self._shutdown()
                
            return True
                
        except Exception as e:
            logger.error(f"システム開始エラー: {e}")
            return False
    
    async def _handle_interactive_input(self):
        """インタラクティブ入力を処理"""
        try:
            print("\n=== AgentShell インタラクティブモード ===")
            print("コマンド例:")
            print("  list                    - エージェント一覧表示")
            print("  status                  - システム状態表示")  
            print("  terminals               - 生成済みターミナル一覧表示")
            print("  managed                 - 管理下のターミナル一覧表示")
            print("  spawn <agent_type> <agent_id> - 新しいターミナルを生成")
            print("  assign <terminal_id> <agent_type> <agent_id> - ターミナルにエージェントを割り当て")
            print("  kill <spawn_id>         - 生成されたターミナルを終了")
            print("  terminate <terminal_id> - 管理下のターミナルを終了")
            print("  @<agent_id> <message>   - 特定のエージェントにメッセージ送信")
            print("  @all <message>          - 全エージェントにブロードキャスト")
            print("  quit/exit               - 終了")
            print("========================================")
            
            while self.running:
                try:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, input, "\n> "
                    )
                    
                    if not user_input.strip():
                        continue
                    
                    command = user_input.strip().lower()
                    
                    if command in ["quit", "exit", "q"]:
                        logger.info("ユーザーからの終了指示")
                        self.running = False
                        break
                    elif command == "list":
                        await self._show_agent_list()
                    elif command == "status":
                        await self._show_system_status()
                    elif command == "terminals":
                        await self._show_spawned_terminals()
                    elif command == "managed":
                        await self._show_managed_terminals()
                    elif user_input.startswith("spawn "):
                        await self._handle_spawn_command(user_input)
                    elif user_input.startswith("assign "):
                        await self._handle_assign_command(user_input)
                    elif user_input.startswith("kill "):
                        await self._handle_kill_command(user_input)
                    elif user_input.startswith("terminate "):
                        await self._handle_terminate_command(user_input)
                    elif user_input.startswith("@"):
                        await self._handle_agent_message(user_input)
                    else:
                        print(f"未知のコマンド: {command}")
                        
                except EOFError:
                    logger.info("EOF detected, shutting down")
                    self.running = False
                    break
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt, shutting down")
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"インタラクティブ入力エラー: {e}")
                    
        except Exception as e:
            logger.error(f"インタラクティブモードエラー: {e}")
    
    async def _show_agent_list(self):
        """エージェント一覧を表示"""
        if not self.agents:
            print("登録されているエージェントはありません")
            return
        
        print("\n=== 登録エージェント ===")
        for agent_id, agent in self.agents.items():
            status = agent.get_status().value
            capabilities = [cap.value for cap in agent.get_capabilities()]
            print(f"- {agent_id}: {status}")
            print(f"  機能: {', '.join(capabilities)}")
        print("=======================")
    
    async def _show_system_status(self):
        """システム状態を表示"""
        startup_status = self.bootstrap_manager.get_startup_status()
        print(f"\n=== システム状態 ===")
        print(f"起動フェーズ: {startup_status['phase']}")
        print(f"進捗: {startup_status['progress']:.1%}")
        print(f"メッセージ: {startup_status.get('message', 'N/A')}")
        print(f"エージェント数: {startup_status.get('agent_count', 0)}")
        print(f"AgentServer接続: {'Yes' if startup_status.get('is_connected', False) else 'No'}")
        print("==================")
    
    async def _handle_agent_message(self, message: str):
        """エージェント宛メッセージを処理"""
        if not self.interactive_coordinator:
            print("インタラクティブコーディネーターが初期化されていません")
            return
        
        try:
            # @target_agent message 形式を解析
            parts = message[1:].split(" ", 1)
            if len(parts) < 2:
                print("使用方法: @<agent_id> <message>")
                return
            
            target_agent, user_message = parts
            
            if target_agent == "all":
                # 全エージェントにブロードキャスト
                await self.interactive_coordinator.broadcast_message({
                    "type": "user_message",
                    "message": user_message,
                    "from": "interactive_user"
                })
                print(f"全エージェントにメッセージを送信しました: {user_message}")
            else:
                # 特定エージェントにメッセージ送信
                if target_agent not in self.agents:
                    print(f"エージェントが見つかりません: {target_agent}")
                    return
                
                response = await self.interactive_coordinator.request_agent_action(
                    target_agent=target_agent,
                    request_type="user_message",
                    data={"message": user_message},
                    timeout=30.0
                )
                
                if response:
                    print(f"{target_agent}からの応答: {response}")
                else:
                    print(f"{target_agent}からの応答がありませんでした（タイムアウト）")
                    
        except Exception as e:
            logger.error(f"エージェントメッセージ処理エラー: {e}")
            print(f"メッセージ送信エラー: {e}")

    async def _show_spawned_terminals(self):
        """生成済みターミナル一覧を表示"""
        if not self.terminal_spawner:
            print("ターミナル生成機能が初期化されていません")
            return

        terminals = self.terminal_spawner.get_spawned_terminals()
        
        if not terminals:
            print("生成されたターミナルはありません")
            return

        print("\n=== 生成済みターミナル ===")
        for spawn_id, config in terminals.items():
            agent_type = config.get("agent_type", "unknown")
            agent_id = config.get("agent_id", "unknown")
            working_dir = config.get("working_directory", "N/A")
            print(f"- {spawn_id}: {agent_type}:{agent_id}")
            print(f"  作業ディレクトリ: {working_dir}")
        print("=========================")

    async def _handle_spawn_command(self, command: str):
        """spawn コマンドを処理"""
        if not self.terminal_spawner:
            print("ターミナル生成機能が初期化されていません")
            return

        try:
            # spawn <agent_type> <agent_id> [working_directory] 形式を解析
            parts = command.strip().split()
            if len(parts) < 3:
                print("使用方法: spawn <agent_type> <agent_id> [working_directory]")
                print("例: spawn claude_code claude_frontend /path/to/project")
                return

            agent_type = parts[1]
            agent_id = parts[2]
            working_directory = parts[3] if len(parts) > 3 else None

            print(f"新しいターミナルを生成中: {agent_type}:{agent_id}...")

            spawn_id = await self.terminal_spawner.spawn_agent_terminal(
                agent_type=agent_type,
                agent_id=agent_id,
                working_directory=working_directory,
            )

            print(f"ターミナルが生成されました: {spawn_id}")

        except Exception as e:
            logger.error(f"ターミナル生成エラー: {e}")
            print(f"ターミナル生成に失敗しました: {e}")

    async def _handle_kill_command(self, command: str):
        """kill コマンドを処理"""
        if not self.terminal_spawner:
            print("ターミナル生成機能が初期化されていません")
            return

        try:
            # kill <spawn_id> 形式を解析
            parts = command.strip().split()
            if len(parts) < 2:
                print("使用方法: kill <spawn_id>")
                return

            spawn_id = parts[1]
            print(f"ターミナルを終了中: {spawn_id}...")

            success = await self.terminal_spawner.terminate_spawned_terminal(spawn_id)

            if success:
                print(f"ターミナルが終了されました: {spawn_id}")
            else:
                print(f"ターミナルの終了に失敗しました: {spawn_id}")

        except Exception as e:
            logger.error(f"ターミナル終了エラー: {e}")
            print(f"ターミナル終了に失敗しました: {e}")

    async def _show_managed_terminals(self):
        """管理下のターミナル一覧を表示"""
        if not self.terminal_manager:
            print("ターミナル管理機能が初期化されていません")
            return

        terminals = self.terminal_manager.get_all_terminals()
        
        if not terminals:
            print("管理下のターミナルはありません")
            return

        print("\n=== 管理下のターミナル ===")
        for terminal_id, status in terminals.items():
            agent_info = "未割り当て"
            if status.agent_assignment:
                agent_info = f"{status.agent_assignment.agent_type}:{status.agent_assignment.agent_id}"
            
            print(f"- {terminal_id}: {status.status}")
            print(f"  エージェント: {agent_info}")
            print(f"  最終アクティビティ: {status.last_activity}")
            if status.process_id:
                print(f"  プロセスID: {status.process_id}")
            if status.error_message:
                print(f"  エラー: {status.error_message}")
        print("========================")

    async def _handle_assign_command(self, command: str):
        """assign コマンドを処理"""
        if not self.terminal_manager:
            print("ターミナル管理機能が初期化されていません")
            return

        try:
            # assign <terminal_id> <agent_type> <agent_id> [working_directory] 形式を解析
            parts = command.strip().split()
            if len(parts) < 4:
                print("使用方法: assign <terminal_id> <agent_type> <agent_id> [working_directory]")
                print("例: assign term_001 claude_code claude_frontend /path/to/project")
                return

            terminal_id = parts[1]
            agent_type = parts[2]
            agent_id = parts[3]
            working_directory = parts[4] if len(parts) > 4 else None

            print(f"エージェントを割り当て中: {terminal_id} → {agent_type}:{agent_id}...")

            assignment_id = await self.terminal_manager.assign_agent_to_terminal(
                terminal_id=terminal_id,
                agent_type=agent_type,
                agent_id=agent_id,
                working_directory=working_directory,
            )

            print(f"エージェントが割り当てられました: {assignment_id}")

        except Exception as e:
            logger.error(f"エージェント割り当てエラー: {e}")
            print(f"エージェント割り当てに失敗しました: {e}")

    async def _handle_terminate_command(self, command: str):
        """terminate コマンドを処理"""
        if not self.terminal_manager:
            print("ターミナル管理機能が初期化されていません")
            return

        try:
            # terminate <terminal_id> [force] 形式を解析
            parts = command.strip().split()
            if len(parts) < 2:
                print("使用方法: terminate <terminal_id> [force]")
                return

            terminal_id = parts[1]
            force = len(parts) > 2 and parts[2].lower() == "force"

            print(f"ターミナルを終了中: {terminal_id} (force: {force})...")

            await self.terminal_manager.terminate_terminal(terminal_id, force)

            print(f"ターミナル終了要求を送信しました: {terminal_id}")

        except Exception as e:
            logger.error(f"ターミナル終了エラー: {e}")
            print(f"ターミナル終了に失敗しました: {e}")
    
    def _setup_message_handlers(self):
        """WebSocketメッセージハンドラを設定"""
        
        async def handle_task_assignment(message):
            """タスク割り当てメッセージを処理"""
            data = message.data
            agent_id = data.get("target_agent")
            
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                try:
                    result = await agent.execute_task(data)
                    logger.info(f"タスク完了: {agent_id} -> {result.get('summary', 'No summary')}")
                except Exception as e:
                    logger.error(f"タスク実行エラー {agent_id}: {e}")
            else:
                logger.warning(f"未知のエージェント: {agent_id}")
        
        async def handle_coordination_request(message):
            """協調要求メッセージを処理"""
            data = message.data
            request_type = data.get("request_type")
            
            if request_type == "status_report":
                # 全エージェントのステータスを報告
                status_report = {}
                for agent_id, agent in self.agents.items():
                    status_report[agent_id] = {
                        "status": agent.get_status().value,
                        "capabilities": [cap.value for cap in agent.get_capabilities()]
                    }
                
                await self.websocket_client.send_message(
                    message.from_agent,
                    MessageType.AGENT_MESSAGE,
                    {"status_report": status_report}
                )
        
        async def handle_broadcast(message):
            """ブロードキャストメッセージを処理"""
            data = message.data
            broadcast_type = data.get("type")
            
            if broadcast_type == "workspace_sync":
                logger.info("ワークスペース同期要求を受信")
                # 同一ファイルシステム上なので特別な処理は不要
            elif broadcast_type == "project_complete":
                logger.info("プロジェクト完了通知を受信")
        
        # ハンドラを登録
        self.websocket_client.register_message_handler(
            MessageType.TASK_ASSIGNMENT, handle_task_assignment
        )
        self.websocket_client.register_message_handler(
            MessageType.COORDINATION_REQUEST, handle_coordination_request
        )
        self.websocket_client.register_message_handler(
            MessageType.BROADCAST, handle_broadcast
        )
    
    async def _main_loop(self):
        """メインループ"""
        while self.running:
            try:
                # 各エージェントの状態をチェック
                for agent_id, agent in self.agents.items():
                    if agent.get_status().value == "error":
                        logger.warning(f"エージェントエラー状態: {agent_id}")
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"メインループエラー: {e}")
                break
    
    async def _shutdown(self):
        """システムをシャットダウン"""
        logger.info("AgentShell協調システムをシャットダウン中...")
        
        self.running = False
        
        # 生成されたターミナルをクリーンアップ
        if self.terminal_spawner:
            try:
                await self.terminal_spawner.cleanup_all_spawned_terminals()
                logger.info("ターミナルスポーナーをクリーンアップしました")
            except Exception as e:
                logger.error(f"ターミナルスポーナークリーンアップエラー: {e}")
        
        # 各エージェントをシャットダウン
        for agent_id, agent in self.agents.items():
            try:
                await agent.shutdown()
                logger.info(f"エージェントシャットダウン: {agent_id}")
            except Exception as e:
                logger.error(f"エージェントシャットダウンエラー {agent_id}: {e}")
        
        # AgentManagerを停止
        await self.agent_manager.stop()
        
        # WebSocket接続を閉じる
        if self.websocket_client:
            await self.websocket_client.disconnect()
        
        logger.info("AgentShell協調システムのシャットダウンが完了しました")


@click.command()
@click.option("--server", "-s", default="http://localhost:57575", help="AgentServer URL")
@click.option("--agents", "-a", multiple=True, help="エージェント設定 (type:id)")
@click.option("--config", "-c", help="設定ファイルパス")
@click.option("--debug", "-d", is_flag=True, help="デバッグモードを有効にする")
@click.option("--interactive", "-i", is_flag=True, help="インタラクティブモードを有効にする")
def main(server: str, agents: tuple, config: str, debug: bool, interactive: bool):
    """AgentShell WebSocketクライアントを開始"""
    
    # ログ設定
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # エージェント仕様を解析
    agent_specs = list(agents) if agents else []
    
    # エージェント仕様の妥当性チェック
    for agent_spec in agent_specs:
        if ":" not in agent_spec:
            logger.error(f"無効なエージェント指定: {agent_spec} (形式: type:id)")
            sys.exit(1)
    
    if not agent_specs:
        # デフォルト設定
        agent_specs = ["claude_code:claude_001"]
        logger.info("デフォルトエージェント設定を使用: claude_code:claude_001")
    
    # オーケストレーターを作成・開始
    orchestrator = AgentShellOrchestrator(server)
    
    # シグナルハンドラを設定
    def signal_handler(signum, frame):
        logger.info(f"シグナル {signum} を受信しました")
        orchestrator.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        success = asyncio.run(orchestrator.start(
            agent_specs=agent_specs,
            config_path=config,
            debug=debug,
            interactive=interactive
        ))
        
        if not success:
            logger.error("AgentShell起動に失敗しました")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("ユーザーによる中断")
    except Exception as e:
        logger.error(f"実行エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()