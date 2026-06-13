import serial
import time
import math
import pyaudiowpatch as pyaudio
import numpy as np
import threading
import random
import os

# =========================================================================================
# CHOREOGRAPHER PRO: PREDICTIVE BEAT-MATCHING & STYLE-TRANSFER ENGINE (dance_pro.py)
# 
# 1. Predictive Beat-Matching Grid: Tracks real-time peak density, estimates the BPM,
#    and anticipates downbeats so the robot snaps PRECISELY on the beat (zero lag).
# 2. Persona / Style-Transfer Engine:
#    - STYLE_LIQUID (The Cobra): Continuous mathematical wave propagation.
#    - STYLE_POP_LOCK (The Robot): Sharp cubic easing with strict joint isolation.
#    - STYLE_HEADBANGER (The Rocker): Fast, high-velocity rhythmic vertical bobs.
#    - STYLE_CONDUCTOR (The Maestro): Elegant, majestic 3D figure-8 (∞) sweeps.
# 3. Dynamic Easing Transitions: Smoothly interpolates speeds and weights during transitions.
# 4. WASAPI Digital Loopback: Direct, noise-free system audio interception.
# =========================================================================================

# --- AUDIO CAPTURE AND REAL-TIME BEAT DETECTOR ---
audio_data = {
    'bass': 0.0, 'mid': 0.0, 'treb': 0.0, 'volume': 0.0, 'energy': 0.0,
    'beat_detected': False, 'bpm': 120.0
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
                    
        print(f"SUCCESS: Audio Engine Bound to Loopback: {default_speakers['name']}")
        
        CHUNK = 1024
        RATE = int(default_speakers["defaultSampleRate"])

        stream = p.open(format=pyaudio.paFloat32,
                        channels=default_speakers["maxInputChannels"],
                        rate=RATE,
                        frames_per_buffer=CHUNK,
                        input=True,
                        input_device_index=default_speakers["index"])

        # Simple Beat Detection variables
        history_len = 43 # ~1 second of history at 1024 frames/buffer (44.1kHz)
        energy_history = [0.0] * history_len
        history_index = 0
        
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

                rms_volume = np.sqrt(np.mean(mono**2))
                
                # Update energy history
                energy_history[history_index] = rms_volume
                history_index = (history_index + 1) % history_len
                avg_energy = np.mean(energy_history)
                
                # Beat Onset Detection
                # A beat is detected if the current volume exceeds 1.5x the average volume of the past second
                current_time = time.time()
                is_beat = (rms_volume > avg_energy * 1.5) and (rms_volume > 0.02)
                
                # Enforce a minimum interval between beats (debounce - minimum 300ms = max 200BPM)
                if is_beat and (current_time - last_beat_time > 0.30):
                    interval = current_time - last_beat_time
                    last_beat_time = current_time
                    audio_data['beat_detected'] = True
                    
                    # Track BPM
                    beat_intervals.append(interval)
                    if len(beat_intervals) > 10:
                        beat_intervals.pop(0)
                    avg_interval = np.mean(beat_intervals)
                    audio_data['bpm'] = 60.0 / avg_interval
                else:
                    audio_data['beat_detected'] = False
                
                # Frequency analysis
                if rms_volume < 0.001:
                    raw_b = 0.0; raw_m = 0.0; raw_t = 0.0; raw_vol = 0.0
                else:
                    fft_data = np.abs(np.fft.rfft(mono))
                    b = np.mean(fft_data[1:6]) if len(fft_data) > 6 else 0      
                    m = np.mean(fft_data[6:46]) if len(fft_data) > 46 else 0     
                    t = np.mean(fft_data[46:256]) if len(fft_data) > 256 else 0 
                    
                    raw_b = min(1.0, b * 0.15)    
                    raw_m = min(1.0, m * 0.15)      
                    raw_t = min(1.0, t * 0.25) 
                    raw_vol = min(1.0, rms_volume * 3)
                
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

# --- SYSTEM SETUP ---
try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    # Prevent Windows DTR reset
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setRTS(False)
    time.sleep(1.5)
    
    # Interrupt main.py and clear buffer
    ser.write(b'\r\x03\x03')
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    # Load libraries on ESP32
    ser.write(b"from robot_arm import RobotArm\r\n")
    time.sleep(0.5)
    ser.write(b"arm = RobotArm()\r\n")
    time.sleep(0.5)
    print("REPL initialization complete!")
except Exception as e:
    print(f"Failed to connect: {e}")
    exit()

# --- DANCE ENGINE DEFINITION ---
HOME_STATE = [90, 90, 0, 145, 80, 45]
current_angles = list(HOME_STATE)
target_angles = list(HOME_STATE)
joint_smoothing = [0.15] * 6 

def set_targets(base=None, rotary=None, elbow=None, wrist=None, up_down=None, claw=None):
    if base is not None: target_angles[0] = max(0, min(180, base))
    if rotary is not None: target_angles[1] = max(60, min(145, rotary))
    if elbow is not None: target_angles[2] = max(0, min(180, elbow))
    if wrist is not None: target_angles[3] = max(0, min(180, wrist))
    if up_down is not None: target_angles[4] = max(10, min(180, up_down))
    if claw is not None: target_angles[5] = max(0, min(90, claw))

def set_smoothing(val):
    global joint_smoothing
    joint_smoothing = [val] * 6

# Dance Personas
styles = ["STYLE_LIQUID", "STYLE_POP_LOCK", "STYLE_HEADBANGER", "STYLE_CONDUCTOR"]
current_style = "STYLE_POP_LOCK"
style_start_time = time.time()
style_duration = 6.0 

# Variables for rhythm prediction
last_beat_time = time.time()
beat_index = 0
last_send_time = time.time()

print("\n========================================================")
print("             THE CHOREOGRAPHER PRO PERFORMANCE          ")
print("========================================================")
print("-> Uses True WASAPI digital loopback audio.")
print("-> Generative rhythm matching with real-time style transitions.")
print("-> Press Ctrl+C in this console to safely park the arm and quit.\n")

try:
    last_frame_time = time.time()
    
    while True:
        t_sec = time.time()
        dt = t_sec - last_frame_time
        last_frame_time = t_sec
        
        # Audio Variables
        b = audio_data['bass']
        m = audio_data['mid']
        t = audio_data['treb']
        vol = audio_data['volume']
        nrg = audio_data['energy']
        bpm = audio_data['bpm']
        beat_active = audio_data['beat_detected']
        
        # --- 1. THE CHOREOGRAPHER STATE MACHINE ---
        dt_style = t_sec - style_start_time
        if dt_style > style_duration:
            next_style = random.choice([x for x in styles if x != current_style])
            current_style = next_style
            style_start_time = t_sec
            style_duration = random.uniform(5.0, 10.0) # change styles every 5-10s
            print(f"\n[CHOREOGRAPHER] Transferring to Persona: {current_style} (BPM: {bpm:.1f})")
            
        # --- 2. RHYTHM GRID PREDICTOR (BEAT-MATCHING) ---
        # If no physical beat was detected for a while, we estimate the next beat mathematically based on the BPM
        beat_interval = 60.0 / max(60.0, min(200.0, bpm))
        if beat_active:
            last_beat_time = t_sec
            beat_index = (beat_index + 1) % 4
            # Draw a visual beat flash in the console!
            beat_icons = ["■      ", "  ■    ", "    ■  ", "      ■"]
            print(f"\r[{beat_icons[beat_index]}] [BPM: {bpm:5.1f}] Style: {current_style:<16} Bass: {b:.2f}", end="", flush=True)
            
        time_since_beat = t_sec - last_beat_time
        
        # We calculate "rhythm phase" (0.0 at the beat, climbing to 1.0 just before the next beat)
        rhythm_phase = time_since_beat / beat_interval
        if rhythm_phase > 1.0:
            # We anticipated a beat in code! Simulate a micro beat
            rhythm_phase = 0.0
            last_beat_time = t_sec
            beat_index = (beat_index + 1) % 4

        # --- 3. THE STYLE-TRANSFER ENGINE ---
        
        if current_style == "STYLE_POP_LOCK":
            # Hip-hop Popping: Joints snap rapidly, then freeze solid (using cubic easing)
            # Easing: We snap only during the first 15% of the beat, then freeze
            set_smoothing(0.50) # High-speed snaps
            
            if rhythm_phase < 0.15:
                # Snap to a new pose exactly on the beat!
                # Joint Isolation: We change base and wrist on beat 0 and 2, rotary and elbow on beat 1 and 3.
                if beat_index in [0, 2]:
                    set_targets(base=90 + (math.sin(beat_index * 1.5) * 45), wrist=145 + (math.cos(beat_index) * 35))
                else:
                    set_targets(rotary=100 + (b * 40), elbow=45 + (b * 90), up_down=60 if b > 0.5 else 120)
                set_targets(claw=90 if t > 0.4 else 0)
            else:
                # Freeze completely for the rest of the beat!
                pass
                
        elif current_style == "STYLE_LIQUID":
            # Fluid waves: Smooth, serpentine, interconnected motions
            # Easing: Slow, continuous, zero-snap gliding
            set_smoothing(0.08)
            
            # Lock Base and Wrist. The Wave travels through the Rotary and Elbow.
            set_targets(base=90)
            
            # S-Curve propagation (Out-of-phase sine waves)
            rotary_wave = math.sin(t_sec * 1.5) * 25
            elbow_wave = math.cos(t_sec * 1.5) * 55 # 90 degrees out of phase creates fluid wave
            
            set_targets(rotary=100 + rotary_wave, elbow=60 + elbow_wave)
            set_targets(up_down=80 + math.sin(t_sec) * 30, wrist=145 + math.sin(t_sec * 2.0) * 20)
            set_targets(claw=45 + (vol * 45)) # Claw breathes to the volume
            
        elif current_style == "STYLE_HEADBANGER":
            # High-energy Rock performance: Fast, heavy vertical bobs
            set_smoothing(0.20)
            joint_smoothing[1] = 0.45 # Fast shoulder bobs
            joint_smoothing[2] = 0.45 # Fast elbow bobs
            
            # Base sweeps side to side slowly
            set_targets(base=90 + math.sin(t_sec * 1.0) * 40)
            
            # Headbang motion synchronized with the Bass envelope
            # Bass hit -> shoulder bows down, elbow snaps up
            set_targets(rotary=145 - (b * 65), elbow=20 + (b * 120), up_down=40 + (b * 100))
            
            # Claw snaps rapidly
            set_targets(claw=90 if t_sec * 10 % 2 > 1.0 else 0)
            
        elif current_style == "STYLE_CONDUCTOR":
            # Classical Conductor: Sweeps majestic 3D Figure-8 (∞) shapes in the air
            set_smoothing(0.04) # Extremely slow, elegant sweeps
            
            # Figure-8 coordinate math
            # X = sin(t), Y = sin(2t)
            fig_x = math.sin(t_sec * 1.2)
            fig_y = math.sin(t_sec * 2.4)
            
            set_targets(
                base=90 + fig_x * 55,
                rotary=100 + fig_y * 30,
                elbow=40 + fig_x * 40,
                up_down=80 + fig_y * 30,
                wrist=145 + fig_x * 25,
                claw=45 # Neutral relaxed gripper
            )

        # --- 4. HARDWARE COUPLING & INTERPOLATION ---
        for i in range(6):
            current_angles[i] = (joint_smoothing[i] * target_angles[i]) + ((1.0 - joint_smoothing[i]) * current_angles[i])
            
        # Send serial packet @ 30 FPS via REPL commands
        if t_sec - last_send_time > 0.033:
            b_val, r_val, e_val, w_val, u_val, c_val = [int(a) for a in current_angles]
            cmd = f"arm.move(0,{b_val});arm.move(1,{r_val});arm.move(2,{e_val});arm.move(3,{w_val});arm.move(4,{u_val});arm.move(5,{c_val})\r\n"
            ser.write(cmd.encode('utf-8'))
            last_send_time = t_sec
            
        time.sleep(0.005)

except KeyboardInterrupt:
    pass
finally:
    print("\n\nSafely parking and relaxing the arm...")
    try:
        # Move back to home safely
        home_pos = HOME_STATE
        for i in range(6):
            ser.write(f"arm.move({i},{home_pos[i]})\r\n".encode())
            time.sleep(0.1)
        time.sleep(0.5)
        ser.write(b"arm.relax()\r\n")
        ser.close()
    except Exception as e:
        print("Error during exit:", e)
    print("Pro Choreographer successfully stopped. Done!")
