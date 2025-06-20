import logging
import os

import socketio
from dependency_injector import containers, providers
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from aetherterm.agentserver.ai_services import create_ai_service, set_ai_service
from aetherterm.config import ConfigManager, create_config_manager


def _create_fastapi_app(static_path):
    """Create FastAPI app with static files mounted."""
    app = FastAPI()
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    return app


class ApplicationContainer(containers.DeclarativeContainer):
    """Root container for the application, focused on Terminal dependency injection."""

    # Configuration Manager
    config_manager = providers.Singleton(create_config_manager)
    
    # DI Configuration from ConfigManager
    config = providers.Configuration()

    # Logging configuration
    logging_level = providers.Callable(
        lambda debug, more: (
            logging.DEBUG if more else (logging.INFO if debug else logging.WARNING)
        ),
        debug=config.debug,
        more=config.more,
    )

    # Socket.IO server provider
    sio = providers.Singleton(
        socketio.AsyncServer,
        async_mode="asgi",
        cors_allowed_origins="*",  # Default to allow all origins, can be configured
    )

    # Static files path
    static_files_path = providers.Singleton(
        lambda: os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    )

    # FastAPI application provider for static files and HTTP routes
    fastapi_app = providers.Singleton(
        lambda static_path: _create_fastapi_app(static_path),
        static_path=static_files_path,
    )

    # Combined ASGI application (Socket.IO + FastAPI)
    app = providers.Singleton(
        socketio.ASGIApp,
        socketio_server=sio,
        other_asgi_app=fastapi_app,
        socketio_path=providers.Callable(
            lambda uri_root_path: f"{uri_root_path}/socket.io" if uri_root_path else "/socket.io",
            uri_root_path=config.uri_root_path,
        ),
    )

    # AI Service Provider
    ai_service = providers.Factory(
        create_ai_service,
        provider=config.ai_provider,
        api_key=config.ai_api_key,
        model=config.ai_model,
    )

    # Terminal factory removed - terminals are created directly in socket handlers
    # to avoid dependency injection complexity with multiple required parameters


def configure_container(config=None):
    """Configure the dependency injection container."""
    container = ApplicationContainer()

    # Initialize ConfigManager and load TOML configuration
    config_manager = container.config_manager()
    
    # Get configuration from ConfigManager
    di_config = config_manager.create_dependency_injector_config()
    
    # Override with any provided config
    if config:
        di_config.update(config)
    
    container.config.from_dict(di_config)

    container.wire(
        modules=[
            "aetherterm.agentserver.routes",
            "aetherterm.agentserver.server",
            "aetherterm.agentserver.socket_handlers",
        ]
    )

    # Initialize AI service
    try:
        ai_service_instance = container.ai_service()
        set_ai_service(ai_service_instance)
        logging.getLogger("aetherterm.agentserver.containers").info(f"AI service initialized with provider: {di_config.get('ai_provider', 'unknown')}")
    except Exception as e:
        logging.getLogger("aetherterm.agentserver.containers").error(f"Failed to initialize AI service: {e}")
        # Fallback to mock service
        from aetherterm.agentserver.ai_services import MockAIService
        set_ai_service(MockAIService())
    
    # Log configuration summary
    config_summary = config_manager.get_config_summary()
    logging.getLogger("aetherterm.agentserver.containers").info(f"Configuration loaded: {config_summary['config_file']} (schema: {config_summary['schema_version']})")
    
    return container
