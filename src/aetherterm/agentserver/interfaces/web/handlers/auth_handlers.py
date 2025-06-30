"""
Authentication & Security WebSocket Handlers - Interface Layer

User authentication, session management, and security handlers with Dependency Injection.
"""

import logging
from datetime import datetime
from dependency_injector.wiring import inject, Provide

from aetherterm.agentserver.infrastructure.external.security_service import SecurityService
from aetherterm.agentserver.infrastructure.config.di_container import MainContainer

log = logging.getLogger("aetherterm.handlers.auth")


def get_user_info_from_environ(environ):
    """Extract user information from environment/headers."""
    user_info = {
        "remote_addr": environ.get("REMOTE_ADDR"),
        "remote_user": environ.get("HTTP_X_REMOTE_USER"),
        "forwarded_for": environ.get("HTTP_X_FORWARDED_FOR"),
        "user_agent": environ.get("HTTP_USER_AGENT"),
    }
    return user_info


@inject
def check_session_ownership(
    session_id, 
    current_user_info,
    security_service: SecurityService = Provide[MainContainer.infrastructure.security_service]
):
    """Check if the current user owns the session."""
    try:
        # Use security service for session ownership validation
        return security_service.validate_session_ownership(session_id, current_user_info)
        
    except Exception as e:
        log.error(f"Failed to check session ownership: {e}")
        return False


@inject
async def connect(
    sid, 
    environ, 
    sio_instance,
    security_service: SecurityService = Provide[MainContainer.infrastructure.security_service]
):
    """Handle client connection with authentication."""
    try:
        user_info = get_user_info_from_environ(environ)
        
        # Validate connection through security service
        is_authorized = await security_service.validate_connection(sid, user_info)
        
        if not is_authorized:
            log.warning(f"Unauthorized connection attempt from {user_info}")
            await sio_instance.disconnect(sid)
            return
        
        log.info(f"Client connected: {sid} from {user_info.get('remote_addr')}")
        await sio_instance.emit("connected", {
            "data": "Connected to AetherTerm",
            "session_id": sid,
            "timestamp": datetime.utcnow().isoformat()
        }, room=sid)

    except Exception as e:
        log.error(f"Failed to handle connection: {e}")
        await sio_instance.disconnect(sid)


@inject
async def disconnect(
    sid, 
    environ=None,
    security_service: SecurityService = Provide[MainContainer.infrastructure.security_service]
):
    """Handle client disconnection with cleanup."""
    try:
        log.info(f"Client disconnected: {sid}")
        
        # Clean up through security service
        await security_service.cleanup_session(sid)

    except Exception as e:
        log.error(f"Failed to handle disconnection: {e}")


@inject
async def validate_request(
    sid, 
    data,
    sio_instance,
    security_service: SecurityService = Provide[MainContainer.infrastructure.security_service]
):
    """Validate incoming request for security."""
    try:
        request_type = data.get("type")
        payload = data.get("payload", {})
        
        # Use security service for request validation
        is_valid = await security_service.validate_request(sid, request_type, payload)
        
        if not is_valid:
            await sio_instance.emit("error", {
                "message": "Request validation failed",
                "type": "security_error"
            }, room=sid)
            return False
            
        return True

    except Exception as e:
        log.error(f"Failed to validate request: {e}")
        return False


@inject
async def session_heartbeat(
    sid, 
    data,
    sio_instance,
    security_service: SecurityService = Provide[MainContainer.infrastructure.security_service]
):
    """Handle session heartbeat for keepalive."""
    try:
        # Update session activity through security service
        await security_service.update_session_activity(sid)
        
        await sio_instance.emit("heartbeat_ack", {
            "timestamp": datetime.utcnow().isoformat()
        }, room=sid)

    except Exception as e:
        log.error(f"Failed to handle heartbeat: {e}")


@inject
async def request_permissions(
    sid, 
    data,
    sio_instance,
    security_service: SecurityService = Provide[MainContainer.infrastructure.security_service]
):
    """Handle permission requests for sensitive operations."""
    try:
        operation = data.get("operation")
        resource = data.get("resource")
        
        # Check permissions through security service
        has_permission = await security_service.check_permission(sid, operation, resource)
        
        await sio_instance.emit("permission_response", {
            "operation": operation,
            "resource": resource,
            "granted": has_permission,
            "timestamp": datetime.utcnow().isoformat()
        }, room=sid)

    except Exception as e:
        log.error(f"Failed to check permissions: {e}")
        await sio_instance.emit("error", {"message": str(e)}, room=sid)