import customtkinter as ctk
from tkinter import messagebox, Menu
import threading
from config import load_config, save_config, DOWNLOAD_DIR, open_folder, FFMPEG_PATH
from downloader import download_videos, cancel_download, translations, detect_available_codecs

def main():
    config = load_config()

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("🎬 YouTube Downloader")
    root.geometry(config.get("geometry", "913x572+312+208"))

    # === Card container ===
    card = ctk.CTkFrame(root, corner_radius=15, fg_color=("gray10", "gray10"))
    card.pack(expand=True, fill="both", padx=40, pady=40)

    # === Left side: Format + Resolution ===
    left_frame = ctk.CTkFrame(card, fg_color="transparent")
    left_frame.pack(side="left", fill="y", padx=(20,10), pady=20)

    codec_label = ctk.CTkLabel(left_frame, text="Format", font=("Segoe UI", 14))
    codec_label.pack(anchor="w", pady=(0,5))

    available_codecs = detect_available_codecs(FFMPEG_PATH)
    codec_values = list(available_codecs.keys())
    codec_choice_var = ctk.StringVar(value=config.get("codec", codec_values[0]))

    codec_dropdown = ctk.CTkComboBox(left_frame, variable=codec_choice_var, values=codec_values, width=180)
    codec_dropdown.pack(pady=(0,20))

    # 🔹 Klik area dropdown langsung buka menu
    codec_dropdown.bind("<Button-1>", lambda e: codec_dropdown._open_dropdown_menu())

    res_label = ctk.CTkLabel(left_frame, text="Resolution", font=("Segoe UI", 14))
    res_label.pack(anchor="w", pady=(0,5))

    res_choice_var = ctk.StringVar(value=config.get("resolution", "1080p"))
    res_dropdown = ctk.CTkComboBox(left_frame, variable=res_choice_var, values=[
        "144p","240p","360p","480p","720p","1080p","1440p (2K)","2160p (4K)","4320p (8K)"], width=180)
    res_dropdown.pack()

    # 🔹 Klik area dropdown langsung buka menu
    res_dropdown.bind("<Button-1>", lambda e: res_dropdown._open_dropdown_menu())

    # === Right side: Input + Buttons + Progress + Log ===
    right_frame = ctk.CTkFrame(card, fg_color="transparent")
    right_frame.pack(side="right", fill="both", expand=True, padx=(10,20), pady=20)

    url_label = ctk.CTkLabel(right_frame, text="Enter Video Link Here", font=("Segoe UI", 14))
    url_label.pack(anchor="w")

    url_text = ctk.CTkTextbox(right_frame, height=55, font=("Segoe UI", 13))
    url_text.pack(fill="x", pady=(5,15))

    # === Enable Copy/Paste (Keyboard Shortcuts) ===
    url_text.bind("<Control-c>", lambda e: url_text.event_generate("<<Copy>>"))
    url_text.bind("<Control-x>", lambda e: url_text.event_generate("<<Cut>>"))
    url_text.bind("<Control-v>", lambda e: url_text.event_generate("<<Paste>>"))

    # === Right-Click Context Menu ===
    def paste_from_clipboard():
        try:
            text = root.clipboard_get()
            url_text.insert("insert", text)
        except:
            pass

    def show_context_menu(event):
        url_text.focus_set()
        menu = Menu(url_text, tearoff=0, bg="#2b2b2b", fg="white",
                    activebackground="#444", activeforeground="white")
        menu.add_command(label="Cut", command=lambda: url_text.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: url_text.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=paste_from_clipboard)
        menu.tk_popup(event.x_root, event.y_root)

    url_text.bind("<Button-3>", show_context_menu)

    # === Button Row ===
    btn_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
    btn_frame.pack(fill="x", pady=(0,15))

    def start_or_cancel():
        if download_btn.cget("text") == "⏹ Cancel":
            cancel_download()
            return
        urls = [u.strip() for u in url_text.get("1.0", "end").splitlines() if u.strip()]
        if not urls:
            messagebox.showwarning(translations["warning"], translations["warn_url"])
            return
        log_text.configure(state="normal")
        log_text.delete("1.0", "end")
        log_text.insert("end", translations["start_download"] + "\n", "info")
        log_text.configure(state="disabled")
        progress_bar.set(0.0)
        download_btn.configure(text="⏹ Cancel")
        threading.Thread(target=download_videos,
                         args=(urls, codec_choice_var.get(), res_choice_var.get(),
                               log_text, prog_label, speed_label,
                               download_btn, progress_bar, phase_label),
                         daemon=True).start()

    download_btn = ctk.CTkButton(btn_frame, text="Download", command=start_or_cancel,
                                 fg_color="green", hover_color="darkgreen",
                                 font=("Segoe UI", 14, "bold"), width=140, height=40, corner_radius=8)
    download_btn.pack(side="left", padx=(0,10))

    open_btn = ctk.CTkButton(btn_frame, text="Open Folder",
                             command=lambda: open_folder(DOWNLOAD_DIR),
                             fg_color="transparent", border_width=2,
                             text_color=("white"), width=140, height=40, corner_radius=8)
    open_btn.pack(side="left")

    # === Progress + Status ===
    phase_label = ctk.CTkLabel(right_frame, text="", font=("Segoe UI", 13, "bold"))
    phase_label.pack(anchor="w")

    progress_bar = ctk.CTkProgressBar(right_frame, height=14)  # ⬅️ ketebalan bar bisa diedit di sini
    progress_bar.set(0.0)
    progress_bar.pack(fill="x", pady=(5,5))

    prog_label = ctk.CTkLabel(right_frame, text=translations["progress"], font=("Segoe UI", 12))
    prog_label.pack(anchor="w")

    speed_label = ctk.CTkLabel(right_frame, text="", font=("Segoe UI", 12))
    speed_label.pack(anchor="e")

    # === Log Output (Colored) ===
    log_text = ctk.CTkTextbox(right_frame, height=120, font=("Consolas", 11))
    log_text.pack(fill="both", expand=True, pady=(10,0))
    log_text.configure(state="disabled")

    # Apply tags for color
    log_text.tag_config("info", foreground="white")
    log_text.tag_config("warning", foreground="yellow")
    log_text.tag_config("error", foreground="red")

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
