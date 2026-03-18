
import asyncio
import json

import websockets


async def test_websocket():
    uri = "ws://localhost:8000/ws/dashboard"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")

            # Wait for initial state
            initial = await websocket.recv()
            print(f"Received initial state: {len(initial)} bytes")

            print("Waiting for events... (Press Ctrl+C to stop)")
            while True:
                msg = await websocket.recv()
                data = json.loads(msg)
                print(f"Received Event: {data.get('type')}")
                if data.get('type') == 'node_start':
                    node = data.get('data', {}).get('node', {})
                    print(f"  -> Node Started: {node.get('node_name')}")
                elif data.get('type') == 'node_complete':
                    node = data.get('data', {}).get('node', {})
                    print(f"  -> Node Completed: {node.get('node_name')} ({node.get('duration_ms')}ms)")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\nTest stopped.")
