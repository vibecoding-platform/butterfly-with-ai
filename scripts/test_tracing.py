#!/usr/bin/env python3
"""
Test script for AetherTerm OpenTelemetry tracing
Tests both Python backend telemetry and frontend-backend correlation
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Any

import socketio
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TracingTestClient:
    """Test client for Socket.IO tracing"""
    
    def __init__(self, server_url: str = "http://localhost:57575"):
        self.server_url = server_url
        self.sio = socketio.AsyncClient()
        self.events_received = []
        self.trace_ids = []
        
        # Register event handlers
        self.sio.on("connect", self.on_connect)
        self.sio.on("disconnect", self.on_disconnect)
        self.sio.on("terminal:created", self.on_terminal_created)
        self.sio.on("terminal:data", self.on_terminal_data)
        self.sio.on("workspace:sync:response", self.on_workspace_sync)
        self.sio.on("ai_chat_chunk", self.on_ai_chat_chunk)
    
    async def on_connect(self):
        logger.info("✅ Connected to server")
    
    async def on_disconnect(self):
        logger.info("❌ Disconnected from server")
    
    async def on_terminal_created(self, data):
        logger.info(f"🖥️ Terminal created: {data}")
        self.events_received.append(("terminal_created", data))
        
        # Extract trace ID if present
        if "_trace" in data:
            self.trace_ids.append(data["_trace"].get("traceId"))
    
    async def on_terminal_data(self, data):
        logger.info(f"📄 Terminal data: {data.get('data', '')[:50]}...")
        self.events_received.append(("terminal_data", data))
    
    async def on_workspace_sync(self, data):
        logger.info(f"🔄 Workspace sync: {data}")
        self.events_received.append(("workspace_sync", data))
    
    async def on_ai_chat_chunk(self, data):
        logger.info(f"🤖 AI chat chunk: {data.get('chunk', '')[:50]}...")
        self.events_received.append(("ai_chat_chunk", data))
    
    async def connect(self):
        """Connect to the server"""
        await self.sio.connect(self.server_url)
    
    async def disconnect(self):
        """Disconnect from server"""
        await self.sio.disconnect()
    
    async def test_workspace_sync(self):
        """Test workspace synchronization with tracing"""
        logger.info("🧪 Testing workspace sync...")
        
        # Generate trace context
        trace_context = {
            "traceId": f"{int(time.time() * 1000000):032x}"[:32],
            "spanId": f"{int(time.time() * 1000):016x}"[:16],
            "sampled": True
        }
        
        request_data = {
            "_trace": trace_context,
            "_requestId": f"test_workspace_sync_{int(time.time())}"
        }
        
        await self.sio.emit("workspace:sync:request", request_data)
        
        # Wait for response
        await asyncio.sleep(2)
        
        return trace_context["traceId"]
    
    async def test_terminal_creation(self):
        """Test terminal creation with tracing"""
        logger.info("🧪 Testing terminal creation...")
        
        # Generate trace context
        trace_context = {
            "traceId": f"{int(time.time() * 1000000):032x}"[:32],
            "spanId": f"{int(time.time() * 1000):016x}"[:16],
            "sampled": True
        }
        
        request_data = {
            "terminalId": "test-terminal-123",
            "paneId": "test-pane-123",
            "cols": 80,
            "rows": 24,
            "_trace": trace_context,
            "_requestId": f"test_terminal_create_{int(time.time())}"
        }
        
        await self.sio.emit("terminal:create", request_data)
        
        # Wait for response
        await asyncio.sleep(3)
        
        return trace_context["traceId"]
    
    async def test_ai_chat(self):
        """Test AI chat with tracing"""
        logger.info("🧪 Testing AI chat...")
        
        # Generate trace context
        trace_context = {
            "traceId": f"{int(time.time() * 1000000):032x}"[:32],
            "spanId": f"{int(time.time() * 1000):016x}"[:16],
            "sampled": True
        }
        
        request_data = {
            "message": "Hello, can you help me with terminal commands?",
            "message_id": f"test_msg_{int(time.time())}",
            "_trace": trace_context,
            "_requestId": f"test_ai_chat_{int(time.time())}"
        }
        
        await self.sio.emit("ai_chat_message", request_data)
        
        # Wait for response
        await asyncio.sleep(5)
        
        return trace_context["traceId"]
    
    async def verify_traces_in_openobserve(self, trace_id: str) -> bool:
        """Verify that traces appear in OpenObserve"""
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        username = os.getenv("OTEL_EXPORTER_OTLP_USERNAME")
        password = os.getenv("OTEL_EXPORTER_OTLP_PASSWORD")
        
        if not all([endpoint, username, password]):
            logger.warning("⚠️ OpenObserve credentials not configured, skipping verification")
            return False
        
        # Extract base URL and organization
        base_url = endpoint.replace("/v1/traces", "")
        
        # Query for traces
        try:
            import base64
            auth_header = base64.b64encode(f"{username}:{password}".encode()).decode()
            
            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/json"
            }
            
            # Search for traces (this depends on OpenObserve's API)
            search_url = f"{base_url}/api/default/_search"
            query = {
                "query": {
                    "match": {
                        "trace_id": trace_id
                    }
                }
            }
            
            response = requests.post(search_url, headers=headers, json=query, timeout=10)
            
            if response.status_code == 200:
                results = response.json()
                trace_count = len(results.get("hits", []))
                logger.info(f"✅ Found {trace_count} traces for ID {trace_id}")
                return trace_count > 0
            else:
                logger.warning(f"⚠️ OpenObserve search failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verifying traces: {e}")
            return False


async def main():
    """Main test function"""
    logger.info("🚀 Starting AetherTerm tracing tests...")
    
    # Check if telemetry is enabled
    if os.getenv("OTEL_ENABLED", "false").lower() != "true":
        logger.error("❌ OTEL_ENABLED is not set to true. Please configure telemetry.")
        return
    
    client = TracingTestClient()
    
    try:
        # Connect to server
        await client.connect()
        
        # Test different operations
        test_results = {}
        
        # Test workspace sync
        trace_id = await client.test_workspace_sync()
        test_results["workspace_sync"] = trace_id
        
        # Test terminal creation
        trace_id = await client.test_terminal_creation()
        test_results["terminal_creation"] = trace_id
        
        # Test AI chat (if enabled)
        try:
            trace_id = await client.test_ai_chat()
            test_results["ai_chat"] = trace_id
        except Exception as e:
            logger.warning(f"⚠️ AI chat test failed: {e}")
        
        # Wait a bit for traces to be exported
        logger.info("⏳ Waiting for traces to be exported...")
        await asyncio.sleep(10)
        
        # Verify traces in OpenObserve
        logger.info("🔍 Verifying traces in OpenObserve...")
        verification_results = {}
        
        for test_name, trace_id in test_results.items():
            if trace_id:
                verified = await client.verify_traces_in_openobserve(trace_id)
                verification_results[test_name] = verified
                logger.info(f"📊 {test_name}: {'✅ Verified' if verified else '❌ Not found'}")
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("📋 TEST SUMMARY")
        logger.info("="*50)
        
        for test_name, trace_id in test_results.items():
            verified = verification_results.get(test_name, False)
            status = "✅ PASS" if verified else "❌ FAIL"
            logger.info(f"{test_name}: {status} (trace: {trace_id})")
        
        logger.info(f"\nTotal events received: {len(client.events_received)}")
        logger.info(f"Total trace IDs generated: {len(client.trace_ids)}")
        
        # Print event details
        if client.events_received:
            logger.info("\n📝 Event Details:")
            for event_type, data in client.events_received[-5:]:  # Last 5 events
                logger.info(f"  {event_type}: {json.dumps(data, indent=2)}")
        
        # Final result
        all_passed = all(verification_results.values())
        logger.info(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())