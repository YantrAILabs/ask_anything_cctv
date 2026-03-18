import socket
import time

def discover_onvif_raw(timeout=3.0):
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
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(1.0)
    
    print("Sending WS-Discovery Probe...")
    sock.sendto(WS_DISCOVERY_PAYLOAD.encode(), ('239.255.255.250', 3702))
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            data, addr = sock.recvfrom(4096)
            print(f"\n--- RESPONSE FROM {addr[0]} ---")
            print(data.decode(errors='ignore'))
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Error: {e}")
            break
    sock.close()

if __name__ == "__main__":
    discover_onvif_raw()
