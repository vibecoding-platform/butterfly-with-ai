#!/usr/bin/env python3
"""
OpenObserve connection test with re-x organization
"""

import os
import sys
import time
import json
import requests

def test_openobserve_rex_auth():
    """Test OpenObserve authentication with re-x organization"""
    print("🔐 OpenObserve re-x Organization Authentication Test")
    print("=" * 60)
    
    # Use provided credentials with re-x organization
    auth_header = "Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"
    
    # Test organizations endpoint
    endpoint = "https://api.openobserve.ai/api/re-x/organizations"
    
    headers = {
        "Authorization": auth_header,
        "User-Agent": "aetherterm-openobserve-rex/1.0.0"
    }
    
    try:
        print(f"📡 Testing: {endpoint}")
        response = requests.get(
            endpoint,
            headers=headers,
            timeout=10
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ re-x組織への認証成功！")
            if response.text:
                try:
                    data = response.json()
                    print(f"📋 Organizations: {json.dumps(data, indent=2)}")
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

def send_trace_to_rex():
    """Send test trace to re-x organization"""
    print("\n📤 re-x組織へのTrace送信テスト")
    print("=" * 60)
    
    # Use provided credentials with re-x organization  
    auth_header = "Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"
    endpoint = "https://api.openobserve.ai/api/re-x/v1/traces"
    
    # Create test trace data
    trace_id = f"{int(time.time() * 1000000):032x}"
    span_id = f"{int(time.time() * 1000):016x}"
    
    print(f"📦 Trace ID: {trace_id}")
    print(f"📦 Span ID: {span_id}")
    print(f"🏢 Organization: re-x")
    
    otlp_data = {
        "resourceSpans": [{
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "aetherterm-backend"}},
                    {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                    {"key": "deployment.environment", "value": {"stringValue": "production"}},
                    {"key": "service.namespace", "value": {"stringValue": "aetherterm"}},
                    {"key": "organization", "value": {"stringValue": "re-x"}},
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
                    "endTimeUnixNano": str(int(time.time() * 1000000000) + 200000000),
                    "attributes": [
                        {"key": "socketio.event", "value": {"stringValue": "terminal:create"}},
                        {"key": "socketio.client_id", "value": {"stringValue": "rex-client-123"}},
                        {"key": "socketio.direction", "value": {"stringValue": "inbound"}},
                        {"key": "terminal.id", "value": {"stringValue": "terminal-rex-456"}},
                        {"key": "terminal.type", "value": {"stringValue": "xterm"}},
                        {"key": "terminal.size", "value": {"stringValue": "120x30"}},
                        {"key": "http.method", "value": {"stringValue": "POST"}},
                        {"key": "http.url", "value": {"stringValue": "/socket.io/terminal/create"}},
                        {"key": "user.id", "value": {"stringValue": "kaz@re-x.info"}},
                        {"key": "organization", "value": {"stringValue": "re-x"}},
                        {"key": "test.timestamp", "value": {"stringValue": str(int(time.time()))}}
                    ],
                    "events": [
                        {
                            "timeUnixNano": str(int(time.time() * 1000000000) + 50000000),
                            "name": "terminal_created",
                            "attributes": [
                                {"key": "terminal.pid", "value": {"stringValue": "12345"}},
                                {"key": "terminal.shell", "value": {"stringValue": "/bin/bash"}},
                                {"key": "organization", "value": {"stringValue": "re-x"}}
                            ]
                        },
                        {
                            "timeUnixNano": str(int(time.time() * 1000000000) + 150000000),
                            "name": "terminal_ready",
                            "attributes": [
                                {"key": "status", "value": {"stringValue": "ready"}},
                                {"key": "initialization_time", "value": {"stringValue": "150ms"}}
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
        "User-Agent": "aetherterm-openobserve-rex/1.0.0"
    }
    
    try:
        print(f"📡 送信先: {endpoint}")
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
            print("\n✅ re-x組織へのトレースデータ送信に成功しました！")
            
            # Show OpenObserve UI URL and search instructions
            print(f"\n🌐 OpenObserve UIでトレースを確認:")
            print(f"   URL: https://api.openobserve.ai/web/traces")
            print(f"   👤 ログイン: kaz@re-x.info / c8KGNeJfJIbZqFu7")
            print(f"   🏢 Organization: re-x")
            print(f"   🔍 検索条件:")
            print(f"     - Service: aetherterm-backend")
            print(f"     - Trace ID: {trace_id}")
            print(f"     - Time Range: Last 15 minutes")
            print(f"     - Operation: socketio.terminal:create")
            print(f"     - Organization: re-x")
            
            print(f"\n📊 表示されるはずのデータ:")
            print(f"   - Service Name: aetherterm-backend")
            print(f"   - Organization: re-x")
            print(f"   - Span Name: socketio.terminal:create")
            print(f"   - Duration: ~200ms")
            print(f"   - Client ID: rex-client-123")
            print(f"   - Terminal ID: terminal-rex-456")
            print(f"   - User: kaz@re-x.info")
            print(f"   - Events: terminal_created, terminal_ready")
            
            return True
        elif response.status_code == 401:
            print("\n❌ 認証エラー")
            return False
        elif response.status_code == 404:
            print("\n❌ エンドポイントが見つかりません (組織名を確認)")
            return False
        else:
            print(f"\n❌ 送信に失敗: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ エラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_complex_workflow_to_rex():
    """Send complex Socket.IO workflow to re-x organization"""
    print("\n📊 re-x組織への複雑なワークフロー送信")
    print("=" * 60)
    
    auth_header = "Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"
    endpoint = "https://api.openobserve.ai/api/re-x/v1/traces"
    
    # Create a complete AetherTerm workflow
    base_time = int(time.time() * 1000000000)
    trace_id = f"{int(time.time() * 1000000):032x}"
    
    # Define AetherTerm workflow spans
    workflow_spans = [
        {
            "name": "aetherterm.session:start",
            "span_id": f"{int(time.time() * 1000) + 1:016x}",
            "parent_id": None,
            "start_offset": 0,
            "duration": 100000000,  # 100ms
            "attributes": {
                "aetherterm.session_id": "session-rex-001",
                "user.email": "kaz@re-x.info",
                "organization": "re-x",
                "session.type": "interactive"
            },
            "events": [
                {"name": "session_initialized", "offset": 20000000},
                {"name": "user_authenticated", "offset": 50000000}
            ]
        },
        {
            "name": "socketio.connect", 
            "span_id": f"{int(time.time() * 1000) + 2:016x}",
            "parent_id": f"{int(time.time() * 1000) + 1:016x}",
            "start_offset": 120000000,
            "duration": 80000000,  # 80ms
            "attributes": {
                "socketio.event": "connect",
                "socketio.client_id": "rex-workflow-client",
                "http.method": "GET",
                "http.url": "/socket.io/",
                "client.ip": "10.0.1.100",
                "organization": "re-x"
            },
            "events": [
                {"name": "connection_established", "offset": 30000000},
                {"name": "authentication_verified", "offset": 60000000}
            ]
        },
        {
            "name": "socketio.workspace_sync_request",
            "span_id": f"{int(time.time() * 1000) + 3:016x}",
            "parent_id": f"{int(time.time() * 1000) + 2:016x}",
            "start_offset": 220000000,
            "duration": 150000000,  # 150ms
            "attributes": {
                "socketio.event": "workspace_sync_request",
                "workspace.id": "workspace-rex-main",
                "workspace.sessions": "3",
                "workspace.tabs": "5",
                "organization": "re-x"
            },
            "events": [
                {"name": "workspace_loaded", "offset": 70000000},
                {"name": "sessions_restored", "offset": 120000000}
            ]
        },
        {
            "name": "socketio.terminal:create",
            "span_id": f"{int(time.time() * 1000) + 4:016x}",
            "parent_id": f"{int(time.time() * 1000) + 3:016x}",
            "start_offset": 400000000,
            "duration": 250000000,  # 250ms
            "attributes": {
                "socketio.event": "terminal:create",
                "terminal.id": "terminal-rex-main",
                "terminal.type": "xterm",
                "terminal.size": "120x40",
                "terminal.shell": "/bin/bash",
                "organization": "re-x"
            },
            "events": [
                {"name": "pty_allocated", "offset": 80000000},
                {"name": "shell_initialized", "offset": 200000000}
            ]
        },
        {
            "name": "socketio.ai_chat_message",
            "span_id": f"{int(time.time() * 1000) + 5:016x}",
            "parent_id": f"{int(time.time() * 1000) + 2:016x}",
            "start_offset": 700000000,
            "duration": 500000000,  # 500ms
            "attributes": {
                "socketio.event": "ai_chat_message",
                "ai.model": "claude-3",
                "ai.message": "Please help me with Docker commands",
                "ai.response_length": "256",
                "organization": "re-x"
            },
            "events": [
                {"name": "ai_request_sent", "offset": 100000000},
                {"name": "ai_response_received", "offset": 450000000}
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
                    "attributes": [
                        {"key": "organization", "value": {"stringValue": "re-x"}}
                    ]
                })
        
        otlp_spans.append(span)
    
    otlp_data = {
        "resourceSpans": [{
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "aetherterm-backend"}},
                    {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                    {"key": "deployment.environment", "value": {"stringValue": "production"}},
                    {"key": "service.namespace", "value": {"stringValue": "aetherterm"}},
                    {"key": "organization", "value": {"stringValue": "re-x"}},
                    {"key": "user.email", "value": {"stringValue": "kaz@re-x.info"}}
                ]
            },
            "scopeSpans": [{
                "scope": {
                    "name": "aetherterm.rex.workflow",
                    "version": "1.0.0"
                },
                "spans": otlp_spans
            }]
        }]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_header,
        "User-Agent": "aetherterm-rex-workflow/1.0.0"
    }
    
    try:
        print(f"📦 Workflow Trace ID: {trace_id}")
        print(f"📊 Spans: {len(otlp_spans)}")
        print(f"🏢 Organization: re-x")
        print(f"📤 送信中...")
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=otlp_data,
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code in [200, 202]:
            print("✅ re-x組織へのワークフロートレース送信成功！")
            
            print(f"\n🌐 OpenObserve UIでワークフロー確認:")
            print(f"   URL: https://api.openobserve.ai/web/traces")
            print(f"   🏢 Organization: re-x")
            print(f"   🔍 Trace ID: {trace_id}")
            print(f"   📊 期待される階層表示:")
            print(f"     ├─ aetherterm.session:start (100ms)")
            print(f"     │  └─ socketio.connect (80ms)")
            print(f"     │     ├─ socketio.workspace_sync_request (150ms)")
            print(f"     │     │  └─ socketio.terminal:create (250ms)")
            print(f"     │     └─ socketio.ai_chat_message (500ms)")
            
            return True
        else:
            print(f"❌ 送信失敗: {response.status_code}")
            if response.text:
                print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    """Main test function"""
    print("🏢 OpenObserve re-x Organization Test")
    print("=" * 70)
    
    results = {}
    
    # Test authentication with re-x organization
    results["auth"] = test_openobserve_rex_auth()
    
    if results["auth"]:
        print("\n✅ re-x組織への認証成功 - トレースデータを送信します")
        
        # Send single test trace
        results["single_trace"] = send_trace_to_rex()
        
        # Send complex workflow trace
        results["workflow_trace"] = send_complex_workflow_to_rex()
        
        if results["single_trace"] or results["workflow_trace"]:
            print(f"\n🎉 re-x組織のOpenObserveにトレースデータを送信しました！")
            print(f"\n📱 今すぐOpenObserve UIを確認してください:")
            print(f"   1. ブラウザで https://api.openobserve.ai/web/traces を開く")
            print(f"   2. kaz@re-x.info でログイン")
            print(f"   3. Organization: re-x を選択")
            print(f"   4. Time Range を 'Last 15 minutes' に設定")
            print(f"   5. Service filter で 'aetherterm-backend' を選択")
            print(f"   6. トレースリストを確認")
            
            print(f"\n🔍 確認すべき項目:")
            print(f"   ✓ Organization: re-x")
            print(f"   ✓ Service Name: aetherterm-backend")
            print(f"   ✓ User: kaz@re-x.info")
            print(f"   ✓ Operations: socketio.terminal:create, aetherterm.session:start")
            print(f"   ✓ Client ID: rex-client-123, rex-workflow-client")
            print(f"   ✓ Terminal ID: terminal-rex-456, terminal-rex-main")
            
    else:
        print("\n❌ re-x組織への認証に失敗しました")
        results["single_trace"] = False
        results["workflow_trace"] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 RE-X ORGANIZATION TEST SUMMARY")
    print("=" * 70)
    
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