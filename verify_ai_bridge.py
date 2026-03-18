import asyncio
import websockets
import cv2
import numpy as np
import httpx
import time

async def verify():
    server_url = "http://localhost:8000"
    ws_url = "ws://localhost:8000"
    site_id = "ai-test-site"
    
    print(f"1. Setting source to native://{site_id}...")
    async with httpx.AsyncClient() as client:
        await client.post(f"{server_url}/api/set_source", json={"source": f"native://{site_id}"})
    
    print("2. Starting frame push...")
    push_endpoint = f"{ws_url}/ws/agent_push/{site_id}"
    
    # Create a test frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, "AI BRIDGE TEST", (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
    _, buffer = cv2.imencode('.jpg', frame)
    frame_bytes = buffer.tobytes()
    
    try:
        async with websockets.connect(push_endpoint) as ws:
            print("Connected to push endpoint.")
            for i in range(60):
                print(f"Pushing frame {i}...")
                await ws.send(frame_bytes)
                await asyncio.sleep(1.0)
            
            print("Push complete. Waiting to see if AI detects it...")
            # Wait for any pending inferences
            await asyncio.sleep(10)
            
    except Exception as e:
        print(f"Push failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
