import customtkinter as ctk
from tkinter import messagebox, Menu
import threading
from config import load_config, save_config, DOWNLOAD_DIR, open_folder, FFMPEG_PATH
from downloader import download_videos, cancel_download, translations, detect_available_codecs


def main():
    config = load_config()

    # === Light Theme Colors ===
    BG_COLOR = "#F9FAFB"          # Putih lembut
    CARD_COLOR = "#FFFFFF"        # Putih murni (card utama)
    TEXT_COLOR = "#111827"        # Hitam keabu-abuan
    PRIMARY_COLOR = "#1D4ED8"     # Biru utama
    SECONDARY_COLOR = "#E5E7EB"   # Abu untuk tombol open
    BORDER_COLOR = "#D1D5DB"      # Abu border tipis

    ctk.set_appearance_mode("light")

    root = ctk.CTk()
    root.title("YT-Downloader")
    root.geometry(config.get("geometry", "720x480"))
    root.configure(fg_color=BG_COLOR)

    # === Main Container ===
    container = ctk.CTkFrame(root, corner_radius=16, fg_color=CARD_COLOR, border_width=0)
    container.pack(fill="both", expand=True, padx=20, pady=20)

    # === Title ===
    title_label = ctk.CTkLabel(container, text="YT-Downloader",
                               font=("Arial", 20, "bold"), text_color=PRIMARY_COLOR)
    title_label.pack(pady=(15, 10))

    # === Top Input Section ===
    input_frame = ctk.CTkFrame(container, fg_color="transparent")
    input_frame.pack(fill="x", padx=25, pady=(5, 10))

    url_text = ctk.CTkEntry(input_frame, placeholder_text="Paste YouTube Link Here",
                            fg_color="white", text_color=TEXT_COLOR,
                            border_color=BORDER_COLOR, border_width=1,
                            height=40, corner_radius=12)
    url_text.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def start_or_cancel():
        if download_btn.cget("text") == "Cancel":
            cancel_download()
            return
        urls = [u.strip() for u in url_text.get().splitlines() if u.strip()]
        if not urls:
            messagebox.showwarning(translations["warning"], translations["warn_url"])
            return
        log_widget.delete("1.0", "end")
        log_widget.insert("end", translations["start_download"] + "\n")
        progress_bar.set(0.0)
        download_btn.configure(text="Cancel")
        threading.Thread(target=download_videos,
                         args=(urls, codec_choice_var.get(), res_choice_var.get(),
                               log_widget, prog_label, speed_label, download_btn, progress_bar, phase_label),
                         daemon=True).start()

    download_btn = ctk.CTkButton(input_frame, text="Download", command=start_or_cancel,
                                 height=40, width=110, corner_radius=12,
                                 fg_color=PRIMARY_COLOR, hover_color="#2563EB", text_color="white")
    download_btn.pack(side="left")

    open_btn = ctk.CTkButton(input_frame, text="Open Folder", command=lambda: open_folder(DOWNLOAD_DIR),
                             height=40, width=120, corner_radius=12,
                             fg_color=SECONDARY_COLOR, hover_color="#D1D5DB", text_color=TEXT_COLOR)
    open_btn.pack(side="left", padx=(10, 0))

    # === Codec & Resolution ===
    option_frame = ctk.CTkFrame(container, fg_color="transparent")
    option_frame.pack(fill="x", padx=25, pady=(0, 15))

    available_codecs = detect_available_codecs(FFMPEG_PATH)
    codec_values = list(available_codecs.keys())
    codec_choice_var = ctk.StringVar(value=config.get("codec", codec_values[0]))

    codec_frame = ctk.CTkFrame(option_frame, fg_color="white", border_color=BORDER_COLOR,
                               border_width=1, corner_radius=12)
    codec_frame.pack(side="left", padx=(0, 20))

    codec_dropdown = ctk.CTkOptionMenu(
        codec_frame,
        variable=codec_choice_var,
        values=codec_values,
        fg_color="white",
        text_color=PRIMARY_COLOR,
        button_color="white",
        button_hover_color="white",
        dropdown_fg_color="white",
        dropdown_hover_color=PRIMARY_COLOR,
        dropdown_text_color="black",
        width=160,
        height=34,
        corner_radius=12
    )
    codec_dropdown.pack(fill="both", expand=True, padx=1, pady=1)
    codec_dropdown._dropdown_menu.configure(activeforeground="white")

    res_choice_var = ctk.StringVar(value=config.get("resolution", "1080p"))

    res_frame = ctk.CTkFrame(option_frame, fg_color="white", border_color=BORDER_COLOR,
                             border_width=1, corner_radius=12)
    res_frame.pack(side="left")

    res_dropdown = ctk.CTkOptionMenu(
        res_frame,
        variable=res_choice_var,
        values=[
            "144p", "240p", "360p", "480p", "720p", "1080p",
            "1440p (2K)", "2160p (4K)", "4320p (8K)"
        ],
        fg_color="white",
        text_color=PRIMARY_COLOR,
        button_color="white",
        button_hover_color="white",
        dropdown_fg_color="white",
        dropdown_hover_color=PRIMARY_COLOR,
        dropdown_text_color=TEXT_COLOR,
        width=140,
        height=34,
        corner_radius=12
    )
    res_dropdown.pack(fill="both", expand=True, padx=1, pady=1)
    res_dropdown._dropdown_menu.configure(activeforeground="white")

    # === Progress Section ===
    prog_label = ctk.CTkLabel(container, text="Progress", font=("Arial", 12, "bold"), text_color=PRIMARY_COLOR)
    prog_label.pack(anchor="w", padx=25, pady=(0, 2))

    progress_bar = ctk.CTkProgressBar(container, fg_color=BORDER_COLOR, progress_color=PRIMARY_COLOR, height=15,
                                      corner_radius=12)
    progress_bar.set(0.0)
    progress_bar.pack(fill="x", padx=25, pady=(0, 12))

    phase_label = ctk.CTkLabel(container, text="", font=("Arial", 12, "bold"), text_color=PRIMARY_COLOR)
    phase_label.pack(anchor="center", pady=(0, 5))

    speed_label = ctk.CTkLabel(container, text="", font=("Arial", 11), text_color=TEXT_COLOR)
    speed_label.pack(anchor="e", padx=25, pady=(0, 5))

    # === Logs Section ===
    log_label = ctk.CTkLabel(container, text="Logs", font=("Arial", 12, "bold"), text_color=PRIMARY_COLOR)
    log_label.pack(anchor="w", padx=25, pady=(0, 2))

    log_widget = ctk.CTkTextbox(container, height=140, fg_color="#F3F4F6", text_color=TEXT_COLOR,
                                border_width=1, border_color=BORDER_COLOR, corner_radius=12)
    log_widget.pack(fill="both", expand=True, padx=25, pady=(0, 20))
    log_widget.tag_config("warning", foreground="orange")
    log_widget.tag_config("error", foreground="red")

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

    menu = Menu(url_text, tearoff=0, bg="white", fg=TEXT_COLOR)
    menu.add_command(label="Copy", command=copy_text)
    menu.add_command(label="Paste", command=paste_text)

    def show_context_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    url_text.bind("<Button-3>", show_context_menu)

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