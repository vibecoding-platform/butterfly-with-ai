# AetherTerm OpenTelemetry Integration Setup

This document explains how to set up OpenTelemetry tracing and logging for AetherTerm, with integration to OpenObserve Cloud and Grafana.

## Overview

AetherTerm now includes comprehensive OpenTelemetry instrumentation that provides:

- **End-to-end tracing** between frontend (Vue.js) and backend (Python)
- **Socket.IO event tracking** with request-response correlation
- **Real-time monitoring** with OpenObserve Cloud
- **Grafana dashboards** for visualization
- **Alerting** for performance and error monitoring

## Architecture

```
Frontend (Vue.js)     Backend (Python)      OpenObserve Cloud     Grafana
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ OpenObserveSink │──▶│ Socket.IO       │──▶│ Traces & Logs   │──▶│ Dashboards      │
│ Trace Context   │   │ Instrumentation │   │ OTLP Endpoint   │   │ Alerts          │
│ B3 Propagation  │   │ FastAPI Auto    │   │ Stream: traces  │   │ Visualizations  │
└─────────────────┘   └─────────────────┘   └─────────────────┘   └─────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
# Python dependencies are already included in pyproject.toml
uv sync

# Frontend dependencies are already included
cd frontend && npm install
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Enable OpenTelemetry
OTEL_ENABLED=true

# Service Information
OTEL_SERVICE_NAME=aetherterm-backend
OTEL_SERVICE_VERSION=1.0.0

# OpenObserve Cloud (get these from your dashboard)
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://your-org.openobserve.ai/v1/traces
OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=https://your-org.openobserve.ai/v1/logs/aetherterm-logs
OTEL_EXPORTER_OTLP_USERNAME=your-username
OTEL_EXPORTER_OTLP_PASSWORD=your-password

# Frontend Configuration
VITE_OPENOBSERVE_ENDPOINT=https://your-org.openobserve.ai
VITE_OPENOBSERVE_ORG=your-organization
VITE_OPENOBSERVE_USER=your-username
VITE_OPENOBSERVE_PASS=your-password
```

### 3. Build and Run

```bash
# Build frontend with telemetry
cd frontend && npm run build
cd .. && make build-frontend

# Start AetherTerm with telemetry enabled
make run-agentserver ARGS="--host=localhost --port=57575 --debug"
```

### 4. Verify Setup

```bash
# Run the tracing test
python scripts/test_tracing.py
```

## Detailed Configuration

### Backend Configuration

The Python backend uses OpenTelemetry with the following components:

#### Dependencies (pyproject.toml)
```toml
dependencies = [
    # OpenTelemetry Core
    "opentelemetry-api>=1.20.0",
    "opentelemetry-sdk>=1.20.0",
    
    # Instrumentation
    "opentelemetry-instrumentation-fastapi>=0.41b0",
    "opentelemetry-instrumentation-socketio>=0.41b0",
    "opentelemetry-instrumentation-logging>=0.41b0",
    
    # Exporters
    "opentelemetry-exporter-otlp>=1.20.0",
    "opentelemetry-exporter-otlp-proto-http>=1.20.0",
    
    # Propagators
    "opentelemetry-propagator-b3>=1.20.0",
]
```

#### Environment Variables
```env
# Core Settings
OTEL_ENABLED=true                           # Enable/disable telemetry
OTEL_SERVICE_NAME=aetherterm-backend        # Service identifier
OTEL_SERVICE_VERSION=1.0.0                 # Version tag

# OpenObserve Endpoints
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://your-org.openobserve.ai/v1/traces
OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=https://your-org.openobserve.ai/v1/logs/aetherterm-logs
OTEL_EXPORTER_OTLP_USERNAME=your-username
OTEL_EXPORTER_OTLP_PASSWORD=your-password

# Advanced Settings
OTEL_DEBUG=false                            # Debug mode
OTEL_SAMPLE_RATE=1.0                       # Sampling rate (0.0-1.0)
DEPLOYMENT_ENV=development                  # Environment tag
```

### Frontend Configuration

The frontend uses a custom OpenObserve sink with OTLP-compatible format:

#### Environment Variables (.env)
```env
VITE_OPENOBSERVE_ENDPOINT=https://your-org.openobserve.ai
VITE_OPENOBSERVE_ORG=your-organization
VITE_OPENOBSERVE_USER=your-username
VITE_OPENOBSERVE_PASS=your-password
```

#### Integration
The frontend automatically instruments Socket.IO events and correlates them with backend traces using B3 propagation headers.

## Instrumented Components

### Backend (Python)

#### Socket.IO Events
All Socket.IO event handlers are instrumented with `@instrument_socketio_handler()`:

```python
@instrument_socketio_handler("terminal:create")
async def terminal_create(sid, data):
    # Automatically traced with:
    # - Request/response correlation
    # - Timing metrics
    # - Error handling
    # - Trace context propagation
```

#### FastAPI Routes
FastAPI routes are automatically instrumented via `FastAPIInstrumentor`.

#### Logging
Python logging is integrated with OpenTelemetry for automatic trace correlation.

### Frontend (Vue.js)

#### Socket.IO Events
All Socket.IO operations are traced via `OpenObserveSink`:

```typescript
// Automatic tracing for:
// - emit() calls
// - Response correlation
// - Connection status
// - Error handling
// - Timeout detection
```

## Monitoring & Observability

### Traces Captured

1. **Socket.IO Operations**
   - Event emissions (frontend → backend)
   - Event handling (backend processing)
   - Response correlation
   - Connection lifecycle

2. **Terminal Operations**
   - Terminal creation
   - Input/output streams
   - Resize operations
   - Session management

3. **AI Interactions**
   - Chat messages
   - Command analysis
   - Streaming responses

4. **Workspace Management**
   - Tab creation/switching
   - Pane splitting/closing
   - State synchronization

### Metrics Available

- Request rates and response times
- Error rates and types
- Active sessions and connections
- Trace correlation success rates
- Resource utilization

### Log Integration

- Structured logging with trace correlation
- Error tracking with stack traces
- Performance monitoring
- Debug information

## Grafana Dashboard

Import the dashboard from `grafana/dashboards/aetherterm-socketio-tracing.json`:

### Panels Include:
- Socket.IO request rate
- Response time percentiles
- Frontend-backend trace correlation
- Events by type
- Error rates
- Terminal operations timeline
- Active sessions/clients
- Slow request logs

### Variables:
- Service filter
- Event type filter

## Alerting

Import alerts from `grafana/alerts/socketio-alerts.yaml`:

### Alerts Include:
- High error rate (>5%)
- High response time (>2s)
- Trace correlation issues
- Service downtime
- Terminal creation failures
- High pending requests

### Notification Channels:
- Slack integration
- Email notifications

## Testing

### Manual Testing

1. **Start AetherTerm with telemetry enabled**
2. **Open browser and interact with terminals**
3. **Check OpenObserve for traces**
4. **View Grafana dashboard**

### Automated Testing

Run the comprehensive test suite:

```bash
python scripts/test_tracing.py
```

This script:
- Connects to AetherTerm
- Performs various Socket.IO operations
- Generates traces with correlation IDs
- Verifies traces in OpenObserve
- Reports success/failure rates

## Performance Considerations

### Sampling
Configure sampling to control overhead:
```env
OTEL_SAMPLE_RATE=0.1  # Sample 10% of traces
```

### Batching
Traces and logs are batched for efficiency:
- Batch size: 512 spans/logs
- Export interval: 5 seconds
- Queue size: 2048 items

### Resource Usage
- Minimal CPU overhead (<1%)
- Memory usage: ~10MB additional
- Network: Compressed OTLP format

## Troubleshooting

### Common Issues

1. **No traces appearing in OpenObserve**
   - Check OTEL_ENABLED=true
   - Verify endpoint URLs
   - Check authentication credentials
   - Review backend logs for export errors

2. **Frontend traces not correlating**
   - Ensure frontend environment variables are set
   - Check browser console for sink errors
   - Verify B3 headers in network tab

3. **High overhead**
   - Reduce sampling rate
   - Increase batch size
   - Check for infinite trace loops

### Debug Mode

Enable debug logging:
```env
OTEL_DEBUG=true
```

This provides detailed information about:
- Trace export attempts
- Instrumentation status
- Correlation success/failure
- Performance metrics

### Log Analysis

Check these log patterns:

```bash
# Successful trace export
grep "Exported.*traces to OpenObserve" logs/

# Correlation issues
grep "Failed to extract trace context" logs/

# Performance problems
grep "slow response" logs/
```

## Advanced Configuration

### Custom Attributes

Add custom attributes to traces:

```python
from opentelemetry import trace

span = trace.get_current_span()
span.set_attribute("user.id", user_id)
span.set_attribute("terminal.type", "bash")
```

### Custom Metrics

Add custom metrics:

```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__)
request_counter = meter.create_counter("socketio_custom_requests")
request_counter.add(1, {"event_type": "terminal_create"})
```

### Different Exporters

Switch to other exporters:

```env
# Jaeger
OTEL_EXPORTER_JAEGER_ENDPOINT=http://localhost:14268/api/traces

# Console (for debugging)
OTEL_TRACES_EXPORTER=console
OTEL_LOGS_EXPORTER=console
```

## Security Considerations

1. **Credentials**: Store OpenObserve credentials securely
2. **Sampling**: Use sampling in production to limit data exposure
3. **Sanitization**: Sensitive data is automatically filtered
4. **Network**: Use HTTPS endpoints for data export

## Support

For issues and questions:
1. Check this documentation
2. Review logs in debug mode
3. Run the test script
4. Check OpenObserve and Grafana configurations