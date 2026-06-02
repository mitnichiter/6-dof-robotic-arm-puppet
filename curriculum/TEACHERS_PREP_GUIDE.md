# Teacher's Masterclass Preparation Guide & Checklist

Welcome to Prep Day! Taking a class of 75 students (divided into 3 batches of ~25) is highly rewarding, but requires solid preparation. This guide ensures that every piece of hardware, software, and logistics is 100% dialled in before the first student walks into the room.

---

## ⚡ STEP 1: Hardware Diagnostics & Calibration (The Robot)
*Estimated Time: 20 Mins*

Before demonstrating the arm, you must verify its physical connections and make sure there is zero physical binding or power issues.

- [ ] **Power Supply Check:** Ensure the silver 5V external power supply (3A - 5A) is plugged firmly into the green terminal block of the PCA9685 driver board.
  *   *Why?* You cannot run 6 servos off the ESP32's USB power—it will cause current brownouts and make the arm twitch or crash the board.
- [ ] **I2C Wiring Check:** Double-check that the SCL and SDA pins are wired correctly:
  *   **SDA** on PCA9685 $\rightarrow$ **GPIO 21** on ESP32.
  *   **SCL** on PCA9685 $\rightarrow$ **GPIO 22** on ESP32.
  *   **VCC** (Logic) on PCA9685 $\rightarrow$ **3.3V** on ESP32.
  *   **GND** on PCA9685 $\rightarrow$ **GND** on ESP32 (Ensure grounds are shared!).
- [ ] **Run the Quick Calibration CLI:**
    ```bash
    python arm_control/calibrate.py
    ```
    *   Test each joint (0 to 5) using the keyboard. Make sure the joints move smoothly and there are no buzzing noises (which indicate mechanical binding or stalling).
- [ ] **Clean Flash ESP32 Firmware:**
    Ensure the ESP32 is running the latest clean safety files:
    ```bash
    python arm_control/upload_via_repl.py
    ```
    Confirm the arm reboots and immediately folds itself safely into your custom Home pose: `[90, 90, 0, 145, 80, 45]`.

---

## 💻 STEP 2: Host Software Configuration (Your Laptop)
*Estimated Time: 15 Mins*

Your presenter laptop must have all computer vision, AI, and audio packages pre-cached and fully functional.

- [ ] **Verify Python Environment:**
    Ensure all required libraries are installed and compiled:
    ```bash
    python -m pip install opencv-python mediapipe ultralytics pyaudiowpatch numpy pywin32 customtkinter pyautogui
    ```
- [ ] **Pre-Cache YOLO11 Models:**
    YOLO11 downloads model files (`yolo11n-seg.pt` and `yolo11n.pt`) on its first execution. **Do not do this on class Wi-Fi!** Run the starter script once now to pre-download and cache the weights locally:
    ```bash
    python curriculum/Day1_Code_Lab/yolo_starter.py
    ```
    Make sure the camera window opens, download completes, and segmentation overlays render. Press `q` to close.
- [ ] **Dry-Run the Primary Vision Controllers:**
    *   Test **`vision_puppet_pro.py`**: Put your hand up, test left/right swiveling, reach down, and make a **fist ✊ (Pose Hold)**. Confirm it freezes and holds its position smoothly.
    *   Test **`dance.py`**: Play a loud song on your laptop speakers. Press `d` and verify the arm dances dynamically using your WASAPI loopback, and matches the beat of your music.
- [ ] **Dry-Run the Skeletal Virtual Mouse:**
    ```bash
    python curriculum/Day1_Code_Lab/virtual_mouse.py
    ```
    Ensure you can point to move the cursor, pinch index/thumb to drag a window, and pinch middle/thumb to right-click.

---

## 🏫 STEP 3: Classroom & Student Lab Prep (Logistics)
*Estimated Time: 25 Mins*

With 3 batches of 25 students, keeping the software setup under 10 minutes is critical to saving lab time.

- [ ] **Pre-Package the Student Lab Files:**
    Create a simple ZIP file containing only the `Day1_Code_Lab` folder or give them the link to your GitHub repository:
    *   🔗 **Your Repository:** [https://github.com/mitnichiter/6-dof-robotic-arm-puppet](https://github.com/mitnichiter/6-dof-robotic-arm-puppet)
    *   They can simply clone or download your repo to get the three clean starter files (`opencv_starter.py`, `mediapipe_starter.py`, `yolo_starter.py`, and `virtual_mouse.py`).
- [ ] **Write the Install Command on the Whiteboard:**
    Before the students sit down, write the installation command prominently on the physical whiteboard so they can start installing dependencies immediately:
    ```bash
    pip install opencv-python mediapipe ultralytics pyautogui
    ```
- [ ] **Audio & Projector Check:**
    *   Ensure your laptop screen is duplicated (not extended) on the projector so they see exactly what you are doing.
    *   Verify that your laptop’s audio is loud enough for the entire classroom to hear during the **Robotic Arm Dance Demo** on Day 2.

---

## 🎭 STEP 4: Live Presentation Dry-Run (The Pitch)
*Estimated Time: 10 Mins*

- [ ] **Review `PRESENTATION_NOTES.md`:**
    *   Open and review your presentation notes in `curriculum/PRESENTATION_NOTES.md`.
    *   Remember: **You are selling a hook.** You do not need to explain complex trigonometry or deep convolutional layers. Keep it magical, highly visual, and interactive.
    *   Identify the exact moments where you will invite students up to the desk to control the arm. (Choose high-energy students; it builds incredible classroom atmosphere!).

---

## 📋 Quick-Start Cheat Sheet during Class

| If this happens... | The Root Cause is... | How to Fix It instantly... |
| :--- | :--- | :--- |
| **Arm twitches or fails to connect** | Port is held open by another script. | Run `Stop-Process -Name "python" -Force` in PowerShell, then reconnect USB. |
| **"Failed to access COM5"** | ESP32 serial buffer is flooded or frozen. | Unplug ESP32 USB, plug it back in, run `upload_via_repl.py` to reset the loop. |
| **YOLO is lagging heavily** | Laptop is running on battery saver or using Integrated GPU. | Plug in your laptop charger, and set Windows Power Mode to "Best Performance". |
| **Virtual Mouse moves too fast** | Monitor resolution is very high (e.g. 4K). | Open `virtual_mouse.py` and decrease `SMOOTHING_FACTOR` to `0.15` or `0.10` for slower, smoother glides. |
