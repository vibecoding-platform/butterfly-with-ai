"""
AI & Context Inference WebSocket Handlers - Interface Layer

AI chat, context inference, and analytics handlers with Dependency Injection.
"""

import logging
from datetime import datetime
from uuid import uuid4
from dependency_injector.wiring import inject, Provide

from aetherterm.agentserver.application.services.agent_service import AgentService
from aetherterm.agentserver.infrastructure.external.ai_service import AIService
from aetherterm.agentserver.infrastructure.config.di_container import MainContainer

log = logging.getLogger("aetherterm.handlers.ai")


@inject
async def ai_chat_message(
    sid, 
    data,
    sio_instance,
    ai_service: AIService = Provide[MainContainer.infrastructure.ai_service]
):
    """Handle AI chat message requests."""
    try:
        message = data.get("message", "")
        context = data.get("context", {})
        session_id = data.get("session_id")
        
        if not message:
            await sio_instance.emit("error", {"message": "Message required"}, room=sid)
            return
        
        # Use AI service for chat processing
        response = await ai_service.process_chat_message(
            message=message,
            context=context,
            session_id=session_id
        )
        
        await sio_instance.emit("ai_chat_response", {
            "response": response,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }, room=sid)

    except Exception as e:
        log.error(f"Failed to process AI chat message: {e}")
        await sio_instance.emit("error", {"message": str(e)}, room=sid)


@inject
async def context_inference_subscribe(
    sid, 
    data,
    sio_instance,
    ai_service: AIService = Provide[MainContainer.infrastructure.ai_service]
):
    """Subscribe to context inference updates."""
    try:
        session_id = data.get("session_id")
        inference_config = data.get("config", {})
        
        # Enable context inference through AI service
        result = await ai_service.enable_context_inference(
            session_id=session_id,
            config=inference_config
        )
        
        await sio_instance.emit("context_inference_subscribed", {
            "session_id": session_id,
            "status": "subscribed",
            "config": inference_config,
            "timestamp": datetime.utcnow().isoformat()
        }, room=sid)

    except Exception as e:
        log.error(f"Failed to subscribe to context inference: {e}")
        await sio_instance.emit("error", {"message": str(e)}, room=sid)


@inject
async def predict_next_commands(
    sid, 
    data,
    sio_instance,
    ai_service: AIService = Provide[MainContainer.infrastructure.ai_service]
):
    """Predict next commands based on context."""
    try:
        session_id = data.get("session_id")
        current_command = data.get("current_command", "")
        working_directory = data.get("working_directory", "/")
        command_history = data.get("history", [])
        
        # Use AI service for command prediction
        predictions = await ai_service.predict_commands(
            session_id=session_id,
            current_command=current_command,
            working_directory=working_directory,
            history=command_history
        )
        
        await sio_instance.emit("command_predictions", {
            "session_id": session_id,
            "predictions": predictions,
            "context": {
                "current_command": current_command,
                "working_directory": working_directory
            },
            "timestamp": datetime.utcnow().isoformat()
        }, room=sid)

    except Exception as e:
        log.error(f"Failed to predict commands: {e}")
        await sio_instance.emit("error", {"message": str(e)}, room=sid)


@inject
async def get_operation_analytics(
    sid, 
    data,
    sio_instance,
    ai_service: AIService = Provide[MainContainer.infrastructure.ai_service]
):
    """Get operation analytics and insights."""
    try:
        session_id = data.get("session_id")
        time_range = data.get("time_range", "1h")
        operation_types = data.get("operation_types", [])
        
        # Use AI service for analytics generation
        analytics = await ai_service.generate_analytics(
            session_id=session_id,
            time_range=time_range,
            operation_types=operation_types
        )
        
        await sio_instance.emit("operation_analytics", {
            "session_id": session_id,
            "analytics": analytics,
            "time_range": time_range,
            "timestamp": datetime.utcnow().isoformat()
        }, room=sid)

    except Exception as e:
        log.error(f"Failed to get operation analytics: {e}")
        await sio_instance.emit("error", {"message": str(e)}, room=sid)


@inject
async def training_data_feedback(
    sid, 
    data,
    sio_instance,
    ai_service: AIService = Provide[MainContainer.infrastructure.ai_service]
):
    """Provide feedback for AI model training."""
    try:
        feedback_type = data.get("type")  # "correct", "incorrect", "improvement"
        prediction_id = data.get("prediction_id")
        actual_command = data.get("actual_command")
        user_rating = data.get("rating")
        comments = data.get("comments", "")
        
        # Submit feedback to AI service
        result = await ai_service.submit_feedback(
            feedback_type=feedback_type,
            prediction_id=prediction_id,
            actual_command=actual_command,
            rating=user_rating,
            comments=comments
        )
        
        await sio_instance.emit("feedback_submitted", {
            "prediction_id": prediction_id,
            "status": "submitted",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }, room=sid)

    except Exception as e:
        log.error(f"Failed to submit training feedback: {e}")
        await sio_instance.emit("error", {"message": str(e)}, room=sid)


@inject
async def get_ai_suggestions(
    sid, 
    data,
    sio_instance,
    ai_service: AIService = Provide[MainContainer.infrastructure.ai_service]
):
    """Get AI suggestions for current context."""
    try:
        session_id = data.get("session_id")
        context_type = data.get("context_type", "command")
        current_input = data.get("current_input", "")
        
        # Get suggestions from AI service
        suggestions = await ai_service.get_suggestions(
            session_id=session_id,
            context_type=context_type,
            current_input=current_input
        )
        
        await sio_instance.emit("ai_suggestions", {
            "session_id": session_id,
            "suggestions": suggestions,
            "context_type": context_type,
            "timestamp": datetime.utcnow().isoformat()
        }, room=sid)

    except Exception as e:
        log.error(f"Failed to get AI suggestions: {e}")
        await sio_instance.emit("error", {"message": str(e)}, room=sid)