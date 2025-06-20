"""
AetherTerm Configuration Management Package

AgentServer、AgentShell、ControlServer間で共有される設定管理システム。
TOML設定ファイルの読み込み、バリデーション、バージョン管理を提供します。
"""

from .config_manager import ConfigManager, create_config_manager, get_config_manager
from .version_manager import ConfigVersionManager, get_version_manager

__all__ = [
    "ConfigManager",
    "create_config_manager", 
    "get_config_manager",
    "ConfigVersionManager",
    "get_version_manager",
]