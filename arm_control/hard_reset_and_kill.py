import serial
import time

try:
    print("Forcing hardware reset on ESP32 (COM5)...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    
    # Toggle DTR/RTS to force hardware reset
    ser.dtr = False
    ser.rts = True
    time.sleep(0.1)
    ser.dtr = True
    ser.rts = False
    time.sleep(0.1)
    ser.dtr = False
    
    print("Waiting for boot...")
    time.sleep(1)
    
    # Spam Ctrl+C during boot to interrupt main.py before it locks stdin
    print("Spamming Ctrl+C to abort main.py...")
    for _ in range(10):
        ser.write(b'\r\x03')
        time.sleep(0.1)
        
    ser.reset_input_buffer()
    
    # Check if we got to REPL
    ser.write(b"print('REPL_READY')\r\n")
    time.sleep(0.5)
    out = ser.read_all().decode(errors='ignore')
    print("Output:", out)
    
    if "REPL_READY" in out:
        print("Successfully interrupted main.py! Now sending kill signals to PCA9685...")
        # Send raw I2C kill commands
        ser.write(b"from machine import I2C, Pin\r\n")
        time.sleep(0.1)
        ser.write(b"try:\r\n")
        ser.write(b"    i2c = I2C(0, scl=Pin(22), sda=Pin(21))\r\n")
        ser.write(b"    i2c.writeto_mem(0x40, 0xFD, b'\\x10')\r\n")
        ser.write(b"    i2c.writeto_mem(0x40, 0x00, b'\\x10')\r\n")
        ser.write(b"    print('I2C_KILLED_SUCCESSFULLY')\r\n")
        ser.write(b"except Exception as e:\r\n")
        ser.write(b"    print('I2C_ERROR:', e)\r\n")
        ser.write(b"\r\n")
        
        time.sleep(1)
        out2 = ser.read_all().decode(errors='ignore')
        print("Kill Output:", out2)
        
        # Also remove main.py using python os module so it doesn't run again
        ser.write(b"import os; os.remove('main.py')\r\n")
        time.sleep(0.5)
        print("Removed main.py from ESP32.")
    else:
        print("Failed to reach REPL. The board might need a manual reset button press.")

    ser.close()
except Exception as e:
    print(f"Error: {e}")
