#!/usr/bin/env python3
"""
Real OpenObserve connection test with provided valid credentials
"""

import os
import sys
import time
import json
import requests

def test_openobserve_auth():
    """Test OpenObserve authentication"""
    print("🔐 OpenObserve Authentication Test")
    print("=" * 50)
    
    # Use provided real credentials
    auth_header = "Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"
    
    # First, try to get organizations to verify auth
    endpoint = "https://api.openobserve.ai/api/default/organizations"
    
    headers = {
        "Authorization": auth_header,
        "User-Agent": "aetherterm-openobserve-test/1.0.0"
    }
    
    try:
        response = requests.get(
            endpoint,
            headers=headers,
            timeout=10
        )
        
        print(f"📊 Organizations Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 認証成功！")
            if response.text:
                try:
                    data = response.json()
                    print(f"📋 Available Organizations:")
                    for org in data:
                        print(f"   - {org}")
                except:
                    print(f"📄 Response: {response.text[:200]}")
            return True
        elif response.status_code == 401:
            print("❌ 認証エラー")
            return False
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False

def send_test_trace():
    """Send test trace to OpenObserve"""
    print("\n📤 Test Trace送信")
    print("=" * 50)
    
    # Use provided real credentials
    auth_header = "Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"
    endpoint = "https://api.openobserve.ai/api/default/v1/traces"
    
    # Create test trace data
    trace_id = f"{int(time.time() * 1000000):032x}"
    span_id = f"{int(time.time() * 1000):016x}"
    
    print(f"📦 Trace ID: {trace_id}")
    print(f"📦 Span ID: {span_id}")
    
    otlp_data = {
        "resourceSpans": [{
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "aetherterm-backend"}},
                    {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                    {"key": "deployment.environment", "value": {"stringValue": "production"}},
                    {"key": "service.namespace", "value": {"stringValue": "aetherterm"}},
                    {"key": "telemetry.sdk.name", "value": {"stringValue": "opentelemetry"}},
                    {"key": "telemetry.sdk.language", "value": {"stringValue": "python"}}
                ]
            },
            "scopeSpans": [{
                "scope": {
                    "name": "aetherterm.socketio",
                    "version": "1.0.0"
                },
                "spans": [{
                    "traceId": trace_id,
                    "spanId": span_id,
                    "name": "socketio.terminal:create",
                    "kind": 1,
                    "startTimeUnixNano": str(int(time.time() * 1000000000)),
                    "endTimeUnixNano": str(int(time.time() * 1000000000) + 150000000),
                    "attributes": [
                        {"key": "socketio.event", "value": {"stringValue": "terminal:create"}},
                        {"key": "socketio.client_id", "value": {"stringValue": "production-client-123"}},
                        {"key": "socketio.direction", "value": {"stringValue": "inbound"}},
                        {"key": "terminal.id", "value": {"stringValue": "terminal-prod-456"}},
                        {"key": "terminal.type", "value": {"stringValue": "xterm"}},
                        {"key": "terminal.size", "value": {"stringValue": "80x24"}},
                        {"key": "http.method", "value": {"stringValue": "POST"}},
                        {"key": "http.url", "value": {"stringValue": "/socket.io/terminal/create"}},
                        {"key": "user.id", "value": {"stringValue": "user-789"}},
                        {"key": "test.timestamp", "value": {"stringValue": str(int(time.time()))}}
                    ],
                    "events": [
                        {
                            "timeUnixNano": str(int(time.time() * 1000000000) + 50000000),
                            "name": "terminal_created",
                            "attributes": [
                                {"key": "terminal.pid", "value": {"stringValue": "12345"}},
                                {"key": "terminal.shell", "value": {"stringValue": "/bin/bash"}}
                            ]
                        },
                        {
                            "timeUnixNano": str(int(time.time() * 1000000000) + 100000000),
                            "name": "terminal_ready",
                            "attributes": [
                                {"key": "status", "value": {"stringValue": "ready"}},
                                {"key": "initialization_time", "value": {"stringValue": "100ms"}}
                            ]
                        }
                    ],
                    "status": {"code": 1, "message": ""}
                }]
            }]
        }]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_header,
        "User-Agent": "aetherterm-openobserve-production/1.0.0"
    }
    
    try:
        print(f"📡 送信先: {endpoint}")
        print(f"🔐 Auth: Basic ***")
        print(f"📤 データ送信中...")
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=otlp_data,
            timeout=30
        )
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.text:
            print(f"📄 Response Body: {response.text}")
        
        if response.status_code in [200, 202]:
            print("\n✅ トレースデータの送信に成功しました！")
            
            # Show OpenObserve UI URL and search instructions
            print(f"\n🌐 OpenObserve UIでトレースを確認:")
            print(f"   URL: https://api.openobserve.ai/web/traces")
            print(f"   👤 ログイン: kaz@re-x.info / c8KGNeJfJIbZqFu7")
            print(f"   🏢 Organization: default")
            print(f"   🔍 検索条件:")
            print(f"     - Service: aetherterm-backend")
            print(f"     - Trace ID: {trace_id}")
            print(f"     - Time Range: Last 15 minutes")
            print(f"     - Operation: socketio.terminal:create")
            
            print(f"\n📊 表示されるはずのデータ:")
            print(f"   - Service Name: aetherterm-backend")
            print(f"   - Span Name: socketio.terminal:create")
            print(f"   - Duration: ~150ms")
            print(f"   - Attributes: socketio.event, terminal.id, client_id")
            print(f"   - Events: terminal_created, terminal_ready")
            
            return True
        elif response.status_code == 401:
            print("\n❌ 認証エラー")
            return False
        elif response.status_code == 404:
            print("\n❌ エンドポイントが見つかりません")
            return False
        else:
            print(f"\n❌ 送信に失敗: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ エラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_multiple_traces():
    """Send multiple related traces to create a more complex view"""
    print("\n📊 Multiple Traces送信 (複雑なワークフロー)")
    print("=" * 50)
    
    auth_header = "Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"
    endpoint = "https://api.openobserve.ai/api/default/v1/traces"
    
    # Create a complete Socket.IO workflow
    base_time = int(time.time() * 1000000000)
    trace_id = f"{int(time.time() * 1000000):032x}"
    
    # Define workflow spans
    workflow_spans = [
        {
            "name": "socketio.connect",
            "span_id": f"{int(time.time() * 1000) + 1:016x}",
            "parent_id": None,
            "start_offset": 0,
            "duration": 50000000,  # 50ms
            "attributes": {
                "socketio.event": "connect",
                "socketio.client_id": "workflow-client-456",
                "http.method": "GET",
                "http.url": "/socket.io/",
                "client.ip": "192.168.1.100"
            },
            "events": [
                {"name": "connection_established", "offset": 10000000},
                {"name": "authentication_verified", "offset": 30000000}
            ]
        },
        {
            "name": "socketio.create_terminal", 
            "span_id": f"{int(time.time() * 1000) + 2:016x}",
            "parent_id": f"{int(time.time() * 1000) + 1:016x}",
            "start_offset": 60000000,
            "duration": 200000000,  # 200ms
            "attributes": {
                "socketio.event": "create_terminal",
                "terminal.type": "xterm",
                "terminal.size": "120x30",
                "terminal.id": "term-workflow-789"
            },
            "events": [
                {"name": "pty_allocated", "offset": 50000000},
                {"name": "shell_started", "offset": 150000000}
            ]
        },
        {
            "name": "socketio.terminal_input",
            "span_id": f"{int(time.time() * 1000) + 3:016x}",
            "parent_id": f"{int(time.time() * 1000) + 2:016x}",
            "start_offset": 300000000,
            "duration": 100000000,  # 100ms
            "attributes": {
                "socketio.event": "terminal:input",
                "terminal.id": "term-workflow-789",
                "input.command": "echo 'Hello OpenObserve!'",
                "input.length": "22"
            },
            "events": [
                {"name": "command_executed", "offset": 50000000},
                {"name": "output_generated", "offset": 80000000}
            ]
        },
        {
            "name": "socketio.ai_chat_message",
            "span_id": f"{int(time.time() * 1000) + 4:016x}",
            "parent_id": f"{int(time.time() * 1000) + 1:016x}",
            "start_offset": 450000000,
            "duration": 300000000,  # 300ms
            "attributes": {
                "socketio.event": "ai_chat_message",
                "ai.model": "claude-3",
                "ai.message_length": "45",
                "ai.response_length": "120"
            },
            "events": [
                {"name": "ai_request_sent", "offset": 50000000},
                {"name": "ai_response_received", "offset": 250000000}
            ]
        }
    ]
    
    # Convert to OTLP format
    otlp_spans = []
    for span_data in workflow_spans:
        span = {
            "traceId": trace_id,
            "spanId": span_data["span_id"],
            "name": span_data["name"],
            "kind": 1,
            "startTimeUnixNano": str(base_time + span_data["start_offset"]),
            "endTimeUnixNano": str(base_time + span_data["start_offset"] + span_data["duration"]),
            "attributes": [
                {"key": k, "value": {"stringValue": str(v)}} 
                for k, v in span_data["attributes"].items()
            ],
            "status": {"code": 1, "message": ""}
        }
        
        if span_data["parent_id"]:
            span["parentSpanId"] = span_data["parent_id"]
        
        if span_data.get("events"):
            span["events"] = []
            for event in span_data["events"]:
                span["events"].append({
                    "timeUnixNano": str(base_time + span_data["start_offset"] + event["offset"]),
                    "name": event["name"],
                    "attributes": []
                })
        
        otlp_spans.append(span)
    
    otlp_data = {
        "resourceSpans": [{
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "aetherterm-backend"}},
                    {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                    {"key": "deployment.environment", "value": {"stringValue": "production"}},
                    {"key": "service.namespace", "value": {"stringValue": "aetherterm"}}
                ]
            },
            "scopeSpans": [{
                "scope": {
                    "name": "aetherterm.socketio.workflow",
                    "version": "1.0.0"
                },
                "spans": otlp_spans
            }]
        }]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_header,
        "User-Agent": "aetherterm-openobserve-workflow/1.0.0"
    }
    
    try:
        print(f"📦 Workflow Trace ID: {trace_id}")
        print(f"📊 Spans: {len(otlp_spans)}")
        print(f"📤 送信中...")
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=otlp_data,
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code in [200, 202]:
            print("✅ ワークフロートレースの送信に成功しました！")
            
            print(f"\n🌐 OpenObserve UIでワークフロー確認:")
            print(f"   URL: https://api.openobserve.ai/web/traces")
            print(f"   🔍 Trace ID: {trace_id}")
            print(f"   📊 期待される表示:")
            print(f"     ├─ socketio.connect (50ms)")
            print(f"     │  ├─ socketio.create_terminal (200ms)")
            print(f"     │  │  └─ socketio.terminal_input (100ms)")
            print(f"     │  └─ socketio.ai_chat_message (300ms)")
            
            return True
        else:
            print(f"❌ 送信失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    """Main test function"""
    print("🔍 OpenObserve Real Connection Test")
    print("=" * 60)
    
    results = {}
    
    # Test authentication
    results["auth"] = test_openobserve_auth()
    
    if results["auth"]:
        print("\n✅ 認証成功 - トレースデータを送信します")
        
        # Send single test trace
        results["single_trace"] = send_test_trace()
        
        # Send multiple related traces
        results["workflow_trace"] = send_multiple_traces()
        
        if results["single_trace"] or results["workflow_trace"]:
            print(f"\n🎉 OpenObserveにトレースデータを送信しました！")
            print(f"\n📱 今すぐOpenObserve UIを確認してください:")
            print(f"   1. ブラウザで https://api.openobserve.ai/web/traces を開く")
            print(f"   2. kaz@re-x.info でログイン")
            print(f"   3. Time Range を 'Last 15 minutes' に設定")
            print(f"   4. Service filter で 'aetherterm-backend' を選択")
            print(f"   5. トレースリストで socketio.terminal:create を探す")
            print(f"   6. トレースをクリックして詳細を確認")
            
            print(f"\n🔍 確認すべき項目:")
            print(f"   ✓ Service Name: aetherterm-backend")
            print(f"   ✓ Operation Name: socketio.terminal:create")
            print(f"   ✓ Span Attributes: socketio.event, terminal.id")
            print(f"   ✓ Events: terminal_created, terminal_ready")
            print(f"   ✓ Duration: ~150ms-300ms")
            
    else:
        print("\n❌ 認証に失敗しました")
        results["single_trace"] = False
        results["workflow_trace"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 OPENOBSERVE REAL TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    return passed >= 1

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)