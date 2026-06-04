import cv2
import mediapipe as mp
import serial
import time
import math

# =========================================================================================
# VISION PUPPET PRO: HUMAN-LIKE KINEMATICS & INTELLIGENCE
# 
# 1. Holt's Double Exponential Smoothing: Simulates organic muscle mass and momentum.
# 2. Gesture "Clutch": Make a tight FIST to freeze the arm in space. Open hand to resume.
# 3. Kinematic Coupling: Coordinated shoulder, elbow, and wrist-pitch for natural reaching.
# 4. Organic Idle: The arm subtly "breathes" when parked, making it look alive.
# =========================================================================================

class OrganicSmoother:
    """Holt's Double Exponential Smoothing. Tracks both position and velocity 
    to simulate physical momentum and mass, preventing jerky robotic movements."""
    def __init__(self, initial_val, alpha=0.35, beta=0.15):
        self.s = initial_val  # Position
        self.b = 0.0          # Velocity / Trend
        self.alpha = alpha    # Data smoothing factor
        self.beta = beta      # Trend smoothing factor

    def update(self, target):
        old_s = self.s
        self.s = self.alpha * target + (1 - self.alpha) * (self.s + self.b)
        self.b = self.beta * (self.s - old_s) + (1 - self.beta) * self.b
        return self.s

def map_range(x, in_min, in_max, out_min, out_max):
    val = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return max(min(out_min, out_max), min(max(out_min, out_max), val))

def is_fist(landmarks):
    """Detects if the hand is closed in a fist (Clutch gesture)"""
    wrist = landmarks.landmark[mp_hands.HandLandmark.WRIST]
    tips = [
        mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP
    ]
    mcps = [
        mp_hands.HandLandmark.INDEX_FINGER_MCP,
        mp_hands.HandLandmark.MIDDLE_FINGER_MCP,
        mp_hands.HandLandmark.RING_FINGER_MCP,
        mp_hands.HandLandmark.PINKY_MCP
    ]
    
    curled_fingers = 0
    for tip, mcp in zip(tips, mcps):
        dist_tip_to_wrist = math.hypot(landmarks.landmark[tip].x - wrist.x, landmarks.landmark[tip].y - wrist.y)
        dist_mcp_to_wrist = math.hypot(landmarks.landmark[mcp].x - wrist.x, landmarks.landmark[mcp].y - wrist.y)
        if dist_tip_to_wrist < dist_mcp_to_wrist:
            curled_fingers += 1
            
    return curled_fingers >= 3

# --- SERIAL SETUP ---
try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    time.sleep(3)
    ser.reset_input_buffer()
except Exception as e:
    print(f"Failed to connect to ESP32: {e}")
    exit()

# --- VISION SETUP ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.75, min_tracking_confidence=0.75)
mp_draw = mp.solutions.drawing_utils

# Open external USB Webcam (Index 1) using DirectShow, fallback to internal (Index 0)
cap = cv2.VideoCapture(1 + cv2.CAP_DSHOW)
if not cap.isOpened():
    print("USB Webcam (Index 1) not found. Falling back to internal camera (Index 0).")
    cap = cv2.VideoCapture(0 + cv2.CAP_DSHOW)

# --- STATE VARIABLES ---
home_state = [90, 90, 0, 145, 80, 45]
smoothers = [OrganicSmoother(val) for val in home_state]
last_send_time = time.time()
arm_frozen = False
no_hand_time = time.time()

print("\n--- PRO SYSTEM ACTIVE ---")
print("-> Make a FIST to FREEZE the arm (Clutch).")
print("-> OPEN HAND to resume tracking.")
print("-> Drops hand out of view to auto-park.\n")

try:
    while cap.isOpened():
        success, image = cap.read()
        if not success: continue

        image = cv2.flip(image, 1) # Natural mirror
        results = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        target_angles = list(home_state)
        hand_detected = False

        if results.multi_hand_landmarks:
            hand_detected = True
            no_hand_time = time.time()
            hand_landmarks = results.multi_hand_landmarks[0]
            mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # 1. GESTURE ENGINE (The Clutch)
            if is_fist(hand_landmarks):
                arm_frozen = True
                cv2.putText(image, "CLUTCH ACTIVE (FROZEN)", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            else:
                arm_frozen = False
                
            if not arm_frozen:
                lm0 = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                lm9 = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                
                # 2. COORDINATED KINEMATIC REACHING
                center_x, center_y = lm9.x, lm9.y
                palm_size = math.hypot(lm9.x - lm0.x, lm9.y - lm0.y)
                
                # Reach mapping (0.0=Retracted, 1.0=Fully Extended)
                reach_factor = map_range(palm_size, 0.05, 0.25, 0.0, 1.0)
                
                # As you reach forward, Rotary leans, Elbow opens, and Up/Down tilts to compensate!
                rotary_target = map_range(reach_factor, 0.0, 1.0, 145, 60)
                elbow_target = map_range(reach_factor, 0.0, 1.0, 0, 150)
                
                # Base Swivel (X-axis)
                base_target = map_range(center_x, 0.1, 0.9, 180, 0)
                
                # Elevation (Y-axis) - Adjusts height
                base_elevation = map_range(center_y, 0.1, 0.9, 160, 20)
                up_down_target = base_elevation
                
                # 3. WRIST ROLL
                dx = lm9.x - lm0.x
                dy = lm9.y - lm0.y
                angle_deg = math.degrees(math.atan2(dy, dx))
                wrist_target = map_range(angle_deg, -135, -45, 190, 100)
                
                # 4. DYNAMIC GRIP (Continuous Claw)
                thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                pinch_dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
                claw_target = map_range(pinch_dist, 0.03, 0.12, 0, 90)
                
                target_angles = [base_target, rotary_target, elbow_target, wrist_target, up_down_target, claw_target]

        # Apply Organic Smoothing (If frozen, targets become whatever it is currently at)
        current_smoothed = []
        for i in range(6):
            if arm_frozen:
                # Bypass smoothing and lock current state
                current_smoothed.append(smoothers[i].s)
            elif not hand_detected and time.time() - no_hand_time > 1.5:
                # Organic Idle Breathing
                idle_target = home_state[i]
                if i in [1, 4]: # Breathe on Rotary and Up_Down
                    idle_target += math.sin(time.time() * 2) * 3 
                current_smoothed.append(smoothers[i].update(idle_target))
                cv2.putText(image, "PARKED & BREATHING", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 150, 0), 2)
            else:
                # Normal organic tracking
                current_smoothed.append(smoothers[i].update(target_angles[i]))
                
        # Send Serial Commands @ 30 FPS
        if time.time() - last_send_time > 0.03:
            b, r, e, w, u, c = [int(a) for a in current_smoothed]
            cmd = f"<{b},{r},{e},{w},{u},{c}>\n"
            ser.write(cmd.encode('utf-8'))
            last_send_time = time.time()
            if hand_detected and not arm_frozen:
                cv2.putText(image, f"TRACKING KINEMATICS", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('Robot Arm PRO Puppet', image)
        if cv2.waitKey(5) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass
finally:
    try:
        ser.write(b"<HOME>\n")
        time.sleep(1.5)
        ser.write(b"<RELAX>\n")
        ser.close()
    except: pass
    cap.release()
    cv2.destroyAllWindows()
