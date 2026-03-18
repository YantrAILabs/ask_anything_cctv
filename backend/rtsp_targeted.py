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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
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
    # Port 8000 is open on .10, Port 8899 is open on .2
    targets = [
        ("192.168.1.10", 8000),
        ("192.168.1.2", 8899),
        ("192.168.1.10", 554), # Double check 554 with auth
        ("192.168.1.2", 554)
    ]
    paths = [
        "/cam/realmonitor?channel=1&subtype=0",
        "/cam/realmonitor?channel=1&subtype=1",
        "/live/ch0",
        "/live/ch1",
        "/stream1",
        "/onvif1",
        "/media/video1",
        "/1",
        ""
    ]
    
    found = []
    for ip, port in targets:
        for path in paths:
            url = f"rtsp://{creds}@{ip}:{port}{path}"
            success, msg = test_rtsp(url)
            if success:
                print(f"!!! FOUND WORKING URL: {url} !!!")
                found.append(url)
                return # Stop at first working URL
            else:
                if "Unauthorized" in msg:
                    print(f"  Auth Failure: {ip}:{port}{path}")
                elif "Invalid data" in msg:
                    print(f"  Path Error or Data Error: {ip}:{port}{path}")

    if not found:
        print("\nNo working RTSP URLs found.")

if __name__ == "__main__":
    main()
