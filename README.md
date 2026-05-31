# 6-DOF Robotic Arm - Computer Vision & Audio Reactive Control System

Welcome to the 6-DOF 3D-printed robotic arm project! This system uses an ESP32 microcontroller and a PCA9685 driver to enable real-time hand-tracking puppet control (via OpenCV and MediaPipe) and generative, audio-reactive dancing (via Windows WASAPI).

---

## 📂 Project Directory Structure

Here is a map of the key files in the repository:

```
D:/arm/
├── README.md                          # Main project overview (This file)
├── docs/
│   ├── HARDWARE_CALIBRATION.md        # Specs, joint pins, and limits
│   ├── FIRMWARE_MICROPYTHON.md        # MicroPython, ESP32 classes, and uploads
│   └── VISION_CONTROL.md              # OpenCV, MediaPipe, filters, and gestures
└── arm_control/
    ├── robot_arm.py                   # On-board ESP32 control class
    ├── main.py                        # On-board ESP32 non-blocking uselect loop
    ├── kill.py                        # On-board ESP32 instant motor cutoff
    ├── upload_via_repl.py             # PC-side safe firmware uploader script
    ├── calibrate.py                   # Interactive joint calibration CLI
    ├── gui_controller.py              # Dark-mode slider calibration GUI
    ├── vision_puppet_pro.py           # Human-like tracking with Clutch (Fist freeze)
    ├── vision_puppet_audio.py         # Advanced hand-tracking + Key-activated music dance
    └── dance.py                       # Standalone Generative Keyframe Audio Dancer
```

---

## ⚙️ Quick Start Guide

### Step 1: Physical Setup
1.  Verify SCL is wired to **GPIO 22** and SDA is wired to **GPIO 21** on the ESP32.
2.  Plug the 6 servos into Channels 0-5 of the PCA9685 driver board.
3.  Connect a dedicated external 5V (3A - 5A) power supply to the PCA9685's green terminal block.
4.  *Read more details in:* [Hardware Specifications & Joint Calibration](./docs/HARDWARE_CALIBRATION.md)

### Step 2: Upload Firmware
1.  Connect your ESP32 to your PC via USB.
2.  Install requirements and run our custom uploader to flash `robot_arm.py` and `main.py`:
    ```bash
    python -m pip install pyserial
    python arm_control/upload_via_repl.py
    ```
3.  The arm will immediately boot and fold itself safely into its home state: `[90, 90, 0, 145, 80, 45]`.
4.  *Read more details in:* [MicroPython Firmware & ESP32 Controller](./docs/FIRMWARE_MICROPYTHON.md)

### Step 3: Run Hand Tracking & Gesture Control
1.  Install dependencies on your PC:
    ```bash
    python -m pip install opencv-python mediapipe pyaudiowpatch numpy pywin32 customtkinter
    ```
2.  Launch the advanced, human-like puppet controller:
    ```bash
    python arm_control/vision_puppet_pro.py
    ```
3.  **Hold your hand up** to the webcam. Tilt your hand to spin the wrist, pinch your index/thumb to close the claw, and reach forward/backward to extend the arm.
4.  **Make a tight fist ✊** to activate the "Clutch" and freeze the arm in mid-air.
5.  *Read more details in:* [Webcam Tracking & Advanced Gesture Control](./docs/VISION_CONTROL.md)

### Step 4: Run Generative Audio Dance Mode
1.  Play your favorite song on your PC (Spotify, YouTube, etc.).
2.  Launch the standalone, intelligent choreographer:
    ```bash
    python arm_control/dance.py
    ```
3.  The arm will hook into your system audio loopback and dynamically generate hip-hop dance moves (Headbangs, DJ scratching, Cobras, and volume-bobs) in real-time!

---

## 📘 Detailed Documentation

To dive deeper into the mathematics, algorithms, and configurations of this project, please explore our sub-documents:

*   **[Hardware Calibration](./docs/HARDWARE_CALIBRATION.md):** Learn about the servos, safe physical limits (why the rotary joint is capped between 60° and 145°), and how to manually align your motor horns.
*   **[MicroPython Firmware](./docs/FIRMWARE_MICROPYTHON.md):** Learn how `uselect.poll()` handles high-frequency serial commands on the ESP32 without blocking the main CPU, and review our custom packet structure.
*   **[Vision Control & Audio Reactivity](./docs/VISION_CONTROL.md):** Deep-dive into our Adaptive "Butter-Smooth" filter, our stable Palm-Size Z-axis tracking, and how our audio thread uses Fast Fourier Transforms (FFT) and Envelope Followers to simulate momentum.
