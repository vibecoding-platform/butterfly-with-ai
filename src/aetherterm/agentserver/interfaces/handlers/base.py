"""
Base Socket Handler

Socket.IOハンドラの基底クラスとユーティリティ
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from dependency_injector.wiring import Provide, inject

from aetherterm.core.container import DIContainer
from aetherterm.logprocessing.log_processing_manager import LogProcessingManager

log = logging.getLogger("aetherterm.handlers.base")


class BaseSocketHandler(ABC):
    """Socket.IOハンドラの基底クラス"""

    def __init__(self, sio, log_manager: LogProcessingManager = None):
        self.sio = sio
        self.log_manager = log_manager or DIContainer.get_log_processing_manager()

    @abstractmethod
    async def handle_event(self, sid: str, data: Dict[str, Any]) -> Any:
        """イベントを処理"""

    def get_user_info_from_environ(self, environ: Dict[str, Any]) -> Dict[str, Any]:
        """環境変数からユーザー情報を抽出"""
        return {
            "remote_addr": environ.get("REMOTE_ADDR"),
            "remote_user": environ.get("HTTP_X_REMOTE_USER"),
            "forwarded_for": environ.get("HTTP_X_FORWARDED_FOR"),
            "user_agent": environ.get("HTTP_USER_AGENT"),
            "accept_language": environ.get("HTTP_ACCEPT_LANGUAGE"),
            "host": environ.get("HTTP_HOST"),
        }

    async def emit_to_client(self, sid: str, event: str, data: Any):
        """クライアントにイベントを送信"""
        try:
            await self.sio.emit(event, data, room=sid)
        except Exception as e:
            log.error(f"Failed to emit {event} to {sid}: {e}")

    async def emit_to_room(self, room: str, event: str, data: Any):
        """ルームにイベントを送信"""
        try:
            await self.sio.emit(event, data, room=room)
        except Exception as e:
            log.error(f"Failed to emit {event} to room {room}: {e}")


@inject
def create_handler_registry(
    log_manager: LogProcessingManager = Provide[DIContainer.get_container().log_processing_manager],
) -> Dict[str, BaseSocketHandler]:
    """ハンドラレジストリを作成"""
    return {
        # ハンドラを追加していく
    }
