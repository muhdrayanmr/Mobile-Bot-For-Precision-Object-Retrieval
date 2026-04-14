# Autonomous Pick-and-Place Robot Architecture

This document describes the software architecture and logic flow for the autonomous pick-and-place robot. The system coordinates three distinct hardware entities to identify, navigate to, retrieve, and drop off specific targets.

## System Components

1. **Vision System (`vision.py`)** 
   - **Hardware**: PC or Laptop, utilizing a mobile phone camera feed (e.g., via IP Webcam or Iriun).
   - **Role**: Serves as the "brain" for high-level targeting. Uses OpenCV to detect objects by matching specific HSV (Hue-Saturation-Value) color ranges. It computes alignment offsets and issues navigation commands (forward, left, right, spin) to the NodeMCU over Wi-Fi.
2. **Main Motor Controller (`sketch.ino`)**
   - **Hardware**: NodeMCU (ESP8266).
   - **Role**: Manages Wi-Fi networking, UDP broadcasting, IR/Ultrasonic sensory inputs, and motor driver (L298N) outputs. It operates the core state machine for the robot and handles the fallback "Roamer Mode" when no target is detected.
3. **Claw/Arm Actuator (`claw.ino`)**
   - **Hardware**: Arduino Uno.
   - **Role**: Drives the physical servo motors to smoothly raise/lower the arm and open/close the claw. It operates as a slave to the NodeMCU, waiting for a physical GPIO trigger to execute an action.

---

## State Machine & Logic Flow

The robot follows a strictly defined sequential state machine representing its goals. 

### Phase 1: Auto-Discovery & Initialization
- Upon powering on, the **NodeMCU** connects to the local hotspot and begins broadcasting its IP address continuously over the network using `WiFiUDP` (Port 4210).
- The **Vision script** listens on this UDP port. Upon receiving the payload `NITC_BOT_IP:xxx.xxx...`, it parses the IP and binds an HTTP Client. 
- Using dynamic binding prevents the need for manual hard-coding whenever DHCP assigns a new IP address.

### Phase 2: Roamer Mode
- If no target is visible, the Python script sends `/stop` to indicate it is not tracking anything. The NodeMCU's internal `target_visible` flag stays `false`.
- The NodeMCU activates **Roamer Mode**. It drives forward at a regular speed and relies on the two front Infrared (IR) sensors and the Ultrasonic sensor to actively swerve and avoid obstacles in real-time.

### Phase 3: Object Detection & Alignment
- **Detection**: OpenCV processes frames using YUV histogram equalization and applies the *Target Object* HSV mask. If a valid contour exceeding `AREA_MIN` is detected, the target's center point ($$X_{cx}$$) is calculated.
- **Alignment**:
  - If $$X_{cx}$$ is significantly left of the frame center point (`CLAW_ALIGN_X - THRESHOLD`), it requests `/left`. 
  - If it is to the right, it requests `/right`.
  - When locked to the center, it requests `/forward`.
- **NodeMCU Override**: Receiving these commands triggers `target_visible = true`. In this state, the robot **ignores the IR sensors** (to prevent dodging the target object itself) and relies heavily on the Ultrasonic sensor to gauge distance to the target. Fine motors movements are used (e.g., lower `turnSpeed` parameter) to maintain alignment precision.

### Phase 4: Handshake & Pickup
- As the robot approaches the target object, the distance read by the Ultrasonic sensor rapidly drops.
- When `dist < 10 cm`, it executes an immediate Hardware Stop.
- **Handshake Protocol**:
  1. NodeMCU asserts state `EMPTY` to `HOLDING`.
  2. NodeMCU pulses `CLAW_TRIG` (LOW) to the Arduino Uno.
  3. The Arduino Uno triggers the `pickup()` function, smoothly operating the servos.
  4. The Uno holds `CLAW_DONE` high while busy, pulling it LOW when the physical movement completes.
  5. The NodeMCU waits for the LOW signal from `CLAW_DONE` before continuing.
- Once completed, the NodeMCU informs `vision.py` by replying with `holding` to HTTP requests.

### Phase 5: Search & Drop-Off
- `vision.py` reads the new `holding` state and dynamically switches its OpenCV pipeline to seek the *Drop-Off* HSV range instead of the object color.
- Since the drop-off base is likely out of frame, the object logic resolves to `idle`, so Python requests `/spin`.
- The NodeMCU receives `/spin`, locks one set of wheels forward and the other backward, and continuously executes a slow 360-degree rotation.
- When the drop-off target is spotted, Python overrides the spin with alignment logic (`/left`, `/right`, `/forward`) and steers the robot to the base.

### Phase 6: Final Drop & Termination
- As before, when the Ultrasonic sensor reads `dist < 10 cm`, it signals arrival at the drop-off base.
- **Drop-off**:
  1. NodeMCU verifies it is in the `HOLDING` state.
  2. It triggers `CLAW_TRIG` a final time.
  3. The Arduino Uno toggles to the `drop()` sequence, opening the claw and retracting the arm to standby (`ARM_UP`).
- NodeMCU updates its master state to `DONE`.
- `vision.py` queries an endpoint, reads `done`, submits one last fail-safe `/stop` command, and cleanly terminates execution.
- NodeMCU enters a perpetual blocking loop where motors are deactivated indefinitely. Mission Success is achieved. 

---

## Safety Mechanisms
1. **Network Watchdog**: If the NodeMCU stops receiving commands from Python for >1000ms during an active run, it kills the motors and reverts to roamer mode to prevent crashing if the PC disconnects.
2. **Servo Sweeping System**: The Arduino Uno utilizes manual degree-by-degree iteration rather than high-level position snaps. This reduces torque fatigue and battery voltage droop (brown-outs) on the ESP.
3. **Impedance Pins**: The Arduino Uno ensures its `DONE_PIN` is set as high-impedance `INPUT` when not sending a completion signal, keeping the NodeMCU's UART lines interference-free during boot.
