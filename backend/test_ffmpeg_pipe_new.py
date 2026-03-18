import subprocess
import os
import numpy as np

def test_ffmpeg_pipe_new():
    url = "rtsp://admin:password@192.168.1.9:5543/live/channel0"
    FRAME_W, FRAME_H = 1280, 720
    frame_size = FRAME_W * FRAME_H * 3
    
    # New command with -timeout instead of -stimeout
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "debug",
        "-rtsp_transport", "tcp",
        "-timeout", "5000000",
        "-i", url,
        "-vf", f"scale={FRAME_W}:{FRAME_H}",
        "-pix_fmt", "bgr24", "-vcodec", "rawvideo",
        "-an", "-sn", "-f", "rawvideo", "pipe:1"
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Read one frame
        raw = proc.stdout.read(frame_size)
        err = proc.stderr.read(3000).decode(errors='ignore')
        
        if len(raw) == frame_size:
            print("SUCCESS: Read one full frame from pipe.")
        else:
            print(f"FAILURE: Read only {len(raw)} bytes. Expected {frame_size}.")
            print("--- STDERR SNIPPET ---")
            print(err)
            
        proc.kill()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ffmpeg_pipe_new()
