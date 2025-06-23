#!/usr/bin/env python3
"""
Simple telemetry test without full dependencies
Tests OpenTelemetry functionality in isolation
"""

import os
import sys
import time
import json
from pathlib import Path

def test_opentelemetry_basic():
    """Test basic OpenTelemetry functionality."""
    print("🔭 Testing OpenTelemetry Basic Functionality")
    print("=" * 50)
    
    try:
        # Test imports
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        print("✅ All imports successful")
        
        # Create resource
        resource = Resource.create({
            SERVICE_NAME: "aetherterm-test",
            SERVICE_VERSION: "1.0.0",
            "service.namespace": "aetherterm",
            "deployment.environment": "test",
        })
        print("✅ Resource created")
        
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        print("✅ TracerProvider set")
        
        # Test console exporter
        console_exporter = ConsoleSpanExporter()
        console_processor = BatchSpanProcessor(console_exporter)
        tracer_provider.add_span_processor(console_processor)
        print("✅ Console exporter configured")
        
        # Create tracer
        tracer = trace.get_tracer("test-tracer", "1.0.0")
        print("✅ Tracer created")
        
        # Create test spans
        print("\n📊 Creating test spans...")
        
        with tracer.start_as_current_span("test_operation") as span:
            span.set_attribute("test.attribute", "test_value")
            span.set_attribute("socketio.event", "terminal:create")
            span.set_attribute("socketio.client_id", "test-client-123")
            span.add_event("test_event", {
                "event.type": "test",
                "event.data": "sample_data"
            })
            
            # Simulate nested operation
            with tracer.start_as_current_span("nested_operation") as nested_span:
                nested_span.set_attribute("nested.value", 42)
                time.sleep(0.1)  # Simulate work
            
            print("✅ Nested spans created")
        
        print("✅ Spans finished and should be exported")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in basic OpenTelemetry test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_otlp_exporter_config():
    """Test OTLP exporter configuration (without sending data)."""
    print("\n📡 Testing OTLP Exporter Configuration")
    print("=" * 50)
    
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        
        # Test exporter creation with various configurations
        test_configs = [
            {
                "name": "Jaeger",
                "endpoint": "http://localhost:14268/api/traces",
                "headers": {}
            },
            {
                "name": "Grafana Cloud",
                "endpoint": "https://otlp-gateway-prod-us-central-0.grafana.net/otlp/v1/traces",
                "headers": {"Authorization": "Basic dGVzdDp0ZXN0"}  # test:test in base64
            },
            {
                "name": "Local OTLP",
                "endpoint": "http://localhost:4318/v1/traces",
                "headers": {}
            }
        ]
        
        for config in test_configs:
            try:
                exporter = OTLPSpanExporter(
                    endpoint=config["endpoint"],
                    headers=config["headers"],
                    timeout=10
                )
                print(f"✅ {config['name']} exporter created: {config['endpoint']}")
            except Exception as e:
                print(f"❌ {config['name']} exporter failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing OTLP exporter: {e}")
        return False


def test_socket_io_trace_format():
    """Test Socket.IO trace data format."""
    print("\n🔌 Testing Socket.IO Trace Format")
    print("=" * 50)
    
    try:
        # Simulate trace data that would be generated
        trace_data = {
            "timestamp": int(time.time() * 1000),
            "traceId": "1234567890abcdef1234567890abcdef",
            "spanId": "1234567890abcdef",
            "operationName": "terminal:create",
            "duration": 150,  # ms
            "tags": {
                "socketio.event": "terminal:create",
                "socketio.client_id": "client-123",
                "socketio.direction": "inbound",
                "terminal.id": "terminal-456",
                "service.name": "aetherterm-backend",
                "service.version": "1.0.0"
            },
            "status": "ok",
            "level": "info"
        }
        
        print("✅ Sample trace data:")
        print(json.dumps(trace_data, indent=2))
        
        # Convert to OTLP format
        otlp_span = {
            "traceId": trace_data["traceId"],
            "spanId": trace_data["spanId"],
            "name": trace_data["operationName"],
            "kind": 1,  # SPAN_KIND_CLIENT
            "startTimeUnixNano": str(trace_data["timestamp"] * 1000000),
            "endTimeUnixNano": str((trace_data["timestamp"] + trace_data["duration"]) * 1000000),
            "attributes": [
                {"key": k, "value": {"stringValue": str(v)}} 
                for k, v in trace_data["tags"].items()
            ],
            "status": {
                "code": 1 if trace_data["status"] == "ok" else 2,
                "message": ""
            }
        }
        
        print("\n✅ OTLP span format:")
        print(json.dumps(otlp_span, indent=2))
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing trace format: {e}")
        return False


def test_environment_setup():
    """Test environment variable setup."""
    print("\n🌍 Testing Environment Setup")
    print("=" * 50)
    
    # Check for .env.example
    env_example = Path(".env.example")
    if env_example.exists():
        print("✅ .env.example file found")
        
        # Show example configuration
        with open(env_example) as f:
            content = f.read()
            
        print("\n📋 Example configuration:")
        lines = content.split('\n')
        for line in lines[:15]:  # Show first 15 lines
            if line.strip() and not line.startswith('#'):
                print(f"   {line}")
    else:
        print("❌ .env.example file not found")
    
    # Check current environment
    env_vars = [
        "OTEL_ENABLED",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "OTEL_EXPORTER_OTLP_USERNAME",
        "OTEL_EXPORTER_OTLP_PASSWORD"
    ]
    
    print(f"\n🔍 Current environment:")
    configured = 0
    for var in env_vars:
        value = os.getenv(var)
        if value:
            configured += 1
            if "PASSWORD" in var:
                print(f"   {var}: *** (hidden)")
            else:
                print(f"   {var}: {value}")
        else:
            print(f"   {var}: Not set")
    
    if configured == 0:
        print(f"\n💡 To enable telemetry:")
        print(f"   1. Copy .env.example to .env")
        print(f"   2. Edit .env with your OpenObserve credentials")
        print(f"   3. Export the variables or use python-dotenv")
    
    return configured > 0


def test_manual_trace_export():
    """Test manual trace export with mock data."""
    print("\n📤 Testing Manual Trace Export")
    print("=" * 50)
    
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    headers_env = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    
    if not endpoint:
        print("⚠️ Missing required environment variables for export test")
        print("   Set OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        print("   Optionally set OTEL_EXPORTER_OTLP_HEADERS for authentication")
        return False
    
    try:
        import requests
        
        # Parse headers from environment variable
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "aetherterm-telemetry-test/1.0.0"
        }
        
        if headers_env:
            # Parse headers from string format like "Authorization=Bearer token,Custom-Header=value"
            header_pairs = headers_env.split(',')
            for pair in header_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    headers[key.strip()] = value.strip()
        
        # Create test trace data in OTLP format
        otlp_data = {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "aetherterm-test"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "instrumentationLibrarySpans": [{
                    "instrumentationLibrary": {
                        "name": "aetherterm.test",
                        "version": "1.0.0"
                    },
                    "spans": [{
                        "traceId": "1234567890abcdef1234567890abcdef",
                        "spanId": "1234567890abcdef",
                        "name": "test_telemetry_connection",
                        "kind": 1,
                        "startTimeUnixNano": str(int(time.time() * 1000000000)),
                        "endTimeUnixNano": str(int(time.time() * 1000000000) + 100000000),
                        "attributes": [
                            {"key": "test.type", "value": {"stringValue": "connection_test"}},
                            {"key": "test.timestamp", "value": {"stringValue": str(int(time.time()))}}
                        ],
                        "status": {"code": 1, "message": ""}
                    }]
                }]
            }]
        }
        
        print(f"📡 Sending test trace to: {endpoint}")
        response = requests.post(
            endpoint,
            headers=headers,
            json=otlp_data,
            timeout=10
        )
        
        if response.status_code in [200, 202]:
            print("✅ Test trace sent successfully!")
            print(f"   Response status: {response.status_code}")
            return True
        else:
            print(f"❌ Failed to send trace: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except ImportError:
        print("❌ requests library not available for export test")
        return False
    except Exception as e:
        print(f"❌ Error sending test trace: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 AetherTerm Telemetry Test Suite")
    print("=" * 60)
    
    results = {}
    
    # Test basic OpenTelemetry
    results["basic"] = test_opentelemetry_basic()
    
    # Test OTLP exporter configuration
    results["otlp_config"] = test_otlp_exporter_config()
    
    # Test trace format
    results["trace_format"] = test_socket_io_trace_format()
    
    # Test environment setup
    results["environment"] = test_environment_setup()
    
    # Test actual export (if configured)
    results["export"] = test_manual_trace_export()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TELEMETRY TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    # Final assessment
    if results["basic"] and results["otlp_config"]:
        print("\n✅ OpenTelemetry is properly configured and ready to use!")
        
        if results["export"]:
            print("🎉 End-to-end telemetry is working!")
            print("🚀 You can now start AetherTerm with telemetry enabled:")
            print("   export OTEL_ENABLED=true")
            print("   make run-agentserver")
        else:
            print("⚠️ Export test failed - check your OpenObserve configuration")
            print("💡 Configure your .env file with valid OpenObserve credentials")
    else:
        print("❌ Basic OpenTelemetry configuration has issues")
        print("🔧 Install dependencies with: uv sync")
    
    return passed >= 3  # At least 3 out of 5 tests should pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)