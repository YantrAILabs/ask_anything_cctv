import subprocess

def test_rtsp(url):
    print(f"Testing: {url}")
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-rtsp_transport", "tcp",
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
    creds = "admin:password"
    # Port 8000 is open on .9
    targets = [
        ("192.168.1.9", 8000)
    ]
    paths = [
        "/stream1",
        "/stream2",
        "/live/ch0",
        "/live/ch1",
        "/cam/realmonitor?channel=1&subtype=0",
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
                print(f"  Fail: {msg}")

    if not found:
        print("\nNo working RTSP URLs found.")

if __name__ == "__main__":
    main()
