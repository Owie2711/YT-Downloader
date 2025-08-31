import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import threading, os, platform, subprocess, sys, json, re
from yt_dlp import YoutubeDL

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg.exe")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "download")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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

class TkinterLogger:
    def __init__(self, log_widget, percent_label, speed_label):
        self.log_widget = log_widget
        self.percent_label = percent_label
        self.speed_label = speed_label
        self.progress_pattern = re.compile(r"(\d{1,3}\.?\d*)%")
        self.speed_pattern = re.compile(r"at ([0-9\.]+[KMG]iB/s)")

    def debug(self, msg):
        self._log(msg)

    def warning(self, msg):
        self._log(f"⚠️ {msg}", "orange")

    def error(self, msg):
        self._log(f"❌ {msg}", "red")

    def _log(self, msg, color="white"):
        if msg.strip():
            clean_msg = re.sub(r"\x1B\[[0-9;]*[a-zA-Z]", "", msg)
            self.log_widget.insert(tk.END, clean_msg + "\n", color)
            self.log_widget.see(tk.END)
            self.log_widget.update_idletasks()
            match = self.progress_pattern.search(msg)
            if match:
                try:
                    val = float(match.group(1))
                    self.percent_label.config(text=f" ({val:.1f}%)")
                except:
                    pass
            smatch = self.speed_pattern.search(msg)
            if smatch:
                self.speed_label.config(text=f"⚡ {smatch.group(1)}")

def download_videos(urls, codec_choice, res_choice,
                    log_widget, percent_label, speed_label, download_btn):
    def log(msg, color="white"):
        clean_msg = re.sub(r"\x1B\[[0-9;]*[a-zA-Z]", "", msg)
        log_widget.insert(tk.END, clean_msg + "\n", color)
        log_widget.see(tk.END)
        log_widget.update_idletasks()

    res_map = {
        "144p": 144, "240p": 240, "360p": 360, "480p": 480,
        "720p": 720, "1080p": 1080, "1440p (2K)": 1440,
        "2160p (4K)": 2160, "4320p (8K)": 4320
    }
    res_value = res_map.get(res_choice, 1080)

    format_selector = f'bestvideo[height<={res_value}]+bestaudio/best/best'
    postprocessors = []
    postprocessor_args = []

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
        'logger': TkinterLogger(log_widget, percent_label, speed_label),
    }
    if postprocessor_args:
        ydl_opts['postprocessor_args']=postprocessor_args

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)
        log("✅ Download selesai!", "green")
    except Exception as e:
        log(f"❌ Error: {e}", "red")
    finally:
        download_btn.config(state="normal", text="⬇️ Download")
        percent_label.config(text="")

def start_download(url_text, codec_choice_var, res_choice_var,
                   log_widget, percent_label, speed_label, download_btn):
    urls = [u.strip() for u in url_text.get("1.0", tk.END).splitlines() if u.strip()]
    if not urls:
        messagebox.showwarning("Peringatan", "Masukkan minimal 1 URL YouTube")
        return

    save_config({
        "codec": codec_choice_var.get(),
        "resolution": res_choice_var.get()
    })

    log_widget.delete("1.0", tk.END)
    log_widget.insert(tk.END, "🚀 Mulai download...\n", "white")
    percent_label.config(text="")
    speed_label.config(text="")

    download_btn.config(state="disabled", text="⏳ Downloading...")

    t = threading.Thread(target=download_videos,
        args=(urls, codec_choice_var.get(), res_choice_var.get(),
              log_widget, percent_label, speed_label, download_btn))
    t.start()

def main():
    root = tk.Tk()
    root.title("🎬 YouTube Downloader")
    root.geometry("560x750")
    root.configure(bg="#1e1e1e")

    style = ttk.Style(root)
    style.theme_use("clam")

    accent = "#2196f3"
    style.configure("Rounded.TButton", background=accent, foreground="white",
                    padding=10, relief="flat", font=("Segoe UI", 11, "bold"))
    style.map("Rounded.TButton",
              background=[("active", "#1976d2"), ("disabled", accent)],
              foreground=[("disabled", "white"), ("active", "white"), ("!disabled", "white")])

    style.configure(
        "Modern.TCombobox",
        fieldbackground="#2c2c2c",
        foreground="white",
        background="#2c2c2c",
        arrowsize=16,
        padding=6,
    )
    style.map(
        "Modern.TCombobox",
        fieldbackground=[("readonly", "#2c2c2c"), ("focus", "#2c2c2c"), ("!focus", "#2c2c2c"), ("disabled", "#444")],
        foreground=[("disabled", "#777"), ("!disabled", "white")],
        selectbackground=[("!disabled", "#37474f")],
        selectforeground=[("!disabled", accent)],
        arrowcolor=[("disabled", "#777"), ("!disabled", accent)],
    )

    root.option_add('*Listbox.background', '#2c2c2c')
    root.option_add('*Listbox.foreground', 'white')
    root.option_add('*Listbox.selectBackground', '#37474f')
    root.option_add('*Listbox.selectForeground', accent)

    config = load_config()

    def make_labelframe(master, text):
        frame = tk.LabelFrame(master, text=text, bg="#2b2b2b",
                              font=("Segoe UI", 11, "bold"), fg="white",
                              bd=0, relief="flat", labelanchor="nw")
        frame.config(highlightbackground="#444", highlightcolor=accent, highlightthickness=1)
        return frame

    root.grid_columnconfigure(0, weight=1)

    url_frame = make_labelframe(root, "🔗 Masukkan URL YouTube")
    url_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
    url_text = scrolledtext.ScrolledText(url_frame, height=5, font=("Segoe UI", 10),
                                         bd=0, relief="flat", bg="#1e1e1e", fg="white")
    url_text.pack(fill="both", expand=True, padx=10, pady=8)
    url_text.configure(highlightbackground="#444", highlightcolor=accent, highlightthickness=1)

    menu = tk.Menu(url_text, tearoff=0, bg="#2c2c2c", fg="white")
    menu.add_command(label="Copy", command=lambda: url_text.event_generate("<<Copy>>"))
    menu.add_command(label="Paste", command=lambda: url_text.event_generate("<<Paste>>"))
    url_text.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    codec_frame = make_labelframe(root, "🎞 Pilihan Format")
    codec_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=6)
    codec_choice_var = tk.StringVar(value=config.get("codec", "H.264 (CPU libx264)"))
    codec_dropdown = ttk.Combobox(
        codec_frame,
        textvariable=codec_choice_var,
        state="readonly",
        font=("Segoe UI", 10),
        style="Modern.TCombobox",
    )
    codec_dropdown['values'] = [
        "H.264 (CPU libx264)", "H.264 (NVIDIA NVENC)", "H.264 (AMD AMF)", "H.264 (Intel QSV)",
        "H.265 (CPU libx265)", "H.265 (NVIDIA NVENC)", "H.265 (AMD AMF)", "H.265 (Intel QSV)",
        "VP9 (CPU libvpx-vp9)", "MP3 (Audio Only)", "AAC (Audio Only)", "Opus (Audio Only)"
    ]
    codec_dropdown.pack(fill="x", padx=12, pady=8)

    res_frame = make_labelframe(root, "📺 Pilihan Resolusi")
    res_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=6)
    res_choice_var = tk.StringVar(value=config.get("resolution", "1080p"))
    res_dropdown = ttk.Combobox(
        res_frame,
        textvariable=res_choice_var,
        state="readonly",
        font=("Segoe UI", 10),
        style="Modern.TCombobox",
    )
    res_dropdown['values'] = ["144p", "240p", "360p", "480p", "720p",
                              "1080p", "1440p (2K)", "2160p (4K)", "4320p (8K)"]
    res_dropdown.pack(fill="x", padx=12, pady=8)

    btn_frame = tk.Frame(root, bg="#1e1e1e")
    btn_frame.grid(row=3, column=0, pady=12)
    download_btn = ttk.Button(btn_frame, text="⬇️ Download", style="Rounded.TButton",
        command=lambda: start_download(url_text, codec_choice_var, res_choice_var,
                                       log_widget, percent_label, speed_label, download_btn))
    download_btn.pack(side="left", padx=12)
    ttk.Button(btn_frame, text="📂 Open Folder", style="Rounded.TButton",
        command=lambda: open_folder(DOWNLOAD_DIR)).pack(side="left", padx=12)

    prog_frame = make_labelframe(root, "⏳ Progress")
    prog_frame.grid(row=4, column=0, sticky="nsew", padx=20, pady=12)
    root.grid_rowconfigure(4, weight=1)

    title_frame = tk.Frame(prog_frame, bg="#2b2b2b")
    title_frame.pack(fill="x", pady=(0,4))
    percent_label = tk.Label(title_frame, text="", bg="#2b2b2b", font=("Segoe UI", 10, "bold"), fg=accent)
    percent_label.pack(side="left")
    speed_label = tk.Label(title_frame, text="", bg="#2b2b2b", font=("Segoe UI", 10, "italic"), fg="#ccc")
    speed_label.pack(side="right", padx=5)

    log_widget = scrolledtext.ScrolledText(prog_frame, height=14, font=("Consolas", 9),
                                           bd=0, relief="flat", bg="#1e1e1e", fg="white")
    log_widget.pack(fill="both", expand=True, padx=10, pady=8)
    log_widget.configure(highlightbackground="#444", highlightcolor=accent, highlightthickness=1)
    log_widget.tag_config("black", foreground="white")
    log_widget.tag_config("green", foreground="#4caf50")
    log_widget.tag_config("red", foreground="#f44336")
    log_widget.tag_config("orange", foreground="#ff9800")

    def toggle_resolution(event=None):
        try:
            codec_dropdown.selection_clear()
            res_dropdown.selection_clear()
        except Exception:
            pass

        if "Audio Only" in codec_choice_var.get():
            res_frame.grid_remove()
            res_dropdown.configure(state="disabled")
        else:
            res_frame.grid()
            res_dropdown.configure(state="readonly")

    codec_dropdown.bind("<<ComboboxSelected>>", toggle_resolution)
    res_dropdown.bind("<<ComboboxSelected>>", lambda e: (res_dropdown.selection_clear()))
    toggle_resolution()

    def on_close():
        save_config({"codec": codec_choice_var.get(), "resolution": res_choice_var.get()})
        root.destroy()

    root.update_idletasks()
    root.minsize(560, 420)
    root.maxsize(1280, 1400)
    root.resizable(False, True)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__=="__main__":
    main()
