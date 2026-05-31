# PC-Side Computer Vision Tracking and Gestures

This document details the architecture, design, and mathematical implementation of the computer vision control, skeletal mapping, signal filtering, and autonomous intelligent routines of the robotic arm.

---

## 1. Camera System & Interactive Window

The vision pipeline is built on a standard video capturing engine using OpenCV (`cv2`) and MediaPipe Hands to process high-frequency video frames with minimal overhead.

### Mirroring and Intuitive Control
By default, camera feeds are inverted from the user's perspective. To ensure control feels natural—like looking into a mirror—the frame is flipped horizontally along the vertical axis immediately after capture:
```python
# Capture the frame
success, image = cap.read()
if success:
    # Flip horizontally for intuitive mirroring (left hand moves left in screen space)
    image = cv2.flip(image, 1)
```

### Screen Space Interaction Window
To prevent tracking issues at screen edges and maximize resolution in the active workspace, hand landmarks are normalized within a high-performance interaction window spanning `0.1` to `0.9` of normalized screen space. 

Landmarks outside this `[0.1, 0.9]` boundary are clamped to the boundaries, protecting the system from edge-loss anomalies. This design ensures that the entire physical range of the arm is accessible within a comfortable hand-movement area.

---

## 2. Multi-Axis Hand Mapping

The position and orientation of the user's hand are mapped to individual joint servo angles using geometric calculations on specific landmarks.

```
       [8] Index Tip       [12] Middle Tip
          \                  /
    [7] Index PIP      [11] Middle PIP
          |                  |
    [6] Index MCP      [10] Middle MCP
          \                  /
           \--[9] Knuckle --/ (Middle MCP - Center of Hand)
                 |
                 |
               [0] Wrist
```

### Base Swivel (X-Axis)
*   **Source Landmark**: Middle Finger MCP / Knuckle (Landmark 9) X-coordinate.
*   **Target Joint**: Base Servo (0° to 180°).
*   **Behavior**: Knuckle `center_x` in the range `[0.1, 0.9]` is linearly mapped to `[180, 0]` degrees. Mirroring inverts the direction so that moving your hand to the left swivels the base to the left.
*   **Mapping**:
    ```python
    base_target = map_range(center_x, 0.1, 0.9, 180, 0)
    ```

### Elevation (Y-Axis)
*   **Source Landmark**: Middle Finger MCP / Knuckle (Landmark 9) Y-coordinate.
*   **Target Joint**: Up/Down Servo (20° to 160°).
*   **Behavior**: Vertical movement maps `center_y` in the range `[0.1, 0.9]` to `[20, 160]` (or `[160, 20]`). Upward physical movement (smaller Y coordinate in screen coordinates) raises the arm, while downward movement lowers it.
*   **Mapping**:
    ```python
    up_down_target = map_range(center_y, 0.1, 0.9, 20, 160)
    ```

### Reach Depth (Z-Axis & Coordinated Kinematics)
*   **Source landmarks**: Wrist (Landmark 0) and Middle Finger MCP (Landmark 9).
*   **Target Joints**: Coordinated coupling of Rotary (Shoulder) Servo and Elbow Servo.
*   **Skeletal Stability**: Utilizing the physical distance between the Wrist (0) and Middle Knuckle (9) as a depth metric solves depth-glitch problems associated with index-thumb pinching. Because the distance between Landmark 0 and 9 remains rigid regardless of finger curls, depth calculation remains exceptionally stable.
*   **Behavior**: 
    *   **Palm size**: Computed using the Euclidean distance (hypot) in 2D space.
        $$\text{palm\_size} = \sqrt{(x_9 - x_0)^2 + (y_9 - y_0)^2}$$
    *   **Reach Factor**: Normalized to a `[0.0, 1.0]` range.
    *   **Forward Reach**: Hand close to camera (large palm size, e.g., 0.25) $\rightarrow$ Reach Factor = 1.0 $\rightarrow$ Rotary reaches forward (60°), Elbow opens up (150°).
    *   **Pull Back**: Hand far from camera (small palm size, e.g., 0.05) $\rightarrow$ Reach Factor = 0.0 $\rightarrow$ Rotary pulls back (145°), Elbow retracts (0°).
*   **Coupled Kinematics Equations**:
    ```python
    palm_size = math.hypot(lm9.x - lm0.x, lm9.y - lm0.y)
    reach_factor = map_range(palm_size, 0.05, 0.25, 0.0, 1.0)
    
    rotary_target = map_range(reach_factor, 0.0, 1.0, 145, 60)
    elbow_target = map_range(reach_factor, 0.0, 1.0, 0, 150)
    ```

### Wrist Roll
*   **Source Landmarks**: Vector from Wrist (0) to Middle Knuckle (9).
*   **Target Joint**: Wrist Roll Servo.
*   **Behavior**: Computes hand tilt angle relative to the frame using `math.atan2` on the delta coordinates. It maps the dynamic rotational angle to the Wrist servo with a neutral rest center positioned around 145°.
*   **Mapping**:
    ```python
    dx = lm9.x - lm0.x
    dy = lm9.y - lm0.y
    angle_deg = math.degrees(math.atan2(dy, dx))
    
    # Map tilt degrees [-135, -45] to servo limits [190, 100]
    wrist_target = map_range(angle_deg, -135, -45, 190, 100)
    ```

### Claw Grip (Continuous)
*   **Source Landmarks**: Thumb Tip (Landmark 4) and Index Finger Tip (Landmark 8).
*   **Target Joint**: Claw Servo (0° to 90°).
*   **Behavior**: Measures the Euclidean pinch distance. A small distance closes the claw (0°), while opening index/thumb fully opens the claw (90°).
*   **Mapping**:
    ```python
    pinch_dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
    claw_target = map_range(pinch_dist, 0.03, 0.12, 0, 90)
    ```

---

## 3. Filters & Momentum Simulation

To convert raw, noisy vision coordinates into fluid, professional robot motions, two advanced signal-filtering strategies are utilized in the control loop.

### Butter-Smooth Adaptive Velocity Filter
Standard exponential smoothing uses a fixed weighting factor ($\alpha$), which introduces a trade-off: high $\alpha$ is responsive but shaky, while low $\alpha$ is laggy.

The **Butter-Smooth Filter** solves this by dynamically adjusting $\alpha$ based on joint velocity (the delta between target and current state):
*   **Stationary State**: When delta is tiny (hand is stationary/jittering), $\alpha \rightarrow 0.02$ (heavy smoothing). This completely eliminates high-frequency twitching and twitch jitter.
*   **High-Speed State**: When delta is large (fast movement), $\alpha \rightarrow 0.35$ (instantaneous responsiveness), preserving agility with negligible lag.

```python
class ButterSmoothFilter:
    def __init__(self, initial_val):
        self.val = initial_val

    def update(self, target):
        delta = abs(target - self.val)
        # Scale alpha between 0.02 (stationary) and 0.35 (fast motion)
        alpha = max(0.02, min(0.35, 0.02 + (delta / 100.0) * 0.33))
        self.val = (alpha * target) + ((1.0 - alpha) * self.val)
        return self.val
```

### Holt's Double Exponential Smoothing
To mimic the physical momentum, mass, and inertia of real human muscle, Holt's forecasting model is employed. It tracks both the coordinate position and its velocity trend:

$$\begin{aligned}
s_t &= \alpha y_t + (1 - \alpha)(s_{t-1} + b_{t-1}) \\
b_t &= \beta(s_t - s_{t-1}) + (1 - \beta)b_{t-1}
\end{aligned}$$

This filter generates organic acceleration and deceleration curves, transforming raw servo movements into elegant, lifelike gestures.

```python
class OrganicSmoother:
    """Holt's Double Exponential Smoothing.
    Tracks both s (position) and b (velocity/trend) to simulate inertia."""
    def __init__(self, initial_val, alpha=0.35, beta=0.15):
        self.s = initial_val  # Position
        self.b = 0.0          # Trend / Velocity
        self.alpha = alpha    # Data smoothing factor
        self.beta = beta      # Trend smoothing factor

    def update(self, target):
        old_s = self.s
        self.s = self.alpha * target + (1 - self.alpha) * (self.s + self.b)
        self.b = self.beta * (self.s - old_s) + (1 - self.beta) * self.b
        return self.s
```

---

## 4. Intelligent Routines

Outside of direct mapping, the robot contains several autonomous execution modes that enhance its agency and interactivity.

### Pose Hold (Clutch)
The "Clutch" is a safety and alignment gesture. When the user makes a tight fist, the system locks the current smoothed coordinates, ignoring any further tracking updates. This allows the user to reposition their hand or step away without causing the arm to move or park.

*   **Fist Detection Logic**: Counts how many finger tips are closer to the wrist than their respective MCP joints. If 3 or more fingers are curled, it triggers the clutch.
```python
def is_fist(landmarks):
    wrist = landmarks.landmark[mp_hands.HandLandmark.WRIST]
    tips = [
        mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP
    ]
    mcps = [
        mp_hands.HandLandmark.INDEX_FINGER_MCP,
        mp_hands.HandLandmark.MIDDLE_FINGER_MCP,
        mp_hands.HandLandmark.RING_FINGER_MCP,
        mp_hands.HandLandmark.PINKY_MCP
    ]
    
    curled_fingers = 0
    for tip, mcp in zip(tips, mcps):
        dist_tip_to_wrist = math.hypot(landmarks.landmark[tip].x - wrist.x, landmarks.landmark[tip].y - wrist.y)
        dist_mcp_to_wrist = math.hypot(landmarks.landmark[mcp].x - wrist.x, landmarks.landmark[mcp].y - wrist.y)
        if dist_tip_to_wrist < dist_mcp_to_wrist:
            curled_fingers += 1
            
    return curled_fingers >= 3
```

### Generative Audio-Reactive Dancing
In dance mode, the arm transitions from visual puppet to a music-driven performer. By binding directly to the Windows WASAPI Loopback driver using PyAudioWPatch, the PC intercepts pure speaker audio stream without needing an external microphone.

```
+-------------------------------------------------------------+
|                     Windows Audio Session                   |
+-------------------------------------------------------------+
                              |
                     WASAPI Loopback Capture
                              |
                              v
                      FFT / Band Filtering
        +---------------------+---------------------+
        |                     |                     |
     [BASS]                 [MID]                [TREB]
  (60 - 250 Hz)        (250 - 2000 Hz)       (2000 - 8000 Hz)
        |                     |                     |
        v                     v                     v
  Shoulder Hit           Torso Bob              Claw Snap
```

The audio is processed via FFT, splitting the wave into three frequency bands:
1.  **Bass Envelope (60Hz - 250Hz)**: Drives "The Hit". Triggers deep, fast muscle-like forward leans on the Rotary shoulder and Elbow joints, with slow organic recovery.
2.  **Mid Envelope (250Hz - 2kHz)**: Drives "The Bounce". Controls rhythmic bobbing on the Up/Down axis.
3.  **Treble Envelope (2kHz - 8kHz)**: Drives "The Snap". Triggers sharp claw snaps on transient high-frequency percussion.
4.  **RMS Volume / Energy**: Drives "The Groove" and Phase Modulation.
    *   **Phase Modulation**: Modulates the velocity of time ($t$) in the wave functions. High-energy segments accelerate the movement pace.
        $$\text{dance\_time} = \text{dance\_time} + dt \times (1.0 + (\text{energy} \times 1.5))$$
    *   **Sway Width**: Expands base swivel boundaries as music volume increases.
        $$\theta_{\text{base}} = 90^\circ + \sin(\text{dance\_time} \times 1.2) \times (15^\circ + (\text{energy} \times 45^\circ))$$

### Organic Idle Breathing
To make the robotic arm feel alive even when parked, an idle subroutine initiates automatically whenever a hand is absent from the camera field for more than `1.5` seconds.

Rather than remaining rigidly static, the arm simulates resting respiration using a superposition of multiple out-of-phase sine and cosine waves on the Rotary and Up/Down joints. This generates complex, non-repeating lifelike idle breathing:

```python
# Multi-frequency out-of-phase wave superposition for organic idle
idle_target = HOME_STATE[i]
if i in [1, 4]: # Rotary and Elevation
    idle_target += (math.sin(t_idle * 1.2) * 3) + (math.cos(t_idle * 0.5) * 1.5)
elif i == 3: # Wrist
    idle_target += math.sin(t_idle * 0.8) * 2
```
This continuous micro-oscillation keeps the arm moving naturally, preventing it from appearing deactivated or sterile.
