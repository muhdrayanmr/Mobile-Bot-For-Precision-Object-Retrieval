import cv2
import numpy as np
import requests
import time

# --- CONSTANTS ---
# UPDATE THIS IP with the one shown in your Arduino Serial Monitor or Phone Menu
ESP_IP = "http://10.216.190.237" 

CLAW_ALIGN_X = 320 # True center for 640px width
THRESHOLD = 45     # Deadzone for alignment
AREA_MIN = 800     # Minimum size of object to trigger Vision Mode

# HSV Ranges (Optimized for Green)
low_green = np.array([49,85,0])
high_green = np.array([76, 255, 255])

cap = cv2.VideoCapture(1) # Try 0 if 1 doesn't open
last_cmd = ""
last_send_time = 0
SEND_INTERVAL = 0.15 # 150ms buffer to keep NodeMCU stable

def send(path):
    global last_cmd, last_send_time
    curr_time = time.time()
    
    # Only send if command changed OR to keep the connection alive (heartbeat)
    if path != last_cmd or (curr_time - last_send_time) > SEND_INTERVAL:
        try:
            requests.get(f"{ESP_IP}/{path}", timeout=0.08)
            last_cmd = path
            last_send_time = curr_time
        except:
            pass # Silently fail if bot is out of range

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # 1. Resize and Flip
    frame = cv2.resize(frame, (640, 480))
    frame = cv2.flip(frame, 1)

    # 2. Pre-processing for better color detection
    img_yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
    img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
    frame_norm = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
    hsv = cv2.cvtColor(frame_norm, cv2.COLOR_BGR2HSV)

    # 3. Masking
    mask = cv2.inRange(hsv, low_green, high_green)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    command = "idle" 

    if contours:
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) > AREA_MIN:
            x, y, w, h = cv2.boundingRect(largest)
            cx = x + (w // 2)

            # Draw UI Visuals
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.line(frame, (CLAW_ALIGN_X, 0), (CLAW_ALIGN_X, 480), (255, 255, 0), 1)
            cv2.circle(frame, (cx, y + (h//2)), 5, (0, 0, 255), -1)

            # Alignment Logic
            if cx < (CLAW_ALIGN_X - THRESHOLD): 
                command = "left"
            elif cx > (CLAW_ALIGN_X + THRESHOLD): 
                command = "right"
            else:
                command = "forward"
                cv2.putText(frame, "LOCKED", (250, 50), 1, 2, (0, 255, 0), 2)

    # 4. Handoff to NodeMCU
    if command == "idle":
        send("stop") # Triggers Roamer Mode on NodeMCU
        mode_text = "ROAMING (Obstacle Avoidance)"
        color = (0, 0, 255)
    else:
        send(command) # Triggers Vision Mode
        mode_text = f"VISION ACTIVE: {command.upper()}"
        color = (0, 255, 0)

    # UI Overlay
    cv2.putText(frame, mode_text, (10, 30), 1, 1, color, 2)
    cv2.imshow("NITC Bot Vision System", frame)
    
    if cv2.waitKey(1) == ord('q'):
        send("stop") # Ensure bot enters safe mode on exit
        break

cap.release()
cv2.destroyAllWindows()