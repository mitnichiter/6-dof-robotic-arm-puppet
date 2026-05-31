from robot_arm import RobotArm
import time

arm = RobotArm()

print("Setting all joints to 90 degrees one by one...")

# Doing this one by one prevents a massive power spike
# and lets you see exactly which joint is moving.

print("1. Base to 90 (Center)")
arm.move(arm.BASE, 90, speed=0)
time.sleep(1.5)

print("2. Rotary to 90 (Center)")
arm.move(arm.ROTARY, 90, speed=0)
time.sleep(1.5)

print("3. Elbow to 90 (Center)")
arm.move(arm.ELBOW, 90, speed=0)
time.sleep(1.5)

print("4. Up/Down to 90 (Center)")
arm.move(arm.UP_DOWN, 90, speed=0)
time.sleep(1.5)

print("5. Wrist to 90 (Center)")
arm.move(arm.WRIST, 90, speed=0)
time.sleep(1.5)

print("6. Claw to 90 (Center)")
arm.move(arm.CLAW, 90, speed=0)
time.sleep(1.5)

print("All joints are now at 90 degrees.")
print("Take a look at the physical arm. Does this look like a good 'Rest' position?")
