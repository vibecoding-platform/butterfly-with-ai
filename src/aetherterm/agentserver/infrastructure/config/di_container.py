"""
Dependency Injection Container - Infrastructure Layer

Clean Architecture DI container for managing service dependencies.
"""

import logging
from dependency_injector import containers, providers

from aetherterm.agentserver.application.services.workspace_service import WorkspaceService
from aetherterm.agentserver.application.services.agent_service import AgentService
from aetherterm.agentserver.application.services.report_service import ReportService
from aetherterm.agentserver.application.services.context_service import ContextService
from aetherterm.agentserver.infrastructure.external.ai_service import AIService
from aetherterm.agentserver.infrastructure.external.security_service import SecurityService
from aetherterm.agentserver.infrastructure.persistence.memory_store import MemoryStore
from aetherterm.agentserver.infrastructure.config.ssl_config import SSLConfig
from aetherterm.agentserver.infrastructure.logging.log_analyzer import LogAnalyzer


class InfrastructureContainer(containers.DeclarativeContainer):
    """Infrastructure layer services container."""
    
    config = providers.Configuration()
    
    # AI Service
    ai_service = providers.Singleton(
        AIService,
        provider=config.ai.provider.provided.as_("mock"),
        api_key=config.ai.api_key,
        model=config.ai.model.provided.as_("claude-3-5-sonnet")
    )
    
    # Security Service
    security_service = providers.Singleton(SecurityService)
    
    # Memory Store
    memory_store = providers.Singleton(MemoryStore)
    
    # SSL Configuration
    ssl_config = providers.Singleton(SSLConfig)
    
    # Log Analyzer
    log_analyzer = providers.Singleton(LogAnalyzer)


class ApplicationContainer(containers.DeclarativeContainer):
    """Application layer services container."""
    
    config = providers.Configuration()
    
    # Infrastructure dependencies
    infrastructure = providers.DependenciesContainer()
    
    # Workspace Service
    workspace_service = providers.Singleton(WorkspaceService)
    
    # Agent Service  
    agent_service = providers.Singleton(AgentService)
    
    # Report Service
    report_service = providers.Singleton(ReportService)
    
    # Context Service
    context_service = providers.Singleton(ContextService)


class MainContainer(containers.DeclarativeContainer):
    """Main application container."""
    
    config = providers.Configuration()
    
    # Infrastructure container
    infrastructure = providers.Container(
        InfrastructureContainer,
        config=config.infrastructure
    )
    
    # Application container with infrastructure dependencies
    application = providers.Container(
        ApplicationContainer,
        config=config.application,
        infrastructure=infrastructure
    )
    
    # Logging configuration
    logging_level = providers.Callable(
        lambda debug, more: (
            logging.DEBUG if more else (logging.INFO if debug else logging.WARNING)
        ),
        debug=config.debug.provided.as_(False),
        more=config.more.provided.as_(False),
    )


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