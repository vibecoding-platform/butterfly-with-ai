"""
ControlServer接続クライアント - AgentServer側

ControlServerとWebSocket接続を確立し、短期記憶データを送信
"""

import asyncio
import json
import logging
import websockets
from typing import Optional
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


class ControlServerClient:
    """ControlServer接続クライアント"""
    
    def __init__(self, control_server_url: str = "ws://localhost:8765/agent", agent_id: str = None):
        self.control_server_url = control_server_url
        self.agent_id = agent_id or f"agentserver_{str(uuid4())[:8]}"
        
        # 接続管理
        self.websocket = None
        self.connected = False
        self.connection_task = None
        self.heartbeat_task = None
        
        # 設定
        self.reconnect_interval = 5  # 5秒間隔で再接続試行
        self.heartbeat_interval = 30  # 30秒間隔でハートビート
        
    async def start(self):
        """ControlServer接続開始"""
        logger.info(f"Starting ControlServer client for agent {self.agent_id}")
        
        # 接続タスクを開始
        self.connection_task = asyncio.create_task(self._connection_loop())
        
    async def stop(self):
        """ControlServer接続停止"""
        logger.info(f"Stopping ControlServer client for agent {self.agent_id}")
        
        self.connected = False
        
        if self.connection_task:
            self.connection_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            
        if self.websocket:
            await self.websocket.close()
            
        try:
            await asyncio.gather(self.connection_task, self.heartbeat_task, return_exceptions=True)
        except Exception:
            pass
    
    async def _connection_loop(self):
        """接続維持ループ"""
        while True:
            try:
                await self._connect_to_control_server()
                
                # 接続が切れるまで待機
                while self.connected:
                    await asyncio.sleep(1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"ControlServer connection error: {e}")
                
            # 再接続前に待機
            if not self.connected:
                logger.info(f"Reconnecting to ControlServer in {self.reconnect_interval} seconds...")
                await asyncio.sleep(self.reconnect_interval)
    
    async def _connect_to_control_server(self):
        """ControlServerに接続"""
        try:
            logger.info(f"Connecting to ControlServer at {self.control_server_url}")
            
            self.websocket = await websockets.connect(self.control_server_url)
            self.connected = True
            
            logger.info("Connected to ControlServer")
            
            # AgentServerとして登録
            await self._register_agent()
            
            # ターミナルクラスに接続を設定
            from aetherterm.agentserver.terminals.asyncio_terminal import AsyncioTerminal
            AsyncioTerminal.set_control_server_connection(self.websocket)
            
            # ハートビートタスクを開始
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # メッセージ受信ループ
            await self._receive_loop()
            
        except Exception as e:
            logger.error(f"Failed to connect to ControlServer: {e}")
            self.connected = False
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
    
    async def _register_agent(self):
        """AgentServerとして登録"""
        registration_message = {
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": "agentserver",
            "capabilities": [
                "terminal_management",
                "short_term_memory",
                "agent_coordination"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Sent registration for agent {self.agent_id}")
    
    async def _heartbeat_loop(self):
        """ハートビートループ"""
        while self.connected:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                if self.websocket and self.connected:
                    heartbeat_message = {
                        "type": "heartbeat",
                        "agent_id": self.agent_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await self.websocket.send(json.dumps(heartbeat_message))
                    logger.debug("Sent heartbeat to ControlServer")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                self.connected = False
                break
    
    async def _receive_loop(self):
        """メッセージ受信ループ"""
        try:
            async for message in self.websocket:
                await self._handle_message(message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("ControlServer connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error receiving message from ControlServer: {e}")
            self.connected = False
    
    async def _handle_message(self, message: str):
        """ControlServerからのメッセージを処理"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "registration_confirmed":
                logger.info(f"Registration confirmed by ControlServer: {data.get('agent_id')}")
            elif message_type == "emergency_block":
                await self._handle_emergency_block(data)
            elif message_type == "unblock_session":
                await self._handle_unblock_session(data)
            elif message_type == "log_summary_request":
                await self._handle_log_summary_request(data)
            else:
                logger.debug(f"Received message from ControlServer: {message_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from ControlServer: {e}")
        except Exception as e:
            logger.error(f"Error handling ControlServer message: {e}")
    
    async def _handle_emergency_block(self, data: Dict):
        """緊急ブロック処理"""
        block_id = data.get("block_id")
        action = data.get("action")
        affected_sessions = data.get("affected_sessions", [])
        
        logger.warning(f"Emergency block received: {action} (ID: {block_id})")
        
        # AgentServerのブロック機能に転送
        try:
            from aetherterm.agentserver.auto_blocker import get_auto_blocker
            auto_blocker = get_auto_blocker()
            
            if action == "block_all_sessions":
                # 全セッションブロック
                from aetherterm.agentserver.terminals.asyncio_terminal import AsyncioTerminal
                for session_id in AsyncioTerminal.sessions:
                    auto_blocker.block_session(session_id, data.get("message", "Emergency block"))
            elif action == "block_session" and affected_sessions:
                # 個別セッションブロック
                for session_id in affected_sessions:
                    auto_blocker.block_session(session_id, data.get("message", "Session blocked"))
            
            # ブロック確認をControlServerに送信
            confirmation_message = {
                "type": "block_confirmation",
                "block_id": block_id,
                "confirmed_sessions": affected_sessions,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.websocket.send(json.dumps(confirmation_message))
            
        except Exception as e:
            logger.error(f"Error handling emergency block: {e}")
    
    async def _handle_unblock_session(self, data: Dict):
        """セッションブロック解除処理"""
        session_id = data.get("session_id")
        admin_user = data.get("admin_user")
        
        logger.info(f"Unblock session request: {session_id} by {admin_user}")
        
        try:
            from aetherterm.agentserver.auto_blocker import get_auto_blocker
            auto_blocker = get_auto_blocker()
            auto_blocker.unblock_session(session_id)
            
            logger.info(f"Session {session_id} unblocked successfully")
            
        except Exception as e:
            logger.error(f"Error unblocking session {session_id}: {e}")
    
    async def _handle_log_summary_request(self, data: Dict):
        """ログサマリ要求処理"""
        try:
            # 短期記憶の統計情報を送信
            from aetherterm.agentserver.terminals.asyncio_terminal import AsyncioTerminal
            
            if AsyncioTerminal.short_term_memory_manager:
                summary = AsyncioTerminal.short_term_memory_manager.get_memory_summary()
                
                response_message = {
                    "type": "memory_summary_response",
                    "request_id": data.get("request_id"),
                    "summary": summary,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await self.websocket.send(json.dumps(response_message))
                
        except Exception as e:
            logger.error(f"Error handling log summary request: {e}")
    
    async def send_session_update(self, session_info: Dict):
        """セッション更新をControlServerに送信"""
        if not self.websocket or not self.connected:
            return
            
        try:
            message = {
                "type": "session_update",
                "session": session_info,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.websocket.send(json.dumps(message))
            
        except Exception as e:
            logger.error(f"Error sending session update: {e}")
    
    def is_connected(self) -> bool:
        """接続状態を確認"""
        return self.connected and self.websocket is not None
    
    def get_connection_info(self) -> Dict:
        """接続情報を取得"""
        return {
            "agent_id": self.agent_id,
            "control_server_url": self.control_server_url,
            "connected": self.connected,
            "websocket_state": str(self.websocket.state) if self.websocket else "None"
        }