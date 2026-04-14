import cv2
import numpy as np
import requests
import time
import socket

def get_bot_ip():
    print("Listening for bot IP via UDP broadcast (port 4210)...")
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_socket.bind(("", 4210))
    udp_socket.settimeout(15.0)

    try: 
        while True:
            data, addr = udp_socket.recvfrom(1024)
            msg = data.decode('utf-8', errors='ignore')
            if msg.startswith("ESP_IP:") or msg.startswith("NITC_BOT_IP:"):
                ip = msg.split("IP:")[1].strip()
                print(f"Dynamically found bot at IP: {ip}")
                udp_socket.close()
                return f"http://{ip}"
    except socket.timeout:
        print("Timeout! Make sure bot is on and connected to the same network.")
        udp_socket.close()
        import sys
        sys.exit(1)

# --- CONSTANTS ---
ESP_IP = get_bot_ip() 

CLAW_ALIGN_X = 320 
THRESHOLD = 45     
AREA_MIN = 800     

# HSV Ranges (Optimized for Target Object)
low_obj_color = np.array([122, 56, 0])
high_obj_color = np.array([180, 255, 255])

# HSV Ranges (Optimized for Drop-off Base)
low_dropoff_color = np.array([100, 21, 0])
high_dropoff_color = np.array([140, 255, 255])

cap = cv2.VideoCapture(1) 
last_cmd = ""
last_send_time = 0
SEND_INTERVAL = 0.5 
RATE_LIMIT = 0.1 
robot_state = "empty" # From NodeMCU

def send(path):
    global last_cmd, last_send_time, robot_state
    curr_time = time.time()
    
    is_new_cmd = (path != last_cmd) and ((curr_time - last_send_time) > RATE_LIMIT)
    is_heartbeat = (curr_time - last_send_time) > SEND_INTERVAL
    
    if is_new_cmd or is_heartbeat:
        try:
            response = requests.get(f"{ESP_IP}/{path}", timeout=0.08)
            last_cmd = path
            last_send_time = curr_time
            if response.status_code == 200:
                new_state = response.text.strip()
                if new_state == "holding" and robot_state == "empty":
                    print("SUCCESS! Object physically grabbed! Switching to DROP-OFF search mode.")
                elif new_state == "done" and robot_state == "holding":
                    print("SUCCESS! Object dropped off! Mission completed.")
                robot_state = new_state
        except:
            pass 

while True:
    if robot_state == "done":
        try:
            requests.get(f"{ESP_IP}/stop", timeout=0.1)
        except:
            pass
        break

    ret, frame = cap.read()
    if not ret:
        break
    
    frame = cv2.resize(frame, (640, 480))

    img_yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
    img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
    frame_norm = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
    hsv = cv2.cvtColor(frame_norm, cv2.COLOR_BGR2HSV)

    if robot_state == "holding":
        mask = cv2.inRange(hsv, low_dropoff_color, high_dropoff_color)
        target_name = "DROP-OFF BASE"
        box_color = (255, 0, 0)
    else:
        mask = cv2.inRange(hsv, low_obj_color, high_obj_color)
        target_name = "TARGET OBJECT"
        box_color = (0, 255, 0)
        
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    command = "idle" 

    if contours:
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) > AREA_MIN:
            x, y, w, h = cv2.boundingRect(largest)
            cx = x + (w // 2)

            cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
            cv2.line(frame, (CLAW_ALIGN_X, 0), (CLAW_ALIGN_X, 480), (255, 255, 0), 1)
            cv2.circle(frame, (cx, y + (h//2)), 5, (0, 0, 255), -1)

            if cx < (CLAW_ALIGN_X - THRESHOLD): 
                command = "left"
            elif cx > (CLAW_ALIGN_X + THRESHOLD): 
                command = "right"
            else:
                command = "forward"
                cv2.putText(frame, "LOCKED", (250, 50), 1, 2, (0, 255, 0), 2)

    if command == "idle":
        if robot_state == "holding":
            send("spin") 
            mode_text = f"SPINNING (Seeking {target_name})"
            color = (0, 255, 255) 
        else:
            send("stop") 
            mode_text = f"ROAMING (Seeking {target_name})"
            color = (0, 0, 255)
    else:
        send(command) 
        mode_text = f"TRACKING {target_name}: {command.upper()}"
        color = box_color

    cv2.putText(frame, mode_text, (10, 30), 1, 1, color, 2)
    cv2.imshow("NITC Bot Vision System", frame)
    
    if cv2.waitKey(1) == ord('q'):
        try:
            requests.get(f"{ESP_IP}/stop", timeout=0.1) 
        except:
            pass
        break

cap.release()
cv2.destroyAllWindows()