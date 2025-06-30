"""
設定ローダー

AgentShellの設定ファイル読み込みと解析を提供
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import toml

logger = logging.getLogger(__name__)


class ConfigLoader:
    """AgentShell設定ローダー"""
    
    def __init__(self):
        self.default_config = {
            "server": {
                "url": "http://localhost:57575",
                "reconnect_interval": 5.0,
                "heartbeat_interval": 30.0,
                "connection_timeout": 10.0
            },
            "agents": {
                "claude_code": {
                    "executable": "claude",
                    "timeout": 120.0,
                    "max_retries": 3,
                    "working_directory": None
                },
                "openhands": {
                    "endpoint": "http://localhost:3000",
                    "timeout": 300.0,
                    "max_retries": 2,
                    "api_key": None
                }
            },
            "coordination": {
                "enable_interactive": True,
                "enable_auto_requests": True,
                "request_timeout": 30.0,
                "max_concurrent_tasks": 5
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": None
            }
        }
    
    async def load_from_file(self, config_path: str) -> Dict[str, Any]:
        """設定ファイルから読み込み"""
        try:
            config_file = Path(config_path)
            
            if not config_file.exists():
                logger.warning(f"設定ファイルが見つかりません: {config_path}")
                return self.default_config.copy()
            
            # ファイル拡張子に基づく読み込み
            if config_file.suffix.lower() == '.toml':
                return await self._load_toml(config_file)
            elif config_file.suffix.lower() == '.json':
                return await self._load_json(config_file)
            else:
                logger.error(f"未対応の設定ファイル形式: {config_file.suffix}")
                return self.default_config.copy()
                
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー: {e}")
            return self.default_config.copy()
    
    async def _load_toml(self, config_file: Path) -> Dict[str, Any]:
        """TOML設定ファイルを読み込み"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = toml.load(f)
                
            # デフォルト設定とマージ
            merged_config = self._merge_configs(self.default_config, file_config)
            logger.info(f"TOML設定ファイルを読み込みました: {config_file}")
            return merged_config
            
        except Exception as e:
            logger.error(f"TOML設定ファイル読み込みエラー: {e}")
            return self.default_config.copy()
    
    async def _load_json(self, config_file: Path) -> Dict[str, Any]:
        """JSON設定ファイルを読み込み"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                
            # デフォルト設定とマージ
            merged_config = self._merge_configs(self.default_config, file_config)
            logger.info(f"JSON設定ファイルを読み込みました: {config_file}")
            return merged_config
            
        except Exception as e:
            logger.error(f"JSON設定ファイル読み込みエラー: {e}")
            return self.default_config.copy()
    
    def _merge_configs(self, default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """設定を再帰的にマージ"""
        result = default.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def find_config_file(self, explicit_path: Optional[str] = None) -> Optional[str]:
        """設定ファイルを検索"""
        # 明示的なパスが指定されている場合
        if explicit_path:
            if Path(explicit_path).exists():
                return explicit_path
            else:
                logger.warning(f"指定された設定ファイルが見つかりません: {explicit_path}")
        
        # 標準的な場所を検索
        search_paths = [
            "./agentshell_config.toml",
            "./agentshell_config.json", 
            "~/.config/aetherterm/agentshell.toml",
            "~/.config/aetherterm/agentshell.json",
            "/etc/aetherterm/agentshell.toml",
            "/etc/aetherterm/agentshell.json"
        ]
        
        for path_str in search_paths:
            path = Path(path_str).expanduser()
            if path.exists():
                logger.info(f"設定ファイルを発見: {path}")
                return str(path)
        
        logger.info("設定ファイルが見つからないため、デフォルト設定を使用")
        return None
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """設定を検証"""
        errors = []
        
        # サーバー設定検証
        server_config = config.get("server", {})
        if not server_config.get("url"):
            errors.append("server.url が設定されていません")
        
        if server_config.get("reconnect_interval", 0) <= 0:
            errors.append("server.reconnect_interval は正の数値である必要があります")
        
        # エージェント設定検証
        agents_config = config.get("agents", {})
        
        # ClaudeCode設定検証
        claude_config = agents_config.get("claude_code", {})
        if claude_config.get("timeout", 0) <= 0:
            errors.append("agents.claude_code.timeout は正の数値である必要があります")
        
        # OpenHands設定検証
        openhands_config = agents_config.get("openhands", {})
        if openhands_config.get("timeout", 0) <= 0:
            errors.append("agents.openhands.timeout は正の数値である必要があります")
        
        # 協調設定検証
        coordination_config = config.get("coordination", {})
        if coordination_config.get("request_timeout", 0) <= 0:
            errors.append("coordination.request_timeout は正の数値である必要があります")
        
        if coordination_config.get("max_concurrent_tasks", 0) <= 0:
            errors.append("coordination.max_concurrent_tasks は正の整数である必要があります")
        
        return len(errors) == 0, errors
    
    def get_agent_config(self, config: Dict[str, Any], agent_type: str) -> Dict[str, Any]:
        """特定エージェントタイプの設定を取得"""
        agents_config = config.get("agents", {})
        return agents_config.get(agent_type, {})
    
    def get_server_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """サーバー設定を取得"""
        return config.get("server", {})
    
    def get_coordination_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """協調設定を取得"""
        return config.get("coordination", {})
    
    def apply_environment_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """環境変数による設定オーバーライドを適用"""
        env_mappings = {
            "AGENTSHELL_SERVER_URL": ("server", "url"),
            "AGENTSHELL_SERVER_TIMEOUT": ("server", "connection_timeout"),
            "AGENTSHELL_CLAUDE_TIMEOUT": ("agents", "claude_code", "timeout"),
            "AGENTSHELL_OPENHANDS_ENDPOINT": ("agents", "openhands", "endpoint"),
            "AGENTSHELL_OPENHANDS_API_KEY": ("agents", "openhands", "api_key"),
            "AGENTSHELL_DEBUG": ("logging", "level"),
        }
        
        result_config = config.copy()
        
        for env_var, config_path in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value:
                # ネストされた設定パスを辿る
                current = result_config
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                # 型変換
                final_key = config_path[-1]
                if env_var.endswith("_TIMEOUT"):
                    try:
                        current[final_key] = float(env_value)
                    except ValueError:
                        logger.warning(f"環境変数 {env_var} の値が数値ではありません: {env_value}")
                elif env_var == "AGENTSHELL_DEBUG":
                    current[final_key] = "DEBUG" if env_value.lower() in ("1", "true", "yes") else "INFO"
                else:
                    current[final_key] = env_value
                
                logger.debug(f"環境変数 {env_var} により設定をオーバーライド: {env_value}")
        
        return result_config
    
    def create_example_config(self, output_path: str) -> bool:
        """サンプル設定ファイルを作成"""
        try:
            config_content = """# AgentShell 設定ファイル

[server]
url = "http://localhost:57575"
reconnect_interval = 5.0
heartbeat_interval = 30.0
connection_timeout = 10.0

[agents.claude_code]
executable = "claude"
timeout = 120.0
max_retries = 3
# working_directory = "/path/to/project"

[agents.openhands]
endpoint = "http://localhost:3000"
timeout = 300.0
max_retries = 2
# api_key = "your-api-key-here"

[coordination]
enable_interactive = true
enable_auto_requests = true
request_timeout = 30.0
max_concurrent_tasks = 5

[logging]
level = "INFO"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# file = "/var/log/agentshell.log"
"""
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            logger.info(f"サンプル設定ファイルを作成しました: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"サンプル設定ファイル作成エラー: {e}")
            return False