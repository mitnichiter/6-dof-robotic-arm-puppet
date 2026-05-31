import cv2
import mediapipe as mp
import serial
import time
import math

# Connect to ESP32
try:
    print("Connecting to ESP32 on COM5...")
    # Opening the serial port will toggle DTR/RTS and reset the ESP32
    ser = serial.Serial('COM5', 115200, timeout=1)
    
    # Wait for the ESP32 to boot up and run main.py (which sends it to Home state)
    print("Waiting for ESP32 to boot and run main.py...")
    time.sleep(3)
    
    # Clear any startup text from the buffer
    ser.reset_input_buffer()
    print("Ready to send commands.")
except Exception as e:
    print(f"Failed to connect to ESP32: {e}")
    exit()

# Initialize MediaPipe Hand Tracking
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1, # Track one hand for the arm
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Open Webcam
cap = cv2.VideoCapture(0)

# Helper function to map values from one range to another (like Arduino's map())
def map_range(x, in_min, in_max, out_min, out_max):
    val = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    # Constrain the value to the output range
    return max(min(out_min, out_max), min(max(out_min, out_max), val))

print("\n--- INSTRUCTIONS ---")
print("1. Stand in front of the camera and raise your hand.")
print("2. Move hand Left/Right -> Base moves.")
print("3. Move hand Up/Down -> Arm lifts/lowers.")
print("4. Move hand Close/Far -> Arm extends/retracts.")
print("5. Pinch thumb and index finger -> Claw closes.")
print("6. Drop hand out of frame -> Arm returns to Home.")
print("7. Press 'q' in the video window to quit.")
print("--------------------\n")

last_send_time = time.time()

try:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            continue

        # Flip the image horizontally so it acts like a mirror
        image = cv2.flip(image, 1)
        
        # Process the image to find hands
        results = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw the skeleton on the screen
                mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Get bounding box limits (to find center and area)
                x_coords = [lm.x for lm in hand_landmarks.landmark]
                y_coords = [lm.y for lm in hand_landmarks.landmark]
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                
                # Center of the hand
                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2
                
                # Area of bounding box (proxy for depth/Z-axis)
                area = (max_x - min_x) * (max_y - min_y)
                
                # Pinch distance (Thumb tip vs Index tip)
                thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                pinch_dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
                
                # ---- CALCULATE ANGLES ----
                # Base: X-axis (0.2 left to 0.8 right) maps to (0 to 180 degrees)
                base_angle = int(map_range(center_x, 0.2, 0.8, 0, 180))
                
                # Up/Down: Y-axis (0.2 top to 0.8 bottom) maps to (120 to 20 degrees)
                up_down_angle = int(map_range(center_y, 0.2, 0.8, 120, 20))
                
                # Extend/Retract: Area (0.02 far to 0.15 close) maps to Rotary & Elbow
                # Far = Folded (Rotary 180, Elbow 180). Close = Extended (Rotary 60, Elbow 90)
                rotary_angle = int(map_range(area, 0.02, 0.15, 180, 60))
                elbow_angle = int(map_range(area, 0.02, 0.15, 180, 90))
                
                # Claw: Pinch Distance (< 0.05 closed, > 0.10 open)
                claw_angle = int(map_range(pinch_dist, 0.05, 0.10, 60, 160))
                
                # Wrist: Locked at 90 for stability
                wrist_angle = 90
                
                # Send command over Serial at ~30 FPS
                if time.time() - last_send_time > 0.03:
                    cmd = f"<{base_angle},{rotary_angle},{elbow_angle},{wrist_angle},{up_down_angle},{claw_angle}>\n"
                    ser.write(cmd.encode('utf-8'))
                    last_send_time = time.time()
                    
                    # Display debug text on video
                    cv2.putText(image, f"Area: {area:.3f} Pinch: {pinch_dist:.3f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(image, f"CMD: {cmd.strip()}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        else:
            # No hand detected! Send Home command occasionally
            if time.time() - last_send_time > 1.0:
                ser.write(b"<HOME>\n")
                last_send_time = time.time()
                cv2.putText(image, "NO HAND - HOMING", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Show the video feed
        cv2.imshow('Robot Arm Vision Puppet', image)
        
        # Press 'q' to quit
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
