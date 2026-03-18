from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import cv2
import asyncio
import base64
import json
import time
import threading
import os
from pathlib import Path
import sys

# Path resolution for PyInstaller
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    # Root of the project is one level up from backend/
    root = Path(__file__).parent.parent
    return root / relative_path

from motion_detector import MotionDetector
from datetime import datetime
import subprocess
import socket
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel
from typing import Optional, List, Dict
from onvif import ONVIFCamera
import supabase_db as database

class SmartConnectRequest(BaseModel):
    username: str
    password: str

# --- ONVIF Logic ---

async def fetch_onvif_uri(ip: str, port: int, user: str, password: str):
    try:
        # We run this in a thread to not block the async event loop if it's slow
        loop = asyncio.get_event_loop()
        def _get_uri():
            mycam = ONVIFCamera(ip, port, user, password)
            media = mycam.create_media_service()
            profiles = media.GetProfiles()
            if not profiles: return None
            
            profile = profiles[0]
            obj = media.create_type('GetStreamUri')
            obj.StreamSetup = {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}}
            obj.ProfileToken = profile.token
            res = media.GetStreamUri(obj)
            return res.Uri
            
        return await loop.run_in_executor(None, _get_uri)
    except Exception as e:
        print(f"ONVIF Probe for {ip} failed: {e}")
        return None

app = FastAPI()

# Global state for Video handling
current_video_source = database.get_config("video_source", "0")
latest_raw_frame = None
frame_lock = threading.Lock()
ffmpeg_proc = None
stop_event = threading.Event()
global_executor = ThreadPoolExecutor(max_workers=50)

print(f"LOG: Backend started with initial source: {current_video_source}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = MotionDetector()


# Global state
vision_engine = None
engine_initializing = False
last_frame_base64 = None
connected_chat_clients = set()
chat_lock = asyncio.Lock()
agent_buffers = {} # site_id -> frame_bytes
agent_buffer_lock = threading.Lock()

DEFAULT_INSTRUCTION = "Describe what is happening in this video frame in one very short, professional sentence for a security activity log. Focus on movements, people, or significant changes."

def get_vision_engine():
    global vision_engine, engine_initializing
    if vision_engine is None and not engine_initializing:
        # Start initialization in a background thread to avoid blocking loop
        engine_initializing = True
        def init_task():
            global vision_engine, engine_initializing
            try:
                print("LOG: Starting background VisionEngine initialization...")
                from vision_engine import VisionEngine
                vision_engine = VisionEngine()
                print("LOG: VisionEngine is ready.")
            except Exception as e:
                print(f"LOG: Vision Engine Error: {e}")
            finally:
                engine_initializing = False
        
        threading.Thread(target=init_task, daemon=True).start()
    return vision_engine
# --- Network Scanning Logic (from CCTV app) ---

def _get_local_info() -> Dict[str, str]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return {"subnet": ".".join(local_ip.split(".")[:3]), "ip": local_ip}
    except Exception:
        return {"subnet": "192.168.1", "ip": "127.0.0.1"}

def _probe_host(ip: str, ports: List[int] = [554, 8554, 8000, 8080, 8899, 37777, 34567, 5000, 5544, 10554, 80, 443, 8001, 8002, 9000, 9100], timeout: float = 0.5) -> List[Dict]:
    """Probes a host for common camera ports (Deep Scan ports inherited)."""
    found_on_ip = []
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except Exception:
                    hostname = ip
                found_on_ip.append({"ip": ip, "port": port, "hostname": hostname})
        except Exception:
            pass
    return found_on_ip

async def scan_network_internal():
    info = _get_local_info()
    subnet = info["subnet"]
    my_ip = info["ip"]
    hosts = [f"{subnet}.{i}" for i in range(1, 255) if f"{subnet}.{i}" != my_ip]
    found: List[dict] = []

    # Use the global executor to avoid creating too many threads
    loop = asyncio.get_event_loop()
    
    # Run WS-Discovery in parallel with port scanning
    discovery_task = asyncio.create_task(discover_onvif())
    
    futures = [loop.run_in_executor(global_executor, _probe_host, ip) for ip in hosts]
    results = await asyncio.gather(*futures)

    # results is a list of lists, flatten it
    found = [item for sublist in results for item in sublist]
    
    # Await WS-Discovery results
    try:
        ws_found = await discovery_task
        for dev in ws_found:
            # Avoid duplicates by IP
            if not any(d['ip'] == dev['ip'] for d in found):
                found.append(dev)
    except Exception as e:
        print(f"LOG: WS-Discovery Error: {e}")

    found.sort(key=lambda x: (int(x["ip"].split(".")[-1]), x["port"]))
    return {"subnet": subnet, "devices": found, "total_scanned": len(hosts)}

async def discover_onvif(timeout=5.0) -> List[Dict]:
    """Basic WS-Discovery via UDP broadcast on 3702."""
    WS_DISCOVERY_PAYLOAD = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Envelope xmlns:tds="http://www.onvif.org/ver10/device/wsdl" '
        'xmlns="http://www.w3.org/2003/05/soap-envelope">'
        '<Header><MessageID xmlns="http://schemas.xmlsoap.org/ws/2004/08/addressing">'
        'uuid:f2b1c4c1-4b1c-4b1c-4b1c-4b1c4b1c4b1c</MessageID>'
        '<To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</To>'
        '<Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</Action>'
        '</Header><Body><Probe xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery">'
        '<Types>tds:Device</Types></Probe></Body></Envelope>'
    )
    
    print(f"LOG: [discover_onvif] Starting scan (timeout={timeout}s)...")
    found = []
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(1.0) # Longer recv timeout
        
        sock.sendto(WS_DISCOVERY_PAYLOAD.encode(), ('239.255.255.250', 3702))
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                loop = asyncio.get_event_loop()
                data, addr = await loop.run_in_executor(None, lambda: sock.recvfrom(4096))
                ip = addr[0]
                if not any(d['ip'] == ip for d in found):
                    print(f"LOG: [discover_onvif] Found device at {ip}")
                    found.append({"ip": ip, "port": 8899, "hostname": f"ONVIF Device ({ip})"})
            except (socket.timeout, asyncio.TimeoutError):
                if time.time() - start_time >= timeout: break
                continue
            except Exception as e:
                print(f"LOG: [discover_onvif] Recv error: {e}")
                break
    except Exception as e:
        print(f"LOG: [discover_onvif] Setup failed: {e}")
    finally:
        if sock: sock.close()
    return found

# --- Robust FFmpeg Frame Generation ---

def create_dummy_frame(width, height, text="STREAM OFFLINE"):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    # Add random noise for a "static" effect
    noise = np.random.randint(0, 40, (height, width, 3), dtype=np.uint8)
    frame = cv2.add(frame, noise)
    cv2.putText(frame, text, (width//2 - 150, height//2), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 116, 139), 2)
    return frame

def generate_frames():
    global latest_raw_frame, ffmpeg_proc, current_video_source
    
    FRAME_W, FRAME_H = 640, 360
    frame_size = FRAME_W * FRAME_H * 3
    last_source = None

    def open_pipe(source):
        print(f"LOG: [open_pipe] Opening VideoCapture for: {source}")
        if str(source).startswith("native://"):
            # Native Bridge source - we don't open it via cv2
            print(f"LOG: [open_pipe] Native Bridge source detected: {source}")
            return "NATIVE_BRIDGE"
        
        if str(source) == "0" or source == 0:
            cap = cv2.VideoCapture(0)
        else:
            # Use TCP transport for reliability, set low latency
            cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
        
        # Set small buffer to always get latest frame
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # Set capture resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
        
        if not cap.isOpened():
            print(f"LOG: [open_pipe] Failed to open source: {source}")
        return cap

    cap = None
    
    while not stop_event.is_set():
        try:
            if current_video_source != last_source:
                print(f"LOG: Changing source to {current_video_source}")
                if cap is not None and not isinstance(cap, str):
                    cap.release()
                
                cap = open_pipe(current_video_source)
                last_source = current_video_source

            if cap == "NATIVE_BRIDGE":
                # Do nothing, agent_push WebSocket handles latest_raw_frame
                time.sleep(0.1)
                continue

            if cap is not None and cap.isOpened():
                success, frame = cap.read()
                if not success:
                    print("LOG: [frame_gen] Capture read failed, retrying...")
                    frame = create_dummy_frame(FRAME_W, FRAME_H, "STREAM ERROR / RECONNECTING")
                    cap.release()
                    time.sleep(2)
                    cap = open_pipe(current_video_source)
                else:
                    # Resize to standard size for app
                    if frame.shape[1] != FRAME_W or frame.shape[0] != FRAME_H:
                        frame = cv2.resize(frame, (FRAME_W, FRAME_H))
            else:
                if current_video_source.startswith("native://"):
                    # Wait for agent push instead of showing offline
                    time.sleep(0.1)
                    continue
                frame = create_dummy_frame(FRAME_W, FRAME_H, "OFFLINE / CONNECTING...")
                time.sleep(2)
                cap = open_pipe(current_video_source)

            with frame_lock:
                latest_raw_frame = frame

            time.sleep(0.01) # Yield
        except Exception as e:
            print(f"LOG: Frame gen error: {e}")
            time.sleep(2)

@app.on_event("startup")
async def startup_event():
    get_vision_engine() # Start loading model immediately on startup
    threading.Thread(target=generate_frames, daemon=True).start()
    asyncio.create_task(auto_observation_loop())

@app.post("/api/set_source")
async def set_source(data: dict):
    global current_video_source
    source = data.get("source")
    if source is not None:
        current_video_source = str(source)
        database.update_config("video_source", current_video_source)
        print(f"LOG: API set_source successful: {current_video_source}")
        return {"status": "success", "source": current_video_source}
    return {"status": "error", "message": "No source provided"}

@app.get("/api/get_source")
async def get_source():
    return {"source": current_video_source}

async def auto_observation_loop():
    global vision_engine, last_frame_base64, latest_raw_frame
    print("LOG: Auto-observation loop started (async).")
    while True:
        try:
            # Fetch dynamic interval from database
            interval = int(database.get_config("logging_interval", "15"))
            await asyncio.sleep(interval)
            
            # Use local reference to avoid race conditions
            engine = vision_engine
            
            with frame_lock:
                if latest_raw_frame is not None:
                    _, buffer = cv2.imencode('.jpg', latest_raw_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    frame = base64.b64encode(buffer).decode('utf-8')
                else:
                    frame = None
            
            if engine and frame:
                print("LOG: Running auto-observation for cam-01...")
                # Fetch camera specific instruction from DB
                current_instruction = database.get_camera_role("cam-01", DEFAULT_INSTRUCTION)
                
                # Run inference in worker thread
                summary = await asyncio.get_event_loop().run_in_executor(
                    None, engine.summarize_scene, frame, current_instruction
                )
                
                # Save to database
                database.insert_log("cam-01", summary)
                
                payload = json.dumps({
                    "type": "log",
                    "camera_id": "cam-01",
                    "text": summary,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
                
                # Broadcast to all connected clients
                if connected_chat_clients:
                    async with chat_lock:
                        print(f"LOG: Broadcasting log to {len(connected_chat_clients)} clients.")
                        disconnected = []
                        for client in connected_chat_clients:
                            try:
                                await client.send_text(payload)
                            except:
                                disconnected.append(client)
                        
                        for client in disconnected:
                            connected_chat_clients.remove(client)
        except Exception as e:
            print(f"LOG: Auto-observation loop error: {e}")

@app.get("/api/health")
async def health_check():
    return {"message": "CCTV AI Backend Running"}

def get_dir_size(path):
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    except:
        pass
    return total

@app.get("/status")
async def get_status():
    # Estimate progress for Qwen2-VL (approx 4.5GB)
    progress = 0
    cache_path = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub", "models--Qwen--Qwen2-VL-2B-Instruct")
    if os.path.exists(cache_path):
        current_size = get_dir_size(cache_path)
        # Total size for 2B Instruct is ~4.5GB
        progress = min(99, int((current_size / (4.5 * 1024 * 1024 * 1024)) * 100))
    
    if vision_engine:
        progress = 100

    return {
        "models": [
            {
                "name": "OpenCV Motion Detector",
                "status": "Ready",
                "progress": 100,
                "type": "CPU"
            },
            {
                "name": "Qwen2-VL-2B-Instruct",
                "status": "Ready" if vision_engine else ("Initializing" if engine_initializing else "Pending"),
                "progress": progress,
                "type": "GPU/CPU"
            }
        ],
        "engine_ready": vision_engine is not None,
        "initializing": engine_initializing,
        "first_frame_captured": last_frame_base64 is not None
    }

@app.post("/config/instruction")
async def update_instruction(data: dict):
    camera_id = data.get("camera_id", "cam-01")
    new_instr = data.get("instruction")
    if new_instr:
        database.update_camera_role(camera_id, new_instr)
        print(f"LOG: Instruction updated for {camera_id}: {new_instr[:50]}...")
        return {"status": "success"}
    return {"status": "error", "message": "No instruction provided"}

@app.get("/config/instruction/{camera_id}")
async def get_instruction(camera_id: str):
    role = database.get_camera_role(camera_id, DEFAULT_INSTRUCTION)
    return {"instruction": role}

@app.get("/config/logging_frequency")
async def get_logging_frequency():
    interval = database.get_config("logging_interval", "15")
    return {"interval": int(interval)}

@app.post("/config/logging_frequency")
async def update_logging_frequency(data: dict):
    interval = data.get("interval")
    if interval is not None:
        database.update_config("logging_interval", str(interval))
        print(f"LOG: Logging interval updated to {interval}s")
        return {"status": "success"}
    return {"status": "error", "message": "No interval provided"}

@app.get("/api/scan_network")
async def scan_network_api():
    return await scan_network_internal()

# --- Remote Agent Endpoints ---

@app.post("/api/agent/register")
async def agent_register(data: dict):
    site_name = data.get("site_name", "Unknown Site")
    site_id = data.get("site_id")  # New hardware-based ID
    local_rtsp = data.get("local_rtsp", "")
    remote_url = data.get("remote_url", "")
    
    site = database.register_site(site_name, local_rtsp, remote_url, site_id=site_id)
    final_id = site.get("site_id") or site_id
    print(f"LOG: Agent registered: {site_name} (ID: {final_id})")
    return {"status": "success", "message": f"Site '{site_name}' registered.", "site_id": final_id}

@app.get("/api/agent/sites")
async def get_agent_sites():
    sites = database.get_all_sites()
    # Convert datetime objects to strings for JSON
    for s in sites:
        for k, v in s.items():
            if hasattr(v, 'isoformat'):
                s[k] = v.isoformat()
    return {"sites": sites}

@app.post("/api/smart_connect")
async def smart_connect(req: SmartConnectRequest):
    global current_video_source
    print(f"LOG: Smart Connect initiated for user: {req.username}")
    
    # Step 1: Fast WS-Discovery (UDP multicast, ~5s)
    ws_devices = await discover_onvif(timeout=5.0)
    print(f"LOG: [Smart Connect] WS-Discovery found {len(ws_devices)} devices")
    
    # Step 2: If WS-Discovery found nothing, do a quick targeted port probe
    # on the local subnet for common ONVIF ports only
    candidate_ips = set()
    for dev in ws_devices:
        candidate_ips.add(dev['ip'])
    
    if not candidate_ips:
        print("LOG: [Smart Connect] WS-Discovery empty. Doing quick targeted scan...")
        info = _get_local_info()
        subnet = info["subnet"]
        my_ip = info["ip"]
        # Deep Scan fallback: probe all common camera ports in the local subnet
        COMMON_CAMERA_PORTS = [554, 8554, 8000, 8080, 8899, 37777, 34567, 80, 8001, 8002, 5000]
        hosts_to_check = [f"{subnet}.{i}" for i in range(1, 255) if f"{subnet}.{i}" != my_ip]
        
        async def quick_check(ip):
            try:
                def _check():
                    # We check the most likely ones first
                    for p in [8000, 80, 554, 37777, 8899]:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(0.2)
                        res = s.connect_ex((ip, p))
                        s.close()
                        if res == 0: return (ip, p)
                    return None
                return await loop.run_in_executor(global_executor, _check)
            except:
                return None
        
        results = await asyncio.gather(*[quick_check(ip) for ip in hosts_to_check])
        # Candidate IPs is now a map of IP -> Port to prioritize the found port
        candidates = {res[0]: res[1] for res in results if res is not None}
        candidate_ips = set(candidates.keys())
        print(f"LOG: [Smart Connect] Deep Scan found {len(candidate_ips)} potential camera IPs")
    
    if not candidate_ips:
        return {"status": "error", "message": "No cameras found. Ensure the camera is on the same network and supports ONVIF/RTSP."}
    
    # Step 3: For each candidate, try ONVIF authentication
    # Prioritize the port we found during the scan
    all_ports_to_try = [8000, 80, 8899, 8080, 37777, 34567, 554]
    
    for ip in candidate_ips:
        found_port = candidates.get(ip)
        ports_to_probe = [found_port] + [p for p in all_ports_to_try if p != found_port] if found_port else all_ports_to_try
        
        for port in ports_to_probe:
            print(f"LOG: [Smart Connect] Attempting ONVIF probe at http://{ip}:{port}...")
            uri = await fetch_onvif_uri(ip, port, req.username, req.password)
            if uri:
                # Inject credentials into URI if not already present
                final_uri = uri
                if f"{req.username}:" not in uri and "@" not in uri:
                    parts = uri.split("://")
                    if len(parts) == 2:
                        final_uri = f"{parts[0]}://{req.username}:{req.password}@{parts[1]}"
                
                print(f"LOG: Smart Connect SUCCESS! Found URI: {final_uri}")
                current_video_source = final_uri
                database.update_config("video_source", final_uri)
                return {
                    "status": "success", 
                    "message": f"Connected to camera at {ip}",
                    "uri": final_uri
                }
    
    return {"status": "error", "message": "Could not authenticate on any discovered devices. Check your credentials."}

@app.post("/api/set_source")
async def set_source(data: dict):
    global current_video_source
    source = data.get("source")
    if source is not None:
        current_video_source = str(source)
        database.update_config("video_source", current_video_source)
        print(f"LOG: Video source manually updated to: {current_video_source}")
        return {"status": "success"}
    return {"status": "error", "message": "No source provided"}

@app.get("/api/get_source")
async def get_source():
    return {"source": current_video_source}

@app.websocket("/ws/agent_push/{site_id}")
async def agent_push(websocket: WebSocket, site_id: str):
    """Endpoint for remote agents to push camera frames."""
    await websocket.accept()
    print(f"LOG: Agent connected for push: {site_id}")
    try:
        while True:
            # Receive binary frame (JPG)
            data = await websocket.receive_bytes()
            if data:
                with agent_buffer_lock:
                    agent_buffers[site_id] = data
                
                # AI Bridge: Feed to global vision loop if this is active
                if current_video_source == f"native://{site_id}":
                    try:
                        nparr = np.frombuffer(data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            with frame_lock:
                                latest_raw_frame = frame
                    except Exception as e:
                        print(f"LOG: AI Bridge decode error: {e}")
    except WebSocketDisconnect:
        print(f"LOG: Agent disconnected from push: {site_id}")
    except Exception as e:
        print(f"LOG: Agent push error ({site_id}): {e}")

@app.websocket("/ws/stream")
async def video_stream(websocket: WebSocket):
    global last_frame_base64, latest_raw_frame, current_video_source
    await websocket.accept()
    try:
        while True:
            frame_base64 = None
            motion_detected = False

            # Check if current source is a native bridge site
            if current_video_source.startswith("native://"):
                site_id = current_video_source.replace("native://", "")
                with agent_buffer_lock:
                    raw_bytes = agent_buffers.get(site_id)
                
                if raw_bytes:
                    frame_base64 = base64.b64encode(raw_bytes).decode('utf-8')
                    motion_detected = False 
            else:
                # Standard RTSP/Local flow
                with frame_lock:
                    if latest_raw_frame is not None:
                        frame = latest_raw_frame.copy()
                        motion_detected, _ = detector.detect(frame)
                        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                        frame_base64 = base64.b64encode(buffer).decode('utf-8')

            if frame_base64:
                last_frame_base64 = frame_base64
                payload = json.dumps({
                    "frame": frame_base64,
                    "motion": motion_detected
                })
                await websocket.send_text(payload)
            
            await asyncio.sleep(0.03) # ~30fps
    except:
        pass

@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_chat_clients.add(websocket)
    print(f"LOG: Chat client connected. Total: {len(connected_chat_clients)}")
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                message = json.loads(raw_data)
                prompt = message.get("text", "")
            except:
                continue
            
            if vision_engine and last_frame_base64:
                print("LOG: Starting manual chat inference...")
                
                # Fetch recent logs from DB to give the AI memory/context
                recent_logs = database.get_recent_logs(limit=10)
                context_lines = []
                for entry in recent_logs:
                    context_lines.append(f"[{entry['timestamp']}] {entry['description']}")
                
                if context_lines:
                    context_block = "\n".join(context_lines)
                    augmented_prompt = (
                        f"You are an intelligent CCTV surveillance assistant. "
                        f"Here are the most recent activity logs observed by the camera:\n\n"
                        f"{context_block}\n\n"
                        f"Based on these observations and the current frame, answer this question: {prompt}"
                    )
                else:
                    augmented_prompt = prompt
                    
                response = await asyncio.get_event_loop().run_in_executor(
                    None, vision_engine.analyze_frame, last_frame_base64, augmented_prompt
                )
            elif engine_initializing:
                response = "Vision Engine is initializing. Please wait..."
            elif not vision_engine:
                get_vision_engine()
                response = "Vision Engine starting... try again in a moment."
            else:
                response = "Awaiting camera sync..."
                
            async with chat_lock:
                await websocket.send_text(json.dumps({"type": "chat", "text": response}))
    except Exception as e:
        print(f"LOG: Chat WS Error: {e}")
    finally:
        if websocket in connected_chat_clients:
            connected_chat_clients.remove(websocket)
        print(f"LOG: Chat client disconnected. Total: {len(connected_chat_clients)}")

@app.get("/api/onsite/static/OnsiteAgent.exe")
async def download_onsite():
    """Serve the standalone Onsite agent executable with the filename in the URL for better proxy compatibility."""
    # Use absolute path calculation
    base_dir = Path(__file__).resolve().parent.parent
    exe_path = base_dir / "agent" / "dist" / "OnsiteAgent.exe"
    
    print(f"LOG: [Download] Request received for OnsiteAgent.exe. Searching at: {exe_path}")
    
    if exe_path.exists():
        print(f"LOG: [Download] File found. Size: {exe_path.stat().st_size} bytes. Serving with explicit headers...")
        return FileResponse(
            str(exe_path), 
            filename="OnsiteAgent.exe", 
            media_type="application/octet-stream"
        )
    
    print(f"LOG: [Download] ERROR - File not found at: {exe_path}")
    return {"status": "error", "message": f"Onsite agent build not found on server at {exe_path}"}

# --- Serve Built Frontend ---
FRONTEND_DIR = get_resource_path("frontend/dist")
if FRONTEND_DIR.exists() and FRONTEND_DIR.is_dir():
    # Only mount /assets if directory exists
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Serve index.html for all non-API routes (SPA routing)
        file_path = FRONTEND_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIR / "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
