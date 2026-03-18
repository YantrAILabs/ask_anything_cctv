import asyncio
import socket
import time
from typing import List, Dict
from onvif import ONVIFCamera
from pathlib import Path
import onvif

async def fetch_onvif_uri(ip: str, port: int, user: str, password: str):
    print(f"Probing {ip}:{port}...")
    try:
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
        print(f"FAILED {ip}:{port}: {e}")
        return None

async def test_flow():
    ip = "192.168.1.9"
    user = "admin"
    password = "password"
    
    # Test common ONVIF ports from main.py
    for port in [8000, 8899, 80, 8080]:
        uri = await fetch_onvif_uri(ip, port, user, password)
        if uri:
            print(f"SUCCESS! URI: {uri}")
            return
    print("All ports failed.")

if __name__ == "__main__":
    asyncio.run(test_flow())
