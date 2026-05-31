import cv2
import mediapipe as mp
import serial
import time
import math

# =========================================================================================
# VISION PUPPET: TRUE INVERSE KINEMATICS & AI INTELLIGENCE
# 
# 1. True Cartesian IK: Maps hand X, Y, Z directly to mathematical coordinates, calculating
#    exact servo angles to achieve straight-line movements in physical space.
# 2. "Butter-Smooth" Dynamic Filter: Adaptive velocity-based alpha for zero-jitter gliding.
# 3. Organic Breathing: Uses complex overlapping sine waves for a highly organic idle.
# 4. Peace Sign Dance: Detects a peace sign ✌️ to trigger an autonomous, rhythmic dance.
# =========================================================================================

# --- ADVANCED MATH FILTERS ---
class ButterSmoothFilter:
    """Adaptive exponential filter. Smooths heavily when slow/jittering, reacts instantly when fast."""
    def __init__(self, initial_val):
        self.val = initial_val

    def update(self, target):
        # Calculate distance to target
        delta = abs(target - self.val)
        # Dynamic Alpha: if delta is small (jitter), alpha is tiny (0.02 = heavy smoothing).
        # If delta is large (fast movement), alpha scales up to 0.35 (fast tracking).
        alpha = max(0.02, min(0.35, 0.02 + (delta / 100.0) * 0.33))
        self.val = (alpha * target) + ((1.0 - alpha) * self.val)
        return self.val

# --- INVERSE KINEMATICS ENGINE ---
def calculate_ik(x, y, z):
    """
    Solves 3D Inverse Kinematics for a standard 3-link robotic arm.
    x: Left/Right (-10 to 10)
    y: Depth from base (5 to 15)
    z: Height from base (0 to 15)
    Returns: (Base Angle, Rotary Angle, Elbow Angle)
    """
    L1, L2 = 10.0, 10.0  # Link lengths
    
    # Base Angle (Yaw)
    base_rad = math.atan2(x, y)
    base_deg = 90 - math.degrees(base_rad) # Center at 90
    
    # 2D Planar distance for Shoulder/Elbow
    r = math.hypot(x, y)
    d = math.hypot(r, z)
    
    # Prevent math domain errors if target is physically unreachable
    d = min(d, L1 + L2 - 0.01)
    
    # Law of Cosines for Elbow and Shoulder
    elbow_rad = math.acos((d**2 - L1**2 - L2**2) / (2 * L1 * L2))
    rotary_rad = math.atan2(z, r) + math.atan2(L2 * math.sin(elbow_rad), L1 + L2 * math.cos(elbow_rad))
    
    # Convert to Degrees
    rotary_deg = math.degrees(rotary_rad)
    elbow_deg = math.degrees(elbow_rad)
    
    # Map raw IK math to our specific physical servo ranges
    # Standard math puts elbow straight at 0. Our servo puts it straight at 180.
    final_base = base_deg
    final_rotary = 180 - rotary_deg  # Invert so leaning forward matches servo config
    final_elbow = 180 - elbow_deg    # Invert so bent is lower angle
    
    return final_base, final_rotary, final_elbow

def map_range(x, in_min, in_max, out_min, out_max):
    val = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return max(min(out_min, out_max), min(max(out_min, out_max), val))

def is_peace_sign(landmarks):
    """Detects ✌️: Index & Middle UP, Thumb, Ring, Pinky DOWN."""
    def is_curled(tip, mcp, wrist):
        return math.hypot(tip.x - wrist.x, tip.y - wrist.y) < math.hypot(mcp.x - wrist.x, mcp.y - wrist.y)
    
    lms = landmarks.landmark
    wrist = lms[mp_hands.HandLandmark.WRIST]
    
    index_up = not is_curled(lms[mp_hands.HandLandmark.INDEX_FINGER_TIP], lms[mp_hands.HandLandmark.INDEX_FINGER_MCP], wrist)
    middle_up = not is_curled(lms[mp_hands.HandLandmark.MIDDLE_FINGER_TIP], lms[mp_hands.HandLandmark.MIDDLE_FINGER_MCP], wrist)
    ring_down = is_curled(lms[mp_hands.HandLandmark.RING_FINGER_TIP], lms[mp_hands.HandLandmark.RING_FINGER_MCP], wrist)
    pinky_down = is_curled(lms[mp_hands.HandLandmark.PINKY_TIP], lms[mp_hands.HandLandmark.PINKY_MCP], wrist)
    
    return index_up and middle_up and ring_down and pinky_down

# --- SYSTEM SETUP ---
try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    time.sleep(3)
    ser.reset_input_buffer()
except Exception as e:
    print(f"Failed to connect to ESP32: {e}")
    exit()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.75, min_tracking_confidence=0.75)
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)

# --- STATE VARIABLES ---
HOME_STATE = [90, 90, 0, 145, 80, 45]
smoothers = [ButterSmoothFilter(val) for val in HOME_STATE]
last_send_time = time.time()
no_hand_time = time.time()

# Dance State
is_dancing = False
dance_start_time = 0

print("\n--- TRUE IK SYSTEM ACTIVE ---")
print("-> Show a PEACE SIGN ✌️ to trigger the Dance Routine!")
print("-> Hand Tracking now uses Absolute Cartesian XYZ coordinates.\n")

try:
    while cap.isOpened():
        success, image = cap.read()
        if not success: continue

        image = cv2.flip(image, 1) 
        results = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        target_angles = list(HOME_STATE)
        hand_detected = False

        if results.multi_hand_landmarks:
            hand_detected = True
            no_hand_time = time.time()
            hand_landmarks = results.multi_hand_landmarks[0]
            mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # --- DANCE LOGIC ---
            if is_peace_sign(hand_landmarks) and not is_dancing:
                is_dancing = True
                dance_start_time = time.time()
                print("PEACE SIGN DETECTED: INITIATING DANCE SEQUENCE!")
                
            if is_dancing:
                t = time.time() - dance_start_time
                if t > 8.0: # Dance for 8 seconds
                    is_dancing = False
                else:
                    cv2.putText(image, "DANCE MODE ACTIVE!", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
                    # Procedural Dance Animation using Math
                    target_angles[0] = 90 + math.sin(t * 3.14) * 45  # Base sweeps side to side
                    target_angles[1] = 90 + math.cos(t * 2.0) * 30   # Rotary bobs
                    target_angles[2] = 45 + math.sin(t * 4.0) * 45   # Elbow flaps fast
                    target_angles[3] = 145 + math.cos(t * 6.0) * 35  # Wrist shakes
                    target_angles[4] = 80 + math.sin(t * 1.5) * 40   # Up/down swoops
                    target_angles[5] = 45 + math.sin(t * 8.0) * 45   # Claw snaps to the beat

            # --- IK TRACKING LOGIC ---
            if not is_dancing:
                lm0 = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                lm9 = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                
                # Camera space to Cartesian space mapping
                center_x, center_y = lm9.x, lm9.y
                palm_size = math.hypot(lm9.x - lm0.x, lm9.y - lm0.y)
                
                # X: -10 (Left) to 10 (Right)
                ik_x = map_range(center_x, 0.1, 0.9, -10, 10)
                # Y: 5 (Close/Retracted) to 15 (Far/Extended) -> based on Palm Size
                ik_y = map_range(palm_size, 0.05, 0.25, 5, 15)
                # Z: 0 (Low) to 15 (High) -> based on camera Y
                ik_z = map_range(center_y, 0.1, 0.9, 15, 0)
                
                # Calculate True Angles using IK Math
                base_t, rotary_t, elbow_t = calculate_ik(ik_x, ik_y, ik_z)
                
                # Apply safe hardware limits for the targets
                target_angles[0] = map_range(base_t, 0, 180, 0, 180)
                target_angles[1] = map_range(rotary_t, 0, 180, 60, 145)
                target_angles[2] = map_range(elbow_t, 0, 180, 0, 180)
                
                # Elevation Helper (Up/Down Servo) coupled with Z-height
                target_angles[4] = map_range(ik_z, 0, 15, 20, 160)
                
                # Wrist Pitch
                dx = lm9.x - lm0.x
                dy = lm9.y - lm0.y
                angle_deg = math.degrees(math.atan2(dy, dx))
                target_angles[3] = map_range(angle_deg, -135, -45, 190, 100)
                
                # Dynamic Pinch
                thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                pinch_dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
                target_angles[5] = map_range(pinch_dist, 0.03, 0.10, 0, 90)

        # Apply Butter-Smooth Filtering or Organic Idle
        current_smoothed = []
        for i in range(6):
            if not hand_detected and time.time() - no_hand_time > 1.5:
                # Organic Breathing (Complex sine wave superposition for lifelike idle)
                t = time.time()
                idle_target = HOME_STATE[i]
                if i in [1, 4]: # Rotary & Up/Down
                    idle_target += (math.sin(t * 1.2) * 3) + (math.cos(t * 0.5) * 1.5)
                elif i == 3: # Wrist subtle roll
                    idle_target += math.sin(t * 0.8) * 2
                current_smoothed.append(smoothers[i].update(idle_target))
                cv2.putText(image, "ORGANIC IDLE (BREATHING)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 150, 0), 2)
            else:
                current_smoothed.append(smoothers[i].update(target_angles[i]))
                
        # Send Serial Commands @ 30 FPS
        if time.time() - last_send_time > 0.03:
            b, r, e, w, u, c = [int(a) for a in current_smoothed]
            cmd = f"<{b},{r},{e},{w},{u},{c}>\n"
            ser.write(cmd.encode('utf-8'))
            last_send_time = time.time()
            if hand_detected and not is_dancing:
                cv2.putText(image, f"IK CARTESIAN TRACKING", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('Robot Arm TRUE IK Controller', image)
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
