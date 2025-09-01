import re, threading, os, subprocess
from datetime import datetime
from typing import List, Dict
from tkinter import messagebox
from yt_dlp import YoutubeDL
from config import DOWNLOAD_DIR, FFMPEG_PATH

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
        result = subprocess.run(test_cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

# === Detect available codecs ===
def detect_available_codecs(ffmpeg_path: str) -> Dict[str, list]:
    """Detect encoders supported and usable by ffmpeg on this system"""
    codec_map = {
        "H.264 (CPU libx264)": ['-c:v','libx264','-preset','medium'],

        # AMD AMF → stabil dengan quality + pix_fmt
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
    for name, args in codec_map.items():
        if args is None:  # audio always available
            available_codecs[name] = args
        else:
            encoder_name = args[1]
            if encoder_is_usable(ffmpeg_path, encoder_name):
                available_codecs[name] = args

    return available_codecs

# === Logger ===
class TkinterLogger:
    def __init__(self, log_widget, prog_label, speed_label, progress_bar, phase_label):
        self.log_widget = log_widget
        self.prog_label = prog_label
        self.speed_label = speed_label
        self.progress_bar = progress_bar
        self.phase_label = phase_label
        self.progress_pattern = re.compile(r"(\d{1,3}\.?\d*)%")
        self.speed_pattern = re.compile(r"at ([0-9\.]+[KMG]iB/s)")

    def debug(self, msg): self._log(msg)
    def warning(self, msg): self._log(f"⚠️ {msg}", "warning")
    def error(self, msg): self._log(f"❌ {msg}", "error")

    def _log(self, msg: str, tag: str = None):
        if stop_event.is_set():
            raise Exception("Canceled by user")

        if msg.strip():
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            clean_msg = re.sub(r"\x1B\[[0-9;]*[a-zA-Z]", "", msg)
            self.log_widget.insert("end", timestamp + clean_msg + "\n", tag)
            self.log_widget.see("end")
            self.log_widget.update_idletasks()

            if "Downloading webpage" in msg or "Extracting" in msg:
                self.progress_bar.configure(mode="determinate")
                self.progress_bar.set(0.05)
                self.phase_label.configure(text=translations["phase_prepare"])

            match = self.progress_pattern.search(msg)
            if match:
                try:
                    val = float(match.group(1))
                    mapped = 0.1 + (val / 100.0) * 0.8
                    self.progress_bar.configure(mode="determinate")
                    self.progress_bar.set(mapped)
                    self.phase_label.configure(text=translations["phase_download"])
                    self.prog_label.configure(text=f"{translations['progress']} ({val:.1f}%)")
                except Exception as e:
                    print(f"Progress parse error: {e}")

            if any(word in msg for word in ["Merging", "Post-process", "Converting", "Extracting audio"]):
                self.progress_bar.configure(mode="determinate")
                self.progress_bar.set(0.95)
                self.phase_label.configure(text=translations["phase_post"])

            smatch = self.speed_pattern.search(msg)
            if smatch:
                self.speed_label.configure(text=f"⚡ {smatch.group(1)}")

# === Download Function ===
def download_videos(urls: List[str], codec_choice: str, res_choice: str,
                    log_widget, prog_label, speed_label, download_btn, progress_bar, phase_label) -> None:
    stop_event.clear()

    youtube_pattern = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+")
    urls = [u for u in urls if youtube_pattern.match(u)]
    if not urls:
        messagebox.showwarning(translations["warning"], translations["warn_url"])
        download_btn.configure(text="⬇️ Download")
        return

    res_map = {"144p":144,"240p":240,"360p":360,"480p":480,"720p":720,"1080p":1080,
               "1440p (2K)":1440,"2160p (4K)":2160,"4320p (8K)":4320}
    res_value = res_map.get(res_choice, 1080)

    format_selector = f'bestvideo[height<={res_value}]+bestaudio/best/best'
    postprocessors, postprocessor_args = [], []

    available_codecs = detect_available_codecs(FFMPEG_PATH)
    codec_args = available_codecs.get(codec_choice)

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

    ydl_opts = {
        'format': format_selector,
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'postprocessors': postprocessors,
        'noplaylist': False,
        'ignoreerrors': True,
        'ffmpeg_location': FFMPEG_PATH,
        'logger': TkinterLogger(log_widget, prog_label, speed_label, progress_bar, phase_label),
    }
    if postprocessor_args:
        ydl_opts['postprocessor_args'] = postprocessor_args

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)

        if stop_event.is_set():
            log_widget.insert("end", translations["canceled"] + "\n")
            phase_label.configure(text=translations["canceled"])
            prog_label.configure(text=f"{translations['progress']}")
            progress_bar.set(0.0)
        else:
            log_widget.insert("end", translations["done"] + "\n")
            progress_bar.set(1.0)
            phase_label.configure(text=translations["phase_done"])
            prog_label.configure(text=f"{translations['progress']} (100%)")

    except Exception as e:
        # === Fallback kalau AMF gagal ===
        if "amf" in codec_choice.lower():
            log_widget.insert("end", "⚠️ AMF encode failed, falling back to CPU (libx264)\n")
            codec_choice = "H.264 (CPU libx264)"
            return download_videos(urls, codec_choice, res_choice,
                                   log_widget, prog_label, speed_label,
                                   download_btn, progress_bar, phase_label)
        else:
            log_widget.insert("end", translations["error"] + f": {e}\n")
            messagebox.showerror(translations["error"], str(e))
    finally:
        download_btn.configure(text="⬇️ Download")

def cancel_download():
    stop_event.set()
