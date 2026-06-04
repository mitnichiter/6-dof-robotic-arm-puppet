import cv2
import mediapipe as mp
import serial
import time
import math
import pyaudiowpatch as pyaudio
import numpy as np
import threading

# =========================================================================================
# VISION PUPPET: ORGANIC, INTELLIGENT AUDIO DANCE
# 
# Advancements Implemented:
# 1. Audio Envelopes: Uses Fast Attack / Slow Decay on audio bands so the arm "hits" on 
#    the beat but glides naturally out of it, exactly like human muscle momentum.
# 2. Long-Term Energy: Tracks the overall energy of the song. During a drop, movements 
#    become massive. During a bridge/intro, movements are tight and slow.
# 3. Dynamic Time (Phase Modulation): The internal "clock" speeds up when the song is loud.
# =========================================================================================

# --- AUDIO THREAD (FFT & ENVELOPES) ---
audio_data = {
    'bass_env': 0.0, 'mid_env': 0.0, 'treb_env': 0.0, 
    'energy': 0.0, 
    'volume': 0.0
}

def audio_listener():
    try:
        # Use PyAudioWPatch to hook directly into Windows WASAPI Loopback (ignores Stereo Mix!)
        p = pyaudio.PyAudio()
        
        # Find default WASAPI Loopback device
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        
        if not default_speakers["isLoopbackDevice"]:
            # Find the loopback variant of the default speaker
            for loopback in p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    break
                    
        print(f"SUCCESS: Bound to WASAPI Loopback: {default_speakers['name']}")
        
        CHUNK = 1024
        RATE = int(default_speakers["defaultSampleRate"])

        stream = p.open(format=pyaudio.paFloat32,
                        channels=default_speakers["maxInputChannels"],
                        rate=RATE,
                        frames_per_buffer=CHUNK,
                        input=True,
                        input_device_index=default_speakers["index"])

        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                # Convert raw bytes to numpy array
                audio_np = np.frombuffer(data, dtype=np.float32)
                
                # If stereo, mix to mono
                if default_speakers["maxInputChannels"] > 1:
                    mono = np.mean(audio_np.reshape(-1, default_speakers["maxInputChannels"]), axis=1)
                else:
                    mono = audio_np

                if np.max(np.abs(mono)) < 0.001:
                    raw_vol = 0.0; raw_b = 0.0; raw_m = 0.0; raw_t = 0.0
                else:
                    fft_data = np.abs(np.fft.rfft(mono))
                    
                    # Frequency Bins (~43Hz per bin at 44.1kHz)
                    b = np.mean(fft_data[1:6]) if len(fft_data) > 6 else 0      
                    m = np.mean(fft_data[6:46]) if len(fft_data) > 46 else 0     
                    t = np.mean(fft_data[46:256]) if len(fft_data) > 256 else 0 
                    
                    # Normalize & Boost for raw WASAPI float data
                    raw_b = min(1.0, b * 0.15)    
                    raw_m = min(1.0, m * 0.15)      
                    raw_t = min(1.0, t * 0.25) 
                    raw_vol = min(1.0, np.sqrt(np.mean(mono**2)) * 3)
                
                # ENVELOPE FILTERING
                decay = 0.85 
                audio_data['bass_env'] = raw_b if raw_b > audio_data['bass_env'] else audio_data['bass_env'] * decay
                audio_data['mid_env'] = raw_m if raw_m > audio_data['mid_env'] else audio_data['mid_env'] * decay
                audio_data['treb_env'] = raw_t if raw_t > audio_data['treb_env'] else audio_data['treb_env'] * 0.70 
                audio_data['volume'] = raw_vol
                audio_data['energy'] = (0.02 * raw_vol) + (0.98 * audio_data['energy'])

            except IOError:
                pass # Ignore stream underflows
                
    except Exception as e:
        print("Audio listener CRITICAL error:", e)

threading.Thread(target=audio_listener, daemon=True).start()

# --- SMOOTHING FILTER ---
class ButterSmoothFilter:
    def __init__(self, initial_val):
        self.val = initial_val

    def update(self, target):
        delta = abs(target - self.val)
        alpha = max(0.02, min(0.35, 0.02 + (delta / 100.0) * 0.33))
        self.val = (alpha * target) + ((1.0 - alpha) * self.val)
        return self.val

def map_range(x, in_min, in_max, out_min, out_max):
    val = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return max(min(out_min, out_max), min(max(out_min, out_max), val))

def is_fist(landmarks):
    def is_curled(tip, mcp, wrist):
        return math.hypot(tip.x - wrist.x, tip.y - wrist.y) < math.hypot(mcp.x - wrist.x, mcp.y - wrist.y)
    lms = landmarks.landmark
    wrist = lms[mp_hands.HandLandmark.WRIST]
    index_down = is_curled(lms[mp_hands.HandLandmark.INDEX_FINGER_TIP], lms[mp_hands.HandLandmark.INDEX_FINGER_MCP], wrist)
    middle_down = is_curled(lms[mp_hands.HandLandmark.MIDDLE_FINGER_TIP], lms[mp_hands.HandLandmark.MIDDLE_FINGER_MCP], wrist)
    ring_down = is_curled(lms[mp_hands.HandLandmark.RING_FINGER_TIP], lms[mp_hands.HandLandmark.RING_FINGER_MCP], wrist)
    pinky_down = is_curled(lms[mp_hands.HandLandmark.PINKY_TIP], lms[mp_hands.HandLandmark.PINKY_MCP], wrist)
    return index_down and middle_down and ring_down and pinky_down

# --- SYSTEM SETUP ---
try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    time.sleep(3)
    ser.reset_input_buffer()
except Exception as e:
    print(f"Failed to connect to ESP32: {e}")
    exit()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.75, min_tracking_confidence=0.75)
mp_draw = mp.solutions.drawing_utils

# Open external USB Webcam (Index 1) using DirectShow, fallback to internal (Index 0)
cap = cv2.VideoCapture(1 + cv2.CAP_DSHOW)
if not cap.isOpened():
    print("USB Webcam (Index 1) not found. Falling back to internal camera (Index 0).")
    cap = cv2.VideoCapture(0 + cv2.CAP_DSHOW)

# --- STATE VARIABLES ---
HOME_STATE = [90, 90, 0, 145, 80, 45]
smoothers = [ButterSmoothFilter(val) for val in HOME_STATE]
last_send_time = time.time()
no_hand_time = time.time()

dance_mode = False
arm_frozen = False
dance_time = 0.0 # Dynamic internal clock

print("\n--- ORGANIC AUDIO-REACTIVE SYSTEM ACTIVE ---")
print("-> Press 'd' on your keyboard to TURN ON/OFF Dance Mode.")
print("-> Make a FIST ✊ to FREEZE the arm in place (Clutch).\n")

try:
    last_frame_time = time.time()
    while cap.isOpened():
        success, image = cap.read()
        if not success: continue

        current_time = time.time()
        dt = current_time - last_frame_time
        last_frame_time = current_time

        image = cv2.flip(image, 1) 
        results = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        target_angles = list(HOME_STATE)
        hand_detected = False

        if results.multi_hand_landmarks:
            hand_detected = True
            no_hand_time = current_time
            hand_landmarks = results.multi_hand_landmarks[0]
            mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            if is_fist(hand_landmarks):
                arm_frozen = True
            else:
                arm_frozen = False
            
            if arm_frozen and not dance_mode:
                cv2.putText(image, "POSE HOLD (CLUTCH) ACTIVE", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            elif not dance_mode:
                # --- DIRECT MAPPING TRACKING ---
                lm0 = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                lm9 = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                center_x, center_y = lm9.x, lm9.y
                palm_size = math.hypot(lm9.x - lm0.x, lm9.y - lm0.y)
                
                target_angles[0] = map_range(center_x, 0.1, 0.9, 180, 0)
                target_angles[4] = map_range(center_y, 0.1, 0.9, 20, 160)
                target_angles[1] = map_range(palm_size, 0.05, 0.25, 145, 60)
                target_angles[2] = map_range(palm_size, 0.05, 0.25, 0, 150)
                
                dx = lm9.x - lm0.x
                dy = lm9.y - lm0.y
                angle_deg = math.degrees(math.atan2(dy, dx))
                target_angles[3] = map_range(angle_deg, -135, -45, 190, 100)
                
                thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                pinch_dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
                target_angles[5] = map_range(pinch_dist, 0.03, 0.10, 0, 90)

        # --- ORGANIC DANCE ENGINE ---
        if dance_mode:
            cv2.putText(image, "ORGANIC DANCE ENGINE \u266B", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
            
            b = audio_data['bass_env']
            m = audio_data['mid_env']
            t = audio_data['treb_env']
            energy = audio_data['energy'] # 0.0 to ~1.0
            
            # Print debug data to terminal
            print(f"Dance -> Energy:{energy:.2f} Bass:{b:.2f} Mid:{m:.2f} Treb:{t:.2f}")
            
            # Phase Modulation: Time moves faster when the song is highly energetic!
            # Normal speed is dt*1.0. During a drop, it can speed up to dt*2.5
            dance_time += dt * (1.0 + (energy * 1.5))
            
            # 1. THE GROOVE (Base)
            # Gentle sway that gets WIDER during high energy parts of the song
            sway_width = 15 + (energy * 45) # Sways 15 deg in quiet parts, up to 60 deg in loud parts
            target_angles[0] = 90 + math.sin(dance_time * 1.2) * sway_width
            
            # 2. THE HIT (Rotary & Elbow)
            # Uses the Envelope! It will strike fast on the beat, and glide back slowly, mimicking real muscle.
            # Strikes are deeper when the overall energy is high.
            strike_depth = b * (30 + (energy * 55)) 
            target_angles[1] = 145 - strike_depth       # Lean forward
            target_angles[2] = 0 + (strike_depth * 1.6) # Drop elbow
            
            # 3. THE FLOURISH (Wrist)
            # Organic overlapping sine waves. Rotates more aggressively during high energy.
            wrist_spin = 15 + (energy * 40)
            target_angles[3] = 145 + (math.sin(dance_time * 2.1) * wrist_spin) + (math.cos(dance_time * 0.8) * 10)
            
            # 4. THE BOUNCE (Up/Down)
            # Bobs up and down rhythmically, amplitude dictated by Mid-range envelope
            target_angles[4] = 80 + math.cos(dance_time * 3.5) * (15 + (m * 45))
            
            # 5. THE SNAP (Claw)
            # Snaps exactly on crisp treble hits
            target_angles[5] = 90 if t > 0.5 else (45 if energy > 0.5 else 0)

        # Apply Smooth Filtering
        current_smoothed = []
        for i in range(6):
            if arm_frozen and not dance_mode:
                current_smoothed.append(smoothers[i].s if hasattr(smoothers[i], 's') else smoothers[i].val)
            elif not hand_detected and not dance_mode and current_time - no_hand_time > 1.5:
                # Organic Breathing (Idle)
                t_idle = current_time
                idle_target = HOME_STATE[i]
                if i in [1, 4]: 
                    idle_target += (math.sin(t_idle * 1.2) * 3) + (math.cos(t_idle * 0.5) * 1.5)
                elif i == 3: 
                    idle_target += math.sin(t_idle * 0.8) * 2
                current_smoothed.append(smoothers[i].update(idle_target))
                cv2.putText(image, "ORGANIC IDLE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 150, 0), 2)
            else:
                current_smoothed.append(smoothers[i].update(target_angles[i]))
                
        # Send Commands @ ~30 FPS
        if current_time - last_send_time > 0.03:
            b_val, r_val, e_val, w_val, u_val, c_val = [int(a) for a in current_smoothed]
            cmd = f"<{b_val},{r_val},{e_val},{w_val},{u_val},{c_val}>\n"
            ser.write(cmd.encode('utf-8'))
            last_send_time = current_time
            if hand_detected and not arm_frozen and not dance_mode:
                cv2.putText(image, "DIRECT TRACKING", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('Robot Arm AUDIO PUPPET', image)
        
        # Keyboard commands
        key = cv2.waitKey(5) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('d'):
            dance_mode = not dance_mode
            print(f"Keyboard Trigger -> Dance Mode: {'ON' if dance_mode else 'OFF'}")

except KeyboardInterrupt:
    pass
finally:
    try:
        ser.write(b"<HOME>\n")
        time.sleep(1.5)
        ser.write(b"<RELAX>\n")
        ser.close()
    except: pass
    cap.release()
    cv2.destroyAllWindows()
