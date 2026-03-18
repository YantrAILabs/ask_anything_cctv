import requests
import re

def get_onvif_stream_uri(ip, port, user, password):
    url = f"http://{ip}:{port}/onvif/device_service"
    
    # Simple SOAP request to GetStreamUri
    # We first need to get profiles, but let's try a generic probe or just use raw SOAP
    
    headers = {'Content-Type': 'application/soap+xml; charset=utf-8'}
    
    # 1. GetProfiles
    get_profiles_soap = f"""<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:trt="http://www.onvif.org/ver10/media/wsdl">
      <s:Body>
        <trt:GetProfiles/>
      </s:Body>
    </s:Envelope>"""
    
    print(f"Querying Profiles on {url}...")
    try:
        # Note: True ONVIF needs WS-UsernameToken auth, but let's see if it responds or gives 401 with details
        response = requests.post(url, data=get_profiles_soap, headers=headers, timeout=5)
        print(f"Response Status: {response.status_code}")
        
        # Look for ProfileToken in response
        tokens = re.findall(r'token="([^"]+)"', response.text)
        if not tokens:
            tokens = re.findall(r'<tt:Name>([^<]+)</tt:Name>', response.text) # sometimes in Name
        
        if not tokens:
            print("No profiles found. Response text snippet:")
            print(response.text[:500])
            return None
        
        token = tokens[0]
        print(f"Using Profile Token: {token}")
        
        # 2. GetStreamUri
        get_stream_uri_soap = f"""<?xml version="1.0" encoding="utf-8"?>
        <s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:trt="http://www.onvif.org/ver10/media/wsdl" xmlns:tt="http://www.onvif.org/ver10/schema">
          <s:Body>
            <trt:GetStreamUri>
              <trt:StreamSetup>
                <tt:Stream>RTP-Unicast</tt:Stream>
                <tt:Transport>
                  <tt:Protocol>RTSP</tt:Protocol>
                </tt:Transport>
              </trt:StreamSetup>
              <trt:ProfileToken>{token}</trt:ProfileToken>
            </trt:GetStreamUri>
          </s:Body>
        </s:Envelope>"""
        
        response = requests.post(url, data=get_stream_uri_soap, headers=headers, timeout=5)
        uri_match = re.search(r'<tt:Uri>([^<]+)</tt:Uri>', response.text)
        if uri_match:
            return uri_match.group(1)
        else:
            print("Stream URI not found in response.")
            print(response.text[:500])
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    uri = get_onvif_stream_uri("192.168.1.9", "8000", "admin", "password")
    if uri:
        print(f"\nSUCCESS! ONVIF Stream URI: {uri}")
    else:
        print("\nFailed to get stream URI via ONVIF.")
