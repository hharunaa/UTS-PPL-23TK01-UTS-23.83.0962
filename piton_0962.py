# /mnt/data/zigzag.py
# Revisi besar: zigzag modern + automation features
import time
import sys
import os
import math
import random
import threading
import json
import shutil
import datetime
from collections import deque

# optional imports
try:
    import psutil
except Exception:
    psutil = None

# Try to use pyfiglet for ASCII big text; fallback if not available
try:
    import pyfiglet
except Exception:
    pyfiglet = None

# Terminal helpers
CSI = "\x1b["
RESET = CSI + "0m"

ANSI_COLORS = [
    CSI + "31m",  # Red
    CSI + "33m",  # Yellow
    CSI + "32m",  # Green
    CSI + "36m",  # Cyan
    CSI + "34m",  # Blue
    CSI + "35m",  # Magenta
]

# Temperature gradient colors (left=blue, right=red)
TEMP_COLORS = [
    CSI + "34m",  # Blue
    CSI + "36m",  # Cyan
    CSI + "32m",  # Green
    CSI + "33m",  # Yellow
    CSI + "31m",  # Red
]

# Patters available (6 patterns)
PATTERNS = ["********", "########", "========", ">>>>><<<<<", "~~~~~~", "++++++"]

# CONFIG defaults (can be hot-reloaded from config.json)
CONFIG_PATH = "config.json"
config = {
    "base_speed": 0.09,
    "min_speed": 0.02,
    "max_speed": 0.6,
    "sin_intensity": 0.5,
    "pattern_cycles_before_switch": 3,
    "color_rotate_frames": 10,
    "earthquake_strength": 2,
    "tail_length": 4,
    "auto_night_start": 18,
    "auto_night_end": 6,
    "motivation_time": "08:00",
    "daily_log_time": "20:00",
    "monitor_interval_minutes": 60,
    "auto_save_interval": 10,
    "max_runtime_minutes": None,  # None means infinite
}

# Shared state
state = {
    "running": True,
    "paused": False,
    "frame": 0,
    "pattern_index": 0,
    "pattern_cycle_count": 0,
    "color_index": 0,
    "earthquake": False,
    "use_color": True,
    "big_text": None,
    "max_indent": max(10, (os.getpid() % 15) + 5),
    "start_time": time.time(),
    "last_config_mtime": None,
    "last_config_check": 0,
    "last_log_time": 0,
    "last_monitor": 0,
}

# tail buffer for persistent tail effect
tail_buffer = deque(maxlen=config["tail_length"])

# simple logger
def log(msg, fname="zigzag.log"):
    ts = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
    try:
        with open(fname, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

# config hot-reload
def reload_config():
    try:
        if not os.path.exists(CONFIG_PATH):
            return
        mtime = os.path.getmtime(CONFIG_PATH)
        if state["last_config_mtime"] is None or mtime != state["last_config_mtime"]:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            config.update(data)
            state["last_config_mtime"] = mtime
            log("Config reloaded.")
    except Exception as e:
        log("Config reload failed: " + str(e))

# ASCII big text builder
def build_big_text(s):
    if not s:
        return None
    if pyfiglet:
        try:
            fig = pyfiglet.Figlet(font='standard')
            return fig.renderText(s)
        except Exception:
            pass
    # fallback: naive enlarge by repeating characters to make them 'big'
    lines = []
    for r in range(6):  # 6 rows per char
        row = []
        for ch in s.upper():
            # simple pattern for A-Z and digits
            if ch == " ":
                row.append("   ")
            else:
                # two-line stylized block: repeat ch r+1 times
                rep = (r % 3) + 1
                row.append(ch * rep + " ")
        lines.append(" ".join(row))
    return "\n".join(lines)

# non-blocking keyboard helper (cross-platform)
if os.name == "nt":
    import msvcrt

    def kb_hit():
        return msvcrt.kbhit()

    def kb_get():
        return msvcrt.getch().decode(errors="ignore")
else:
    import sys
    import select
    import tty
    import termios

    def kb_hit():
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        return bool(dr)

    def kb_get():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

# Scheduler helpers
def check_and_fire_schedulers():
    now = datetime.datetime.now()
    # motivation
    try:
        mh, mm = map(int, config["motivation_time"].split(":"))
        if now.hour == mh and now.minute == mm and time.time() - state["last_log_time"] > 50:
            mot = random.choice([
                "Semangat pagi! Kamu bisa!",
                "Sedikit maju tiap hari lebih baik daripada tidak sama sekali.",
                "Jangan takut gagal; takutlah jika tidak pernah mencoba."
            ])
            print("\n" + CSI + "1m" + "[Motivation Scheduler] " + mot + RESET)
            with open("motivation.log", "a", encoding="utf-8") as f:
                f.write(f"{now.isoformat()} - {mot}\n")
            state["last_log_time"] = time.time()
    except Exception:
        pass

    # daily log
    try:
        dh, dm = map(int, config["daily_log_time"].split(":"))
        if now.hour == dh and now.minute == dm and time.time() - state.get("last_daily", 0) > 50:
            with open("daily_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{now.isoformat()} - Ran zigzag session frame {state['frame']}\n")
            state["last_daily"] = time.time()
            print("\n[Daily Log] entry recorded.")
    except Exception:
        pass

    # monitoring
    try:
        interval = config.get("monitor_interval_minutes", 60)
        if time.time() - state["last_monitor"] > interval * 60:
            cpu = psutil.cpu_percent() if psutil else None
            mem = psutil.virtual_memory().percent if psutil else None
            with open("monitor.log", "a", encoding="utf-8") as f:
                f.write(f"{now.isoformat()} CPU={cpu} MEM={mem}\n")
            state["last_monitor"] = time.time()
            print(f"\n[Monitor] CPU={cpu} MEM={mem}")
    except Exception:
        pass

# Auto-runtime efficiency mode
def runtime_efficiency_multiplier():
    runtime = time.time() - state["start_time"]
    minutes = runtime / 60.0
    if minutes <= 1:
        return 1.0  # high perf
    if minutes <= 3:
        return 1.5  # balanced
    return 2.5  # power saver

# Auto-night mode
def is_night():
    h = datetime.datetime.now().hour
    start = config.get("auto_night_start", 18)
    end = config.get("auto_night_end", 6)
    if start < end:
        return start <= h < end
    else:
        return h >= start or h < end

# Pattern switch notification
def notify_pattern_change(idx, pattern):
    msg = f"\n[Pattern Switch] New pattern #{idx}: {pattern}"
    print(msg)

# Input thread: non-blocking commands
def input_thread():
    print("[Controls] space=Pause/Resume | +=faster | -=slower | t=new text | p=toggle quake | c=toggle color | g=game | q=quit")
    while state["running"]:
        try:
            if kb_hit():
                ch = kb_get()
                if not ch:
                    time.sleep(0.01)
                    continue
                if ch == " ":
                    state["paused"] = not state["paused"]
                    print("\n[Paused]" if state["paused"] else "\n[Resumed]")
                elif ch in ["+", "="]:
                    config["base_speed"] = max(config["min_speed"], config["base_speed"] - 0.01)
                    print(f"\n[Speed] base_speed={config['base_speed']:.3f}")
                elif ch == "-":
                    config["base_speed"] = min(config["max_speed"], config["base_speed"] + 0.01)
                    print(f"\n[Speed] base_speed={config['base_speed']:.3f}")
                elif ch.lower() == "t":
                    # ask user for text in a blocking prompt (it's ok here)
                    print("\nEnter text for ASCII Big Text Builder: ", end="", flush=True)
                    txt = sys.stdin.readline().strip()
                    state["big_text"] = build_big_text(txt)
                    print("[Big text updated]")
                elif ch.lower() == "p":
                    state["earthquake"] = not state["earthquake"]
                    print(f"\n[Earthquake] {'ON' if state['earthquake'] else 'OFF'}")
                elif ch.lower() == "c":
                    state["use_color"] = not state["use_color"]
                    print(f"\n[Color Rotation] {'ON' if state['use_color'] else 'OFF'}")
                elif ch.lower() == "g":
                    launch_mini_game()
                elif ch.lower() == "q":
                    state["running"] = False
                    break
            else:
                time.sleep(0.05)
        except Exception as e:
            log("Input thread error: " + str(e))

# Simple mini-game: Tebak Angka (1-5)
def launch_mini_game():
    print("\n[Mini-Game] Tebak Angka (1-5). Tebak 3 kali atau ketik 'exit' to quit.")
    secret = random.randint(1, 5)
    tries = 3
    while tries > 0:
        try:
            print(f"Tries left: {tries}. Tebak: ", end="", flush=True)
            ans = sys.stdin.readline().strip()
            if ans.lower() == "exit":
                print("Exiting game.")
                return
            guess = int(ans)
            if guess == secret:
                print("Benar! +10 points")
                # for now just print. can integrate scoring.
                return
            elif guess < secret:
                print("Terlalu kecil.")
            else:
                print("Terlalu besar.")
            tries -= 1
        except Exception:
            print("Input invalid.")
    print("Kalah! angka nya adalah", secret)

# Render one frame line (centralized)
def render_frame(indent, pattern, color_code, quake_offset, tail_chars):
    # prepare left padding
    pad = max(0, indent + quake_offset)
    # temperature color mapping left->right
    temp_idx = int((pad / max(1, state["max_indent"])) * (len(TEMP_COLORS)-1))
    temp_color = TEMP_COLORS[temp_idx]
    s = " " * pad + pattern
    if state["use_color"]:
        out = color_code + temp_color + s + RESET
    else:
        out = s
    # combine tail: render earlier tail lines above current with faded characters
    tail_lines = []
    for i, t in enumerate(tail_chars):
        fade = i + 1
        tail_pad = max(0, t[0])
        ch = t[1]
        # faded char selection
        fade_char = '.' if fade > 2 else ':'
        tail_lines.append(" " * tail_pad + (ch if fade == 1 else fade_char))
    # we return tail_lines then current line
    return tail_lines, out

# main animation loop
def animation_loop():
    indent = 0
    increasing = True
    last_frame_time = time.time()
    cycle_count = 0
    sin_phase = 0.0
    pattern_index = state.get("pattern_index", 0)
    pattern = PATTERNS[pattern_index]
    frames_since_color = 0
    cycles_for_pattern = config["pattern_cycles_before_switch"]

    try:
        while state["running"]:
            # config reload occasionally
            if time.time() - state.get("last_config_check", 0) > 2:
                reload_config()
                state["last_config_check"] = time.time()
                # adjust max indent to terminal width
                cols = shutil.get_terminal_size((80, 20)).columns
                # keep some margin to avoid wrapping
                state["max_indent"] = max(5, min(cols - len(pattern) - 4, (os.getpid() % 15) + 10))

            if config.get("max_runtime_minutes") is not None:
                if (time.time() - state["start_time"]) > config["max_runtime_minutes"] * 60:
                    print("\n[Auto-stop] max runtime reached.")
                    state["running"] = False
                    break

            if state["paused"]:
                time.sleep(0.1)
                continue

            # schedulers
            check_and_fire_schedulers()

            # calc delta & fps
            current_time = time.time()
            delta = current_time - last_frame_time if last_frame_time > 0 else 1.0/30.0
            last_frame_time = current_time
            actual_fps = 1.0 / delta if delta > 0 else 999

            # sinusoidal auto-speed modulation (Auto-Speed Adjustment)
            sin_phase += 0.15  # phase increment (controls period)
            sin_val = math.sin(sin_phase)
            # speed multiplier from sin: map -1..1 to (1 - sin_intensity) .. (1 + sin_intensity)
            m = 1.0 + config.get("sin_intensity", 0.5) * sin_val
            runtime_mult = runtime_efficiency_multiplier()
            speed = config["base_speed"] * m * runtime_mult
            speed = max(config["min_speed"], min(config["max_speed"], speed))

            # earthquake shaker offset
            quake_offset = 0
            if state["earthquake"]:
                quake_offset = random.randint(-config.get("earthquake_strength", 2), config.get("earthquake_strength", 2))

            # auto-night mode changes pattern and speed
            if is_night():
                pattern = "########"
                speed = min(speed * 1.6, config["max_speed"])  # slower at night
            else:
                # normal pattern but may change by pattern_index
                pattern = PATTERNS[pattern_index % len(PATTERNS)]

            # tail: append current position to buffer
            tail_buffer.appendleft((indent, pattern[0] if pattern else "*"))
            tail_chars = list(tail_buffer)  # each element is (pad, char)

            # auto-color rotation
            frames_since_color += 1
            if frames_since_color >= config["color_rotate_frames"]:
                state["color_index"] = (state["color_index"] + 1) % len(ANSI_COLORS)
                frames_since_color = 0

            color_code = ANSI_COLORS[state["color_index"] % len(ANSI_COLORS)] if state["use_color"] else ""

            # temperature color mapping applied inside render_frame
            tail_lines, current_line = render_frame(indent, pattern, color_code, quake_offset, tail_chars)

            # Clear line and print tail lines above? We'll print whole screen small: tail above current
            try:
                # print tail (older entries) - only top few to simulate fading tail
                for i, tl in enumerate(reversed(tail_lines[-config["tail_length"]:])):
                    print(tl)
                # print current
                print(current_line, end="\r")
            except Exception as e:
                log("Render error: " + str(e))
                # attempt auto-recovery
                with open("error_recover.log", "a", encoding="utf-8") as f:
                    f.write(f"{datetime.datetime.now().isoformat()} Recovering from render error: {e}\n")
                time.sleep(0.5)
                continue

            # indentation movement: we keep zigzag but with variable step from sin_val
            step = 1 if sin_val >= 0 else 1
            if increasing:
                indent += step
                if indent >= state["max_indent"]:
                    increasing = False
                    cycle_count += 0.5
            else:
                indent -= step
                if indent <= 0:
                    increasing = True
                    cycle_count += 0.5

            # count full cycles (every 1.0 is a full back-and-forth)
            if cycle_count >= 1.0:
                state["pattern_cycle_count"] += 1
                cycle_count = cycle_count - 1.0
                # check pattern switch
                if state["pattern_cycle_count"] >= cycles_for_pattern:
                    state["pattern_cycle_count"] = 0
                    pattern_index = (pattern_index + 1) % len(PATTERNS)
                    notify_pattern_change(pattern_index, PATTERNS[pattern_index])

            # color rotation and frame increment
            state["frame"] += 1

            # ascii big text display once every few frames if set
            if state["big_text"] and state["frame"] % 50 == 0:
                print("\n--- ASCII BIG TEXT ---")
                print(state["big_text"])

            # logging auto-benchmark occasionally
            if state["frame"] % 200 == 0:
                fps_report = f"[Auto-Benchmark] FPS approx {actual_fps:.1f} | Speed {speed:.3f}"
                log(fps_report, fname="benchmark.log")

            time.sleep(speed)
    except KeyboardInterrupt:
        state["running"] = False
    except Exception as e:
        log("Animation loop fatal: " + str(e), fname="fatal.log")
        state["running"] = False

# Start input thread
t_input = threading.Thread(target=input_thread, daemon=True)
t_input.start()

# Start animation loop in main thread
try:
    animation_loop()
finally:
    state["running"] = False
    print("\nExiting. Goodbye!")
