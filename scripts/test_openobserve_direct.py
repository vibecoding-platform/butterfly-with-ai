#!/usr/bin/env python3
"""
Direct OpenObserve connection test with provided credentials
"""

import os
import sys
import time
import json
import requests

def test_openobserve_direct():
    """Test OpenObserve with provided credentials"""
    print("🌩️ OpenObserve Direct Connection Test")
    print("=" * 60)
    
    # Use provided credentials
    endpoint = "https://api.openobserve.ai/api/default/v1/traces"
    auth_header = "Basic cm9vdEBleGFtcGxlLmNvbTpDb21wbGV4cGFzcyMxMjM="
    
    print(f"📡 Endpoint: {endpoint}")
    print(f"🔐 Auth: Basic ***")
    
    # Create test trace data
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
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_header,
        "User-Agent": "aetherterm-openobserve-test/1.0.0"
    }
    
    print(f"\n📦 Trace ID: {trace_id}")
    print(f"📦 Span ID: {span_id}")
    print(f"📤 送信中...")
    
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=otlp_data,
            timeout=30
        )
        
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        
        if response.text:
            print(f"📄 Response Body: {response.text[:500]}")
        
        if response.status_code in [200, 202]:
            print("\n✅ トレースデータの送信に成功しました！")
            
            # Show OpenObserve UI URL
            print(f"\n🌐 OpenObserve UIでデータを確認:")
            print(f"   URL: https://api.openobserve.ai/web/traces")
            print(f"   Service: aetherterm-test")
            print(f"   Trace ID: {trace_id}")
            print(f"   Time Range: 最近5分間")
            
            return True
        elif response.status_code == 401:
            print("\n❌ 認証エラー: 認証情報を確認してください")
            print("💡 OpenObserveアカウントとパスワードが正しいか確認")
            return False
        elif response.status_code == 403:
            print("\n❌ 権限エラー: アカウントにトレース書き込み権限がありません")
            return False
        elif response.status_code == 404:
            print("\n❌ エンドポイントが見つかりません")
            print("💡 組織名やエンドポイントURLを確認してください")
            return False
        else:
            print(f"\n❌ 送信に失敗: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ エラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_openobserve_organizations():
    """Test OpenObserve organizations endpoint"""
    print("\n🏢 Organizations Endpoint Test")
    print("=" * 50)
    
    endpoint = "https://api.openobserve.ai/api/default/organizations"
    auth_header = "Basic cm9vdEBleGFtcGxlLmNvbTpDb21wbGV4cGFzcyMxMjM="
    
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
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 認証成功")
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
            print(f"❌ その他のエラー: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False

def main():
    """Main test function"""
    print("🔍 OpenObserve Direct Test with Provided Credentials")
    print("=" * 70)
    
    # Test organizations endpoint first
    auth_success = test_openobserve_organizations()
    
    if auth_success:
        print("\n✅ 認証が成功しました。トレースデータを送信します...")
        trace_success = test_openobserve_direct()
        
        if trace_success:
            print("\n🎉 OpenObserveとの統合が完全に動作しています！")
            print("📊 データはOpenObserve UIで確認できます")
        else:
            print("\n⚠️ 認証は成功しましたが、トレース送信で問題が発生")
    else:
        print("\n❌ 認証に失敗しました")
        print("💡 認証情報またはエンドポイントを確認してください")
        
        # Still try trace endpoint to see what happens
        print("\n🔄 それでもトレースエンドポイントをテストします...")
        test_openobserve_direct()
    
    return auth_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)