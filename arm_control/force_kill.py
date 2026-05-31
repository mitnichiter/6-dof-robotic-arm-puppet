import serial
import time

try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    time.sleep(0.5)
    
    # Send Ctrl+C multiple times to interrupt any running loops
    print("Sending interrupts...")
    ser.write(b'\r\x03\x03\x03') 
    time.sleep(1)
    
    # Clear buffer
    ser.reset_input_buffer()
    
    # Send raw I2C kill commands directly through REPL
    print("Sending I2C kill commands...")
    ser.write(b"from machine import I2C, Pin\r\n")
    time.sleep(0.2)
    ser.write(b"i2c = I2C(0, scl=Pin(22), sda=Pin(21))\r\n")
    time.sleep(0.2)
    ser.write(b"try:\r\n")
    ser.write(b"    i2c.writeto_mem(0x40, 0xFD, b'\\x10')\r\n")
    ser.write(b"    i2c.writeto_mem(0x40, 0x00, b'\\x10')\r\n")
    ser.write(b"    print('KILLED')\r\n")
    ser.write(b"except Exception as e:\r\n")
    ser.write(b"    print('ERR:', e)\r\n")
    ser.write(b"\r\n")
    
    time.sleep(1)
    output = ser.read_all().decode(errors='ignore')
    print("ESP32 Response:")
    print(output)
    
    ser.close()
except Exception as e:
    print(f"Serial Error: {e}")
