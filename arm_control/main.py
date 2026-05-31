import sys
import uselect
import time
from robot_arm import RobotArm

# Initialize the arm and go to the safe home position immediately
arm = RobotArm()
arm.home(speed=0.01)

# Set up non-blocking serial read from USB (sys.stdin)
poll = uselect.poll()
poll.register(sys.stdin, uselect.POLLIN)

# Clear any garbage in the serial buffer
while poll.poll(0):
    sys.stdin.read(1)

print("READY")

while True:
    events = poll.poll(10) # 10ms timeout for fast loop
    if events:
        line = sys.stdin.readline().strip()
        
        if line == '<HOME>':
            arm.home(speed=0.02)
        elif line == '<RELAX>':
            arm.relax()
        elif line.startswith('<') and line.endswith('>'):
            try:
                parts = line[1:-1].split(',')
                if len(parts) == 6:
                    b, r, e, w, u, c = [int(p) for p in parts]
                    
                    # Ensure instant mirroring with safety constraints applied in the move() method
                    arm.move(arm.BASE, b, speed=0)
                    arm.move(arm.ROTARY, r, speed=0)
                    arm.move(arm.ELBOW, e, speed=0)
                    arm.move(arm.WRIST, w, speed=0)
                    arm.move(arm.UP_DOWN, u, speed=0)
                    arm.move(arm.CLAW, c, speed=0)
            except Exception:
                # Silently catch malformed strings so the script never crashes
                pass
