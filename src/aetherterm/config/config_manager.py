"""
Configuration Management System

DependencyInjector統合のConfiguration Manager implementation.
TOML設定ファイルの読み込み、バリデーション、バージョン管理を行います。
"""

import logging
import os
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dependency_injector import providers

from .version_manager import ConfigVersionManager, get_version_manager

logger = logging.getLogger(__name__)


class ConfigManager:
    """設定管理クラス - DependencyInjectorと統合"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        version_manager: Optional[ConfigVersionManager] = None,
    ):
        """
        ConfigManagerを初期化

        Args:
            config_path: 設定ファイルのパス
            version_manager: バージョンマネージャー（省略時は自動取得）
        """
        self.config_path = config_path or self._get_default_config_path()
        self.version_manager = version_manager or get_version_manager()
        self._config_data: Optional[Dict[str, Any]] = None
        self._validation_errors: List[str] = []

    def _get_default_config_path(self) -> str:
        """デフォルト設定ファイルパスを取得"""
        # 実行ディレクトリからの相対パス、または絶対パスを試行
        candidates = [
            "aetherterm.toml",
            "src/aetherterm/config/aetherterm.toml.default",
            os.path.join(os.path.dirname(__file__), "aetherterm.toml.default"),
        ]
        
        for candidate in candidates:
            if os.path.exists(candidate):
                logger.debug(f"Found config file: {candidate}")
                return candidate
                
        # フォールバック: デフォルト設定ファイル
        fallback = os.path.join(os.path.dirname(__file__), "aetherterm.toml.default")
        logger.warning(f"No config file found in candidates, using fallback: {fallback}")
        return fallback

    def load_config(self) -> Tuple[bool, List[str]]:
        """
        設定ファイルを読み込み、バリデーションを実行

        Returns:
            Tuple[bool, List[str]]: (成功, エラーメッセージ一覧)
        """
        errors = []
        
        try:
            # ファイル読み込み
            if not os.path.exists(self.config_path):
                errors.append(f"Configuration file not found: {self.config_path}")
                return False, errors

            with open(self.config_path, "rb") as f:
                config_data = tomllib.load(f)

            logger.info(f"Loaded configuration from: {self.config_path}")

            # スキーマバージョン検証
            is_valid, schema_version, validation_warnings = self.version_manager.validate_config_schema_version(config_data)
            
            if not is_valid:
                errors.extend(validation_warnings)
                return False, errors

            # 警告があれば記録
            if validation_warnings:
                for warning in validation_warnings:
                    logger.warning(f"Configuration warning: {warning}")

            self._config_data = config_data
            self._validation_errors = []
            
            logger.info(f"Configuration loaded successfully (schema version: {schema_version})")
            return True, []

        except tomllib.TOMLDecodeError as e:
            error_msg = f"TOML parsing error in {self.config_path}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return False, errors

        except Exception as e:
            error_msg = f"Failed to load configuration: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return False, errors

    def get_config_data(self) -> Dict[str, Any]:
        """設定データを取得（読み込み済みの場合）"""
        if self._config_data is None:
            success, errors = self.load_config()
            if not success:
                logger.error(f"Failed to load config: {errors}")
                return {}
        
        return self._config_data or {}

    def get_section(self, section_name: str) -> Dict[str, Any]:
        """指定されたセクションの設定を取得"""
        config = self.get_config_data()
        return config.get(section_name, {})

    def get_value(self, key_path: str, default: Any = None) -> Any:
        """
        ドット記法で設定値を取得

        Args:
            key_path: "section.key" or "section.subsection.key" 形式
            default: デフォルト値

        Returns:
            設定値またはデフォルト値
        """
        config = self.get_config_data()
        
        keys = key_path.split(".")
        current = config
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            logger.debug(f"Configuration key not found: {key_path}, using default: {default}")
            return default

    def is_feature_enabled(self, feature_name: str) -> bool:
        """機能の有効/無効を確認"""
        # features.{feature_name} の値を確認
        return self.get_value(f"features.{feature_name}", False)

    def get_ai_config(self) -> Dict[str, Any]:
        """AI関連の設定を取得"""
        return self.get_section("ai")

    def get_server_config(self) -> Dict[str, Any]:
        """サーバー関連の設定を取得"""
        return self.get_section("server")

    def get_security_config(self) -> Dict[str, Any]:
        """セキュリティ関連の設定を取得"""
        return self.get_section("security")

    def get_ui_config(self) -> Dict[str, Any]:
        """UI関連の設定を取得"""
        return self.get_section("ui")

    def get_logging_config(self) -> Dict[str, Any]:
        """ログ関連の設定を取得"""
        return self.get_section("logging")

    def get_performance_config(self) -> Dict[str, Any]:
        """パフォーマンス関連の設定を取得"""
        return self.get_section("performance")

    def get_integrations_config(self) -> Dict[str, Any]:
        """外部統合関連の設定を取得"""
        return self.get_section("integrations")

    def create_dependency_injector_config(self) -> Dict[str, Any]:
        """DependencyInjector用の設定辞書を作成"""
        config = self.get_config_data()
        if not config:
            logger.warning("No configuration loaded, returning empty config")
            return {}

        # DependencyInjectorで使用するための平坦化された設定を作成
        di_config = {}
        
        # サーバー設定
        server = self.get_server_config()
        di_config.update({
            "host": server.get("host", "localhost"),
            "port": server.get("port", 57575),
            "debug": server.get("debug", False),
            "more": server.get("more", False),
            "unminified": server.get("unminified", False),
        })

        # セキュリティ設定
        security = self.get_security_config()
        di_config.update({
            "unsecure": security.get("unsecure", False),
            "login": security.get("login", False),
            "ssl_version": security.get("ssl_version", "auto"),
        })

        # AI設定
        ai = self.get_ai_config()
        ai_chat = ai.get("chat", {})
        di_config.update({
            "ai_enabled": self.is_feature_enabled("ai_enabled"),
            "ai_provider": ai_chat.get("provider", "mock"),
            "ai_model": ai_chat.get("model", "claude-3-5-sonnet-20241022"),
            "ai_api_key": ai_chat.get("api_key") or os.getenv("ANTHROPIC_API_KEY"),
            "ai_mode": "streaming",  # 固定値
            "ai_max_messages": ai_chat.get("max_messages", 100),
            "ai_auto_context": ai_chat.get("auto_context", True),
        })

        # その他の設定
        di_config.update({
            "uri_root_path": "",  # 固定値
            "multi_tab_enabled": self.is_feature_enabled("multi_tab_enabled"),
            "supervisor_panel_enabled": self.is_feature_enabled("supervisor_panel_enabled"),
            "dev_tools_enabled": self.is_feature_enabled("dev_tools_enabled"),
        })

        return di_config

    def reload_config(self) -> Tuple[bool, List[str]]:
        """設定ファイルを再読み込み"""
        logger.info("Reloading configuration...")
        self._config_data = None
        return self.load_config()

    def get_schema_version(self) -> Optional[str]:
        """現在の設定のスキーマバージョンを取得"""
        config = self.get_config_data()
        return config.get("schema_version")

    def validate_schema_compatibility(self) -> Tuple[bool, List[str]]:
        """スキーマの互換性を検証"""
        config = self.get_config_data()
        if not config:
            return False, ["No configuration loaded"]
            
        return self.version_manager.validate_config_schema_version(config)

    def get_config_summary(self) -> Dict[str, Any]:
        """設定の概要情報を取得"""
        config = self.get_config_data()
        version_info = self.version_manager.get_version_summary()
        
        return {
            "config_file": self.config_path,
            "schema_version": config.get("schema_version", "unknown"),
            "loaded": config is not None,
            "validation_errors": self._validation_errors,
            "version_manager": version_info,
            "feature_flags": {
                "ai_enabled": self.is_feature_enabled("ai_enabled"),
                "multi_tab_enabled": self.is_feature_enabled("multi_tab_enabled"), 
                "supervisor_panel_enabled": self.is_feature_enabled("supervisor_panel_enabled"),
                "dev_tools_enabled": self.is_feature_enabled("dev_tools_enabled"),
            }
        }


# DependencyInjectorプロバイダー
def create_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """ConfigManagerインスタンスを作成（DI用ファクトリー）"""
    manager = ConfigManager(config_path=config_path)
    success, errors = manager.load_config()
    
    if not success:
        logger.error(f"Failed to initialize ConfigManager: {errors}")
        # エラーでも継続（デフォルト値で動作）
    
    return manager


# グローバルConfigManagerインスタンス
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """グローバルConfigManagerを取得"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = create_config_manager()
    return _global_config_manager


def set_config_manager(manager: ConfigManager) -> None:
    """グローバルConfigManagerを設定"""
    global _global_config_manager
    _global_config_manager = manager