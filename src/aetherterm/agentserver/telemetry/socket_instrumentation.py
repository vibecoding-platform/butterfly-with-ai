"""
Socket.IO OpenTelemetry Instrumentation
Custom instrumentation for Socket.IO events to integrate with frontend tracing
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.util.http import get_excluded_urls

logger = logging.getLogger(__name__)


class SocketIOInstrumentation:
    """Socket.IO OpenTelemetry instrumentation"""
    
    def __init__(self, tracer_name: str = "aetherterm.socketio"):
        self.tracer = trace.get_tracer(tracer_name)
        self.enabled = True
        self._excluded_events = {
            "connect", "disconnect", "ping", "pong"
        }
    
    def instrument_event_handler(self, event_name: str) -> Callable:
        """
        Decorator to instrument Socket.IO event handlers
        
        Usage:
            @socketio_instrumentation.instrument_event_handler("terminal:create")
            async def terminal_create(sid, data):
                ...
        """
        def decorator(func: Callable) -> Callable:
            if not self.enabled or event_name in self._excluded_events:
                return func
            
            @wraps(func)
            async def wrapper(sid: str, data: Dict[str, Any] = None, *args, **kwargs):
                # Extract trace context from data if available
                trace_context = self._extract_trace_context(data)
                
                # Create span for this Socket.IO event
                with self.tracer.start_as_current_span(
                    name=f"socketio.{event_name}",
                    kind=trace.SpanKind.SERVER,
                    context=trace_context,
                ) as span:
                    try:
                        # Set span attributes
                        self._set_span_attributes(span, event_name, sid, data)
                        
                        # Track request timing
                        start_time = time.time()
                        
                        # Call the original handler
                        result = await func(sid, data, *args, **kwargs)
                        
                        # Calculate duration
                        duration_ms = (time.time() - start_time) * 1000
                        span.set_attribute("socketio.duration_ms", duration_ms)
                        span.set_attribute("socketio.success", True)
                        
                        # Set success status
                        span.set_status(Status(StatusCode.OK))
                        
                        return result
                        
                    except Exception as e:
                        # Record error
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.set_attribute("socketio.success", False)
                        span.set_attribute("socketio.error", str(e))
                        
                        # Re-raise the exception
                        raise
            
            return wrapper
        return decorator
    
    def instrument_emit(self, sio_instance) -> None:
        """Instrument Socket.IO emit method"""
        if not self.enabled:
            return
        
        original_emit = sio_instance.emit
        
        async def instrumented_emit(event: str, data: Any = None, to: Any = None, 
                                  room: Any = None, skip_sid: Any = None, 
                                  namespace: str = None, callback: Callable = None,
                                  **kwargs):
            
            if event in self._excluded_events:
                return await original_emit(
                    event, data, to=to, room=room, skip_sid=skip_sid,
                    namespace=namespace, callback=callback, **kwargs
                )
            
            with self.tracer.start_as_current_span(
                name=f"socketio.emit.{event}",
                kind=trace.SpanKind.CLIENT,
            ) as span:
                try:
                    # Set span attributes
                    span.set_attribute("socketio.event", event)
                    span.set_attribute("socketio.direction", "outbound")
                    
                    if room:
                        span.set_attribute("socketio.room", str(room))
                    if to:
                        span.set_attribute("socketio.to", str(to))
                    if namespace:
                        span.set_attribute("socketio.namespace", namespace)
                    
                    # Add trace context to data if it's a dict
                    if isinstance(data, dict):
                        data = self._inject_trace_context(data, span)
                    
                    # Track timing
                    start_time = time.time()
                    
                    # Call original emit
                    result = await original_emit(
                        event, data, to=to, room=room, skip_sid=skip_sid,
                        namespace=namespace, callback=callback, **kwargs
                    )
                    
                    # Calculate duration
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("socketio.duration_ms", duration_ms)
                    span.set_attribute("socketio.success", True)
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("socketio.success", False)
                    raise
        
        # Replace the emit method
        sio_instance.emit = instrumented_emit
        logger.info("🔧 Socket.IO emit method instrumented")
    
    def create_child_span(self, operation_name: str, parent_span_context: Optional[Any] = None) -> trace.Span:
        """Create a child span for Socket.IO operations"""
        return self.tracer.start_span(
            name=f"socketio.{operation_name}",
            context=parent_span_context,
            kind=trace.SpanKind.INTERNAL,
        )
    
    def _extract_trace_context(self, data: Optional[Dict[str, Any]]) -> Optional[Any]:
        """Extract trace context from Socket.IO data"""
        if not data or not isinstance(data, dict):
            return None
        
        trace_headers = data.get("_trace")
        if not trace_headers:
            return None
        
        try:
            # Extract B3 trace context
            from opentelemetry.propagators.b3 import B3MultiFormat
            from opentelemetry import context as context_api
            
            propagator = B3MultiFormat()
            
            # Convert to headers format
            headers = {}
            if "traceId" in trace_headers:
                headers["b3"] = f"{trace_headers['traceId']}-{trace_headers.get('spanId', '')}"
            
            # Extract context
            context = propagator.extract(headers)
            return context
            
        except Exception as e:
            logger.debug(f"Failed to extract trace context: {e}")
            return None
    
    def _inject_trace_context(self, data: Dict[str, Any], span: trace.Span) -> Dict[str, Any]:
        """Inject trace context into Socket.IO data"""
        try:
            span_context = span.get_span_context()
            if not span_context or not span_context.is_valid:
                return data
            
            # Create a copy to avoid modifying original data
            data_copy = dict(data)
            
            # Inject trace context
            data_copy["_trace"] = {
                "traceId": f"{span_context.trace_id:032x}",
                "spanId": f"{span_context.span_id:016x}",
                "sampled": span_context.trace_flags.sampled,
            }
            
            return data_copy
            
        except Exception as e:
            logger.debug(f"Failed to inject trace context: {e}")
            return data
    
    def _set_span_attributes(self, span: trace.Span, event_name: str, 
                           sid: str, data: Optional[Dict[str, Any]]) -> None:
        """Set standard span attributes for Socket.IO events"""
        span.set_attribute("socketio.event", event_name)
        span.set_attribute("socketio.direction", "inbound")
        span.set_attribute("socketio.client_id", sid)
        
        if data:
            # Add request ID if available
            if "_requestId" in data:
                span.set_attribute("socketio.request_id", data["_requestId"])
            
            # Add terminal ID if available
            if "terminalId" in data:
                span.set_attribute("socketio.terminal_id", data["terminalId"])
            
            # Add session ID if available
            if "sessionId" in data:
                span.set_attribute("socketio.session_id", data["sessionId"])
            
            # Add tab/pane IDs if available
            if "tabId" in data:
                span.set_attribute("socketio.tab_id", data["tabId"])
            if "paneId" in data:
                span.set_attribute("socketio.pane_id", data["paneId"])
            
            # Data size
            try:
                import json
                data_size = len(json.dumps(data))
                span.set_attribute("socketio.data_size_bytes", data_size)
            except:
                pass


# Global instrumentation instance
_instrumentation: Optional[SocketIOInstrumentation] = None


def get_socketio_instrumentation() -> SocketIOInstrumentation:
    """Get the global Socket.IO instrumentation instance"""
    global _instrumentation
    if _instrumentation is None:
        _instrumentation = SocketIOInstrumentation()
    return _instrumentation


def instrument_socketio_handler(event_name: str) -> Callable:
    """Decorator for instrumenting Socket.IO event handlers"""
    return get_socketio_instrumentation().instrument_event_handler(event_name)