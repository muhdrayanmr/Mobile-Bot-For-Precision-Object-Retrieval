import cv2
import numpy as np
import time

# --- TUNABLE CALIBRATION ---
CLAW_X = 220 
THRESHOLD = 40 
AREA_MIN = 600
LOCK_TIME_REQ = 2.0 

# HSV Ranges
low_green = np.array([65, 64, 99])
high_green = np.array([96, 255, 255])

cap = cv2.VideoCapture(1) # Try 0 if 1 fails
lock_start = None

print("--- ADVANCED VISION CALIBRATION TOOL ---")
print("1. Align the Cyan line with your physical claw.")
print("2. Adjust THRESHOLD so the 'Strike Zone' is wide enough for your claw.")
print("3. Check if the Area Bar grows consistently as you move closer.")

while True:
    ret, frame = cap.read()
    if not ret: break
    
    frame = cv2.flip(frame, 1)
    h_img, w_img = frame.shape[:2]

    # Pre-processing
    img_yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
    img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
    frame_norm = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
    hsv = cv2.cvtColor(frame_norm, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, low_green, high_green)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    status_color = (255, 255, 0) # Cyan
    sim_cmd = "STOP"

    if contours:
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        
        if area > AREA_MIN:
            x, y, w, h = cv2.boundingRect(largest)
            cx = x + (w // 2)

            # Check Strike Zone
            if abs(cx - CLAW_X) <= THRESHOLD:
                status_color = (0, 255, 0) # Green (Ready)
                sim_cmd = "FORWARD / ALIGNED"
                if lock_start is None: lock_start = time.time()
            else:
                status_color = (0, 0, 255) # Red (Misaligned)
                sim_cmd = "LEFT" if cx < CLAW_X else "RIGHT"
                lock_start = None

            # Visuals
            cv2.rectangle(frame, (x, y), (x + w, y + h), status_color, 2)
            cv2.circle(frame, (cx, y + h//2), 5, (0, 0, 255), -1)
            
            # Area/Distance Bar
            bar_h = int(min(area / 50, 400)) 
            cv2.rectangle(frame, (w_img-40, 450), (w_img-10, 450-bar_h), (255, 100, 0), -1)
            cv2.putText(frame, "DIST", (w_img-50, 470), 1, 1, (255, 255, 255), 1)

    # UI OVERLAYS
    # Draw Strike Zone
    cv2.line(frame, (CLAW_X, 0), (CLAW_X, h_img), status_color, 2)
    cv2.line(frame, (CLAW_X - THRESHOLD, 0), (CLAW_X - THRESHOLD, h_img), (100, 100, 100), 1)
    cv2.line(frame, (CLAW_X + THRESHOLD, 0), (CLAW_X + THRESHOLD, h_img), (100, 100, 100), 1)

    cv2.putText(frame, f"CMD: {sim_cmd}", (10, 50), 1, 2, status_color, 3)
    
    if lock_start:
        elapsed = time.time() - lock_start
        cv2.putText(frame, f"LOCKING: {elapsed:.1f}s", (10, 90), 1, 1.5, (0, 255, 255), 2)
        if elapsed >= LOCK_TIME_REQ:
            cv2.putText(frame, "--- READY TO GRAB ---", (w_img//2 - 100, h_img//2), 1, 2, (0, 255, 0), 3)

    cv2.imshow("Calibration Tool", frame)
    if cv2.waitKey(1) == ord('q'): break

cap.release()
cv2.destroyAllWindows()