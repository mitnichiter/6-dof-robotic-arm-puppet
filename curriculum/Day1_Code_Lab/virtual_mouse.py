# =========================================================================================
# EXTRA ADVANCED WORKSHOP: THE SKELETAL VIRTUAL MOUSE (virtual_mouse.py)
# 
# What we will do:
# 1. Use MediaPipe to track the Index Finger Tip (Landmark 8) as your mouse cursor.
# 2. Map your webcam window coordinates to your actual monitor resolution.
# 3. Left Click & Drag: Touch Thumb Tip (4) and Index Tip (8) together.
# 4. Right Click & Drag: Touch Thumb Tip (4) and Middle Tip (12) together.
# 5. Easing/Smoothing: Applies a smooth filter to make sure the mouse doesn't shake.
# =========================================================================================

import cv2
import mediapipe as mp
import pyautogui
import math
import time

# --- SAFETY FIRST ---
# PyAutoGUI has a built-in Failsafe: if you quickly slam your physical mouse cursor into the 
# extreme top-left corner of the screen, the script will instantly terminate. Keep this on!
pyautogui.FAILSAFE = True
# Turn off default click delay for maximum responsiveness
pyautogui.PAUSE = 0.0

# Initialize MediaPipe Hand tracking
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.75, min_tracking_confidence=0.75)
mp_draw = mp.solutions.drawing_utils

# Get your monitor's actual width and height in pixels
screen_width, screen_height = pyautogui.size()

# Open the webcam
cap = cv2.VideoCapture(0)

# State variables for holding clicks (enables smooth dragging!)
left_button_down = False
right_button_down = False

# Mouse smoothing variables (exponential moving average)
smooth_x, smooth_y = 0.0, 0.0
SMOOTHING_FACTOR = 0.25 # Lower = smoother/slower, Higher = faster/more raw

print("========================================")
print("     SKELETAL VIRTUAL MOUSE RUNNING     ")
print("========================================")
print(f"Monitor Resolution: {screen_width}x{screen_height}")
print("-> Cursor: Point with your Index Finger.")
print("-> Left Click & Drag: Pinch Index + Thumb ✊")
print("-> Right Click & Drag: Pinch Middle + Thumb ✌️")
print("-> FAILSAFE: Slam physical mouse to Top-Left corner of screen to abort.")
print("-> Press 'q' in the camera window to quit.")
print("========================================\n")

while cap.isOpened():
    success, image = cap.read()
    if not success:
        continue

    # Mirror the image horizontally for natural mouse pointing
    image = cv2.flip(image, 1)
    height, width, _ = image.shape
    
    # Process with MediaPipe
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_image)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # 1. GET KEY LANDMARKS
            wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            index_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
            
            # Convert ratio coordinates to pixel values
            thumb_px = (int(thumb_tip.x * width), int(thumb_tip.y * height))
            index_px = (int(index_tip.x * width), int(index_tip.y * height))
            middle_px = (int(middle_tip.x * width), int(middle_tip.y * height))
            index_mcp_px = (int(index_mcp.x * width), int(index_mcp.y * height))
            
            # --- 2. CURSOR MOVEMENT (Using Index MCP / knuckle for extra stability) ---
            # To avoid extending your arm across the entire webcam frame, we map a tight 
            # central box (X: 30% to 70%, Y: 30% to 70%) to your entire high-resolution monitor.
            # This allows comfortable hand movements in the center of the camera.
            active_x = (index_mcp.x - 0.3) / 0.4 # Map 0.3-0.7 range to 0.0-1.0
            active_y = (index_mcp.y - 0.3) / 0.4
            
            # Clamp between 0.0 and 1.0 so we don't go out of bounds
            active_x = max(0.0, min(1.0, active_x))
            active_y = max(0.0, min(1.0, active_y))
            
            # Draw the active tracking boundaries on the webcam window so students see the box
            cv2.rectangle(image, (int(width * 0.3), int(height * 0.3)), 
                          (int(width * 0.7), int(height * 0.7)), (255, 0, 0), 2)
            
            # Calculate target monitor pixels
            target_x = active_x * screen_width
            target_y = active_y * screen_height
            
            # Apply Exponential Smoothing to prevent cursor jitter/trembling
            smooth_x = (SMOOTHING_FACTOR * target_x) + ((1.0 - SMOOTHING_FACTOR) * smooth_x)
            smooth_y = (SMOOTHING_FACTOR * target_y) + ((1.0 - SMOOTHING_FACTOR) * smooth_y)
            
            # Move the actual PC cursor
            try:
                pyautogui.moveTo(int(smooth_x), int(smooth_y))
            except pyautogui.FailSafeException:
                print("Aborting: Failsafe triggered!")
                cap.release()
                cv2.destroyAllWindows()
                exit()
            
            # --- 3. GESTURE CLICK ENGINE ---
            # Calculate distance between tips
            left_pinch_dist = math.hypot(thumb_px[0] - index_px[0], thumb_px[1] - index_px[1])
            right_pinch_dist = math.hypot(thumb_px[0] - middle_px[0], thumb_px[1] - middle_px[1])
            
            # A. Left Click / Drag (Thumb + Index pinch)
            if left_pinch_dist < 25: # Very close = Pinching!
                cv2.line(image, thumb_px, index_px, (0, 255, 0), 4) # Draw green feedback line
                if not left_button_down:
                    pyautogui.mouseDown(button='left')
                    left_button_down = True
                    print("Left Click & Drag started")
            else: # Fingers separated = Released!
                if left_button_down:
                    pyautogui.mouseUp(button='left')
                    left_button_down = False
                    print("Left Button Released")
                    
            # B. Right Click / Drag (Thumb + Middle pinch)
            if right_pinch_dist < 25:
                cv2.line(image, thumb_px, middle_px, (0, 0, 255), 4) # Draw red feedback line
                if not right_button_down:
                    pyautogui.mouseDown(button='right')
                    right_button_down = True
                    print("Right Click & Drag started")
            else:
                if right_button_down:
                    pyautogui.mouseUp(button='right')
                    right_button_down = False
                    print("Right Button Released")

    # Status Overlay
    cv2.putText(image, "VIRTUAL SKELETAL MOUSE", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
    status_text = "DRAGGING" if (left_button_down or right_button_down) else "TRACKING"
    status_color = (0, 255, 255) if (left_button_down or right_button_down) else (255, 255, 255)
    cv2.putText(image, f"STATE: {status_text}", (20, 80), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

    cv2.imshow('Day 1 - Virtual Mouse Controller', image)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
if left_button_down: pyautogui.mouseUp(button='left')
if right_button_down: pyautogui.mouseUp(button='right')
cap.release()
cv2.destroyAllWindows()
print("Virtual Mouse safely stopped.")
