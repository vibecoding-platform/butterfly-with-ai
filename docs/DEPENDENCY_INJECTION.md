# Dependency Injection in AetherTerm

AetherTerm uses the `dependency-injector` library to manage dependencies and configuration throughout the application.

## Architecture

### Container (`src/aetherterm/containers.py`)

The `ApplicationContainer` class defines all the application's dependencies:

- **config**: Configuration provider that holds all application settings
- **logging_level**: Computed based on debug/more flags
- **sio**: Socket.IO server instance (singleton)
- **static_files_path**: Path to static files
- **socketio_path**: Computed Socket.IO path based on URI root path
- **ai_assistance_service**: Selector for AI assistance mode

### Usage

#### 1. From AetherTerm CLI

The application can be started using the `aetherterm` command with either uvicorn or hypercorn:

```bash
# Using uvicorn (default)
aetherterm --host 0.0.0.0 --port 8080

# Using hypercorn
aetherterm --server hypercorn --host 0.0.0.0 --port 8080

# With SSL
aetherterm --host myserver.com --port 443

# Generate SSL certificates
aetherterm --generate-certs --host myserver.com
```

#### 2. From ASGI Server (uvicorn/hypercorn)

The application provides an ASGI factory function that can be called directly:

```bash
# Using uvicorn
uvicorn aetherterm.server:create_asgi_app --factory --host 0.0.0.0 --port 8080

# Using hypercorn  
hypercorn aetherterm.server:create_asgi_app --factory --bind 0.0.0.0:8080
```

Configuration is passed via environment variables when using the factory:

```bash
export AETHERTERM_HOST=0.0.0.0
export AETHERTERM_PORT=8080
export AETHERTERM_DEBUG=true
export AETHERTERM_URI_ROOT_PATH=/terminal
export AETHERTERM_LOGIN=true
export AETHERTERM_AI_MODE=streaming

uvicorn aetherterm.server:create_asgi_app --factory
```

## Dependency Injection in Code

### Routes (`src/aetherterm/routes.py`)

Routes use the `@inject` decorator to access configuration:

```python
@router.get("/", response_class=HTMLResponse)
@inject
async def index(
    request: Request,
    uri_root_path: str = Provide[ApplicationContainer.config.uri_root_path],
):
    # uri_root_path is automatically injected
    ...
```

### Socket Handlers (`src/aetherterm/socket_handlers.py`)

Socket handlers access injected configuration:

```python
@inject
async def create_terminal(
    sid,
    data,
    config_login: bool = Provide[ApplicationContainer.config.login],
    config_pam_profile: str = Provide[ApplicationContainer.config.pam_profile],
    config_uri_root_path: str = Provide[ApplicationContainer.config.uri_root_path],
):
    # Configuration values are automatically injected
    ...
```

## Adding New Dependencies

To add new dependencies to the container:

1. Add the provider to `ApplicationContainer` in `containers.py`:

```python
class ApplicationContainer(containers.DeclarativeContainer):
    # ... existing providers ...
    
    my_service = providers.Singleton(
        MyService,
        config_value=config.my_config_value,
    )
```

2. Wire the module that will use the dependency:

```python
def configure_container(config=None):
    container = ApplicationContainer()
    # ... existing configuration ...
    
    container.wire(
        modules=[
            "aetherterm.routes",
            "aetherterm.server", 
            "aetherterm.socket_handlers",
            "aetherterm.my_module",  # Add your module here
        ]
    )
```

3. Use the dependency with `@inject`:

```python
from dependency_injector.wiring import Provide, inject
from aetherterm.containers import ApplicationContainer

@inject
async def my_function(
    my_service: MyService = Provide[ApplicationContainer.my_service],
):
    # my_service is automatically injected
    result = await my_service.do_something()
```

## Configuration

All configuration values are centralized in the container and can be accessed via:

- Direct injection in functions with `@inject`
- Environment variables when using the ASGI factory
- Command-line arguments when using the `aetherterm` CLI

The configuration flow:

1. CLI arguments → `main.py`/`scripts/aetherterm.py`
2. Environment variables → `create_asgi_app` factory
3. Container configuration → `configure_container`
4. Dependency injection → `@inject` decorated functions