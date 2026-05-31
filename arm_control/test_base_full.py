from machine import I2C, Pin
import time
import ustruct

class SimplePCA9685:
    def __init__(self, i2c, address=0x40):
        self.i2c = i2c
        self.address = address
        self.i2c.writeto_mem(self.address, 0x00, b'\x00') # Wake up
        
        # Set frequency to 50Hz for standard servos
        self.i2c.writeto_mem(self.address, 0x00, b'\x10') # Sleep
        self.i2c.writeto_mem(self.address, 0xFE, bytes([121])) # Prescale
        self.i2c.writeto_mem(self.address, 0x00, b'\x00') # Wake
        time.sleep_us(500)
        self.i2c.writeto_mem(self.address, 0x00, b'\xa1') # Auto-increment
        
    def set_pwm(self, channel, on, off):
        data = ustruct.pack('<HH', on, off)
        self.i2c.writeto_mem(self.address, 0x06 + 4 * channel, data)

    def set_angle(self, channel, angle):
        # Constrain angle safely
        if angle < 0: angle = 0
        if angle > 180: angle = 180
        
        min_duty = 102
        max_duty = 512
        duty = int(min_duty + (max_duty - min_duty) * (angle / 180.0))
        self.set_pwm(channel, 0, duty)

    def turn_off(self, channel):
        self.set_pwm(channel, 0, 0)

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
pca = SimplePCA9685(i2c)

def test_full_range(channel):
    print(f"\n--- Testing Channel {channel} ---")
    print("Moving to Center (90)...")
    pca.set_angle(channel, 90)
    time.sleep(2)
    
    print("Sweeping slowly towards 0 degrees...")
    for a in range(90, -1, -1):
        pca.set_angle(channel, a)
        time.sleep(0.03) # slightly faster sweep
    time.sleep(1)
    
    print("Sweeping slowly towards 180 degrees...")
    for a in range(0, 181, 1):
        pca.set_angle(channel, a)
        time.sleep(0.03)
    time.sleep(1)
    
    print("Returning to Center (90)...")
    for a in range(180, 89, -1):
        pca.set_angle(channel, a)
        time.sleep(0.03)
    time.sleep(1)
    
    pca.turn_off(channel)
    print(f"Channel {channel} Test Complete and signal killed.")

# Test Base (Channel 0) to its full 0-180 limits
test_full_range(0)
