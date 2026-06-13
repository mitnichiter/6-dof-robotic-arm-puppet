import serial
import time
import math
import pyaudiowpatch as pyaudio
import numpy as np
import threading
import sys

# =========================================================================================
# GENERATIVE CHOREOGRAPHY ENGINE: THE 10-STEP THINKING (dance_generative.py)
# 
# This script does NOT use pre-made moves, keyframes, or a random state machine.
# Instead, it runs a continuous, multi-dimensional mathematical vector engine that
# translates live system audio frequencies directly into organic, fluid joint trajectories.
# =========================================================================================

# --- AUDIO CAPTURE AND REAL-TIME SIGNAL PROCESSING ---
audio_data = {
    'bass': 0.0, 'mid': 0.0, 'treb': 0.0, 'volume': 0.0, 'energy': 0.0,
    'beat_onset': False
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

        # History for beat detection
        energy_history = [0.0] * 43
        history_idx = 0

        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                audio_np = np.frombuffer(data, dtype=np.float32)
                
                if default_speakers["maxInputChannels"] > 1:
                    mono = np.mean(audio_np.reshape(-1, default_speakers["maxInputChannels"]), axis=1)
                else:
                    mono = audio_np

                rms = np.sqrt(np.mean(mono**2))
                
                # Update history for local energy thresholding
                energy_history[history_idx] = rms
                history_idx = (history_idx + 1) % 43
                avg_energy = np.mean(energy_history)
                
                is_beat = (rms > avg_energy * 1.5) and (rms > 0.02)
                audio_data['beat_onset'] = is_beat
                
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
                
                # Fast attack / slow decay envelopes
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

# --- ESP32 DRIVER INTERFACE ---
try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    
    # Force hardware reset exactly as tested and working
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setRTS(False)
    
    print("Waiting 2 seconds for ESP32 to boot and start main.py...")
    time.sleep(2.0)
    ser.reset_input_buffer()
    print("ESP32 board successfully initialized and listening!")
except Exception as e:
    print(f"Failed to connect: {e}")
    exit()

# --- 10-STEP GENERATIVE CHOREOGRAPHY ENGINE ---

# Absolute hardware boundaries (safety guard bands)
LIMITS = {
    0: (0, 180),    # Base
    1: (60, 145),   # Rotary
    2: (0, 180),    # Elbow
    3: (0, 180),    # Wrist
    4: (10, 180),   # Up/Down
    5: (0, 90)      # Claw
}

HOME_STATE = [90, 90, 0, 145, 80, 45]
current_angles = list(HOME_STATE)
target_angles = list(HOME_STATE)

# Easing coefficients (Exponential Moving Average)
smoothing_speeds = [0.10] * 6

def map_range(x, in_min, in_max, out_min, out_max):
    val = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return max(min(out_min, out_max), min(max(out_min, out_max), val))

# Time phase clocks for sine wave synthesis
clock_yaw = 0.0
clock_pitch = 0.0
clock_roll = 0.0

last_frame_time = time.time()
last_send_time = time.time()

print("\n=========================================================")
print("          10-STEP GENERATIVE CHOREOGRAPHY MODULE         ")
print("=========================================================")
print("-> Generates organic joint trajectories from raw waveforms.")
print("-> 100% mathematical, no pre-programmed keyframe moves.")
print("-> Press Ctrl+C in this terminal to quit safely.\n")

try:
    while True:
        t_now = time.time()
        dt = t_now - last_frame_time
        last_frame_time = t_now
        
        # Step 1: Raw Spectral Extraction (Isolated FFT values)
        b = audio_data['bass']
        m = audio_data['mid']
        t = audio_data['treb']
        vol = audio_data['volume']
        nrg = audio_data['energy'] # Long-term energy track (vibe sensor)
        beat_hit = audio_data['beat_onset']
        
        # Step 2: Dynamic Tempo matching & Phase Modulation
        # We accelerate our internal clocks when the music is louder (higher energy)
        # This makes the robot sway faster to hype music, and slow down to chill music.
        tempo_multiplier = 1.0 + (nrg * 1.5)
        clock_yaw += dt * 1.2 * tempo_multiplier
        clock_pitch += dt * 1.8 * tempo_multiplier
        clock_roll += dt * 2.5 * tempo_multiplier
        
        # Step 3: Base Swivel Trajectory (Step-by-Step Generative Math)
        # Slow, rhythmic sway that gets dynamically wider during louder choruses
        sway_amplitude = 15 + (nrg * 55) # sways 15 deg on verses, up to 70 deg on drops
        target_angles[0] = 90 + math.sin(clock_yaw) * sway_amplitude
        
        # Step 4: Shoulder (Rotary) and Elbow Kinematic Coupling
        # To maintain a fluid reaching profile, the rotary and elbow are mathematically coupled.
        # Bass hits cause a forward-and-down "headbang" strike.
        bass_strike = b * (25 + (nrg * 55)) # up to 80 degrees of impact
        target_angles[1] = 145 - bass_strike       # Shoulder leans forward
        target_angles[2] = 0 + (bass_strike * 1.6) # Elbow reaches down to match
        
        # Step 5: Wrist Roll Wave Superposition
        # We superimpose two out-of-phase sine waves to create complex, non-repetitive flourishes,
        # multiplied by the high-end treble envelope.
        twist_wave = (math.sin(clock_roll * 1.5) * 35) + (math.cos(clock_roll * 0.7) * 15)
        target_angles[3] = 145 + (twist_wave * (0.2 + t * 0.8))
        
        # Step 6: Up/Down Height Bounce
        # Bobs vertically up and down. The amplitude is driven directly by the Mids/vocals.
        target_angles[4] = 80 + math.cos(clock_pitch) * (15 + (m * 45))
        
        # Step 7: Claw Transients Snapping
        # Standard claws open on treble. We add a probabilistic threshold:
        # If a treble spike occurs, snap open, otherwise remain relaxed.
        if t > 0.45:
            target_angles[5] = 90 # Snap wide open
        else:
            # Let the claw relax back to closed or slightly open based on energy
            target_angles[5] = max(0, min(90, int(nrg * 45)))
            
        # Step 8: Dynamic Easing (The Anti-Twerking Algorithm)
        # We adjust our joint smoothing speeds in real-time.
        # If the music is fast and energetic, we use high smoothing speed (0.35) for snappy, rigid locking.
        # If the music is soft or silent, we drop to 0.04 for buttery-smooth glides.
        for i in range(6):
            smoothing_speeds[i] = map_range(vol, 0.05, 0.8, 0.04, 0.35)
            
        # Step 9: Joint Isolation Allocation
        # During soft parts (low energy), we mathematically mute certain joints (like Base and Wrist)
        # so they freeze, and only the shoulder "breathes". This creates high-contrast professional locking.
        if nrg < 0.15:
            target_angles[0] = 90  # Center base
            target_angles[3] = 145 # Center wrist
            smoothing_speeds[0] = 0.02 # Heavy freeze
            smoothing_speeds[3] = 0.02
            
        # Step 10: Failsafe Boundary Clamping
        # Final hardware-level clamping before serial dispatch
        for i in range(6):
            min_ang, max_ang = LIMITS[i]
            target_angles[i] = max(min_ang, min(target_angles[i], max_ang))
            
        # Interpolate positions (Easing)
        for i in range(6):
            current_angles[i] = (smoothing_speeds[i] * target_angles[i]) + ((1.0 - smoothing_speeds[i]) * current_angles[i])
            
        # Dispatch serial command envelope to ESP32 @ 30 FPS
        if t_now - last_send_time > 0.033:
            b_val, r_val, e_val, w_val, u_val, c_val = [int(a) for a in current_angles]
            # Stream the safe coordinates directly to the ESP32 main.py listener!
            cmd = f"<{b_val},{r_val},{e_val},{w_val},{u_val},{c_val}>\n"
            ser.write(cmd.encode('utf-8'))
            last_send_time = t_now
            
            # Print a beautiful real-time terminal visual of the generative parameters!
            bar_width = int(b * 15)
            bass_bar = "█" * bar_width + " " * (15 - bar_width)
            print(f"\r[BASS: {bass_bar}] [ENERGY: {nrg:.2f}] [CLOCK: {clock_pitch:5.1f}] [SPEED: {smoothing_speeds[0]:.2f}]", end="", flush=True)

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
    print("10-Step Generative Engine safely stopped. Done!")
