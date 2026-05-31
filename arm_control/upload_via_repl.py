import serial
import time
import sys

def upload_file(ser, local_path, remote_path):
    print(f"Reading local file: {local_path}")
    with open(local_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"Uploading to remote file on ESP32: {remote_path}")
    # Prepare the commands
    # Open the file for writing on ESP32
    ser.write(f"f = open('{remote_path}', 'w')\r\n".encode())
    time.sleep(0.5)
    
    # We will write the file line by line to avoid serial buffer overflow
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # We need to escape single quotes and backslashes
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
    
    # Force hardware reset exactly as tested in step 25
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setRTS(False)
    time.sleep(0.1)
    
    print("Waiting 1.5 seconds for ESP32 boot & main.py to print READY...")
    time.sleep(1.5)
    
    # Read anything printed during boot
    boot_output = ser.read_all()
    print("Boot Output:", boot_output)
    
    # Spam Ctrl+C to abort the running main.py and drop into REPL
    print("Sending Ctrl+C to stop main.py...")
    ser.write(b'\r\x03\x03\x03')
    time.sleep(0.5)
        
    ser.reset_input_buffer()
    
    # Verify REPL is active by writing a print statement
    ser.write(b"print('REPL_CONNECTED')\r\n")
    time.sleep(0.5)
    out = ser.read_all().decode(errors='ignore')
    
    if "REPL_CONNECTED" in out:
        print("REPL connection verified!")
        
        # Upload robot_arm.py
        upload_file(ser, "D:/arm/arm_control/robot_arm.py", "robot_arm.py")
        
        # Upload main.py
        upload_file(ser, "D:/arm/arm_control/main.py", "main.py")
        
        # Reset the board to run the new main.py
        print("Resetting ESP32 to execute the new code...")
        ser.write(b"import machine; machine.reset()\r\n")
        time.sleep(1)
        print("ESP32 successfully booted and is now running main.py with the new home state.")
    else:
        print("Could not verify REPL. Please try again.")
        print("Raw output:", out)
        
    ser.close()
except Exception as e:
    print("Error:", e)
