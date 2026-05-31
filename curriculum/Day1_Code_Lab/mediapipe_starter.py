# =========================================================================================
# LESSON 2: SKELETAL TRACKING & THE VIRTUAL SLIDER (mediapipe_starter.py)
# 
# What we will do:
# 1. Capture webcam video using OpenCV.
# 2. Feed the frames into MediaPipe Hands to detect 21 skeletal coordinates.
# 3. Calculate the distance between your Thumb (Landmark 4) and Index Finger (Landmark 8).
# 4. Generate a gorgeous, responsive "Air Volume Slider" that fills up as you pinch!
# =========================================================================================

import cv2
import mediapipe as mp
import math

# Step 1: Initialize MediaPipe Hand Tracking utilities
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,                 # Track only one hand for simplicity
    min_detection_confidence=0.7,    # Minimum confidence to detect hand
    min_tracking_confidence=0.7      # Minimum confidence to track hand skeleton
)
mp_draw = mp.solutions.drawing_utils # Utility to draw skeletal connections

# Step 2: Open the webcam
cap = cv2.VideoCapture(0)

print("MediaPipe Tracker Initialized!")
print("Raise your hand to the camera. Press 'q' to quit.")

while cap.isOpened():
    success, image = cap.read()
    if not success:
        continue

    # Mirror the image for natural perspective
    image = cv2.flip(image, 1)
    height, width, _ = image.shape
    
    # MediaPipe requires RGB color format (OpenCV uses BGR by default)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Step 3: Process the frame to find hand skeletons
    results = hands.process(rgb_image)

    pinch_pct = 0.0 # Default slider percentage (0% to 100%)

    # Step 4: If a hand is found on the screen
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Draw the 21 dots and connecting skeleton bones on the frame
            mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Step 5: Extract Thumb Tip (Landmark 4) and Index Finger Tip (Landmark 8)
            # Coordinates are returned as a ratio (0.0 to 1.0) of screen width and height
            thumb = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            index = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            
            # Convert ratio coordinates to exact pixel locations
            thumb_px = (int(thumb.x * width), int(thumb.y * height))
            index_px = (int(index.x * width), int(index.y * height))
            
            # Draw small bright blue highlights on the index and thumb tips
            cv2.circle(image, thumb_px, 8, (255, 255, 0), -1)
            cv2.circle(image, index_px, 8, (255, 255, 0), -1)
            
            # Draw a line connecting the thumb and index finger
            cv2.line(image, thumb_px, index_px, (0, 255, 255), 2)
            
            # Step 6: Calculate the Euclidean distance between index and thumb tips
            pixel_distance = math.hypot(thumb_px[0] - index_px[0], thumb_px[1] - index_px[1])
            
            # Map distance (from closed pinch ~20px to wide open ~180px) to percentage (0% to 100%)
            # Closed pinch = 100% full bar, open hand = 0% empty bar (pinch slider effect)
            pinch_pct = (180.0 - pixel_distance) / 160.0
            pinch_pct = max(0.0, min(1.0, pinch_pct)) # Clamp between 0.0 and 1.0

    # Step 7: Draw the responsive "Air Slider" on the screen
    # Draw the background border of the slider on the left side
    cv2.rectangle(image, (30, 100), (60, 350), (100, 100, 100), 2)
    
    # Calculate fill height based on our pinch percentage
    fill_height = int(250 * pinch_pct)
    
    # Draw the dynamic, filled green rectangle representing the pinch state
    if fill_height > 0:
        cv2.rectangle(image, (30, 350 - fill_height), (60, 350), (0, 255, 0), -1)
        
    # Write the current pinch percentage text on screen
    cv2.putText(image, f"PINCH: {int(pinch_pct * 100)}%", (20, 80), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
    cv2.putText(image, "MEDIAPIPE GESTURE SLIDER", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 150, 0), 2)

    # Show video window
    cv2.imshow('Day 1 - MediaPipe Starter', image)
    
    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("MediaPipe demo closed safely!")
