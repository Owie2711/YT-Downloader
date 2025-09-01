import customtkinter as ctk
from tkinter import messagebox
import threading, os, platform, subprocess, sys, json, re
from yt_dlp import YoutubeDL

# === Translations ===
translations = {
    "id": {
        "title": "🎬 YouTube Downloader",
        "url_label": "🔗 Masukkan URL YouTube",
        "format_label": "🎞 Pilihan Format",
        "res_label": "📺 Pilihan Resolusi",
        "download": "⬇️ Download",
        "open_folder": "📂 Buka Folder",
        "progress": "⏳ Progres",
        "start_download": "🚀 Mulai download...",
        "done": "✅ Download selesai!",
        "error": "❌ Error",
        "warn_url": "Masukkan minimal 1 URL YouTube",
        "warning": "Peringatan",
        "lang_label": "🌐 Pilih Bahasa",
        "phase_prepare": "🔍 Menyiapkan...",
        "phase_download": "⬇️ Mengunduh...",
        "phase_post": "🛠️ Memproses...",
        "phase_done": "✅ Selesai!"
    },
    "en": {
        "title": "🎬 YouTube Downloader",
        "url_label": "🔗 Enter YouTube URL",
        "format_label": "🎞 Format Options",
        "res_label": "📺 Resolution Options",
        "download": "⬇️ Download",
        "open_folder": "📂 Open Folder",
        "progress": "⏳ Progress",
        "start_download": "🚀 Starting download...",
        "done": "✅ Download completed!",
        "error": "❌ Error",
        "warn_url": "Please enter at least 1 YouTube URL",
        "warning": "Warning",
        "lang_label": "🌐 Select Language",
        "phase_prepare": "🔍 Preparing...",
        "phase_download": "⬇️ Downloading...",
        "phase_post": "🛠️ Processing...",
        "phase_done": "✅ Done!"
    }
}
current_lang = "id"

# === Path Setup ===
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg.exe")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "download")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# === Config Helpers ===
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except:
        pass

def open_folder(path):
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        messagebox.showerror("Error", f"Gagal membuka folder: {e}")

# === Logger ===
class TkinterLogger:
    def __init__(self, log_widget, percent_label, speed_label, progress_bar, phase_label):
        self.log_widget = log_widget
        self.percent_label = percent_label
        self.speed_label = speed_label
        self.progress_bar = progress_bar
        self.phase_label = phase_label
        self.progress_pattern = re.compile(r"(\d{1,3}\.?\d*)%")
        self.speed_pattern = re.compile(r"at ([0-9\.]+[KMG]iB/s)")

    def debug(self, msg): self._log(msg)
    def warning(self, msg): self._log(f"⚠️ {msg}")
    def error(self, msg): self._log(f"❌ {msg}")

    def _log(self, msg):
        if msg.strip():
            clean_msg = re.sub(r"\x1B\[[0-9;]*[a-zA-Z]", "", msg)
            self.log_widget.insert("end", clean_msg + "\n")
            self.log_widget.see("end")
            self.log_widget.update_idletasks()

            # Stage 1: Preparing
            if "Downloading webpage" in msg or "Extracting" in msg:
                self.progress_bar.configure(mode="determinate")
                self.progress_bar.set(0.05)
                self.phase_label.configure(text=translations[current_lang]["phase_prepare"])

            # Stage 2: Downloading (map % to 10–90%)
            match = self.progress_pattern.search(msg)
            if match:
                try:
                    val = float(match.group(1))  # 0–100
                    mapped = 0.1 + (val / 100.0) * 0.8
                    self.progress_bar.configure(mode="determinate")
                    self.progress_bar.set(mapped)
                    self.percent_label.configure(text=f" ({val:.1f}%)")
                    self.phase_label.configure(text=translations[current_lang]["phase_download"])
                except:
                    pass

            # Stage 3: Post-processing
            if any(word in msg for word in ["Merging", "Post-process", "Converting", "Extracting audio"]):
                self.progress_bar.configure(mode="determinate")
                self.progress_bar.set(0.95)
                self.phase_label.configure(text=translations[current_lang]["phase_post"])

            # Speed
            smatch = self.speed_pattern.search(msg)
            if smatch:
                self.speed_label.configure(text=f"⚡ {smatch.group(1)}")

# === Downloader ===
def download_videos(urls, codec_choice, res_choice,
                    log_widget, percent_label, speed_label, download_btn, progress_bar, phase_label):
    def log(msg):
        clean_msg = re.sub(r"\x1B\[[0-9;]*[a-zA-Z]", "", msg)
        log_widget.insert("end", clean_msg + "\n")
        log_widget.see("end")
        log_widget.update_idletasks()

    res_map = {
        "144p": 144, "240p": 240, "360p": 360, "480p": 480,
        "720p": 720, "1080p": 1080, "1440p (2K)": 1440,
        "2160p (4K)": 2160, "4320p (8K)": 4320
    }
    res_value = res_map.get(res_choice, 1080)

    format_selector = f'bestvideo[height<={res_value}]+bestaudio/best/best'
    postprocessors, postprocessor_args = [], []

    codec_map = {
        "H.264 (CPU libx264)": ['-c:v','libx264','-preset','medium'],
        "H.264 (NVIDIA NVENC)": ['-c:v','h264_nvenc'],
        "H.264 (AMD AMF)": ['-c:v','h264_amf'],
        "H.264 (Intel QSV)": ['-c:v','h264_qsv'],
        "H.265 (CPU libx265)": ['-c:v','libx265','-crf','28','-preset','medium'],
        "H.265 (NVIDIA NVENC)": ['-c:v','hevc_nvenc'],
        "H.265 (AMD AMF)": ['-c:v','hevc_amf'],
        "H.265 (Intel QSV)": ['-c:v','hevc_qsv'],
        "VP9 (CPU libvpx-vp9)": ['-c:v','libvpx-vp9','-b:v','2M'],
        "MP3 (Audio Only)": None, "AAC (Audio Only)": None, "Opus (Audio Only)": None
    }

    if "Audio Only" in codec_choice:
        format_selector = 'bestaudio/best'
        if codec_choice == "MP3 (Audio Only)":
            postprocessors=[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}]
        elif codec_choice == "AAC (Audio Only)":
            postprocessors=[{'key':'FFmpegExtractAudio','preferredcodec':'aac','preferredquality':'192'}]
        elif codec_choice == "Opus (Audio Only)":
            postprocessors=[{'key':'FFmpegExtractAudio','preferredcodec':'opus','preferredquality':'192'}]
    else:
        postprocessor_args = (codec_map.get(codec_choice, []) or []) + ['-c:a','aac','-b:a','192k']

    ydl_opts = {
        'format': format_selector,
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'postprocessors': postprocessors,
        'noplaylist': False,
        'ignoreerrors': True,
        'ffmpeg_location': FFMPEG_PATH,
        'logger': TkinterLogger(log_widget, percent_label, speed_label, progress_bar, phase_label),
    }
    if postprocessor_args:
        ydl_opts['postprocessor_args']=postprocessor_args

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)
        log(translations[current_lang]["done"])
        progress_bar.set(1.0)
        phase_label.configure(text=translations[current_lang]["phase_done"])
    except Exception as e:
        log(translations[current_lang]["error"] + f": {e}")
    finally:
        download_btn.configure(state="normal", text=translations[current_lang]["download"])
        percent_label.configure(text="")

def start_download(url_text, codec_choice_var, res_choice_var,
                   log_widget, percent_label, speed_label, download_btn, progress_bar, phase_label):
    urls = [u.strip() for u in url_text.get("1.0", "end").splitlines() if u.strip()]
    if not urls:
        messagebox.showwarning(translations[current_lang]["warning"],
                               translations[current_lang]["warn_url"])
        return

    save_config({
        "codec": codec_choice_var.get(),
        "resolution": res_choice_var.get(),
        "language": current_lang
    })

    log_widget.delete("1.0", "end")
    log_widget.insert("end", translations[current_lang]["start_download"] + "\n")
    percent_label.configure(text="")
    speed_label.configure(text="")
    progress_bar.configure(mode="determinate")
    progress_bar.set(0.0)
    phase_label.configure(text=translations[current_lang]["phase_prepare"])

    download_btn.configure(state="disabled", text="⏳ Downloading...")

    t = threading.Thread(target=download_videos,
        args=(urls, codec_choice_var.get(), res_choice_var.get(),
              log_widget, percent_label, speed_label, download_btn, progress_bar, phase_label))
    t.start()

# === Main UI ===
def main():
    global current_lang
    config = load_config()
    current_lang = config.get("language", "id")

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title(translations[current_lang]["title"])
    root.geometry(config.get("geometry", "600x750"))

    # === Language Selector ===
    lang_frame = ctk.CTkFrame(root, fg_color="transparent")
    lang_frame.pack(fill="x", padx=20, pady=6)

    lang_label = ctk.CTkLabel(lang_frame, text=translations[current_lang]["lang_label"])
    lang_label.pack(side="left", padx=5)

    lang_var = ctk.StringVar(value=current_lang)
    lang_dropdown = ctk.CTkComboBox(
        lang_frame, variable=lang_var, values=["id", "en"],
        command=lambda _: switch_language()
    )
    lang_dropdown.pack(side="left", padx=5)

    # === URL Input ===
    url_label = ctk.CTkLabel(root, text=translations[current_lang]["url_label"])
    url_label.pack(anchor="w", padx=20, pady=(10,2))

    url_text = ctk.CTkTextbox(root, height=100)
    url_text.pack(fill="x", padx=20, pady=5)

    # === Codec Selection ===
    codec_label = ctk.CTkLabel(root, text=translations[current_lang]["format_label"])
    codec_label.pack(anchor="w", padx=20, pady=(10,2))

    codec_choice_var = ctk.StringVar(value=config.get("codec", "H.264 (CPU libx264)"))
    codec_dropdown = ctk.CTkComboBox(root, variable=codec_choice_var, values=[
        "H.264 (CPU libx264)", "H.264 (NVIDIA NVENC)", "H.264 (AMD AMF)", "H.264 (Intel QSV)",
        "H.265 (CPU libx265)", "H.265 (NVIDIA NVENC)", "H.265 (AMD AMF)", "H.265 (Intel QSV)",
        "VP9 (CPU libvpx-vp9)", "MP3 (Audio Only)", "AAC (Audio Only)", "Opus (Audio Only)"
    ])
    codec_dropdown.pack(fill="x", padx=20, pady=5)

    # === Resolution Selection ===
    res_label = ctk.CTkLabel(root, text=translations[current_lang]["res_label"])
    res_label.pack(anchor="w", padx=20, pady=(10,2))

    res_choice_var = ctk.StringVar(value=config.get("resolution", "1080p"))
    res_dropdown = ctk.CTkComboBox(root, variable=res_choice_var, values=[
        "144p","240p","360p","480p","720p","1080p","1440p (2K)","2160p (4K)","4320p (8K)"
    ])
    res_dropdown.pack(fill="x", padx=20, pady=5)

    # === Buttons ===
    btn_frame = ctk.CTkFrame(root, fg_color="transparent")
    btn_frame.pack(pady=12)

    download_btn = ctk.CTkButton(btn_frame, text=translations[current_lang]["download"],
        command=lambda: start_download(url_text, codec_choice_var, res_choice_var,
                                       log_widget, percent_label, speed_label, download_btn, progress_bar, phase_label))
    download_btn.pack(side="left", padx=12)

    open_btn = ctk.CTkButton(btn_frame, text=translations[current_lang]["open_folder"],
        command=lambda: open_folder(DOWNLOAD_DIR))
    open_btn.pack(side="left", padx=12)

    # === Progress & Log ===
    prog_label = ctk.CTkLabel(root, text=translations[current_lang]["progress"])
    prog_label.pack(anchor="w", padx=20, pady=(10,2))

    progress_bar = ctk.CTkProgressBar(root)
    progress_bar.set(0.0)
    progress_bar.pack(fill="x", padx=20, pady=(0,5))

    phase_label = ctk.CTkLabel(root, text="", font=("Segoe UI", 12, "bold"))
    phase_label.pack(anchor="center", pady=(0,5))

    percent_label = ctk.CTkLabel(root, text="")
    percent_label.pack(anchor="w", padx=20)

    speed_label = ctk.CTkLabel(root, text="")
    speed_label.pack(anchor="e", padx=20)

    log_widget = ctk.CTkTextbox(root, height=200)
    log_widget.pack(fill="both", expand=True, padx=20, pady=10)

    # === Language Switch ===
    def apply_language():
        root.title(translations[current_lang]["title"])
        url_label.configure(text=translations[current_lang]["url_label"])
        codec_label.configure(text=translations[current_lang]["format_label"])
        res_label.configure(text=translations[current_lang]["res_label"])
        prog_label.configure(text=translations[current_lang]["progress"])
        download_btn.configure(text=translations[current_lang]["download"])
        open_btn.configure(text=translations[current_lang]["open_folder"])
        lang_label.configure(text=translations[current_lang]["lang_label"])
        phase_label.configure(text="")

    def switch_language():
        global current_lang
        current_lang = lang_var.get()
        save_config({
            "codec": codec_choice_var.get(),
            "resolution": res_choice_var.get(),
            "language": current_lang,
            "geometry": root.geometry()
        })
        apply_language()

    def on_close():
        geom = root.geometry()
        save_config({"codec": codec_choice_var.get(),
                     "resolution": res_choice_var.get(),
                     "language": current_lang,
                     "geometry": geom})
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__=="__main__":
    main()
