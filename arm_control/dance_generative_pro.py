import serial
import time
import math
import pyaudiowpatch as pyaudio
import numpy as np
import threading

# =========================================================================================
# THE GENERATIVE VECTOR-BLENDING CHOREOGRAPHER (dance_generative_pro.py)
# 
# 1. Coordinate Vector Space Interpolation (Choreographic Morphing): 
#    Instead of random joint scaling, we define 5 beautifully coordinated, stable poses.
#    The robot's posture at any millisecond is a weighted blend (morph) of these poses.
# 2. Dynamic Audio Mapping:
#    - BASS (Envelopes) morphs the arm toward POSE_REACH (striking forward and down).
#    - VOLUME (Loudness) morphs the arm toward POSE_TALL (towering high and proud).
#    - MIDS (vocals/melodies) morphs the arm smoothly between SWEEP_LEFT and SWEEP_RIGHT.
#    - SILENCE pulls the arm back to the HOME state.
# 3. Butter-Smooth Filtering: Ensures all morphs are seamless, fluid, and organic.
# =========================================================================================

# --- AUDIO THREAD (FFT & ENVELOPES) ---
audio_data = {'bass': 0.0, 'mid': 0.0, 'treb': 0.0, 'volume': 0.0, 'energy': 0.0}

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

                rms = np.sqrt(np.mean(mono**2))
                if rms < 0.001:
                    raw_b = 0.0; raw_m = 0.0; raw_t = 0.0; raw_vol = 0.0
                else:
                    fft_data = np.abs(np.fft.rfft(mono))
                    b = np.mean(fft_data[1:6]) if len(fft_data) > 6 else 0      
                    m = np.mean(fft_data[6:46]) if len(fft_data) > 46 else 0     
                    t = np.mean(fft_data[46:256]) if len(fft_data) > 256 else 0 
                    
                    # Clean digital boosts
                    raw_b = min(1.0, b * 0.15)    
                    raw_m = min(1.0, m * 0.15)      
                    raw_t = min(1.0, t * 0.25) 
                    raw_vol = min(1.0, rms * 3)
                
                decay = 0.85
                audio_data['bass'] = raw_b if raw_b > audio_data['bass'] else audio_data['bass'] * decay
                audio_data['mid'] = raw_m if raw_m > audio_data['mid'] else audio_data['mid'] * decay
                audio_data['treb'] = raw_t if raw_t > audio_data['treb'] else audio_data['treb'] * 0.70 
                audio_data['volume'] = raw_vol
                audio_data['energy'] = (0.02 * raw_vol) + (0.98 * audio_data['energy'])

            except IOError:
                pass 
    except Exception as e:
        print("Audio listener error:", e)

threading.Thread(target=audio_listener, daemon=True).start()

# --- ESP32 CONNECTION ---
try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    # Reset board so main.py runs
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setRTS(False)
    
    print("Waiting 2s for ESP32 to boot...")
    time.sleep(2.0)
    ser.reset_input_buffer()
    print("ESP32 connected successfully!")
except Exception as e:
    print(f"Failed to connect: {e}")
    exit()

# --- SMOOTHING FILTER ---
class ButterSmoothFilter:
    def __init__(self, initial_val):
        self.val = initial_val

    def update(self, target):
        delta = abs(target - self.val)
        # Smooth and majestic conductor-like damping
        alpha = max(0.03, min(0.15, 0.03 + (delta / 100.0) * 0.12))
        self.val = (alpha * target) + ((1.0 - alpha) * self.val)
        return self.val

# --- COORDINATED POSE VECTORS ---
# Standard Order: [BASE, ROTARY, ELBOW, WRIST, UP_DOWN, CLAW]
POSES = {
    'HOME':        [90, 90, 0, 145, 80, 45],       # Center resting pose
    'REACH':       [90, 60, 150, 145, 30, 90],     # Reaches deeply forward/down (Claw open)
    'TALL':        [90, 145, 0, 145, 160, 0],      # Towers straight up in the air (Claw closed)
    'SWEEP_LEFT':  [40, 100, 30, 90, 100, 45],     # Sweeps left, wrist tilted down
    'SWEEP_RIGHT': [140, 100, 30, 180, 100, 45]    # Sweeps right, wrist tilted up
}

LIMITS = {
    0: (0, 180),    # Base
    1: (60, 145),   # Rotary
    2: (0, 180),    # Elbow
    3: (0, 180),    # Wrist
    4: (10, 180),   # Up/Down
    5: (0, 90)      # Claw
}

current_angles = list(POSES['HOME'])
target_angles = list(POSES['HOME'])
smoothers = [ButterSmoothFilter(val) for val in POSES['HOME']]

last_send_time = time.time()

print("\n=========================================================")
print("          THE COORDINATED VECTOR-BLENDING DANCER         ")
print("=========================================================")
print("-> Synthesizes professional-grade joint movements.")
print("-> Morphs dynamically between 5 hand-crafted 3D poses.")
print("-> Zero random joint twitching—always structured and cool.")
print("-> Press Ctrl+C in this terminal to safely exit.\n")

try:
    while True:
        t_now = time.time()
        
        # Audio Variables
        b = audio_data['bass']
        m = audio_data['mid']
        t = audio_data['treb']
        vol = audio_data['volume']
        nrg = audio_data['energy'] # long term volume track
        
        # --- 1. GENERATIVE BLENDING WEIGHTS ---
        # We calculate the presence of each pose in our final blend:
        
        # A. REACH (Driven by BASS)
        # Intense bass hits morph the robot toward the forward-reaching "REACH" posture
        w_reach = b * 0.9
        
        # B. TALL (Driven by total LOUDNESS/VOLUME)
        # Loud sections make the robot tower up in the air
        w_tall = vol * 0.8
        
        # C. SWEEPS (Driven by MID-RANGE melody + a slow sway clock)
        # We use a slow sine wave to alternate the sway direction, but the scale of the 
        # sway is multiplied directly by the mid-range melody (vocals/synths)
        sway_factor = math.sin(t_now * 2.0)
        if sway_factor > 0:
            w_sweep_right = sway_factor * (m * 0.8)
            w_sweep_left = 0.0
        else:
            w_sweep_left = abs(sway_factor) * (m * 0.8)
            w_sweep_right = 0.0
            
        # D. HOME (The baseline pull)
        # Any remaining weight pulls the arm back toward the safe HOME posture.
        # If the music is quiet or silent, w_home becomes 1.0, pulling the arm back to rest.
        total_active_weight = w_reach + w_tall + w_sweep_left + w_sweep_right
        w_home = max(0.0, 1.0 - total_active_weight)
        
        # --- 2. VECTOR SPACE INTERPOLATION ---
        # Normalize weights so they sum to exactly 1.0
        weights_sum = w_home + w_reach + w_tall + w_sweep_left + w_sweep_right
        
        n_home = w_home / weights_sum
        n_reach = w_reach / weights_sum
        n_tall = w_tall / weights_sum
        n_left = w_sweep_left / weights_sum
        n_right = w_sweep_right / weights_sum
        
        # Calculate the weighted average coordinate for each joint
        for i in range(6):
            target_angles[i] = (
                n_home  * POSES['HOME'][i] +
                n_reach * POSES['REACH'][i] +
                n_tall  * POSES['TALL'][i] +
                n_left  * POSES['SWEEP_LEFT'][i] +
                n_right * POSES['SWEEP_RIGHT'][i]
            )
            
        # --- 3. HARDWARE CLAMP & SMOOTHING ---
        for i in range(6):
            min_ang, max_ang = LIMITS[i]
            target_angles[i] = max(min_ang, min(target_angles[i], max_ang))
            current_angles[i] = smoothers[i].update(target_angles[i])

        # Send command @ 30 FPS
        if t_now - last_send_time > 0.033:
            b_val, r_val, e_val, w_val, u_val, c_val = [int(a) for a in current_angles]
            cmd = f"<{b_val},{r_val},{e_val},{w_val},{u_val},{c_val}>\n"
            ser.write(cmd.encode('utf-8'))
            last_send_time = t_now
            
            # Print beautiful debug metrics showing the live blending coordinates
            print(f"\rBlend -> Home:{n_home:.2f} Reach:{n_reach:.2f} Tall:{n_tall:.2f} Left:{n_left:.2f} Right:{n_right:.2f}", end="", flush=True)

        time.sleep(0.005)

except KeyboardInterrupt:
    pass
finally:
    print("\n\nSafely parking and relaxing the arm...")
    try:
        ser.write(b"<HOME>\n")
        time.sleep(1.5)
        ser.write(b"<RELAX>\n")
        ser.close()
    except Exception as e:
        print("Error during shutdown:", e)
    print("Vector-Blending Engine successfully stopped. Done!")
