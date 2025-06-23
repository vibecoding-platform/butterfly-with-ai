#!/usr/bin/env python3
"""
Multi-window synchronization test for AetherTerm workspace functionality
"""

import asyncio
import socketio
import json
from datetime import datetime


class MultiWindowTestClient:
    def __init__(self, client_name: str, server_url="http://localhost:57575"):
        self.client_name = client_name
        self.server_url = server_url
        self.sio = socketio.AsyncClient()
        self.workspace_state = {}
        self.events_received = []

        # Register event handlers
        self.sio.on("connect", self.on_connect)
        self.sio.on("disconnect", self.on_disconnect)
        self.sio.on("workspace:initialized", self.on_workspace_initialized)
        self.sio.on("workspace:tab_created", self.on_tab_created)
        self.sio.on("workspace:tab_switched", self.on_tab_switched)
        self.sio.on("workspace:tab_closed", self.on_tab_closed)
        self.sio.on("workspace:pane_created", self.on_pane_created)
        self.sio.on("workspace:ui_updated", self.on_ui_updated)
        self.sio.on("workspace:error", self.on_error)

    async def on_connect(self):
        print(f"[{self.client_name}] ✅ Connected to {self.server_url}")

        # Initialize workspace
        await self.sio.emit("workspace:initialize", {"environ": {}})

    async def on_disconnect(self):
        print(f"[{self.client_name}] ❌ Disconnected from server")

    async def on_workspace_initialized(self, data):
        self.workspace_state = data
        self.events_received.append(("workspace:initialized", data))
        print(f"[{self.client_name}] 🚀 Workspace initialized:")
        print(f"  - Tabs: {len(data.get('tabs', []))}")
        print(f"  - Connected clients: {data.get('connectedClients', 0)}")
        print(f"  - Active tab: {data.get('uiState', {}).get('activeTabId', 'None')}")

    async def on_tab_created(self, data):
        self.events_received.append(("workspace:tab_created", data))
        tab = data.get("tab", {})
        print(
            f"[{self.client_name}] 📋 Tab created: {tab.get('title', 'Unknown')} ({tab.get('id', 'Unknown')})"
        )

    async def on_tab_switched(self, data):
        self.events_received.append(("workspace:tab_switched", data))
        print(f"[{self.client_name}] 🔄 Tab switched to: {data.get('tabId', 'Unknown')}")

    async def on_tab_closed(self, data):
        self.events_received.append(("workspace:tab_closed", data))
        print(f"[{self.client_name}] ❌ Tab closed: {data.get('tabId', 'Unknown')}")

    async def on_pane_created(self, data):
        self.events_received.append(("workspace:pane_created", data))
        pane = data.get("pane", {})
        print(
            f"[{self.client_name}] 🔲 Pane created: {pane.get('title', 'Unknown')} ({data.get('direction', 'Unknown')} split)"
        )

    async def on_ui_updated(self, data):
        self.events_received.append(("workspace:ui_updated", data))
        updates = data.get("updates", {})
        print(f"[{self.client_name}] 🎛️ UI updated: {json.dumps(updates)}")

    async def on_error(self, data):
        self.events_received.append(("workspace:error", data))
        print(f"[{self.client_name}] ❌ Error: {data.get('error', 'Unknown error')}")

    async def connect(self):
        """Connect to the server"""
        try:
            await self.sio.connect(self.server_url)
            return True
        except Exception as e:
            print(f"[{self.client_name}] ❌ Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from server"""
        await self.sio.disconnect()

    async def create_tab(self, title=None):
        """Create a new tab"""
        print(f"[{self.client_name}] 🚀 Creating tab: {title or 'New Tab'}")
        await self.sio.emit("workspace:tab:create", {"title": title, "type": "terminal"})
        await asyncio.sleep(1)  # Wait for response

    async def switch_tab(self, tab_id):
        """Switch to a tab"""
        print(f"[{self.client_name}] 🔄 Switching to tab: {tab_id}")
        await self.sio.emit("workspace:tab:switch", {"tabId": tab_id})
        await asyncio.sleep(1)  # Wait for response

    async def split_pane(self, tab_id, pane_id, direction="horizontal"):
        """Split a pane"""
        print(f"[{self.client_name}] 🔲 Splitting pane {pane_id} {direction}ly")
        await self.sio.emit(
            "workspace:pane:split", {"tabId": tab_id, "paneId": pane_id, "direction": direction}
        )
        await asyncio.sleep(1)  # Wait for response

    async def update_ui(self, updates):
        """Update UI state"""
        print(f"[{self.client_name}] 🎛️ Updating UI: {json.dumps(updates)}")
        await self.sio.emit("workspace:ui:update", {"updates": updates})
        await asyncio.sleep(1)  # Wait for response


async def run_multiwindow_test():
    """Run comprehensive multi-window synchronization tests"""

    print("=" * 70)
    print("🧪 AETHERTERM MULTI-WINDOW SYNCHRONIZATION TESTS")
    print("=" * 70)

    # Create two clients to simulate multiple windows
    client1 = MultiWindowTestClient("Window-1")
    client2 = MultiWindowTestClient("Window-2")

    try:
        # Step 1: Connect both clients
        print("\n📡 Step 1: Connecting clients...")
        if not await client1.connect():
            return
        await asyncio.sleep(2)  # Wait for workspace initialization

        if not await client2.connect():
            return
        await asyncio.sleep(2)  # Wait for workspace initialization

        print(f"✅ Both clients connected successfully")

        # Step 2: Test tab creation from client1
        print("\n📋 Step 2: Testing tab creation synchronization...")
        await client1.create_tab("Development Tab")

        # Step 3: Test tab switching from client2
        print("\n🔄 Step 3: Testing tab switching synchronization...")
        # Get tab ID from client1's workspace state
        tabs = client1.workspace_state.get("tabs", [])
        if len(tabs) > 1:
            second_tab_id = tabs[1]["id"]
            await client2.switch_tab(second_tab_id)

        # Step 4: Test pane splitting from client1
        print("\n🔲 Step 4: Testing pane splitting synchronization...")
        if tabs:
            first_tab = tabs[0]
            if first_tab.get("panes"):
                first_pane_id = first_tab["panes"][0]["id"]
                await client1.split_pane(first_tab["id"], first_pane_id, "horizontal")

        # Step 5: Test UI state updates from client2
        print("\n🎛️ Step 5: Testing UI state synchronization...")
        await client2.update_ui({"panelWidth": 400, "isPanelVisible": False})

        # Step 6: Create another tab from client2
        print("\n📋 Step 6: Testing cross-client tab creation...")
        await client2.create_tab("Testing Tab")

        # Wait for final synchronization
        await asyncio.sleep(3)

        # Step 7: Verify synchronization
        print("\n🔍 Step 7: Verifying synchronization...")

        # Check event counts
        client1_events = len(client1.events_received)
        client2_events = len(client2.events_received)

        print(f"Client 1 received {client1_events} events")
        print(f"Client 2 received {client2_events} events")

        # Both clients should have received synchronization events
        if client1_events > 5 and client2_events > 5:
            print("✅ Multi-window synchronization is working!")
        else:
            print("❌ Insufficient synchronization events received")

        # Show event summary
        print("\n📊 Event Summary:")
        print("Client 1 Events:")
        for event_type, _ in client1.events_received:
            print(f"  - {event_type}")

        print("Client 2 Events:")
        for event_type, _ in client2.events_received:
            print(f"  - {event_type}")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")

    finally:
        print("\n🔌 Disconnecting clients...")
        await client1.disconnect()
        await client2.disconnect()

        print("\n" + "=" * 70)
        print("🏁 MULTI-WINDOW SYNCHRONIZATION TEST COMPLETE")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_multiwindow_test())
