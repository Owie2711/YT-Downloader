import os, sys, json, shutil, platform, subprocess
from typing import Dict, Any

# === Base Path Setup ===
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Enhanced FFMPEG path detection with validation
def find_ffmpeg_path():
    """Find and validate FFMPEG executable"""
    paths_to_try = [
        shutil.which("ffmpeg"),  # System PATH
        os.path.join(BASE_DIR, "ffmpeg.exe"),  # Windows bundled
        os.path.join(BASE_DIR, "ffmpeg"),  # Linux/macOS bundled
        "/usr/bin/ffmpeg",  # Common Linux path
        "/usr/local/bin/ffmpeg",  # Homebrew macOS path
    ]
    
    for path in paths_to_try:
        if path and os.path.isfile(path):
            try:
                # Test if FFMPEG is executable
                result = subprocess.run([path, "-version"], 
                                       capture_output=True, timeout=5)
                if result.returncode == 0:
                    return path
            except Exception:
                continue
    
    return None  # No valid FFMPEG found

FFMPEG_PATH = find_ffmpeg_path()
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "download")

# Create download directory with error handling
try:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
except Exception as e:
    print(f"Warning: Could not create download directory: {e}")

def get_startupinfo():
    """Suppress terminal window in Windows"""
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None

def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Validate config data
                if not isinstance(data, dict):
                    return {}
                return data
        except (json.JSONDecodeError, UnicodeDecodeError, Exception) as e:
            print(f"Config load error: {e}")
            # Backup corrupted config
            try:
                backup_path = CONFIG_FILE + ".backup"
                shutil.copy2(CONFIG_FILE, backup_path)
                print(f"Corrupted config backed up to: {backup_path}")
            except Exception:
                pass
            return {}
    return {}

def save_config(config: Dict[str, Any]) -> None:
    if not isinstance(config, dict):
        print("Error: Config must be a dictionary")
        return
        
    try:
        # Create backup before saving
        if os.path.exists(CONFIG_FILE):
            backup_path = CONFIG_FILE + ".bak"
            shutil.copy2(CONFIG_FILE, backup_path)
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Config save error: {e}")

def open_folder(path: str) -> None:
    """Cross-platform folder opener (no terminal popup)"""
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", path], startupinfo=get_startupinfo())
        else:  # Linux
            subprocess.Popen(
                ["xdg-open", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=get_startupinfo()
            )
    except Exception as e:
        print(f"Failed to open folder: {e}")
