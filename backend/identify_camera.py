import socket

def get_banner(ip, port, timeout=2.0):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        # Send a generic HTTP request to see if we get a response
        sock.send(b"GET / HTTP/1.1\r\nHost: " + ip.encode() + b"\r\n\r\n")
        banner = sock.recv(1024)
        sock.close()
        return banner.decode(errors='ignore')
    except Exception as e:
        return str(e)

def identify():
    targets = [("192.168.1.2", 8899), ("192.168.1.10", 8000)]
    for ip, port in targets:
        print(f"--- Probing {ip}:{port} ---")
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            print(f"Hostname: {hostname}")
        except:
            print("Hostname: Unknown")
        
        banner = get_banner(ip, port)
        print(f"Banner/Response: {banner[:200]}...")
        print("\n")

if __name__ == "__main__":
    identify()
