from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject


class ApplicationContainer(containers.DeclarativeContainer):
    """Root container for the application, focused on Terminal dependency injection."""
    config = providers.Configuration()
    
    terminal = providers.Factory(
        'butterfly.terminal.DefaultTerminal'
    )

def configure_container(config=None):
    """Configure the dependency injection container."""
    container = ApplicationContainer()
    
    if config:
        container.config.from_dict(config)
    
    container.wire(modules=[
        'butterfly.server',
        'butterfly.terminal'
    ])
    
    return container