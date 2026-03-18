import cv2
import subprocess
import time
import os

def test_capture(url):
    print(f"\n--- Testing Capture for: {url} ---")
    # Try with OpenCV first (usually uses FFmpeg backend)
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        print("OpenCV: Could not open stream.")
    else:
        ret, frame = cap.read()
        if ret:
            print("OpenCV: SUCCESS - Captured frame.")
            cv2.imwrite("test_capture_cv2.jpg", frame)
            cap.release()
            return True
        else:
            print("OpenCV: Failed to read frame.")
    cap.release()

    # Try raw FFmpeg command to isolate environmental issues
    print("Trying raw FFmpeg command...")
    output_file = "test_capture_ffmpeg.jpg"
    if os.path.exists(output_file): os.remove(output_file)
    
    cmd = [
        "ffmpeg", "-y",
        "-rtsp_transport", "tcp",
        "-i", url,
        "-frames:v", "1",
        "-f", "image2",
        output_file
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if os.path.exists(output_file):
            print("FFmpeg: SUCCESS - Captured frame.")
            return True
        else:
            print(f"FFmpeg: FAILED. Return code: {proc.returncode}")
            print(f"Error Log: {proc.stderr[-500:]}")
    except Exception as e:
        print(f"FFmpeg Error: {e}")
    
    return False

if __name__ == "__main__":
    url = "rtsp://admin:password@192.168.1.9:5543/live/channel0"
    test_capture(url)
