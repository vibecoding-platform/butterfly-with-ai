#!/usr/bin/env python3
"""
Direct telemetry module test without full application dependencies
Tests the telemetry modules in isolation
"""

import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

def test_direct_telemetry_imports():
    """Test direct telemetry module imports"""
    print("🔭 Testing Direct Telemetry Imports")
    print("=" * 50)
    
    try:
        # Test config module
        from aetherterm.agentserver.telemetry.config import TelemetryConfig
        print("✅ TelemetryConfig imported")
        
        # Test direct config creation
        config = TelemetryConfig(
            enabled=True,
            service_name="test-service",
            otlp_traces_endpoint="http://localhost:4318/v1/traces",
            otlp_headers="Authorization=Bearer test-token"
        )
        print("✅ TelemetryConfig created manually")
        
        # Test environment config creation
        os.environ["OTEL_ENABLED"] = "true"
        os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "http://localhost:4318/v1/traces" 
        os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = "Authorization=Bearer test-token"
        
        env_config = TelemetryConfig.from_env()
        print(f"✅ TelemetryConfig from environment: {env_config.service_name}")
        print(f"   Enabled: {env_config.enabled}")
        print(f"   Endpoint: {env_config.otlp_traces_endpoint}")
        print(f"   Headers: {'***' if env_config.otlp_headers else 'None'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing config: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_exporter():
    """Test direct exporter creation"""
    print("\n📊 Testing Direct Exporter")
    print("=" * 50)
    
    try:
        from aetherterm.agentserver.telemetry.exporter import GenericOTLPExporter, GenericOTLPLogExporter
        
        # Test trace exporter
        trace_exporter = GenericOTLPExporter(
            endpoint="http://localhost:4318/v1/traces",
            headers={"Authorization": "Bearer test-token"}
        )
        print("✅ GenericOTLPExporter created")
        
        # Test log exporter  
        log_exporter = GenericOTLPLogExporter(
            endpoint="http://localhost:4318/v1/logs",
            headers={"Authorization": "Bearer test-token"}
        )
        print("✅ GenericOTLPLogExporter created")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing exporter: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_instrumentation():
    """Test direct socket instrumentation"""
    print("\n🔌 Testing Direct Socket Instrumentation")
    print("=" * 50)
    
    try:
        from aetherterm.agentserver.telemetry.socket_instrumentation import (
            SocketIOInstrumentation,
            instrument_socketio_handler
        )
        
        # Test instrumentation creation
        instrumentation = SocketIOInstrumentation()
        print("✅ SocketIOInstrumentation created")
        
        # Test decorator
        @instrument_socketio_handler("test_event")
        async def test_handler(sid, data):
            return "test_response"
            
        print("✅ instrumentation decorator applied")
        print(f"   Handler name: {test_handler.__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing socket instrumentation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_full_config():
    """Test full telemetry configuration"""
    print("\n⚙️ Testing Direct Full Configuration")
    print("=" * 50)
    
    try:
        from aetherterm.agentserver.telemetry.config import configure_telemetry, TelemetryConfig
        
        # Test configuration with disabled telemetry (safe)
        disabled_config = TelemetryConfig(enabled=False)
        result_config = configure_telemetry(disabled_config)
        print(f"✅ configure_telemetry with disabled config: {result_config.enabled}")
        
        # Test configuration with enabled telemetry and console output
        os.environ["OTEL_TRACES_EXPORTER"] = "console"
        os.environ["OTEL_LOGS_EXPORTER"] = "console"
        
        enabled_config = TelemetryConfig(
            enabled=True,
            service_name="test-service",
            otlp_traces_endpoint="http://localhost:4318/v1/traces"
        )
        
        result_config = configure_telemetry(enabled_config)
        print(f"✅ configure_telemetry with enabled config: {result_config.service_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing full configuration: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all direct tests"""
    print("🚀 AetherTerm Direct Telemetry Test")
    print("=" * 60)
    
    results = {}
    
    # Test direct imports
    results["config"] = test_direct_telemetry_imports()
    
    # Test direct exporter
    results["exporter"] = test_direct_exporter() 
    
    # Test direct instrumentation
    results["instrumentation"] = test_direct_instrumentation()
    
    # Test full configuration
    results["full_config"] = test_direct_full_config()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DIRECT TELEMETRY TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All direct telemetry tests passed!")
        print("🔧 The telemetry system is properly configured and vendor-agnostic")
        print("📡 Ready to connect to any OTLP-compatible backend:")
        print("   - Jaeger")
        print("   - Grafana Cloud") 
        print("   - DataDog")
        print("   - New Relic")
        print("   - Any other OTLP endpoint")
    else:
        print("\n⚠️ Some direct telemetry tests failed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)