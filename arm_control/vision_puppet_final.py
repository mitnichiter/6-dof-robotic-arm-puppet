import cv2
import mediapipe as mp
import serial
import time
import math

# =========================================================================================
# THE ULTIMATE ROBOT ARM VISION CONTROLLER
# Optimizations applied:
# 1. Full Frame Resolution: Interaction bounds expanded to 10% to 90% of the screen.
# 2. Stable Depth (Z-Axis): Uses skeletal Palm Size instead of volatile Bounding Box Area.
# 3. Dynamic Smoothing: Adapts instantly to fast movements, but freezes micro-jitters.
# 4. Corrected Reach Kinematics: Hand close to camera = leans forward & points down at table.
# =========================================================================================

# --- ADVANCED CONFIGURATION ---
MIN_SMOOTH = 0.05  # Heavy smoothing for micro-movements (eliminates twerking)
MAX_SMOOTH = 0.40  # Fast response for large, sweeping arm movements
# ------------------------------

try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    print("Waiting 3s for ESP32 to boot and run main.py...")
    time.sleep(3)
    ser.reset_input_buffer()
    print("Ready to send commands.")
except Exception as e:
    print(f"Failed to connect to ESP32: {e}")
    exit()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

def map_range(x, in_min, in_max, out_min, out_max):
    val = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return max(min(out_min, out_max), min(max(out_min, out_max), val))

# Initialize to the safe reset state: [90, 90, 0, 145, 80, 45]
smoothed_angles = [90, 90, 0, 145, 80, 45]
last_send_time = time.time()

print("\n--- SYSTEM ACTIVE ---")
print("Press 'q' in the video window to safely park the arm and quit.\n")

try:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            continue

        # Mirror the image so moving your physical right hand moves the arm right
        image = cv2.flip(image, 1)
        results = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # We use specific skeletal landmarks instead of a bounding box for absolute stability
                lm0 = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                lm9 = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                
                # 1. BASE (X-Axis) & UP/DOWN (Y-Axis)
                # Using Landmark 9 (middle knuckle) as the core anchor point
                center_x, center_y = lm9.x, lm9.y
                
                # FULL FRAME MAPPING: 0.1 to 0.9 (Uses 80% of your camera instead of 30%)
                base_target = map_range(center_x, 0.1, 0.9, 180, 0)
                
                # Y-Axis Mapping: Hand High (y=0.1) -> Arm Up (160), Hand Low (y=0.9) -> Arm Down (20)
                up_down_target = map_range(center_y, 0.1, 0.9, 160, 20) 
                
                # 2. DEPTH / REACH (Z-Axis)
                # Optimization: Palm Size (Distance from Wrist to Knuckle) never changes when you 
                # open/close your fingers. This stops the arm from glitching forward/backward when pinching!
                palm_size = math.hypot(lm9.x - lm0.x, lm9.y - lm0.y)
                
                # Hand Close (Large Palm ~ 0.25) -> Arm reaches FORWARD (Rotary 60) and elbows DOWN at table (150)
                # Hand Far (Small Palm ~ 0.05) -> Arm folds BACKWARD (Rotary 145) and elbows UP (0)
                rotary_target = map_range(palm_size, 0.05, 0.25, 145, 60)
                elbow_target = map_range(palm_size, 0.05, 0.25, 0, 150)
                
                # 3. WRIST ROLL (Tilt)
                dx = lm9.x - lm0.x
                dy = lm9.y - lm0.y
                angle_deg = math.degrees(math.atan2(dy, dx))
                # Straight up is approx -90 degrees. Offset it so -90 maps to 145 (Neutral Reset State)
                wrist_target = map_range(angle_deg, -135, -45, 190, 100)
                
                # 4. CLAW (Pinch)
                thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                pinch_dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
                claw_target = map_range(pinch_dist, 0.03, 0.10, 0, 90)
                
                target_angles = [base_target, rotary_target, elbow_target, wrist_target, up_down_target, claw_target]
                
                # 5. DYNAMIC SMOOTHING (The Anti-Twerking Algorithm)
                for i in range(6):
                    # Calculate how far the target is from the current position
                    diff = abs(target_angles[i] - smoothed_angles[i])
                    # If moving a lot (>30 deg), react fast (0.4). If holding still (<5 deg), smooth heavily (0.05)
                    alpha = map_range(diff, 5, 30, MIN_SMOOTH, MAX_SMOOTH)
                    
                    smoothed_angles[i] = (alpha * target_angles[i]) + ((1.0 - alpha) * smoothed_angles[i])
                
                # 6. SERIAL TRANSMISSION
                if time.time() - last_send_time > 0.03: # 30 FPS Cap
                    b, r, e, w, u, c = [int(a) for a in smoothed_angles]
                    cmd = f"<{b},{r},{e},{w},{u},{c}>\n"
                    ser.write(cmd.encode('utf-8'))
                    last_send_time = time.time()
                    
                    cv2.putText(image, f"Palm Depth: {palm_size:.3f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(image, f"CMD: {cmd.strip()}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        else:
            if time.time() - last_send_time > 1.0:
                ser.write(b"<HOME>\n")
                last_send_time = time.time()
                # Reset smoothed angles to home
                smoothed_angles = [90, 90, 0, 145, 80, 45]
                cv2.putText(image, "NO HAND - SAFELY PARKED", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow('Ultimate Robot Arm Control', image)
        if cv2.waitKey(5) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass
finally:
    print("Cleaning up and securing the arm...")
    try:
        ser.write(b"<HOME>\n")
        time.sleep(1)
        ser.write(b"<RELAX>\n")
        ser.close()
    except:
        pass
    cap.release()
    cv2.destroyAllWindows()
