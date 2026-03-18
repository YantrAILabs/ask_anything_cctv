import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    ips = ["192.168.1.1", "192.168.1.2", "192.168.1.3", "192.168.1.5", "192.168.1.7", "192.168.1.10", "192.168.1.12"]
    ports = [554, 8554, 80, 8080, 8888, 7447, 8899, 37777, 34567, 8000]
    print(f"Targeted scan on {len(ips)} IPs across {len(ports)} ports...")
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for ip in ips:
            for port in ports:
                futures.append(executor.submit(probe_host, ip, port))
        
        for future in as_completed(futures):
            res = future.result()
            if res:
                print(f"FOUND: {res[0]}:{res[1]}")

if __name__ == "__main__":
    scan()
