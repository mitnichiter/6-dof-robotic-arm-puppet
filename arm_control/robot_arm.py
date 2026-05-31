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
        
        # Absolute Safety Limits based on latest calibration and user state
        self.limits = {
            self.BASE: (0, 180),
            self.ROTARY: (0, 180),   # ALLOWING FULL RANGE FOR TESTING
            self.ELBOW: (0, 180),
            self.WRIST: (0, 180),
            self.UP_DOWN: (0, 180),
            self.CLAW: (0, 90)       # <-- FIXED: Restricted to 0-90 as requested
        }
        
        # Track current positions. Initialized to the new Ideal Reset State.
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
        # Order: BASE, ROTARY, ELBOW, WRIST, UP_DOWN, CLAW
        home_angles = {
            self.BASE: 90, self.ROTARY: 90, self.ELBOW: 0,
            self.WRIST: 145, self.UP_DOWN: 80, self.CLAW: 45
        }
        for joint, angle in home_angles.items():
            self.move(joint, angle, speed)
        print("Arm is in Home/Reset state.")
