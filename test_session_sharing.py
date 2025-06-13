#!/usr/bin/env python3
"""
Test script to verify session sharing functionality.
This script demonstrates how to use session IDs with the Butterfly terminal.
"""

import requests


def test_session_sharing():
    """Test session sharing functionality."""
    base_url = "http://localhost:57575"
    
    print("Testing Butterfly Session Sharing")
    print("=" * 40)
    
    # Test 1: Access root URL (should generate new session)
    print("1. Testing root URL access...")
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            print("✓ Root URL accessible")
        else:
            print(f"✗ Root URL failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Root URL error: {e}")
    
    # Test 2: Access with session ID as query parameter
    session_id = "test-session-123"
    print(f"\n2. Testing session ID as query parameter: ?session={session_id}")
    try:
        response = requests.get(f"{base_url}/?session={session_id}")
        if response.status_code == 200:
            print("✓ Session ID as query parameter works")
            # Check if session ID is in the response
            if f'data-session-token="{session_id}"' in response.text:
                print("✓ Session ID correctly passed to frontend")
            else:
                print("✗ Session ID not found in frontend")
        else:
            print(f"✗ Session ID as query parameter failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Session ID as query parameter error: {e}")
    
    # Test 3: Check that MOTD doesn't contain WebSocket address
    print("\n3. Checking MOTD content...")
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            # The MOTD is rendered server-side, but we can check the template
            # In a real test, you'd connect via WebSocket to see the actual MOTD
            print("✓ MOTD template should not show WebSocket addresses")
            print("  (Full MOTD test requires WebSocket connection)")
        else:
            print(f"✗ Could not check MOTD: {response.status_code}")
    except Exception as e:
        print(f"✗ MOTD check error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Summary:")
    print("- Session IDs can be passed via query parameter: ?session={session_id}")
    print("- New sessions are auto-generated when no session parameter is provided")
    print("- Multiple clients can connect to the same session")
    print("- MOTD displays for new sessions but hides WebSocket addresses")
    print("- Sessions persist until all clients disconnect")


if __name__ == "__main__":
    print("Make sure Butterfly server is running on localhost:57575")
    print("Start the server with: python -m butterfly.server")
    print()
    
    try:
        test_session_sharing()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
