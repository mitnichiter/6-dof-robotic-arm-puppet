import cv2
import sys

print("========================================")
print("     WINDOWS CAMERA INDEX SCANNER       ")
print("========================================")
print("Testing indices 0, 1, 2, 3 using DirectShow...")

for index in range(4):
    # Use cv2.CAP_DSHOW for Windows DirectShow backend (faster loading and better USB matching)
    cap = cv2.VideoCapture(index + cv2.CAP_DSHOW)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f" -> Index {index}: ACTIVE (Working)")
            # Show a test frame for 2 seconds to let the user see which camera it is!
            window_name = f"Camera Index {index} (DirectShow)"
            cv2.imshow(window_name, frame)
            cv2.waitKey(2000) # wait 2 seconds
            cv2.destroyWindow(window_name)
        else:
            print(f" -> Index {index}: Opened, but failed to read frame.")
        cap.release()
    else:
        print(f" -> Index {index}: OFFLINE")

print("\nScan complete. Please tell me which index was your external USB camera!")
input("Press Enter to exit...")
cv2.destroyAllWindows()
