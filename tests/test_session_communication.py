#!/usr/bin/env python3
"""
Test inter-session communication functionality
"""

import asyncio
import socketio
import json
from datetime import datetime


class SessionCommunicationTest:
    def __init__(self, server_url="http://localhost:57575"):
        self.server_url = server_url
        self.sio = socketio.AsyncClient()
        self.responses = {}

        # Register event handlers
        self.sio.on("connect", self.on_connect)
        self.sio.on("session:created", self.on_session_created)
        self.sio.on("session:message:received", self.on_message_received)
        self.sio.on("error", self.on_error)

    async def on_connect(self):
        print(f"[{datetime.now()}] ✅ Connected to {self.server_url}")

    async def on_session_created(self, data):
        print(f"[{datetime.now()}] 🎉 Session created: {data['id']}")
        self.responses["session_created"] = data

    async def on_message_received(self, data):
        print(f"[{datetime.now()}] 💬 Message received: {json.dumps(data, indent=2)}")
        self.responses["message_received"] = data

    async def on_error(self, data):
        print(f"[{datetime.now()}] ❌ Error: {json.dumps(data, indent=2)}")
        self.responses["error"] = data

    async def connect(self):
        try:
            await self.sio.connect(self.server_url)
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    async def disconnect(self):
        await self.sio.disconnect()

    async def test_session_communication(self):
        """Test sending messages in a session"""

        # Step 1: Create session
        print("🚀 Creating session...")
        await self.sio.emit(
            "session:create",
            {"name": "Communication Test Session", "settings": {"allow_collaborators": True}},
        )
        await asyncio.sleep(1)

        if "session_created" not in self.responses:
            print("❌ Failed to create session")
            return

        session_data = self.responses["session_created"]
        session_id = session_data["id"]

        print(f"✅ Session created: {session_id}")

        # Step 2: Test text message
        print("\n💬 Testing text message...")
        await self.sio.emit(
            "session:message:send",
            {"sessionId": session_id, "content": "Hello from test client!", "type": "text"},
        )
        await asyncio.sleep(1)

        # Step 3: Test command message
        print("\n⚡ Testing command message...")
        await self.sio.emit(
            "session:message:send",
            {"sessionId": session_id, "content": "ls -la", "type": "command"},
        )
        await asyncio.sleep(1)

        # Step 4: Test notification message
        print("\n🔔 Testing notification message...")
        await self.sio.emit(
            "session:message:send",
            {
                "sessionId": session_id,
                "content": "Test completed successfully",
                "type": "notification",
            },
        )
        await asyncio.sleep(1)


async def run_communication_tests():
    """Run session communication tests"""
    client = SessionCommunicationTest()

    if not await client.connect():
        return

    try:
        print("=" * 60)
        print("🧪 AETHERTERM SESSION COMMUNICATION TESTS")
        print("=" * 60)

        await client.test_session_communication()

        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        for event, data in client.responses.items():
            print(f"✅ {event}: received")

        # Check if we received message responses
        if "message_received" in client.responses:
            print("✅ Session communication is working!")
        else:
            print("❌ No message responses received")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(run_communication_tests())
