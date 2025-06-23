#!/usr/bin/env python3
"""
Simple test for workspace initialization and multi-window sync
"""

import asyncio
import json
import socketio


async def test_workspace_initialization():
    """Test basic workspace initialization"""
    print("🧪 SIMPLE WORKSPACE INITIALIZATION TEST")
    print("=" * 50)

    # Create client
    sio = socketio.AsyncClient()

    events_received = []

    @sio.event
    async def workspace_initialized(data):
        events_received.append(("workspace:initialized", data))
        print(f"✅ Workspace initialized: {json.dumps(data, indent=2)}")

    @sio.event
    async def workspace_error(data):
        events_received.append(("workspace:error", data))
        print(f"❌ Workspace error: {data}")

    try:
        # Connect to server
        print("📡 Connecting to server...")
        await sio.connect("http://localhost:57575")
        print("✅ Connected successfully")

        # Initialize workspace
        print("🚀 Initializing workspace...")
        await sio.emit(
            "workspace:initialize",
            {"environ": {"REMOTE_ADDR": "127.0.0.1", "HTTP_USER_AGENT": "Simple Test Client"}},
        )

        # Wait for response
        await asyncio.sleep(2)

        print(f"\n📊 Events received: {len(events_received)}")
        for event_type, data in events_received:
            print(f"  - {event_type}: {json.dumps(data) if isinstance(data, dict) else data}")

        # Test tab creation
        print("\n🏗️ Creating test tab...")
        await sio.emit("workspace:tab:create", {"title": "Test Tab", "type": "terminal"})

        await asyncio.sleep(1)

        print(f"\n📊 Final events received: {len(events_received)}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        if sio.connected:
            await sio.disconnect()
            print("🔌 Disconnected")


if __name__ == "__main__":
    asyncio.run(test_workspace_initialization())
