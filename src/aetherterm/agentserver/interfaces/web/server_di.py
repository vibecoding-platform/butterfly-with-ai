"""
Server with Dependency Injection - Interface Layer

FastAPI server setup with Clean Architecture DI integration.
"""

import logging
import os
from dependency_injector.wiring import inject, Provide

from aetherterm.agentserver.infrastructure.config.di_container import MainContainer
from aetherterm.agentserver.application import initialize_app_services
from aetherterm.agentserver.infrastructure import initialize_infra_services

log = logging.getLogger("aetherterm.server_di")


@inject
async def create_server_with_di(
    host: str = "localhost",
    port: int = 57575,
    debug: bool = False,
    container: MainContainer = Provide[MainContainer]
):
    """Create server with dependency injection setup."""
    try:
        # Configure DI container
        container.config.debug.from_value(debug)
        container.config.infrastructure.ai.provider.from_value("mock")
        container.config.infrastructure.ai.model.from_value("claude-3-5-sonnet")
        
        # Initialize services with DI
        initialize_infra_services(container.infrastructure)
        initialize_app_services(container.application)
        
        # Wire DI container
        container.wire(modules=[
            "aetherterm.agentserver.interfaces.web.socket_handlers",
            "aetherterm.agentserver.interfaces.web.routes",
        ])
        
        log.info(f"DI container initialized and wired for {host}:{port}")
        return container
        
    except Exception as e:
        log.error(f"Failed to create server with DI: {e}")
        raise


def setup_di_container() -> MainContainer:
    """Setup and return configured DI container."""
    container = MainContainer()
    
    # Basic configuration
    container.config.debug.from_value(False)
    container.config.more.from_value(False)
    
    # Infrastructure config
    container.config.infrastructure.ai.provider.from_value("mock")
    container.config.infrastructure.ai.api_key.from_value(None)
    container.config.infrastructure.ai.model.from_value("claude-3-5-sonnet")
    
    return container