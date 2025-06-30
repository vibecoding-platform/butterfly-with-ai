"""
Terminal Socket Handler

ターミナル関連のSocket.IOイベントを処理
"""

import logging
from typing import Any, Dict

from .base import BaseSocketHandler
from ..terminals.asyncio_terminal import AsyncioTerminal
from ..terminals.agent_shell_terminal import AgentShellTerminal

log = logging.getLogger("aetherterm.handlers.terminal")


class TerminalHandler(BaseSocketHandler):
    """ターミナルイベントハンドラ"""

    def __init__(self, sio, log_manager=None):
        super().__init__(sio, log_manager)
        self.terminals: Dict[str, AsyncioTerminal] = {}

    async def handle_terminal_create(self, sid: str, data: Dict[str, Any]):
        """新しいターミナルセッションを作成"""
        try:
            terminal_id = data.get('terminal_id', sid)
            launch_mode = data.get('launch_mode', 'default')  # default, agentshell, agent
            agent_config = data.get('agent_config', {})
            
            if terminal_id in self.terminals:
                await self.emit_to_client(sid, 'terminal_error', {
                    'error': 'Terminal already exists'
                })
                return

            # ターミナル作成（起動モードに応じて適切なクラスを選択）
            if launch_mode in ["agentshell", "agent"]:
                terminal = AgentShellTerminal(
                    terminal_id=terminal_id,
                    socket_io=self.sio,
                    sid=sid,
                    launch_mode=launch_mode,
                    agent_config=agent_config
                )
            else:
                # 従来のターミナル（レガシーサポート）
                terminal = AsyncioTerminal(
                    user=None,  # 適切なユーザー情報を渡す
                    path=agent_config.get("working_directory", "/"),
                    session=terminal_id,
                    socket=None,  # 適切なソケット情報を渡す
                    uri="",
                    render_string="",
                    broadcast=self._broadcast_to_client,
                    login=False,
                    pam_profile=None
                )
            
            self.terminals[terminal_id] = terminal
            await terminal.start()
            
            await self.emit_to_client(sid, 'terminal_created', {
                'terminal_id': terminal_id,
                'status': 'ready',
                'launch_mode': launch_mode,
                'agent_config': agent_config
            })
            
            log.info(f"Terminal {terminal_id} created for session {sid} with mode {launch_mode}")
            
        except Exception as e:
            log.error(f"Failed to create terminal: {e}")
            await self.emit_to_client(sid, 'terminal_error', {
                'error': str(e)
            })

    async def handle_terminal_input(self, sid: str, data: Dict[str, Any]):
        """ターミナル入力を処理"""
        try:
            terminal_id = data.get('terminal_id', sid)
            input_data = data.get('input', '')
            
            if terminal_id not in self.terminals:
                await self.emit_to_client(sid, 'terminal_error', {
                    'error': 'Terminal not found'
                })
                return
                
            terminal = self.terminals[terminal_id]
            await terminal.write_input(input_data)
            
        except Exception as e:
            log.error(f"Failed to handle terminal input: {e}")
            await self.emit_to_client(sid, 'terminal_error', {
                'error': str(e)
            })

    async def handle_terminal_resize(self, sid: str, data: Dict[str, Any]):
        """ターミナルリサイズを処理"""
        try:
            terminal_id = data.get('terminal_id', sid)
            rows = data.get('rows', 24)
            cols = data.get('cols', 80)
            
            if terminal_id not in self.terminals:
                return
                
            terminal = self.terminals[terminal_id]
            await terminal.resize(rows, cols)
            
        except Exception as e:
            log.error(f"Failed to resize terminal: {e}")

    async def handle_terminal_disconnect(self, sid: str):
        """ターミナル切断を処理"""
        try:
            terminals_to_remove = []
            for terminal_id, terminal in self.terminals.items():
                if terminal.sid == sid:
                    await terminal.stop()
                    terminals_to_remove.append(terminal_id)
            
            for terminal_id in terminals_to_remove:
                del self.terminals[terminal_id]
                log.info(f"Terminal {terminal_id} removed for session {sid}")
                
        except Exception as e:
            log.error(f"Failed to disconnect terminal: {e}")

    async def handle_event(self, sid: str, data: Dict[str, Any]) -> Any:
        """イベントルーティング"""
        event_type = data.get('type')
        
        if event_type == 'create':
            await self.handle_terminal_create(sid, data)
        elif event_type == 'input':
            await self.handle_terminal_input(sid, data)
        elif event_type == 'resize':
            await self.handle_terminal_resize(sid, data)
        elif event_type == 'disconnect':
            await self.handle_terminal_disconnect(sid)
        elif event_type == 'spawn':
            await self.handle_terminal_spawn(sid, data)
        else:
            log.warning(f"Unknown terminal event type: {event_type}")

    async def handle_terminal_spawn(self, sid: str, data: Dict[str, Any]):
        """新しいターミナルを生成（AgentShellからの要求）"""
        try:
            parent_terminal_id = data.get('parent_terminal_id')
            spawn_config = data.get('spawn_config', {})
            
            if parent_terminal_id not in self.terminals:
                await self.emit_to_client(sid, 'terminal_error', {
                    'error': 'Parent terminal not found'
                })
                return
            
            parent_terminal = self.terminals[parent_terminal_id]
            
            # AgentShellTerminalでない場合はエラー
            if not isinstance(parent_terminal, AgentShellTerminal):
                await self.emit_to_client(sid, 'terminal_error', {
                    'error': 'Terminal spawning not supported for this terminal type'
                })
                return
            
            # 新しいターミナルを生成
            new_terminal_id = await parent_terminal.spawn_additional_terminal(spawn_config)
            
            log.info(f"Terminal spawned: {new_terminal_id} from {parent_terminal_id}")
            
        except Exception as e:
            log.error(f"Failed to spawn terminal: {e}")
            await self.emit_to_client(sid, 'terminal_error', {
                'error': str(e)
            })

    def _broadcast_to_client(self, session_id: str, message: str):
        """クライアントにメッセージをブロードキャスト（レガシーサポート）"""
        # 実装は省略 - 必要に応じて追加
        pass