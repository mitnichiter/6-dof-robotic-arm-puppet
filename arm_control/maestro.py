import serial
import time
import math
import pyaudiowpatch as pyaudio
import numpy as np
import threading

# =========================================================================================
# THE MAESTRO: ORCHESTRAL CONDUCTOR SIMULATOR (maestro.py)
# 
# 1. Classical 4/4 Conducting Pattern: Mathematically generates an elegant 3D space 
#    conducting path (Down, Left, Right, Up) using parameter equations.
# 2. Dynamic Scale (Forte vs Piano): Loud sections (forte) translate to massive, sweeping
#    baton movements. Quiet sections (piano) shrink to delicate, subtle wrist flicks.
# 3. Tempo Phase Lock: Clocks are modulated by predicted BPM and short-term energy.
# 4. Butter-Smooth Glides: Uses heavy adaptive smoothing for organic, fluid sweeps.
# =========================================================================================

# --- AUDIO THREAD (FFT & ENVELOPES) ---
audio_data = {
    'bass': 0.0, 'mid': 0.0, 'treb': 0.0, 'volume': 0.0, 'energy': 0.0,
    'beat_detected': False, 'bpm': 100.0
}

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

        energy_history = [0.0] * 43
        history_idx = 0
        last_beat_time = time.time()
        beat_intervals = []

        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                audio_np = np.frombuffer(data, dtype=np.float32)
                
                if default_speakers["maxInputChannels"] > 1:
                    mono = np.mean(audio_np.reshape(-1, default_speakers["maxInputChannels"]), axis=1)
                else:
                    mono = audio_np

                rms = np.sqrt(np.mean(mono**2))
                
                energy_history[history_idx] = rms
                history_idx = (history_idx + 1) % 43
                avg_energy = np.mean(energy_history)
                
                current_time = time.time()
                is_beat = (rms > avg_energy * 1.4) and (rms > 0.015)
                
                if is_beat and (current_time - last_beat_time > 0.35):
                    interval = current_time - last_beat_time
                    last_beat_time = current_time
                    audio_data['beat_detected'] = True
                    
                    beat_intervals.append(interval)
                    if len(beat_intervals) > 10:
                        beat_intervals.pop(0)
                    avg_interval = np.mean(beat_intervals)
                    audio_data['bpm'] = 60.0 / avg_interval
                else:
                    audio_data['beat_detected'] = False
                
                if rms < 0.001:
                    raw_b = 0.0; raw_m = 0.0; raw_t = 0.0; raw_vol = 0.0
                else:
                    fft_data = np.abs(np.fft.rfft(mono))
                    b = np.mean(fft_data[1:6]) if len(fft_data) > 6 else 0      
                    m = np.mean(fft_data[6:46]) if len(fft_data) > 46 else 0     
                    t = np.mean(fft_data[46:256]) if len(fft_data) > 256 else 0 
                    
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
        # Conductor mode requires extremely heavy smoothing (0.015 - 0.08) for majestic glides
        alpha = max(0.015, min(0.08, 0.015 + (delta / 100.0) * 0.065))
        self.val = (alpha * target) + ((1.0 - alpha) * self.val)
        return self.val

# --- CONDUCTOR TRAJECTORY CALCULATION ---
HOME_STATE = [90, 90, 0, 145, 80, 45]
current_angles = list(HOME_STATE)
target_angles = list(HOME_STATE)
smoothers = [ButterSmoothFilter(val) for val in HOME_STATE]

LIMITS = {
    0: (0, 180),    # Base
    1: (60, 145),   # Rotary
    2: (0, 180),    # Elbow
    3: (0, 180),    # Wrist
    4: (10, 180),   # Up/Down
    5: (0, 90)      # Claw
}

# Clocks
conductor_phase = 0.0
last_frame_time = time.time()
last_send_time = time.time()
last_beat_time = time.time()
beat_index = 0

print("\n=========================================================")
print("                THE MAESTRO ORCHESTRA CONDUCTOR          ")
print("=========================================================")
print("-> Generates smooth, fluid 3D conducting trajectories.")
print("-> Dynamics: Low volume = piano; High volume = forte.")
print("-> Press Ctrl+C in this terminal to safely park and exit.\n")

try:
    while True:
        t_now = time.time()
        dt = t_now - last_frame_time
        last_frame_time = t_now
        
        # Audio cues
        vol = audio_data['volume']
        nrg = audio_data['energy'] # General volume profile
        bpm = audio_data['bpm']
        beat_active = audio_data['beat_detected']
        
        # --- BEAT PHASE MODULATION ---
        # The conductor moves at a rate directly tied to the song's BPM
        beat_interval = 60.0 / max(60.0, min(180.0, bpm))
        if beat_active:
            last_beat_time = t_now
            beat_index = (beat_index + 1) % 4
            
        time_since_beat = t_now - last_beat_time
        rhythm_phase = time_since_beat / beat_interval
        if rhythm_phase > 1.0:
            rhythm_phase = 0.0
            last_beat_time = t_now
            beat_index = (beat_index + 1) % 4
            
        # Continuous time phase for smooth math curves
        # Speeds up slightly during higher energy sections
        conductor_phase += dt * (0.6 + (nrg * 0.6))

        # Default values
        yaw = 90
        shoulder = 90
        elbow = 0
        wrist = 145
        up_down = 80
        claw = 20 # Hold baton slightly pinched

        # --- DYNAMIC CONDUCTING MATHEMATICS ---
        if nrg > 0.01:
            # Scale (Forte vs Piano): Quiet section = tiny moves; Loud section = massive sweeps
            # we scale the amplitude multiplier directly by long term audio energy
            scale = 0.2 + (nrg * 0.8) # 20% to 100% of full range
            
            # A classical 4/4 conducting shape:
            # - Beat 0 (Downbeat): Big stroke straight DOWN.
            # - Beat 1 (Left stroke): Sweep LEFT.
            # - Beat 2 (Right stroke): Sweep RIGHT.
            # - Beat 3 (Upbeat): Sweep UP and center.
            # We model this on-the-fly using parametric trigonometry!
            
            # Base horizontal sweep (Yaw)
            # Sways side-to-side, wider during high energy
            yaw_amplitude = 50 * scale
            yaw = 90 + math.sin(conductor_phase * 1.0) * yaw_amplitude
            
            # Vertical height strokes (Up_down)
            # Sharp downward impacts on the beat, slow graceful rises
            # This is modeled by a saw-tooth-like sine wave
            vertical_wave = math.cos(conductor_phase * 2.0)
            up_down = 80 + (vertical_wave * (35 * scale))
            
            # Coordinated shoulder and elbow reach (creates the forward-reaching baton sweep)
            # As the baton goes down, the shoulder leans slightly forward and elbow bends down
            baton_strike = max(0.0, vertical_wave) * (45 * scale)
            shoulder = 120 - baton_strike
            elbow = 20 + (baton_strike * 1.5)
            
            # Delicate Wrist Flicks (Roll)
            # The wrist rolls left and right at the end of each stroke to "flick" the baton.
            # We use an out-of-phase cosine wave to flick exactly at the stroke boundaries
            wrist_flick = math.cos(conductor_phase * 1.0 + math.pi/4) * (35 * scale)
            wrist = 145 + wrist_flick
            
            # Claw (Baton grip) - holds the baton tightly during large movements
            claw = int(20 + (nrg * 30))
            
        else:
            # Silent: Return to relaxed Home and perform very slow, subtle "idle breathing"
            t_idle = t_now
            yaw = 90
            shoulder = 90 + (math.sin(t_idle * 1.2) * 2)
            elbow = 0
            wrist = 145 + (math.cos(t_idle * 0.8) * 2)
            up_down = 80 + (math.sin(t_idle * 1.0) * 3)
            claw = 45

        # --- APPLY HARDWARE CLAMPING & SMOOTHING ---
        target_angles = [yaw, shoulder, elbow, wrist, up_down, claw]
        for i in range(6):
            min_ang, max_ang = LIMITS[i]
            target_angles[i] = max(min_ang, min(target_angles[i], max_ang))
            current_angles[i] = smoothers[i].update(target_angles[i])

        # Send command @ 30 FPS
        if t_now - last_send_time > 0.033:
            b, r, e, w, u, c = [int(a) for a in current_angles]
            cmd = f"<{b},{r},{e},{w},{u},{c}>\n"
            ser.write(cmd.encode('utf-8'))
            last_send_time = t_now
            
            # Visual ASCII Feedback of the Conductor's Baton Height
            height_idx = max(0, min(19, int((up_down - 20) / 140.0 * 20)))
            visual_bar = " " * height_idx + "■" + " " * (19 - height_idx)
            print(f"\r[Baton Height: {visual_bar}] [Energy: {nrg:.2f}] [BPM: {bpm:5.1f}] Style: MAESTRO", end="", flush=True)

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
    print("Maestro Conductor successfully stopped. Done!")
