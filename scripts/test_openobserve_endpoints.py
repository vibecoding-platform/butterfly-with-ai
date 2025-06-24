#!/usr/bin/env python3
"""
OpenObserve endpoint exploration to find correct organization structure
"""

import os
import sys
import time
import json
import requests

def test_various_endpoints():
    """Test various OpenObserve endpoint patterns"""
    print("🔍 OpenObserve Endpoint Exploration")
    print("=" * 60)
    
    auth_header = "Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"
    
    # Various endpoint patterns to test
    endpoints_to_test = [
        # Organization endpoints
        "https://api.openobserve.ai/api/organizations",
        "https://api.openobserve.ai/api/re-x/organizations", 
        "https://api.openobserve.ai/api/default/organizations",
        
        # Traces endpoints
        "https://api.openobserve.ai/api/re-x/v1/traces",
        "https://api.openobserve.ai/api/default/v1/traces",
        "https://api.openobserve.ai/v1/traces",
        
        # Health/info endpoints
        "https://api.openobserve.ai/healthz",
        "https://api.openobserve.ai/api/healthz",
        "https://api.openobserve.ai/config",
        "https://api.openobserve.ai/api/config",
        
        # User info
        "https://api.openobserve.ai/api/user",
        "https://api.openobserve.ai/user",
    ]
    
    headers = {
        "Authorization": auth_header,
        "User-Agent": "aetherterm-endpoint-explorer/1.0.0"
    }
    
    results = {}
    
    for endpoint in endpoints_to_test:
        try:
            print(f"\n📡 Testing: {endpoint}")
            response = requests.get(
                endpoint,
                headers=headers,
                timeout=10
            )
            
            status = response.status_code
            print(f"   Status: {status}")
            
            if status == 200:
                print("   ✅ SUCCESS")
                try:
                    data = response.json()
                    print(f"   📋 Data: {json.dumps(data, indent=4)[:200]}...")
                except:
                    print(f"   📄 Text: {response.text[:100]}...")
            elif status == 401:
                print("   ❌ UNAUTHORIZED")
            elif status == 404:
                print("   ⚠️ NOT FOUND")
            elif status == 403:
                print("   🚫 FORBIDDEN")
            else:
                print(f"   ❓ OTHER: {response.text[:50] if response.text else 'No content'}")
            
            results[endpoint] = status
            
        except Exception as e:
            print(f"   💥 ERROR: {e}")
            results[endpoint] = "ERROR"
    
    return results

def test_simple_trace_without_org():
    """Test sending trace without organization in URL"""
    print("\n📤 Simple Trace Test (No Organization in URL)")
    print("=" * 60)
    
    auth_header = "Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"
    
    # Try simpler endpoint structure
    endpoints_to_try = [
        "https://api.openobserve.ai/v1/traces",
        "https://api.openobserve.ai/api/v1/traces",
        "https://api.openobserve.ai/api/default/v1/traces"
    ]
    
    # Create minimal test trace
    trace_id = f"{int(time.time() * 1000000):032x}"
    span_id = f"{int(time.time() * 1000):016x}"
    
    otlp_data = {
        "resourceSpans": [{
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "aetherterm-test"}},
                    {"key": "organization", "value": {"stringValue": "re-x"}}
                ]
            },
            "scopeSpans": [{
                "scope": {
                    "name": "test",
                    "version": "1.0.0"
                },
                "spans": [{
                    "traceId": trace_id,
                    "spanId": span_id,
                    "name": "test_span",
                    "kind": 1,
                    "startTimeUnixNano": str(int(time.time() * 1000000000)),
                    "endTimeUnixNano": str(int(time.time() * 1000000000) + 100000000),
                    "attributes": [
                        {"key": "test.type", "value": {"stringValue": "endpoint_discovery"}},
                        {"key": "organization", "value": {"stringValue": "re-x"}}
                    ],
                    "status": {"code": 1, "message": ""}
                }]
            }]
        }]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_header,
        "User-Agent": "aetherterm-endpoint-test/1.0.0"
    }
    
    success = False
    
    for endpoint in endpoints_to_try:
        try:
            print(f"\n📡 Trying: {endpoint}")
            response = requests.post(
                endpoint,
                headers=headers,
                json=otlp_data,
                timeout=30
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.text:
                print(f"   Response: {response.text[:100]}")
            
            if response.status_code in [200, 202]:
                print(f"   ✅ SUCCESS! Trace sent successfully")
                print(f"   📦 Trace ID: {trace_id}")
                success = True
                break
            elif response.status_code == 401:
                print(f"   ❌ UNAUTHORIZED")
            elif response.status_code == 404:
                print(f"   ⚠️ NOT FOUND")
            else:
                print(f"   ❓ OTHER ERROR")
                
        except Exception as e:
            print(f"   💥 ERROR: {e}")
    
    return success

def test_openobserve_web_access():
    """Test OpenObserve web UI access"""
    print("\n🌐 OpenObserve Web UI Access Test")
    print("=" * 60)
    
    web_urls = [
        "https://api.openobserve.ai/web/",
        "https://api.openobserve.ai/",
        "https://web.openobserve.ai/",
        "https://openobserve.ai/"
    ]
    
    for url in web_urls:
        try:
            print(f"\n📱 Testing: {url}")
            response = requests.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Web UI accessible")
                if "login" in response.text.lower() or "sign" in response.text.lower():
                    print("   🔐 Login page detected")
                print(f"   🌐 Use this URL: {url}")
                return url
            else:
                print(f"   ❌ Not accessible")
                
        except Exception as e:
            print(f"   💥 ERROR: {e}")
    
    return None

def create_final_config():
    """Create final configuration based on findings"""
    print("\n📝 Final Configuration Creation")
    print("=" * 60)
    
    config_template = """# AetherTerm OpenObserve Configuration
# Based on endpoint exploration results

# Enable OpenTelemetry
OTEL_ENABLED=true
OTEL_SERVICE_NAME=aetherterm-backend
OTEL_SERVICE_VERSION=1.0.0

# OpenObserve Configuration (re-x organization)
# Credentials: kaz@re-x.info / c8KGNeJfJIbZqFu7
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://api.openobserve.ai/api/re-x/v1/traces
OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=https://api.openobserve.ai/api/re-x/v1/logs
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"

# Alternative endpoints to try if re-x specific fails:
# OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://api.openobserve.ai/api/default/v1/traces
# OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://api.openobserve.ai/v1/traces

# Debug settings
OTEL_DEBUG=true
OTEL_SAMPLE_RATE=1.0

# Additional attributes
DEPLOYMENT_ENV=production
ORGANIZATION=re-x

# OpenObserve Web UI
# URL: https://api.openobserve.ai/web/
# Login: kaz@re-x.info
# Password: c8KGNeJfJIbZqFu7
# Organization: re-x (if applicable)

# Usage:
# 1. Copy this to .env
# 2. Start AetherTerm: OTEL_ENABLED=true uv run python src/aetherterm/agentserver/main.py
# 3. Open OpenObserve UI and check for traces
"""
    
    config_file = "openobserve-rex-config.env"
    with open(config_file, 'w') as f:
        f.write(config_template)
    
    print(f"✅ Configuration written to: {config_file}")
    print("💡 Copy this file to .env and test with AetherTerm")
    
    return True

def main():
    """Main exploration function"""
    print("🔬 OpenObserve Endpoint Exploration for re-x Organization")
    print("=" * 70)
    
    # Test various endpoints
    print("\n1️⃣ Endpoint Pattern Testing")
    endpoint_results = test_various_endpoints()
    
    # Test simple trace sending
    print("\n2️⃣ Simple Trace Sending")
    trace_success = test_simple_trace_without_org()
    
    # Test web UI access
    print("\n3️⃣ Web UI Access Testing")
    web_url = test_openobserve_web_access()
    
    # Create final configuration
    print("\n4️⃣ Configuration Generation")
    config_created = create_final_config()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 EXPLORATION SUMMARY")
    print("=" * 70)
    
    working_endpoints = [ep for ep, status in endpoint_results.items() if status == 200]
    
    print(f"🔍 Endpoints tested: {len(endpoint_results)}")
    print(f"✅ Working endpoints: {len(working_endpoints)}")
    print(f"📤 Trace sending: {'✅ SUCCESS' if trace_success else '❌ FAILED'}")
    print(f"🌐 Web UI: {'✅ FOUND' if web_url else '❌ NOT FOUND'}")
    
    if working_endpoints:
        print(f"\n🎯 Working endpoints:")
        for ep in working_endpoints:
            print(f"   ✅ {ep}")
    
    if web_url:
        print(f"\n🌐 OpenObserve UI URL: {web_url}")
        print(f"   👤 Login: kaz@re-x.info")
        print(f"   🔑 Password: c8KGNeJfJIbZqFu7")
        print(f"   🏢 Organization: re-x")
    
    if trace_success:
        print(f"\n🎉 トレース送信成功！")
        print(f"📊 OpenObserve UIでデータを確認してください")
    else:
        print(f"\n💡 次のステップ:")
        print(f"1. openobserve-rex-config.env ファイルを確認")
        print(f"2. 正しいエンドポイントで手動テスト")
        print(f"3. OpenObserveアカウント設定を確認")
    
    return trace_success or len(working_endpoints) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)