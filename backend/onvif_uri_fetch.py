from onvif import ONVIFCamera
import os

def get_onvif_uri(ip, port, user, password):
    print(f"Connecting to ONVIF camera at {ip}:{port}...")
    try:
        # CP-Plus often uses port 8000 for ONVIF
        # onvif-zeep expects the path to wsdl files, but usually it finds them in its own package
        mycam = ONVIFCamera(ip, port, user, password)
        
        # Create media service
        media = mycam.create_media_service()
        
        # Get profiles
        profiles = media.GetProfiles()
        if not profiles:
            print("No ONVIF profiles found.")
            return None
        
        # Use first profile
        profile = profiles[0]
        token = profile.token
        print(f"Found Profile: {profile.Name} (Token: {token})")
        
        # Get Stream URI
        obj = media.create_type('GetStreamUri')
        obj.StreamSetup = {
            'Stream': 'RTP-Unicast',
            'Transport': {'Protocol': 'RTSP'}
        }
        obj.ProfileToken = token
        
        res = media.GetStreamUri(obj)
        return res.Uri
        
    except Exception as e:
        print(f"ONVIF Error: {e}")
        return None

if __name__ == "__main__":
    uri = get_onvif_uri("192.168.1.9", 8000, "admin", "password")
    if uri:
        print(f"\nSUCCESS! ONVIF Stream URI: {uri}")
        # Write to a temp file for the agent to read
        with open("working_uri.txt", "w") as f:
            f.write(uri)
    else:
        print("\nFailed to retrieve stream URI.")
