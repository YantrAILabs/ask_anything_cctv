import subprocess

def test_rtsp(url):
    print(f"Testing: {url}")
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        url
    ]
    try:
        # Use a short timeout
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return True, "SUCCESS"
        else:
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)

def main():
    creds = "admin:Mohit@1234"
    ips = ["192.168.1.10", "192.168.1.2"]
    ports = [554, 8000, 8899, 5544]
    paths = [
        "/cam/realmonitor?channel=1&subtype=0",
        "/live/ch0",
        "/stream1",
        "/onvif1",
        "/media/video1",
        ""
    ]
    
    found = []
    for ip in ips:
        for port in ports:
            for path in paths:
                url = f"rtsp://{creds}@{ip}:{port}{path}"
                success, msg = test_rtsp(url)
                if success:
                    print(f"!!! FOUND WORKING URL: {url} !!!")
                    found.append(url)
                else:
                    # Print only errors that aren't just "connection refused" if possible
                    if "Invalid data" in msg or "Unauthorized" in msg:
                        print(f"  Result: {msg}")

    if not found:
        print("\nNo working RTSP URLs found.")
    else:
        print(f"\nFound {len(found)} working URLs.")

if __name__ == "__main__":
    main()
