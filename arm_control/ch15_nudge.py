import customtkinter as ctk
import serial
import time

# --- SERIAL SETUP ---
try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    # Prevent Windows reset
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setRTS(False)
    time.sleep(0.1)
    
    print("Waiting 1.5s for boot...")
    time.sleep(1.5)
    ser.write(b'\r\x03\x03\x03')
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    # Initialize PCA9685 driver directly to bypass robot_arm.py limits
    ser.write(b'from machine import I2C, Pin\r\n')
    time.sleep(0.1)
    ser.write(b'import ustruct\r\n')
    time.sleep(0.1)
    ser.write(b'class PCA9685:\r\n')
    ser.write(b'    def __init__(self, i2c):\r\n')
    ser.write(b'        self.i2c = i2c\r\n')
    ser.write(b'        self.i2c.writeto_mem(0x40, 0x00, b"\\x00")\r\n')
    ser.write(b'        self.i2c.writeto_mem(0x40, 0x00, b"\\x10")\r\n')
    ser.write(b'        self.i2c.writeto_mem(0x40, 0xFE, bytes([121]))\r\n')
    ser.write(b'        self.i2c.writeto_mem(0x40, 0x00, b"\\x00")\r\n')
    ser.write(b'        self.i2c.writeto_mem(0x40, 0x00, b"\\xa1")\r\n')
    ser.write(b'    def set_pwm(self, ch, duty):\r\n')
    ser.write(b'        self.i2c.writeto_mem(0x40, 0x06 + 4 * ch, ustruct.pack("<HH", 0, duty))\r\n')
    ser.write(b'\r\n')
    time.sleep(0.1)
    
    ser.write(b'i2c = I2C(0, scl=Pin(22), sda=Pin(21))\r\n')
    ser.write(b'driver = PCA9685(i2c)\r\n')
    time.sleep(0.5)
    print("Direct I2C control established!")
except Exception as e:
    print(f"Failed to connect: {e}")
    exit()

# State variable for Channel 15
current_angle = 90

def angle_to_duty(angle):
    min_duty = 102
    max_duty = 512
    angle = max(0, min(angle, 180))
    return int(min_duty + (max_duty - min_duty) * (angle / 180.0))

def update_servo():
    duty = angle_to_duty(current_angle)
    # Send direct hardware command to channel 15
    cmd = f"driver.set_pwm(15, {duty})\r\n"
    ser.write(cmd.encode())
    lbl_angle.configure(text=f"{current_angle}°")

def move_up():
    global current_angle
    current_angle = min(180, current_angle + 5)
    update_servo()

def move_down():
    global current_angle
    current_angle = max(0, current_angle - 5)
    update_servo()
    
def relax():
    ser.write(b"driver.set_pwm(15, 0)\r\n")

# --- GUI SETUP ---
app = ctk.CTk()
app.title("Channel 15 Nudge Tool")
app.geometry("300x250")
ctk.set_appearance_mode("dark")

ctk.CTkLabel(app, text="Channel 15 Control", font=("Arial", 18, "bold")).pack(pady=10)

lbl_angle = ctk.CTkLabel(app, text=f"{current_angle}°", font=("Arial", 32, "bold"), text_color="#00ff00")
lbl_angle.pack(pady=10)

btn_frame = ctk.CTkFrame(app, fg_color="transparent")
btn_frame.pack(pady=10)

btn_down = ctk.CTkButton(btn_frame, text="-5°", command=move_down, width=60, font=("Arial", 16, "bold"))
btn_down.pack(side="left", padx=10)

btn_up = ctk.CTkButton(btn_frame, text="+5°", command=move_up, width=60, font=("Arial", 16, "bold"))
btn_up.pack(side="left", padx=10)

ctk.CTkButton(app, text="Relax Motor 15", command=relax, fg_color="#c0392b", hover_color="#900000").pack(pady=20)

def on_closing():
    relax()
    ser.close()
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)

# Center it initially
update_servo()

app.mainloop()
