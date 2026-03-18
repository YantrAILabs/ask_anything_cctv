import socket

def probe_rtsp(ip, port, timeout=3.0):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        if result == 0:
            return True
    except:
        pass
    return False

def deep_scan():
    ip = "192.168.1.10"
    common_ports = [554, 8554, 8000, 8080, 10554, 5544, 37777, 34567, 8899]
    print(f"Deep probing {ip}...")
    for port in common_ports:
        if probe_rtsp(ip, port):
            print(f"OPEN: {port}")
        else:
            print(f"CLOSED: {port}")

if __name__ == "__main__":
    deep_scan()
