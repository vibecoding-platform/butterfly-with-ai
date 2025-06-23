"""
Generic OTLP Exporter for OpenTelemetry
Vendor-agnostic exporter for OTLP-compatible backends (Jaeger, Grafana, DataDog, etc.)
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional, Sequence
import requests

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk._logs import LogData

logger = logging.getLogger(__name__)


class GenericOTLPExporter(SpanExporter):
    """
    Generic OTLP exporter for traces
    Works with any OTLP-compatible backend (Jaeger, Grafana Cloud, DataDog, etc.)
    """
    
    def __init__(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "aetherterm-otlp-exporter/1.0.0",
        }
        
        if headers:
            self.headers.update(headers)
        
        # Use the endpoint as-is (should be complete OTLP endpoint)
        self.traces_endpoint = self.endpoint
        
        logger.info(f"🔭 Generic OTLP exporter initialized: {self.traces_endpoint}")
    
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export spans to OTLP-compatible backend"""
        if not spans:
            return SpanExportResult.SUCCESS
        
        try:
            # Convert spans to OTLP format
            otlp_data = self._convert_spans_to_otlp(spans)
            
            # Send to OTLP endpoint
            response = requests.post(
                self.traces_endpoint,
                headers=self.headers,
                data=json.dumps(otlp_data),
                timeout=self.timeout,
            )
            
            if response.status_code in [200, 202]:
                logger.debug(f"✅ Exported {len(spans)} spans to OTLP backend")
                return SpanExportResult.SUCCESS
            else:
                logger.error(
                    f"❌ Failed to export spans: HTTP {response.status_code} - {response.text}"
                )
                return SpanExportResult.FAILURE
                
        except Exception as e:
            logger.error(f"❌ Error exporting spans to OTLP backend: {e}")
            return SpanExportResult.FAILURE
    
    def shutdown(self) -> None:
        """Shutdown the exporter"""
        logger.info("🔭 Generic OTLP exporter shutdown")
    
    def _convert_spans_to_otlp(self, spans: Sequence[ReadableSpan]) -> Dict[str, Any]:
        """Convert spans to OTLP format"""
        otlp_spans = []
        
        for span in spans:
            # Convert span to OTLP format
            otlp_span = {
                "traceId": f"{span.context.trace_id:032x}",
                "spanId": f"{span.context.span_id:016x}",
                "name": span.name,
                "kind": span.kind.value,
                "startTimeUnixNano": str(span.start_time),
                "endTimeUnixNano": str(span.end_time),
                "attributes": self._convert_attributes(span.attributes),
                "status": {
                    "code": span.status.status_code.value,
                    "message": span.status.description or "",
                },
            }
            
            # Add parent span ID if available
            if span.parent and span.parent.span_id:
                otlp_span["parentSpanId"] = f"{span.parent.span_id:016x}"
            
            # Add events
            if span.events:
                otlp_span["events"] = [
                    {
                        "timeUnixNano": str(event.timestamp),
                        "name": event.name,
                        "attributes": self._convert_attributes(event.attributes),
                    }
                    for event in span.events
                ]
            
            # Add links
            if span.links:
                otlp_span["links"] = [
                    {
                        "traceId": f"{link.context.trace_id:032x}",
                        "spanId": f"{link.context.span_id:016x}",
                        "attributes": self._convert_attributes(link.attributes),
                    }
                    for link in span.links
                ]
            
            otlp_spans.append(otlp_span)
        
        # Create OTLP resource spans structure
        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {
                                "key": "service.name",
                                "value": {"stringValue": "aetherterm-backend"}
                            },
                            {
                                "key": "service.version",
                                "value": {"stringValue": "1.0.0"}
                            },
                            {
                                "key": "telemetry.sdk.name",
                                "value": {"stringValue": "opentelemetry"}
                            },
                            {
                                "key": "telemetry.sdk.language",
                                "value": {"stringValue": "python"}
                            },
                        ]
                    },
                    "instrumentationLibrarySpans": [
                        {
                            "instrumentationLibrary": {
                                "name": "aetherterm.socketio",
                                "version": "1.0.0"
                            },
                            "spans": otlp_spans
                        }
                    ]
                }
            ]
        }
    
    def _convert_attributes(self, attributes: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert attributes to OTLP format"""
        if not attributes:
            return []
        
        otlp_attributes = []
        for key, value in attributes.items():
            attr = {"key": key}
            
            if isinstance(value, str):
                attr["value"] = {"stringValue": value}
            elif isinstance(value, int):
                attr["value"] = {"intValue": str(value)}
            elif isinstance(value, float):
                attr["value"] = {"doubleValue": value}
            elif isinstance(value, bool):
                attr["value"] = {"boolValue": value}
            else:
                # Convert to string for other types
                attr["value"] = {"stringValue": str(value)}
            
            otlp_attributes.append(attr)
        
        return otlp_attributes


class GenericOTLPLogExporter(LogExporter):
    """
    Generic OTLP exporter for logs
    """
    
    def __init__(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "aetherterm-otlp-log-exporter/1.0.0",
        }
        
        if headers:
            self.headers.update(headers)
        
        # Use the endpoint as-is (should be complete OTLP logs endpoint)
        self.logs_endpoint = self.endpoint
        
        logger.info(f"📝 Generic OTLP log exporter initialized: {self.logs_endpoint}")
    
    def export(self, batch: Sequence[LogData]) -> LogExportResult:
        """Export logs to OTLP-compatible backend"""
        if not batch:
            return LogExportResult.SUCCESS
        
        try:
            # Convert logs to OpenObserve format
            log_records = []
            
            for log_data in batch:
                log_record = {
                    "timestamp": log_data.log_record.timestamp,
                    "level": self._get_log_level(log_data.log_record.severity_text),
                    "message": log_data.log_record.body,
                    "service": "aetherterm-backend",
                }
                
                # Add trace context if available
                if log_data.log_record.trace_id:
                    log_record["trace_id"] = f"{log_data.log_record.trace_id:032x}"
                if log_data.log_record.span_id:
                    log_record["span_id"] = f"{log_data.log_record.span_id:016x}"
                
                # Add attributes
                if log_data.log_record.attributes:
                    for key, value in log_data.log_record.attributes.items():
                        log_record[key] = value
                
                log_records.append(log_record)
            
            # Send to OTLP endpoint
            response = requests.post(
                self.logs_endpoint,
                headers=self.headers,
                data=json.dumps(log_records),
                timeout=self.timeout,
            )
            
            if response.status_code in [200, 202]:
                logger.debug(f"✅ Exported {len(log_records)} logs to OTLP backend")
                return LogExportResult.SUCCESS
            else:
                logger.error(
                    f"❌ Failed to export logs: HTTP {response.status_code} - {response.text}"
                )
                return LogExportResult.FAILURE
                
        except Exception as e:
            logger.error(f"❌ Error exporting logs to OTLP backend: {e}")
            return LogExportResult.FAILURE
    
    def shutdown(self) -> None:
        """Shutdown the exporter"""
        logger.info("📝 Generic OTLP log exporter shutdown")
    
    def _get_log_level(self, severity_text: Optional[str]) -> str:
        """Convert severity text to log level"""
        if not severity_text:
            return "INFO"
        
        severity_text = severity_text.upper()
        if "ERROR" in severity_text:
            return "ERROR"
        elif "WARN" in severity_text:
            return "WARN"
        elif "DEBUG" in severity_text:
            return "DEBUG"
        else:
            return "INFO"