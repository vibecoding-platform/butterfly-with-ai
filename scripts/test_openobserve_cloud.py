#!/usr/bin/env python3
"""
OpenObserve Cloud connection test
Tests telemetry data export to OpenObserve SaaS
"""

import os
import sys
import time
import json
from pathlib import Path

def test_openobserve_cloud_connection():
    """Test connection to OpenObserve Cloud"""
    print("🌩️ Testing OpenObserve Cloud Connection")
    print("=" * 50)
    
    # OpenObserve Cloud endpoint format: https://your-org.openobserve.ai
    cloud_endpoint = input("OpenObserve Cloud組織URL (例: https://your-org.openobserve.ai): ").strip()
    if not cloud_endpoint:
        cloud_endpoint = "https://demo.openobserve.ai"  # Demo endpoint
    
    username = input("ユーザー名/Email: ").strip()
    if not username:
        username = "demo@openobserve.ai"
    
    password = input("パスワード: ").strip()
    if not password:
        password = "demo123"
    
    # Set environment variables
    os.environ["OTEL_ENABLED"] = "true"
    os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{cloud_endpoint}/api/default/v1/traces"
    
    # Create Basic Auth header
    import base64
    auth_string = f"{username}:{password}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth_header}"
    
    print(f"✅ 設定完了:")
    print(f"   Endpoint: {os.environ['OTEL_EXPORTER_OTLP_TRACES_ENDPOINT']}")
    print(f"   Auth: Basic ***")
    
    return True

def test_send_sample_trace():
    """Send sample trace to OpenObserve Cloud"""
    print("\n📤 Sample Traceの送信テスト")
    print("=" * 50)
    
    try:
        import requests
        
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        headers_env = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
        
        if not endpoint:
            print("❌ OTEL_EXPORTER_OTLP_TRACES_ENDPOINT が設定されていません")
            return False
        
        # Parse headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "aetherterm-openobserve-test/1.0.0"
        }
        
        if headers_env:
            header_pairs = headers_env.split(',')
            for pair in header_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    headers[key.strip()] = value.strip()
        
        # Create test trace data in OTLP format
        trace_id = f"{int(time.time() * 1000000):032x}"
        span_id = f"{int(time.time() * 1000):016x}"
        
        otlp_data = {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "aetherterm-test"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                        {"key": "deployment.environment", "value": {"stringValue": "test"}}
                    ]
                },
                "scopeSpans": [{
                    "scope": {
                        "name": "aetherterm.socketio.test",
                        "version": "1.0.0"
                    },
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": "socketio.terminal:create",
                        "kind": 1,
                        "startTimeUnixNano": str(int(time.time() * 1000000000)),
                        "endTimeUnixNano": str(int(time.time() * 1000000000) + 100000000),
                        "attributes": [
                            {"key": "socketio.event", "value": {"stringValue": "terminal:create"}},
                            {"key": "socketio.client_id", "value": {"stringValue": "test-client-123"}},
                            {"key": "socketio.direction", "value": {"stringValue": "inbound"}},
                            {"key": "terminal.id", "value": {"stringValue": "terminal-456"}},
                            {"key": "test.timestamp", "value": {"stringValue": str(int(time.time()))}}
                        ],
                        "status": {"code": 1, "message": ""}
                    }]
                }]
            }]
        }
        
        print(f"📡 送信先: {endpoint}")
        print(f"📦 Trace ID: {trace_id}")
        print(f"📦 Span ID: {span_id}")
        
        # Send to OpenObserve Cloud
        response = requests.post(
            endpoint,
            headers=headers,
            json=otlp_data,
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code in [200, 202]:
            print("✅ トレースデータの送信に成功しました！")
            print(f"   Response: {response.text[:100] if response.text else 'Empty'}")
            
            # Show OpenObserve UI URL
            base_url = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "").replace("/api/default/v1/traces", "")
            print(f"\n🌐 OpenObserve UIでデータを確認:")
            print(f"   URL: {base_url}/web/traces")
            print(f"   Service: aetherterm-test")
            print(f"   Trace ID: {trace_id}")
            
            return True
        else:
            print(f"❌ 送信に失敗: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ エラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_opentelemetry_integration():
    """Test OpenTelemetry integration with OpenObserve Cloud"""
    print("\n🔭 OpenTelemetry統合テスト")
    print("=" * 50)
    
    try:
        # Add src to path
        src_path = Path(__file__).parent.parent / "src"
        sys.path.insert(0, str(src_path))
        
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
        
        # Configure resource
        resource = Resource.create({
            SERVICE_NAME: "aetherterm-openobserve-test",
            SERVICE_VERSION: "1.0.0",
            "deployment.environment": "test",
        })
        
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        # Configure OTLP exporter
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        headers_env = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
        
        headers = {}
        if headers_env:
            header_pairs = headers_env.split(',')
            for pair in header_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    headers[key.strip()] = value.strip()
        
        otlp_exporter = OTLPSpanExporter(
            endpoint=endpoint,
            headers=headers,
            timeout=30,
        )
        
        span_processor = BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
        )
        
        tracer_provider.add_span_processor(span_processor)
        
        # Create tracer and test span
        tracer = trace.get_tracer("aetherterm.openobserve.test", "1.0.0")
        
        print("📊 OpenTelemetry Spanを作成中...")
        
        with tracer.start_as_current_span("openobserve_integration_test") as span:
            span.set_attribute("test.type", "openobserve_cloud")
            span.set_attribute("socketio.event", "terminal:create")
            span.set_attribute("socketio.client_id", "openobserve-test-client")
            span.set_attribute("terminal.id", "openobserve-terminal-123")
            span.set_attribute("test.timestamp", str(int(time.time())))
            
            span.add_event("test_started", {
                "event.type": "openobserve_test",
                "event.message": "OpenObserve Cloud integration test"
            })
            
            # Simulate some work
            time.sleep(0.1)
            
            span.add_event("test_completed", {
                "event.result": "success",
                "event.duration": "100ms"
            })
        
        # Force export
        span_processor.force_flush(30)
        
        print("✅ OpenTelemetry Spanの送信完了")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenTelemetry統合エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🌩️ OpenObserve Cloud Telemetry Test")
    print("=" * 60)
    
    results = {}
    
    # Test connection setup
    results["setup"] = test_openobserve_cloud_connection()
    
    if results["setup"]:
        # Test manual trace export
        results["manual_export"] = test_send_sample_trace()
        
        # Test OpenTelemetry integration
        results["opentelemetry"] = test_opentelemetry_integration()
    else:
        results["manual_export"] = False
        results["opentelemetry"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 OPENOBSERVE CLOUD TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed >= 2:
        print("\n✅ OpenObserve Cloudとの接続に成功！")
        print("🔗 OpenObserve UIでトレースデータを確認してください")
        
        base_url = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "").replace("/api/default/v1/traces", "")
        if base_url:
            print(f"   📱 UI URL: {base_url}/web/traces")
            print(f"   🔍 Service: aetherterm-test, aetherterm-openobserve-test")
    else:
        print("\n⚠️ OpenObserve Cloudへの接続に問題があります")
        print("💡 認証情報やエンドポイントを確認してください")
    
    return passed >= 2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)