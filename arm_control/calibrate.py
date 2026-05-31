import serial
import time
import sys

print("========================================")
print("       ROBOT ARM CALIBRATION TOOL       ")
print("========================================")
try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    print("Waiting 2 seconds for ESP32 to boot...")
    time.sleep(2) 
    
    # Interrupt any running loops and clear buffer
    ser.write(b'\r\x03\x03')
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    # Initialize the library
    ser.write(b'from robot_arm import RobotArm\r\n')
    time.sleep(0.5)
    ser.write(b'arm = RobotArm()\r\n')
    time.sleep(0.5)
    print("Successfully connected and ready!")
except Exception as e:
    print(f"Error: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

joint_names = ["0: Base", "1: Rotary", "2: Elbow", "3: Wrist", "4: Up/Down", "5: Claw"]

def send_angle(joint, angle):
    cmd = f"arm.move_raw({joint}, {int(angle)})\r\n"
    ser.write(cmd.encode())

while True:
    print("\n-------------------------")
    for j in joint_names:
        print(f"  {j}")
    print("-------------------------")
    joint_in = input("Enter Joint ID to test (0-5) or 'q' to quit: ").strip()
    
    if joint_in.lower() == 'q':
        break
    
    try:
        joint_id = int(joint_in)
        if not (0 <= joint_id <= 5):
            print("Invalid joint ID.")
            continue
    except:
        print("Please enter a number 0-5.")
        continue
        
    print(f"\n--- Calibrating {joint_names[joint_id]} ---")
    print("Type an angle (0-180) and press Enter.")
    print("Tips:")
    print(" - Start at 90 (center).")
    print(" - Sneak up in small steps (e.g., 90, then 95, then 100).")
    print(" - Type 'r' to relax motors if it starts shaking.")
    print(" - Type 'b' to go back to joint selection.")
    
    while True:
        val = input(f"> Angle for {joint_names[joint_id]}: ").strip()
        if val.lower() == 'b':
            break
        if val.lower() == 'r':
            ser.write(b'arm.relax()\r\n')
            print(" -> Motors relaxed.")
            continue
        
        try:
            angle = int(val)
            if 0 <= angle <= 180:
                send_angle(joint_id, angle)
                print(f" -> Moved Joint {joint_id} to {angle} degrees")
            else:
                print("! Angle must be between 0 and 180.")
        except:
            print("! Invalid input. Enter a number, 'r', or 'b'.")

print("\nRelaxing arm and closing connection...")
ser.write(b'arm.relax()\r\n')
time.sleep(0.5)
ser.close()
print("Done. Goodbye!")
