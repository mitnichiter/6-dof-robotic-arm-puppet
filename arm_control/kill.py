from machine import I2C, Pin
import time

def kill_servos():
    # Setup I2C
    i2c = I2C(0, scl=Pin(22), sda=Pin(21))
    
    try:
        # The PCA9685 has a special register (0xFD) to turn ALL channels OFF immediately.
        # Writing 0x10 to register 0xFD sets the "Full OFF" bit.
        i2c.writeto_mem(0x40, 0xFD, b'\x10')
        
        # Also put the chip to sleep (Register 0x00, bit 4)
        i2c.writeto_mem(0x40, 0x00, b'\x10')
        print("SUCCESS: Sent KILL command to all servos. The driver board is asleep.")
    except Exception as e:
        print("ERROR: Could not communicate with driver board.", e)

kill_servos()
