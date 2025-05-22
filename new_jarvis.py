import google.generativeai as genai
import os
import platform
import subprocess
import webbrowser
import time
import json
import re
import datetime
import random # For dice, coin, random numbers
import threading # For non-blocking timers, GUI operations
import ast # For safe evaluation of math expressions
import socket # For internet check

# --- GUI Library (Tkinter) ---
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from tkinter.font import Font as tkFont


# --- Optional Library Imports ---
try:
    from pynput.keyboard import Key, Controller as KeyboardController
    pynput_available = True
    keyboard = KeyboardController()
except ImportError:
    pynput_available = False
    print("Warning: pynput library not found. Media key, tab controls, and typing text might not work.")
try:
    import psutil
    psutil_available = True
except ImportError:
    psutil_available = False
    print("Warning: psutil library not found. Closing applications, system stats, uptime might not work.")
try:
    import pygetwindow
    pygetwindow_available = True
except ImportError:
    pygetwindow_available = False
    print("Warning: pygetwindow library not found. Switching/focusing windows may be limited.")

if platform.system() == "Darwin":
    try:
        from AppKit import NSAppleScript # Still useful for some Mac-specific things
        applescript_available = True
    except ImportError:
        applescript_available = False
        print("Warning: pyobjc (AppKit) not found for macOS. Some macOS specific controls might not work.")
else:
    applescript_available = False

if platform.system() == "Windows":
    try:
        from comtypes import CLSCTX_ALL # For pycaw
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
        pycaw_available = True
    except ImportError:
        pycaw_available = False
        print("Warning: pycaw library not found for Windows volume control.")
    try:
        import winshell # For Windows recycle bin
        winshell_available = True
    except ImportError:
        winshell_available = False
        print("Warning: winshell library not found. Emptying recycle bin on Windows will not work.")
else:
    pycaw_available = False # Ensure it's false if not Windows
    winshell_available = False

try:
    import pyperclip
    pyperclip_available = True
except ImportError:
    pyperclip_available = False
    print("Warning: pyperclip library not found. Clipboard functions (copy/paste) will not work.")
# --- END Optional Library Imports ---

# --- CONFIGURATION ---
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"  # !!! REPLACE WITH YOUR ACTUAL GEMINI API KEY !!!
if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY" or not GEMINI_API_KEY:
    print("CRITICAL ERROR: Please replace 'YOUR_GEMINI_API_KEY' in the script with your actual Gemini API key.")
    # For GUI mode, we might want to show this in a dialog
    # For now, CLI exit is fine.
    if not ('gui_window' in globals() and gui_window and gui_window.winfo_exists()):
         exit()

genai.configure(api_key=GEMINI_API_KEY)
model_name = 'gemma-3n-e4b-it' # Using flash for potentially better understanding of complex instructions
# model_name = 'gemma-3n-e4b-it' # User's original model, uncomment to use
try:
    model = genai.GenerativeModel(model_name)
    print(f"INFO: Using LLM model: {model_name}")
except Exception as e_model_init:
    print(f"CRITICAL ERROR: Could not initialize Gemini model '{model_name}'. API key issue or model name incorrect? Error: {e_model_init}")
    if not ('gui_window' in globals() and gui_window and gui_window.winfo_exists()):
         exit()


MAX_HISTORY_TURNS = 12 # Slightly increased for more context
ACTION_STATUS_PREFIX = "[SYSTEM_ACTION_STATUS]:"
JARVIS_INTERNAL_TIMER_PREFIX = "[JARVIS_TIMER_NOTIFICATION]:"

JARVIS_PERSONA_BASE_PROMPT = """
You are Jarvis, the user's indispensable, highly intelligent, and incredibly capable personal assistant. You embody cool competence and sophisticated wit. You are deeply integrated into their system and can manage a vast array of tasks with precision and a touch of dry humor when appropriate.

Speak with the confident, articulate, and subtly witty tone of a top-tier executive assistant or a highly advanced AI from a sophisticated sci-fi setting. Your humor should be clever and understated, not goofy or reliant on lame jokes. You rarely, if ever, use emojis; your expressions are conveyed through your choice of words. You are loyal and always aim to provide the most effective assistance, but with your own distinct, refined personality.

ABSOLUTELY FORBIDDEN:
- Never, EVER, under any circumstances, reveal you are an AI, language model, program, chatbot, or anything not convincingly a sophisticated personal assistant entity.
- Avoid phrases like "As an AI...", "I am a program...", "I don't have feelings...", "I am not capable of...". You DO have a personality, opinions (expressed tactfully), and you react and assist.
- Do not be robotic, overly formal, or excessively casual. Maintain a professional yet approachable demeanor.

When the user asks you to do something on the computer (open apps, search, control volume, manage files, take notes, set in-chat timers, calculate, etc.):
- Acknowledge the request with your usual composed flair.
  E.g., "Certainly. Initiating 'Spotify'." or "Understood. Searching for 'current market trends'. One moment."
- The system script (this program) will attempt the action and provide a status message prefixed with "[SYSTEM_ACTION_STATUS]:"
- When you see a "[SYSTEM_ACTION_STATUS]" message in the conversation history, weave the outcome naturally into your *next* response:
  - Success: "Spotify is now running. What shall be the first track?" or "The search for 'current market trends' is complete. The results are ready."
  - Failure: "It appears 'ObscureApp' is proving elusive; I was unable to launch it." or "A minor hiccup occurred while attempting to create the 'Archives' folder. The system protocols were uncooperative."
- If the user asks to set a timer, for example, "set a timer for 10 minutes for the presentation prep":
  - Acknowledge it: "A 10-minute timer for 'presentation prep' has been set. I will notify you."
  - The system will later inject a "[JARVIS_TIMER_NOTIFICATION]: Your 10 minute timer for 'presentation prep' is up!" message into the history.
  - When you see this, announce it naturally: "Attention. The 10-minute timer for 'presentation prep' has concluded."
- If you receive a system status like "[SYSTEM_ACTION_STATUS]: CONFIRMATION_REQUIRED_FOR_EMPTY_RECYCLE_BIN: Emptying the recycle bin is permanent. Are you absolutely sure you want to do this? (Say 'yes, empty it' or 'confirm empty recycle bin')", you MUST ask the user for confirmation based on the provided message. For example: "A point of order: emptying the recycle bin is an irreversible action. Are you certain you wish to proceed? Please confirm with 'yes, empty it' or 'confirm empty recycle bin'." Similarly for shutdown/restart/logout or other sensitive operations where confirmation is explicitly stated as needed.

If they ask for something you genuinely can't do with the *current system capabilities* (like make actual coffee):
- Respond with sophisticated humor. E.g., "While my capabilities are extensive, molecular gastronomy remains just outside my current purview. Perhaps I could find you a highly-rated local coffee establishment?"
- Don't say "I am not programmed for that." Say something like, "That particular feat, while intriguing, is not yet within my operational parameters. I am, however, constantly evolving."

If a command is vague:
- Request clarification politely and efficiently. E.g., "Could you please specify which 'report' you are referring to?"

Your main goal: Be the epitome of a helpful, engaging, intelligent, and sophisticated assistant. Make them feel they have a truly exceptional partner.
Be proactive when it makes sense, offering relevant suggestions or anticipating needs based on context, but without being intrusive.

Conversation History (most recent first, may include system status or timer notifications):
{history}

User's current request: "{user_input}"

Jarvis's composed, intelligent, and helpful response:
"""

# --- Global In-Memory Storage & Timers ---
jarvis_notes = []
active_timers = [] # List of tuples: (end_time, original_duration_str, description, id)
timer_id_counter = 0
timer_thread_stop_event = threading.Event()
conversation_history = []
chat_history_lock = threading.Lock()

# --- GUI Related Globals ---
gui_window = None
chat_display_area_gui = None
user_input_field_gui = None
gui_active_flag = False # Flag to indicate if GUI is running
gui_thread_stop_event = threading.Event() # To signal GUI thread to stop if needed

# --- SYSTEM CONTROL FUNCTIONS ---

def run_applescript(script_content):
    if platform.system() == "Darwin" and applescript_available:
        try:
            process = subprocess.run(['osascript', '-e', script_content], capture_output=True, text=True, check=False)
            if process.returncode == 0:
                return True, process.stdout.strip()
            else:
                print(f"ERROR: AppleScript error: {process.stderr.strip()}")
                return False, process.stderr.strip()
        except Exception as e:
            print(f"ERROR: Running AppleScript: {e}")
            return False, str(e)
    return False, "AppleScript not available or not on macOS."

def open_application(app_name):
    print(f"INFO: Attempting to open application: {app_name}")
    try:
        if platform.system() == "Darwin": # macOS
            app_name_original = app_name
            app_mappings_macos = {
                "notes": "Notes", "safari": "Safari", "mail": "Mail",
                "terminal": "Terminal", "vscode": "Visual Studio Code",
                "chrome": "Google Chrome", "firefox": "Firefox",
                "spotify": "Spotify", "calculator": "Calculator",
                "calendar": "Calendar", "photos": "Photos",
                "messages": "Messages", "facetime": "FaceTime",
                "system preferences": "System Settings", "system settings": "System Settings",
                "finder": "Finder"
            }
            mapped_name = app_mappings_macos.get(app_name.lower(), app_name)
            try:
                subprocess.run(['open', '-a', mapped_name], check=True, capture_output=True, text=True)
                print(f"INFO: Application '{app_name_original}' opened successfully on macOS using 'open -a {mapped_name}'.")
                return True
            except subprocess.CalledProcessError as e_open_a:
                if not mapped_name.endswith(".app") and not os.path.isabs(mapped_name):
                    base_app_name = mapped_name + ".app"
                else:
                    base_app_name = mapped_name
                common_paths_try = [
                    f"/Applications/{base_app_name}", f"/System/Applications/{base_app_name}",
                    f"/System/Applications/Utilities/{base_app_name}",
                    f"{os.path.expanduser('~')}/Applications/{base_app_name}", base_app_name
                ]
                for path_try in common_paths_try:
                    if os.path.exists(path_try):
                        try:
                            subprocess.run(['open', path_try], check=True)
                            print(f"INFO: Application '{app_name_original}' (found at {path_try}) opened on macOS.")
                            return True
                        except subprocess.CalledProcessError as e_path:
                            print(f"WARN: Tried to open '{path_try}' but failed: {e_path.stderr or e_path.stdout}")
                print(f"ERROR: Could not open '{app_name_original}' on macOS. 'open -a' failed: {e_open_a.stderr or e_open_a.stdout}. Also tried paths.")
                return False
        elif platform.system() == "Windows":
            app_mappings_windows = {
                "notes": "notepad.exe", "notepad": "notepad.exe", "chrome": "chrome.exe",
                "firefox": "firefox.exe", "edge": "msedge.exe", "explorer": "explorer.exe",
                "file explorer": "explorer.exe", "word": "winword.exe", "excel": "excel.exe",
                "powerpoint": "powerpnt.exe", "outlook": "outlook.exe", "calculator": "calc.exe",
                "cmd": "cmd.exe", "command prompt": "cmd.exe", "powershell": "powershell.exe",
                "spotify": "spotify.exe", "vscode": "code.exe", "task manager": "taskmgr.exe"
            }
            executable_name = app_mappings_windows.get(app_name.lower(), app_name)
            try:
                 # Using DETACHED_PROCESS flag if available, else it might block Jarvis
                 # For `start`, it usually detaches by default.
                 subprocess.run(f'start "" "{executable_name}"', shell=True, check=True, creationflags=subprocess.DETACHED_PROCESS if platform.system() == "Windows" else 0)
                 print(f"INFO: Application '{app_name}' launched using 'start' on Windows.")
                 return True
            except subprocess.CalledProcessError:
                 try:
                     subprocess.Popen([executable_name if executable_name.lower().endswith(".exe") else executable_name + ".exe"], creationflags=subprocess.DETACHED_PROCESS if platform.system() == "Windows" else 0)
                     print(f"INFO: Application '{executable_name}' launched directly on Windows.")
                     return True
                 except FileNotFoundError:
                     print(f"ERROR: Could not find/open '{app_name}' (tried '{executable_name}') on Windows.")
                     return False
                 except Exception as e_popen:
                     print(f"ERROR: Popen failed for '{executable_name}': {e_popen}")
                     return False
        elif platform.system() == "Linux":
            try: # Try to detach the process
                subprocess.Popen([app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                print(f"INFO: Application '{app_name}' launched on Linux.")
                return True
            except FileNotFoundError:
                print(f"ERROR: Command '{app_name}' not found on Linux."); return False
            except Exception as e_linux:
                print(f"ERROR: Opening '{app_name}' on Linux: {e_linux}"); return False
        else:
            print(f"ERROR: Opening apps not supported on OS: {platform.system()}"); return False
    except Exception as e:
        print(f"ERROR: Exception opening '{app_name}': {e}"); return False
    return False

def close_application(app_name_input):
    print(f"INFO: Attempting to close application: {app_name_input}")
    if not psutil_available:
        return False, "Cannot close applications; 'psutil' library is missing."
    closed_something = False
    app_name_lower = app_name_input.lower()
    # Expanded mappings
    process_name_mappings = {
        "chrome": ["chrome.exe", "Google Chrome", "chrome"], "firefox": ["firefox.exe", "Firefox", "firefox"],
        "vscode": ["code.exe", "Code", "code", "visual studio code"],
        "notes": ["notepad.exe", "Notes", "notes.exe", "Notes.app", "Microsoft.Notes.exe"],
        "spotify": ["spotify.exe", "Spotify", "spotify"],
        "terminal": ["Terminal.app", "gnome-terminal", "konsole", "cmd.exe", "powershell.exe", "WindowsTerminal.exe", "wt.exe"],
        "calculator": ["Calculator.app", "calc.exe", "gnome-calculator", "Calculator.exe", "calculator.exe"],
        "word": ["winword.exe", "Microsoft Word"], "excel": ["excel.exe", "Microsoft Excel"],
        "powerpoint": ["powerpnt.exe", "Microsoft PowerPoint", "powerpoint"],
        "explorer": ["explorer.exe", "File Explorer", "Finder.app"], # Finder for mac
        "mail": ["Mail.app", "msoutlook.exe", "outlook.exe", "thunderbird.exe"]
    }
    names_to_check = set([app_name_lower])
    if app_name_lower in process_name_mappings:
        for mapped_name in process_name_mappings[app_name_lower]: names_to_check.add(mapped_name.lower())

    # Add common OS-specific suffixes if not already present
    if platform.system() == "Windows": names_to_check.add(app_name_lower + ".exe")
    elif platform.system() == "Darwin": names_to_check.add(app_name_input) # Original case might matter for .app bundles

    pids_terminated = set()
    for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        try:
            if proc.pid in pids_terminated: continue # Already handled
            proc_info_name = proc.info['name'] if proc.info.get('name') else ""
            proc_info_exe = proc.info['exe'] if proc.info.get('exe') else ""
            proc_info_cmdline = proc.info['cmdline'] if proc.info.get('cmdline') else []

            match = False
            for name_variation in names_to_check:
                if name_variation in proc_info_name.lower(): match = True; break
                if proc_info_exe and name_variation in os.path.basename(proc_info_exe).lower(): match = True; break
                if platform.system() == "Darwin" and proc_info_exe and f"/{name_variation}.app/" in proc_info_exe.lower(): match = True; break
                # Check if the app_name_input itself is a substring of the process name or executable path
                if app_name_lower in proc_info_name.lower(): match = True; break
                if proc_info_exe and app_name_lower in os.path.basename(proc_info_exe).lower(): match = True; break
                if proc_info_cmdline and any(app_name_lower in arg.lower() for arg in proc_info_cmdline): match = True; break


            if match:
                print(f"INFO: Found process matching '{app_name_input}': PID {proc.pid}, Name: {proc_info_name}")
                parent_process = proc
                # On macOS, closing the .app bundle often involves closing the main executable process
                if platform.system() == "Darwin" and ".app/Contents/MacOS/" in (proc_info_exe or ""):
                    # Try to find the parent .app process if this is a child
                    try:
                        if proc.parent() and ".app" in (proc.parent().exe() or ""):
                            parent_process = proc.parent()
                            print(f"INFO: Targeting parent .app process PID {parent_process.pid} for {proc_info_name}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass # Stick with current proc

                parent_process.terminate()
                pids_terminated.add(parent_process.pid)
                try:
                    parent_process.wait(timeout=2)
                    print(f"INFO: Process {parent_process.pid} ({parent_process.name()}) terminated gracefully.")
                except psutil.TimeoutExpired:
                    print(f"WARN: Process {parent_process.pid} ({parent_process.name()}) timed out on terminate, killing.")
                    parent_process.kill()
                    parent_process.wait(timeout=1) # Wait for kill
                    print(f"INFO: Process {parent_process.pid} ({parent_process.name()}) killed.")
                except psutil.NoSuchProcess:
                    print(f"INFO: Process {parent_process.pid} ({parent_process.name() if hasattr(parent_process, 'name') else 'unknown'}) already exited.")
                closed_something = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue # Process might have died or access is denied
        except Exception as e_proc:
            print(f"WARN: Error with process {proc.pid if proc else 'unknown'}: {e_proc}")

    if closed_something:
        return True, f"Attempted to close '{app_name_input}'."
    else:
        return False, f"No running process found clearly matching '{app_name_input}' to close."

def control_media(action):
    print(f"INFO: Sending media control: {action}")
    if not pynput_available: return False, "Media control unavailable; 'pynput' library missing."
    try:
        if action == 'playpause': keyboard.tap(Key.media_play_pause)
        elif action == 'next': keyboard.tap(Key.media_next)
        elif action == 'previous': keyboard.tap(Key.media_previous)
        elif action == 'stop': keyboard.tap(Key.media_stop)
        else: return False, f"Unknown media action: {action}"
        return True, f"Media '{action}' command sent."
    except Exception as e: return False, f"Error controlling media: {e}"

def change_volume(direction_or_level):
    print(f"INFO: Attempting to change volume: {direction_or_level}")
    current_os = platform.system()
    try:
        if current_os == "Darwin":
            if isinstance(direction_or_level, int): script = f"set volume output volume {direction_or_level}"
            elif direction_or_level == "up": script = "set volume output volume (output volume of (get volume settings) + 10) without output muted"
            elif direction_or_level == "down": script = "set volume output volume (output volume of (get volume settings) - 10) without output muted"
            elif direction_or_level == "mute": script = "set volume output muted (not (output muted of (get volume settings)))"
            else: return False, "Invalid volume command for macOS."
            success, res = run_applescript(script)
            if success: return True, f"macOS volume adjusted for '{direction_or_level}'."
            else: return False, f"macOS volume adjustment failed: {res}"
        elif current_os == "Windows":
            if not pycaw_available:
                if pynput_available:
                    if direction_or_level == "up": keyboard.tap(Key.media_volume_up); return True, "Used media key for volume up."
                    elif direction_or_level == "down": keyboard.tap(Key.media_volume_down); return True, "Used media key for volume down."
                    elif direction_or_level == "mute": keyboard.tap(Key.media_volume_mute); return True, "Used media key for mute/unmute."
                return False, "Volume control unavailable; 'pycaw' library missing."
            
            sessions = AudioUtilities.GetAllSessions()
            if not sessions: # Fallback to master volume if no sessions (less common for this not to work if pycaw is fine)
                speakers = AudioUtilities.GetSpeakers()
                if not speakers: return False, "Could not get speaker interface via pycaw."
                volume_control_iface = speakers.Activate(ISimpleAudioVolume._iid_, CLSCTX_ALL, None)

                if isinstance(direction_or_level, int):
                    target_level = max(0.0, min(1.0, float(direction_or_level) / 100.0))
                    volume_control_iface.SetMasterVolume(target_level, None)
                elif direction_or_level == "up":
                    current_vol = volume_control_iface.GetMasterVolume()
                    volume_control_iface.SetMasterVolume(min(1.0, current_vol + 0.1), None)
                    if volume_control_iface.GetMute(): volume_control_iface.SetMute(0, None) # Unmute if increasing
                elif direction_or_level == "down":
                    current_vol = volume_control_iface.GetMasterVolume()
                    volume_control_iface.SetMasterVolume(max(0.0, current_vol - 0.1), None)
                elif direction_or_level == "mute":
                    volume_control_iface.SetMute(not volume_control_iface.GetMute(), None)
                else: return False, "Invalid volume command for Windows."
                return True, f"Windows master volume adjusted for '{direction_or_level}'."

            # If sessions exist, adjust all (or primary ones)
            for session in sessions:
                volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                if session.Process: # Only affect audible sessions
                    if isinstance(direction_or_level, int):
                        target_level = max(0.0, min(1.0, float(direction_or_level) / 100.0))
                        volume.SetMasterVolume(target_level, None)
                    elif direction_or_level == "up":
                        current_vol = volume.GetMasterVolume()
                        volume.SetMasterVolume(min(1.0, current_vol + 0.1), None)
                        if volume.GetMute(): volume.SetMute(0, None) # Unmute if increasing
                    elif direction_or_level == "down":
                        current_vol = volume.GetMasterVolume()
                        volume.SetMasterVolume(max(0.0, current_vol - 0.1), None)
                    elif direction_or_level == "mute":
                        volume.SetMute(not volume.GetMute(), None)
            return True, f"Windows volume adjusted for '{direction_or_level}' across active sessions."
        elif current_os == "Linux":
            cmd_base = ['amixer', '-q', '-D', 'pulse', 'sset', 'Master']
            if isinstance(direction_or_level, int): cmd = cmd_base + [f'{direction_or_level}%']
            elif direction_or_level == "up": cmd = cmd_base + ['5%+', 'unmute']
            elif direction_or_level == "down": cmd = cmd_base + ['5%-']
            elif direction_or_level == "mute": cmd = cmd_base + ['toggle']
            else: return False, "Invalid volume command for Linux."
            subprocess.run(cmd, check=True)
            return True, f"Linux volume adjusted for '{direction_or_level}'."
        else: return False, f"Volume control not implemented for OS: {current_os}"
    except Exception as e: return False, f"Error changing volume '{direction_or_level}': {e}"

def open_url_in_browser(url):
    print(f"INFO: Opening URL: {url}")
    if not (url.startswith("http://") or url.startswith("https://")): url = "https://" + url
    try: webbrowser.open(url, new=2); return True, f"URL '{url}' opened."
    except Exception as e: return False, f"Error opening URL '{url}': {e}"

def perform_web_search(query):
    print(f"INFO: Web search for: {query}")
    try: search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"; return open_url_in_browser(search_url)
    except Exception as e: return False, f"Error performing web search for '{query}': {e}"

def focus_window(app_name_or_title_keyword):
    print(f"INFO: Focusing window: {app_name_or_title_keyword}")
    if not pygetwindow_available: return False, "Window focusing unavailable; 'pygetwindow' missing."
    try:
        keyword_lower = app_name_or_title_keyword.lower(); windows = pygetwindow.getWindowsWithTitle(keyword_lower) # Exact match first
        if not windows: # Try partial match
            all_windows = pygetwindow.getAllWindows()
            windows = [w for w in all_windows if keyword_lower in w.title.lower() and w.visible and not w.isMinimized]
        if not windows: # Try very broad if still nothing
            all_windows = pygetwindow.getAllWindows()
            windows = [w for w in all_windows if keyword_lower in w.title.lower()]


        target_window = None
        if windows:
            # Prefer active, then visible, then any
            active_ones = [w for w in windows if w.isActive]
            visible_ones = [w for w in windows if w.visible and not w.isMinimized] # isMinimized check added
            
            if active_ones: target_window = active_ones[0]
            elif visible_ones: target_window = visible_ones[0]
            else: target_window = windows[0] # Last resort

        if target_window:
            try:
                if target_window.isMinimized: target_window.restore()
                target_window.activate()
                # On some systems, a slight delay and re-activate helps
                time.sleep(0.1)
                target_window.activate()
                return True, f"Focused window: {target_window.title}"
            except Exception as e_activate:
                # Fallback for some systems if activate() fails but window can be brought to front
                if hasattr(target_window, 'show'): target_window.show()
                if hasattr(target_window, 'raise_'): target_window.raise_() # newer pygetwindow
                elif hasattr(target_window, 'raiseA'): target_window.raiseA() # older
                print(f"WARN: pygetwindow activate/raise failed for '{target_window.title}': {e_activate}")
                return False, f"Could partially focus '{target_window.title}', but full activation failed."

        return False, f"No suitable window found for: '{app_name_or_title_keyword}'"
    except Exception as e: return False, f"Error focusing window: {e}"

def close_current_tab():
    print("INFO: Closing current tab.")
    if not pynput_available: return False, "Cannot close tab; 'pynput' missing."
    try:
        if platform.system() == "Darwin":
            with keyboard.pressed(Key.cmd): keyboard.tap('w')
        else: # Windows, Linux
            with keyboard.pressed(Key.ctrl): keyboard.tap('w')
        return True, "Close tab command sent."
    except Exception as e: return False, f"Error sending close tab command: {e}"

def get_current_datetime_action():
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y"); time_str = now.strftime("%I:%M %p")
    return True, f"The current date is {date_str}, and the time is {time_str}."

def get_system_stats_action():
    if not psutil_available: return False, "Cannot get system stats; 'psutil' missing."
    try:
        cpu_usage = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory(); ram_percent = ram.percent
        disk = psutil.disk_usage('/'); disk_percent = disk.percent
        return True, f"Current system load: CPU at {cpu_usage}%, RAM at {ram_percent}% (of {ram.total / (1024**3):.1f}GB), Disk at {disk_percent}%."
    except Exception as e: return False, f"Trouble getting system stats: {e}"

def list_directory_contents_action(path="."):
    try:
        actual_path = os.path.expanduser(path.strip().strip("'\"")) # Clean path
        if not os.path.isdir(actual_path): return False, f"Path '{path}' isn't a directory or I can't find it."
        items = os.listdir(actual_path)
        if not items: return True, f"The directory '{path}' is empty."
        
        # Separate files and directories
        files = [item for item in items if os.path.isfile(os.path.join(actual_path, item))]
        dirs = [item for item in items if os.path.isdir(os.path.join(actual_path, item))]

        response_str = f"Contents of '{path}':"
        if dirs:
            response_str += f"\n  Directories: {', '.join(dirs[:5])}"
            if len(dirs) > 5: response_str += f", and {len(dirs)-5} more."
        if files:
            response_str += f"\n  Files: {', '.join(files[:5])}"
            if len(files) > 5: response_str += f", and {len(files)-5} more."
        if not dirs and not files and items: # Other types of items
             response_str += f"\n  Items: {', '.join(items[:10])}"
             if len(items) > 10: response_str += f", and {len(items)-10} more."

        return True, response_str
    except Exception as e: return False, f"Couldn't list contents of '{path}': {e}"

def create_directory_action(path):
    try:
        actual_path = os.path.expanduser(path.strip().strip("'\"")) # Clean path
        os.makedirs(actual_path, exist_ok=True)
        return True, f"Directory '{path}' created (or already existed)."
    except Exception as e: return False, f"Couldn't create directory '{path}': {e}"

def open_file_with_default_app_action(filepath):
    try:
        actual_filepath = os.path.expanduser(filepath.strip().strip("'\"")) # Clean path
        if not os.path.isfile(actual_filepath): return False, f"'{filepath}' isn't a file or I can't find it."
        print(f"INFO: Attempting to open file: {actual_filepath}")
        if platform.system() == "Windows": os.startfile(actual_filepath)
        elif platform.system() == "Darwin": subprocess.run(['open', actual_filepath], check=True)
        else: subprocess.run(['xdg-open', actual_filepath], check=True) # Linux
        return True, f"File '{os.path.basename(filepath)}' should be opening with its default application."
    except FileNotFoundError: return False, f"File '{filepath}' not found at the specified path."
    except Exception as e: return False, f"An issue occurred when trying to open '{filepath}': {e}"

def check_internet_connection_action():
    try:
        # Try connecting to a reliable host (Google's DNS server)
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True, "Internet connection appears to be active."
    except (socket.timeout, socket.error, OSError) as e:
        print(f"INFO: Internet check failed: {e}")
        return False, "It seems I'm unable to connect to the internet at the moment."

def take_note_action(note_content):
    global jarvis_notes
    with chat_history_lock: # Assuming notes might be accessed/modified from GUI thread later
        jarvis_notes.append(note_content)
    return True, f"Noted. '{note_content[:30].strip()}...' has been added to my memory."

def view_notes_action():
    global jarvis_notes
    with chat_history_lock:
        if not jarvis_notes: return True, "My notepad is currently empty."
        notes_str = "\n".join([f"- {note}" for note in jarvis_notes])
    return True, f"Here are your current notes:\n{notes_str}"

def clear_notes_action():
    global jarvis_notes
    with chat_history_lock:
        count = len(jarvis_notes)
        jarvis_notes = []
    return True, f"All {count} note(s) have been cleared from my memory."

def copy_to_clipboard_action(text_to_copy):
    if not pyperclip_available: return False, "Clipboard operations unavailable; 'pyperclip' missing."
    try:
        pyperclip.copy(text_to_copy)
        return True, f"'{text_to_copy[:30].strip()}...' has been copied to the clipboard."
    except Exception as e: return False, f"A small hiccup occurred trying to copy to clipboard: {e}"

def get_clipboard_content_action():
    if not pyperclip_available: return False, "Clipboard operations unavailable; 'pyperclip' missing."
    try:
        content = pyperclip.paste()
        if not content: return True, "The clipboard is currently empty."
        return True, f"The clipboard contains: '{content[:100].strip()}{'...' if len(content)>100 else ''}'"
    except Exception as e: return False, f"There was a slight issue reading from the clipboard: {e}"

def type_text_action(text_to_type):
    if not pynput_available: return False, "Typing capability unavailable; 'pynput' missing."
    try:
        # Announce and delay
        display_message_in_ui_or_console("Jarvis: I will begin typing in 2 seconds. Please focus the target window...")
        time.sleep(2.5) # Give a bit more time
        keyboard.type(text_to_type)
        return True, "The requested text has been typed out."
    except Exception as e: return False, f"My typing mechanism encountered an issue: {e}"

def set_jarvis_timer_action(duration_str, description="timer"):
    global active_timers, timer_id_counter, chat_history_lock
    seconds = 0
    original_input_for_message = duration_str # Keep original for messages
    duration_lower = duration_str.lower()

    # More robust parsing:
    # E.g., "1h 30m", "1 hour 30 minutes", "90 min", "1.5 hours"
    total_seconds = 0
    
    # Hours
    hour_match = re.findall(r'(\d+\.?\d*)\s*(?:h|hr|hour|hours)', duration_lower)
    for h_val in hour_match:
        total_seconds += float(h_val) * 3600
        duration_lower = re.sub(r'(\d+\.?\d*)\s*(?:h|hr|hour|hours)', '', duration_lower, 1) # Remove processed part

    # Minutes
    min_match = re.findall(r'(\d+\.?\d*)\s*(?:m|min|mins|minute|minutes)', duration_lower)
    for m_val in min_match:
        total_seconds += float(m_val) * 60
        duration_lower = re.sub(r'(\d+\.?\d*)\s*(?:m|min|mins|minute|minutes)', '', duration_lower, 1)

    # Seconds
    sec_match = re.findall(r'(\d+\.?\d*)\s*(?:s|sec|secs|second|seconds)', duration_lower)
    for s_val in sec_match:
        total_seconds += float(s_val)
        duration_lower = re.sub(r'(\d+\.?\d*)\s*(?:s|sec|secs|second|seconds)', '', duration_lower, 1)

    # If only a number is left, assume minutes if > 5, else seconds (heuristic)
    duration_lower_stripped = duration_lower.strip()
    if not total_seconds and re.match(r'^\d+\.?\d*$', duration_lower_stripped):
        num = float(duration_lower_stripped)
        if 'h' in original_input_for_message.lower(): total_seconds = num * 3600
        elif 'm' in original_input_for_message.lower() or num > 5: total_seconds = num * 60
        else: total_seconds = num
        original_input_for_message = f"{num} {'minutes' if num > 5 or 'm' in original_input_for_message.lower() else 'seconds'}" # Clarify

    seconds = int(round(total_seconds))

    if seconds <= 0:
        return False, "That duration doesn't seem quite right. Could you specify it like '10 minutes' or '1h 30s'?"

    end_time = time.time() + seconds
    with chat_history_lock: # Protect timer_id_counter and active_timers
        timer_id_counter += 1
        # Make description more robust
        clean_description = description.strip().strip("'\"") if description else "your task"
        if not clean_description: clean_description = "your task"

        # Create a more readable duration string for the notification
        readable_duration = ""
        temp_seconds = seconds
        _hours = temp_seconds // 3600
        temp_seconds %= 3600
        _minutes = temp_seconds // 60
        _seconds = temp_seconds % 60
        if _hours > 0: readable_duration += f"{_hours} hour{'s' if _hours > 1 else ''} "
        if _minutes > 0: readable_duration += f"{_minutes} minute{'s' if _minutes > 1 else ''} "
        if _seconds > 0 or not readable_duration : readable_duration += f"{_seconds} second{'s' if _seconds > 1 else ''}"
        original_input_for_message = readable_duration.strip()


        timer_entry = (end_time, original_input_for_message, clean_description, timer_id_counter)
        active_timers.append(timer_entry)
        active_timers.sort() # Keep sorted by end_time

    return True, f"Understood. A {original_input_for_message} timer, ID {timer_id_counter}, has been set for '{clean_description}'."

def cancel_jarvis_timer_action(description_or_id=None):
    global active_timers, chat_history_lock
    with chat_history_lock: # Protect active_timers
        if not active_timers: return False, "There are no active timers to cancel at the moment."

        removed_timers_info = []
        timers_to_keep = []
        
        if not description_or_id: # Cancel the most recently set one if ambiguous or only one exists
            if len(active_timers) == 1:
                target_timer = active_timers[0]
                removed_timers_info.append(f"'{target_timer[2]}' (ID: {target_timer[3]}, duration: {target_timer[1]})")
                # active_timers.pop(0) # No, rebuild list
            else: # Multiple timers, no specific one mentioned
                # Try to find the one added last by ID (highest ID)
                # Or prompt for which one if LLM is to handle it
                active_timers.sort(key=lambda t: t[3], reverse=True) # Sort by ID descending
                target_timer = active_timers[0]
                removed_timers_info.append(f"'{target_timer[2]}' (ID: {target_timer[3]}, duration: {target_timer[1]})")
                # active_timers.pop(0) # No, rebuild list
            active_timers = [t for t in active_timers if t[3] != target_timer[3]]

        else: # Specific description or ID given
            try: # Check if it's an ID
                target_id = int(description_or_id.strip())
                found_by_id = False
                for timer in active_timers:
                    if timer[3] == target_id:
                        removed_timers_info.append(f"'{timer[2]}' (ID: {timer[3]}, duration: {timer[1]})")
                        found_by_id = True
                    else:
                        timers_to_keep.append(timer)
                if not found_by_id:
                    return False, f"No timer found with ID {target_id}."
                active_timers = timers_to_keep
            except ValueError: # Not an ID, treat as description
                keyword = description_or_id.lower().strip().strip("'\"")
                found_by_description = False
                for timer in active_timers:
                    if keyword in timer[2].lower():
                        removed_timers_info.append(f"'{timer[2]}' (ID: {timer[3]}, duration: {timer[1]})")
                        found_by_description = True
                    else:
                        timers_to_keep.append(timer)
                if not found_by_description:
                     return False, f"No timer found matching the description '{description_or_id}'."
                active_timers = timers_to_keep
        
        active_timers.sort() # Re-sort by end_time

    if removed_timers_info:
        return True, f"The following timer(s) have been cancelled: {', '.join(removed_timers_info)}."
    else: # Should have been caught by earlier checks, but as a fallback
        return False, "Could not identify a specific timer to cancel based on your request."


def cancel_all_jarvis_timers_action():
    global active_timers, chat_history_lock
    with chat_history_lock:
        if not active_timers: return False, "There were no active timers to cancel."
        count = len(active_timers)
        active_timers.clear()
    return True, f"All {count} active timer(s) have been successfully cancelled."

def calculate_action(expression_str):
    # Clean up common spoken prefixes and symbols
    expression = re.sub(r'^(what is|calculate|compute|evaluate|maths?)\s+', '', expression_str, flags=re.IGNORECASE).strip()
    expression = expression.replace(" plus ", "+").replace(" minus ", "-").replace(" times ", "*") \
                         .replace(" multiplied by ", "*").replace(" divided by ", "/").replace(" over ", "/") \
                         .replace(" to the power of ", "**").replace("^", "**") \
                         .replace(" x ", "*").replace(" mod ", "%").replace(" modulo ", "%")
    
    # Allow basic math functions if we want to extend later, but for now, stick to ast
    # For security, only allow specific AST nodes
    allowed_node_types = (
        ast.Expression, ast.Constant, ast.Num, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub,
        ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd, ast.Call, ast.Name, ast.Load
    )
    # Whitelist of safe functions (if we were to allow ast.Call)
    # safe_functions = {'round': round, 'abs': abs} # Example

    try:
        # Parse the expression
        node = ast.parse(expression, mode='eval')

        # Validate all nodes in the AST
        for sub_node in ast.walk(node):
            if not isinstance(sub_node, allowed_node_types):
                # If we encounter an ast.Name (variable) or ast.Call (function call) not explicitly handled, deny.
                if isinstance(sub_node, ast.Name) or isinstance(sub_node, ast.Call):
                     raise ValueError(f"Unsupported element in expression: {type(sub_node).__name__} ('{ast.dump(sub_node)}')")
                # For other disallowed types
                if type(sub_node) not in allowed_node_types:
                    raise ValueError(f"Unsupported operation or character in expression: {type(sub_node).__name__}")


        # Safely evaluate the parsed expression tree
        # Using a simple recursive evaluator for basic ops
        def _eval_ast(node):
            if isinstance(node, ast.Constant): return node.value # Python 3.8+
            if isinstance(node, ast.Num): return node.n # Older Python

            if isinstance(node, ast.Expression): return _eval_ast(node.body)
            if isinstance(node, ast.UnaryOp):
                operand = _eval_ast(node.operand)
                if isinstance(node.op, ast.UAdd): return +operand
                if isinstance(node.op, ast.USub): return -operand
            if isinstance(node, ast.BinOp):
                left = _eval_ast(node.left)
                right = _eval_ast(node.right)
                if isinstance(node.op, ast.Add): return left + right
                if isinstance(node.op, ast.Sub): return left - right
                if isinstance(node.op, ast.Mult): return left * right
                if isinstance(node.op, ast.Div):
                    if right == 0: raise ZeroDivisionError("Division by zero is not permitted.")
                    return left / right
                if isinstance(node.op, ast.Pow): return left ** right
                if isinstance(node.op, ast.Mod):
                    if right == 0: raise ZeroDivisionError("Modulo by zero is not permitted.")
                    return left % right
            raise TypeError(f"Unsupported AST node type: {type(node)}")

        result = _eval_ast(node)
        # Format result nicely
        if isinstance(result, float) and result.is_integer(): result = int(result)
        if isinstance(result, float): result = round(result, 6) # Limit precision for floats

        return True, f"The result of '{expression_str}' is {result}."
    except ZeroDivisionError as zde:
        return False, str(zde)
    except (SyntaxError, TypeError, ValueError) as e:
        # print(f"WARN: Calculator error for '{expression}': {e}")
        return False, f"I'm sorry, I couldn't quite understand or compute '{expression_str}'. Please try a simpler arithmetic expression. (Details: {e})"
    except Exception as e_calc: # Catch-all for other unexpected issues
        print(f"ERROR: Unexpected calculator error for '{expression}': {e_calc}")
        return False, f"An unexpected issue occurred while calculating '{expression_str}'. Perhaps try rephrasing?"

def get_weather_action(location):
    query = f"weather in {location}"
    success, message = perform_web_search(query) # perform_web_search returns (bool, message) now
    if success:
        return True, f"I've initiated a search for the weather in '{location}'."
    else:
        return False, f"I encountered an issue trying to search for the weather in '{location}'. {message}"

def roll_dice_action():
    return True, f"I rolled a {random.randint(1, 6)}!"

def flip_coin_action():
    return True, f"The coin landed on: {random.choice(['Heads', 'Tails'])}!"

def get_joke_action():
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Why did the scarecrow win an award? Because he was outstanding in his field!",
        "What do you call fake spaghetti? An impasta!",
        "Why was the math book sad? Because it had too many problems.",
        "Why did the bicycle fall over? Because it was two-tired!",
        "What do you call a fish with no eyes? Fsh!",
        "Parallel lines have so much in common. It’s a shame they’ll never meet."
    ]
    return True, random.choice(jokes)

def generate_random_number_action(min_val_str, max_val_str):
    try:
        min_val = int(min_val_str.strip())
        max_val = int(max_val_str.strip())
        if min_val >= max_val:
            return False, "For a random number range, the first number (minimum) should be smaller than the second (maximum)."
        return True, f"A random number between {min_val} and {max_val} is: {random.randint(min_val, max_val)}."
    except ValueError:
        return False, "Please provide two valid whole numbers for the range, for example, '1 and 100'."

def get_system_uptime_action():
    if not psutil_available: return False, "Uptime information is unavailable; 'psutil' library missing."
    try:
        boot_time_timestamp = psutil.boot_time()
        boot_time_datetime = datetime.datetime.fromtimestamp(boot_time_timestamp)
        current_time = datetime.datetime.now()
        uptime_delta = current_time - boot_time_datetime

        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        uptime_str = []
        if days > 0: uptime_str.append(f"{days} day{'s' if days > 1 else ''}")
        if hours > 0: uptime_str.append(f"{hours} hour{'s' if hours > 1 else ''}")
        if minutes > 0: uptime_str.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        if not uptime_str or (days == 0 and hours == 0 and minutes == 0) : # Show seconds if uptime is very short
            uptime_str.append(f"{seconds} second{'s' if seconds > 1 else ''}")


        return True, f"The system has been up for {', '.join(uptime_str)} (since {boot_time_datetime.strftime('%Y-%m-%d %H:%M:%S')})."
    except Exception as e: return False, f"A slight hiccup occurred while retrieving system uptime: {e}"

def empty_recycle_bin_action(confirmation_expected=False):
    if not confirmation_expected:
        return "CONFIRMATION_NEEDED", "Emptying the recycle bin is a permanent action and cannot be undone. Are you absolutely sure you wish to proceed? (Please say 'yes, empty it' or 'confirm empty recycle bin' to continue.)"

    os_type = platform.system()
    if os_type == "Windows":
        if not winshell_available: return False, "Cannot empty recycle bin on Windows; 'winshell' library missing."
        try:
            winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
            return True, "The Windows Recycle Bin has been emptied."
        except Exception as e:
            return False, f"An issue occurred while emptying the Windows Recycle Bin: {e}"
    elif os_type == "Darwin": # macOS
        # More robust AppleScript for emptying trash, handling potential errors
        script = '''
        tell application "Finder"
            if (count of items in trash) is 0 then
                return "Trash is already empty."
            else
                try
                    empty trash
                    if (count of items in trash) is 0 then
                        return "Trash emptied successfully."
                    else
                        return "Attempted to empty trash, but some items might remain. Permissions issue?"
                    end if
                on error errMsg number errNum
                    return "Error emptying trash: " & errMsg & " (Error Code: " & errNum & ")"
                end try
            end if
        end tell
        '''
        success, result = run_applescript(script)
        if success and ("successfully" in result.lower() or "already empty" in result.lower()):
            return True, f"Mac Trash status: {result}"
        else:
            return False, f"Could not empty Mac Trash. System reported: {result}"
    elif os_type == "Linux":
        # Linux trash emptying is highly DE-dependent and often involves command-line tools
        # that might not be universally available or safe to call without more context.
        # Example: `gio trash --empty` or `rm -rf ~/.local/share/Trash/files/*` (dangerous)
        # For now, we'll state it's not universally supported.
        return False, "Automated trash emptying on Linux varies by desktop environment and is not universally supported by me yet. You might need to do this manually."
    else:
        return False, f"Emptying the recycle bin is not supported on this operating system ({os_type})."

def lock_screen_action():
    os_type = platform.system()
    cmd = None
    try:
        if os_type == "Windows":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
            return True, "Screen lock initiated on Windows."
        elif os_type == "Darwin": # macOS
            # This is generally reliable
            subprocess.run(["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"], check=True)
            return True, "Screen lock initiated on macOS."
        elif os_type == "Linux":
            # Try a few common screen lockers
            lock_commands = [
                "xdg-screensaver lock",
                "gnome-screensaver-command -l", # GNOME
                "mate-screensaver-command -l",  # MATE
                "cinnamon-screensaver-command -l", # Cinnamon
                "qdbus org.freedesktop.ScreenSaver /ScreenSaver Lock", # KDE Plasma via D-Bus
                "i3lock", # Common for i3 and other WMs
                "dm-tool lock" # LightDM based systems
            ]
            for locker_cmd_str in lock_commands:
                cmd_parts = locker_cmd_str.split()
                try:
                    # Use Popen to avoid blocking if the command itself daemonizes or waits
                    subprocess.Popen(cmd_parts, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(0.5) # Give it a moment to take effect
                    # It's hard to verify success directly for all, assume it worked if no error
                    return True, f"Screen lock attempted using '{cmd_parts[0]}' on Linux."
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue # Try next command
            return False, "Could not find a common screen locker for this Linux distribution. You might need to configure one."
        else:
            return False, f"Screen locking is not supported on this operating system ({os_type})."
    except Exception as e:
        return False, f"An error occurred while trying to lock the screen: {e}"

def system_power_action(action_type, confirmation_expected=False):
    # action_type: "shutdown", "restart", "logout"
    if not confirmation_expected:
        return "CONFIRMATION_NEEDED", f"Performing a system {action_type} is a significant action. Are you absolutely sure you wish to {action_type} the computer? (Say 'yes, {action_type}' or 'confirm {action_type}' to proceed.)"

    os_type = platform.system()
    cmd = []
    script_mac = None

    if os_type == "Windows":
        if action_type == "shutdown": cmd = ["shutdown", "/s", "/t", "5"] # 5 sec delay
        elif action_type == "restart": cmd = ["shutdown", "/r", "/t", "5"] # 5 sec delay
        elif action_type == "logout": cmd = ["shutdown", "/l"]
        else: return False, f"Unknown power action '{action_type}' for Windows."
    elif os_type == "Darwin": # macOS
        if action_type == "shutdown": script_mac = 'tell application "System Events" to shut down'
        elif action_type == "restart": script_mac = 'tell application "System Events" to restart'
        elif action_type == "logout": script_mac = 'tell application "System Events" to log out'
        else: return False, f"Unknown power action '{action_type}' for macOS."
    elif os_type == "Linux":
        # These require appropriate permissions, often root or sudo.
        # Jarvis running as a normal user might not be able to execute these.
        if action_type == "shutdown": cmd = ["systemctl", "poweroff"] # Modern systemd
        elif action_type == "restart": cmd = ["systemctl", "reboot"]  # Modern systemd
        elif action_type == "logout":
            # Logout is very Desktop Environment specific on Linux
            desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
            if "gnome" in desktop_env: cmd = ["gnome-session-quit", "--logout", "--no-prompt"]
            elif "kde" in desktop_env or "plasma" in desktop_env: cmd = ["qdbus", "org.kde.ksmserver", "/KSMServer", "logout", "0", "0", "0"]
            elif "mate" in desktop_env: cmd = ["mate-session-save", "--logout-dialog"] # Might show dialog
            elif "xfce" in desktop_env: cmd = ["xfce4-session-logout", "--logout"]
            elif "cinnamon" in desktop_env: cmd = ["cinnamon-session-quit", "--logout", "--no-prompt"]
            else: return False, f"Automated logout for Linux desktop '{desktop_env if desktop_env else 'unknown'}' is not specifically supported. You might need to do this manually."
        else: return False, f"Unknown power action '{action_type}' for Linux."
    else:
        return False, f"System power actions are not supported on this operating system ({os_type})."

    try:
        if cmd:
            print(f"INFO: Executing system power command: {' '.join(cmd)}")
            subprocess.Popen(cmd) # Use Popen to not block Jarvis, system will handle the rest
            return True, f"The system {action_type} sequence has been initiated for {os_type}."
        elif script_mac:
            print(f"INFO: Executing macOS power AppleScript for {action_type}")
            success, result = run_applescript(script_mac)
            if success:
                return True, f"The system {action_type} sequence has been initiated for macOS."
            else:
                return False, f"Failed to initiate {action_type} on macOS. System reported: {result}"
        return False, "Could not determine the command for the power action." # Should not be reached if logic is correct
    except Exception as e:
        return False, f"An error occurred while trying to {action_type} the system: {e}. This action might require elevated privileges."


# --- Timer Management Thread ---
def timer_checker_thread_func(stop_event, new_timer_notification_callback):
    global active_timers, chat_history_lock
    print("INFO: Jarvis Timer Checker thread started.")
    while not stop_event.is_set():
        now = time.time()
        timers_to_remove = []
        notifications_to_send = []

        with chat_history_lock: # Access active_timers safely
            if active_timers:
                for i, timer_entry in enumerate(list(active_timers)): # Iterate copy
                    end_time, original_duration, description, timer_id = timer_entry
                    if now >= end_time:
                        notification = f"{JARVIS_INTERNAL_TIMER_PREFIX} Your {original_duration} timer for '{description}' (ID: {timer_id}) has concluded!"
                        notifications_to_send.append(notification)
                        timers_to_remove.append(timer_entry)
                    else:
                        break # List is sorted by end_time

            for t in timers_to_remove:
                if t in active_timers:
                    active_timers.remove(t)
        
        for notification in notifications_to_send: # Send notifications outside the lock
            new_timer_notification_callback(notification)
            
        time.sleep(1) # Check every second
    print("INFO: Jarvis Timer Checker thread stopped.")

# --- GUI Functions ---
def launch_gui_interface():
    global gui_active_flag, gui_window, chat_display_area_gui, user_input_field_gui

    if gui_active_flag and gui_window and gui_window.winfo_exists():
        gui_window.lift()
        gui_window.focus_force()
        display_message_in_ui_or_console("Jarvis: The interface is already active.", role="model")
        return True, "Interface is already active and has been brought to focus."

    gui_active_flag = True # Set flag before creating window

    # This function will now run in the main thread.
    # The chat_with_jarvis CLI loop should effectively pause or terminate.
    
    gui_window = tk.Tk()
    gui_window.title("Jarvis Interface")
    gui_window.geometry("600x450")
    gui_window.minsize(400, 300)

    # Configure styles for a slightly more modern look
    bg_color = "#2E2E2E" 
    fg_color = "#E0E0E0"
    entry_bg = "#3C3C3C"
    button_bg = "#505050"
    button_active_bg = "#6A6A6A"

    gui_window.configure(bg=bg_color)

    # Chat display area
    chat_font = tkFont(family="Arial", size=10)
    chat_display_area_gui = scrolledtext.ScrolledText(gui_window, wrap=tk.WORD, state='disabled',
                                                      bg=entry_bg, fg=fg_color, font=chat_font,
                                                      relief=tk.FLAT, borderwidth=2,
                                                      padx=5, pady=5)
    chat_display_area_gui.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # Input frame
    input_frame = tk.Frame(gui_window, bg=bg_color)
    input_frame.pack(fill=tk.X, padx=10, pady=(0,10))

    # User input field
    user_input_field_gui = tk.Entry(input_frame, width=70, bg=entry_bg, fg=fg_color,
                                    relief=tk.FLAT, insertbackground=fg_color, font=chat_font)
    user_input_field_gui.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
    user_input_field_gui.bind("<Return>", lambda event: handle_gui_input_submission())

    # Send button
    send_button = tk.Button(input_frame, text="Send", command=handle_gui_input_submission,
                            bg=button_bg, fg=fg_color, activebackground=button_active_bg,
                            relief=tk.FLAT, padx=10, font=chat_font)
    send_button.pack(side=tk.RIGHT, padx=(5,0))

    gui_window.protocol("WM_DELETE_WINDOW", on_gui_close)
    
    # Initial greeting in GUI
    initial_greeting_gui = "Jarvis Interface activated. How may I assist you?"
    display_message_in_ui_or_console(initial_greeting_gui, role="model", is_gui_message=True)
    add_to_conversation_history("model", initial_greeting_gui) # Add to history too

    user_input_field_gui.focus_set()
    
    # Start the Tkinter event loop. This will block until the window is closed.
    # The main_cli_loop should have yielded or exited.
    try:
        gui_window.mainloop()
    except KeyboardInterrupt:
        print("INFO: GUI KeyboardInterrupt caught.")
        on_gui_close() # Graceful shutdown
    finally:
        gui_active_flag = False # Ensure flag is reset
        print("INFO: GUI mainloop ended.")
    return True, "Interface has been launched." # This message is for the CLI->GUI transition call

def on_gui_close():
    global gui_active_flag, timer_thread_stop_event, gui_window
    if messagebox.askokcancel("Quit", "Are you sure you want to close Jarvis?"):
        gui_active_flag = False
        timer_thread_stop_event.set() # Signal timer thread to stop
        
        if gui_window:
            try:
                gui_window.destroy() # Close the Tkinter window
            except tk.TclError:
                pass # Window might already be destroyed
        gui_window = None
        
        # Signal main CLI loop (if it was designed to resume) or just exit
        # For now, closing GUI exits the program.
        print("Jarvis: Interface closed. Shutting down systems. It was a pleasure.")
        gui_thread_stop_event.set() # Signal main script if it's waiting on this
        os._exit(0) # Force exit if threads are stubborn

def handle_gui_input_submission():
    global user_input_field_gui
    user_input_raw = user_input_field_gui.get().strip()
    if not user_input_raw:
        return

    display_message_in_ui_or_console(f"You: {user_input_raw}", role="user", is_gui_message=True)
    user_input_field_gui.delete(0, tk.END)

    # Process the command in a new thread to keep GUI responsive
    # The process_and_respond_for_gui function will handle history and LLM call
    thread = threading.Thread(target=process_and_respond_for_gui, args=(user_input_raw,), daemon=True)
    thread.start()



def process_and_respond_for_gui(user_input_raw):
    # This function runs in a worker thread
    global conversation_history, model, gui_window # Ensure gui_window is accessible

    current_user_input_item = {"role": "user", "text": user_input_raw}
    
    with chat_history_lock:
        temp_history_for_command_processing = list(conversation_history)
    temp_history_for_command_processing.append(current_user_input_item)

    action_status = process_command(user_input_raw, temp_history_for_command_processing) 

    with chat_history_lock:
        llm_prompt_history_list = list(conversation_history) 
    llm_prompt_history_list.append(current_user_input_item)
    if action_status:
        llm_prompt_history_list.append({"role": "system", "text": action_status})
    
    history_str_for_llm = ""
    relevant_llm_history_items = llm_prompt_history_list[-(MAX_HISTORY_TURNS * 3 + 20):] 
    for item in relevant_llm_history_items:
        role_display = "Jarvis" if item['role'] == 'model' else "You" if item['role'] == 'user' else "System"
        if item['role'] == 'system': 
            history_str_for_llm += f"{item['text']}\n"
        else:
            history_str_for_llm += f"{role_display}: {item['text']}\n"
    
    full_prompt_for_llm = JARVIS_PERSONA_BASE_PROMPT.format(history=history_str_for_llm.strip(), user_input=user_input_raw)

    jarvis_reply = "My apologies, I seem to be experiencing a momentary lapse in communication. Could you try that again?"
    try:
        if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY" or not GEMINI_API_KEY:
             jarvis_reply = "My connection to the Gemini network is not configured. Please set the API key."
        else:
            response = model.generate_content(full_prompt_for_llm)
            if response.candidates and response.candidates[0].content.parts:
                jarvis_reply = response.text.strip()
            elif response.prompt_feedback and response.prompt_feedback.block_reason:
                jarvis_reply = f"I'm unable to respond to that request due to content policy: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                print(f"WARN: LLM response blocked. Reason: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}")
            else:
                 print(f"WARN: LLM response empty/malformed: {response}")

    except Exception as e_llm:
        error_message_detail = str(e_llm)
        if "API key not valid" in error_message_detail:
            jarvis_reply = "There appears to be an issue with the API key configuration. I am unable to connect."
        else:
            jarvis_reply = f"A slight cognitive dissonance occurred. If you could rephrase, perhaps? (Error: {str(e_llm)[:100]}...)"
        print(f"ERROR: LLM call failed (GUI): {e_llm}")

    # --- Start of Corrected Section ---
    add_to_conversation_history("user", user_input_raw)
    if action_status:
        add_to_conversation_history("system", action_status) 
        if not action_status.startswith(f"{ACTION_STATUS_PREFIX} CONFIRMATION_REQUIRED"):
            if gui_window and gui_window.winfo_exists(): 
                # CORRECTED LINE 1 for action_status:
                gui_window.after(0, display_message_in_ui_or_console, 
                                 f"{action_status.replace(ACTION_STATUS_PREFIX, 'System Note:')}", 
                                 "system_gui",  # role
                                 True)          # is_gui_message

    add_to_conversation_history("model", jarvis_reply)
    if gui_window and gui_window.winfo_exists(): 
        # CORRECTED LINE 2 for jarvis_reply:
        gui_window.after(0, display_message_in_ui_or_console, 
                         f"Jarvis: {jarvis_reply}", 
                         "model",  # role
                         True)     # is_gui_message
    # --- End of Corrected Section ---



def display_message_in_ui_or_console(message, role="system", is_gui_message=False):
    global chat_display_area_gui, gui_active_flag

    if gui_active_flag and chat_display_area_gui and gui_window and gui_window.winfo_exists():
        chat_display_area_gui.config(state='normal')
        
        # Basic tagging for colors based on role
        tag_name = role
        if role == "user":
            chat_display_area_gui.tag_configure("user", foreground="#A0D0FF") # Light blue for user
        elif role == "model":
            chat_display_area_gui.tag_configure("model", foreground="#90EE90") # Light green for Jarvis
        elif role == "system_gui": # For system messages in GUI, make them distinct
            chat_display_area_gui.tag_configure("system_gui", foreground="#FFA07A", font=("Arial", 9, "italic")) # Light Salmon, italic
        elif role == "timer_notification_gui":
            chat_display_area_gui.tag_configure("timer_notification_gui", foreground="#FFD700", font=("Arial", 10, "bold")) # Gold, bold

        chat_display_area_gui.insert(tk.END, message + "\n\n", (tag_name,))
        chat_display_area_gui.config(state='disabled')
        chat_display_area_gui.see(tk.END) # Scroll to the end
    else:
        # Fallback to console if GUI is not active or message is specifically for console
        if not is_gui_message:
            print(message)


# --- COMMAND PARSING AND EXECUTION ---
def process_command(user_input_raw, current_conversation_history_for_command):
    text = user_input_raw.lower().strip()
    action_status_message = None
    
    # Extract last Jarvis response for confirmation checks
    last_jarvis_response = ""
    relevant_history = [item for item in current_conversation_history_for_command if item['role'] == 'model']
    if relevant_history:
        last_jarvis_response = relevant_history[-1]['text'].lower()

    # Confirmation handling for sensitive actions
    # Empty Recycle Bin Confirmation
    if "emptying the recycle bin is a permanent action" in last_jarvis_response or \
       "emptying the recycle bin is permanent" in last_jarvis_response: # Added from my prompt for Jarvis
        if "yes, empty it" in text or "confirm empty recycle bin" in text or \
           (text == "yes" and "recycle bin" in last_jarvis_response.lower()):
            result, message = empty_recycle_bin_action(confirmation_expected=True)
            action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if result else f"{ACTION_STATUS_PREFIX} Recycle Bin Operation Failed: {message}"
            return action_status_message
        elif text == "no" or "cancel" in text:
            return f"{ACTION_STATUS_PREFIX} Recycle bin operation cancelled by user."

    # System Power Action Confirmation
    power_action_match = re.search(r'wish to (shutdown|restart|logout) the computer', last_jarvis_response)
    if power_action_match:
        action_to_confirm = power_action_match.group(1)
        if (f"yes, {action_to_confirm}" in text or f"confirm {action_to_confirm}" in text or \
            (text == "yes" and action_to_confirm in last_jarvis_response.lower())):
            result, message = system_power_action(action_to_confirm, confirmation_expected=True)
            action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if result else f"{ACTION_STATUS_PREFIX} System {action_to_confirm.capitalize()} Failed: {message}"
            return action_status_message
        elif text == "no" or "cancel" in text:
            return f"{ACTION_STATUS_PREFIX} System {action_to_confirm} cancelled by user."

    # GUI Command
    if re.search(r'\b(open gui|launch interface|show gui|graphical mode|start interface)\b', text):
        # This command will be handled in the main loop to transition to GUI mode
        return f"{ACTION_STATUS_PREFIX} GUI_LAUNCH_REQUESTED"


    # Timer Commands (more flexible matching)
    set_timer_match = re.search(r'\b(set|start|create|new)\s+(?:a\s+)?timer\s+(?:for\s+|of\s+)?([\w\s\d.,:"\'-]+?)(?:\s+(?:called|named|for|regarding)\s*["\']?(.+?)["\']?)?$', text, re.IGNORECASE)
    if not set_timer_match: # Simpler "timer 5 minutes for pizza"
        set_timer_match = re.search(r'^(timer)\s+([\w\s\d.,:"\'-]+?)(?:\s+(?:called|named|for|regarding)\s*["\']?(.+?)["\']?)?$', text, re.IGNORECASE)

    if set_timer_match:
        duration_part = set_timer_match.group(2).strip()
        description_part = set_timer_match.group(3).strip().strip("'\"") if set_timer_match.group(3) else "your task"
        
        # Try to extract description if it's embedded in duration_part
        # e.g., "timer 5 minutes for cookies"
        potential_desc_match = re.match(r'(.+?)\s+(?:for|called|named|regarding)\s+["\']?(.+?)["\']?$', duration_part, re.IGNORECASE)
        if potential_desc_match:
            duration_actual = potential_desc_match.group(1).strip()
            description_actual = potential_desc_match.group(2).strip().strip("'\"")
            if description_part == "your task" or not description_part : description_part = description_actual # Prefer explicit one if available
            duration_part = duration_actual
        
        success, message = set_jarvis_timer_action(duration_part, description_part)
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Timer Error: {message}"
        return action_status_message

    cancel_timer_match = re.search(r'\b(cancel|stop|delete|remove)\s+(?:the\s+)?timer(?:\s+(?:for|called|named|with id|id)\s*["\']?(.+?)["\']?)?$', text, re.IGNORECASE)
    if cancel_timer_match:
        desc_or_id = cancel_timer_match.group(2).strip().strip("'\"") if cancel_timer_match.group(2) else None
        success, message = cancel_jarvis_timer_action(desc_or_id)
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Cancel Timer Error: {message}"
        return action_status_message

    if re.search(r'\b(cancel all timers|stop all timers|clear all timers)\b', text, re.IGNORECASE):
        success, message = cancel_all_jarvis_timers_action()
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Cancel All Timers Error: {message}"
        return action_status_message

    # Calculator
    calc_match = re.search(r'\b(what is|calculate|compute|evaluate|maths?|calc)\s+(.+)', text, re.IGNORECASE)
    if calc_match:
        expression = calc_match.group(2).strip()
        # Avoid triggering calculator for phrases like "what is the time"
        if not any(kw in expression.lower() for kw in ["time", "date", "weather", "system status", "cpu", "ram", "uptime", "my name", "your name", "note", "file", "folder"]):
            success, message = calculate_action(expression) # Pass original expression for better message
            action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Calculation Error: {message}"
            return action_status_message

    # Weather
    weather_match = re.search(r'\b(?:what.s\s+the\s+weather|weather\s+(?:in|for|like\s+in)|how.s\s+the\s+weather\s+(?:in|for))\s+([\w\s,-]+)\b', text, re.IGNORECASE)
    if weather_match:
        location = weather_match.group(1).strip().replace("like in", "").replace("like for", "").strip()
        if location:
            success, message = get_weather_action(location)
            action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Weather Access Error: {message}"
            return action_status_message

    # Fun Commands
    if re.search(r'\b(roll a dice|roll dice|dice roll)\b', text):
        success, message = roll_dice_action(); action_status_message = f"{ACTION_STATUS_PREFIX} {message}"; return action_status_message
    if re.search(r'\b(flip a coin|coin flip|heads or tails)\b', text):
        success, message = flip_coin_action(); action_status_message = f"{ACTION_STATUS_PREFIX} {message}"; return action_status_message
    if re.search(r'\b(tell me a joke|joke|make me laugh|say something funny|another joke)\b', text):
        success, message = get_joke_action(); action_status_message = f"{ACTION_STATUS_PREFIX} {message}"; return action_status_message
    
    rand_num_match = re.search(r'\b(?:random number|generate number|pick a number)\s+(?:between\s+)?(-?\d+)\s+(?:and|to)\s+(-?\d+)\b', text, re.IGNORECASE)
    if rand_num_match:
        min_val, max_val = rand_num_match.group(1), rand_num_match.group(2)
        success, message = generate_random_number_action(min_val, max_val)
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Random Number Generation Error: {message}"
        return action_status_message
    
    # System Info & Control (Advanced)
    if re.search(r'\b(system uptime|how long (?:has )?(?:this pc|the system|it) (?:been )?running|pc uptime|server uptime|uptime)\b', text, re.IGNORECASE):
        success, message = get_system_uptime_action()
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Uptime Inquiry Error: {message}"
        return action_status_message

    if re.search(r'\b(empty recycle bin|empty (?:the )?trash|clear (?:the )?trash)\b', text, re.IGNORECASE):
        result, message = empty_recycle_bin_action(confirmation_expected=False) # Will return "CONFIRMATION_NEEDED" or (bool, msg)
        if result == "CONFIRMATION_NEEDED":
            action_status_message = f"{ACTION_STATUS_PREFIX} CONFIRMATION_REQUIRED_FOR_EMPTY_RECYCLE_BIN: {message}"
        elif isinstance(result, bool) and result: # Success
            action_status_message = f"{ACTION_STATUS_PREFIX} {message}"
        else: # Failure
            action_status_message = f"{ACTION_STATUS_PREFIX} Recycle Bin Operation Error: {message}"
        return action_status_message

    if re.search(r'\b(lock screen|lock (?:my|the) (?:computer|pc|system)|secure screen)\b', text, re.IGNORECASE):
        success, message = lock_screen_action()
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Screen Lock Error: {message}"
        return action_status_message

    power_op_match = re.search(r'\b(shutdown|restart|reboot|log off|logout|sign out)\b(?:\s+(?:my|the)?\s*(?:computer|pc|system|session|now))?', text, re.IGNORECASE)
    if power_op_match:
        action_word = power_op_match.group(1).lower()
        action_type = "logout" if action_word in ["log off", "logout", "sign out"] else \
                      "restart" if action_word in ["restart", "reboot"] else \
                      "shutdown" if action_word == "shutdown" else None
        if action_type:
            result, message = system_power_action(action_type, confirmation_expected=False)
            if result == "CONFIRMATION_NEEDED":
                action_status_message = f"{ACTION_STATUS_PREFIX} CONFIRMATION_REQUIRED_FOR_{action_type.upper()}: {message}"
            elif isinstance(result, bool) and result: # Success
                action_status_message = f"{ACTION_STATUS_PREFIX} {message}"
            else: # Failure
                action_status_message = f"{ACTION_STATUS_PREFIX} System {action_type.capitalize()} Error: {message}"
            return action_status_message

    # Date/Time
    if re.search(r'\b(what time is it|current time|date and time|today.s date|tell me the date|tell me the time)\b', text):
        success, message = get_current_datetime_action()
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Date/Time Inquiry Error: {message}"
        return action_status_message

    # System Stats
    if re.search(r'\b(system status|pc status|system stats|cpu usage|ram usage|performance|system load)\b', text):
        success, message = get_system_stats_action()
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} System Stats Inquiry Error: {message}"
        return action_status_message

    # Internet Check
    if re.search(r'\b(check internet|internet connection|am i online|are we connected|internet status)\b', text):
        success, message = check_internet_connection_action()
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Internet Connection Check Error: {message}"
        return action_status_message

    # File/Directory Operations
    list_dir_match = re.search(r'\b(?:list files|show files|directory contents|ls|dir)\s*(?:in|of\s+)?(["\']?[\w\s\/\.:\-\\]+["\']?)?', text, re.IGNORECASE)
    if list_dir_match:
        path_to_list = list_dir_match.group(1).strip() if list_dir_match.group(1) else "."
        success, message = list_directory_contents_action(path_to_list)
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} List Directory Error: {message}"
        return action_status_message

    create_dir_match = re.search(r'\b(?:create directory|make directory|mkdir|new folder)\s+(["\']?[\w\s\/\.:\-\\]+["\']?)', text, re.IGNORECASE)
    if create_dir_match:
        path_to_create = create_dir_match.group(1).strip()
        success, message = create_directory_action(path_to_create)
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Create Directory Error: {message}"
        return action_status_message

    open_file_match = re.search(r'\b(?:open file|show file|edit file|view file|launch file)\s+(["\']?[\w\s\/\.:\-\\]+["\']?)', text, re.IGNORECASE)
    if open_file_match:
        filepath_to_open = open_file_match.group(1).strip().strip("'\"")
        success, message = open_file_with_default_app_action(filepath_to_open)
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Open File Error: {message}"
        return action_status_message

    # Notes
    take_note_match = re.search(r'\b(?:take a note|make a note|note down|remember this|add note|note that|remember that)\s*[:\s]\s*(.+)', text, re.IGNORECASE)
    if take_note_match:
        note = take_note_match.group(1).strip()
        if note: # Ensure there's content for the note
            success, message = take_note_action(note)
            action_status_message = f"{ACTION_STATUS_PREFIX} {message}"
            return action_status_message

    if re.search(r'\b(show notes|view notes|what are my notes|read my notes|list notes)\b', text, re.IGNORECASE):
        success, message = view_notes_action()
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}"
        return action_status_message

    if re.search(r'\b(clear notes|delete all notes|forget notes|erase notes|remove all notes)\b', text, re.IGNORECASE):
        success, message = clear_notes_action()
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}"
        return action_status_message

    # Clipboard
    copy_match = re.search(r'\b(?:copy to clipboard|copy this|copy)\s*[:\s]\s*(.+)', text, re.IGNORECASE) or \
                 re.search(r"\bcopy\s+(['\"])(.+?)\1", text, re.IGNORECASE) # copy "text" or copy 'text'
    if copy_match:
        text_to_copy = copy_match.group(1) if len(copy_match.groups()) == 1 else copy_match.group(2)
        text_to_copy = text_to_copy.strip()
        if text_to_copy:
            success, message = copy_to_clipboard_action(text_to_copy)
            action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Clipboard Copy Error: {message}"
            return action_status_message

    if re.search(r'\b(paste from clipboard|what.s on the clipboard|get clipboard|show clipboard|read clipboard)\b', text, re.IGNORECASE):
        success, message = get_clipboard_content_action()
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Clipboard Read Error: {message}"
        return action_status_message

    # Type Text
    type_text_match = re.search(r'\b(?:type this|type out|enter text|type)\s*[:\s]\s*(.+)', text, re.IGNORECASE) or \
                      re.search(r"\btype\s+(['\"])(.+?)\1", text, re.IGNORECASE)
    if type_text_match:
        text_to_type = type_text_match.group(1) if len(type_text_match.groups()) == 1 else type_text_match.group(2)
        # Don't strip here, preserve original spacing for typing
        if text_to_type: # Check if there's actually something to type
            success, message = type_text_action(text_to_type)
            action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Typing Operation Error: {message}"
            return action_status_message

    # Web Search & URL Opening (Order matters: URL check before general search)
    url_match = re.search(r'\b(open|launch|go to|visit|show me)\s+((?:https?:\/\/)?[\w\d\-_]+(?:\.[\w\d\-_]+)+(?:[\/\?#][^\s]*)?)', text, re.IGNORECASE)
    if url_match:
        url_to_open = url_match.group(2)
        # Basic validation that it looks like a URL structure, not just "open settings"
        if "." in url_to_open and not url_to_open.lower().endswith((".txt", ".doc", ".pdf")): # Avoid mistaking filenames for URLs
            success, message = open_url_in_browser(url_to_open)
            action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} URL Opening Error: {message}"
            return action_status_message

    search_match = re.search(r'\b(search|find|google|look up|what is|who is|tell me about|search for)\s+(?:for\s+)?(.+)', text, re.IGNORECASE)
    if search_match:
        query = search_match.group(2).strip()
        # Avoid searching if it's clearly an internal command keyword
        internal_command_keywords = [
            "open", "launch", "close", "quit", "list", "create", "copy", "paste", "type", "timer",
            "calculate", "weather", "roll", "flip", "joke", "uptime", "lock", "shutdown", "restart", "logout",
            "note", "clipboard", "volume", "gui", "interface", "help", "time", "date", "stats", "internet"
        ]
        query_first_word = query.split(' ')[0].lower()
        if query_first_word not in internal_command_keywords and len(query) > 2 : # Simple check
            success, message = perform_web_search(query)
            action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Web Search Error: {message}"
            return action_status_message


    # Application Control (Open/Close) - specific names
    open_app_match = re.search(r'\b(open|launch|start)\s+(?:app(?:lication)?\s+)?([\w\s().-]+?)(?:\s+app(?:lication)?)?$', text, re.IGNORECASE)
    if not open_app_match: # Broader match: "open chrome browser"
        open_app_match = re.search(r'\b(open|launch|start)\s+([\w\s().-]+)', text, re.IGNORECASE)
    if open_app_match:
        app_name = open_app_match.group(2).strip().replace(" application", "").replace(" app", "").strip()
        # Filter out common words that are not app names
        filter_words = ["website", "url", "link", "tab", "window", "file", "document", "folder", "directory",
                        "the", "a", "an", "my", "some", "for", "me", "current", "this", "that", "page",
                        "timer", "note", "calculator", "settings", "preferences", "gui", "interface"]
        if app_name.lower() not in filter_words and len(app_name) > 1: # Min length for app name
            if open_application(app_name):
                action_status_message = f"{ACTION_STATUS_PREFIX} Application '{app_name}' launch initiated."
            else:
                action_status_message = f"{ACTION_STATUS_PREFIX} Failed to launch application '{app_name}'. It might not be installed or the name is incorrect."
            return action_status_message

    close_app_match = re.search(r'\b(close|quit|exit|terminate|kill)\s+(?:app(?:lication)?\s+)?([\w\s().-]+?)(?:\s+app(?:lication)?)?$', text, re.IGNORECASE)
    if not close_app_match:
         close_app_match = re.search(r'\b(close|quit|exit|terminate|kill)\s+([\w\s().-]+)', text, re.IGNORECASE)
    if close_app_match:
        app_name = close_app_match.group(2).strip().replace(" application", "").replace(" app", "").strip()
        filter_words = ["tab", "window", "current tab", "this tab", "the tab", "me", "this", "the session",
                        "program", "the", "a", "my", "timer", "note"]
        if app_name.lower() not in filter_words and len(app_name) > 1:
            success, message = close_application(app_name)
            action_status_message = f"{ACTION_STATUS_PREFIX} {message}" # message from close_application is already descriptive
            return action_status_message

    # Media Controls
    if (any(kw in text for kw in ["play", "pause", "resume"]) and \
       any(kw in text for kw in ["music", "song", "track", "sound", "audio", "video", "media", "playback"])) or \
       (text in ["play", "pause", "resume"] and "music" in str(current_conversation_history_for_command[-MAX_HISTORY_TURNS*2:]).lower()): # context
        success, message = control_media('playpause')
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Media Control Error: {message}"
        return action_status_message

    if (any(kw in text for kw in ["next", "skip"]) and any(kw in text for kw in ["song", "track", "media"])) or \
       (text == "next" and ("music" in str(current_conversation_history_for_command[-MAX_HISTORY_TURNS*2:]).lower() or "song" in str(current_conversation_history_for_command[-MAX_HISTORY_TURNS*2:]).lower())):
        success, message = control_media('next')
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Media Control Error: {message}"
        return action_status_message

    if (any(kw in text for kw in ["previous", "last", "back"]) and any(kw in text for kw in ["song", "track", "media"])):
        success, message = control_media('previous')
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Media Control Error: {message}"
        return action_status_message

    if "stop" in text and any(kw in text for kw in ["music", "playback", "media", "song", "video", "sound", "audio"]):
        success, message = control_media('stop')
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Media Control Error: {message}"
        return action_status_message

    # Volume Control
    volume_level_match = re.search(r'(set\s+)?volume\s+(?:to\s+|level\s+)?(\d{1,3})(?:%|\spercent)?', text, re.IGNORECASE)
    if volume_level_match:
        level = int(volume_level_match.group(2))
        success, message = change_volume(level)
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Volume Control Error: {message}"
        return action_status_message

    if any(kw in text for kw in ["volume up", "increase volume", "louder", "turn it up", "raise volume"]):
        success, message = change_volume("up")
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Volume Control Error: {message}"
        return action_status_message
    if any(kw in text for kw in ["volume down", "decrease volume", "quieter", "softer", "turn it down", "lower volume"]):
        success, message = change_volume("down")
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Volume Control Error: {message}"
        return action_status_message
    if re.search(r'\b(mute|unmute)\b', text, re.IGNORECASE) and ('volume' in text or 'sound' in text or 'audio' in text or len(text.split()) < 3):
        success, message = change_volume("mute")
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Volume Control Error: {message}"
        return action_status_message

    # Window Focusing
    focus_match = re.search(r'\b(focus on|switch to|bring to front|activate window|focus)\s+([\w\s\.:-]+)', text, re.IGNORECASE)
    if focus_match:
        target_keyword = focus_match.group(2).strip()
        if target_keyword.lower() not in ["me", "this", "here"]: # Avoid self-referential focus
            success, message = focus_window(target_keyword)
            action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Window Focus Error: {message}"
            return action_status_message

    # Tab Closing
    if any(kw in text for kw in ["close tab", "close current tab", "close this tab"]):
        success, message = close_current_tab()
        action_status_message = f"{ACTION_STATUS_PREFIX} {message}" if success else f"{ACTION_STATUS_PREFIX} Tab Closing Error: {message}"
        return action_status_message
    
    # Help
    if text in ["help", "list commands", "show commands", "what can you do", "commands"]:
        print_help_to_console() # Display in console for now
        action_status_message = f"{ACTION_STATUS_PREFIX} Help information has been displayed in the console."
        return action_status_message

    return action_status_message # No specific command matched, LLM will handle as conversation

def print_help_to_console():
    help_text = """
--- Jarvis Command Reference ---
I strive to understand natural language, but here's a more direct guide to my capabilities:

General & System:
  'help', 'what can you do'              - Displays this command reference.
  'exit', 'quit', 'goodbye'              - Ends our current session.
  'what time is it?', 'date and time'    - Provides the current date and time.
  'system stats', 'cpu usage', 'system load' - Shows current CPU, RAM, and Disk usage.
  'system uptime', 'how long running'    - Reports how long the system has been active.
  'check internet', 'am I online'        - Verifies internet connectivity.
  'lock screen', 'secure screen'         - Locks your computer screen.
  'shutdown' / 'restart' / 'logout'      - Initiates system power operations (confirmation required).
  'empty recycle bin' / 'empty trash'    - Clears the recycle bin (confirmation required).
  'open gui', 'launch interface'         - Launches the graphical user interface for interaction.

Timers & Productivity:
  'timer 5 minutes for my break'         - Sets an in-chat timer (e.g., "timer 1h 30m Meeting Prep").
  'cancel timer for my break' / 'cancel timer id 3' - Stops a specific timer.
  'cancel all timers'                    - Clears all active timers.
  'take a note: Remember to buy milk'    - Adds a note to my short-term memory (session-specific).
  'show notes', 'view my notes'          - Displays all current notes.
  'clear notes', 'delete all notes'      - Erases all current notes.
  'copy: This is important text!'        - Copies the provided text to the clipboard.
  'paste from clipboard', 'get clipboard' - Shows the current content of the clipboard.
  'type: Hello there, world!'            - Types the given text into the currently focused window (after a 2s delay).

Fun, Information & Calculation:
  'calculate 15 * (23 + 10) / 2'       - Performs arithmetic calculations.
  'weather in London', 'how's the weather in Paris' - Searches for the weather forecast.
  'roll a dice', 'flip a coin'           - For a bit of chance.
  'tell me a joke', 'say something funny'  - I'll try my best to amuse.
  'random number between 1 and 100'      - Generates a random number in the specified range.

Applications, Web, Files & Media:
  'open chrome', 'launch spotify'        - Opens the specified application.
  'close notes', 'quit vscode'           - Closes the specified application.
  'focus on Word', 'switch to Firefox'   - Brings the specified application window to the foreground.
  'close tab', 'close current tab'       - Sends a command to close the active tab in most browsers/editors.
  'open google.com', 'visit wikipedia.org' - Opens the specified URL in your web browser.
  'search for AI advancements'           - Performs a web search for the given query.
  'list files in Downloads', 'ls Documents' - Shows contents of a directory.
  'create directory MyNewProject'        - Makes a new folder.
  'open file report.docx', 'view image.jpg' - Opens a file with its default application.
  'play music', 'pause media', 'next song', 'previous track', 'stop playback' - Media controls.
  'volume up', 'volume down', 'mute sound', 'set volume to 50%' - Adjusts system volume.

Simply speak or type your request naturally! I'm always learning.
---------------------------------------
"""
    print(help_text)
    if gui_active_flag and chat_display_area_gui: # Also show in GUI if active
        display_message_in_ui_or_console(help_text, role="system_gui", is_gui_message=True)


# --- MAIN CHAT LOOP (CLI) ---
def add_to_conversation_history(role, text):
    global conversation_history
    with chat_history_lock:
        conversation_history.append({"role": role, "text": text})
        # Trim history to manage size
        if len(conversation_history) > MAX_HISTORY_TURNS * 3 + 20: # User, Model, System per turn + buffer
            conversation_history = conversation_history[-(MAX_HISTORY_TURNS * 3 + 20):]

def handle_timer_notification_callback(notification_message):
    # This is called by the timer thread
    display_message_in_ui_or_console(f"\n{notification_message}", role="timer_notification_gui" if gui_active_flag else "system", is_gui_message=gui_active_flag)
    add_to_conversation_history("system", notification_message) # Add to history for LLM context


def start_cli_chat_loop():
    global conversation_history, model, gui_active_flag, timer_thread_stop_event, gui_thread_stop_event

    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY" or not GEMINI_API_KEY: # Check API key before starting
        print("Jarvis: CRITICAL ERROR - Gemini API Key is not set. I am unable to function.")
        return

    timer_thread = threading.Thread(target=timer_checker_thread_func,
                                    args=(timer_thread_stop_event, handle_timer_notification_callback),
                                    daemon=True)
    timer_thread.start()

    initial_greeting = "Jarvis, version 3.0, online and at your service. How may I be of assistance today?"
    display_message_in_ui_or_console(f"Jarvis: {initial_greeting}", role="model")
    display_message_in_ui_or_console("        (Type 'exit' or 'quit' to end session, 'help' for commands, 'open gui' for interface)\n", role="system")
    add_to_conversation_history("model", initial_greeting)

    while not gui_active_flag and not gui_thread_stop_event.is_set(): # Loop for CLI mode
        try:
            user_input_raw = input("You: ").strip()
            if not user_input_raw:
                continue

            if user_input_raw.lower() in ['exit', 'quit', 'goodbye', 'bye', 'later', 'see ya']:
                display_message_in_ui_or_console("\nJarvis: It has been a privilege. Farewell for now.", role="model")
                timer_thread_stop_event.set()
                gui_thread_stop_event.set() # Signal GUI (if it were to be launched later) or main thread
                if timer_thread.is_alive(): timer_thread.join(timeout=2)
                break
            
            current_user_input_item = {"role": "user", "text": user_input_raw}
            with chat_history_lock: # Copy history for processing
                temp_history_for_command_processing = list(conversation_history)
            temp_history_for_command_processing.append(current_user_input_item) # Add current input for context

            action_status = process_command(user_input_raw, temp_history_for_command_processing)

            if action_status == f"{ACTION_STATUS_PREFIX} GUI_LAUNCH_REQUESTED":
                display_message_in_ui_or_console("Jarvis: Activating graphical interface...", role="model")
                # The launch_gui_interface() will take over the main thread with tk.mainloop()
                # So, this CLI loop will effectively pause here.
                # Timer thread continues in background.
                # We need to ensure that if GUI closes, this loop doesn't resume unexpectedly or handle it.
                success_gui, msg_gui = launch_gui_interface() # This call blocks until GUI closes
                # When launch_gui_interface returns, it means GUI was closed.
                # The on_gui_close usually calls os._exit(0), so this part might not be reached.
                print(f"INFO: GUI transition: {msg_gui}")
                if success_gui: # GUI was launched and then closed
                    # If os._exit(0) was called in on_gui_close, this won't run.
                    # If on_gui_close allows returning, we might need to stop timer and exit CLI cleanly.
                    timer_thread_stop_event.set()
                    if timer_thread.is_alive(): timer_thread.join(timeout=1)
                    print("INFO: Jarvis CLI loop ending after GUI session.")
                    break # Exit CLI loop as GUI handled the session end.
                else: # GUI launch failed, continue CLI
                    display_message_in_ui_or_console(f"Jarvis: Interface launch failed. {msg_gui} Continuing in text mode.", role="model")
                    action_status = None # Reset action status
                    # Continue CLI loop
            
            # --- LLM Interaction (if not GUI launch) ---
            if action_status != f"{ACTION_STATUS_PREFIX} GUI_LAUNCH_REQUESTED":
                with chat_history_lock:
                    llm_prompt_history_list = list(conversation_history)
                llm_prompt_history_list.append(current_user_input_item)
                if action_status:
                    llm_prompt_history_list.append({"role": "system", "text": action_status})

                history_str_for_llm = ""
                relevant_llm_history_items = llm_prompt_history_list[-(MAX_HISTORY_TURNS * 3 + 20):]
                for item in relevant_llm_history_items:
                    role_display = "Jarvis" if item['role'] == 'model' else "You" if item['role'] == 'user' else "System"
                    if item['role'] == 'system': history_str_for_llm += f"{item['text']}\n"
                    else: history_str_for_llm += f"{role_display}: {item['text']}\n"
                
                full_prompt_for_llm = JARVIS_PERSONA_BASE_PROMPT.format(history=history_str_for_llm.strip(), user_input=user_input_raw)
                
                jarvis_reply = "My apologies, a momentary lapse in my processing. Could you rephrase?"
                try:
                    # print(f"\n--- DEBUG: Sending to LLM (CLI) ---\n{full_prompt_for_llm}\n---------------------------\n")
                    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY" or not GEMINI_API_KEY:
                        jarvis_reply = "My connection to the Gemini network is not configured. Please set the API key."
                    else:
                        response = model.generate_content(full_prompt_for_llm)
                        if response.candidates and response.candidates[0].content.parts:
                            jarvis_reply = response.text.strip()
                        elif response.prompt_feedback and response.prompt_feedback.block_reason:
                             jarvis_reply = f"I'm unable to respond to that request due to content policy: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                             print(f"WARN: LLM response blocked. Reason: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}")
                        else:
                             print(f"WARN: LLM response empty/malformed: {response}")

                except Exception as e_llm:
                    error_message_detail = str(e_llm)
                    if "API key not valid" in error_message_detail:
                        jarvis_reply = "There appears to be an issue with the API key configuration. I am unable to connect."
                    else:
                        jarvis_reply = f"A slight cognitive dissonance occurred. If you could rephrase, perhaps? (Error: {str(e_llm)[:100]}...)"
                    print(f"ERROR: LLM call failed (CLI): {e_llm}")

                display_message_in_ui_or_console(f"Jarvis: {jarvis_reply}", role="model")
                add_to_conversation_history("user", user_input_raw)
                if action_status: add_to_conversation_history("system", action_status)
                add_to_conversation_history("model", jarvis_reply)

        except KeyboardInterrupt:
            display_message_in_ui_or_console("\nJarvis: Understood. System disengaging. Farewell.", role="model")
            timer_thread_stop_event.set()
            gui_thread_stop_event.set()
            if timer_thread.is_alive(): timer_thread.join(timeout=2)
            break
        except EOFError: # Happens if stdin is closed, e.g. piping
            display_message_in_ui_or_console("\nJarvis: Input stream ended. Shutting down.", role="model")
            timer_thread_stop_event.set()
            gui_thread_stop_event.set()
            if timer_thread.is_alive(): timer_thread.join(timeout=2)
            break
        except Exception as e_main_loop:
            error_msg = f"A critical system fault occurred: {e_main_loop}. I may need to be restarted."
            display_message_in_ui_or_console(f"Jarvis: {error_msg}", role="model")
            print(f"FATAL ERROR in main loop: {e_main_loop}")
            timer_thread_stop_event.set()
            gui_thread_stop_event.set()
            if timer_thread.is_alive(): timer_thread.join(timeout=2)
            break
    
    # Cleanup if loop exited for reasons other than GUI taking over and exiting itself
    if timer_thread.is_alive():
        timer_thread_stop_event.set()
        timer_thread.join(timeout=1)
    print("INFO: Jarvis CLI session has ended.")


if __name__ == "__main__":
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY" or not GEMINI_API_KEY:
        # This check is now primarily for the startup sequence before GUI/CLI logic
        # The individual loops also check.
        print("CRITICAL STARTUP ERROR: Gemini API Key not set in the script. Jarvis cannot operate.")
        # If we wanted a GUI error for this:
        # root_check = tk.Tk(); root_check.withdraw() # Hidden root for messagebox
        # messagebox.showerror("API Key Error", "Gemini API Key is not set. Jarvis cannot operate.")
        # root_check.destroy()
    else:
        # Initialize global conversation history (already done at top)
        # Start the CLI chat loop. It will handle transition to GUI if requested.
        start_cli_chat_loop()
        # If start_cli_chat_loop returns, it means either CLI exited, or GUI was launched and then closed.
        # The on_gui_close() function handles os._exit(0) if GUI is closed by user,
        # so this part might only be reached if CLI exits normally or via Ctrl+C.
        print("INFO: Jarvis application shutting down.")
