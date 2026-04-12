import cv2
import numpy as np

# Global variable to store the HSV frame
hsv_frame = None 

def nothing(x):
    pass

def pick_color(event, x, y, flags, param):
    global hsv_frame
    if event == cv2.EVENT_LBUTTONDBLCLK:
        if hsv_frame is not None:
            # Get the HSV value at the clicked coordinate
            # Note: y is row, x is column
            h, s, v = hsv_frame[y, x]
            
            # Create a range
            h_min, h_max = np.clip([h-10, h+10], 0, 180)
            s_min, s_max = np.clip([s-40, s+40], 0, 255)
            v_min, v_max = np.clip([v-40, v+40], 0, 255)

            # Update Trackbars
            cv2.setTrackbarPos("H Min", "Controls", int(h_min))
            cv2.setTrackbarPos("H Max", "Controls", int(h_max))
            cv2.setTrackbarPos("S Min", "Controls", int(s_min))
            cv2.setTrackbarPos("S Max", "Controls", int(s_max))
            cv2.setTrackbarPos("V Min", "Controls", int(v_min))
            cv2.setTrackbarPos("V Max", "Controls", int(v_max))
            print(f"Picked HSV: {h}, {s}, {v}")

# 1. Create Windows First
cv2.namedWindow("Controls")
cv2.namedWindow("Bot Control")
cv2.setMouseCallback("Bot Control", pick_color)

# 2. Create Trackbars on the "Controls" window
cv2.createTrackbar("H Min", "Controls", 0, 180, nothing)
cv2.createTrackbar("H Max", "Controls", 180, 180, nothing)
cv2.createTrackbar("S Min", "Controls", 0, 255, nothing)
cv2.createTrackbar("S Max", "Controls", 255, 255, nothing)
cv2.createTrackbar("V Min", "Controls", 0, 255, nothing)
cv2.createTrackbar("V Max", "Controls", 255, 255, nothing)

cap = cv2.VideoCapture(1)

while True:
    ret, frame = cap.read()
    if not ret: break

    # FORCE frame to a consistent size so mouse coordinates match
    frame = cv2.resize(frame, (640, 480))
    
    # Lighting Normalization (Must match your bot code)
    img_yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
    img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
    frame_norm = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
    
    # Update the global HSV frame
    hsv_frame = cv2.cvtColor(frame_norm, cv2.COLOR_BGR2HSV)

    # Read Trackbars from "Controls" window
    h_min = cv2.getTrackbarPos("H Min", "Controls")
    h_max = cv2.getTrackbarPos("H Max", "Controls")
    s_min = cv2.getTrackbarPos("S Min", "Controls")
    s_max = cv2.getTrackbarPos("S Max", "Controls")
    v_min = cv2.getTrackbarPos("V Min", "Controls")
    v_max = cv2.getTrackbarPos("V Max", "Controls")

    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, s_max, v_max])

    # Create Mask
    mask = cv2.inRange(hsv_frame, lower, upper)
    
    # Show the actual filtered object (Bitwise AND)
    res = cv2.bitwise_and(frame_norm, frame_norm, mask=mask)

    cv2.imshow("Bot Control", frame_norm)
    cv2.imshow("Mask", mask)
    cv2.imshow("Live Filter", res)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()