"""
ClaudeCodeエージェント統合

Anthropic公式CLIとの連携を提供
"""

import asyncio
import json
import logging
import re
import subprocess
from typing import Any, Dict, List, Optional
from uuid import UUID

from .base import AgentInterface, AgentCapability, AgentStatus, TaskStatus
from ..coordination.interactive_coordinator import InteractiveCoordinator
from ..websocket.protocol import AgentMessage, MessageType

logger = logging.getLogger(__name__)


class ClaudeCodeOutputParser:
    """ClaudeCodeの自由テキスト出力を構造化データに変換"""
    
    def __init__(self):
        # ファイル操作パターン
        self.file_patterns = {
            'created': re.compile(r'(?:created|wrote|generated)\s+(?:file\s+)?["`]?([^\s"`]+)["`]?', re.IGNORECASE),
            'modified': re.compile(r'(?:modified|updated|edited|changed)\s+(?:file\s+)?["`]?([^\s"`]+)["`]?', re.IGNORECASE),
            'deleted': re.compile(r'(?:deleted|removed)\s+(?:file\s+)?["`]?([^\s"`]+)["`]?', re.IGNORECASE),
        }
        
        # コードブロックパターン  
        self.code_pattern = re.compile(r'```(\w+)?\n(.*?)\n```', re.DOTALL)
        
        # エラーパターン
        self.error_patterns = [
            re.compile(r'error[:：]\s*(.+)', re.IGNORECASE),
            re.compile(r'failed[:：]\s*(.+)', re.IGNORECASE),
            re.compile(r'cannot\s+(.+)', re.IGNORECASE),
        ]
        
        # 完了パターン
        self.completion_patterns = [
            re.compile(r'(?:done|completed|finished|success)', re.IGNORECASE),
            re.compile(r'task\s+(?:completed|finished)', re.IGNORECASE),
        ]
        
        # エージェント依頼パターン
        self.request_patterns = {
            'review': re.compile(r'REQUEST_REVIEW:\s*([^\s]+)', re.IGNORECASE),
            'tests': re.compile(r'REQUEST_TESTS:\s*([^\s]+)', re.IGNORECASE), 
            'docs': re.compile(r'REQUEST_DOCS:\s*([^\s]+)', re.IGNORECASE),
        }
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """ClaudeCodeの出力を解析して構造化"""
        result = {
            'status': 'unknown',
            'files': {
                'created': [],
                'modified': [],
                'deleted': []
            },
            'code_blocks': [],
            'errors': [],
            'summary': '',
            'raw_output': output
        }
        
        # ファイル操作を抽出
        for action, pattern in self.file_patterns.items():
            matches = pattern.findall(output)
            result['files'][action].extend(matches)
        
        # コードブロックを抽出
        for match in self.code_pattern.finditer(output):
            language = match.group(1) or 'text'
            code = match.group(2).strip()
            result['code_blocks'].append({
                'language': language,
                'code': code
            })
        
        # エラーを抽出
        for pattern in self.error_patterns:
            matches = pattern.findall(output)
            result['errors'].extend(matches)
        
        # ステータス判定
        if result['errors']:
            result['status'] = 'error'
        elif any(pattern.search(output) for pattern in self.completion_patterns):
            result['status'] = 'completed'
        elif result['files']['created'] or result['files']['modified']:
            result['status'] = 'partial_success'
        else:
            result['status'] = 'in_progress'
        
        # サマリー生成
        result['summary'] = self._generate_summary(result)
        
        return result
    
    def _generate_summary(self, parsed_result: Dict[str, Any]) -> str:
        """解析結果からサマリーを生成"""
        parts = []
        
        files = parsed_result['files']
        if files['created']:
            parts.append(f"Created {len(files['created'])} files")
        if files['modified']:
            parts.append(f"Modified {len(files['modified'])} files")
        if files['deleted']:
            parts.append(f"Deleted {len(files['deleted'])} files")
        
        if parsed_result['errors']:
            parts.append(f"Found {len(parsed_result['errors'])} errors")
        
        return ", ".join(parts) if parts else "No significant actions detected"


class ClaudeCodeAgent(AgentInterface):
    """ClaudeCodeエージェント"""
    
    CAPABILITIES = [
        AgentCapability.CODE_GENERATION,
        AgentCapability.CODE_EDITING,
        AgentCapability.CODE_REVIEW,
        AgentCapability.DEBUGGING,
        AgentCapability.DOCUMENTATION,
        AgentCapability.GENERAL_ASSISTANCE,
    ]
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.process: Optional[asyncio.subprocess.Process] = None
        self.parser = ClaudeCodeOutputParser()
        self.current_task: Optional[UUID] = None
        self.status = AgentStatus.IDLE
        self.coordinator: Optional[InteractiveCoordinator] = None
        
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """エージェントを初期化"""
        try:
            # ClaudeCodeの存在確認
            result = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            
            if result.returncode != 0:
                logger.error("ClaudeCode CLIが見つかりません")
                return False
            
            self.status = AgentStatus.IDLE
            logger.info(f"ClaudeCodeエージェント {self.agent_id} が初期化されました")
            return True
            
        except Exception as e:
            logger.error(f"ClaudeCodeエージェント初期化エラー: {e}")
            return False
    
    def set_websocket_client(self, websocket_client):
        """WebSocketクライアントとコーディネーターを設定"""
        self.websocket_client = websocket_client
        self.coordinator = InteractiveCoordinator(websocket_client, self.agent_id)
    
    async def shutdown(self) -> None:
        """エージェントをシャットダウン"""
        if self.process and self.process.returncode is None:
            self.process.terminate()
            await self.process.wait()
        self.status = AgentStatus.OFFLINE
    
    def get_capabilities(self) -> List[AgentCapability]:
        """エージェントの能力を取得"""
        return self.CAPABILITIES
    
    def get_status(self) -> AgentStatus:
        """現在のステータスを取得"""
        return self.status
    
    async def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """タスクを実行"""
        self.current_task = UUID(task_data.get('task_id', str(UUID())))
        self.status = AgentStatus.BUSY
        
        try:
            # ClaudeCodeに送信するプロンプトを構築
            prompt = self._build_prompt(task_data)
            
            # ClaudeCodeを実行
            raw_output = await self._execute_claude_code(prompt)
            
            # 出力を解析
            parsed_result = self.parser.parse_output(raw_output)
            
            # WebSocket経由で結果を送信
            if self.websocket_client:
                await self._send_task_result(parsed_result)
            
            self.status = AgentStatus.IDLE
            return parsed_result
            
        except Exception as e:
            logger.error(f"タスク実行エラー: {e}")
            self.status = AgentStatus.ERROR
            
            error_result = {
                'status': 'error',
                'error': str(e),
                'files': {'created': [], 'modified': [], 'deleted': []},
                'code_blocks': [],
                'errors': [str(e)],
                'summary': f"Task failed: {e}"
            }
            
            if self.websocket_client:
                await self._send_task_result(error_result)
                
            return error_result
    
    def _build_prompt(self, task_data: Dict[str, Any]) -> str:
        """タスクデータからClaudeCode用プロンプトを構築"""
        prompt_parts = []
        
        # 基本指示
        prompt_parts.append("Please complete the following task:")
        prompt_parts.append(f"Task: {task_data.get('description', '')}")
        
        # ファイル情報
        if 'files' in task_data:
            prompt_parts.append("\nRelevant files:")
            for file_path in task_data['files']:
                prompt_parts.append(f"- {file_path}")
        
        # コンテキスト情報
        if 'context' in task_data:
            prompt_parts.append(f"\nContext: {task_data['context']}")
        
        # 構造化出力の要求
        prompt_parts.append("""
Please be explicit about:
1. Any files you create, modify, or delete (mention the exact file paths)
2. Any errors or issues encountered  
3. When the task is completed
4. Include code in properly formatted code blocks when relevant

If you need assistance from other agents, you can request:
- Code review: mention "REQUEST_REVIEW: <file_path>"
- Test generation: mention "REQUEST_TESTS: <module_path>"
- Documentation: mention "REQUEST_DOCS: <code_path>"
        """)
        
        return "\n".join(prompt_parts)
    
    async def _execute_claude_code(self, prompt: str) -> str:
        """ClaudeCodeを実行して結果を取得"""
        try:
            self.process = await asyncio.create_subprocess_exec(
                "claude",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = await self.process.communicate(input=prompt)
            
            if stderr:
                logger.warning(f"ClaudeCode stderr: {stderr}")
            
            return stdout or stderr or "No output received"
            
        except Exception as e:
            logger.error(f"ClaudeCode実行エラー: {e}")
            raise
    
    async def _send_task_result(self, result: Dict[str, Any]):
        """WebSocket経由でタスク結果を送信"""
        if not self.websocket_client or not self.current_task:
            return
        
        message_type = MessageType.TASK_COMPLETION if result['status'] in ['completed', 'partial_success'] else MessageType.TASK_ERROR
        
        await self.websocket_client.broadcast_message(
            message_type,
            {
                'task_id': str(self.current_task),
                'agent_id': self.agent_id,
                'result': result
            }
        )
    
    async def cancel_task(self) -> bool:
        """現在のタスクをキャンセル"""
        if self.process and self.process.returncode is None:
            self.process.terminate()
            await self.process.wait()
            self.status = AgentStatus.IDLE
            return True
        return False
    
    async def get_task_status(self, task_id: UUID) -> Optional[TaskStatus]:
        """タスクの状態を取得"""
        if self.current_task == task_id:
            if self.status == AgentStatus.BUSY:
                return TaskStatus.RUNNING
            elif self.status == AgentStatus.ERROR:
                return TaskStatus.FAILED
        return None
    
    async def get_task_progress(self, task_id: UUID) -> Optional[float]:
        """タスクの進捗を取得"""
        if self.current_task == task_id and self.status == AgentStatus.BUSY:
            return 0.5  # ClaudeCodeは進捗が不明なので中間値
        return None
    
    async def _wait_for_intervention_response(self, intervention) -> Any:
        """介入応答を待つ（実装省略）"""
        pass