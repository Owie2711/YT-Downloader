import customtkinter as ctk
from tkinter import messagebox, Menu
import threading
from config import load_config, save_config, DOWNLOAD_DIR, open_folder, FFMPEG_PATH
from downloader import download_videos, cancel_download, translations, detect_available_codecs


def main():
    config = load_config()

    # === Modern Minimalist Deep Dark Theme Colors ===
    BG_COLOR = "#0D0D0D"           # Deep dark background
    CARD_COLOR = "#1E1E1E"         # Slightly lighter for panels/cards
    TEXT_COLOR = "#E6E6E6"         # Light text for high contrast
    ACCENT_GREEN = "#4CAF50"       # Elegant green accent
    ACCENT_GREEN_HOVER = "#45A049"
    BTN_SECONDARY = "#333333"      # Neutral button color
    BTN_SECONDARY_HOVER = "#444444"
    WARNING_COLOR = "#FFD700"
    ERROR_COLOR = "#F44336"

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")

    root = ctk.CTk()
    root.title("🎬 YouTube Downloader")
    root.geometry(config.get("geometry", "780x480"))
    root.configure(fg_color=BG_COLOR)

    # === Main Container (Central Card) ===
    container = ctk.CTkFrame(root, corner_radius=15, fg_color=CARD_COLOR)
    container.pack(fill="both", expand=True, padx=25, pady=25)

    # === Left Panel: Format & Resolution ===
    left_panel = ctk.CTkFrame(container, corner_radius=15, fg_color=CARD_COLOR)
    left_panel.pack(side="left", fill="y", padx=(20, 10), pady=20)

    codec_label = ctk.CTkLabel(left_panel, text="Format", font=("Segoe UI", 14, "bold"), text_color=TEXT_COLOR)
    codec_label.pack(anchor="w", padx=15, pady=(15, 5))

    available_codecs = detect_available_codecs(FFMPEG_PATH)
    codec_values = list(available_codecs.keys())
    codec_choice_var = ctk.StringVar(value=config.get("codec", codec_values[0] if codec_values else "mp4"))
    codec_dropdown = ctk.CTkComboBox(left_panel, variable=codec_choice_var, values=codec_values,
                                     fg_color=BG_COLOR, text_color=TEXT_COLOR, button_color=ACCENT_GREEN,
                                     dropdown_fg_color=CARD_COLOR, dropdown_text_color=TEXT_COLOR,
                                     button_hover_color=ACCENT_GREEN_HOVER)
    codec_dropdown.pack(fill="x", padx=15, pady=(0, 15))

    res_label = ctk.CTkLabel(left_panel, text="Resolution", font=("Segoe UI", 14, "bold"), text_color=TEXT_COLOR)
    res_label.pack(anchor="w", padx=15, pady=(0, 5))

    res_choice_var = ctk.StringVar(value=config.get("resolution", "1080p"))
    res_dropdown = ctk.CTkComboBox(left_panel, variable=res_choice_var, values=[
        "144p", "240p", "360p", "480p", "720p", "1080p", "1440p (2K)", "2160p (4K)", "4320p (8K)"],
        fg_color=BG_COLOR, text_color=TEXT_COLOR, button_color=ACCENT_GREEN,
        dropdown_fg_color=CARD_COLOR, dropdown_text_color=TEXT_COLOR,
        button_hover_color=ACCENT_GREEN_HOVER)
    res_dropdown.pack(fill="x", padx=15, pady=(0, 15))

    # === Right Panel: Input + Buttons + Progress ===
    right_panel = ctk.CTkFrame(container, corner_radius=15, fg_color=CARD_COLOR)
    right_panel.pack(side="left", fill="both", expand=True, padx=(10, 20), pady=20)

    url_label = ctk.CTkLabel(right_panel, text="Enter Video Link Here", font=("Segoe UI", 14, "bold"), text_color=TEXT_COLOR)
    url_label.pack(anchor="w", padx=15, pady=(15, 5))

    url_text = ctk.CTkTextbox(right_panel, height=60, fg_color=BG_COLOR, text_color=TEXT_COLOR, corner_radius=10)
    url_text.pack(fill="x", padx=15, pady=(0, 12))

    # === Add Right-Click Menu (Copy/Paste) ===
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
        download_btn.configure(text="⏹️ Cancel", fg_color=ERROR_COLOR, hover_color="#C0392B")
        threading.Thread(target=download_videos,
                         args=(urls, codec_choice_var.get(), res_choice_var.get(),
                               log_widget, prog_label, speed_label, download_btn, progress_bar, phase_label,
                               ACCENT_GREEN, ACCENT_GREEN_HOVER),
                         daemon=True).start()

    download_btn = ctk.CTkButton(btn_frame, text="Download", command=start_or_cancel, height=40, width=140,
                                 fg_color=ACCENT_GREEN, hover_color=ACCENT_GREEN_HOVER, text_color="white",
                                 corner_radius=10)
    download_btn.pack(side="left", padx=(0, 10))

    open_btn = ctk.CTkButton(btn_frame, text="Open Folder", command=lambda: open_folder(DOWNLOAD_DIR), height=40, width=140,
                              fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_COLOR,
                              corner_radius=10)
    open_btn.pack(side="left")

    # === Progress Section ===
    prog_label = ctk.CTkLabel(right_panel, text="Downloading:", font=("Segoe UI", 12), text_color=TEXT_COLOR)
    prog_label.pack(anchor="w", padx=15, pady=(5, 2))

    progress_bar = ctk.CTkProgressBar(right_panel, fg_color=BG_COLOR, progress_color=ACCENT_GREEN)
    progress_bar.set(0.0)
    progress_bar.pack(fill="x", padx=15, pady=(0, 8))

    phase_label = ctk.CTkLabel(right_panel, text="", font=("Segoe UI", 12, "bold"), text_color=TEXT_COLOR)
    phase_label.pack(anchor="center", pady=(0, 5))

    speed_label = ctk.CTkLabel(right_panel, text="", font=("Segoe UI", 11), text_color=TEXT_COLOR)
    speed_label.pack(anchor="e", padx=15, pady=(0, 5))

    log_widget = ctk.CTkTextbox(right_panel, height=140, fg_color=BG_COLOR, text_color=TEXT_COLOR, corner_radius=10)
    log_widget.pack(fill="both", expand=True, padx=15, pady=10)
    log_widget.tag_config("warning", foreground=WARNING_COLOR)
    log_widget.tag_config("error", foreground=ERROR_COLOR)

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