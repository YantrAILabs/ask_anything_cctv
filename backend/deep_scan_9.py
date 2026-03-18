import socket
from concurrent.futures import ThreadPoolExecutor

def probe_port(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        res = sock.connect_ex((ip, port))
        sock.close()
        if res == 0:
            return port
    except:
        pass
    return None

def main():
    ip = "192.168.1.9"
    # Wider range of potential camera ports
    ports = [
        554, 8554, 8000, 8080, 8899, 37777, 34567, 5000, 5544, 10554, 
        80, 443, 81, 82, 8001, 8002, 9000, 9100, 5001, 5002, 6001, 6002
    ]
    print(f"Scanning {ip} for common camera ports...")
    
    with ThreadPoolExecutor(max_workers=len(ports)) as executor:
        results = executor.map(lambda p: probe_port(ip, p), ports)
        
    found = [p for p in results if p is not None]
    if found:
        print(f"FOUND OPEN PORTS: {found}")
    else:
        print("No open ports found in the test list.")

if __name__ == "__main__":
    main()
