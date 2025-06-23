#!/usr/bin/env python3
"""
Test OpenTelemetry configuration and functionality
Tests telemetry setup without running the full server
"""

import os
import sys
import logging
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_telemetry_imports():
    """Test that telemetry modules can be imported."""
    print("🧪 Testing OpenTelemetry imports...")
    
    try:
        import opentelemetry
        print("✅ opentelemetry core imported")
    except ImportError as e:
        print(f"❌ opentelemetry core import failed: {e}")
        return False
    
    try:
        from opentelemetry import trace
        print("✅ opentelemetry.trace imported")
    except ImportError as e:
        print(f"❌ opentelemetry.trace import failed: {e}")
        return False
    
    try:
        from opentelemetry.sdk.trace import TracerProvider
        print("✅ TracerProvider imported")
    except ImportError as e:
        print(f"❌ TracerProvider import failed: {e}")
        return False
    
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        print("✅ OTLPSpanExporter imported")
    except ImportError as e:
        print(f"❌ OTLPSpanExporter import failed: {e}")
        return False
    
    return True


def test_telemetry_config():
    """Test telemetry configuration."""
    print("\n🔧 Testing telemetry configuration...")
    
    try:
        from aetherterm.agentserver.telemetry.config import TelemetryConfig, configure_telemetry
        
        # Test configuration from environment
        config = TelemetryConfig.from_env()
        print(f"✅ TelemetryConfig created")
        print(f"   Enabled: {config.enabled}")
        print(f"   Service name: {config.service_name}")
        print(f"   Service version: {config.service_version}")
        print(f"   Traces endpoint: {config.otlp_traces_endpoint}")
        print(f"   Logs endpoint: {config.otlp_logs_endpoint}")
        print(f"   Username: {'***' if config.username else None}")
        print(f"   Debug mode: {config.debug}")
        print(f"   Sample rate: {config.sample_rate}")
        
        return config
        
    except Exception as e:
        print(f"❌ Error testing telemetry config: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_telemetry_initialization():
    """Test telemetry initialization."""
    print("\n🚀 Testing telemetry initialization...")
    
    try:
        from aetherterm.agentserver.telemetry.config import configure_telemetry
        
        # Test with disabled telemetry
        config = configure_telemetry()
        print(f"✅ Telemetry configured with enabled={config.enabled}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing telemetry: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_socket_instrumentation():
    """Test Socket.IO instrumentation."""
    print("\n🔌 Testing Socket.IO instrumentation...")
    
    try:
        from aetherterm.agentserver.telemetry.socket_instrumentation import (
            SocketIOInstrumentation,
            get_socketio_instrumentation,
            instrument_socketio_handler
        )
        
        # Test instrumentation creation
        instrumentation = SocketIOInstrumentation()
        print("✅ SocketIOInstrumentation created")
        
        # Test global instance
        global_inst = get_socketio_instrumentation()
        print("✅ Global instrumentation instance retrieved")
        
        # Test decorator
        @instrument_socketio_handler("test_event")
        async def test_handler(sid, data):
            return "test"
        
        print("✅ Instrumentation decorator applied")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Socket.IO instrumentation: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_otlp_exporter():
    """Test Generic OTLP exporter."""
    print("\n📊 Testing Generic OTLP exporter...")
    
    try:
        from aetherterm.agentserver.telemetry.exporter import GenericOTLPExporter
        
        # Test exporter creation (with dummy config)
        exporter = GenericOTLPExporter(
            endpoint="http://localhost:4318/v1/traces",
            headers={"Authorization": "Bearer test-token"}
        )
        print("✅ GenericOTLPExporter created")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing OpenObserve exporter: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trace_creation():
    """Test trace creation."""
    print("\n🔍 Testing trace creation...")
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        
        # Set up a simple tracer
        resource = Resource.create({SERVICE_NAME: "test-service"})
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        tracer = trace.get_tracer(__name__)
        
        # Create a test span
        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test.attribute", "test_value")
            span.add_event("test_event", {"event.data": "test"})
            print("✅ Test span created and finished")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating test trace: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_environment_variables():
    """Test environment variable configuration."""
    print("\n🌍 Testing environment variables...")
    
    env_vars = [
        "OTEL_ENABLED",
        "OTEL_SERVICE_NAME",
        "OTEL_SERVICE_VERSION",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT", 
        "OTEL_EXPORTER_OTLP_HEADERS",
        "OTEL_DEBUG",
        "OTEL_SAMPLE_RATE",
    ]
    
    configured_vars = 0
    for var in env_vars:
        value = os.getenv(var)
        if value:
            configured_vars += 1
            # Hide sensitive values
            if "PASSWORD" in var or "USERNAME" in var or "HEADERS" in var:
                display_value = "***"
            else:
                display_value = value
            print(f"   {var}: {display_value}")
        else:
            print(f"   {var}: Not set")
    
    print(f"\n📊 {configured_vars}/{len(env_vars)} environment variables configured")
    
    if configured_vars == 0:
        print("💡 To enable telemetry, set environment variables:")
        print("   export OTEL_ENABLED=true")
        print("   export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4318/v1/traces")
        print("   export OTEL_EXPORTER_OTLP_HEADERS='Authorization=Bearer your-token'")
    
    return configured_vars > 0


def main():
    """Main test function."""
    print("🔭 OpenTelemetry Configuration Test")
    print("=" * 50)
    
    # Run tests
    results = {}
    
    print("\n1️⃣ Testing OpenTelemetry Dependencies")
    results["imports"] = test_telemetry_imports()
    
    if results["imports"]:
        print("\n2️⃣ Testing Configuration")
        config = test_telemetry_config()
        results["config"] = config is not None
        
        print("\n3️⃣ Testing Initialization")
        results["init"] = test_telemetry_initialization()
        
        print("\n4️⃣ Testing Socket.IO Instrumentation")
        results["socket"] = test_socket_instrumentation()
        
        print("\n5️⃣ Testing OTLP Exporter")
        results["exporter"] = test_otlp_exporter()
        
        print("\n6️⃣ Testing Trace Creation")
        results["traces"] = test_trace_creation()
    else:
        print("❌ Skipping other tests due to import failures")
        results.update({
            "config": False,
            "init": False,
            "socket": False,
            "exporter": False,
            "traces": False
        })
    
    print("\n7️⃣ Testing Environment Configuration")
    results["env"] = test_environment_variables()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {test_name.capitalize()}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    # Recommendations
    print("\n💡 Recommendations:")
    
    if not results["imports"]:
        print("   1. Install OpenTelemetry dependencies:")
        print("      uv sync  # Core dependencies include OpenTelemetry")
    elif not results["env"]:
        print("   1. Configure environment variables:")
        print("      cp .env.example .env")
        print("      # Edit .env with your OTLP backend credentials")
    elif passed == total:
        print("   ✅ All tests passed! Telemetry is ready to use.")
        print("   🚀 Start AetherTerm with: OTEL_ENABLED=true make run-agentserver")
    else:
        print("   ⚠️ Some tests failed. Check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)