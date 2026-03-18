import cv2
import time

def check_link(url):
    print(f"Checking {url}...")
    cap = cv2.VideoCapture(url)
    if cap.isOpened():
        print("✅ Link is active!")
        cap.release()
        return True
    else:
        print("❌ Link is inactive or unreachable.")
        return False

if __name__ == "__main__":
    check_link("rtsp://admin:password@pressure-invention.gl.joinmc.link:25565/live/channel0")
