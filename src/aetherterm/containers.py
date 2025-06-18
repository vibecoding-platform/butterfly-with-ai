import logging
import os

import socketio
from dependency_injector import containers, providers
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


class ApplicationContainer(containers.DeclarativeContainer):
    """Root container for the application, focused on Terminal dependency injection."""

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

    # Socket.IO path provider
    socketio_path = providers.Callable(
        lambda uri_root_path: f"{uri_root_path}/socket.io" if uri_root_path else "/socket.io",
        uri_root_path=config.uri_root_path,
    )

    # AI Assistance Logic Provider
    ai_assistance_service = providers.Selector(
        config.ai_mode,
        streaming=providers.Factory(object),  # Placeholder for streaming AI service
        sentence_by_sentence=providers.Factory(
            object
        ),  # Placeholder for sentence-by-sentence AI service
    )

    # Terminal factory removed - terminals are created directly in socket handlers
    # to avoid dependency injection complexity with multiple required parameters


def configure_container(config=None):
    """Configure the dependency injection container."""
    container = ApplicationContainer()

    # Set default values first
    defaults = {
        "uri_root_path": "",
        "unsecure": False,
        "debug": False,
        "more": False,
        "ai_mode": "streaming",
    }

    # Merge defaults with provided config
    final_config = defaults.copy()
    if config:
        final_config.update(config)

    container.config.from_dict(final_config)

    container.wire(
        modules=[
            "aetherterm.routes",
            "aetherterm.server",
            "aetherterm.socket_handlers",
        ]
    )

    return container
