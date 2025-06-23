#!/usr/bin/env python3
"""
Simple test client for AetherTerm session management functionality
"""

import asyncio
import socketio
import json
from datetime import datetime


class SessionTestClient:
    def __init__(self, server_url="http://localhost:57575"):
        self.server_url = server_url
        self.sio = socketio.AsyncClient()
        self.responses = {}

        # Register event handlers
        self.sio.on("connect", self.on_connect)
        self.sio.on("disconnect", self.on_disconnect)
        self.sio.on("session:created", self.on_session_created)
        self.sio.on("session:joined", self.on_session_joined)
        self.sio.on("tab:created", self.on_tab_created)
        self.sio.on("pane:created", self.on_pane_created)
        self.sio.on("session:message:received", self.on_message_received)
        self.sio.on("error", self.on_error)

    async def on_connect(self):
        print(f"[{datetime.now()}] ✅ Connected to {self.server_url}")

    async def on_disconnect(self):
        print(f"[{datetime.now()}] ❌ Disconnected from server")

    async def on_session_created(self, data):
        print(f"[{datetime.now()}] 🎉 Session created: {json.dumps(data, indent=2)}")
        self.responses["session_created"] = data

    async def on_session_joined(self, data):
        print(f"[{datetime.now()}] 👥 Session joined: {json.dumps(data, indent=2)}")
        self.responses["session_joined"] = data

    async def on_tab_created(self, data):
        print(f"[{datetime.now()}] 📋 Tab created: {json.dumps(data, indent=2)}")
        self.responses["tab_created"] = data

    async def on_pane_created(self, data):
        print(f"[{datetime.now()}] 🔲 Pane created: {json.dumps(data, indent=2)}")
        self.responses["pane_created"] = data

    async def on_message_received(self, data):
        print(f"[{datetime.now()}] 💬 Message received: {json.dumps(data, indent=2)}")
        self.responses["message_received"] = data

    async def on_error(self, data):
        print(f"[{datetime.now()}] ❌ Error: {json.dumps(data, indent=2)}")
        self.responses["error"] = data

    async def connect(self):
        """Connect to the server"""
        try:
            await self.sio.connect(self.server_url)
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from server"""
        await self.sio.disconnect()

    async def create_session(self, name="Test Session"):
        """Create a new session"""
        print(f"\n🚀 Creating session: {name}")
        await self.sio.emit(
            "session:create",
            {
                "name": name,
                "settings": {"allow_collaborators": True, "allow_observers": True, "max_users": 10},
            },
        )
        await asyncio.sleep(1)  # Wait for response

    async def join_session(self, session_id, permission="observer"):
        """Join an existing session"""
        print(f"\n👥 Joining session {session_id} as {permission}")
        await self.sio.emit("session:join", {"session_id": session_id, "permission": permission})
        await asyncio.sleep(1)  # Wait for response

    async def create_tab(self, session_id, tab_type="terminal", title="New Tab"):
        """Create a new tab in session"""
        print(f"\n📋 Creating {tab_type} tab: {title}")
        await self.sio.emit(
            "tab:create", {"session_id": session_id, "tab_type": tab_type, "title": title}
        )
        await asyncio.sleep(1)  # Wait for response

    async def split_pane(self, session_id, tab_id, pane_id, direction="horizontal"):
        """Split a pane in a tab"""
        print(f"\n🔲 Splitting pane {pane_id} {direction}ly")
        await self.sio.emit(
            "pane:split",
            {
                "session_id": session_id,
                "tab_id": tab_id,
                "pane_id": pane_id,
                "direction": direction,
            },
        )
        await asyncio.sleep(1)  # Wait for response

    async def send_message(self, session_id, message, message_type="text"):
        """Send message to session"""
        print(f"\n💬 Sending message: {message}")
        await self.sio.emit(
            "session:message:send",
            {"session_id": session_id, "message": message, "message_type": message_type},
        )
        await asyncio.sleep(1)  # Wait for response


async def run_session_tests():
    """Run comprehensive session management tests"""
    client = SessionTestClient()

    if not await client.connect():
        return

    try:
        print("=" * 60)
        print("🧪 AETHERTERM SESSION MANAGEMENT TESTS")
        print("=" * 60)

        # Test 1: Create session
        await client.create_session("Test Session 1")

        # Check if session was created
        if "session_created" in client.responses:
            session_data = client.responses["session_created"]
            session_id = session_data.get("session", {}).get("id")

            if session_id:
                print(f"✅ Session created successfully with ID: {session_id}")

                # Test 2: Create a terminal tab
                await client.create_tab(session_id, "terminal", "Terminal 1")

                # Check if tab was created
                if "tab_created" in client.responses:
                    tab_data = client.responses["tab_created"]
                    tab_id = tab_data.get("tab", {}).get("id")

                    if tab_id:
                        print(f"✅ Tab created successfully with ID: {tab_id}")

                        # Test 3: Split pane (assuming first pane exists)
                        # For testing purposes, let's assume pane_id is generated or available
                        first_pane_id = "pane-1"  # This would normally come from tab creation
                        await client.split_pane(session_id, tab_id, first_pane_id, "horizontal")

                        # Test 4: Send message
                        await client.send_message(session_id, "Hello from test client!")

                    else:
                        print("❌ Tab creation failed - no tab ID returned")
                else:
                    print("❌ Tab creation failed - no response received")
            else:
                print("❌ Session creation failed - no session ID returned")
        else:
            print("❌ Session creation failed - no response received")

        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        for event, data in client.responses.items():
            print(f"✅ {event}: {type(data).__name__}")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(run_session_tests())
