"""
server_link.py — Communicates with the central YantrAI server.
Registers discovered cameras and sends stream URLs.
"""

import json
import urllib.request
import urllib.error
import uuid
import platform
import hashlib
from typing import Optional, Callable


def get_machine_id() -> str:
    """Generate a unique, persistent ID for this machine."""
    # Combine MAC address and node name for a stable hardware-linked ID
    node = str(uuid.getnode())
    machine_name = platform.node()
    combined = f"yantrai-{node}-{machine_name}"
    return hashlib.sha256(combined.encode()).hexdigest()[:12]


def register_stream(
    server_url: str,
    site_name: str,
    rtsp_uri: str,
    ngrok_url: str,
    on_status: Optional[Callable] = None
) -> bool:
    """
    Register a discovered camera stream with the central server.
    """
    def log(msg):
        print(msg)
        if on_status:
            on_status(msg)

    endpoint = f"{server_url.rstrip('/')}/api/agent/register"
    
    # Use deterministic machine-based site ID if name is default
    final_site_name = site_name if site_name else f"Site-{platform.node()}"
    machine_id = get_machine_id()
    
    payload = json.dumps({
        "site_name": final_site_name,
        "site_id": machine_id, # Inform server of our preferred static ID
        "local_rtsp": rtsp_uri,
        "remote_url": ngrok_url,
    }).encode("utf-8")

    log(f"📡 Registering with server at {server_url}...")

    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=45)
            raw_response = resp.read().decode()
            data = json.loads(raw_response)

            if data.get("status") == "success":
                log(f"✅ Registered with server! Site: {final_site_name}")
                return data.get("site_id")
            else:
                log(f"⚠️ Server responded: {data.get('message', 'Unknown error')}")
                return None
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < max_retries - 1:
                log(f"⚠️ Registration attempt {attempt+1} timed out. Retrying in {retry_delay}s...")
                import time
                time.sleep(retry_delay)
            else:
                log(f"❌ Cannot reach server after {max_retries} attempts: {e}")
                return None
        except urllib.error.HTTPError as e:
            log(f"❌ Server Error ({e.code}): {e.reason}")
            try:
                error_data = json.loads(e.read().decode())
                log(f"   -> Detail: {error_data.get('message', 'No detail')}")
            except: pass
            return None
        except (urllib.error.URLError, TimeoutError) as e:
            log(f"❌ Registration failed: {e}")
            return None


def check_server(server_url: str) -> bool:
    """Check if the central server is reachable."""
    try:
        req = urllib.request.urlopen(f"{server_url.rstrip('/')}/api/health", timeout=15)
        return req.status == 200
    except:
        return False
