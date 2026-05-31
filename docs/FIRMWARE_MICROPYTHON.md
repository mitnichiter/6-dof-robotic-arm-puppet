# ESP32 MicroPython Firmware & Server Documentation

This document describes the flashing procedure, file system layout, communication protocol, and reliable upload mechanism for the ESP32-based MicroPython robot arm controller.

---

## 1. Flashing MicroPython Firmware

To run the custom control software, the ESP32 board must be flashed with standard MicroPython firmware.

### Prerequisites
1. Install Python 3 on the host PC.
2. Install the Espressif chip programming utility `esptool.py`:
   ```bash
   pip install esptool
   ```
3. Download the official MicroPython firmware binary for ESP32. The project has been tested with `ESP32_GENERIC-*.bin` (e.g., `ESP32_GENERIC-20231005-v1.21.0.bin` or newer).

### Flashing Steps

Run the following commands in the terminal (adjust `COM5` to match your local ESP32 serial port):

1. **Erase the existing flash memory:**
   ```bash
   esptool.py --chip esp32 --port COM5 erase_flash
   ```
   *Expected Output:*
   ```text
   esptool.py v4.6.2
   Serial port COM5
   Connecting........__
   Chip is ESP32-D0WDQ6-V3 (revision v3.0)
   Features: WiFi, BT, Dual Core, 240MHz, Voci, Coding Scheme 11
   Crystal is 40MHz
   MAC: e8:9f:6d:08:b8:34
   Uploading stub...
   Running stub...
   Stub running...
   Erasing flash (this may take a while)...
   Chip erase completed successfully in 3.4s
   Hard resetting via RTS pin...
   ```

2. **Write the new MicroPython firmware starting at address `0x1000`:**
   ```bash
   esptool.py --chip esp32 --port COM5 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-20231005-v1.21.0.bin
   ```
   *Note: Using a higher baud rate (such as 460800) speeds up the transfer. If connection errors occur, fall back to 115200.*

---

## 2. ESP32 File System

Once flashed, the ESP32 runs a virtual file system. Three core scripts are deployed on the board to run the robot arm:
1. `robot_arm.py`: Custom driver class implementing PCA9685 control, safety limit mapping, clamp boundaries, and software sweep movements.
2. `main.py`: Non-blocking serial listener running on boot at 30+ FPS.
3. `kill.py`: Instant low-level I2C register override to cut power to all PWM channels.

### A. Core Driver: `robot_arm.py`

This module defines the `PCA9685` register controller and the high-level `RobotArm` API. It enforces absolute safety constraints, soft limits mapping, clamp boundaries, and sweeping movements.

```python
from machine import I2C, Pin
import time
import ustruct

class PCA9685:
    def __init__(self, i2c, address=0x40):
        self.i2c = i2c
        self.address = address
        self.i2c.writeto_mem(self.address, 0x00, b'\x00') # Wake up
        self.i2c.writeto_mem(self.address, 0x00, b'\x10') # Sleep
        self.i2c.writeto_mem(self.address, 0xFE, bytes([121])) # Prescale for 50Hz
        self.i2c.writeto_mem(self.address, 0x00, b'\x00') # Wake
        time.sleep_us(500)
        self.i2c.writeto_mem(self.address, 0x00, b'\xa1') # Auto-increment
        
    def set_pwm(self, channel, on, off):
        data = ustruct.pack('<HH', on, off)
        self.i2c.writeto_mem(self.address, 0x06 + 4 * channel, data)

class RobotArm:
    # Joint Constants
    BASE = 0
    ROTARY = 1
    ELBOW = 2
    WRIST = 3
    UP_DOWN = 4
    CLAW = 5

    def __init__(self, scl_pin=22, sda_pin=21):
        self.i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin))
        self.driver = PCA9685(self.i2c)
        
        # Absolute Safety Limits based on calibration data
        self.limits = {
            self.BASE: (0, 180),
            self.ROTARY: (0, 180),   # Full range enabled for experimental range testing
            self.ELBOW: (0, 180),
            self.WRIST: (0, 180),
            self.UP_DOWN: (0, 180),
            self.CLAW: (0, 90)       # Restricted claw boundaries to prevent mechanical stalls
        }
        
        # Track current positions. Initialized to the Ideal Home Reset State.
        self.current_positions = {
            self.BASE: 90, self.ROTARY: 90, self.ELBOW: 0,
            self.WRIST: 145, self.UP_DOWN: 80, self.CLAW: 45
        }

    def _angle_to_duty(self, angle):
        min_duty = 102
        max_duty = 512
        # Failsafe clamp to 0-180 physical servo limits
        angle = max(0, min(angle, 180))
        return int(min_duty + (max_duty - min_duty) * (angle / 180.0))

    def move_raw(self, joint, angle):
        """Direct move without safety constraints - ONLY FOR CALIBRATION"""
        duty = self._angle_to_duty(angle)
        self.driver.set_pwm(joint, 0, duty)

    def move(self, joint, angle, speed=0):
        """Moves a specific joint to an angle safely with optional software sweeping."""
        if joint not in self.limits:
            return
            
        # Constrain to safe limits
        min_angle, max_angle = self.limits[joint]
        target_angle = max(min_angle, min(angle, max_angle))
        
        start_angle = self.current_positions.get(joint, 90)
        
        if speed == 0:
            duty = self._angle_to_duty(target_angle)
            self.driver.set_pwm(joint, 0, duty)
        else:
            # Sweep slowly
            step = 1 if target_angle > start_angle else -1
            for a in range(int(start_angle), int(target_angle) + step, step):
                duty = self._angle_to_duty(a)
                self.driver.set_pwm(joint, 0, duty)
                time.sleep(speed)
                
        self.current_positions[joint] = target_angle

    def relax(self):
        """Kills power to all servos"""
        for i in range(6):
            self.driver.set_pwm(i, 0, 0)
        print("Arm relaxed.")

    def center(self, speed=0.01):
        """Moves all joints to 90 degrees safely"""
        for joint in range(6):
            min_a, max_a = self.limits[joint]
            safe_center = max(min_a, min(90, max_a))
            self.move(joint, safe_center, speed)
            
    def home(self, speed=0.01):
        """Moves all joints to the safe reset state: [90, 90, 0, 145, 80, 45]"""
        home_angles = {
            self.BASE: 90, self.ROTARY: 90, self.ELBOW: 0,
            self.WRIST: 145, self.UP_DOWN: 80, self.CLAW: 45
        }
        for joint, angle in home_angles.items():
            self.move(joint, angle, speed)
        print("Arm is in Home/Reset state.")
```

### B. Communication Server: `main.py`

This is the startup script running on the ESP32. It initializes the robot arm to its safe home position and sets up a non-blocking poll loop to parse incoming serial commands in real time.

```python
import sys
import uselect
import time
from robot_arm import RobotArm

# Initialize the arm and go to the safe home position immediately
arm = RobotArm()
arm.home(speed=0.01)

# Set up non-blocking serial read from USB (sys.stdin)
poll = uselect.poll()
poll.register(sys.stdin, uselect.POLLIN)

# Clear any garbage in the serial buffer
while poll.poll(0):
    sys.stdin.read(1)

print("READY")

while True:
    events = poll.poll(10) # 10ms timeout for fast loop
    if events:
        line = sys.stdin.readline().strip()
        
        if line == '<HOME>':
            arm.home(speed=0.02)
        elif line == '<RELAX>':
            arm.relax()
        elif line.startswith('<') and line.endswith('>'):
            try:
                parts = line[1:-1].split(',')
                if len(parts) == 6:
                    b, r, e, w, u, c = [int(p) for p in parts]
                    
                    # Ensure instant mirroring with safety constraints applied in the move() method
                    arm.move(arm.BASE, b, speed=0)
                    arm.move(arm.ROTARY, r, speed=0)
                    arm.move(arm.ELBOW, e, speed=0)
                    arm.move(arm.WRIST, w, speed=0)
                    arm.move(arm.UP_DOWN, u, speed=0)
                    arm.move(arm.CLAW, c, speed=0)
            except Exception:
                # Silently catch malformed strings so the script never crashes
                pass
```

### C. Emergency Stop: `kill.py`

In an emergency, safety is critical. Instead of waiting for a high-level response, we execute an instant low-level direct write to the PCA9685 registers over the I2C bus. This disables the oscillator and clears all PWM duty cycles, dropping all arm torque immediately.

```python
from machine import I2C, Pin

try:
    # Initialize connection to the PCA9685 chip
    i2c = I2C(0, scl=Pin(22), sda=Pin(21))
    
    # 1. Write \x10 to register 0xFD (ALL_LED_OFF_H)
    # This turns on bit 4 of the High ALL_LED_OFF register, activating FULL-OFF on all 16 channels
    i2c.writeto_mem(0x40, 0xFD, b'\x10')
    
    # 2. Write \x10 to register 0x00 (MODE1)
    # This turns on the SLEEP bit (bit 4) of Mode Register 1, shutting down the internal oscillator
    i2c.writeto_mem(0x40, 0x00, b'\x10')
    
    print("PCA9685 sleep registered, PWM outputs cut off successfully.")
except Exception as e:
    print("Failed to execute emergency shutdown:", e)
```

---

## 3. Communication Protocol

The PC streams movements to the ESP32 using a simple, high-frequency, structured ASCII text format over the USB virtual COM port.

### Packet Format
`"<b,r,e,w,u,c>\n"`

The parameters correspond to:
- `b`: Base servo angle (`0` to `180` degrees)
- `r`: Rotary joint angle (`0` to `180` degrees)
- `e`: Elbow joint angle (`0` to `180` degrees)
- `w`: Wrist joint angle (`0` to `180` degrees)
- `u`: Up-down pitch joint angle (`0` to `180` degrees)
- `c`: Claw gripper clamp angle (`0` to `90` degrees)

*Example mirror packet:*
```text
<90,90,45,145,80,30>
```

### Handshake and Directives
- **`READY`**: The ESP32 prints `READY\n` once boot is complete and it is ready to receive coordinate streams.
- **`<HOME>`**: Triggers a safe, smooth sweep returning the arm to the ideal rest state: `[90, 90, 0, 145, 80, 45]`.
- **`<RELAX>`**: Shuts off PWM duty cycles on all channels so that operators can adjust the arm positions manually without fighting servo magnetic resistance.

### Protocol Robustness & Crash Immunity
Because high-frequency serial streams are prone to cable vibration, packet truncation, or electrical noise, the ESP32 server implements strict packet hygiene:
- Input characters are compiled until a newline `\n` is read.
- The string must begin with `<` and terminate with `>`.
- The internal segment count must be exactly 6.
- All parsed coordinates are converted within a `try/except` guard. If any cast fails or a value is corrupted, the entire packet is discarded instantly, and the listener safely continues to the next cycle without crashing.

---

## 4. Reliable Upload System

The ESP32 execution environment can be challenging to manage over raw USB since `main.py` runs on startup, hijacking standard input (`sys.stdin`) for movement tracking. Sending files during active execution would cause input collisions.

To solve this, we use a PC-side utility script `upload_via_repl.py`. This script bypasses the serial listener by forcing a hardware reset, dropping into the MicroPython interactive prompt (REPL), transferring source files line-by-line, and rebooting.

### Upload Workflow

```text
+-------------------+      1. Toggle DTR/RTS      +-------------------+
|                   | --------------------------> |                   |
|                   |                             |   ESP32 Board     |
|   PC Controller   |      2. Spam Ctrl+C         |   Reboots and     |
|                   | --------------------------> |   Drops to REPL   |
| (upload_via_repl) |                             |                   |
|                   |   3. Write files line-by-line|                  |
|                   | --------------------------> | Writes flash memory|
|                   |                             |                   |
|                   |      4. machine.reset()     |   Executes new    |
|                   | --------------------------> |   main.py loop    |
+-------------------+                             +-------------------+
```

1. **Hardware Reboot**: Toggles the DTR (Data Terminal Ready) and RTS (Request To Send) serial lines to force a clean, cold start.
2. **Interrupt Main execution**: Spams Ctrl+C (`\x03`) immediately post-boot. This interrupts the MicroPython interpreter before it can enter the blocking loop of `main.py`, falling back to the serial interactive prompt.
3. **Chunk-Safe Transfer**: 
   - MicroPython has limited hardware serial buffers. Sending entire source files at once will overflow input channels and drop characters.
   - The script opens the target file path in write mode (`f = open('filename.py', 'w')`).
   - Source code is written line-by-line. All backslashes and single-quotes are escaped (`\\`, `\'`) and sent across with a stable 20ms delay.
   - Once complete, `f.close()` is written to save the file.
4. **Soft Reboot**: Sends `import machine; machine.reset()` to reboot the ESP32 and resume runtime operation.

### Deployment Tool Implementation (`upload_via_repl.py`)

```python
import serial
import time
import sys

def upload_file(ser, local_path, remote_path):
    print(f"Reading local file: {local_path}")
    with open(local_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"Uploading to remote file on ESP32: {remote_path}")
    # Open the file for writing on ESP32
    ser.write(f"f = open('{remote_path}', 'w')\r\n".encode())
    time.sleep(0.5)
    
    # Write the file line by line to avoid serial buffer overflow
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # Escape single quotes and backslashes
        escaped_line = line.replace('\\', '\\\\').replace("'", "\\'")
        cmd = f"f.write('{escaped_line}\\n')\r\n"
        ser.write(cmd.encode('utf-8'))
        time.sleep(0.02)  # small delay for stability
        if i % 20 == 0:
            print(f"  Sent {i}/{len(lines)} lines...")
            
    ser.write(b"f.close()\r\n")
    time.sleep(0.5)
    print(f"Successfully finished uploading {remote_path}!")

try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    
    # Force hardware reset by pulsing DTR/RTS lines
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setRTS(False)
    time.sleep(0.1)
    
    print("Waiting 1.5 seconds for ESP32 boot & main.py to print READY...")
    time.sleep(1.5)
    
    # Read boot log output
    boot_output = ser.read_all()
    print("Boot Output:", boot_output)
    
    # Spam Ctrl+C to abort active scripts and drop into interactive REPL
    print("Sending Ctrl+C to stop main.py...")
    ser.write(b'\r\x03\x03\x03')
    time.sleep(0.5)
        
    ser.reset_input_buffer()
    
    # Verify REPL connection is active
    ser.write(b"print('REPL_CONNECTED')\r\n")
    time.sleep(0.5)
    out = ser.read_all().decode(errors='ignore')
    
    if "REPL_CONNECTED" in out:
        print("REPL connection verified!")
        
        # Upload robot_arm.py
        upload_file(ser, "D:/arm/arm_control/robot_arm.py", "robot_arm.py")
        
        # Upload main.py
        upload_file(ser, "D:/arm/arm_control/main.py", "main.py")
        
        # Reset the board to run the new main.py loop
        print("Resetting ESP32 to execute the new code...")
        ser.write(b"import machine; machine.reset()\r\n")
        time.sleep(1)
        print("ESP32 successfully booted and is now running main.py.")
    else:
        print("Could not verify REPL. Please try again.")
        print("Raw output:", out)
        
    ser.close()
except Exception as e:
    print("Error:", e)
```
