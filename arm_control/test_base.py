from machine import I2C, Pin
import time
import ustruct

class SimplePCA9685:
    def __init__(self, i2c, address=0x40):
        self.i2c = i2c
        self.address = address
        self.i2c.writeto_mem(self.address, 0x00, b'\x00') # Wake up
        
        # Set frequency to 50Hz for standard servos
        # prescale = int(25000000.0 / 4096.0 / 50 - 0.5) = 121
        self.i2c.writeto_mem(self.address, 0x00, b'\x10') # Sleep
        self.i2c.writeto_mem(self.address, 0xFE, bytes([121])) # Prescale
        self.i2c.writeto_mem(self.address, 0x00, b'\x00') # Wake
        time.sleep_us(500)
        self.i2c.writeto_mem(self.address, 0x00, b'\xa1') # Auto-increment
        
    def set_pwm(self, channel, on, off):
        data = ustruct.pack('<HH', on, off)
        self.i2c.writeto_mem(self.address, 0x06 + 4 * channel, data)

    def set_angle(self, channel, angle):
        # Maps 0-180 degrees to PWM duty cycle
        # min_duty (0 deg) = 102 (out of 4096)
        # max_duty (180 deg) = 512 (out of 4096)
        min_duty = 102
        max_duty = 512
        duty = int(min_duty + (max_duty - min_duty) * (angle / 180.0))
        self.set_pwm(channel, 0, duty)

    def turn_off(self, channel):
        # A duty cycle of 0 turns off the signal to the servo
        self.set_pwm(channel, 0, 0)

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
pca = SimplePCA9685(i2c)

def test_motor(channel):
    print(f"Initializing Channel {channel} to 90 degrees (center)...")
    pca.set_angle(channel, 90)
    time.sleep(2)
    
    print("Sweeping slowly to 60 degrees...")
    for a in range(90, 59, -1):
        pca.set_angle(channel, a)
        time.sleep(0.05)
    time.sleep(1)
    
    print("Sweeping slowly to 120 degrees...")
    for a in range(60, 121, 1):
        pca.set_angle(channel, a)
        time.sleep(0.05)
    time.sleep(1)
    
    print("Returning to center (90)...")
    for a in range(120, 89, -1):
        pca.set_angle(channel, a)
        time.sleep(0.05)
    time.sleep(1)

# Test the base motor (Channel 0)
test_motor(0)

# Turn off the signal so the motor doesn't strain against resistance
pca.turn_off(0)
print("Test complete. Motor signal turned off.")
