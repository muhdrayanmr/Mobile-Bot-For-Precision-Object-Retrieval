import cv2
import numpy as np
import time

# --- TUNABLE CALIBRATION (Match these to your mission script later) ---
CLAW_X = 220 
THRESHOLD = 40 
AREA_MIN = 600
LOCK_TIME_REQ = 2.0 

# CURRENT TARGET: 0 for Green Object, 1 for Blue Drop Zone
TEST_MODE = 0 

# HSV Ranges (Updated from your tuning)
low_green = np.array([46, 52, 100])
high_green = np.array([73, 184, 255])

low_blue = np.array([96, 59, 156]) # Placeholder - Tune this with your picker!
high_blue = np.array([120, 212, 255])

cap = cv2.VideoCapture(1) 

lock_start = None

print("--- BOT MISSION CALIBRATION TOOL ---")
print("Verify your CLAW_X matches the physical claw hinge.")
print("Press 'm' to toggle between Green (Object) and Blue (Drop) testing.")

while True:
    ret, frame = cap.read()
    if not ret: break
    
    frame = cv2.flip(frame, 1)
    h_img, w_img = frame.shape[:2]

    # 1. LIGHTING NORMALIZATION (Identical to Mission Code)
    img_yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
    img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
    frame_norm = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
    hsv = cv2.cvtColor(frame_norm, cv2.COLOR_BGR2HSV)

    # 2. SELECT RANGE
    low, high = (low_green, high_green) if TEST_MODE == 0 else (low_blue, high_blue)
    target_name = "GREEN OBJECT" if TEST_MODE == 0 else "BLUE DROP-ZONE"

    mask = cv2.inRange(hsv, low, high)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    status_color = (255, 255, 0) # Cyan (Default)
    sim_cmd = "STOP"

    if contours:
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        
        if area > AREA_MIN:
            x, y, w, h = cv2.boundingRect(largest)
            cx = x + (w // 2)

            # 3. ALIGNMENT LOGIC (Matches NodeMCU steer directions)
            if abs(cx - CLAW_X) <= THRESHOLD:
                status_color = (0, 255, 0) # Green (Aligned)
                sim_cmd = "FORWARD"
                if lock_start is None: lock_start = time.time()
            else:
                status_color = (0, 0, 255) # Red (Misaligned)
                sim_cmd = "TURN LEFT" if cx < CLAW_X else "TURN RIGHT"
                lock_start = None

            cv2.rectangle(frame, (x, y), (x + w, y + h), status_color, 2)
            cv2.circle(frame, (cx, y + h//2), 5, (0, 0, 255), -1)
            
            # Area/Distance Visualization
            bar_h = int(min(area / 50, 400)) 
            cv2.rectangle(frame, (w_img-40, 450), (w_img-10, 450-bar_h), (255, 165, 0), -1)

    # UI OVERLAYS
    cv2.line(frame, (CLAW_X, 0), (CLAW_X, h_img), (255, 255, 0), 2) # The "Goal"
    cv2.line(frame, (CLAW_X - THRESHOLD, 0), (CLAW_X - THRESHOLD, h_img), (100, 100, 100), 1)
    cv2.line(frame, (CLAW_X + THRESHOLD, 0), (CLAW_X + THRESHOLD, h_img), (100, 100, 100), 1)

    cv2.putText(frame, f"TESTING: {target_name}", (10, 30), 1, 1, (255, 255, 255), 1)
    cv2.putText(frame, f"NAV: {sim_cmd}", (10, 70), 1, 2, status_color, 3)
    
    if lock_start:
        elapsed = time.time() - lock_start
        cv2.putText(frame, f"LOCKING: {elapsed:.1f}s", (10, 110), 1, 1.5, (0, 255, 255), 2)
        if elapsed >= LOCK_TIME_REQ:
            action = "PICKUP" if TEST_MODE == 0 else "DROP"
            cv2.putText(frame, f"!!! TRIGGER {action} !!!", (w_img//2 - 150, h_img//2), 1, 2, (0, 255, 0), 3)

    cv2.imshow("Mission Calibration", frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    if key == ord('m'): TEST_MODE = 1 - TEST_MODE # Toggle mode

cap.release()
cv2.destroyAllWindows()