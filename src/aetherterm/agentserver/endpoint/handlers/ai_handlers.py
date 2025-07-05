"""
AI Chat & Log Search WebSocket Handlers - Interface Layer

Simplified AI handlers for chat and log search functionality only.
"""

import logging
from datetime import datetime
# from dependency_injector.wiring import inject, Provide

from aetherterm.agentserver.infrastructure.external.ai_service import AIService
from aetherterm.agentserver.infrastructure.config.di_container import get_container
from aetherterm.agentserver.domain.entities.terminals.asyncio_terminal import AsyncioTerminal

log = logging.getLogger("aetherterm.handlers.ai")


async def ai_chat_message(sid, data, sio_instance):
    """Handle AI chat message requests."""
    container = get_container()
    ai_service = container.infrastructure.ai_service()
    try:
        message = data.get("message", "")
        session_id = data.get("session_id")
        stream = data.get("stream", False)
        
        if not message:
            await sio_instance.emit("error", {"message": "Message required"}, room=sid)
            return
        
        # Prepare context from terminal session if available
        terminal_context = {}
        if session_id and session_id in AsyncioTerminal.sessions:
            terminal = AsyncioTerminal.sessions[session_id]
            terminal_context = {
                "recent_history": terminal.history[-1000:] if terminal.history else "",
                "session_id": session_id,
                "working_directory": getattr(terminal, 'current_dir', '/'),
            }
        
        # Prepare messages for AI service
        messages = [{"role": "user", "content": message}]
        
        # Use AI service for chat processing
        response_generator = ai_service.chat_completion(
            messages=messages,
            terminal_context=terminal_context,
            stream=stream
        )
        
        if stream:
            # Send streaming response
            full_response = ""
            async for chunk in response_generator:
                full_response += chunk
                await sio_instance.emit("ai_chat_chunk", {
                    "chunk": chunk,
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat()
                }, room=sid)
            
            # Send final complete response
            await sio_instance.emit("ai_chat_complete", {
                "response": full_response,
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            }, room=sid)
        else:
            # Send complete response
            response = ""
            async for chunk in response_generator:
                response += chunk
            
            await sio_instance.emit("ai_chat_response", {
                "response": response,
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            }, room=sid)

    except Exception as e:
        log.error(f"Failed to process AI chat message: {e}")
        await sio_instance.emit("error", {"message": str(e)}, room=sid)


async def ai_log_search(sid, data, sio_instance):
    """Search logs using AI-enhanced matching."""
    container = get_container()
    ai_service = container.infrastructure.ai_service()
    try:
        query = data.get("query", "")
        session_id = data.get("session_id")
        limit = data.get("limit", 50)
        
        if not query:
            await sio_instance.emit("error", {"message": "Search query required"}, room=sid)
            return
        
        # Get logs from AsyncioTerminal
        recent_logs = AsyncioTerminal.get_recent_logs(limit=1000)
        
        # Filter by session if specified
        if session_id:
            recent_logs = [log for log in recent_logs if log.get("session_id") == session_id]
        
        # Use AI service for enhanced search
        search_results = await ai_service.search_logs(
            query=query,
            logs=recent_logs,
            limit=limit
        )
        
        await sio_instance.emit("ai_log_search_results", {
            "query": query,
            "results": search_results,
            "total_found": len(search_results),
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }, room=sid)

    except Exception as e:
        log.error(f"Failed to search logs: {e}")
        await sio_instance.emit("error", {"message": str(e)}, room=sid)


async def ai_search_suggestions(sid, data, sio_instance):
    """Get search term suggestions for log search."""
    container = get_container()
    ai_service = container.infrastructure.ai_service()
    try:
        partial_query = data.get("partial_query", "")
        
        # Use AI service for search suggestions
        suggestions = await ai_service.suggest_search_terms(partial_query)
        
        await sio_instance.emit("ai_search_suggestions", {
            "partial_query": partial_query,
            "suggestions": suggestions,
            "timestamp": datetime.utcnow().isoformat()
        }, room=sid)

    except Exception as e:
        log.error(f"Failed to get search suggestions: {e}")
        await sio_instance.emit("error", {"message": str(e)}, room=sid)


# All other AI functions removed - focusing only on chat and log search
# Use local insights API for analytics and suggestions