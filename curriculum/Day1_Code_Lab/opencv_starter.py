# =========================================================================================
# LESSON 1: INTRODUCTION TO OPENCV (opencv_starter.py)
# 
# What we will do:
# 1. Initialize your laptop's webcam.
# 2. Mirror the video feed so it acts like a natural mirror.
# 3. Read raw frame pixels, draw a green target circle in the center, and write text overlays.
# =========================================================================================

import cv2

# Step 1: Open the connection to your default camera (0 is usually the built-in webcam)
cap = cv2.VideoCapture(0)

# Check if webcam opened successfully
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Webcam successfully activated!")
print("Press 'q' in the video window to quit.")

while True:
    # Step 2: Capture frame-by-frame
    # 'ret' is a boolean (True if frame is captured successfully), 'frame' is the image array
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to grab frame.")
        break

    # Step 3: Flip the image horizontally (1) so it acts like a mirror
    frame = cv2.flip(frame, 1)

    # Get the width and height of the video frame
    height, width, _ = frame.shape
    center_x = int(width / 2)
    center_y = int(height / 2)

    # Step 4: Draw a green target circle in the center of the screen
    # cv2.circle(image, center_coordinates, radius, color_BGR, thickness)
    cv2.circle(frame, (center_x, center_y), 40, (0, 255, 0), 3)

    # Draw a small center dot
    cv2.circle(frame, (center_x, center_y), 4, (0, 0, 255), -1) # -1 thickness means filled circle

    # Step 5: Overlay a cool title on the screen
    # cv2.putText(image, text, origin_point, font, scale, color_BGR, thickness)
    cv2.putText(frame, "OPENCV PIXEL WORKSHOP", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    
    cv2.putText(frame, "Press 'q' to Quit", (20, height - 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # Step 6: Display the resulting frame in a window
    cv2.imshow('Day 1 - OpenCV Starter', frame)

    # Step 7: Wait for 1 millisecond and check if the user pressed the 'q' key to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Step 8: When everything is done, release the webcam capture and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()
print("Webcam released. OpenCV shut down successfully!")
