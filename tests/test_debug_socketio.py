#!/usr/bin/env python3
"""
Debug Socket.IO connection and workspace events
"""

import asyncio
import socketio
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


async def test_debug_socketio():
    """Test Socket.IO connection with debug logging"""
    print("🔧 DEBUG SOCKET.IO TEST")
    print("=" * 50)

    sio = socketio.AsyncClient(logger=True, engineio_logger=True)

    events_received = []

    @sio.event
    async def connect():
        print("✅ Connected to server")
        print("📧 Emitting workspace:initialize...")
        await sio.emit(
            "workspace:initialize",
            {"environ": {"REMOTE_ADDR": "127.0.0.1", "HTTP_USER_AGENT": "Debug Test Client"}},
        )

    @sio.event
    async def workspace_initialized(data):
        events_received.append(("workspace:initialized", data))
        print(f"✅ workspace:initialized received: {data}")

    @sio.event
    async def workspace_error(data):
        events_received.append(("workspace:error", data))
        print(f"❌ workspace:error received: {data}")

    @sio.event
    async def workspace_tab_created(data):
        events_received.append(("workspace:tab_created", data))
        print(f"✅ workspace:tab_created received: {data}")

    @sio.event
    async def disconnect():
        print("❌ Disconnected from server")

    try:
        print("📡 Connecting to server...")
        await sio.connect("http://localhost:57575")

        # Wait for connection and initialization
        await asyncio.sleep(3)

        print("🏗️ Creating test tab...")
        await sio.emit("workspace:tab:create", {"title": "Debug Test Tab", "type": "terminal"})

        # Wait for tab creation
        await asyncio.sleep(2)

        print(f"\n📊 Total events received: {len(events_received)}")
        for i, (event_type, data) in enumerate(events_received):
            print(f"  {i + 1}. {event_type}: {data}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        if sio.connected:
            await sio.disconnect()
            print("🔌 Disconnected")


if __name__ == "__main__":
    asyncio.run(test_debug_socketio())
