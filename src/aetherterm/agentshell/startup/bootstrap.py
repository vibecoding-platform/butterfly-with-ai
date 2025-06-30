"""
AgentShell起動ブートストラップ

詳細な起動フローを管理
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .config_loader import ConfigLoader
from .dependency_checker import DependencyChecker
from .registration_flow import RegistrationFlow
from ..websocket.client import WebSocketClient

logger = logging.getLogger(__name__)


class StartupPhase(str, Enum):
    """起動フェーズ"""
    INIT = "initialization"
    CONFIG_LOAD = "config_loading"
    DEPENDENCY_CHECK = "dependency_check"
    SERVER_CONNECTION = "server_connection"
    AGENT_PREPARATION = "agent_preparation"
    AGENT_REGISTRATION = "agent_registration"
    COORDINATION_SETUP = "coordination_setup"
    READY = "ready"
    FAILED = "failed"


@dataclass
class StartupProgress:
    """起動進捗"""
    phase: StartupPhase
    progress: float  # 0.0-1.0
    message: str
    details: Dict[str, Any]
    timestamp: float


class BootstrapManager:
    """AgentShell起動マネージャー"""
    
    def __init__(self):
        self.config_loader = ConfigLoader()
        self.dependency_checker = DependencyChecker()
        self.registration_flow = RegistrationFlow()
        
        self.progress_history: List[StartupProgress] = []
        self.current_phase = StartupPhase.INIT
        self.websocket_client: Optional[WebSocketClient] = None
        
        # 起動設定
        self.server_url = "http://localhost:57575"
        self.agent_configs: List[Dict[str, str]] = []
        self.startup_timeout = 60.0  # 秒
        self.retry_attempts = 3
        
    async def bootstrap(
        self, 
        server_url: str,
        agent_specs: List[str],
        config_path: Optional[str] = None,
        debug: bool = False
    ) -> Tuple[bool, str]:
        """
        AgentShellを起動
        
        Returns:
            (success: bool, error_message: str)
        """
        start_time = time.time()
        
        try:
            # Phase 1: 初期化
            await self._update_progress(StartupPhase.INIT, 0.0, "起動プロセスを開始")
            
            self.server_url = server_url
            if debug:
                logging.getLogger().setLevel(logging.DEBUG)
            
            # Phase 2: 設定読み込み
            await self._update_progress(StartupPhase.CONFIG_LOAD, 0.1, "設定を読み込み中")
            config_success, config_error = await self._load_configuration(config_path, agent_specs)
            if not config_success:
                return False, f"設定読み込みエラー: {config_error}"
            
            # Phase 3: 依存関係チェック
            await self._update_progress(StartupPhase.DEPENDENCY_CHECK, 0.2, "依存関係をチェック中")
            dep_success, dep_error = await self._check_dependencies()
            if not dep_success:
                return False, f"依存関係エラー: {dep_error}"
            
            # Phase 4: AgentServer接続
            await self._update_progress(StartupPhase.SERVER_CONNECTION, 0.3, "AgentServerに接続中")
            conn_success, conn_error = await self._connect_to_server()
            if not conn_success:
                return False, f"サーバー接続エラー: {conn_error}"
            
            # Phase 5: エージェント準備
            await self._update_progress(StartupPhase.AGENT_PREPARATION, 0.5, "エージェントを準備中")
            prep_success, prep_error = await self._prepare_agents()
            if not prep_success:
                return False, f"エージェント準備エラー: {prep_error}"
            
            # Phase 6: エージェント登録
            await self._update_progress(StartupPhase.AGENT_REGISTRATION, 0.7, "エージェントを登録中")
            reg_success, reg_error = await self._register_agents()
            if not reg_success:
                return False, f"エージェント登録エラー: {reg_error}"
            
            # Phase 7: 協調システム設定
            await self._update_progress(StartupPhase.COORDINATION_SETUP, 0.9, "協調システムを設定中")
            coord_success, coord_error = await self._setup_coordination()
            if not coord_success:
                return False, f"協調システム設定エラー: {coord_error}"
            
            # Phase 8: 完了
            elapsed_time = time.time() - start_time
            await self._update_progress(
                StartupPhase.READY, 
                1.0, 
                f"起動完了 ({elapsed_time:.1f}秒)"
            )
            
            return True, "起動成功"
            
        except Exception as e:
            await self._update_progress(StartupPhase.FAILED, 0.0, f"起動失敗: {e}")
            logger.error(f"起動プロセスでエラー: {e}")
            return False, str(e)
    
    async def _load_configuration(self, config_path: Optional[str], agent_specs: List[str]) -> Tuple[bool, str]:
        """設定を読み込み"""
        try:
            # 設定ファイルから基本設定を読み込み
            if config_path:
                base_config = await self.config_loader.load_from_file(config_path)
                self.server_url = base_config.get("server_url", self.server_url)
                self.startup_timeout = base_config.get("startup_timeout", self.startup_timeout)
            
            # エージェント仕様を解析
            self.agent_configs = []
            for spec in agent_specs:
                if ":" not in spec:
                    return False, f"無効なエージェント仕様: {spec} (形式: type:id)"
                
                agent_type, agent_id = spec.split(":", 1)
                if agent_type not in ["claude_code", "openhands"]:
                    return False, f"未対応のエージェントタイプ: {agent_type}"
                
                self.agent_configs.append({
                    "agent_type": agent_type,
                    "agent_id": agent_id,
                    "spec": spec
                })
            
            if not self.agent_configs:
                # デフォルト設定
                self.agent_configs = [
                    {"agent_type": "claude_code", "agent_id": "claude_001", "spec": "claude_code:claude_001"},
                    {"agent_type": "openhands", "agent_id": "openhands_001", "spec": "openhands:openhands_001"}
                ]
            
            await self._update_progress(
                StartupPhase.CONFIG_LOAD, 
                0.15,
                f"設定読み込み完了: {len(self.agent_configs)}エージェント"
            )
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    async def _check_dependencies(self) -> Tuple[bool, str]:
        """依存関係をチェック"""
        try:
            # 各エージェントタイプの依存関係をチェック
            required_agents = set(config["agent_type"] for config in self.agent_configs)
            
            for agent_type in required_agents:
                success, error = await self.dependency_checker.check_agent_dependencies(agent_type)
                if not success:
                    return False, f"{agent_type}: {error}"
                
                await self._update_progress(
                    StartupPhase.DEPENDENCY_CHECK,
                    0.2 + (0.05 * len([t for t in required_agents if t <= agent_type])),
                    f"{agent_type} 依存関係確認済み"
                )
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    async def _connect_to_server(self) -> Tuple[bool, str]:
        """AgentServerに接続"""
        try:
            self.websocket_client = WebSocketClient(self.server_url)
            
            # リトライ付き接続
            for attempt in range(self.retry_attempts):
                await self._update_progress(
                    StartupPhase.SERVER_CONNECTION,
                    0.3 + (0.05 * attempt),
                    f"接続試行 {attempt + 1}/{self.retry_attempts}"
                )
                
                if await self.websocket_client.connect():
                    await self._update_progress(
                        StartupPhase.SERVER_CONNECTION,
                        0.45,
                        "AgentServer接続成功"
                    )
                    return True, ""
                
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2.0 * (attempt + 1))  # 指数バックオフ
            
            return False, f"AgentServerに接続できません: {self.server_url}"
            
        except Exception as e:
            return False, str(e)
    
    async def _prepare_agents(self) -> Tuple[bool, str]:
        """エージェントを準備"""
        try:
            # エージェント実行ファイルの存在確認
            for i, config in enumerate(self.agent_configs):
                agent_type = config["agent_type"]
                agent_id = config["agent_id"]
                
                await self._update_progress(
                    StartupPhase.AGENT_PREPARATION,
                    0.5 + (0.15 * i / len(self.agent_configs)),
                    f"{agent_id} を準備中"
                )
                
                # エージェント特有の準備処理
                prep_success, prep_error = await self._prepare_individual_agent(config)
                if not prep_success:
                    return False, f"{agent_id}: {prep_error}"
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    async def _prepare_individual_agent(self, config: Dict[str, str]) -> Tuple[bool, str]:
        """個別エージェントの準備"""
        agent_type = config["agent_type"]
        agent_id = config["agent_id"]
        
        if agent_type == "claude_code":
            # ClaudeCode CLIの動作確認
            try:
                proc = await asyncio.create_subprocess_exec(
                    "claude", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await proc.wait()
                if proc.returncode != 0:
                    return False, "ClaudeCode CLI not found or not working"
            except FileNotFoundError:
                return False, "ClaudeCode CLI not installed"
                
        elif agent_type == "openhands":
            # OpenHandsサービスの接続確認
            # TODO: OpenHandsの具体的な確認方法を実装
            pass
        
        return True, ""
    
    async def _register_agents(self) -> Tuple[bool, str]:
        """エージェントを登録"""
        try:
            success, error = await self.registration_flow.register_all_agents(
                self.websocket_client,
                self.agent_configs
            )
            
            if not success:
                return False, error
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    async def _setup_coordination(self) -> Tuple[bool, str]:
        """協調システムを設定"""
        try:
            # ハートビート開始
            asyncio.create_task(self.websocket_client.start_heartbeat())
            
            # エージェント間通信テスト
            await asyncio.sleep(1.0)  # 接続安定化待ち
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    async def _update_progress(self, phase: StartupPhase, progress: float, message: str):
        """起動進捗を更新"""
        self.current_phase = phase
        
        progress_info = StartupProgress(
            phase=phase,
            progress=progress,
            message=message,
            details={},
            timestamp=time.time()
        )
        
        self.progress_history.append(progress_info)
        logger.info(f"[{phase.value}] {progress:.1%} - {message}")
    
    def get_startup_status(self) -> Dict[str, Any]:
        """起動状況を取得"""
        if not self.progress_history:
            return {"phase": "not_started", "progress": 0.0}
        
        latest = self.progress_history[-1]
        return {
            "phase": latest.phase.value,
            "progress": latest.progress,
            "message": latest.message,
            "agent_count": len(self.agent_configs),
            "server_url": self.server_url,
            "is_connected": self.websocket_client.is_connected if self.websocket_client else False
        }