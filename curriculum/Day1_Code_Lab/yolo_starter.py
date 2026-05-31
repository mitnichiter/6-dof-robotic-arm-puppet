# =========================================================================================
# LESSON 3: OBJECT DETECTION WITH YOLOv8 (yolo_starter.py)
# 
# What we will do:
# 1. Install Ultralytics library (the developer of YOLO).
# 2. Load the pre-trained, lightweight YOLOv8n (nano) neural network.
# 3. Detect and classify 80 standard objects (phones, cups, chairs, persons) in real-time.
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

# Step 1: Load the lightweight pre-trained YOLOv8 Nano model
# The model will automatically download 'yolov8n.pt' (approx 6MB) on its very first run!
print("Loading YOLOv8 AI Model... (this might download a 6MB file on the first run)")
model = YOLO('yolov8n.pt')
print("YOLOv8 successfully loaded and ready!")

# Step 2: Open webcam capture
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)

    # Step 3: Run YOLOv8 on the frame
    # 'stream=True' optimizes performance for continuous webcam frames
    results = model(frame, stream=True)

    # Step 4: Parse detection results
    for r in results:
        # Get detected bounding boxes
        boxes = r.boxes
        for box in boxes:
            # 1. Get raw coordinates of the bounding box
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # 2. Get the Object Class ID and Name (e.g. Person, Cup, Cell phone)
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            
            # 3. Get the prediction confidence rating (0.0 to 1.0)
            confidence = float(box.conf[0])
            
            # 4. Only draw boxes for predictions with greater than 50% confidence
            if confidence > 0.5:
                # Draw a neon blue bounding box around the object
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 100, 0), 3)
                
                # Create a text label: "person: 85%"
                label = f"{class_name}: {int(confidence * 100)}%"
                
                # Draw a text background rectangle
                cv2.rectangle(frame, (x1, y1 - 25), (x1 + len(label) * 11, y1), (255, 100, 0), -1)
                
                # Write label text
                cv2.putText(frame, label, (x1 + 5, y1 - 7), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # Display window title
    cv2.putText(frame, "YOLOv8 REAL-TIME DETECTOR", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    # Show video window
    cv2.imshow('Day 1 - YOLOv8 Object Detection', frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("YOLOv8 shutdown successfully.")
