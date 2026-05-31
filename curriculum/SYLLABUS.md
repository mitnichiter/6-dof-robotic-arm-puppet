# 2-Day Computer Vision & Robotics Masterclass Syllabus

**Target Audience:** 75 Students (Split into 3 batches of ~25 students each)  
**Time Allocation:** 2.5 Hours per batch per day (Total: 5 Hours per student over 2 days)  
**Core Goal:** Showcase "magic" with OpenCV, MediaPipe, and YOLOv8, and then demonstrate how these software layers drive the physical 6-DOF Robotic Arm to hook them into the advanced full-term Robotics Course.

---

## 📅 DAY 1: "The Magic of Computer Vision" (Hands-On Lab)
*Focus: Instant gratification. Students write code on their laptops, see immediate visual feedback, and learn the basic building blocks of AI.*

### ⏱️ Timeline & Breakdown (150 Mins)

#### 0:00 - 0:15 (15 Mins) | The Hook: What is Computer Vision?
*   **Action:** Show a fast, 3-minute video of self-driving cars, surgery robots, and robotic arms sorting sorting items. 
*   **Core Message:** "We are going to teach your laptop how to see today, and tomorrow, we are going to plug your laptop into a robotic arm to make it a physical puppet."

#### 0:15 - 1:00 (45 Mins) | Lab 1: OpenCV — Playing with Pixels
*   **Concepts:** Frame capture, horizontal flip (mirroring), color space conversion (BGR to RGB), drawing overlays (circles, rectangles, texts).
*   **Hands-on:** Students open a basic script, initialize their webcam, and write a simple script to draw a green circle that mirrors their movement on the screen.
*   **Key takeaway:** OpenCV turns raw video into numerical arrays (pixels) we can manipulate with Python.

#### 1:00 - 1:45 (45 Mins) | Lab 2: MediaPipe — Gesture Mapping & The Virtual Slider
*   **Concepts:** Deep-learning based skeletal hand tracking, 21 landmark coordinate vectors.
*   **Hands-on:** Students load a skeletal hands model, isolate the **Thumb Tip (4)** and **Index Tip (8)**, calculate their physical distance, and use it to control an on-screen "Air Slider" or virtual volume bar.
*   **Key takeaway:** We can turn physical human hand poses into exact floating-point numbers in real-time.

#### 1:45 - 2:15 (30 Mins) | Lab 3: YOLOv8 — Giving the AI Eyes
*   **Concepts:** Object Detection vs Tracking, bounding boxes, class classification, pre-trained weights.
*   **Hands-on:** Run a 5-line YOLOv8 model on their webcam. Students hold up their phones, cups, keys, or wallets, and watch the AI draw boxes around them and label them in milliseconds.
*   **Key takeaway:** AI doesn't just see pixels; it understands *objects* and *context*.

#### 2:15 - 2:30 (15 Mins) | Day 1 Debrief & Day 2 Teaser
*   **Recap:** "Today we turned pixels into coordinates (OpenCV), tracked hand skeletons (MediaPipe), and detected objects (YOLO)."
*   **Teaser:** "Tomorrow, we plug these exact scripts into our physical 6-DOF Robotic Arm and turn your hand into a digital controller!"

---

## 📅 DAY 2: "Bringing Code to Life" (The Grand Demo)
*Focus: Showcasing physical robotics, explaining the bridge between software and hardware, and pitching the full-term robotics course.*

### ⏱️ Timeline & Breakdown (150 Mins)

#### 0:00 - 0:30 (30 Mins) | The Showstopper: Live Interactive Puppet Demo
*   **Action:** Power up the 6-DOF arm. Run the **Pro Puppet Script (`vision_puppet_pro.py`)**.
*   **Interaction:** Bring 3-4 students up from the crowd. Let them wave, pinch, and make a **fist ✊ (Pose Hold)** to control the arm. 
*   **Action 2:** Play a song, hit **`d`**, and show off the **Generative Audio-Reactive Dancer (`dance.py`)**. Let them see the arm groove, headbang, and clap to the beat!
*   **Effect:** This sets an incredibly high-energy atmosphere and completely captures their attention.

#### 0:30 - 1:15 (45 Mins) | Hardware Breakdown: Anatomy of a Robot
*   **Concepts:** Microcontroller vs Microprocessor, Servo Motors, Current/Voltage spikes, I2C Protocol.
*   **The Blueprint:**
    *   **The Brain (ESP32):** Receives the commands from our Python scripts via Serial (USB).
    *   **The Muscle Driver (PCA9685):** Generates PWM signals for 16 servos over I2C (only 2 pins: SDA 21, SCL 22).
    *   **The Joints (Servos):** Explains how duty cycles map to exact angles (`500us` to `2500us`).
    *   **The Power Supply:** Why we need a dedicated 5V 5A power supply (stalling motors pull high current, explaining why a USB port isn't enough).

#### 1:15 - 2:00 (45 Mins) | Demystifying the Code (Software-to-Hardware Bridge)
*   **Walkthrough:** Explain the code they learned on Day 1 and show how it bridges to the ESP32:
    *   How `vision_puppet.py` packages coordinates into `<b,r,e,w,u,c>\n` strings and blasts them over COM5 at 115,200 baud.
    *   How `main.py` on the ESP32 reads it, filters it, and passes it to the `RobotArm` safety library.
*   **The Magic Revealed:** Show them that they already wrote 80% of the puppet script on Day 1! The only difference is sending the numbers over serial.

#### 2:00 - 2:30 (30 Mins) | The Pitch: How to Build Your Own Machine
*   **The Roadmap:** What does it take to design and build this from scratch?
    *   CAD & 3D Printing (Structure).
    *   Embedded C++ / MicroPython (Firmware).
    *   Circuit Design & PCBs (Custom Power Boards).
    *   Inverse Kinematics & Path Planning (Advanced Motion Math).
*   **The Hook:** "If you want to move from just writing software to building physical, intelligent, autonomous hardware—join our core Robotics Course. This is what you will design, assemble, and program."
