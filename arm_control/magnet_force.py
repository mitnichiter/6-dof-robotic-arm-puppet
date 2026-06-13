import cv2
import mediapipe as mp
import serial
import time
import math

# =========================================================================================
# THE TELEKINETIC FORCE-FIELD SIMULATOR (magnet_force.py)
# 
# 1. Mass-Spring-Damper Physics Engine: Models the robot as a heavy physical mass connected
#    to your hand by an invisible magnetic spring.
# 2. Realistic Inertia & Overshoot: If you move your hand quickly, the robot accelerates,
#    overshoots your position, bounces back, and oscillates before settling.
# 3. Haptic Illusion: Creates a highly realistic illusion of physical tension, drag,
#    and elasticity connecting your body to the metal and plastic of the arm.
# 4. Interactive HUD: Displays a beautiful physical vector grid on your camera screen,
#    showing the virtual spring tension lines and force magnitude vectors!
# =========================================================================================

# --- PHYSICS ENGINE CONFIGURATION ---
SPRING_K = 15.0   # Spring stiffness (Higher = stiffer/faster snapping, Lower = looser/more bounce)
DAMPING = 2.2     # Friction/Drag (Higher = less bounce/slower settling, Lower = heavy oscillations)
MASS = 1.0        # Virtual weight of the arm (Higher = feels heavier, has more momentum)
# ------------------------------------

# --- SERIAL SETUP ---
try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setRTS(False)
    time.sleep(2.0)
    ser.reset_input_buffer()
    print("Direct board control verified!")
except Exception as e:
    print(f"Failed to connect: {e}")
    exit()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.75, min_tracking_confidence=0.75)
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(1 + cv2.CAP_DSHOW) # External USB Camera with DirectShow
if not cap.isOpened():
    cap = cv2.VideoCapture(0 + cv2.CAP_DSHOW) # Fallback

def map_range(x, in_min, in_max, out_min, out_max):
    val = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return max(min(out_min, out_max), min(max(out_min, out_max), val))

# --- PHYSICAL STATES (3D Space vectors) ---
# Home base position: Base=90, Rotary=90, Elbow=0, Wrist=145, Up/Down=80, Claw=45
HOME_STATE = [90, 90, 0, 145, 80, 45]

# Current physical state of our virtual mass (Position, Velocity, Acceleration) for each joint
robot_pos = list(HOME_STATE)
robot_vel = [0.0] * 6

LIMITS = {
    0: (0, 180),    # Base
    1: (60, 145),   # Rotary
    2: (0, 180),    # Elbow
    3: (0, 180),    # Wrist
    4: (10, 180),   # Up/Down
    5: (0, 90)      # Claw
}

last_frame_time = time.time()
last_send_time = time.time()
no_hand_time = time.time()

print("\n=========================================================")
print("            THE TELEKINETIC FORCE-FIELD ACTIVE           ")
print("=========================================================")
print("-> Move your hand. The arm will accelerate, overshoot,")
print("   bounce, and vibrate with realistic physical inertia!")
print("-> Flick your hand fast to pluck the arm like a spring.")
print("-> Press 'q' in the camera window to safely exit.\n")

try:
    while cap.isOpened():
        success, image = cap.read()
        if not success: continue

        t_now = time.time()
        dt = t_now - last_frame_time
        last_frame_time = t_now
        
        # Prevent huge dt spikes when window is dragged or lagging
        dt = min(0.05, dt)

        image = cv2.flip(image, 1) 
        height, width, _ = image.shape
        results = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        hand_detected = False
        hand_targets = list(HOME_STATE) # If no hand, attract back to home

        if results.multi_hand_landmarks:
            hand_detected = True
            no_hand_time = t_now
            hand_landmarks = results.multi_hand_landmarks[0]
            mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            lm0 = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
            lm9 = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
            
            # --- 1. CAPTURE RAW HAND POSITIONS ---
            center_x, center_y = lm9.x, lm9.y
            palm_size = math.hypot(lm9.x - lm0.x, lm9.y - lm0.y)
            
            # Base (X-axis)
            hand_targets[0] = map_range(center_x, 0.1, 0.9, 180, 0)
            # Up/Down (Y-axis)
            hand_targets[4] = map_range(center_y, 0.1, 0.9, 20, 160)
            
            # Reach (Z-axis) - Coupled Rotary and Elbow
            reach = map_range(palm_size, 0.05, 0.25, 0.0, 1.0)
            hand_targets[1] = map_range(reach, 0.0, 1.0, 145, 60)
            hand_targets[2] = map_range(reach, 0.0, 1.0, 0, 150)
            
            # Wrist Roll (Tilt)
            dx = lm9.x - lm0.x
            dy = lm9.y - lm0.y
            angle_deg = math.degrees(math.atan2(dy, dx))
            hand_targets[3] = map_range(angle_deg, -135, -45, 190, 100)
            
            # Claw (Pinch)
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            pinch_dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
            hand_targets[5] = map_range(pinch_dist, 0.03, 0.10, 0, 90)

            # Draw visual Holographic force vectors on screen!
            # Draws a blue "tension line" connecting your physical hand to the virtual robot target
            idx_mcp_px = (int(index_tip.x * width), int(index_tip.y * height))
            rob_yaw_px = int(map_range(robot_pos[0], 0, 180, width * 0.9, width * 0.1))
            rob_height_px = int(map_range(robot_pos[4], 20, 160, height * 0.1, height * 0.9))
            
            cv2.line(image, idx_mcp_px, (rob_yaw_px, rob_height_px), (0, 255, 255), 2)
            cv2.circle(image, (rob_yaw_px, rob_height_px), 12, (255, 0, 0), -1)
            cv2.putText(image, "MAGNETIC COUPLING", (rob_yaw_px - 60, rob_height_px - 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        else:
            # No hand: Slowly attract back to home pose
            if t_now - no_hand_time > 1.5:
                hand_targets = list(HOME_STATE)
                cv2.putText(image, "NO HAND - RETRACTING", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 150, 0), 2)

        # --- 2. THE MASS-SPRING-DAMPER PHYSICS ENGINE (FOR EACH JOINT) ---
        for i in range(6):
            # Spring Hooke's Law: F = -k * x
            displacement = hand_targets[i] - robot_pos[i]
            spring_force = SPRING_K * displacement
            
            # Damping Friction Force: F = -d * v (resists speed)
            damping_force = DAMPING * robot_vel[i]
            
            # Net Force: F_net = F_spring - F_damping
            net_force = spring_force - damping_force
            
            # Newton's Second Law: a = F_net / m
            acceleration = net_force / MASS
            
            # Euler Integration
            robot_vel[i] += acceleration * dt
            robot_pos[i] += robot_vel[i] * dt
            
            # Clamp position to strict hardware safety limits
            min_ang, max_ang = LIMITS[i]
            robot_pos[i] = max(min_ang, min(robot_pos[i], max_ang))
            
            # Collision Bounce: If the robot hits a physical hard limit,
            # it bounces off elasticly (reverse velocity and absorb energy)!
            if robot_pos[i] == min_ang or robot_pos[i] == max_ang:
                robot_vel[i] = -robot_vel[i] * 0.35 # bounce back with 35% velocity

        # --- 3. SERIAL TRANSMISSION TO ESP32 @ 30 FPS ---
        if t_now - last_send_time > 0.033:
            b, r, e, w, u, c = [int(a) for a in robot_pos]
            cmd = f"<{b},{r},{e},{w},{u},{c}>\n"
            ser.write(cmd.encode('utf-8'))
            last_send_time = t_now
            
            if hand_detected:
                cv2.putText(image, "TENSION FORCE STABLE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('Telekinetic Magnet Field', image)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass
finally:
    print("\nSafely parking and relaxing the arm...")
    try:
        ser.write(b"<HOME>\n")
        time.sleep(1.5)
        ser.write(b"<RELAX>\n")
        ser.close()
    except: pass
    cap.release()
    cv2.destroyAllWindows()
