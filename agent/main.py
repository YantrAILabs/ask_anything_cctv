"""
YantrAI Remote Agent — Main Orchestrator
Ties together: UI → Discovery → Bore.pub → Server Registration
"""

import asyncio
import threading
import sys
import os

# Add agent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_ui import AgentUI
from discovery import discover_and_connect
from server_link import register_stream, check_server, get_machine_id


import cv2
from PIL import Image
import time

# Shared state for restarts and frame sharing
_stop_event = threading.Event()
_current_frame = None
_flow_lock = threading.Lock()

def run_agent_flow(ui: AgentUI, server_url: str, site_name: str,
                   username: str, password: str, tunnel_method: str = "yantrai",
                   manual_url: str = ""):
    """
    The main agent workflow, run in a background thread.
    Supports graceful stop/restart.
    """
    global _current_frame, _stop_event
    
    # 1. Signal stop to ANY running flow first (Outside the lock!)
    _stop_event.set()
    
    with _flow_lock:
        # 2. Clear for the new flow
        _stop_event.clear()

        def log(msg):
            ui.log(msg)

        async def _async_flow():
            global _current_frame
            ui.set_button_state(False)

            # Step 1: Discover / Select Source
            log("")
            log("═══ STEP 1: Camera Source ═══")

            if manual_url == "0":
                log("📷 Using Laptop Inbuilt Camera")
                rtsp_uri = 0
            else:
                log("📡 Scanning for Local CCTV...")
                rtsp_uri = await discover_and_connect(username, password, on_status=log)

            if rtsp_uri is None:
                log("❌ FAILED: No cameras found.")
                ui.set_status("camera", False)
                ui.set_button_state(True)
                return

            ui.set_status("camera", True)
            
            # Step 2: Start Local Preview IMMEDIATELY
            log("🚀 Opening camera feed...")
            cap = cv2.VideoCapture(rtsp_uri)
            if not cap.isOpened():
                log("❌ Could not open camera.")
                ui.set_button_state(True)
                return
            
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            log("✅ Local Monitor Active")

            # Step 3: Server Registration (Background)
            async def do_registration():
                log("")
                # Define local_source_str correctly (restoring missing line)
                local_source_str = str(rtsp_uri) if isinstance(rtsp_uri, int) else rtsp_uri
                
                log(f"📋 Site Hardware ID: {get_machine_id()}")
                site_id = register_stream(
                    server_url=server_url, site_name=site_name,
                    rtsp_uri=local_source_str, ngrok_url="yantrai://bridge",
                    on_status=log
                )

                if site_id:
                    log(f"📎 Sync ID Verified: {site_id}")
                    if _stop_event.is_set(): return
                    ui.set_status("cloud", True)
                    ui.set_status("bridge", True)
                    ui.set_connection_link(f"native://{site_id}")
                    
                    # Start Cloud Push
                    from yantrai_tunnel import start_yantrai_push
                    def provider(): return _current_frame
                    provider._stop_event = _stop_event
                    start_yantrai_push(
                        camera_url=rtsp_uri, server_url=server_url,
                        site_id=site_id, on_status=log,
                        frame_provider=provider
                    )
                    log("🚀 Cloud Sync complete.")
                    ui.set_button_state(True)
                else:
                    log(f"⚠️ Cloud Sync failed. Server did not return a valid Site ID.")

            # Run registration in background
            asyncio.create_task(do_registration())

            # Step 4: Centralized Capture Loop
            try:
                while not _stop_event.is_set():
                    ret, frame = cap.read()
                    if ret:
                        _current_frame = frame
                        # Update UI preview
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(frame_rgb)
                        ui.update_preview(pil_img)
                    else:
                        time.sleep(0.1)
                    await asyncio.sleep(0.04) # Check stop event
            finally:
                cap.release()
                log("🛑 Stream stopped.")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_async_flow())
        loop.close()

def main():
    ui = AgentUI()

    machine_id = get_machine_id()
    ui.set_connection_link(f"native://{machine_id}")

    # Official Build status
    is_official = getattr(sys, 'frozen', False)
    if is_official:
        ui.log("✅ Running OFFICIAL yantrai Onsite Distribution.")
    else:
        ui.log("⚠️ DEV BUILD: Hardware-ID synced.")

    def on_start(**kwargs):
        thread = threading.Thread(
            target=run_agent_flow,
            args=(ui, kwargs['server_url'], kwargs['site_name'],
                  kwargs['username'], kwargs['password'], kwargs['tunnel_method'],
                  kwargs.get('manual_url', "")),
            daemon=True
        )
        thread.start()

    ui.on_start = on_start
    
    # Auto-start on launch with last choice (default CCTV)
    config = ui._load_config()
    if config:
        ui.root.after(500, lambda: on_start(**config))
    else:
        # Default start
        ui.root.after(500, lambda: ui._select_source("cctv"))
    
    ui.run()

if __name__ == "__main__":
    main()
