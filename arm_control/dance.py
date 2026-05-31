import serial
import time
import math
import pyaudiowpatch as pyaudio
import numpy as np
import threading
import random

# =========================================================================================
# THE CHOREOGRAPHER: INTELLIGENT AUDIO DANCE ENGINE (dance.py)
# 
# 1. State Machine: Randomly selects professional dance moves and holds them for N beats.
# 2. Keyframe Animation: Uses target snapping and dynamic easing for Pop & Lock effects.
# 3. Joint Isolation: Locks certain joints completely while snapping others (like a pro dancer).
# 4. Independent Audio Thread: Binds to Windows WASAPI for zero-latency audio tracking.
# =========================================================================================

# --- AUDIO THREAD (FFT & ENVELOPES) ---
audio_data = {'bass': 0.0, 'mid': 0.0, 'treb': 0.0, 'energy': 0.0, 'volume': 0.0}

def audio_listener():
    try:
        p = pyaudio.PyAudio()
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        
        if not default_speakers["isLoopbackDevice"]:
            for loopback in p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    break
                    
        print(f"SUCCESS: Audio Engine Bound to {default_speakers['name']}")
        
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
                audio_np = np.frombuffer(data, dtype=np.float32)
                if default_speakers["maxInputChannels"] > 1:
                    mono = np.mean(audio_np.reshape(-1, default_speakers["maxInputChannels"]), axis=1)
                else:
                    mono = audio_np

                if np.max(np.abs(mono)) < 0.001:
                    r_vol = 0.0; r_b = 0.0; r_m = 0.0; r_t = 0.0
                else:
                    fft_data = np.abs(np.fft.rfft(mono))
                    b = np.mean(fft_data[1:6]) if len(fft_data) > 6 else 0      
                    m = np.mean(fft_data[6:46]) if len(fft_data) > 46 else 0     
                    t = np.mean(fft_data[46:256]) if len(fft_data) > 256 else 0 
                    
                    # Boost for raw WASAPI float data
                    r_b = min(1.0, b * 0.15)    
                    r_m = min(1.0, m * 0.15)      
                    r_t = min(1.0, t * 0.25) 
                    r_vol = min(1.0, np.sqrt(np.mean(mono**2)) * 3)
                
                decay = 0.80 
                audio_data['bass'] = r_b if r_b > audio_data['bass'] else audio_data['bass'] * decay
                audio_data['mid'] = r_m if r_m > audio_data['mid'] else audio_data['mid'] * decay
                audio_data['treb'] = r_t if r_t > audio_data['treb'] else audio_data['treb'] * 0.60 
                audio_data['volume'] = r_vol
                audio_data['energy'] = (0.02 * r_vol) + (0.98 * audio_data['energy'])

            except IOError:
                pass 
    except Exception as e:
        print("Audio listener error:", e)

threading.Thread(target=audio_listener, daemon=True).start()

# --- SYSTEM SETUP ---
try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    time.sleep(3)
    ser.reset_input_buffer()
except Exception as e:
    print(f"Failed to connect to ESP32: {e}")
    exit()

# --- KINEMATIC DANCE ENGINE ---
# Joints: [BASE(0-180), ROTARY(60-145), ELBOW(0-180), WRIST(0-180), UP_DOWN(0-180), CLAW(0-90)]
HOME_STATE = [90, 90, 0, 145, 80, 45]
current_angles = list(HOME_STATE)
target_angles = list(HOME_STATE)
# Smoothing factors per joint. High = fast snap, Low = slow glide.
joint_smoothing = [0.1] * 6 

def set_targets(base=None, rotary=None, elbow=None, wrist=None, up_down=None, claw=None):
    if base is not None: target_angles[0] = max(0, min(180, base))
    if rotary is not None: target_angles[1] = max(60, min(145, rotary))
    if elbow is not None: target_angles[2] = max(0, min(180, elbow))
    if wrist is not None: target_angles[3] = max(0, min(180, wrist))
    if up_down is not None: target_angles[4] = max(0, min(180, up_down))
    if claw is not None: target_angles[5] = max(0, min(90, claw))

def set_smoothing(val):
    global joint_smoothing
    joint_smoothing = [val] * 6

print("\n--- THE CHOREOGRAPHER IS ACTIVE ---")
print("-> Press Ctrl+C in this terminal to quit safely.\n")

# Dance State Machine
moves = ["THE_DJ", "SEARCHLIGHT", "COBRA", "STRIKE_AND_HOLD", "ROBOT_POP"]
current_move = "COBRA"
move_start_time = time.time()
move_duration = 5.0 # Seconds per move

last_send_time = time.time()

try:
    while True:
        t_sec = time.time()
        dt_move = t_sec - move_start_time
        
        # Audio Variables
        b = audio_data['bass']
        m = audio_data['mid']
        t = audio_data['treb']
        vol = audio_data['volume']
        nrg = audio_data['energy']
        
        # --- THE CHOREOGRAPHER (STATE MACHINE) ---
        # Change moves periodically based on energy
        if dt_move > move_duration:
            next_move = random.choice([x for x in moves if x != current_move])
            current_move = next_move
            move_start_time = t_sec
            move_duration = random.uniform(4.0, 8.0)
            print(f"\n[CHOREOGRAPHER] Switching to: {current_move} (Energy: {nrg:.2f})")
            
            # Reset all smoothings on transition
            set_smoothing(0.08)

        # --- THE MOVE LIBRARY ---
        
        if current_move == "THE_DJ":
            # Posture: Arm low and flat, scratching the turntable
            # Isolation: Elbow and Rotary locked. Base sweeps. Wrist snaps on treble.
            set_smoothing(0.15) # Medium response
            joint_smoothing[3] = 0.5 # Fast wrist snaps
            
            set_targets(rotary=120, elbow=130, up_down=30) # Locked low
            
            # Base sweeps on a slow sine wave
            set_targets(base=90 + math.sin(t_sec) * 30)
            
            # Wrist scratching: violent snaps when treble hits
            if t > 0.4:
                set_targets(wrist=180, claw=0)
            else:
                set_targets(wrist=100, claw=90)
                
        elif current_move == "SEARCHLIGHT":
            # Posture: Arm towering high, claw open, sweeping the room. Pumping on bass.
            set_smoothing(0.05) # Very slow, majestic sweep
            joint_smoothing[1] = 0.4 # Fast rotary bumps
            joint_smoothing[2] = 0.4 # Fast elbow bumps
            
            set_targets(wrist=145, up_down=160, claw=90) # Locked high and open
            
            # Base sweeps 180 degrees very slowly
            set_targets(base=90 + math.sin(t_sec * 0.5) * 80)
            
            # Bass causes the arm to temporarily dip forward
            if b > 0.5:
                set_targets(rotary=90, elbow=30)
            else:
                set_targets(rotary=145, elbow=0)
                
        elif current_move == "STRIKE_AND_HOLD":
            # Pop and Lock: Arm retracts and waits. When a huge bass hits, it punches forward and FREEZES.
            set_smoothing(0.6) # Extremely fast snapping
            
            if b > 0.7:
                # STRIKE!
                set_targets(base=90, rotary=60, elbow=150, wrist=145, up_down=60, claw=0)
            elif dt_move < 0.5 or b < 0.2:
                # RETRACT & WAITING
                set_targets(base=90, rotary=145, elbow=0, wrist=90, up_down=140, claw=90)
            # Notice there is no "else". If bass is mid, it just HOLDS its last pose completely still!
            
        elif current_move == "COBRA":
            # Serpentine, slithering movements using out-of-phase sine waves
            set_smoothing(0.1) # Fluid, snake-like
            
            set_targets(base=90) # Base locked
            
            # S-Curves using overlapping math
            r_wave = math.sin(t_sec * 1.5) * 30
            e_wave = math.cos(t_sec * 1.5) * 60 # 90 degrees out of phase for S-curve
            
            set_targets(rotary=100 + r_wave, elbow=60 + e_wave)
            set_targets(up_down=80 + math.sin(t_sec) * 30)
            
            # Claw breathes with the melody
            set_targets(claw=45 + (m * 45))
            
        elif current_move == "ROBOT_POP":
            # Classic robotic isolation. One joint moves at a time, very rigidly.
            set_smoothing(0.5) # Rigid snaps
            
            # Divide the beat into 4 sections
            beat_step = int((t_sec * 2) % 4)
            
            if beat_step == 0:
                set_targets(base=45, wrist=180, claw=0)
            elif beat_step == 1:
                set_targets(up_down=120, rotary=145)
            elif beat_step == 2:
                set_targets(base=135, wrist=90, claw=90)
            elif beat_step == 3:
                set_targets(up_down=40, rotary=90)

        # --- ANIMATION ENGINE (EASING & INTERPOLATION) ---
        # Apply the independent smoothing factors to each joint to glide them to their targets
        for i in range(6):
            current_angles[i] = (joint_smoothing[i] * target_angles[i]) + ((1.0 - joint_smoothing[i]) * current_angles[i])
        
        # --- TRANSMIT TO ESP32 ---
        if t_sec - last_send_time > 0.03: # 30 FPS Lock
            b_val, r_val, e_val, w_val, u_val, c_val = [int(a) for a in current_angles]
            cmd = f"<{b_val},{r_val},{e_val},{w_val},{u_val},{c_val}>\n"
            ser.write(cmd.encode('utf-8'))
            last_send_time = t_sec
            
        # Give CPU a tiny break
        time.sleep(0.005)

except KeyboardInterrupt:
    pass
finally:
    print("\nCleaning up and securing the arm...")
    try:
        ser.write(b"<HOME>\n")
        time.sleep(1.5)
        ser.write(b"<RELAX>\n")
        ser.close()
    except: pass
    print("Done!")
