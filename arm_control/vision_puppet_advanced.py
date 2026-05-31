import cv2
import mediapipe as mp
import serial
import time
import math

# --- CONFIGURATION ---
SMOOTHING_FACTOR = 0.15  # 0.0 to 1.0. Lower = smoother/more lag
# ---------------------

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

last_send_time = time.time()

# Store the smoothed angles (initialized to the NEW Ideal Reset State)
# [90, 90, 0, 145, 80, 45]
smoothed_angles = [90, 90, 0, 145, 80, 45]

try:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            continue

        image = cv2.flip(image, 1)
        results = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Bounding box for X, Y, and Depth (Area)
                x_coords = [lm.x for lm in hand_landmarks.landmark]
                y_coords = [lm.y for lm in hand_landmarks.landmark]
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                
                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2
                area = (max_x - min_x) * (max_y - min_y)
                
                # Wrist Tilt
                lm0 = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                lm9 = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                dx = lm9.x - lm0.x
                dy = lm9.y - lm0.y
                angle_rad = math.atan2(dy, dx)
                wrist_angle_raw = math.degrees(angle_rad) + 180
                
                # Pinch distance for Claw
                thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                pinch_dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
                
                # ---- CALCULATE RAW TARGET ANGLES ----
                # Mirroring correction (180, 0) + High Sensitivity (0.35, 0.65)
                base_target = map_range(center_x, 0.35, 0.65, 180, 0)
                
                # High Sensitivity Y-axis mapping (0.35, 0.65)
                # FIXED: Inverted output (20, 140) so hand UP -> arm UP, hand DOWN -> arm DOWN
                up_down_target = map_range(center_y, 0.35, 0.65, 20, 140)
                
                # Depth (Area) -> ultra high sensitivity (0.04, 0.08)
                # FIXED: Inverted so hand close (large area) -> extend forward (60), hand far (small area) -> retract back (145)
                rotary_target = map_range(area, 0.04, 0.08, 145, 60)
                
                # FIXED: Elbow reaches further down/forward (up to 150) when extending
                elbow_target = map_range(area, 0.04, 0.08, 0, 150)
                
                # Wrist tilt mapped to have 145 degrees as upright neutral center
                wrist_target = map_range(wrist_angle_raw, 45, 135, 100, 190)
                
                # Claw pinch mapping (0 to 90)
                claw_target = map_range(pinch_dist, 0.04, 0.09, 0, 90)
                
                target_angles = [base_target, rotary_target, elbow_target, wrist_target, up_down_target, claw_target]
                
                # ---- APPLY LOW-PASS FILTER (SMOOTHING) ----
                for i in range(6):
                    smoothed_angles[i] = (SMOOTHING_FACTOR * target_angles[i]) + ((1.0 - SMOOTHING_FACTOR) * smoothed_angles[i])
                
                if time.time() - last_send_time > 0.03:
                    b, r, e, w, u, c = [int(a) for a in smoothed_angles]
                    cmd = f"<{b},{r},{e},{w},{u},{c}>\n"
                    ser.write(cmd.encode('utf-8'))
                    last_send_time = time.time()
                    
                    cv2.putText(image, f"Area: {area:.3f} Pinch: {pinch_dist:.3f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                    cv2.putText(image, f"CMD: {cmd.strip()}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        else:
            if time.time() - last_send_time > 1.0:
                ser.write(b"<HOME>\n")
                last_send_time = time.time()
                # Reset smoothed angles to home
                smoothed_angles = [90, 90, 0, 145, 80, 45]
                cv2.putText(image, "NO HAND - HOMING", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow('Final Robot Arm Puppet', image)
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
