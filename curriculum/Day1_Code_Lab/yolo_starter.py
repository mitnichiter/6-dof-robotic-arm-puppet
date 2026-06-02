# =========================================================================================
# LESSON 3: ADVANCED AI SEGMENTATION WITH YOLO11 (yolo_starter.py)
# 
# What we will do:
# 1. Load the bleeding-edge pre-trained YOLO11 Nano Segmentation model (yolo11n-seg.pt).
# 2. Perform live, pixel-perfect instance segmentation (not just bounding boxes,
#    but colored, form-fitting outlines of every object!).
# 3. Use the built-in plot() engine to draw stunning translucent overlays.
# =========================================================================================

# --- INSTRUCTIONS FOR STUDENTS ---
# To run this script, you must install the ultralytics library:
# In your terminal/command prompt run:
#   pip install ultralytics
# ---------------------------------

import cv2
try:
    from ultralytics import YOLO
except ImportError:
    print("\n[ERROR] 'ultralytics' library is not installed!")
    print("Please open your terminal and run: pip install ultralytics")
    input("\nPress Enter to exit...")
    exit()

# Step 1: Load the bleeding-edge pre-trained YOLO11 Nano Segmentation model
# This model will download 'yolo11n-seg.pt' (approx 7.2MB) on its first run
print("Loading Bleeding-Edge YOLO11 Segmentation AI Model...")
model = YOLO('yolo11n-seg.pt')
print("YOLO11 Segmentation model successfully loaded!")

# Step 2: Open webcam capture
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)

    # Step 3: Run YOLO11 Segmentation on the frame
    results = model(frame, stream=True)

    # Step 4: Parse detection results & auto-plot gorgeous outlines/masks
    for r in results:
        # r.plot() is a powerful engine built into Ultralytics.
        # It automatically draws translucent masks on segmented objects, bounding boxes, 
        # class labels (e.g., person, bottle, laptop), and prediction confidence levels!
        frame = r.plot()

    # Display window title
    cv2.putText(frame, "YOLO11 LIVE AI SEGMENTATION", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    # Show video window
    cv2.imshow('Day 1 - YOLO11 Live Segmentation', frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("YOLO11 Segmentation shutdown successfully.")
