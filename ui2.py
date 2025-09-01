import customtkinter as ctk
from tkinter import messagebox, Menu
import threading
from config import load_config, save_config, DOWNLOAD_DIR, open_folder, FFMPEG_PATH
from downloader import download_videos, cancel_download, translations, detect_available_codecs


def main():
    config = load_config()

    # === Futuristic Theme Colors ===
    BG_COLOR = "#0A0F1E"          # Deep space blue-black
    CARD_COLOR = "#141A2E"       # Futuristic card dark blue
    TEXT_COLOR = "#E6F1FF"       # Light cyan-white
    BTN_PRIMARY = ("#00C9FF", "#92FE9D")   # Cyan → Green gradient
    BTN_ACCENT = ("#FF6FD8", "#3813C2")    # Pink → Purple gradient
    HIGHLIGHT = "#00FFC6"        # Neon accent

    ctk.set_appearance_mode("dark")

    root = ctk.CTk()
    root.title("🚀 Futuristic YouTube Downloader")
    root.geometry(config.get("geometry", "820x500"))
    root.configure(fg_color=BG_COLOR)

    # === Main Container with neon border effect ===
    container = ctk.CTkFrame(root, corner_radius=20, fg_color=CARD_COLOR, border_width=2, border_color=HIGHLIGHT)
    container.pack(fill="both", expand=True, padx=25, pady=25)

    # === Left Panel ===
    left_panel = ctk.CTkFrame(container, corner_radius=15, fg_color=CARD_COLOR)
    left_panel.pack(side="left", fill="y", padx=(20, 10), pady=20)

    codec_label = ctk.CTkLabel(left_panel, text="Format", font=("Consolas", 14, "bold"), text_color=TEXT_COLOR)
    codec_label.pack(anchor="w", padx=15, pady=(15, 5))

    available_codecs = detect_available_codecs(FFMPEG_PATH)
    codec_values = list(available_codecs.keys())
    codec_choice_var = ctk.StringVar(value=config.get("codec", codec_values[0]))
    codec_dropdown = ctk.CTkComboBox(left_panel, variable=codec_choice_var, values=codec_values,
                                     fg_color=BG_COLOR, text_color=TEXT_COLOR, button_color=HIGHLIGHT,
                                     dropdown_fg_color=CARD_COLOR, dropdown_text_color=TEXT_COLOR)
    codec_dropdown.pack(fill="x", padx=15, pady=(0, 15))

    res_label = ctk.CTkLabel(left_panel, text="Resolution", font=("Consolas", 14, "bold"), text_color=TEXT_COLOR)
    res_label.pack(anchor="w", padx=15, pady=(0, 5))

    res_choice_var = ctk.StringVar(value=config.get("resolution", "1080p"))
    res_dropdown = ctk.CTkComboBox(left_panel, variable=res_choice_var, values=[
        "144p", "240p", "360p", "480p", "720p", "1080p", "1440p (2K)", "2160p (4K)", "4320p (8K)"],
        fg_color=BG_COLOR, text_color=TEXT_COLOR, button_color=HIGHLIGHT,
        dropdown_fg_color=CARD_COLOR, dropdown_text_color=TEXT_COLOR)
    res_dropdown.pack(fill="x", padx=15, pady=(0, 15))

    # === Right Panel ===
    right_panel = ctk.CTkFrame(container, corner_radius=15, fg_color=CARD_COLOR)
    right_panel.pack(side="left", fill="both", expand=True, padx=(10, 20), pady=20)

    url_label = ctk.CTkLabel(right_panel, text="Paste Video Link", font=("Consolas", 14, "bold"), text_color=HIGHLIGHT)
    url_label.pack(anchor="w", padx=15, pady=(15, 5))

    url_text = ctk.CTkTextbox(right_panel, height=60, fg_color=BG_COLOR, text_color=TEXT_COLOR, corner_radius=10,
                              border_width=1, border_color=HIGHLIGHT)
    url_text.pack(fill="x", padx=15, pady=(0, 12))

    # === Context Menu (Copy/Paste) ===
    def paste_text():
        try:
            clip = root.clipboard_get()
            url_text.insert("insert", clip)
        except Exception:
            pass

    def copy_text():
        try:
            selected = url_text.get("sel.first", "sel.last")
            root.clipboard_clear()
            root.clipboard_append(selected)
        except Exception:
            pass

    menu = Menu(url_text, tearoff=0, bg=CARD_COLOR, fg=TEXT_COLOR)
    menu.add_command(label="Copy", command=copy_text)
    menu.add_command(label="Paste", command=paste_text)

    def show_context_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    url_text.bind("<Button-3>", show_context_menu)

    # === Buttons ===
    btn_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
    btn_frame.pack(fill="x", padx=15, pady=(0, 12))

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

    # Futuristic Gradient Buttons
    download_btn = ctk.CTkButton(btn_frame, text="⬇ Download", command=start_or_cancel, height=42, width=150,
                                 fg_color=BTN_PRIMARY[0], hover_color=BTN_PRIMARY[1], text_color="black",
                                 font=("Consolas", 13, "bold"), corner_radius=14)
    download_btn.pack(side="left", padx=(0, 12))

    open_btn = ctk.CTkButton(btn_frame, text="📂 Open Folder", command=lambda: open_folder(DOWNLOAD_DIR), height=42, width=150,
                              fg_color=BTN_ACCENT[0], hover_color=BTN_ACCENT[1], text_color="white",
                              font=("Consolas", 13, "bold"), corner_radius=14)
    open_btn.pack(side="left")

    # === Progress Section ===
    prog_label = ctk.CTkLabel(right_panel, text="Progress:", font=("Consolas", 12), text_color=TEXT_COLOR)
    prog_label.pack(anchor="w", padx=15, pady=(5, 2))

    progress_bar = ctk.CTkProgressBar(right_panel, fg_color=BG_COLOR, progress_color=HIGHLIGHT)
    progress_bar.set(0.0)
    progress_bar.pack(fill="x", padx=15, pady=(0, 8))

    phase_label = ctk.CTkLabel(right_panel, text="", font=("Consolas", 12, "bold"), text_color=HIGHLIGHT)
    phase_label.pack(anchor="center", pady=(0, 5))

    speed_label = ctk.CTkLabel(right_panel, text="", font=("Consolas", 11), text_color=TEXT_COLOR)
    speed_label.pack(anchor="e", padx=15, pady=(0, 5))

    log_widget = ctk.CTkTextbox(right_panel, height=140, fg_color=BG_COLOR, text_color=TEXT_COLOR,
                                border_width=1, border_color=HIGHLIGHT)
    log_widget.pack(fill="both", expand=True, padx=15, pady=10)
    log_widget.tag_config("warning", foreground="orange")
    log_widget.tag_config("error", foreground="red")

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
