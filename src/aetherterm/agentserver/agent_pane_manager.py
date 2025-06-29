"""
エージェントペーン管理

エージェント用のペーン（ターミナルセッション）を管理し、
エージェント間のメッセージルーティングを行います。
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from ..common.agent_protocol import (
    AgentMessage,
    MessageType,
    PaneConfig,
    PaneType,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentPane:
    """エージェントペーン"""

    pane_id: str = field(default_factory=lambda: f"pane_{uuid4().hex[:8]}")
    parent_session_id: str = ""
    agent_id: str = ""
    agent_type: str = ""
    pane_type: PaneType = PaneType.AGENT
    title: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    terminal_id: Optional[str] = None
    socket_id: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentPaneManager:
    """
    エージェントペーンマネージャー

    エージェント用のペーンを管理し、メッセージのルーティングを行います。
    AgentServerの拡張として動作します。
    """

    def __init__(self):
        self._panes: Dict[str, AgentPane] = {}
        self._agent_to_pane: Dict[str, str] = {}  # agent_id -> pane_id
        self._socket_to_pane: Dict[str, str] = {}  # socket_id -> pane_id
        self._message_router: Optional[MessageRouter] = None
        self._terminal_manager = None  # AgentServerのターミナルマネージャーへの参照

        # コールバック
        self._pane_created_callbacks: List[Callable[[AgentPane], None]] = []
        self._pane_destroyed_callbacks: List[Callable[[str], None]] = []

    def set_terminal_manager(self, terminal_manager: Any) -> None:
        """ターミナルマネージャーを設定"""
        self._terminal_manager = terminal_manager

    def set_message_router(self, router: "MessageRouter") -> None:
        """メッセージルーターを設定"""
        self._message_router = router

    async def create_agent_pane(
        self, parent_session_id: str, agent_type: str, config: PaneConfig
    ) -> AgentPane:
        """
        新しいエージェントペーンを作成

        Args:
            parent_session_id: 親セッションID
            agent_type: エージェントタイプ
            config: ペーン設定

        Returns:
            AgentPane: 作成されたペーン
        """
        # ペーンを作成
        pane = AgentPane(
            parent_session_id=parent_session_id,
            agent_type=agent_type,
            pane_type=config.pane_type,
            title=config.title or f"{agent_type} Agent",
            config=config.__dict__,
            metadata=config.metadata,
        )

        # エージェントIDを生成
        pane.agent_id = f"{agent_type}_{pane.pane_id}"

        # ターミナルセッションを作成（必要な場合）
        if self._terminal_manager and config.pane_type in [PaneType.AGENT, PaneType.TERMINAL]:
            try:
                terminal_config = {
                    "rows": config.size.get("rows", 24),
                    "cols": config.size.get("cols", 80),
                    "title": pane.title,
                    "agent_mode": True,
                    "agent_id": pane.agent_id,
                }

                # 新しいターミナルを作成
                terminal_id = await self._create_terminal_session(terminal_config)
                pane.terminal_id = terminal_id

            except Exception as e:
                logger.error(f"ターミナルセッションの作成に失敗しました: {e}")
                raise

        # ペーンを登録
        self._panes[pane.pane_id] = pane
        self._agent_to_pane[pane.agent_id] = pane.pane_id

        # コールバックを実行
        for callback in self._pane_created_callbacks:
            try:
                await self._execute_callback(callback, pane)
            except Exception as e:
                logger.error(f"ペーン作成コールバック実行中にエラー: {e}")

        logger.info(
            f"エージェントペーンを作成しました: {pane.pane_id} (エージェント: {pane.agent_id})"
        )

        # エージェントを起動（設定されている場合）
        if config.agent_config and config.agent_config.get("auto_start"):
            await self._start_agent(pane)

        return pane

    async def destroy_pane(self, pane_id: str) -> bool:
        """
        ペーンを破棄

        Args:
            pane_id: ペーンID

        Returns:
            bool: 破棄が成功した場合True
        """
        pane = self._panes.get(pane_id)
        if not pane:
            return False

        # エージェントを停止
        if pane.status == "active":
            await self._stop_agent(pane)

        # ターミナルセッションを破棄
        if pane.terminal_id and self._terminal_manager:
            try:
                await self._destroy_terminal_session(pane.terminal_id)
            except Exception as e:
                logger.error(f"ターミナルセッションの破棄に失敗しました: {e}")

        # 登録を解除
        del self._panes[pane_id]
        self._agent_to_pane.pop(pane.agent_id, None)
        if pane.socket_id:
            self._socket_to_pane.pop(pane.socket_id, None)

        # コールバックを実行
        for callback in self._pane_destroyed_callbacks:
            try:
                await self._execute_callback(callback, pane_id)
            except Exception as e:
                logger.error(f"ペーン破棄コールバック実行中にエラー: {e}")

        logger.info(f"エージェントペーンを破棄しました: {pane_id}")
        return True

    async def route_message(self, from_pane: str, to_pane: str, message: AgentMessage) -> bool:
        """
        ペーン間のメッセージをルーティング

        Args:
            from_pane: 送信元ペーンID
            to_pane: 送信先ペーンID
            message: メッセージ

        Returns:
            bool: ルーティングが成功した場合True
        """
        if self._message_router:
            return await self._message_router.route(from_pane, to_pane, message)

        logger.warning("メッセージルーターが設定されていません")
        return False

    async def broadcast_to_agents(
        self, message: AgentMessage, agent_types: Optional[List[str]] = None
    ) -> int:
        """
        エージェントにブロードキャスト

        Args:
            message: メッセージ
            agent_types: 対象エージェントタイプ（Noneの場合は全エージェント）

        Returns:
            int: 送信したエージェント数
        """
        count = 0

        for pane in self._panes.values():
            if pane.status != "active":
                continue

            if agent_types and pane.agent_type not in agent_types:
                continue

            if await self.route_message("system", pane.pane_id, message):
                count += 1

        return count

    def get_pane(self, pane_id: str) -> Optional[AgentPane]:
        """ペーンを取得"""
        return self._panes.get(pane_id)

    def get_pane_by_agent(self, agent_id: str) -> Optional[AgentPane]:
        """エージェントIDからペーンを取得"""
        pane_id = self._agent_to_pane.get(agent_id)
        return self._panes.get(pane_id) if pane_id else None

    def get_pane_by_socket(self, socket_id: str) -> Optional[AgentPane]:
        """ソケットIDからペーンを取得"""
        pane_id = self._socket_to_pane.get(socket_id)
        return self._panes.get(pane_id) if pane_id else None

    def list_panes(
        self,
        parent_session_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[AgentPane]:
        """
        ペーンの一覧を取得

        Args:
            parent_session_id: 親セッションIDでフィルタ
            agent_type: エージェントタイプでフィルタ
            status: ステータスでフィルタ

        Returns:
            List[AgentPane]: ペーンのリスト
        """
        panes = list(self._panes.values())

        if parent_session_id:
            panes = [p for p in panes if p.parent_session_id == parent_session_id]

        if agent_type:
            panes = [p for p in panes if p.agent_type == agent_type]

        if status:
            panes = [p for p in panes if p.status == status]

        return panes

    def update_socket_mapping(self, pane_id: str, socket_id: str) -> None:
        """ソケットIDマッピングを更新"""
        pane = self._panes.get(pane_id)
        if pane:
            # 古いマッピングを削除
            if pane.socket_id:
                self._socket_to_pane.pop(pane.socket_id, None)

            # 新しいマッピングを設定
            pane.socket_id = socket_id
            self._socket_to_pane[socket_id] = pane_id

    def register_pane_created_callback(self, callback: Callable[[AgentPane], None]) -> None:
        """ペーン作成コールバックを登録"""
        if callback not in self._pane_created_callbacks:
            self._pane_created_callbacks.append(callback)

    def unregister_pane_created_callback(self, callback: Callable[[AgentPane], None]) -> None:
        """ペーン作成コールバックを解除"""
        if callback in self._pane_created_callbacks:
            self._pane_created_callbacks.remove(callback)

    def register_pane_destroyed_callback(self, callback: Callable[[str], None]) -> None:
        """ペーン破棄コールバックを登録"""
        if callback not in self._pane_destroyed_callbacks:
            self._pane_destroyed_callbacks.append(callback)

    def unregister_pane_destroyed_callback(self, callback: Callable[[str], None]) -> None:
        """ペーン破棄コールバックを解除"""
        if callback in self._pane_destroyed_callbacks:
            self._pane_destroyed_callbacks.remove(callback)

    async def _create_terminal_session(self, config: Dict[str, Any]) -> str:
        """ターミナルセッションを作成（実装はAgentServerに依存）"""
        # ターミナルマネージャーのcreate_terminalメソッドを呼び出す
        # 実際の実装はAgentServerとの統合時に行う
        terminal_id = f"term_{uuid4().hex[:8]}"
        logger.info(f"ターミナルセッションを作成しました: {terminal_id}")
        return terminal_id

    async def _destroy_terminal_session(self, terminal_id: str) -> None:
        """ターミナルセッションを破棄（実装はAgentServerに依存）"""
        logger.info(f"ターミナルセッションを破棄しました: {terminal_id}")

    async def _start_agent(self, pane: AgentPane) -> None:
        """エージェントを起動"""
        logger.info(f"エージェントを起動します: {pane.agent_id}")

        # エージェント起動コマンドを送信
        if pane.terminal_id and self._terminal_manager:
            # エージェントタイプに応じたコマンドを実行
            if pane.agent_type == "openhands":
                command = "openhands-agent --pane-mode"
            else:
                command = f"{pane.agent_type}-agent"

            # ターミナルにコマンドを送信
            # 実際の実装はAgentServerとの統合時に行う
            logger.debug(f"エージェント起動コマンド: {command}")

    async def _stop_agent(self, pane: AgentPane) -> None:
        """エージェントを停止"""
        logger.info(f"エージェントを停止します: {pane.agent_id}")
        pane.status = "stopped"

    async def _execute_callback(self, callback: Callable, *args) -> None:
        """コールバックを実行（同期/非同期対応）"""
        if asyncio.iscoroutinefunction(callback):
            await callback(*args)
        else:
            callback(*args)


class MessageRouter:
    """
    メッセージルーター

    エージェント間のメッセージをルーティングします。
    """

    def __init__(self, pane_manager: AgentPaneManager):
        self.pane_manager = pane_manager
        self._routes: Dict[str, List[str]] = {}  # from_pane -> [to_panes]
        self._handlers: Dict[str, Callable[[AgentMessage], None]] = {}

    async def route(self, from_pane: str, to_pane: str, message: AgentMessage) -> bool:
        """
        メッセージをルーティング

        Args:
            from_pane: 送信元ペーンID
            to_pane: 送信先ペーンID
            message: メッセージ

        Returns:
            bool: ルーティングが成功した場合True
        """
        # 送信先ペーンを確認
        target_pane = self.pane_manager.get_pane(to_pane)
        if not target_pane:
            # エージェントIDで検索
            target_pane = self.pane_manager.get_pane_by_agent(to_pane)
            if not target_pane:
                logger.warning(f"送信先ペーンが見つかりません: {to_pane}")
                return False

        # メッセージを配信
        handler = self._handlers.get(target_pane.pane_id)
        if handler:
            try:
                await self._execute_handler(handler, message)
                return True
            except Exception as e:
                logger.error(f"メッセージハンドラー実行中にエラー: {e}")
                return False

        # デフォルトの配信方法（WebSocket経由など）
        # 実際の実装はAgentServerとの統合時に行う
        logger.debug(f"メッセージをルーティング: {from_pane} -> {to_pane}")
        return True

    def register_handler(self, pane_id: str, handler: Callable[[AgentMessage], None]) -> None:
        """メッセージハンドラーを登録"""
        self._handlers[pane_id] = handler

    def unregister_handler(self, pane_id: str) -> None:
        """メッセージハンドラーを解除"""
        self._handlers.pop(pane_id, None)

    async def _execute_handler(
        self, handler: Callable[[AgentMessage], None], message: AgentMessage
    ) -> None:
        """ハンドラーを実行（同期/非同期対応）"""
        if asyncio.iscoroutinefunction(handler):
            await handler(message)
        else:
            handler(message)
