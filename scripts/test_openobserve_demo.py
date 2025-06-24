#!/usr/bin/env python3
"""
OpenObserve Demo connection test
Tests telemetry data export to OpenObserve demo instance
"""

import os
import sys
import time
import json
from pathlib import Path

def setup_demo_config():
    """Setup demo OpenObserve configuration"""
    print("🌩️ OpenObserve Demo設定")
    print("=" * 50)
    
    # Demo configuration (publicly available demo instance)
    demo_endpoint = "https://api.openobserve.ai"
    demo_org = "demo"
    demo_user = "demo@openobserve.ai"
    demo_pass = "demo123"
    
    # Set environment variables for demo
    os.environ["OTEL_ENABLED"] = "true"
    os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{demo_endpoint}/api/{demo_org}/v1/traces"
    
    # Create Basic Auth header
    import base64
    auth_string = f"{demo_user}:{demo_pass}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth_header}"
    
    print(f"✅ Demo設定完了:")
    print(f"   Endpoint: {os.environ['OTEL_EXPORTER_OTLP_TRACES_ENDPOINT']}")
    print(f"   Organization: {demo_org}")
    print(f"   User: {demo_user}")
    
    return True

def test_endpoint_availability():
    """Test if OpenObserve endpoint is available"""
    print("\n🔍 Endpoint可用性テスト")
    print("=" * 50)
    
    try:
        import requests
        
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        base_url = endpoint.replace("/api/demo/v1/traces", "")
        
        # Test basic connectivity
        health_url = f"{base_url}/api/demo/organizations"
        
        headers = {}
        headers_env = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
        if headers_env:
            header_pairs = headers_env.split(',')
            for pair in header_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    headers[key.strip()] = value.strip()
        
        print(f"📡 Testing: {health_url}")
        
        response = requests.get(
            health_url,
            headers=headers,
            timeout=10
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code in [200, 401, 403]:  # 401/403 means endpoint exists
            print("✅ Endpointに到達可能")
            return True
        else:
            print(f"❌ Endpoint到達不可: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False

def test_send_sample_trace():
    """Send sample trace to OpenObserve"""
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
        
        # Send to OpenObserve
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
            base_url = endpoint.replace("/api/demo/v1/traces", "")
            print(f"\n🌐 OpenObserve UIでデータを確認:")
            print(f"   URL: {base_url}/web/traces")
            print(f"   Service: aetherterm-test")
            print(f"   Trace ID: {trace_id}")
            
            return True
        elif response.status_code == 401:
            print("❌ 認証エラー: デモ認証情報が無効です")
            return False
        elif response.status_code == 404:
            print("❌ エンドポイントが見つかりません")
            return False
        else:
            print(f"❌ 送信に失敗: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ エラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_alternative_endpoints():
    """Test with alternative public OTLP endpoints"""
    print("\n🔄 代替エンドポイントテスト")
    print("=" * 50)
    
    # Test with Jaeger (if available locally)
    test_endpoints = [
        {
            "name": "Local Jaeger",
            "endpoint": "http://localhost:14268/api/traces",
            "headers": {}
        },
        {
            "name": "Local OTLP Collector", 
            "endpoint": "http://localhost:4318/v1/traces",
            "headers": {}
        }
    ]
    
    for config in test_endpoints:
        print(f"\n🔧 Testing {config['name']}: {config['endpoint']}")
        
        try:
            import requests
            
            # Simple connectivity test
            response = requests.get(
                config['endpoint'].replace('/v1/traces', '/'),
                timeout=5
            )
            print(f"   Status: {response.status_code} (endpoint reachable)")
            
        except requests.exceptions.ConnectionError:
            print(f"   Status: Connection refused (endpoint not available)")
        except Exception as e:
            print(f"   Status: Error - {e}")
    
    return True

def create_env_file_template():
    """Create environment file template for OpenObserve"""
    print("\n📝 .env テンプレート作成")
    print("=" * 50)
    
    template = """# OpenObserve Cloud Configuration
# Copy this to .env and update with your actual credentials

# Enable OpenTelemetry
OTEL_ENABLED=true
OTEL_SERVICE_NAME=aetherterm-backend
OTEL_SERVICE_VERSION=1.0.0

# OpenObserve Cloud Settings (replace with your values)
# OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://your-org.openobserve.ai/api/default/v1/traces
# OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=https://your-org.openobserve.ai/api/default/v1/logs
# OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64-encoded-user:password>"

# Example for demo (may not work in production)
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://api.openobserve.ai/api/demo/v1/traces
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic ZGVtb0BvcGVub2JzZXJ2ZS5haTpkZW1vMTIz"

# Debug settings
OTEL_DEBUG=false
OTEL_SAMPLE_RATE=1.0

# Socket.IO tracking
SOCKET_TRACKING_ENABLED=true
"""
    
    env_file = Path(__file__).parent.parent / ".env.openobserve"
    
    with open(env_file, 'w') as f:
        f.write(template)
    
    print(f"✅ テンプレート作成: {env_file}")
    print("💡 実際のOpenObserve認証情報で更新してください")
    
    return True

def main():
    """Main test function"""
    print("🌩️ OpenObserve Connection Test")
    print("=" * 60)
    
    results = {}
    
    # Setup demo configuration
    results["setup"] = setup_demo_config()
    
    # Test endpoint availability
    results["endpoint"] = test_endpoint_availability()
    
    # Test manual trace export (even if endpoint is not available)
    results["manual_export"] = test_send_sample_trace()
    
    # Test alternative endpoints
    results["alternatives"] = test_alternative_endpoints()
    
    # Create env template
    results["template"] = create_env_file_template()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 OPENOBSERVE CONNECTION TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if results.get("manual_export"):
        print("\n✅ OpenObserveとの接続テストが成功しました！")
        print("🔗 OpenObserve UIでトレースデータを確認してください")
    else:
        print("\n📋 OpenObserve接続の次のステップ:")
        print("1. 有効なOpenObserve Cloudアカウントを取得")
        print("2. .env.openobserveファイルを実際の認証情報で更新")
        print("3. AetherTermでOTEL_ENABLED=trueで起動してテスト")
        
        print("\n💡 利用可能なOpenObserve設定:")
        print("   • OpenObserve Cloud SaaS")
        print("   • Self-hosted OpenObserve")
        print("   • Docker Compose ローカル環境")
    
    return passed >= 3

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)