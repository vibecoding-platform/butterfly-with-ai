#!/usr/bin/env python3
"""
OpenObserve UI debugging and trace verification
"""

import os
import sys
import time
import json
import requests

def check_openobserve_ui_access():
    """Check OpenObserve UI access and provide detailed instructions"""
    print("🔍 OpenObserve UI Access Debug Guide")
    print("=" * 60)
    
    print("📱 Step 1: OpenObserve UIアクセス")
    print("   URL: https://api.openobserve.ai/web/")
    print("   ブラウザで上記URLを開いてください")
    
    print("\n🔐 Step 2: ログイン情報")
    print("   Email: kaz@re-x.info")
    print("   Password: c8KGNeJfJIbZqFu7")
    
    print("\n🏢 Step 3: Organization確認")
    print("   ログイン後、Organization: 'default' を選択")
    print("   (画面右上または左上に組織名が表示されます)")
    
    print("\n📊 Step 4: Traces画面に移動")
    print("   左サイドメニューから 'Traces' をクリック")
    print("   または 'Observability' → 'Traces'")
    
    print("\n🕐 Step 5: 時間範囲設定")
    print("   Time Range を以下から選択:")
    print("   • Last 1 hour (推奨)")
    print("   • Last 24 hours")
    print("   • Custom range (今日の日付)")
    
    print("\n🔍 Step 6: フィルター設定")
    print("   以下のフィルターを試してください:")
    print("   • Service: 'aetherterm' で検索")
    print("   • Service: 'aetherterm-backend'")
    print("   • Service: 'aetherterm-test'")
    print("   • Operation: 'socketio' で検索")
    
    print("\n❓ トラブルシューティング:")
    print("   ✓ ログインできない → 認証情報を再確認")
    print("   ✓ Organizationが見つからない → 'default' を検索")
    print("   ✓ Tracesメニューがない → 権限を確認")
    print("   ✓ データが表示されない → 時間範囲を広げる")

def send_test_trace_with_current_time():
    """Send a test trace with current timestamp for immediate verification"""
    print("\n📤 現在時刻でのテストトレース送信")
    print("=" * 60)
    
    auth_header = "Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"
    endpoint = "https://api.openobserve.ai/api/default/v1/traces"
    
    # Generate unique identifiers
    current_time = int(time.time())
    trace_id = f"{current_time:032x}"
    span_id = f"{current_time & 0xFFFFFFFFFFFFFFFF:016x}"
    
    print(f"⏰ Current Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"📦 Trace ID: {trace_id}")
    print(f"📦 Span ID: {span_id}")
    
    # Create easily identifiable trace
    otlp_data = {
        "resourceSpans": [{
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "aetherterm-ui-debug"}},
                    {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                    {"key": "deployment.environment", "value": {"stringValue": "debug"}},
                    {"key": "test.type", "value": {"stringValue": "ui_verification"}},
                    {"key": "user.email", "value": {"stringValue": "kaz@re-x.info"}},
                    {"key": "organization.name", "value": {"stringValue": "default"}},
                    {"key": "debug.timestamp", "value": {"stringValue": str(current_time)}}
                ]
            },
            "scopeSpans": [{
                "scope": {
                    "name": "aetherterm.ui.debug",
                    "version": "1.0.0"
                },
                "spans": [{
                    "traceId": trace_id,
                    "spanId": span_id,
                    "name": "ui_debug_test_trace",
                    "kind": 1,
                    "startTimeUnixNano": str(current_time * 1000000000),
                    "endTimeUnixNano": str((current_time + 5) * 1000000000),
                    "attributes": [
                        {"key": "test.name", "value": {"stringValue": "OpenObserve UI Debug Test"}},
                        {"key": "test.timestamp", "value": {"stringValue": str(current_time)}},
                        {"key": "test.human_time", "value": {"stringValue": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}},
                        {"key": "debug.purpose", "value": {"stringValue": "Verify UI display"}},
                        {"key": "search.keyword", "value": {"stringValue": "UI_DEBUG_TEST"}},
                        {"key": "user.email", "value": {"stringValue": "kaz@re-x.info"}},
                        {"key": "organization.name", "value": {"stringValue": "default"}}
                    ],
                    "events": [
                        {
                            "timeUnixNano": str((current_time + 1) * 1000000000),
                            "name": "debug_test_started",
                            "attributes": [
                                {"key": "message", "value": {"stringValue": "This trace should be visible in OpenObserve UI"}},
                                {"key": "search.hint", "value": {"stringValue": "Look for UI_DEBUG_TEST"}}
                            ]
                        },
                        {
                            "timeUnixNano": str((current_time + 3) * 1000000000),
                            "name": "debug_test_completed",
                            "attributes": [
                                {"key": "result", "value": {"stringValue": "success"}},
                                {"key": "verification.status", "value": {"stringValue": "awaiting_ui_confirmation"}}
                            ]
                        }
                    ],
                    "status": {"code": 1, "message": "Debug test completed successfully"}
                }]
            }]
        }]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_header,
        "User-Agent": "aetherterm-ui-debug/1.0.0"
    }
    
    try:
        print(f"📡 送信先: {endpoint}")
        response = requests.post(
            endpoint,
            headers=headers,
            json=otlp_data,
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        if response.text:
            print(f"📄 Response: {response.text}")
        
        if response.status_code in [200, 202]:
            print("\n✅ デバッグトレース送信成功！")
            return trace_id, current_time
        else:
            print(f"\n❌ 送信失敗: {response.status_code}")
            return None, current_time
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None, current_time

def provide_detailed_ui_search_instructions(trace_id, timestamp):
    """Provide detailed instructions for finding the trace in UI"""
    print(f"\n🔍 OpenObserve UIでのトレース検索手順")
    print("=" * 60)
    
    human_time = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(timestamp))
    
    print(f"🎯 検索対象:")
    print(f"   Trace ID: {trace_id}")
    print(f"   Timestamp: {human_time}")
    print(f"   Service: aetherterm-ui-debug")
    
    print(f"\n📋 UI検索ステップ:")
    print(f"   1. https://api.openobserve.ai/web/ でログイン")
    print(f"   2. Organization: 'default' を確認")
    print(f"   3. 'Traces' メニューに移動")
    print(f"   4. Time Range: 'Last 1 hour' に設定")
    print(f"   5. 以下の検索条件を試す:")
    
    print(f"\n🔍 検索パターン:")
    print(f"   Pattern 1: Service = 'aetherterm-ui-debug'")
    print(f"   Pattern 2: Operation = 'ui_debug_test_trace'")
    print(f"   Pattern 3: Trace ID = '{trace_id}'")
    print(f"   Pattern 4: Text search = 'UI_DEBUG_TEST'")
    print(f"   Pattern 5: User = 'kaz@re-x.info'")
    
    print(f"\n📊 期待される表示:")
    print(f"   • Service Name: aetherterm-ui-debug")
    print(f"   • Operation Name: ui_debug_test_trace") 
    print(f"   • Duration: 5.00s")
    print(f"   • Status: OK")
    print(f"   • Timestamp: {human_time}")
    
    print(f"\n💡 トラブルシューティング:")
    print(f"   ❓ トレースが見つからない場合:")
    print(f"      1. Time Range を 'Last 24 hours' に拡大")
    print(f"      2. すべてのフィルターをクリア")
    print(f"      3. Refresh/Reload ボタンをクリック")
    print(f"      4. 別のブラウザで試す")
    print(f"      5. Organizationが 'default' か再確認")

def send_multiple_test_traces():
    """Send multiple test traces with different patterns for easier identification"""
    print(f"\n📊 複数パターンのテストトレース送信")
    print("=" * 60)
    
    auth_header = "Basic a2F6QHJlLXguaW5mbzpjOEtHTmVKZkpJYlpxRnU3"
    endpoint = "https://api.openobserve.ai/api/default/v1/traces"
    
    # Different service names for easier identification
    test_patterns = [
        {
            "service": "AETHERTERM-TEST-1",
            "operation": "test_pattern_alpha",
            "keyword": "ALPHA_TEST"
        },
        {
            "service": "AETHERTERM-TEST-2", 
            "operation": "test_pattern_beta",
            "keyword": "BETA_TEST"
        },
        {
            "service": "AETHERTERM-TEST-3",
            "operation": "test_pattern_gamma", 
            "keyword": "GAMMA_TEST"
        }
    ]
    
    successful_traces = []
    
    for i, pattern in enumerate(test_patterns):
        current_time = int(time.time()) + i
        trace_id = f"{current_time:032x}"
        span_id = f"{(current_time + i):016x}"
        
        otlp_data = {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": pattern["service"]}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                        {"key": "test.pattern", "value": {"stringValue": pattern["keyword"]}},
                        {"key": "user.email", "value": {"stringValue": "kaz@re-x.info"}},
                        {"key": "organization.name", "value": {"stringValue": "default"}}
                    ]
                },
                "scopeSpans": [{
                    "scope": {"name": "aetherterm.test", "version": "1.0.0"},
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": pattern["operation"],
                        "kind": 1,
                        "startTimeUnixNano": str(current_time * 1000000000),
                        "endTimeUnixNano": str((current_time + 2) * 1000000000),
                        "attributes": [
                            {"key": "test.keyword", "value": {"stringValue": pattern["keyword"]}},
                            {"key": "test.number", "value": {"stringValue": str(i + 1)}},
                            {"key": "search.term", "value": {"stringValue": f"AETHERTERM-TEST-{i + 1}"}}
                        ],
                        "status": {"code": 1, "message": ""}
                    }]
                }]
            }]
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": auth_header,
            "User-Agent": f"aetherterm-test-{i+1}/1.0.0"
        }
        
        try:
            print(f"📤 Sending {pattern['service']}...")
            response = requests.post(endpoint, headers=headers, json=otlp_data, timeout=30)
            
            if response.status_code in [200, 202]:
                print(f"✅ {pattern['service']} sent successfully")
                successful_traces.append({
                    "service": pattern["service"],
                    "trace_id": trace_id,
                    "keyword": pattern["keyword"],
                    "timestamp": current_time
                })
            else:
                print(f"❌ {pattern['service']} failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {pattern['service']} error: {e}")
    
    return successful_traces

def main():
    """Main debugging function"""
    print("🔧 OpenObserve UI Display Debug")
    print("=" * 70)
    
    # Step 1: Provide UI access instructions
    check_openobserve_ui_access()
    
    # Step 2: Send current time test trace
    trace_id, timestamp = send_test_trace_with_current_time()
    
    if trace_id:
        # Step 3: Provide detailed search instructions
        provide_detailed_ui_search_instructions(trace_id, timestamp)
        
        # Step 4: Send multiple test patterns
        successful_traces = send_multiple_test_traces()
        
        if successful_traces:
            print(f"\n🎯 検索可能なトレース:")
            for trace in successful_traces:
                human_time = time.strftime('%H:%M:%S', time.gmtime(trace['timestamp']))
                print(f"   • {trace['service']} - {trace['keyword']} - {human_time}")
            
            print(f"\n💡 UI検索のコツ:")
            print(f"   1. まず 'AETHERTERM-TEST' で検索")
            print(f"   2. Time Range を広めに設定")
            print(f"   3. Service一覧で上記のサービス名を探す")
            print(f"   4. 見つからない場合はページをリフレッシュ")
        
        print(f"\n📱 今すぐ確認:")
        print(f"   URL: https://api.openobserve.ai/web/")
        print(f"   Login: kaz@re-x.info")
        print(f"   検索: AETHERTERM-TEST または UI_DEBUG_TEST")
        
    else:
        print(f"\n❌ トレース送信に失敗しました")
        print(f"💡 以下を確認してください:")
        print(f"   • ネットワーク接続")
        print(f"   • OpenObserveアカウントの有効性")
        print(f"   • 組織への書き込み権限")

if __name__ == "__main__":
    main()