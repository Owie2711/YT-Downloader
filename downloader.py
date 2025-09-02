import re, threading, os, subprocess, sys
from datetime import datetime
from typing import List, Dict, Optional, Any
from tkinter import messagebox
from yt_dlp import YoutubeDL
from config import DOWNLOAD_DIR, FFMPEG_PATH, get_startupinfo

# === English only ===
translations: Dict[str, str] = {
    "progress": "⏳ Progress",
    "phase_prepare": "🔍 Preparing...",
    "phase_download": "⬇️ Downloading...",
    "phase_post": "🛠️ Processing...",
    "phase_done": "✅ Done!",
    "done": "✅ Download completed!",
    "canceled": "⏹️ Download canceled!",
    "error": "❌ Error",
    "warning": "Warning",
    "warn_url": "Please enter at least 1 YouTube URL",
    "start_download": "🚀 Starting download..."
}

stop_event = threading.Event()
download_active = threading.Lock()
current_processes = []  # Module-level variable to track processes

# === Enhanced URL validation ===
def validate_youtube_url(url: str) -> bool:
    """Enhanced YouTube URL validation"""
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
        r'(?:https?://)?youtu\.be/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/c/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/@[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/channel/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/user/[\w-]+'
    ]
    return any(re.match(pattern, url.strip()) for pattern in patterns)

# === Helper: test encoder works ===
def encoder_is_usable(ffmpeg_path: str, encoder: str) -> bool:
    """Test if an encoder actually works on this system"""
    try:
        test_cmd = [
            ffmpeg_path,
            "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2",
            "-t", "1",
            "-c:v", encoder,
            "-f", "null", "-"
        ]
        result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            startupinfo=get_startupinfo()
        )
        return result.returncode == 0
    except Exception:
        return False

# === Detect available codecs ===
def detect_available_codecs(ffmpeg_path: str) -> Dict[str, list]:
    """Detect encoders supported and usable by ffmpeg on this system with enhanced safety"""
    if not ffmpeg_path or not isinstance(ffmpeg_path, str) or not os.path.exists(ffmpeg_path):
        # Return only safe fallback options
        return {  # pyright: ignore[reportReturnType]
            "H.264 (CPU libx264)": ['-c:v','libx264','-preset','medium'],
            "MP3 (Audio Only)": None,
            "AAC (Audio Only)": None,
            "Opus (Audio Only)": None
        }
        
    codec_map = {
        "H.264 (CPU libx264)": ['-c:v','libx264','-preset','medium'],

        # AMD AMF - stable with quality + pix_fmt
        "H.264 (AMD AMF)": ['-c:v','h264_amf','-quality','balanced','-pix_fmt','yuv420p'],
        "H.265 (AMD AMF)": ['-c:v','hevc_amf','-quality','balanced','-pix_fmt','yuv420p'],

        # NVIDIA
        "H.264 (NVIDIA NVENC)": ['-c:v','h264_nvenc','-preset','p4'],
        "H.265 (NVIDIA NVENC)": ['-c:v','hevc_nvenc','-preset','p4'],

        # Intel QSV
        "H.264 (Intel QSV)": ['-c:v','h264_qsv'],
        "H.265 (Intel QSV)": ['-c:v','hevc_qsv'],

        "H.265 (CPU libx265)": ['-c:v','libx265','-crf','28','-preset','medium'],
        "VP9 (CPU libvpx-vp9)": ['-c:v','libvpx-vp9','-b:v','2M'],

        # Audio
        "MP3 (Audio Only)": None,
        "AAC (Audio Only)": None,
        "Opus (Audio Only)": None
    }

    available_codecs = {}
    
    try:
        for name, args in codec_map.items():
            if args is None:  # audio always available
                available_codecs[name] = args
            else:
                encoder_name = args[1] if len(args) > 1 else None
                if encoder_name and encoder_is_usable(ffmpeg_path, encoder_name):
                    available_codecs[name] = args
    except Exception:
        # Fallback to basic codecs if detection fails
        available_codecs = {
            "H.264 (CPU libx264)": ['-c:v','libx264','-preset','medium'],
            "MP3 (Audio Only)": None,
            "AAC (Audio Only)": None,
            "Opus (Audio Only)": None
        }

    return available_codecs

# === Thread-safe Logger ===
class TkinterLogger:
    def __init__(self, log_widget: Any, prog_label: Any, speed_label: Any, progress_bar: Any, phase_label: Any, root: Any):
        self.log_widget = log_widget
        self.prog_label = prog_label
        self.speed_label = speed_label
        self.progress_bar = progress_bar
        self.phase_label = phase_label
        self.root = root
        self.progress_pattern = re.compile(r"(\d{1,3}\.?\d*)%")
        self.speed_pattern = re.compile(r"at ([0-9\.]+[KMG]iB/s)")

    def debug(self, msg: str) -> None: 
        self._log(msg)
    
    def warning(self, msg: str) -> None: 
        self._log(f"⚠️ {msg}", "warning")
    
    def error(self, msg: str) -> None: 
        self._log(f"❌ {msg}", "error")

    def _safe_ui_update(self, func) -> None:
        """Thread-safe UI updates"""
        if self.root and hasattr(self.root, 'winfo_exists'):
            try:
                if self.root.winfo_exists():
                    self.root.after(0, func)
            except Exception:
                pass

    def _log(self, msg: str, tag: Optional[str] = None):
        if stop_event.is_set():
            raise Exception("Canceled by user")

        if msg.strip():
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            clean_msg = re.sub(r"\x1B\[[0-9;]*[a-zA-Z]", "", msg)
            
            def update_log():
                try:
                    self.log_widget.insert("end", timestamp + clean_msg + "\n", tag)
                    self.log_widget.see("end")
                    
                    # Keep log widget from growing too large (memory management)
                    lines = int(self.log_widget.index('end-1c').split('.')[0])
                    if lines > 1000:
                        self.log_widget.delete("1.0", "100.0")
                        
                except Exception:
                    pass
            
            self._safe_ui_update(update_log)

            # Progress updates
            if "Downloading webpage" in msg or "Extracting" in msg:
                def update_progress():
                    try:
                        self.progress_bar.configure(mode="determinate")
                        self.progress_bar.set(0.05)
                        self.phase_label.configure(text=translations["phase_prepare"])
                    except Exception:
                        pass
                self._safe_ui_update(update_progress)

            match = self.progress_pattern.search(msg)
            if match:
                try:
                    val = float(match.group(1))
                    mapped = 0.1 + (val / 100.0) * 0.8
                    
                    def update_progress():
                        try:
                            self.progress_bar.configure(mode="determinate")
                            self.progress_bar.set(mapped)
                            self.phase_label.configure(text=translations["phase_download"])
                            self.prog_label.configure(text=f"{translations['progress']} ({val:.1f}%)")
                        except Exception:
                            pass
                    self._safe_ui_update(update_progress)
                except Exception as e:
                    print(f"Progress parse error: {e}")

            if any(word in msg for word in ["Merging", "Post-process", "Converting", "Extracting audio"]):
                def update_progress():
                    try:
                        self.progress_bar.configure(mode="determinate")
                        self.progress_bar.set(0.95)
                        self.phase_label.configure(text=translations["phase_post"])
                    except Exception:
                        pass
                self._safe_ui_update(update_progress)

            smatch = self.speed_pattern.search(msg)
            if smatch:
                def update_speed():
                    try:
                        self.speed_label.configure(text=f"⚡ {smatch.group(1)}")
                    except Exception:
                        pass
                self._safe_ui_update(update_speed)

# === Enhanced Download Function with Better Thread Safety ===
def download_videos(urls: List[str], codec_choice: str, res_choice: str,
                    log_widget: Any, prog_label: Any, speed_label: Any, 
                    download_btn: Any, progress_bar: Any, phase_label: Any, root: Any) -> None:
    # Prevent multiple simultaneous downloads
    if not download_active.acquire(blocking=False):
        def show_warning():
            try:
                messagebox.showwarning("Warning", "Download already in progress!")
            except Exception:
                pass
        if root and hasattr(root, 'after'):
            root.after(0, show_warning)
        return
    
    lock_acquired = True  # Track lock state
    
    try:
        stop_event.clear()

        # Validate inputs with thread safety
        if not urls or not isinstance(urls, list):
            return
            
        # Enhanced URL validation
        valid_urls = []
        for url in urls:
            if isinstance(url, str) and validate_youtube_url(url.strip()):
                valid_urls.append(url.strip())
        
        if not valid_urls:
            def show_warning():
                try:
                    messagebox.showwarning(translations["warning"], translations["warn_url"])
                    download_btn.configure(text="⬇️ Download")
                except Exception:
                    pass
            if root and hasattr(root, 'after'):
                root.after(0, show_warning)
            return

        # Validate resolution choice
        res_map = {"144p":144,"240p":240,"360p":360,"480p":480,"720p":720,"1080p":1080,
                   "1440p (2K)":1440,"2160p (4K)":2160,"4320p (8K)":4320}
        res_value = res_map.get(res_choice, 1080)

        # Validate codec choice
        if not isinstance(codec_choice, str):
            codec_choice = "H.264 (CPU libx264)"

        format_selector = f'bestvideo[height<={res_value}]+bestaudio/best/best'
        postprocessors, postprocessor_args = [], []

        # Safe codec detection with None check
        try:
            if FFMPEG_PATH is not None:
                available_codecs = detect_available_codecs(FFMPEG_PATH)
                codec_args = available_codecs.get(codec_choice)
            else:
                codec_args = None
        except Exception:
            codec_args = None

        if "Audio Only" in codec_choice:
            format_selector = 'bestaudio/best'
            if codec_choice == "MP3 (Audio Only)":
                postprocessors=[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}]
            elif codec_choice == "AAC (Audio Only)":
                postprocessors=[{'key':'FFmpegExtractAudio','preferredcodec':'aac','preferredquality':'192'}]
            elif codec_choice == "Opus (Audio Only)":
                postprocessors=[{'key':'FFmpegExtractAudio','preferredcodec':'opus','preferredquality':'192'}]
        else:
            postprocessor_args = (codec_args or []) + ['-c:a','aac','-b:a','192k']

        # Validate output directory
        if not os.path.exists(DOWNLOAD_DIR):
            try:
                os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            except Exception as e:
                def show_error():
                    try:
                        messagebox.showerror("Error", f"Cannot create download directory: {e}")
                    except Exception:
                        pass
                if root and hasattr(root, 'after'):
                    root.after(0, show_error)
                return

        # Build ydl_opts with safe FFMPEG_PATH handling
        ydl_opts = {
            'format': format_selector,
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'postprocessors': postprocessors,
            'noplaylist': False,
            'ignoreerrors': True,
            'logger': TkinterLogger(log_widget, prog_label, speed_label, progress_bar, phase_label, root),
        }
        
        # Only add ffmpeg_location if FFMPEG_PATH is not None
        if FFMPEG_PATH is not None:
            ydl_opts['ffmpeg_location'] = FFMPEG_PATH
            
        if postprocessor_args:
            ydl_opts['postprocessor_args'] = postprocessor_args

        try:
            with YoutubeDL(ydl_opts) as ydl:
                # Check for cancellation before starting download
                if stop_event.is_set():
                    raise Exception("Canceled by user")
                
                # Download each URL individually with cancellation checks
                for url in valid_urls:
                    if stop_event.is_set():
                        raise Exception("Canceled by user")
                    try:
                        ydl.download([url])
                    except Exception as e:
                        if stop_event.is_set() or "Canceled by user" in str(e):
                            raise Exception("Canceled by user")
                        # For other errors, continue with next URL or re-raise depending on severity
                        raise e

            def update_completion():
                try:
                    if stop_event.is_set():
                        if log_widget and hasattr(log_widget, 'insert'):
                            log_widget.insert("end", "❌ Download canceled by user\n", "error")
                        if phase_label and hasattr(phase_label, 'configure'):
                            phase_label.configure(text="⏹️ Canceled")
                        if prog_label and hasattr(prog_label, 'configure'):
                            prog_label.configure(text="Progress")
                        if progress_bar and hasattr(progress_bar, 'set'):
                            progress_bar.set(0.0)
                        if speed_label and hasattr(speed_label, 'configure'):
                            speed_label.configure(text="")
                    else:
                        if log_widget and hasattr(log_widget, 'insert'):
                            log_widget.insert("end", translations["done"] + "\n")
                        if progress_bar and hasattr(progress_bar, 'set'):
                            progress_bar.set(1.0)
                        if phase_label and hasattr(phase_label, 'configure'):
                            phase_label.configure(text=translations["phase_done"])
                        if prog_label and hasattr(prog_label, 'configure'):
                            prog_label.configure(text=f"{translations['progress']} (100%)")
                except Exception:
                    pass
            
            if root and hasattr(root, 'after'):
                root.after(0, update_completion)

        except Exception as e:
            # Check if it's a user cancellation
            if stop_event.is_set() or "Canceled by user" in str(e):
                def show_canceled():
                    try:
                        if log_widget and hasattr(log_widget, 'insert'):
                            log_widget.insert("end", "❌ Download canceled by user\n", "error")
                        if phase_label and hasattr(phase_label, 'configure'):
                            phase_label.configure(text="⏹️ Canceled")
                        if prog_label and hasattr(prog_label, 'configure'):
                            prog_label.configure(text="Progress")
                        if progress_bar and hasattr(progress_bar, 'set'):
                            progress_bar.set(0.0)
                        if speed_label and hasattr(speed_label, 'configure'):
                            speed_label.configure(text="")
                    except Exception:
                        pass
                
                if root and hasattr(root, 'after'):
                    root.after(0, show_canceled)
                return  # Don't try fallback for user cancellation
            
            # Enhanced fallback mechanism
            if "amf" in codec_choice.lower() and ("not available" in str(e).lower() or "failed" in str(e).lower()):
                def retry_with_fallback():
                    try:
                        if log_widget and hasattr(log_widget, 'insert'):
                            log_widget.insert("end", "⚠️ AMD AMF encoding failed, retrying with CPU encoding...\n", "warning")
                    except Exception:
                        pass
                
                if root and hasattr(root, 'after'):
                    root.after(0, retry_with_fallback)
                
                # Release lock before recursive call
                if lock_acquired:
                    try:
                        download_active.release()
                        lock_acquired = False
                    except Exception:
                        pass
                        
                return download_videos(valid_urls, "H.264 (CPU libx264)", res_choice,
                                       log_widget, prog_label, speed_label,
                                       download_btn, progress_bar, phase_label, root)
            else:
                def show_error():
                    try:
                        if log_widget and hasattr(log_widget, 'insert'):
                            log_widget.insert("end", translations["error"] + f": {e}\n", "error")
                        messagebox.showerror(translations["error"], str(e))
                    except Exception:
                        pass
                
                if root and hasattr(root, 'after'):
                    root.after(0, show_error)
                
    finally:
        # Ensure UI is reset and lock is released safely
        def reset_ui():
            try:
                if download_btn and hasattr(download_btn, 'configure'):
                    download_btn.configure(text="⬇️ Download")
                
                # If download was canceled, ensure UI shows canceled state
                if stop_event.is_set():
                    if phase_label and hasattr(phase_label, 'configure'):
                        phase_label.configure(text="⏹️ Canceled")
                    if prog_label and hasattr(prog_label, 'configure'):
                        prog_label.configure(text="Progress")
                    if progress_bar and hasattr(progress_bar, 'set'):
                        progress_bar.set(0.0)
                    if speed_label and hasattr(speed_label, 'configure'):
                        speed_label.configure(text="")
            except Exception:
                pass
        
        if root and hasattr(root, 'after'):
            root.after(0, reset_ui)
        
        # Safe lock release
        if lock_acquired:
            try:
                download_active.release()
            except Exception:
                pass

# === Enhanced Cancel Function ===
def cancel_download():
    """Enhanced cancel with proper cleanup and immediate UI feedback"""
    global current_processes
    stop_event.set()
    
    # Additional cancellation for any running subprocesses
    import signal
    try:
        # Try to terminate any running ffmpeg processes
        for proc in current_processes:
            try:
                if proc and proc.poll() is None:  # Process is still running
                    proc.terminate()
                    # Give it a moment to terminate gracefully
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()  # Force kill if necessary
            except Exception:
                pass
        current_processes.clear()
    except Exception:
        pass

