import asyncio
import websockets
import json

async def test_chat():
    uri = "ws://localhost:8000/ws/chat"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to Chat WebSocket.")
            
            # Test 1: Send a message
            test_message = {"text": "What have been your observations lately?"}
            print(f"Sending: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # Test 2: Receive response
            print("Awaiting response...")
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                if data.get("type") == "chat":
                    print("SUCCESS: Received chat response.")
                    print(f"AI Response: {data['text']}")
                    break
                else:
                    print(f"Received intermediate message (type: {data.get('type')}): {data.get('text')}")

    except Exception as e:
        print(f"FAILED to connect or communicate: {e}")

if __name__ == "__main__":
    asyncio.run(test_chat())
