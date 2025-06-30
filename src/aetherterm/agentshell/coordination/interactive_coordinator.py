"""
インタラクティブ協調機能

エージェント実行中に他のエージェントへ動的に依頼を送信
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..websocket.client import WebSocketClient
from ..websocket.protocol import AgentMessage, MessageType

logger = logging.getLogger(__name__)


class AgentRequest:
    """エージェント間依頼"""
    
    def __init__(self, requester_id: str, target_agent: str, request_type: str, data: Dict[str, Any]):
        self.request_id = str(uuid4())
        self.requester_id = requester_id
        self.target_agent = target_agent
        self.request_type = request_type
        self.data = data
        self.response: Optional[Dict[str, Any]] = None
        self.completed = False
        self.event = asyncio.Event()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "requester_id": self.requester_id,
            "target_agent": self.target_agent,
            "request_type": self.request_type,
            "data": self.data
        }


class InteractiveCoordinator:
    """インタラクティブエージェント協調"""
    
    def __init__(self, websocket_client: WebSocketClient, agent_id: str):
        self.websocket_client = websocket_client
        self.agent_id = agent_id
        self.pending_requests: Dict[str, AgentRequest] = {}
        self.keyboard_listener_active = False
        
        # メッセージハンドラを登録
        self._setup_message_handlers()
    
    def _setup_message_handlers(self):
        """メッセージハンドラを設定"""
        
        async def handle_agent_request(message: AgentMessage):
            """他のエージェントからの依頼を処理"""
            data = message.data
            request_id = data.get("request_id")
            request_type = data.get("request_type")
            
            logger.info(f"依頼受信: {message.from_agent} -> {self.agent_id} ({request_type})")
            
            # 依頼タイプに応じて処理
            response = await self._handle_request(request_type, data)
            
            # 応答を送信
            await self.websocket_client.send_message(
                message.from_agent,
                MessageType.AGENT_MESSAGE,
                {
                    "request_id": request_id,
                    "response_type": "request_response",
                    "response": response
                }
            )
        
        async def handle_request_response(message: AgentMessage):
            """依頼への応答を処理"""
            data = message.data
            request_id = data.get("request_id")
            
            if request_id in self.pending_requests:
                request = self.pending_requests[request_id]
                request.response = data.get("response")
                request.completed = True
                request.event.set()
                
                logger.info(f"依頼応答受信: {request_id}")
        
        # 専用メッセージハンドラとして登録
        self.websocket_client.register_message_handler(
            MessageType.AGENT_MESSAGE, 
            self._route_agent_message
        )
    
    async def _route_agent_message(self, message: AgentMessage):
        """エージェントメッセージをルーティング"""
        data = message.data
        
        if data.get("response_type") == "request_response":
            await self._handle_request_response(message)
        elif "request_type" in data:
            await self._handle_agent_request(message)
    
    async def _handle_agent_request(self, message: AgentMessage):
        """他のエージェントからの依頼を処理"""
        data = message.data
        request_id = data.get("request_id")
        request_type = data.get("request_type")
        
        logger.info(f"依頼受信: {message.from_agent} -> {self.agent_id} ({request_type})")
        
        # 依頼タイプに応じて処理
        response = await self._handle_request(request_type, data)
        
        # 応答を送信
        await self.websocket_client.send_message(
            message.from_agent,
            MessageType.AGENT_MESSAGE,
            {
                "request_id": request_id,
                "response_type": "request_response",
                "response": response
            }
        )
    
    async def _handle_request_response(self, message: AgentMessage):
        """依頼への応答を処理"""
        data = message.data
        request_id = data.get("request_id")
        
        if request_id in self.pending_requests:
            request = self.pending_requests[request_id]
            request.response = data.get("response")
            request.completed = True
            request.event.set()
            
            logger.info(f"依頼応答受信: {request_id}")
    
    async def request_agent_action(
        self, 
        target_agent: str, 
        request_type: str, 
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """他のエージェントに依頼を送信して応答を待機"""
        
        request = AgentRequest(self.agent_id, target_agent, request_type, data)
        self.pending_requests[request.request_id] = request
        
        try:
            # 依頼を送信
            await self.websocket_client.send_message(
                target_agent,
                MessageType.AGENT_MESSAGE,
                request.to_dict()
            )
            
            logger.info(f"依頼送信: {self.agent_id} -> {target_agent} ({request_type})")
            
            # 応答を待機
            await asyncio.wait_for(request.event.wait(), timeout=timeout)
            return request.response
            
        except asyncio.TimeoutError:
            logger.warning(f"依頼タイムアウト: {request.request_id}")
            return None
        finally:
            # 依頼を削除
            self.pending_requests.pop(request.request_id, None)
    
    async def _handle_request(self, request_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """受信した依頼を処理"""
        
        if request_type == "status_inquiry":
            # ステータス問い合わせ
            return {
                "agent_id": self.agent_id,
                "status": "active",
                "current_task": data.get("current_task", "none")
            }
        
        elif request_type == "code_review":
            # コードレビュー依頼
            file_path = data.get("file_path")
            return {
                "review_status": "received",
                "file_path": file_path,
                "message": f"コードレビュー依頼を受信: {file_path}"
            }
        
        elif request_type == "test_generation":
            # テスト生成依頼
            module_path = data.get("module_path")
            return {
                "test_status": "received", 
                "module_path": module_path,
                "message": f"テスト生成依頼を受信: {module_path}"
            }
        
        elif request_type == "documentation":
            # ドキュメント生成依頼
            code_path = data.get("code_path")
            return {
                "doc_status": "received",
                "code_path": code_path,
                "message": f"ドキュメント生成依頼を受信: {code_path}"
            }
        
        else:
            return {
                "error": f"未対応の依頼タイプ: {request_type}"
            }
    
    async def start_keyboard_listener(self):
        """キーボード入力でエージェント間通信を開始"""
        self.keyboard_listener_active = True
        
        print("\n=== エージェント間通信モード ===")
        print("利用可能なコマンド:")
        print("  @<agent_id> <request_type> <message>  - 特定エージェントに依頼")
        print("  list                                   - エージェント一覧")
        print("  quit                                   - 終了")
        print("例: @claude_001 code_review /path/to/file.py")
        
        while self.keyboard_listener_active:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "\n> "
                )
                
                await self._process_keyboard_input(user_input.strip())
                
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                logger.error(f"キーボード入力処理エラー: {e}")
    
    async def _process_keyboard_input(self, user_input: str):
        """キーボード入力を処理"""
        if not user_input:
            return
        
        if user_input == "quit":
            self.keyboard_listener_active = False
            return
        
        if user_input == "list":
            # エージェント一覧を要求
            await self.websocket_client.broadcast_message(
                MessageType.COORDINATION_REQUEST,
                {"request_type": "agent_list"}
            )
            return
        
        if user_input.startswith("@"):
            # エージェント依頼
            await self._process_agent_request(user_input)
        else:
            print("無効な入力です。@<agent_id> <request_type> <message> の形式で入力してください")
    
    async def _process_agent_request(self, user_input: str):
        """エージェント依頼を処理"""
        try:
            # @agent_id request_type message の形式をパース
            parts = user_input[1:].split(" ", 2)
            if len(parts) < 2:
                print("形式: @<agent_id> <request_type> [message]")
                return
            
            target_agent = parts[0]
            request_type = parts[1]
            message = parts[2] if len(parts) > 2 else ""
            
            # 依頼を送信
            response = await self.request_agent_action(
                target_agent,
                request_type,
                {"message": message, "timestamp": asyncio.get_event_loop().time()}
            )
            
            if response:
                print(f"応答: {response}")
            else:
                print("応答がありませんでした（タイムアウト）")
                
        except Exception as e:
            print(f"依頼処理エラー: {e}")
    
    def stop_keyboard_listener(self):
        """キーボードリスナーを停止"""
        self.keyboard_listener_active = False