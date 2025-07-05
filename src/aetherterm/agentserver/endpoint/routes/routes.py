"""
Main Routes Module - Simplified Route Management

This file now serves as the main entry point for all web routes,
using a modular structure for better organization and maintainability.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

# Import API routes
from aetherterm.agentserver.endpoint.api.inventory_api import inventory_router
from aetherterm.agentserver.endpoint.api.log_processing_api import router as log_processing_router
from aetherterm.agentserver.endpoint.api.local_insights_api import router as local_insights_router
from aetherterm.agentserver.endpoint.s3_browser import router as s3_browser_router

# Import individual route modules
from .main_routes import router as main_router
from .theme_routes import router as theme_router  
from .session_routes import router as session_router
from .agent_routes import router as agent_router
from .spec_routes import router as spec_router

# Initialize main router
router = APIRouter()
log = logging.getLogger("aetherterm.routes")

# Include API routes
router.include_router(inventory_router, prefix="/api")
router.include_router(log_processing_router, prefix="/api")
router.include_router(local_insights_router, prefix="/api")
router.include_router(s3_browser_router)

# Include web routes (main pages, themes, sessions, agents, specs)
router.include_router(main_router, tags=["Main"])
router.include_router(theme_router, tags=["Theme"])
router.include_router(session_router, tags=["Session"])
router.include_router(agent_router, tags=["Agent"])
router.include_router(spec_router, tags=["Specification"])

# AI Service Test Endpoints
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    stream: bool = False

@router.post("/api/ai/test-chat")
async def test_ai_chat(request: ChatRequest):
    """Test AI chat completion with LMStudio."""
    try:
        from aetherterm.agentserver.infrastructure.config.di_container import get_container
        
        container = get_container()
        ai_service = container.infrastructure.ai_service()
        
        # Check if AI service is available
        is_available = await ai_service.is_available()
        if not is_available:
            return {
                "error": f"AI service ({ai_service.provider}) is not available",
                "provider": ai_service.provider,
                "url": getattr(ai_service, 'lmstudio_url', None)
            }
        
        # Convert messages
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Get response
        response_text = ""
        async for chunk in ai_service.chat_completion(messages, stream=request.stream):
            response_text += chunk
        
        return {
            "response": response_text,
            "provider": ai_service.provider,
            "model": ai_service.model,
            "status": "success"
        }
        
    except Exception as e:
        log.error(f"AI test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/ai/status")
async def ai_service_status():
    """Get AI service status."""
    try:
        from aetherterm.agentserver.infrastructure.config.di_container import get_container
        
        container = get_container()
        ai_service = container.infrastructure.ai_service()
        
        is_available = await ai_service.is_available()
        
        return {
            "provider": ai_service.provider,
            "model": ai_service.model,
            "url": getattr(ai_service, 'lmstudio_url', None),
            "available": is_available,
            "status": "ready" if is_available else "unavailable"
        }
        
    except Exception as e:
        log.error(f"AI status error: {e}")
        return {
            "error": str(e),
            "status": "error"
        }


