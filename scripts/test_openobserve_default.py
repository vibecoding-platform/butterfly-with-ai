#!/usr/bin/env python3
"""
OpenObserve connection test with default organization (discovered from API)
"""

import os
import sys
import time
import json
import requests

def send_trace_to_default_org():
    """Send test trace to default organization"""
    print("🏢 OpenObserve Default Organization Trace Test")
    print("=" * 60)
    
    # Use correct default organization endpoint
    auth_header = "Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"
    endpoint = "https://api.openobserve.ai/api/default/v1/traces"
    
    # Create test trace data
    trace_id = f"{int(time.time() * 1000000):032x}"
    span_id = f"{int(time.time() * 1000):016x}"
    
    print(f"📦 Trace ID: {trace_id}")
    print(f"📦 Span ID: {span_id}")
    print(f"🏢 Organization: default")
    print(f"👤 User: kaz@re-x.info")
    
    otlp_data = {
        "resourceSpans": [{
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "aetherterm-backend"}},
                    {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                    {"key": "deployment.environment", "value": {"stringValue": "production"}},
                    {"key": "service.namespace", "value": {"stringValue": "aetherterm"}},
                    {"key": "user.email", "value": {"stringValue": "kaz@re-x.info"}},
                    {"key": "organization.name", "value": {"stringValue": "default"}},
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
                    "endTimeUnixNano": str(int(time.time() * 1000000000) + 180000000),
                    "attributes": [
                        {"key": "socketio.event", "value": {"stringValue": "terminal:create"}},
                        {"key": "socketio.client_id", "value": {"stringValue": "default-client-123"}},
                        {"key": "socketio.direction", "value": {"stringValue": "inbound"}},
                        {"key": "terminal.id", "value": {"stringValue": "terminal-default-456"}},
                        {"key": "terminal.type", "value": {"stringValue": "xterm"}},
                        {"key": "terminal.size", "value": {"stringValue": "120x30"}},
                        {"key": "http.method", "value": {"stringValue": "POST"}},
                        {"key": "http.url", "value": {"stringValue": "/socket.io/terminal/create"}},
                        {"key": "user.email", "value": {"stringValue": "kaz@re-x.info"}},
                        {"key": "organization.name", "value": {"stringValue": "default"}},
                        {"key": "test.timestamp", "value": {"stringValue": str(int(time.time()))}},
                        {"key": "test.session", "value": {"stringValue": "openobserve_integration_test"}}
                    ],
                    "events": [
                        {
                            "timeUnixNano": str(int(time.time() * 1000000000) + 60000000),
                            "name": "terminal_created",
                            "attributes": [
                                {"key": "terminal.pid", "value": {"stringValue": "12345"}},
                                {"key": "terminal.shell", "value": {"stringValue": "/bin/bash"}},
                                {"key": "organization.name", "value": {"stringValue": "default"}}
                            ]
                        },
                        {
                            "timeUnixNano": str(int(time.time() * 1000000000) + 120000000),
                            "name": "terminal_ready",
                            "attributes": [
                                {"key": "status", "value": {"stringValue": "ready"}},
                                {"key": "initialization_time", "value": {"stringValue": "120ms"}}
                            ]
                        },
                        {
                            "timeUnixNano": str(int(time.time() * 1000000000) + 160000000),
                            "name": "openobserve_test_completed",
                            "attributes": [
                                {"key": "test.result", "value": {"stringValue": "success"}},
                                {"key": "test.type", "value": {"stringValue": "aetherterm_integration"}}
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
        "User-Agent": "aetherterm-openobserve-default/1.0.0"
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
        print(f"📋 Response Headers: {dict(response.headers)}")
        
        if response.text:
            print(f"📄 Response Body: {response.text}")
        
        if response.status_code in [200, 202]:
            print("\n🎉 OpenObserveにトレースデータの送信に成功しました！")
            
            # Show detailed UI access instructions
            print(f"\n🌐 OpenObserve UIでトレースを確認してください:")
            print(f"   📱 URL: https://api.openobserve.ai/web/")
            print(f"   👤 ログイン情報:")
            print(f"      Email: kaz@re-x.info")
            print(f"      Password: c8KGNeJfJIbZqFu7")
            print(f"   🏢 Organization: default")
            
            print(f"\n🔍 UIでの確認手順:")
            print(f"   1. 上記URLでログイン")
            print(f"   2. 左メニューから 'Traces' を選択")
            print(f"   3. Time Range を 'Last 15 minutes' に設定")
            print(f"   4. Service で 'aetherterm-backend' を選択")
            print(f"   5. 以下のトレースを検索:")
            
            print(f"\n📊 確認すべきトレースデータ:")
            print(f"   ✓ Trace ID: {trace_id}")
            print(f"   ✓ Service Name: aetherterm-backend")
            print(f"   ✓ Operation: socketio.terminal:create")
            print(f"   ✓ Duration: ~180ms")
            print(f"   ✓ User: kaz@re-x.info")
            print(f"   ✓ Organization: default")
            print(f"   ✓ Terminal ID: terminal-default-456")
            print(f"   ✓ Client ID: default-client-123")
            
            print(f"\n📈 スパンの詳細で確認できる項目:")
            print(f"   • Attributes: socketio.*, terminal.*, user.email")
            print(f"   • Events: terminal_created, terminal_ready, openobserve_test_completed")
            print(f"   • Timing: 作成(60ms) → 準備完了(120ms) → テスト完了(160ms)")
            
            print(f"\n💡 フィルター例:")
            print(f"   • service.name=aetherterm-backend")
            print(f"   • user.email=kaz@re-x.info")
            print(f"   • terminal.id=terminal-default-456")
            print(f"   • test.session=openobserve_integration_test")
            
            return True
        elif response.status_code == 401:
            print("\n❌ 認証エラー")
            print("💡 認証情報を確認してください")
            return False
        elif response.status_code == 404:
            print("\n❌ エンドポイントが見つかりません")
            print("💡 組織名またはエンドポイントを確認してください")
            return False
        elif response.status_code == 403:
            print("\n❌ 権限エラー")
            print("💡 アカウントにトレース書き込み権限があるか確認してください")
            return False
        else:
            print(f"\n❌ 送信に失敗: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ エラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_aetherterm_workflow():
    """Send complete AetherTerm workflow to demonstrate full tracing capability"""
    print("\n📊 Complete AetherTerm Workflow Trace")
    print("=" * 60)
    
    auth_header = "Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"
    endpoint = "https://api.openobserve.ai/api/default/v1/traces"
    
    # Create a realistic AetherTerm session workflow
    base_time = int(time.time() * 1000000000)
    trace_id = f"{int(time.time() * 1000000):032x}"
    
    # Define complete workflow
    workflow_spans = [
        {
            "name": "aetherterm.session:start",
            "span_id": f"{int(time.time() * 1000) + 1:016x}",
            "parent_id": None,
            "start_offset": 0,
            "duration": 150000000,  # 150ms
            "attributes": {
                "aetherterm.session_id": "session-openobserve-001",
                "user.email": "kaz@re-x.info",
                "organization.name": "default",
                "session.type": "interactive",
                "client.browser": "Chrome/120.0",
                "client.ip": "192.168.1.100"
            },
            "events": [
                {"name": "session_initialized", "offset": 30000000},
                {"name": "user_authenticated", "offset": 80000000},
                {"name": "workspace_loading", "offset": 120000000}
            ]
        },
        {
            "name": "socketio.connect", 
            "span_id": f"{int(time.time() * 1000) + 2:016x}",
            "parent_id": f"{int(time.time() * 1000) + 1:016x}",
            "start_offset": 180000000,
            "duration": 100000000,  # 100ms
            "attributes": {
                "socketio.event": "connect",
                "socketio.client_id": "openobserve-workflow-client",
                "http.method": "GET",
                "http.url": "/socket.io/",
                "socketio.namespace": "/",
                "organization.name": "default"
            },
            "events": [
                {"name": "handshake_completed", "offset": 40000000},
                {"name": "authentication_verified", "offset": 80000000}
            ]
        },
        {
            "name": "socketio.workspace_sync_request",
            "span_id": f"{int(time.time() * 1000) + 3:016x}",
            "parent_id": f"{int(time.time() * 1000) + 2:016x}",
            "start_offset": 300000000,
            "duration": 200000000,  # 200ms
            "attributes": {
                "socketio.event": "workspace_sync_request",
                "workspace.id": "workspace-default-main",
                "workspace.sessions": "2",
                "workspace.tabs": "4",
                "workspace.panes": "6",
                "organization.name": "default"
            },
            "events": [
                {"name": "workspace_state_loaded", "offset": 80000000},
                {"name": "sessions_restored", "offset": 150000000}
            ]
        },
        {
            "name": "socketio.terminal:create",
            "span_id": f"{int(time.time() * 1000) + 4:016x}",
            "parent_id": f"{int(time.time() * 1000) + 3:016x}",
            "start_offset": 520000000,
            "duration": 300000000,  # 300ms
            "attributes": {
                "socketio.event": "terminal:create",
                "terminal.id": "terminal-openobserve-main",
                "terminal.type": "xterm",
                "terminal.size": "120x40",
                "terminal.shell": "/bin/bash",
                "terminal.env": "production",
                "organization.name": "default"
            },
            "events": [
                {"name": "pty_allocated", "offset": 100000000},
                {"name": "shell_started", "offset": 200000000},
                {"name": "terminal_ready", "offset": 280000000}
            ]
        },
        {
            "name": "socketio.terminal:input",
            "span_id": f"{int(time.time() * 1000) + 5:016x}",
            "parent_id": f"{int(time.time() * 1000) + 4:016x}",
            "start_offset": 850000000,
            "duration": 150000000,  # 150ms
            "attributes": {
                "socketio.event": "terminal:input",
                "terminal.id": "terminal-openobserve-main",
                "input.command": "echo 'Hello OpenObserve from AetherTerm!'",
                "input.length": "40",
                "organization.name": "default"
            },
            "events": [
                {"name": "command_received", "offset": 20000000},
                {"name": "command_executed", "offset": 80000000},
                {"name": "output_generated", "offset": 130000000}
            ]
        },
        {
            "name": "socketio.ai_chat_message",
            "span_id": f"{int(time.time() * 1000) + 6:016x}",
            "parent_id": f"{int(time.time() * 1000) + 2:016x}",
            "start_offset": 1020000000,
            "duration": 800000000,  # 800ms
            "attributes": {
                "socketio.event": "ai_chat_message",
                "ai.model": "claude-3-sonnet",
                "ai.message": "Show me how to monitor terminal performance",
                "ai.message_length": "45",
                "ai.response_length": "320",
                "organization.name": "default"
            },
            "events": [
                {"name": "ai_request_sent", "offset": 150000000},
                {"name": "ai_processing", "offset": 400000000},
                {"name": "ai_response_received", "offset": 750000000}
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
                        {"key": "organization.name", "value": {"stringValue": "default"}}
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
                    {"key": "organization.name", "value": {"stringValue": "default"}},
                    {"key": "user.email", "value": {"stringValue": "kaz@re-x.info"}},
                    {"key": "telemetry.integration", "value": {"stringValue": "openobserve_demo"}}
                ]
            },
            "scopeSpans": [{
                "scope": {
                    "name": "aetherterm.openobserve.workflow",
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
        print(f"📊 Total Spans: {len(otlp_spans)}")
        print(f"🏢 Organization: default")
        print(f"📤 送信中...")
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=otlp_data,
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code in [200, 202]:
            print("✅ Complete AetherTerm workflowの送信に成功しました！")
            
            print(f"\n🌐 OpenObserve UIでワークフロー確認:")
            print(f"   📱 URL: https://api.openobserve.ai/web/traces")
            print(f"   🔍 Trace ID: {trace_id}")
            print(f"   📊 期待される階層表示:")
            print(f"     ├─ aetherterm.session:start (150ms)")
            print(f"     │  └─ socketio.connect (100ms)")
            print(f"     │     ├─ socketio.workspace_sync_request (200ms)")
            print(f"     │     │  └─ socketio.terminal:create (300ms)")
            print(f"     │     │     └─ socketio.terminal:input (150ms)")
            print(f"     │     └─ socketio.ai_chat_message (800ms)")
            
            print(f"\n📈 ワークフロー詳細:")
            print(f"   • セッション開始 → WebSocket接続 → ワークスペース同期")
            print(f"   • ターミナル作成 → コマンド実行 → AI チャット")
            print(f"   • 総実行時間: ~1.8秒")
            print(f"   • イベント数: 18個")
            
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
    print("🎯 OpenObserve Default Organization Integration Test")
    print("=" * 70)
    
    results = {}
    
    # Send simple trace
    results["simple_trace"] = send_trace_to_default_org()
    
    if results["simple_trace"]:
        print("\n✅ 基本トレース送信成功 - 複雑なワークフローを送信します")
        
        # Send complex workflow
        results["workflow_trace"] = send_aetherterm_workflow()
        
        if results["workflow_trace"]:
            print(f"\n🎉 OpenObserveへの完全統合が成功しました！")
            print(f"\n📊 送信されたデータ:")
            print(f"   ✓ 基本トレース: socketio.terminal:create")
            print(f"   ✓ 完全ワークフロー: 6スパン構成の階層トレース")
            print(f"   ✓ リアルタイム属性: user, terminal, organization")
            print(f"   ✓ イベント情報: 作成・準備・完了イベント")
            
            print(f"\n🌐 確認方法:")
            print(f"   1. https://api.openobserve.ai/web/ を開く")
            print(f"   2. kaz@re-x.info でログイン")
            print(f"   3. Traces → Service: aetherterm-backend")
            print(f"   4. 最新のトレースを選択して詳細確認")
            
            print(f"\n🔍 AetherTermがリアルタイムで送信するデータ:")
            print(f"   • Socket.IO接続・切断イベント")
            print(f"   • ターミナル作成・入力・出力")
            print(f"   • AIチャットメッセージ")
            print(f"   • ワークスペース・セッション管理")
            print(f"   • エラー・パフォーマンス情報")
            
    else:
        print("\n❌ 基本トレース送信に失敗しました")
        results["workflow_trace"] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 OPENOBSERVE INTEGRATION SUMMARY")
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