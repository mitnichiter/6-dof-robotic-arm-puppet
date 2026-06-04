# =========================================================================================
# EXTRA CHALLENGE: THE HOLOGRAPHIC AIR CANVAS (air_canvas.py)
# 
# What we will do:
# 1. Use MediaPipe to track your Index and Middle fingers.
# 2. Point with ONLY your index finger to draw glowing neon lines in thin air!
# 3. Raise your middle finger (Peace Sign ✌️) to stop drawing and move your hand around.
# 4. Press 'c' to clear the screen!
# =========================================================================================

import cv2
import mediapipe as mp
import numpy as np

# Step 1: Initialize MediaPipe Hand tracking
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.75, min_tracking_confidence=0.75)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

# Create a blank digital canvas that we will draw our lines onto
canvas = None

# Variables to remember where our finger was in the last frame so we can draw a continuous line
prev_x, prev_y = 0, 0

print("========================================")
print("       HOLOGRAPHIC AIR CANVAS LIVE      ")
print("========================================")
print("-> DRAW: Point with your Index Finger ☝️")
print("-> PAUSE/MOVE: Show a Peace Sign ✌️")
print("-> CLEAR: Press 'c' on your keyboard.")
print("-> QUIT: Press 'q' on your keyboard.")
print("========================================\n")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        continue

    # Mirror the image horizontally so it feels natural
    frame = cv2.flip(frame, 1)
    
    # If this is the first frame, create a black canvas of the exact same size
    if canvas is None:
        canvas = np.zeros_like(frame)
        
    height, width, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Optionally draw the skeleton (you can comment this out to just see the drawing!)
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Get the coordinates of the Index and Middle finger tips
            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            middle_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
            
            # Convert ratio coordinates to exact pixel locations
            ix, iy = int(index_tip.x * width), int(index_tip.y * height)
            
            # --- GESTURE LOGIC ---
            # Is the middle finger up? (If tip is physically higher than its knuckle)
            # Note: Y-coordinates go DOWN the screen, so a smaller Y means "higher up"
            middle_is_up = middle_tip.y < middle_mcp.y
            
            if middle_is_up:
                # ✌️ PEACE SIGN MODE: Hovering (Don't Draw)
                prev_x, prev_y = 0, 0 # Break the continuous line
                
                # Draw a hollow "hover" cursor on the screen
                cv2.circle(frame, (ix, iy), 15, (255, 0, 255), 2)
                cv2.putText(frame, "HOVERING", (ix - 30, iy - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
            else:
                # ☝️ INDEX FINGER ONLY: Drawing Mode
                # Draw a solid "drawing" cursor
                cv2.circle(frame, (ix, iy), 15, (255, 0, 255), cv2.FILLED)
                
                if prev_x == 0 and prev_y == 0:
                    prev_x, prev_y = ix, iy # Start of a new line
                    
                # Draw a thick line on our virtual canvas
                cv2.line(canvas, (prev_x, prev_y), (ix, iy), (255, 0, 255), 10)
                
                # Update the previous coordinates for the next frame
                prev_x, prev_y = ix, iy

    # Merge our virtual canvas with the live webcam frame!
    # This makes the glowing neon lines appear floating in the air over the video
    frame = cv2.addWeighted(frame, 1, canvas, 0.5, 0)
    
    cv2.putText(frame, "HOLOGRAPHIC AIR CANVAS", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    cv2.imshow('Day 1 - Air Canvas Challenge', frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('c'):
        canvas = np.zeros_like(frame) # Clear canvas
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Air Canvas closed successfully.")