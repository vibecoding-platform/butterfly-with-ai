#!/usr/bin/env python3
"""
Test pane splitting functionality - tmux-style operations
"""

import asyncio
import socketio
import json
from datetime import datetime


class PaneSplittingTest:
    def __init__(self, server_url="http://localhost:57575"):
        self.server_url = server_url
        self.sio = socketio.AsyncClient()
        self.responses = {}

        # Register event handlers
        self.sio.on("connect", self.on_connect)
        self.sio.on("session:created", self.on_session_created)
        self.sio.on("pane:created", self.on_pane_created)
        self.sio.on("pane:split", self.on_pane_split)
        self.sio.on("error", self.on_error)

    async def on_connect(self):
        print(f"[{datetime.now()}] ✅ Connected to {self.server_url}")

    async def on_session_created(self, data):
        print(f"[{datetime.now()}] 🎉 Session created")
        self.responses["session_created"] = data

    async def on_pane_created(self, data):
        print(f"[{datetime.now()}] 🔲 Pane created: {json.dumps(data, indent=2)}")
        self.responses["pane_created"] = data

    async def on_pane_split(self, data):
        print(f"[{datetime.now()}] ✂️ Pane split: {json.dumps(data, indent=2)}")
        self.responses["pane_split"] = data

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

    async def create_session_and_test_splitting(self):
        """Create session and test various pane splitting scenarios"""

        # Step 1: Create session
        print("🚀 Creating session...")
        await self.sio.emit(
            "session:create",
            {"name": "Pane Split Test Session", "settings": {"allow_collaborators": True}},
        )
        await asyncio.sleep(1)

        if "session_created" not in self.responses:
            print("❌ Failed to create session")
            return

        session_data = self.responses["session_created"]
        session_id = session_data["id"]
        tab_id = session_data["tabs"][0]["id"]
        original_pane_id = session_data["tabs"][0]["panes"][0]["id"]

        print(f"✅ Session created: {session_id}")
        print(f"✅ Tab ID: {tab_id}")
        print(f"✅ Original Pane ID: {original_pane_id}")

        # Step 2: Test horizontal split (tmux Ctrl+B %)
        print("\n🔄 Testing horizontal split (tmux Ctrl+B %)...")
        await self.sio.emit(
            "pane:split",
            {
                "sessionId": session_id,
                "tabId": tab_id,
                "paneId": original_pane_id,
                "direction": "horizontal",
            },
        )
        await asyncio.sleep(2)

        # Step 3: Test vertical split (tmux Ctrl+B ")
        print('\n🔄 Testing vertical split (tmux Ctrl+B ")...')
        await self.sio.emit(
            "pane:split",
            {
                "sessionId": session_id,
                "tabId": tab_id,
                "paneId": original_pane_id,
                "direction": "vertical",
            },
        )
        await asyncio.sleep(2)

        # Step 4: Check final state
        print("\n📊 Final pane layout:")
        if "pane_split" in self.responses:
            print("✅ Pane splitting successful!")
        else:
            print("❌ No pane split response received")


async def run_pane_tests():
    """Run pane splitting tests"""
    client = PaneSplittingTest()

    if not await client.connect():
        return

    try:
        print("=" * 60)
        print("🧪 AETHERTERM PANE SPLITTING TESTS (tmux-style)")
        print("=" * 60)

        await client.create_session_and_test_splitting()

        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        for event, data in client.responses.items():
            print(f"✅ {event}: received")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(run_pane_tests())
