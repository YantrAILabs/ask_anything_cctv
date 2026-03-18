"""
discovery.py — Camera discovery module for YantrAI Remote Agent.
Reuses the ONVIF + WS-Discovery logic from the main backend.
"""

import socket
import time
import asyncio
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=50)


def get_local_info() -> Dict[str, str]:
    """Get the local IP and subnet."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return {"subnet": ".".join(local_ip.split(".")[:3]), "ip": local_ip}
    except Exception:
        return {"subnet": "192.168.1", "ip": "127.0.0.1"}


def probe_host(ip: str, ports: List[int] = [8000, 80, 8899, 37777, 34567, 554, 8554, 8080], timeout: float = 0.3) -> List[Dict]:
    """Check if common ONVIF/RTSP ports are open on a host."""
    found = []
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            if sock.connect_ex((ip, port)) == 0:
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except:
                    hostname = ip
                found.append({"ip": ip, "port": port, "hostname": hostname})
            sock.close()
        except:
            pass
    return found


async def ws_discovery(timeout: float = 5.0) -> List[Dict]:
    """Find ONVIF devices via WS-Discovery (UDP multicast)."""
    WS_PAYLOAD = (
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

    found = []
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(1.0)
        sock.sendto(WS_PAYLOAD.encode(), ('239.255.255.250', 3702))

        start = time.time()
        loop = asyncio.get_event_loop()
        while time.time() - start < timeout:
            try:
                data, addr = await loop.run_in_executor(None, lambda: sock.recvfrom(4096))
                ip = addr[0]
                if not any(d['ip'] == ip for d in found):
                    found.append({"ip": ip, "port": 8000, "hostname": f"ONVIF Device ({ip})"})
            except socket.timeout:
                if time.time() - start >= timeout:
                    break
                continue
            except:
                break
    except Exception as e:
        print(f"WS-Discovery error: {e}")
    finally:
        if sock:
            sock.close()
    return found


async def fetch_onvif_uri(ip: str, port: int, username: str, password: str) -> Optional[str]:
    """Get the RTSP stream URI from an ONVIF device."""
    try:
        from onvif import ONVIFCamera
        loop = asyncio.get_event_loop()

        def _get():
            cam = ONVIFCamera(ip, port, username, password)
            media = cam.create_media_service()
            profiles = media.GetProfiles()
            if not profiles:
                return None
            obj = media.create_type('GetStreamUri')
            obj.StreamSetup = {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}}
            obj.ProfileToken = profiles[0].token
            return media.GetStreamUri(obj).Uri

        return await loop.run_in_executor(None, _get)
    except Exception as e:
        print(f"ONVIF probe {ip}:{port} failed: {e}")
        return None


async def discover_and_connect(username: str, password: str, on_status=None) -> Optional[str]:
    """
    Full discovery flow:
    1. WS-Discovery
    2. Fallback: quick port scan
    3. ONVIF probe with credentials
    Returns the RTSP URI or None.
    """
    def log(msg):
        print(msg)
        if on_status:
            on_status(msg)

    # Step 1: WS-Discovery
    log("🔍 Scanning network via WS-Discovery...")
    devices = await ws_discovery(timeout=5.0)
    log(f"   Found {len(devices)} device(s) via WS-Discovery")

    # Step 2: If empty, quick port scan
    candidate_ips = set(d['ip'] for d in devices)

    if not candidate_ips:
        log("🔍 WS-Discovery empty. Quick-scanning subnet for port 8000...")
        info = get_local_info()
        subnet = info["subnet"]
        my_ip = info["ip"]
        loop = asyncio.get_event_loop()
        hosts = [f"{subnet}.{i}" for i in range(1, 255) if f"{subnet}.{i}" != my_ip]

        async def quick_check(ip):
            try:
                def _check():
                    # Probe most common ONVIF/RTSP ports
                    for p in [8000, 80, 554, 37777, 8899]:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(0.2)
                        res = s.connect_ex((ip, p))
                        s.close()
                        if res == 0: return ip
                    return None
                return await loop.run_in_executor(executor, _check)
            except:
                return None

        results = await asyncio.gather(*[quick_check(ip) for ip in hosts])
        candidate_ips = set(ip for ip in results if ip)
        log(f"   Found {len(candidate_ips)} host(s) with port 8000 open")

    if not candidate_ips:
        log("❌ No cameras found on this network.")
        return None

    # Step 3: ONVIF probe
    for ip in candidate_ips:
        for port in [8000, 80, 8899, 8080]:
            log(f"🔑 Probing {ip}:{port} with credentials...")
            uri = await fetch_onvif_uri(ip, port, username, password)
            if uri:
                # Inject credentials if not in URI
                final = uri
                if f"{username}:" not in uri and "@" not in uri:
                    parts = uri.split("://")
                    if len(parts) == 2:
                        final = f"{parts[0]}://{username}:{password}@{parts[1]}"
                log(f"✅ Found stream: {final}")
                return final

    log("❌ Could not authenticate on any device. Check credentials.")
    return None
