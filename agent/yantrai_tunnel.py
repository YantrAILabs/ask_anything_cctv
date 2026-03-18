"""
yantrai_tunnel.py — Native frame push to Cloud Run.
Allows remote viewing without any 3rd party tunnels.
"""

import cv2
import asyncio
import websockets
import base64
import time
import json
from typing import Optional, Callable

async def push_frames_loop(camera_url: str, server_url: str, site_id: str, 
                         on_status: Optional[Callable] = None,
                         frame_provider: Optional[Callable] = None):
    """
    Main loop to capture frames from camera and push to server.
    """
    def log(msg):
        print(msg)
        if on_status:
            on_status(msg)

    # Convert https:// to ws:// for websocket
    ws_url = server_url.replace("http://", "ws://").replace("https://", "wss://")
    push_endpoint = f"{ws_url.rstrip('/')}/ws/agent_push/{site_id}"

    log(f"🚀 YantrAI Bridge: Starting push to {push_endpoint}")
    
    cap = None
    if not frame_provider:
        cap = cv2.VideoCapture(camera_url)
        if not cap.isOpened():
            log(f"❌ Failed to open camera: {camera_url}")
            return
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    retry_delay = 2
    while True:
        if frame_provider and hasattr(frame_provider, '_stop_event') and frame_provider._stop_event.is_set():
            break
            
        try:
            async with websockets.connect(push_endpoint) as ws:
                log("✅ Connected to YantrAI Hub")
                while True:
                    if frame_provider and hasattr(frame_provider, '_stop_event') and frame_provider._stop_event.is_set():
                        break
                        
                    if frame_provider:
                        frame = frame_provider()
                        success = frame is not None
                    else:
                        success, frame = cap.read()
                    
                    if not success:
                        if not frame_provider:
                            log("⚠️ Camera read failed, retrying...")
                            cap.release()
                            await asyncio.sleep(retry_delay)
                            cap = cv2.VideoCapture(camera_url)
                        else:
                            await asyncio.sleep(0.1)
                        continue
                    
                    # Resize and compress
                    frame = cv2.resize(frame, (640, 360))
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 40])
                    
                    # Send as binary
                    await ws.send(buffer.tobytes())
                    
                    # Limit FPS
                    await asyncio.sleep(0.06)
                    
        except Exception as e:
            log(f"⚠️ Bridge Error: {e}")
            await asyncio.sleep(retry_delay)

def start_yantrai_push(camera_url: str, server_url: str, site_id: str, 
                       on_status: Optional[Callable] = None,
                       frame_provider: Optional[Callable] = None):
    """Entry point to run push in a background loop."""
    new_loop = asyncio.new_event_loop()
    def run():
        asyncio.set_event_loop(new_loop)
        new_loop.run_until_complete(push_frames_loop(camera_url, server_url, site_id, on_status, frame_provider))
    
    import threading
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t
