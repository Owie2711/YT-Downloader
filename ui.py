import customtkinter as ctk
from tkinter import messagebox
import threading
from config import load_config, save_config, DOWNLOAD_DIR, open_folder, FFMPEG_PATH
from downloader import download_videos, cancel_download, translations, detect_available_codecs

def main():
    config = load_config()

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("🎬 YouTube Downloader")
    root.geometry(config.get("geometry", "600x750"))

    # === URL Input ===
    url_label = ctk.CTkLabel(root, text="🔗 Enter YouTube URL")
    url_label.pack(anchor="w", padx=20, pady=(10,2))
    url_text = ctk.CTkTextbox(root, height=100)
    url_text.pack(fill="x", padx=20, pady=5)

    # === Codec Selection (auto detect from ffmpeg) ===
    codec_label = ctk.CTkLabel(root, text="🎞 Format Options")
    codec_label.pack(anchor="w", padx=20, pady=(10,2))

    available_codecs = detect_available_codecs(FFMPEG_PATH)
    codec_values = list(available_codecs.keys())

    codec_choice_var = ctk.StringVar(value=config.get("codec", codec_values[0]))
    codec_dropdown = ctk.CTkComboBox(root, variable=codec_choice_var, values=codec_values)
    codec_dropdown.pack(fill="x", padx=20, pady=5)

    # === Resolution Selection ===
    res_label = ctk.CTkLabel(root, text="📺 Resolution Options")
    res_label.pack(anchor="w", padx=20, pady=(10,2))
    res_choice_var = ctk.StringVar(value=config.get("resolution", "1080p"))
    res_dropdown = ctk.CTkComboBox(root, variable=res_choice_var, values=[
        "144p","240p","360p","480p","720p","1080p","1440p (2K)","2160p (4K)","4320p (8K)"])
    res_dropdown.pack(fill="x", padx=20, pady=5)

    # === Buttons + Progress ===
    btn_frame = ctk.CTkFrame(root, fg_color="transparent")
    btn_frame.pack(pady=12)

    prog_label = ctk.CTkLabel(root, text=translations["progress"])
    prog_label.pack(anchor="w", padx=20, pady=(10,2))
    progress_bar = ctk.CTkProgressBar(root)
    progress_bar.set(0.0)
    progress_bar.pack(fill="x", padx=20, pady=(0,5))
    phase_label = ctk.CTkLabel(root, text="", font=("Segoe UI", 12, "bold"))
    phase_label.pack(anchor="center", pady=(0,5))
    speed_label = ctk.CTkLabel(root, text="")
    speed_label.pack(anchor="e", padx=20)
    log_widget = ctk.CTkTextbox(root, height=200)
    log_widget.pack(fill="both", expand=True, padx=20, pady=10)
    log_widget.tag_config("warning", foreground="orange")
    log_widget.tag_config("error", foreground="red")

    # === Download Button ===
    def start_or_cancel():
        if download_btn.cget("text") == "⏹️ Cancel":
            cancel_download()
            return
        urls = [u.strip() for u in url_text.get("1.0", "end").splitlines() if u.strip()]
        if not urls:
            messagebox.showwarning(translations["warning"], translations["warn_url"])
            return
        log_widget.delete("1.0", "end")
        log_widget.insert("end", translations["start_download"] + "\n")
        progress_bar.set(0.0)
        download_btn.configure(text="⏹️ Cancel")
        threading.Thread(target=download_videos,
                         args=(urls, codec_choice_var.get(), res_choice_var.get(),
                               log_widget, prog_label, speed_label, download_btn, progress_bar, phase_label),
                         daemon=True).start()

    download_btn = ctk.CTkButton(btn_frame, text="⬇️ Download", command=start_or_cancel)
    download_btn.pack(side="left", padx=12)

    open_btn = ctk.CTkButton(btn_frame, text="📂 Open Folder", command=lambda: open_folder(DOWNLOAD_DIR))
    open_btn.pack(side="left", padx=12)

    # === Save Config on Close ===
    def on_close():
        save_config({
            "codec": codec_choice_var.get(),
            "resolution": res_choice_var.get(),
            "geometry": root.geometry()
        })
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
