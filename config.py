import os, sys, json, shutil, platform, subprocess
from typing import Dict, Any

# === Base Path Setup ===
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FFMPEG_PATH = shutil.which("ffmpeg") or os.path.join(BASE_DIR, "ffmpeg.exe")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "download")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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
                return json.load(f)
        except Exception as e:
            print(f"Config load error: {e}")
            return {}
    return {}

def save_config(config: Dict[str, Any]) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
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
