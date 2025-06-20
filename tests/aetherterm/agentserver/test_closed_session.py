#!/usr/bin/env python3
"""
Test script to verify that closed sessions display CLOSED message.
"""

import asyncio
import sys
import time

import socketio


async def test_closed_session():
    """Test connecting to a closed session."""

    # Create first client to establish a session
    sio1 = socketio.AsyncClient()
    session_id = "test-session-123"

    print("Testing closed session handling...")

    try:
        # Connect first client
        await sio1.connect("http://localhost:57575")
        print("✓ First client connected")

        # Create terminal session
        await sio1.emit("create_terminal", {"session": session_id, "user": "", "path": ""})

        # Wait for terminal to be ready
        await asyncio.sleep(2)
        print("✓ Terminal session created")

        # Disconnect first client (this should close the session)
        await sio1.disconnect()
        print("✓ First client disconnected")

        # Wait a moment for cleanup
        await asyncio.sleep(1)

        # Now try to connect second client to the same session
        sio2 = socketio.AsyncClient()

        @sio2.event
        async def terminal_closed(data):
            if data.get("reason") == "session_already_closed":
                print("✓ Second client received 'session_already_closed' message")
                is_owner = data.get("is_owner", "unknown")
                print(f"✓ Session ownership detected as: {is_owner}")
                print("✓ Test PASSED: Closed session properly detected")
            else:
                print(f"✗ Unexpected terminal_closed reason: {data.get('reason')}")
            await sio2.disconnect()

        @sio2.event
        async def terminal_ready(data):
            print("✗ Test FAILED: Terminal should not be ready for closed session")
            await sio2.disconnect()

        await sio2.connect("http://localhost:57575")
        print("✓ Second client connected")

        # Try to connect to the closed session
        await sio2.emit("create_terminal", {"session": session_id, "user": "", "path": ""})

        # Wait for response
        await asyncio.sleep(3)

        await sio2.disconnect()

    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False

    return True


if __name__ == "__main__":
    print("Make sure Butterfly server is running on localhost:57575")
    print("Starting test in 3 seconds...")
    time.sleep(3)

    try:
        result = asyncio.run(test_closed_session())
        if result:
            print("\n✓ All tests completed")
        else:
            print("\n✗ Some tests failed")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
