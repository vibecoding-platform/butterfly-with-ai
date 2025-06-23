"""
OpenTelemetry Configuration for AetherTerm
Configures tracing, logging, and metrics export to OTLP-compatible backends
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass

from opentelemetry import trace, _logs
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.propagators import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat

logger = logging.getLogger(__name__)


@dataclass
class TelemetryConfig:
    """OpenTelemetry configuration"""
    enabled: bool = False
    service_name: str = "aetherterm-backend"
    service_version: str = "1.0.0"
    
    # OTLP endpoint configuration  
    otlp_traces_endpoint: Optional[str] = None
    otlp_logs_endpoint: Optional[str] = None
    otlp_headers: Optional[str] = None
    
    # Additional configuration
    debug: bool = False
    sample_rate: float = 1.0
    
    @classmethod
    def from_env(cls) -> "TelemetryConfig":
        """Create configuration from environment variables"""
        return cls(
            enabled=os.getenv("OTEL_ENABLED", "false").lower() == "true",
            service_name=os.getenv("OTEL_SERVICE_NAME", "aetherterm-backend"),
            service_version=os.getenv("OTEL_SERVICE_VERSION", "1.0.0"),
            
            # OTLP endpoints
            otlp_traces_endpoint=os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"),
            otlp_logs_endpoint=os.getenv("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT"),
            otlp_headers=os.getenv("OTEL_EXPORTER_OTLP_HEADERS"),
            
            debug=os.getenv("OTEL_DEBUG", "false").lower() == "true",
            sample_rate=float(os.getenv("OTEL_SAMPLE_RATE", "1.0")),
        )


def configure_telemetry(config: Optional[TelemetryConfig] = None) -> TelemetryConfig:
    """
    Configure OpenTelemetry with OTLP backend integration
    
    Returns:
        TelemetryConfig: The configuration used
    """
    if config is None:
        config = TelemetryConfig.from_env()
    
    if not config.enabled:
        logger.info("🔭 OpenTelemetry is disabled")
        return config
    
    logger.info(f"🔭 Configuring OpenTelemetry for {config.service_name}")
    
    # Configure resource
    resource = Resource.create({
        SERVICE_NAME: config.service_name,
        SERVICE_VERSION: config.service_version,
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
        "telemetry.sdk.version": "1.20.0",
        "service.namespace": "aetherterm",
        "deployment.environment": os.getenv("DEPLOYMENT_ENV", "development"),
    })
    
    # Configure tracing
    _configure_tracing(config, resource)
    
    # Configure logging
    _configure_logging(config, resource)
    
    # Configure propagators
    set_global_textmap(B3MultiFormat())
    
    # Auto-instrument FastAPI
    _configure_instrumentation()
    
    logger.info("✅ OpenTelemetry configuration completed")
    return config


def _configure_tracing(config: TelemetryConfig, resource: Resource) -> None:
    """Configure tracing with OTLP export"""
    try:
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        # Configure OTLP trace exporter if endpoint is provided
        if config.otlp_traces_endpoint:
            headers = {}
            if config.otlp_headers:
                # Parse headers from string format like "Authorization=Bearer token,Custom-Header=value"
                header_pairs = config.otlp_headers.split(',')
                for pair in header_pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        headers[key.strip()] = value.strip()
            
            otlp_exporter = OTLPSpanExporter(
                endpoint=config.otlp_traces_endpoint,
                headers=headers,
                timeout=30,
            )
            
            span_processor = BatchSpanProcessor(
                otlp_exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                export_timeout=30000,  # 30 seconds
                schedule_delay=5000,   # 5 seconds
            )
            
            tracer_provider.add_span_processor(span_processor)
            logger.info(f"📊 OTLP trace exporter configured: {config.otlp_traces_endpoint}")
        else:
            logger.warning("⚠️ No OTLP traces endpoint configured")
            
    except Exception as e:
        logger.error(f"❌ Failed to configure tracing: {e}")


def _configure_logging(config: TelemetryConfig, resource: Resource) -> None:
    """Configure logging with OTLP export"""
    try:
        # Create logger provider
        logger_provider = LoggerProvider(resource=resource)
        _logs.set_logger_provider(logger_provider)
        
        # Configure OTLP log exporter if endpoint is provided
        if config.otlp_logs_endpoint:
            headers = {}
            if config.otlp_headers:
                # Parse headers from string format like "Authorization=Bearer token,Custom-Header=value"
                header_pairs = config.otlp_headers.split(',')
                for pair in header_pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        headers[key.strip()] = value.strip()
            
            otlp_log_exporter = OTLPLogExporter(
                endpoint=config.otlp_logs_endpoint,
                headers=headers,
                timeout=30,
            )
            
            log_processor = BatchLogRecordProcessor(
                otlp_log_exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                export_timeout=30000,  # 30 seconds
                schedule_delay=5000,   # 5 seconds
            )
            
            logger_provider.add_log_record_processor(log_processor)
            logger.info(f"📝 OTLP log exporter configured: {config.otlp_logs_endpoint}")
        else:
            logger.warning("⚠️ No OTLP logs endpoint configured")
            
    except Exception as e:
        logger.error(f"❌ Failed to configure logging: {e}")


def _configure_instrumentation() -> None:
    """Configure automatic instrumentation"""
    try:
        # Auto-instrument logging
        LoggingInstrumentor().instrument(set_logging_format=True)
        logger.info("🔧 Logging instrumentation configured")
        
        # Note: FastAPI instrumentation will be done at app creation time
        
    except Exception as e:
        logger.error(f"❌ Failed to configure instrumentation: {e}")


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance"""
    return trace.get_tracer(name)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with OpenTelemetry integration"""
    return logging.getLogger(name)