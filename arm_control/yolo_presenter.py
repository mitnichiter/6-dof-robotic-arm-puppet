# =========================================================================================
# PRESENTER SPECIAL: HIGH-PERFORMANCE YOLO11X SEGMENTATION (yolo_presenter.py)
# 
# Optimizations:
# 1. State-of-the-Art Model: Loads 'yolo11x-seg.pt' (56.9M Parameters) for absolute accuracy.
# 2. GPU Acceleration: Forces PyTorch to run on your NVIDIA GPU (CUDA) for buttery-smooth FPS.
# 3. External USB Camera: Attempts to open Index 1 (USB Camera) first, falling back to 0.
# =========================================================================================

import cv2
import sys
import time

try:
    import torch
    from ultralytics import YOLO
except ImportError as e:
    print(f"\n[ERROR] Missing libraries: {e}")
    print("Please run: pip install ultralytics torch")
    input("\nPress Enter to exit...")
    sys.exit()

print("====================================================")
print("     YOLO11S ADVANCED PRESENTATION CONTROLLER       ")
print("====================================================")

# --- STEP 1: VERIFY NVIDIA GPU (CUDA) ACCELERATION ---
device = 'cpu'
if torch.cuda.is_available():
    device = 'cuda'
    gpu_name = torch.cuda.get_device_name(0)
    print(f"✅ NVIDIA GPU DETECTED: {gpu_name}")
    print("🚀 Running with full CUDA hardware acceleration!")
else:
    print("⚠️ WARNING: No NVIDIA GPU detected with CUDA enabled.")
    print("   Running on CPU (The Small model will be very laggy!).")
    print("   For standard CPU laptops, please use yolo_starter.py (Nano) instead.")

# --- STEP 2: LOAD THE SMALL SEGMENTATION MODEL ---
print("\nLoading High-Performance YOLO11s-Seg model... (9.4M params)")
print("Note: On its very first run, it will download a ~20MB file. Please wait...")
try:
    # Explicitly load model onto our targeted device (GPU or CPU)
    model = YOLO('yolo11s-seg.pt').to(device)
    print("✅ Model successfully compiled and loaded on the hardware!")
except Exception as e:
    print(f"Error loading model: {e}")
    sys.exit()

# --- STEP 3: INITIALIZE THE USB CAMERA (INDEX 1) ---
print("\nScanning camera ports...")
# Try Index 1 (External USB Camera) first
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("⚠️ External USB Camera (Index 1) not found or busy.")
    print("🔄 Falling back to default internal webcam (Index 0)...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ CRITICAL ERROR: No webcam could be opened at all!")
        sys.exit()
else:
    print("✅ Successfully connected to External USB Camera!")

# Configure high-resolution feed (Optional, depends on camera support)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("\n--- PRESENTER MODE ACTIVE ---")
print("-> Show objects to your USB camera.")
print("-> Press 'q' in the window to quit safely.\n")

# Performance tracking
prev_time = time.time()

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Horizontal mirror flip (Optional - disable if reading text on items)
    frame = cv2.flip(frame, 1)

    # Step 4: Run YOLO11x Segmentation on the GPU
    results = model(frame, device=device, stream=True)

    # Step 5: Plot results
    for r in results:
        frame = r.plot()

    # Calculate live FPS
    curr_time = time.time()
    fps = 1.0 / (curr_time - prev_time)
    prev_time = curr_time

    # Overlay HUD statistics
    cv2.putText(frame, f"YOLO11s-Seg | Device: {device.upper()}", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (20, 80), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    # Show video window
    cv2.imshow('Presenter Screen - YOLO11s Live Segmentation', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("Presenter YOLO11s model safely stopped.")
