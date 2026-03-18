import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_local_subnet():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return ".".join(local_ip.split(".")[:3])
    except Exception:
        return "192.168.1"

def probe_host(ip, port, timeout=1.5):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        if result == 0:
            return (ip, port)
    except:
        pass
    return None

def scan():
    subnet = get_local_subnet()
    print(f"Scanning subnet: {subnet}.*")
    # Added 8899 (ONVIF), 37777 (CP Plus), 34567 (XMeye)
    ports = [554, 8554, 80, 8080, 8888, 7447, 8899, 37777, 34567, 8000]
    found = []
    
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = []
        for i in range(1, 255):
            ip = f"{subnet}.{i}"
            for port in ports:
                futures.append(executor.submit(probe_host, ip, port))
        
        for future in as_completed(futures):
            res = future.result()
            if res:
                print(f"FOUND: {res[0]}:{res[1]}")
                found.append(res)

    print(f"\nScan complete. Found {len(found)} devices.")

if __name__ == "__main__":
    scan()
