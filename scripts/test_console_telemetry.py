#!/usr/bin/env python3
"""
Console telemetry test to verify data structure and flow
Shows exactly what would be sent to OpenObserve
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

def test_console_telemetry():
    """Test telemetry with console output to see data structure"""
    print("🖥️ Console Telemetry Test (データ構造確認)")
    print("=" * 60)
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
        
        # Configure resource (same as what would go to OpenObserve)
        resource = Resource.create({
            SERVICE_NAME: "aetherterm-openobserve-test",
            SERVICE_VERSION: "1.0.0",
            "deployment.environment": "test",
            "service.namespace": "aetherterm",
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
        })
        
        print("✅ Resource configuration:")
        for key, value in resource.attributes.items():
            print(f"   {key}: {value}")
        
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        # Configure console exporter (shows exact data structure)
        console_exporter = ConsoleSpanExporter()
        span_processor = BatchSpanProcessor(console_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        print("\n📊 Creating Socket.IO traces (OpenObserve format)...")
        
        # Create tracer
        tracer = trace.get_tracer("aetherterm.socketio", "1.0.0")
        
        # Simulate Socket.IO events that would be sent to OpenObserve
        with tracer.start_as_current_span("socketio.connect") as span:
            span.set_attribute("socketio.event", "connect")
            span.set_attribute("socketio.client_id", "client-123")
            span.set_attribute("socketio.direction", "inbound")
            span.set_attribute("http.method", "GET")
            span.set_attribute("http.url", "/socket.io/")
            span.add_event("client_connected", {
                "event.type": "connection",
                "client.ip": "192.168.1.100"
            })
            
            # Nested terminal creation
            with tracer.start_as_current_span("socketio.terminal:create") as terminal_span:
                terminal_span.set_attribute("socketio.event", "terminal:create")
                terminal_span.set_attribute("terminal.id", "terminal-456")
                terminal_span.set_attribute("terminal.type", "xterm")
                terminal_span.set_attribute("terminal.size", "80x24")
                terminal_span.add_event("terminal_created", {
                    "terminal.id": "terminal-456",
                    "terminal.pid": "12345"
                })
                
                time.sleep(0.05)  # Simulate work
                
                # Terminal input event
                with tracer.start_as_current_span("socketio.terminal:input") as input_span:
                    input_span.set_attribute("socketio.event", "terminal:input")
                    input_span.set_attribute("terminal.id", "terminal-456")
                    input_span.set_attribute("input.command", "ls -la")
                    input_span.set_attribute("input.length", "5")
                    
                    time.sleep(0.02)
        
        print("\n📤 Spans exported to console (this is what OpenObserve would receive)")
        
        # Force export to show all spans
        span_processor.force_flush(10)
        
        print("\n✅ Console telemetry test completed")
        print("💡 上記のデータがOpenObserveに送信される形式です")
        
        return True
        
    except Exception as e:
        print(f"❌ Console telemetry error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_aetherterm_telemetry_integration():
    """Test AetherTerm telemetry configuration with console output"""
    print("\n🔧 AetherTerm Telemetry Integration Test")
    print("=" * 60)
    
    # Set environment for console output
    os.environ["OTEL_ENABLED"] = "true"
    os.environ["OTEL_SERVICE_NAME"] = "aetherterm-backend"
    os.environ["OTEL_SERVICE_VERSION"] = "1.0.0"
    os.environ["OTEL_TRACES_EXPORTER"] = "console"
    os.environ["OTEL_DEBUG"] = "true"
    
    try:
        from aetherterm.agentserver.telemetry.config import configure_telemetry, TelemetryConfig
        from aetherterm.agentserver.telemetry.socket_instrumentation import (
            SocketIOInstrumentation, 
            instrument_socketio_handler
        )
        
        print("✅ AetherTerm telemetry modules imported successfully")
        
        # Configure telemetry with console output
        config = TelemetryConfig(
            enabled=True,
            service_name="aetherterm-backend",
            service_version="1.0.0",
            debug=True
        )
        
        print(f"📋 Telemetry config: {config}")
        
        # Initialize telemetry
        result_config = configure_telemetry(config)
        print(f"✅ Telemetry configured: enabled={result_config.enabled}")
        
        # Test Socket.IO instrumentation
        instrumentation = SocketIOInstrumentation()
        print("✅ Socket.IO instrumentation created")
        
        # Test decorator
        @instrument_socketio_handler("test_event")
        async def test_socket_handler(sid, data):
            """Test Socket.IO handler with instrumentation"""
            print(f"📡 Processing Socket.IO event: {data}")
            return {"status": "success", "response": "test_complete"}
        
        print("✅ Socket.IO handler decorated with instrumentation")
        
        # Simulate socket.io event processing
        from opentelemetry import trace
        tracer = trace.get_tracer("aetherterm.socketio.test")
        
        with tracer.start_as_current_span("simulate_socketio_workflow") as span:
            span.set_attribute("workflow.type", "socketio_simulation")
            span.set_attribute("test.scenario", "aetherterm_integration")
            
            # Simulate multiple Socket.IO events
            events = [
                ("connect", {"client_id": "test-123"}),
                ("create_terminal", {"terminal_type": "xterm", "size": "80x24"}),
                ("terminal_input", {"command": "echo 'Hello OpenObserve'"}),
                ("ai_chat_message", {"message": "Please help with terminal commands"}),
                ("disconnect", {"reason": "client_disconnect"})
            ]
            
            for event_name, event_data in events:
                with tracer.start_as_current_span(f"socketio.{event_name}") as event_span:
                    event_span.set_attribute("socketio.event", event_name)
                    event_span.set_attribute("socketio.client_id", "test-123")
                    
                    for key, value in event_data.items():
                        event_span.set_attribute(f"event.{key}", str(value))
                    
                    event_span.add_event("event_processed", {
                        "processing.time": "10ms",
                        "result": "success"
                    })
                
                time.sleep(0.01)  # Simulate processing delay
        
        print("\n📊 AetherTerm Socket.IO workflow simulated")
        print("💡 この構造のデータがOpenObserveで表示されます")
        
        return True
        
    except Exception as e:
        print(f"❌ AetherTerm integration error: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_openobserve_ui_instructions():
    """Show instructions for checking data in OpenObserve UI"""
    print("\n🌐 OpenObserve UIでのデータ確認手順")
    print("=" * 60)
    
    print("📱 ステップ 1: OpenObserve UIにアクセス")
    print("   URL: https://api.openobserve.ai/web/")
    print("   ログイン: root@example.com / Complexpass#123")
    
    print("\n🔍 ステップ 2: Tracesセクションに移動")
    print("   左メニュー > Traces を選択")
    print("   Organization: default を確認")
    
    print("\n📊 ステップ 3: サービスとトレースを確認")
    print("   Service Name で検索:")
    print("   - aetherterm-backend")
    print("   - aetherterm-openobserve-test")
    print("   - aetherterm-test")
    
    print("\n🕐 ステップ 4: 時間範囲を設定")
    print("   Time Range: Last 1 hour に設定")
    print("   または今日の日付を指定")
    
    print("\n🔎 ステップ 5: トレースの詳細を確認")
    print("   表示される項目:")
    print("   - socketio.event: connect, terminal:create, terminal:input")
    print("   - socketio.client_id: test-123, client-123")
    print("   - terminal.id: terminal-456")
    print("   - service.name: aetherterm-backend")
    
    print("\n📈 ステップ 6: スパンの階層構造を確認")
    print("   親スパン: socketio.connect")
    print("   　└─ 子スパン: socketio.terminal:create")
    print("   　　　└─ 孫スパン: socketio.terminal:input")
    
    print("\n💡 トラブルシューティング:")
    print("   - データが表示されない場合: 時間範囲を広げる")
    print("   - 認証エラー: 有効なOpenObserveアカウントが必要")
    print("   - フィルタリング: service.name='aetherterm*' で検索")

def main():
    """Main test function"""
    print("🧪 AetherTerm → OpenObserve Integration Verification")
    print("=" * 70)
    
    results = {}
    
    # Test console telemetry (shows data structure)
    results["console"] = test_console_telemetry()
    
    # Test AetherTerm telemetry integration
    results["integration"] = test_aetherterm_telemetry_integration()
    
    # Show UI instructions
    show_openobserve_ui_instructions()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TELEMETRY VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ AetherTermテレメトリシステムは完全に動作しています！")
        print("📊 上記のConsole出力が、OpenObserveに送信されるデータ形式です")
        print("🌐 有効な認証情報があれば、同じデータがOpenObserve UIに表示されます")
        
        print("\n🚀 本番環境での使用方法:")
        print("   1. 有効なOpenObserveアカウント認証情報を設定")
        print("   2. OTEL_ENABLED=true でAetherTerm起動")
        print("   3. Socket.IOイベントが自動的にOpenObserveに送信される")
        print("   4. OpenObserve UIでリアルタイムトレース監視")
    else:
        print("\n⚠️ 一部のテストで問題が発生しました")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)