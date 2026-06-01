# =========================================================================================
# EXTRA ADVANCED WORKSHOP: THE SKELETAL VIRTUAL MOUSE (virtual_mouse.py)
# 
# What we will do:
# 1. Use MediaPipe to track the Index Finger Knuckle (Landmark 5) as your mouse cursor.
# 2. Distance-Adaptive Sensitivity: Dynamically shrinks the active tracking box when you
#    are far from the camera, allowing tiny hand movements to sweep the entire screen.
# 3. Time-Based Tap vs Drag Engine (Hysteresis-driven):
#    - Pinching index + thumb triggers Left Click.
#    - Pinching middle + thumb triggers Right Click.
#    - 60% Activation Threshold: Fingers within 60% of palm size are considered pinched.
#    - Quick Tap: Release within 250ms triggers a standard OS click.
#    - Smooth Drag: Holding past 250ms triggers Drag Mode (mouseDown) which stays locked
#      until fingers open wide past 75% of palm size (prevents accidental drops).
# 4. Hand Tilt Protection: Disables click triggers if the hand is rotated sideways or upside
#    down to prevent false clicks during hand movement.
# =========================================================================================

import cv2
import mediapipe as mp
import pyautogui
import math
import time

# --- SAFETY FIRST ---
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.0

# Initialize MediaPipe Hand tracking
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.75, min_tracking_confidence=0.75)
mp_draw = mp.solutions.drawing_utils

# Get monitor resolution
screen_width, screen_height = pyautogui.size()

cap = cv2.VideoCapture(0)

# State variables for mouse cursor smoothing
smooth_x, smooth_y = 0.0, 0.0
SMOOTHING_FACTOR = 0.22 

# Time-Based Gesture Engine variables
left_pinch_start = 0.0
right_pinch_start = 0.0
left_is_holding = False
right_is_holding = False

print("========================================")
print("     SKELETAL VIRTUAL MOUSE RUNNING     ")
print("========================================")
print(f"Monitor Resolution: {screen_width}x{screen_height}")
print("-> Cursor: Point with your Index Finger.")
print("-> Quick Left Click: Pinch Index + Thumb quickly.")
print("-> Left Drag & Hold: Pinch and hold Index + Thumb.")
print("-> Quick Right Click: Pinch Middle + Thumb quickly.")
print("-> Right Drag & Hold: Pinch and hold Middle + Thumb.")
print("-> FAILSAFE: Slam physical mouse to Top-Left corner of screen to abort.")
print("-> Press 'q' in the camera window to quit.")
print("========================================\n")

while cap.isOpened():
    success, image = cap.read()
    if not success:
        continue

    # Mirror the image horizontally
    image = cv2.flip(image, 1)
    height, width, _ = image.shape
    
    # Process with MediaPipe
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_image)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Get key skeletal landmarks
            lm0 = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
            lm9 = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            index_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
            
            thumb_px = (int(thumb_tip.x * width), int(thumb_tip.y * height))
            index_px = (int(index_tip.x * width), int(index_tip.y * height))
            middle_px = (int(middle_tip.x * width), int(middle_tip.y * height))
            
            # --- 1. SKELETAL PALM SIZE (DISTANCE-ADAPTIVE SENSITIVITY) ---
            palm_size = math.hypot(lm9.x - lm0.x, lm9.y - lm0.y) * width
            
            def map_range(x, in_min, in_max, out_min, out_max):
                val = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
                return max(min(out_min, out_max), min(max(out_min, out_max), val))
                
            box_width = map_range(palm_size, 40, 180, 0.12, 0.35)
            xmin, xmax = 0.5 - box_width / 2, 0.5 + box_width / 2
            ymin, ymax = 0.5 - box_width / 2, 0.5 + box_width / 2
            
            # Draw the active tracking boundaries on the webcam window dynamically
            cv2.rectangle(image, (int(width * xmin), int(height * ymin)), 
                          (int(width * xmax), int(height * ymax)), (255, 0, 0), 2)
            
            # --- 2. CURSOR MOVEMENT (Index MCP / knuckle for stability) ---
            active_x = (index_mcp.x - xmin) / box_width
            active_y = (index_mcp.y - ymin) / box_width
            
            # Clamp between 0.0 and 1.0
            active_x = max(0.0, min(1.0, active_x))
            active_y = max(0.0, min(1.0, active_y))
            
            target_x = active_x * screen_width
            target_y = active_y * screen_height
            
            # Smooth with exponential moving average
            smooth_x = (SMOOTHING_FACTOR * target_x) + ((1.0 - SMOOTHING_FACTOR) * smooth_x)
            smooth_y = (SMOOTHING_FACTOR * target_y) + ((1.0 - SMOOTHING_FACTOR) * smooth_y)
            
            try:
                pyautogui.moveTo(int(smooth_x), int(smooth_y))
            except pyautogui.FailSafeException:
                print("Failsafe triggered!")
                cap.release()
                cv2.destroyAllWindows()
                exit()
            
            # --- 3. HAND TILT PROTECTION ---
            # Calculate hand angle. Straight up is approx -90 degrees.
            dx = lm9.x - lm0.x
            dy = lm9.y - lm0.y
            hand_angle = math.degrees(math.atan2(dy, dx))
            is_hand_upright = (-140 <= hand_angle <= -40)
            
            # --- 4. TIME-BASED TAP & DRAG ENGINE WITH HYSTERESIS ---
            # Calculate raw pixel distances
            left_pixel_dist = math.hypot(thumb_px[0] - index_px[0], thumb_px[1] - index_px[1])
            right_pixel_dist = math.hypot(thumb_px[0] - middle_px[0], thumb_px[1] - middle_px[1])
            
            # Normalize by current Palm Size (100% distance-independent!)
            left_norm = left_pixel_dist / palm_size
            right_norm = right_pixel_dist / palm_size
            
            # Hysteresis Thresholds:
            # - Activates at 0.60 (intentional pinch close - generous limit!)
            # - Releases only when fingers open past 0.75 (safety release cushion)
            PINCH_ACTIVATE = 0.60
            PINCH_RELEASE = 0.75
            
            if is_hand_upright:
                # A. LEFT CLICK & DRAG (Index + Thumb)
                # Lock out if right click is currently active/pinch is starting
                if not right_is_holding and right_pinch_start == 0.0:
                    if left_norm < PINCH_ACTIVATE:
                        if left_pinch_start == 0.0:
                            left_pinch_start = time.time()
                        else:
                            # Hold detected: if pinched for more than 250ms, start standard Drag (mouseDown)
                            if not left_is_holding and (time.time() - left_pinch_start > 0.25):
                                pyautogui.mouseDown(button='left')
                                left_is_holding = True
                                print("[LEFT] Dragging started...")
                    elif left_norm > PINCH_RELEASE:
                        if left_pinch_start != 0.0:
                            duration = time.time() - left_pinch_start
                            if left_is_holding:
                                # Release active drag
                                pyautogui.mouseUp(button='left')
                                left_is_holding = False
                                print("[LEFT] Dragging released")
                            else:
                                # Quick tap: released before 250ms, register as single Click!
                                pyautogui.click(button='left')
                                print(f"[LEFT] Click registered (Duration: {duration:.2f}s)")
                            left_pinch_start = 0.0
                            
                # B. RIGHT CLICK & DRAG (Middle + Thumb)
                # Lock out if left click is currently active/pinch is starting
                if not left_is_holding and left_pinch_start == 0.0:
                    if right_norm < PINCH_ACTIVATE:
                        if right_pinch_start == 0.0:
                            right_pinch_start = time.time()
                        else:
                            # Hold detected: if pinched for more than 250ms, start Right Drag (mouseDown)
                            if not right_is_holding and (time.time() - right_pinch_start > 0.25):
                                pyautogui.mouseDown(button='right')
                                right_is_holding = True
                                print("[RIGHT] Dragging started...")
                    elif right_norm > PINCH_RELEASE:
                        if right_pinch_start != 0.0:
                            duration = time.time() - right_pinch_start
                            if right_is_holding:
                                # Release active drag
                                pyautogui.mouseUp(button='right')
                                right_is_holding = False
                                print("[RIGHT] Dragging released")
                            else:
                                # Quick tap: released before 250ms, register as single Right Click!
                                pyautogui.click(button='right')
                                print(f"[RIGHT] Click registered (Duration: {duration:.2f}s)")
                            right_pinch_start = 0.0
            else:
                # Hand is tilted sideways. Force release any active clicks for safety.
                if left_is_holding:
                    pyautogui.mouseUp(button='left')
                    left_is_holding = False
                if right_is_holding:
                    pyautogui.mouseUp(button='right')
                    right_is_holding = False
                left_pinch_start = 0.0
                right_pinch_start = 0.0

            # Draw visual feedback lines
            if left_pinch_start != 0.0:
                color = (0, 255, 0) if left_is_holding else (0, 255, 255)
                cv2.line(image, thumb_px, index_px, color, 4)
            if right_pinch_start != 0.0:
                color = (0, 0, 255) if right_is_holding else (255, 0, 255)
                cv2.line(image, thumb_px, middle_px, color, 4)

    # UI Overlays
    cv2.putText(image, "ADAPTIVE SKELETAL MOUSE", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
    status_text = "DRAGGING" if (left_is_holding or right_is_holding) else "TRACKING"
    status_color = (0, 255, 255) if (left_is_holding or right_is_holding) else (255, 255, 255)
    cv2.putText(image, f"STATE: {status_text}", (20, 80), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

    cv2.imshow('Day 1 - Virtual Mouse Controller', image)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup on exit
if left_is_holding: pyautogui.mouseUp(button='left')
if right_is_holding: pyautogui.mouseUp(button='right')
cap.release()
cv2.destroyAllWindows()
print("Skeletal Mouse cleanly stopped.")
