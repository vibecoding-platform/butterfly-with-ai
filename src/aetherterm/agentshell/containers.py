"""
依存性注入コンテナ

dependency-injectorを使用して、設定の切り替えや
動的なモジュールローディングに対応します。
新しいパッケージ構成に対応。
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Type

from dependency_injector import containers, providers

from .config import WrapperConfig
from aetherterm.config import ConfigManager, get_config_manager
from .controller.terminal_controller import TerminalController
from .observability import DistributedTracer, StructuredLogger, TelemetryManager
from .service.ai_service import AIService
from .service.session_service import SessionService
from .service.telemetry_service import TelemetryService

logger = logging.getLogger(__name__)


class EnvironmentConfig:
    """環境別設定管理"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def get_current_environment(cls) -> str:
        """現在の環境を取得"""
        return os.getenv("AETHERTERM_ENV", cls.DEVELOPMENT).lower()

    @classmethod
    def is_development(cls) -> bool:
        """開発環境かどうか"""
        return cls.get_current_environment() == cls.DEVELOPMENT

    @classmethod
    def is_staging(cls) -> bool:
        """ステージング環境かどうか"""
        return cls.get_current_environment() == cls.STAGING

    @classmethod
    def is_production(cls) -> bool:
        """本番環境かどうか"""
        return cls.get_current_environment() == cls.PRODUCTION


class PluginRegistry:
    """プラグインレジストリ"""

    def __init__(self):
        self._plugins: Dict[str, Type] = {}
        self._instances: Dict[str, Any] = {}

    def register_plugin(self, name: str, plugin_class: Type) -> None:
        """プラグインを登録"""
        self._plugins[name] = plugin_class
        logger.debug(f"プラグインを登録しました: {name}")

    def get_plugin_class(self, name: str) -> Optional[Type]:
        """プラグインクラスを取得"""
        return self._plugins.get(name)

    def create_plugin_instance(self, name: str, *args, **kwargs) -> Optional[Any]:
        """プラグインインスタンスを作成"""
        plugin_class = self.get_plugin_class(name)
        if plugin_class:
            instance = plugin_class(*args, **kwargs)
            self._instances[name] = instance
            return instance
        return None

    def get_plugin_instance(self, name: str) -> Optional[Any]:
        """プラグインインスタンスを取得"""
        return self._instances.get(name)

    def list_plugins(self) -> Dict[str, Type]:
        """登録済みプラグイン一覧を取得"""
        return self._plugins.copy()


class WrapperContainer(containers.DeclarativeContainer):
    """ラッパープログラムの依存性注入コンテナ（環境別設定・プラグイン対応）"""

    # 設定プロバイダー
    config = providers.Configuration()

    # 設定ファイルパスプロバイダー
    config_path = providers.Configuration()

    # 環境設定プロバイダー
    environment = providers.Singleton(EnvironmentConfig)

    # プラグインレジストリプロバイダー
    plugin_registry = providers.Singleton(PluginRegistry)

    # OpenTelemetryテレメトリー管理プロバイダー
    telemetry_manager = providers.Singleton(
        TelemetryManager,
        service_name=config.telemetry.service_name,
        service_version=config.telemetry.service_version,
        environment=providers.Factory(lambda: EnvironmentConfig.get_current_environment()),
        otlp_endpoint=config.telemetry.otlp_endpoint,
        enable_console_export=providers.Factory(lambda: EnvironmentConfig.is_development()),
    )

    # 構造化ロガープロバイダー
    structured_logger = providers.Factory(
        StructuredLogger,
        name="aetherterm.shell",
        level=config.logging.level,
        enable_console=True,
        enable_file=providers.Factory(lambda: not EnvironmentConfig.is_development()),
        file_path=config.logging.file_path,
        enable_tracing=config.telemetry.enable_tracing,
    )

    # 分散トレーサープロバイダー
    distributed_tracer = providers.Singleton(
        DistributedTracer,
        service_name=config.telemetry.service_name,
    )

    # ログ設定プロバイダー
    logging_provider = providers.Resource(lambda cfg: cfg.setup_logging(), config.provided)

    # テレメトリー管理プロバイダー（既存）
    telemetry_service = providers.Singleton(
        TelemetryService,
        config=providers.Factory(lambda telemetry_config: telemetry_config, config.telemetry),
    )

    # セッション管理プロバイダー（AetherTerm同期対応）
    session_service = providers.Singleton(
        SessionService,
        config=config.session,
        aetherterm_server_url=config.aetherterm_sync.server_url,
    )

    # AI連携プロバイダー（条件付き）
    ai_service = providers.Singleton(AIService, config=config.ai_service)

    # ターミナル監視コントローラーファクトリー（セッションIDごとに作成）
    terminal_controller_factory = providers.Factory(
        TerminalController,
        config=config.monitor,
        ai_service=ai_service,
        session_service=session_service,
        telemetry_service=telemetry_service,
    )

    # 環境別設定プロバイダー
    @providers.Factory
    def environment_specific_config():
        """環境別の設定を提供"""
        env = EnvironmentConfig.get_current_environment()

        if env == EnvironmentConfig.DEVELOPMENT:
            return {
                "debug": True,
                "log_level": "DEBUG",
                "enable_console_export": True,
                "enable_file_logging": False,
                "ai_timeout": 30,
                "session_timeout": 3600,  # 1時間
            }
        elif env == EnvironmentConfig.STAGING:
            return {
                "debug": False,
                "log_level": "INFO",
                "enable_console_export": True,
                "enable_file_logging": True,
                "ai_timeout": 15,
                "session_timeout": 1800,  # 30分
            }
        else:  # PRODUCTION
            return {
                "debug": False,
                "log_level": "WARNING",
                "enable_console_export": False,
                "enable_file_logging": True,
                "ai_timeout": 10,
                "session_timeout": 900,  # 15分
            }


class WrapperApplication:
    """
    ラッパーアプリケーションクラス

    dependency-injectorを使用した依存性管理と
    動的な設定切り替えに対応
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.container = WrapperContainer()
        self.config_path = config_path or Path(__file__).parent / "wrapper.toml"
        self._initialized = False

    async def initialize(self) -> None:
        """アプリケーションを初期化"""
        if self._initialized:
            return

        logger.info("ラッパーアプリケーションを初期化します")

        # 設定を読み込み
        await self._load_configuration()

        # ログ設定を適用
        await self.container.logging_provider()

        # テレメトリーを初期化
        telemetry_service = await self.container.telemetry_service()
        telemetry_service.initialize()

        # セッション管理を開始
        session_service = await self.container.session_service()
        await session_service.start()

        # AetherTerm同期を有効化（設定されている場合）
        if self.container.config.aetherterm_sync.enable_sync():
            session_service.enable_aetherterm_sync(
                self.container.config.aetherterm_sync.server_url()
            )

        # AI連携を開始（有効な場合）
        if self.container.config.enable_ai():
            ai_service = await self.container.ai_service()
            await ai_service.start()

        self._initialized = True
        logger.info("ラッパーアプリケーションの初期化が完了しました")

    async def shutdown(self) -> None:
        """アプリケーションを終了"""
        if not self._initialized:
            return

        logger.info("ラッパーアプリケーションを終了します")

        try:
            # AI連携を停止
            if self.container.config.enable_ai():
                ai_service = await self.container.ai_service()
                await ai_service.stop()

            # セッション管理を停止
            session_service = await self.container.session_service()
            await session_service.stop()

            # テレメトリーをシャットダウン
            telemetry_service = await self.container.telemetry_service()
            telemetry_service.shutdown()

        except Exception as e:
            logger.error(f"アプリケーション終了中にエラーが発生しました: {e}")

        self._initialized = False
        logger.info("ラッパーアプリケーションの終了が完了しました")

    async def _load_configuration(self) -> None:
        """設定を読み込み（共通設定 + AgentShell固有設定）"""
        try:
            # 共通設定を読み込み
            config_manager = get_config_manager()
            common_config = config_manager.get_config_data()
            
            # AgentShell固有設定を読み込み（存在する場合）
            wrapper_config = None
            if self.config_path.exists():
                wrapper_config = WrapperConfig.load_from_file(self.config_path)
                wrapper_config.apply_environment_overrides()

            # コンテナに設定を注入（共通設定 + AgentShell固有設定）
            ai_config = common_config.get("ai", {}).get("chat", {})
            config_dict = {
                # 共通設定から取得
                "debug": common_config.get("development", {}).get("verbose_logging", False),
                "enable_ai": common_config.get("features", {}).get("ai_enabled", True),
                "ai_service": {
                    "endpoint": ai_config.get("api_endpoint", ""),
                    "api_key": ai_config.get("api_key", ""),
                    "timeout": ai_config.get("timeout", 30),
                    "max_retries": ai_config.get("max_retries", 3),
                    "model": ai_config.get("model", "claude-3-5-sonnet-20241022"),
                },
                "monitor": {
                    "buffer_size": wrapper_config.monitor.buffer_size if wrapper_config else 1024,
                    "poll_interval": wrapper_config.monitor.poll_interval if wrapper_config else 0.1,
                    "max_history": wrapper_config.monitor.max_history if wrapper_config else 1000,
                    "enable_output_capture": wrapper_config.monitor.enable_output_capture if wrapper_config else True,
                    "enable_input_capture": wrapper_config.monitor.enable_input_capture if wrapper_config else True,
                },
                "session": {
                    "session_timeout": wrapper_config.session.session_timeout if wrapper_config else 3600,
                    "max_sessions": wrapper_config.session.max_sessions if wrapper_config else 10,
                    "cleanup_interval": wrapper_config.session.cleanup_interval if wrapper_config else 300,
                    "enable_persistence": wrapper_config.session.enable_persistence if wrapper_config else True,
                },
                "logging": {
                    "level": common_config.get("logging", {}).get("level", "info"),
                    "format": wrapper_config.logging.format if wrapper_config else "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "file_path": common_config.get("logging", {}).get("file_path", "logs/agentshell.log"),
                    "max_file_size": common_config.get("logging", {}).get("max_file_size", "10MB"),
                    "backup_count": common_config.get("logging", {}).get("backup_count", 5),
                },
                "telemetry": {
                    "service_name": wrapper_config.telemetry.service_name if wrapper_config else "aetherterm-agentshell",
                    "service_version": wrapper_config.telemetry.service_version if wrapper_config else "0.1.0",
                    "environment": wrapper_config.telemetry.environment if wrapper_config else "development",
                    "otlp_endpoint": wrapper_config.telemetry.otlp_endpoint if wrapper_config else "",
                    "enable_tracing": wrapper_config.telemetry.enable_tracing if wrapper_config else False,
                    "enable_metrics": wrapper_config.telemetry.enable_metrics if wrapper_config else False,
                    "enable_log_instrumentation": wrapper_config.telemetry.enable_log_instrumentation if wrapper_config else False,
                    "trace_sample_rate": wrapper_config.telemetry.trace_sample_rate if wrapper_config else 1.0,
                    "metrics_export_interval": wrapper_config.telemetry.metrics_export_interval if wrapper_config else 60,
                },
                "aetherterm_sync": {
                    "server_url": common_config.get("server", {}).get("host", "localhost") + ":" + str(common_config.get("server", {}).get("port", 57575)),
                    "enable_sync": wrapper_config.aetherterm_sync.enable_sync if wrapper_config else True,
                    "sync_interval": wrapper_config.aetherterm_sync.sync_interval if wrapper_config else 30,
                    "reconnection_attempts": wrapper_config.aetherterm_sync.reconnection_attempts if wrapper_config else 5,
                    "reconnection_delay": wrapper_config.aetherterm_sync.reconnection_delay if wrapper_config else 5,
                },
                # AgentShell固有設定
                "wrapper_socket_path": wrapper_config.wrapper_socket_path if wrapper_config else "/tmp/agentshell.sock",
            }
            
            # AgentShell固有設定で上書き（存在する場合）
            if wrapper_config:
                # 固有設定で上書きしたい項目があれば追加
                pass
                
            self.container.config.from_dict(config_dict)

            # 設定パスも注入
            self.container.config_path.from_value(str(self.config_path))

            logger.debug(f"設定を読み込みました: {self.config_path}")

        except Exception as e:
            logger.error(f"設定の読み込みに失敗しました: {e}")
            raise

    def create_terminal_controller(self, session_id: str) -> TerminalController:
        """
        ターミナル監視コントローラーインスタンスを作成

        Args:
            session_id: セッションID

        Returns:
            TerminalController: ターミナル監視コントローラーインスタンス
        """
        return self.container.terminal_controller_factory(session_id=session_id)

    async def get_session_service(self) -> SessionService:
        """セッション管理サービスインスタンスを取得"""
        return await self.container.session_service()

    async def get_ai_service(self) -> Optional[AIService]:
        """AI連携サービスインスタンスを取得"""
        if self.container.config.enable_ai():
            return await self.container.ai_service()
        return None

    async def get_telemetry_service(self) -> TelemetryService:
        """テレメトリーサービスインスタンスを取得"""
        return await self.container.telemetry_service()

    def reload_configuration(self, new_config_path: Optional[Path] = None) -> None:
        """
        設定を動的に再読み込み

        Args:
            new_config_path: 新しい設定ファイルパス
        """
        if new_config_path:
            self.config_path = new_config_path

        logger.info(f"設定を再読み込みします: {self.config_path}")

        # 設定を再読み込み（非同期処理は別途必要）
        # 実際の実装では、既存のサービスを停止してから再起動する必要があります
        logger.warning("設定の動的再読み込みは実装中です")

    def get_config_value(self, key: str, default=None):
        """
        設定値を動的に取得

        Args:
            key: 設定キー（ドット記法対応）
            default: デフォルト値

        Returns:
            設定値
        """
        try:
            keys = key.split(".")
            value = self.container.config

            for k in keys:
                value = getattr(value, k)()

            return value
        except Exception:
            return default

    def is_initialized(self) -> bool:
        """初期化済みかどうかを確認"""
        return self._initialized


# グローバルアプリケーションインスタンス
_app_instance: Optional[WrapperApplication] = None


def get_application(config_path: Optional[Path] = None) -> WrapperApplication:
    """
    アプリケーションインスタンスを取得（シングルトン）

    Args:
        config_path: 設定ファイルパス

    Returns:
        WrapperApplication: アプリケーションインスタンス
    """
    global _app_instance

    if _app_instance is None:
        _app_instance = WrapperApplication(config_path)

    return _app_instance


def reset_application() -> None:
    """アプリケーションインスタンスをリセット（テスト用）"""
    global _app_instance
    _app_instance = None
