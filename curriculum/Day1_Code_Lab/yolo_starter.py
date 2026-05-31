# =========================================================================================
# LESSON 3: ADVANCED AI SEGMENTATION WITH YOLOv8 (yolo_starter.py)
# 
# What we will do:
# 1. Load the pre-trained YOLOv8 Nano Segmentation model (yolov8n-seg.pt).
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

# Step 1: Load the advanced pre-trained YOLOv8 Nano Segmentation model
# This model will download 'yolov8n-seg.pt' (approx 7MB) on its first run
print("Loading Advanced YOLOv8 Segmentation AI Model...")
model = YOLO('yolov8n-seg.pt')
print("YOLOv8 Segmentation model successfully loaded!")

# Step 2: Open webcam capture
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)

    # Step 3: Run YOLOv8 Segmentation on the frame
    results = model(frame, stream=True)

    # Step 4: Parse detection results & auto-plot gorgeous outlines/masks
    for r in results:
        # r.plot() is a powerful engine built into Ultralytics.
        # It automatically draws translucent masks on segmented objects, bounding boxes, 
        # class labels (e.g., person, bottle, laptop), and prediction confidence levels!
        frame = r.plot()

    # Display window title
    cv2.putText(frame, "YOLOv8 LIVE AI SEGMENTATION", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    # Show video window
    cv2.imshow('Day 1 - YOLOv8 Live Segmentation', frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("YOLOv8 Segmentation shutdown successfully.")
