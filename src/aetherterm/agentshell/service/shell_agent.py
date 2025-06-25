"""
AetherTerm Shell Agent

ローカルセッション管理、AI連携調整、オプショナルサーバー連携を統合した
メインエージェントクラスです。
"""

import logging
import os
from typing import Any, Dict, List, Optional

from ..config import WrapperConfig
from ..domain.models import WrapperSession
from .ai_service import IndependentAIService
from .server_connector import ServerConnector
from .session_service import SessionService

logger = logging.getLogger(__name__)


class AetherTermShellAgent:
    """
    AetherTerm Shell Agent

    主要責任：
    1. ローカルセッション管理: PID追跡、状態管理
    2. AI連携調整: AIサービスとの連携
    3. オプショナルサーバー連携: サーバーがある場合のみ
    """

    def __init__(self, config: WrapperConfig):
        self.config = config
        self._is_running = False

        # サーバーコネクター（オプショナル）
        self.server_connector: Optional[ServerConnector] = None
        if config.aetherterm_sync.enable_sync:
            self.server_connector = ServerConnector(
                server_url=config.aetherterm_sync.server_url,
                auto_connect=True,
                retry_interval=config.aetherterm_sync.reconnection_delay,
                max_retries=config.aetherterm_sync.reconnection_attempts,
            )

        # AI サービス（必須、独立動作）
        self.ai_service = IndependentAIService(
            config=config.ai_service,
            provider_type=self._determine_ai_provider(),
            server_connector=self.server_connector,
        )

        # セッション管理サービス
        self.session_service = SessionService(
            config=config.session,
            aetherterm_server_url=config.aetherterm_sync.server_url,
            sync_callback=self._handle_sync_event,
        )

        # 内部状態
        self._current_session_id: Optional[str] = None

    async def start(self) -> None:
        """Shell Agentを開始"""
        if self._is_running:
            return

        logger.info("AetherTerm Shell Agentを開始します")

        try:
            # AI サービスを開始（独立動作）
            await self.ai_service.start()

            # セッション管理を開始
            await self.session_service.start()

            # サーバー連携を開始（オプショナル）
            if self.server_connector:
                server_connected = await self.server_connector.start()
                if server_connected:
                    logger.info("サーバー連携が有効になりました")
                else:
                    logger.info("サーバー連携は無効です（スタンドアロンモード）")

            self._is_running = True
            logger.info("AetherTerm Shell Agentが開始されました")

        except Exception as e:
            logger.error(f"Shell Agentの開始に失敗しました: {e}")
            raise

    async def stop(self) -> None:
        """Shell Agentを停止"""
        if not self._is_running:
            return

        logger.info("AetherTerm Shell Agentを停止します")

        try:
            # サーバー連携を停止
            if self.server_connector:
                await self.server_connector.stop()

            # セッション管理を停止
            await self.session_service.stop()

            # AI サービスを停止
            await self.ai_service.stop()

            self._is_running = False
            logger.info("AetherTerm Shell Agentが停止されました")

        except Exception as e:
            logger.error(f"Shell Agentの停止中にエラーが発生しました: {e}")

    def create_session(self, shell_pid: int, **kwargs) -> str:
        """
        新しいセッションを作成

        Args:
            shell_pid: シェルプロセスID
            **kwargs: 追加のセッション情報

        Returns:
            str: セッションID
        """
        session_id = self.session_service.create_session(shell_pid, **kwargs)
        self._current_session_id = session_id

        logger.info(f"新しいセッションを作成しました: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[WrapperSession]:
        """セッション情報を取得"""
        return self.session_service.get_session(session_id)

    def get_current_session(self) -> Optional[WrapperSession]:
        """現在のセッション情報を取得"""
        if self._current_session_id:
            return self.session_service.get_session(self._current_session_id)
        return None

    def get_session_by_pid(self, pid: int) -> Optional[WrapperSession]:
        """PIDからセッション情報を取得"""
        return self.session_service.get_session_by_pid(pid)

    def update_session(self, session_id: str, **kwargs) -> bool:
        """セッション情報を更新"""
        return self.session_service.update_session(session_id, **kwargs)

    def remove_session(self, session_id: str) -> bool:
        """セッションを削除"""
        result = self.session_service.remove_session(session_id)
        if session_id == self._current_session_id:
            self._current_session_id = None
        return result

    def list_sessions(self) -> List[WrapperSession]:
        """全セッションのリストを取得"""
        return self.session_service.list_sessions()

    def get_active_sessions(self) -> List[WrapperSession]:
        """アクティブなセッションのリストを取得"""
        return self.session_service.get_active_sessions()

    async def report_command_execution(
        self,
        session_id: str,
        command: str,
        output: str,
        exit_code: int,
        execution_time: float,
    ) -> None:
        """
        コマンド実行結果をAIサービスに報告

        Args:
            session_id: セッションID
            command: 実行されたコマンド
            output: コマンドの出力
            exit_code: 終了コード
            execution_time: 実行時間
        """
        try:
            await self.ai_service.report_command_execution(
                session_id=session_id,
                command=command,
                output=output,
                exit_code=exit_code,
                execution_time=execution_time,
            )

            # セッションのアクティビティを更新
            self.session_service.update_session(
                session_id,
                metadata={"last_command": command, "last_execution_time": execution_time},
            )

        except Exception as e:
            logger.error(f"コマンド実行報告中にエラーが発生しました: {e}")

    async def analyze_command_with_ai(
        self, command: str, output: str, exit_code: int, execution_time: float
    ) -> Dict[str, Any]:
        """AIを使用してコマンドを解析"""
        return await self.ai_service.analyze_command_with_ai(
            command=command,
            output=output,
            exit_code=exit_code,
            execution_time=execution_time,
        )

    async def suggest_error_fix(
        self, command: str, error_output: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """エラーの修正提案を取得"""
        return await self.ai_service.suggest_error_fix(
            command=command,
            error_output=error_output,
            context=context,
        )

    async def suggest_next_commands(self, current_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """次のコマンドを提案"""
        return await self.ai_service.suggest_next_commands(current_context=current_context)

    def get_command_history(self) -> List[str]:
        """コマンド履歴を取得"""
        return self.ai_service.get_command_history()

    def clear_command_history(self) -> None:
        """コマンド履歴をクリア"""
        self.ai_service.clear_command_history()

    def is_running(self) -> bool:
        """Shell Agentが実行中かどうかを確認"""
        return self._is_running

    def is_server_connected(self) -> bool:
        """サーバーに接続されているかどうかを確認"""
        return self.server_connector.is_connected() if self.server_connector else False

    def has_ai_provider(self) -> bool:
        """AIプロバイダーが利用可能かどうかを確認"""
        return self.ai_service.has_ai_provider()

    def get_operation_mode(self) -> str:
        """現在の動作モードを取得"""
        if self.is_server_connected():
            return "connected"
        if self.has_ai_provider():
            return "standalone_with_ai"
        return "standalone_local"

    def get_status(self) -> Dict[str, Any]:
        """Shell Agentの状態を取得"""
        return {
            "is_running": self._is_running,
            "operation_mode": self.get_operation_mode(),
            "current_session_id": self._current_session_id,
            "session_stats": self.session_service.get_session_stats(),
            "ai_service": self.ai_service.get_status(),
            "server_connector": self.server_connector.get_status()
            if self.server_connector
            else None,
            "config": {
                "ai_enabled": self.config.enable_ai,
                "server_sync_enabled": self.config.aetherterm_sync.enable_sync,
                "debug": self.config.debug,
            },
        }

    def enable_server_sync(self) -> None:
        """サーバー同期を有効化"""
        if self.server_connector:
            self.server_connector.enable()
        else:
            logger.warning("サーバーコネクターが初期化されていません")

    def disable_server_sync(self) -> None:
        """サーバー同期を無効化"""
        if self.server_connector:
            self.server_connector.disable()

    def _determine_ai_provider(self) -> str:
        """設定からAIプロバイダータイプを決定"""
        # 環境変数から取得
        provider = os.getenv("AETHERTERM_AI_PROVIDER", "").lower()
        if provider in ["openai", "anthropic", "local"]:
            return provider

        # エンドポイントから推測
        endpoint = self.config.ai_service.endpoint.lower()
        if "openai" in endpoint or "api.openai.com" in endpoint:
            return "openai"
        if "anthropic" in endpoint or "api.anthropic.com" in endpoint:
            return "anthropic"
        if "localhost" in endpoint or "127.0.0.1" in endpoint:
            return "local"

        # デフォルト
        return "openai"

    async def _handle_sync_event(self, event_type: str, data: Any = None) -> None:
        """サーバー同期イベントを処理"""
        try:
            if event_type == "connected":
                logger.info("サーバー同期が接続されました")
                # 既存セッションを同期
                if self.server_connector:
                    sessions = self.session_service.list_sessions()
                    await self.server_connector.sync_all_sessions(sessions)

            elif event_type == "disconnected":
                logger.warning("サーバー同期が切断されました")

            elif event_type == "server_command":
                logger.info(f"サーバーコマンドを受信しました: {data}")
                # サーバーからのコマンドを処理
                await self._handle_server_command(data)

        except Exception as e:
            logger.error(f"同期イベントの処理中にエラーが発生しました: {e}")

    async def _handle_server_command(self, command_data: Dict[str, Any]) -> None:
        """サーバーからのコマンドを処理"""
        command_type = command_data.get("type")

        if command_type == "get_status":
            # ステータス要求
            status = self.get_status()
            if self.server_connector:
                await self.server_connector.send_ai_notification(
                    session_id=self._current_session_id or "system",
                    notification_type="status_response",
                    data=status,
                )

        elif command_type == "clear_history":
            # 履歴クリア要求
            self.clear_command_history()
            logger.info("コマンド履歴をクリアしました")

        elif command_type == "analyze_command":
            # コマンド解析要求
            cmd_data = command_data.get("data", {})
            if all(key in cmd_data for key in ["command", "output", "exit_code"]):
                analysis = await self.analyze_command_with_ai(
                    command=cmd_data["command"],
                    output=cmd_data["output"],
                    exit_code=cmd_data["exit_code"],
                    execution_time=cmd_data.get("execution_time", 0.0),
                )

                if self.server_connector:
                    await self.server_connector.send_ai_notification(
                        session_id=self._current_session_id or "system",
                        notification_type="analysis_response",
                        data=analysis,
                    )

        else:
            logger.warning(f"未知のサーバーコマンド: {command_type}")
