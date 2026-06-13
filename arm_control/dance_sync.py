import cv2
import mediapipe as mp
import serial
import time
import math
import pyaudiowpatch as pyaudio
import numpy as np
import threading
import random
import customtkinter as ctk
import asyncio
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager

# =========================================================================================
# THE WINDOWS MEDIA SESSION SYNCHRONIZER (dance_sync.py)
# 
# 1. Windows GSMTC Media Sync: Interfaces with native Windows APIs to track the active 
#    song title, artist, and play/pause state from Spotify, YouTube, Chrome, etc.
# 2. Play/Pause Automation: If you pause the music on your PC, the robot instantly freezes
#    its joints in mid-air. When you click play, it immediately resumes dancing.
# 3. Holographic HUD GUI: Displays live track metadata, playback status, current dance style,
#    and moving spectral equalizer bars on a beautiful CustomTkinter desktop panel.
# 4. Generative Audio Core: Uses low-level WASAPI loopback to animate joints in real-time.
# =========================================================================================

# --- SHARED STATE DATA ---
audio_data = {'bass': 0.0, 'mid': 0.0, 'treb': 0.0, 'volume': 0.0, 'energy': 0.0}
media_data = {'title': 'No Track Active', 'artist': 'Offline', 'status': 'PAUSED'}

# --- WINDOWS MEDIA RUNTIME THREAD (winsdk) ---
async def media_tracker():
    try:
        manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        while True:
            session = manager.get_current_session()
            if session:
                try:
                    props = await session.try_get_media_properties_async()
                    media_data['title'] = props.title if props.title else 'Unknown Track'
                    media_data['artist'] = props.artist if props.artist else 'Unknown Artist'
                    
                    # Playback info (4 = Playing, 5 = Paused)
                    playback_info = session.get_playback_info()
                    status = playback_info.playback_status
                    if status == 4:
                        media_data['status'] = 'PLAYING'
                    else:
                        media_data['status'] = 'PAUSED'
                except Exception:
                    pass
            else:
                media_data['title'] = 'No Media Active'
                media_data['artist'] = 'System Audio Only'
                media_data['status'] = 'PLAYING' # Default to active if no GSMTC is registered
                
            await asyncio.sleep(0.5) # Poll every 500ms
    except Exception as e:
        print("Media tracker critical error:", e)

def run_async_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(media_tracker())

async_loop = asyncio.new_event_loop()
threading.Thread(target=run_async_loop, args=(async_loop,), daemon=True).start()

# --- AUDIO LOOPBACK THREAD (FFT PROCESSING) ---
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

# --- ESP32 DRIVER INTERFACE ---
try:
    print("Connecting to ESP32 on COM5...")
    ser = serial.Serial('COM5', 115200, timeout=1)
    
    # Reset board so main.py runs
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setRTS(False)
    
    print("Waiting 2s for ESP32 to boot and run main.py...")
    time.sleep(2.0)
    ser.reset_input_buffer()
    print("ESP32 board successfully initialized and listening!")
except Exception as e:
    print(f"Failed to connect: {e}")
    exit()

# --- SMOOTHING FILTER ---
class ButterSmoothFilter:
    def __init__(self, initial_val):
        self.val = initial_val

    def update(self, target):
        delta = abs(target - self.val)
        alpha = max(0.02, min(0.35, 0.02 + (delta / 100.0) * 0.33))
        self.val = (alpha * target) + ((1.0 - alpha) * self.val)
        return self.val

# --- CHOREOGRAPHER VARIABLES ---
HOME_STATE = [90, 90, 0, 145, 80, 45]
current_angles = list(HOME_STATE)
target_angles = list(HOME_STATE)
smoothers = [ButterSmoothFilter(val) for val in HOME_STATE]

styles = ["STYLE_LIQUID", "STYLE_POP_LOCK", "STYLE_HEADBANGER", "STYLE_CONDUCTOR"]
current_style = "STYLE_POP_LOCK"
style_start_time = time.time()
style_duration = 8.0
last_send_time = time.time()

# --- GUI SETUP ---
app = ctk.CTk()
app.title("Windows Media Synchronizer")
app.geometry("550x550")
ctk.set_appearance_mode("dark")

# Song Frame
frame_track = ctk.CTkFrame(app, corner_radius=15, fg_color="#1e272c")
frame_track.pack(pady=20, padx=20, fill="x")

lbl_status_indicator = ctk.CTkLabel(frame_track, text="PLAYING", font=("Arial", 12, "bold"), text_color="#2ecc71")
lbl_status_indicator.pack(pady=(15, 0))

lbl_title = ctk.CTkLabel(frame_track, text="Detecting Track...", font=("Arial", 22, "bold"), wraplength=480)
lbl_title.pack(pady=(10, 5))

lbl_artist = ctk.CTkLabel(frame_track, text="Scanning System...", font=("Arial", 16), text_color="#95a5a6")
lbl_artist.pack(pady=(0, 15))

# Style Frame
frame_style = ctk.CTkFrame(app, corner_radius=15)
frame_style.pack(pady=10, padx=20, fill="x")

lbl_style_title = ctk.CTkLabel(frame_style, text="CURRENT CHOREOGRAPHY STYLE", font=("Arial", 10, "bold"), text_color="#7f8c8d")
lbl_style_title.pack(pady=(10, 2))

lbl_style = ctk.CTkLabel(frame_style, text="STYLE_POP_LOCK", font=("Arial", 18, "bold"), text_color="#3498db")
lbl_style.pack(pady=(0, 12))

# Equalizer Visualizer Frame
frame_eq = ctk.CTkFrame(app, corner_radius=15)
frame_eq.pack(pady=15, padx=20, fill="both", expand=True)

ctk.CTkLabel(frame_eq, text="SPECTRAL REAL-TIME GRAPH", font=("Arial", 11, "bold"), text_color="#7f8c8d").pack(pady=10)

prog_bass = ctk.CTkProgressBar(frame_eq, width=400, height=20, progress_color="#e74c3c")
prog_bass.pack(pady=8)
prog_bass_label = ctk.CTkLabel(frame_eq, text="BASS (Servo Headbang)", font=("Arial", 11))
prog_bass_label.pack()

prog_mid = ctk.CTkProgressBar(frame_eq, width=400, height=20, progress_color="#3498db")
prog_mid.pack(pady=8)
prog_mid_label = ctk.CTkLabel(frame_eq, text="MIDS (Base Sweep / Volume Bounce)", font=("Arial", 11))
prog_mid_label.pack()

prog_treb = ctk.CTkProgressBar(frame_eq, width=400, height=20, progress_color="#f1c40f")
prog_treb.pack(pady=8)
prog_treb_label = ctk.CTkLabel(frame_eq, text="TREBLE (Claw Snap / Wrist Twist)", font=("Arial", 11))
prog_treb_label.pack()

# --- MAIN APP REFRESH LOOP ---
last_frame_time = time.time()

def update_ui_and_robot():
    global last_frame_time, current_style, style_start_time, style_duration, last_send_time
    
    t_sec = time.time()
    dt = t_sec - last_frame_time
    last_frame_time = t_sec
    
    # Update track labels from winsdk data thread
    lbl_title.configure(text=media_data['title'])
    lbl_artist.configure(text=media_data['artist'])
    lbl_status_indicator.configure(text=media_data['status'])
    
    if media_data['status'] == 'PLAYING':
        lbl_status_indicator.configure(text_color="#2ecc71")
    else:
        lbl_status_indicator.configure(text_color="#e74c3c")
        
    # Set progress bars
    prog_bass.set(audio_data['bass'])
    prog_mid.set(audio_data['mid'])
    prog_treb.set(audio_data['treb'])
    
    # Audio variables
    b = audio_data['bass']
    m = audio_data['mid']
    t = audio_data['treb']
    vol = audio_data['volume']
    nrg = audio_data['energy']
    
    # --- STYLE CHOREOGRAPHER TRANSITION ---
    dt_style = t_sec - style_start_time
    if dt_style > style_duration:
        current_style = random.choice([x for x in styles if x != current_style])
        style_start_time = t_sec
        style_duration = random.uniform(5.0, 10.0)
        lbl_style.configure(text=current_style)
        
    # Determine targets based on play status
    if media_data['status'] == 'PLAYING':
        # --- GENERATIVE MOVEMENT MATH ---
        if current_style == "STYLE_POP_LOCK":
            # Snapping popping moves
            beat_step = int((t_sec * 2.2) % 4)
            if beat_step in [0, 2]:
                target_angles[0] = 90 + (math.sin(t_sec * 2) * 50)
                target_angles[3] = 145 + (math.cos(t_sec * 3) * 35)
            else:
                target_angles[1] = 145 - (b * 60)
                target_angles[2] = 0 + (b * 120)
                target_angles[4] = 60 if b > 0.5 else 120
            target_angles[5] = 90 if t > 0.4 else 0
            
        elif current_style == "STYLE_LIQUID":
            # Serpentine fluid wave S-Curves
            rot_wave = math.sin(t_sec * 1.5) * 25
            elb_wave = math.cos(t_sec * 1.5) * 55
            target_angles[0] = 90
            target_angles[1] = 100 + rot_wave
            target_angles[2] = 60 + elb_wave
            target_angles[3] = 145 + math.sin(t_sec * 2.0) * 20
            target_angles[4] = 80 + math.sin(t_sec) * 30
            target_angles[5] = 45 + (vol * 45)
            
        elif current_style == "STYLE_HEADBANGER":
            # Rhythmic headbanging
            target_angles[0] = 90 + math.sin(t_sec) * 30
            target_angles[1] = 145 - (b * 70)
            target_angles[2] = 0 + (b * 135)
            target_angles[3] = 145 + math.sin(t_sec * 5.0) * (t * 45)
            target_angles[4] = 80 + math.cos(t_sec * 4.0) * (vol * 50)
            target_angles[5] = 90 if t > 0.3 else 0
            
        elif current_style == "STYLE_CONDUCTOR":
            # Conductor Infinity Loop sweeps
            fig_x = math.sin(t_sec * 1.1)
            fig_y = math.sin(t_sec * 2.2)
            target_angles[0] = 90 + fig_x * 55
            target_angles[1] = 100 + fig_y * 30
            target_angles[2] = 40 + fig_x * 40
            target_angles[3] = 145 + fig_x * 25
            target_angles[4] = 80 + fig_y * 30
            target_angles[5] = 45
            
    else:
        # PAUSED STATE: Smoothly transition to Home/Reset Pose and freeze!
        for i in range(6):
            target_angles[i] = HOME_STATE[i]
            
    # Apply Butter-Smooth Smoothing Filters to all joints
    for i in range(6):
        current_angles[i] = smoothers[i].update(target_angles[i])
        
    # Serial Send to ESP32 @ 30 FPS
    if t_sec - last_send_time > 0.033:
        b_val, r_val, e_val, w_val, u_val, c_val = [int(a) for a in current_angles]
        cmd = f"<{b_val},{r_val},{e_val},{w_val},{u_val},{c_val}>\n"
        ser.write(cmd.encode('utf-8'))
        last_send_time = t_sec
        
    # Queue up the next loop execution in 16ms (~60Hz update rate)
    app.after(16, update_ui_and_robot)

# Close cleanly on window exit
def on_closing():
    try:
        ser.write(b"<HOME>\n")
        time.sleep(1.5)
        ser.write(b"<RELAX>\n")
        ser.close()
    except Exception:
        pass
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)

# Start the continuous UI/Motor loop
app.after(16, update_ui_and_robot)
app.mainloop()
