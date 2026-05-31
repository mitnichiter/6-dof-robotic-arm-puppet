# 6-DOF Robotic Arm: Hardware Specifications and Calibration Guide

This document provides a detailed overview of the physical hardware, pinouts, joint channels, safe operating boundaries, and step-by-step physical calibration procedures for the 6-DOF robotic arm.

---

## 1. Hardware Specifications

The robotic arm's electrical and mechanical systems are designed to operate together to achieve fluid, coordinated movement. The core components include:

*   **ESP32 Development Board**: Serves as the central controller. It manages communication (via Serial/REPL, Wi-Fi, or Bluetooth) and commands the PWM driver board over I2C (default pins: SCL to GPIO 22, SDA to GPIO 21).
*   **PCA9685 16-Channel PWM Driver Board**: Communicates with the ESP32 over I2C at address `0x40`. It provides 12-bit PWM resolution at a 50Hz frequency, allowing precise control of up to 16 servos. It also isolates the ESP32's logic power from the high-current power supply required by the servos.
*   **MG996R Metal-Gear High-Torque Servos**: Used for the heavy-duty joints (Base, Rotary/Shoulder, and Elbow) where significant torque is required to lift the arm's physical structure and payload.
*   **SG90 Micro Servos**: Used for the lightweight joints (Wrist Roll, Wrist Pitch/Up-Down, and Claw/Gripper) to reduce overall weight at the end-effector.

---

## 2. Joint Channels and Mapping

The servos are connected to the PCA9685 PWM driver board according to the following channel mapping:

| Joint Channel | Joint Name | Servo Type | Physical Role |
| :--- | :--- | :--- | :--- |
| **Channel 0** | Base | MG996R | Controls horizontal rotation of the entire arm assembly. |
| **Channel 1** | Rotary (Shoulder) | MG996R | Controls forward/backward reach and main lift. |
| **Channel 2** | Elbow | MG996R | Controls secondary height and extension. |
| **Channel 3** | Wrist Roll | SG90 | Controls axial rotation of the wrist/claw assembly. |
| **Channel 4** | Up/Down (Wrist Pitch) | SG90 | Controls pitch angle of the claw (up/down). |
| **Channel 5** | Claw (Gripper) | SG90 | Controls the opening and closing of the gripper fingers. |

---

## 3. Safe Physical Limits

To prevent mechanical damage, stalling, and electrical overloading, strict physical limit constraints must be adhered to:

| Joint Channel | Joint Name | Min Angle | Max Angle | Notes |
| :--- | :--- | :---: | :---: | :--- |
| **Channel 0** | Base | 0° | 180° | Full rotation range. |
| **Channel 1** | Rotary (Shoulder) | 60° | 145° | **Restricted Range**. Exceeding these limits causes mechanical failure. See explanation below. |
| **Channel 2** | Elbow | 0° | 180° | Full rotation range. |
| **Channel 3** | Wrist Roll | 0° | 180° | Full rotation range. |
| **Channel 4** | Up/Down (Wrist Pitch) | 0° | 180° | Full rotation range. |
| **Channel 5** | Claw (Gripper) | 0° | 90° | Restricted range: 0° is fully closed, 90° is fully open. |

### Mechanical Restrictions on the Rotary (Shoulder) Joint
Operating the Rotary joint below **60°** or above **145°** will lead to hardware failure. 
1. **High Torque Load**: At extreme low or high angles, the mechanical advantage of the servo arm is drastically reduced. The servo must exert immense force to hold or lift the structural weight of the upper arm and end-effector.
2. **Mechanical Dead Centers**: At the limits of physical travel, the linkage rods or brackets can align linearly with the servo horn (a dead-center condition), locking the joint.
3. **Stalling & Current Spikes**: When a high torque load or a dead-center locks the servo, it stalls. A stalling MG996R servo draws maximum current (up to 2.5A), leading to:
   * Servos rapidly overheating and burning out.
   * Thermal shutdown or damage to the PCA9685 driver.
   * Voltage drops on the ESP32 power line, causing spontaneous processor resets.

---

## 4. Ideal Reset State

The designated home position / ideal reset state for the arm is:
`[90, 90, 0, 145, 80, 45]`

Representing individual joint angles:
*   **Base**: 90°
*   **Rotary (Shoulder)**: 90°
*   **Elbow**: 0°
*   **Wrist Roll**: 145°
*   **Up/Down (Wrist Pitch)**: 80°
*   **Claw (Gripper)**: 45° (semi-open)

### Mechanical Stability Analysis
This specific pose is chosen as the home configuration for several critical reasons:
*   **Center of Gravity (CoG)**: The arm fold angles pull the physical weight closer to the center of rotation (the base). 
*   **Torque Relief**: By minimizing the horizontal distance (moment arm) between the active joints and the physical center of gravity, the static torque required by the MG996R servos to hold the arm stationary is drastically reduced.
*   **Structural Safety**: While holding this pose, the servos run cool, draw minimal idle current, and are highly stable against external forces or vibration.

---

## 5. Step-by-Step Physical Calibration Guide

Follow this systematic procedure to assemble and calibrate any joint on the robotic arm safely.

### Step 5.1: Software Centering (Before Mechanical Assembly)
Never attach a servo horn to a newly unboxed servo without software-centering it first. If you assemble it at an unknown random physical position, powering on the device could immediately force the servo beyond its physical boundaries and destroy the bracket.

1. Connect the ESP32 and PCA9685 driver board to the appropriate power supply.
2. Run the ESP32 MicroPython firmware with the library loaded.
3. Send a command to position the target channel at exactly **90°** (using `arm.move_raw(channel, 90)`).
4. Keep the servo powered so that its internal feedback loop holds the shaft locked at the electrical center.

### Step 5.2: Physical Horn Alignment
1. With the servo powered and locked at 90°, physically align the servo horn or mounting bracket to its neutral target position (e.g., perpendicular to the physical link, or straight horizontal).
2. Carefully slide the horn onto the splined output shaft.
3. Secure the horn with the center screw. Ensure the bracket does not rub against the servo casing.

### Step 5.3: Safe Boundary Testing
1. Disconnect high-voltage servo power or be prepared to immediately kill power if needed.
2. Run the interactive calibration script from your PC:
   ```bash
   python arm_control/calibrate.py
   ```
3. Establish communication with the ESP32 over `COM5`.
4. Select the joint ID (0 to 5) you wish to test.
5. Command the joint to `90°` first.
6. Slowly "sneak up" on the physical boundaries by changing the angle in small increments (e.g., from `90` to `95`, then `100`, etc.).
7. **Listen Closely**: If you hear a loud buzzing, high-frequency whining, or if the arm starts shaking/vibrating:
   * Immediately type `r` in the CLI to relax the motors and cut current.
   * Back off the angle to a safer range.
   * If a physical obstruction exists, adjust the mechanical horn position or update the soft limits in `robot_arm.py`.

### Step 5.4: Using the GUI Controller
For an interactive, visual testing experience:
1. Run the graphical control panel:
   ```bash
   python arm_control/gui_controller.py
   ```
2. Move the sliders slowly to observe real-time movement of individual joints.
3. Click the **Relax Motors (Stop Shaking)** button immediately if a motor stalls or experiences heavy vibration.
4. Once you find a stable balanced pose, click the **Get Reset State (Print to Screen)** button to print the safe coordinate array to your terminal.
