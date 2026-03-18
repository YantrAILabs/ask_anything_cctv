import cv2
import time

class MotionDetector:
    def __init__(self, threshold=500, min_area=500):
        self.threshold = threshold
        self.min_area = min_area
        self.avg_frame = None

    def detect(self, frame):
        # Convert to grayscale and blur
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # Initialize average frame
        if self.avg_frame is None:
            self.avg_frame = gray.copy().astype("float")
            return False, []

        # Accumulate the weighted average
        cv2.accumulateWeighted(gray, self.avg_frame, 0.5)
        frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(self.avg_frame))

        # Threshold the delta image
        thresh = cv2.threshold(frame_delta, self.threshold, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        # Find contours
        cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_detected = False
        bounding_boxes = []

        for c in cnts:
            if cv2.contourArea(c) < self.min_area:
                continue
            
            (x, y, w, h) = cv2.boundingRect(c)
            bounding_boxes.append((x, y, w, h))
            motion_detected = True

        return motion_detected, bounding_boxes
