"""
WebSocketクライアント

AgentServerとの双方向通信を管理
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

import socketio

from .protocol import AgentMessage, AgentRegistration, MessageType

logger = logging.getLogger(__name__)


class WebSocketClient:
    """AgentServer WebSocketクライアント"""
    
    def __init__(self, server_url: str = "http://localhost:57575"):
        self.server_url = server_url
        self.sio = socketio.AsyncClient()
        self.agent_id: Optional[str] = None
        self.is_connected = False
        self.message_handlers: Dict[MessageType, Callable] = {}
        self._setup_event_handlers()
        
    def _setup_event_handlers(self):
        """Socket.IOイベントハンドラを設定"""
        
        @self.sio.event
        async def connect():
            logger.info(f"AgentServerに接続しました: {self.server_url}")
            self.is_connected = True
            
        @self.sio.event
        async def disconnect():
            logger.info("AgentServerから切断されました")
            self.is_connected = False
            
        @self.sio.event
        async def agent_message(data):
            """他のエージェントからのメッセージ受信"""
            try:
                message = AgentMessage.from_dict(data)
                await self._handle_message(message)
            except Exception as e:
                logger.error(f"メッセージ処理エラー: {e}")
                
        @self.sio.event
        async def broadcast(data):
            """ブロードキャストメッセージ受信"""
            try:
                message = AgentMessage.from_dict(data)
                message.message_type = MessageType.BROADCAST
                await self._handle_message(message)
            except Exception as e:
                logger.error(f"ブロードキャスト処理エラー: {e}")
    
    async def connect(self) -> bool:
        """AgentServerに接続"""
        try:
            await self.sio.connect(self.server_url)
            return True
        except Exception as e:
            logger.error(f"接続エラー: {e}")
            return False
    
    async def disconnect(self):
        """AgentServerから切断"""
        if self.agent_id:
            await self.unregister_agent()
        await self.sio.disconnect()
    
    async def register_agent(self, registration: AgentRegistration) -> bool:
        """エージェントを登録"""
        try:
            self.agent_id = registration.agent_id
            
            message = AgentMessage(
                message_type=MessageType.AGENT_REGISTER,
                from_agent=self.agent_id,
                data=registration.to_dict()
            )
            
            await self.sio.emit("agent_register", message.to_dict())
            logger.info(f"エージェント登録: {self.agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"エージェント登録エラー: {e}")
            return False
    
    async def unregister_agent(self):
        """エージェント登録を解除"""
        if not self.agent_id:
            return
            
        try:
            message = AgentMessage(
                message_type=MessageType.AGENT_UNREGISTER,
                from_agent=self.agent_id
            )
            
            await self.sio.emit("agent_unregister", message.to_dict())
            logger.info(f"エージェント登録解除: {self.agent_id}")
            
        except Exception as e:
            logger.error(f"エージェント登録解除エラー: {e}")
    
    async def send_message(self, to_agent: str, message_type: MessageType, data: Dict[str, Any]) -> bool:
        """他のエージェントにメッセージ送信"""
        if not self.agent_id:
            logger.error("エージェントが登録されていません")
            return False
            
        try:
            message = AgentMessage(
                message_type=message_type,
                from_agent=self.agent_id,
                to_agent=to_agent,
                data=data
            )
            
            await self.sio.emit("agent_message", message.to_dict())
            logger.debug(f"メッセージ送信: {self.agent_id} -> {to_agent}")
            return True
            
        except Exception as e:
            logger.error(f"メッセージ送信エラー: {e}")
            return False
    
    async def broadcast_message(self, message_type: MessageType, data: Dict[str, Any]) -> bool:
        """全エージェントにブロードキャスト"""
        if not self.agent_id:
            logger.error("エージェントが登録されていません")
            return False
            
        try:
            message = AgentMessage(
                message_type=message_type,
                from_agent=self.agent_id,
                to_agent=None,  # ブロードキャスト
                data=data
            )
            
            await self.sio.emit("broadcast", message.to_dict())
            logger.debug(f"ブロードキャスト送信: {self.agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"ブロードキャスト送信エラー: {e}")
            return False
    
    async def send_heartbeat(self):
        """ハートビート送信"""
        if self.agent_id:
            await self.send_message(
                "agentserver",
                MessageType.AGENT_HEARTBEAT,
                {"timestamp": asyncio.get_event_loop().time()}
            )
    
    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """メッセージハンドラを登録"""
        self.message_handlers[message_type] = handler
    
    async def _handle_message(self, message: AgentMessage):
        """受信メッセージを処理"""
        handler = self.message_handlers.get(message.message_type)
        if handler:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"メッセージハンドラエラー: {e}")
        else:
            logger.warning(f"未処理メッセージタイプ: {message.message_type}")
    
    async def start_heartbeat(self, interval: float = 30.0):
        """定期ハートビートを開始"""
        while self.is_connected:
            await self.send_heartbeat()
            await asyncio.sleep(interval)