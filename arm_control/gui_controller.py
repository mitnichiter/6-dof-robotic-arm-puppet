import customtkinter as ctk
import serial
import time
import threading

# Initialize serial connection to ESP32
try:
    print("Connecting to ESP32 on COM5...")
    # Open serial port. Windows will toggle DTR/RTS and reset the ESP32.
    ser = serial.Serial('COM5', 115200, timeout=1)
    
    print("Waiting 2 seconds for ESP32 to finish booting...")
    time.sleep(2) # Crucial wait time!
    
    # Send Ctrl+C twice to stop any stuck scripts and enter REPL
    ser.write(b'\r\x03\x03') 
    time.sleep(0.5)
    
    # Clear any startup garbage from the serial buffer
    ser.reset_input_buffer()
    
    # Import library and initialize arm
    print("Initializing arm library on ESP32...")
    ser.write(b'from robot_arm import RobotArm\r\n')
    time.sleep(0.5)
    ser.write(b'arm = RobotArm()\r\n')
    time.sleep(0.5)
    
    # Print what the ESP32 replied to make sure it worked
    repl_output = ser.read_all().decode(errors='ignore')
    print(f"ESP32 Output: {repl_output}")
    print("Successfully connected and ready!")
except Exception as e:
    print(f"Failed to connect: {e}")
    print("Is the ESP32 plugged in and COM5 available?")
    exit()

def send_command(joint, angle):
    """Send the move command over Serial REPL"""
    cmd = f"arm.move({joint}, {int(angle)})\r\n"
    ser.write(cmd.encode('utf-8'))

def relax_arm():
    """Kills signal to stop twerking"""
    ser.write(b"arm.relax()\r\n")

# GUI Setup
app = ctk.CTk()
app.title("Robot Arm Control Panel")
app.geometry("500x650")
ctk.set_appearance_mode("dark")

lbl_title = ctk.CTkLabel(app, text="Pose the Arm", font=("Arial", 20, "bold"))
lbl_title.pack(pady=15)

# Joint constraints based on our tests
joints = [
    {"id": 0, "name": "0: Base", "min": 0, "max": 180, "val": 90},
    {"id": 1, "name": "1: Rotary", "min": 0, "max": 180, "val": 90},
    {"id": 2, "name": "2: Elbow", "min": 0, "max": 180, "val": 0},
    {"id": 3, "name": "3: Wrist", "min": 0, "max": 180, "val": 145},
    {"id": 4, "name": "4: Up/Down", "min": 0, "max": 180, "val": 80},
    {"id": 5, "name": "5: Claw", "min": 0, "max": 90, "val": 45},
]

sliders = {}

def slider_event(value, joint_id, label):
    val = int(value)
    label.configure(text=f"{val}°")
    send_command(joint_id, val)

# Create sliders
for j in joints:
    frame = ctk.CTkFrame(app)
    frame.pack(pady=10, padx=20, fill="x")
    
    lbl_name = ctk.CTkLabel(frame, text=j["name"], width=100, anchor="w", font=("Arial", 14))
    lbl_name.pack(side="left", padx=10)
    
    lbl_val = ctk.CTkLabel(frame, text=f"{j['val']}°", width=40, font=("Arial", 14, "bold"))
    lbl_val.pack(side="right", padx=10)
    
    slider = ctk.CTkSlider(frame, from_=j["min"], to=j["max"], number_of_steps=j["max"]-j["min"])
    slider.set(j["val"])
    slider.pack(side="left", fill="x", expand=True, padx=10)
    
    # Capture loop variables via default arguments
    slider.configure(command=lambda v, j_id=j["id"], l=lbl_val: slider_event(v, j_id, l))
    sliders[j["id"]] = slider

def print_reset_state():
    angles = [int(sliders[i].get()) for i in range(6)]
    print(f"\n--- IDEAL RESET STATE ---")
    print(f"[{angles[0]}, {angles[1]}, {angles[2]}, {angles[3]}, {angles[4]}, {angles[5]}]")
    lbl_status.configure(text=f"Reset State: {angles}", text_color="green")

# Buttons
btn_frame = ctk.CTkFrame(app, fg_color="transparent")
btn_frame.pack(pady=20)

btn_relax = ctk.CTkButton(btn_frame, text="Relax Motors\n(Stop Shaking)", command=relax_arm, 
                          fg_color="#c0392b", hover_color="#900000", font=("Arial", 14, "bold"))
btn_relax.pack(side="left", padx=10)

btn_save = ctk.CTkButton(btn_frame, text="Get Reset State\n(Print to Screen)", command=print_reset_state, 
                         fg_color="#27ae60", hover_color="#1e8449", font=("Arial", 14, "bold"))
btn_save.pack(side="right", padx=10)

lbl_status = ctk.CTkLabel(app, text="Ready. Move sliders to pose the arm in a balanced way.")
lbl_status.pack(pady=10)

# Make sure to close serial on exit
def on_closing():
    relax_arm()
    time.sleep(0.5)
    ser.close()
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()
