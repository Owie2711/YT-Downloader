import customtkinter as ctk
from tkinter import messagebox, Menu
import threading
import platform
import sys
from config import load_config, save_config, DOWNLOAD_DIR, open_folder, FFMPEG_PATH
from downloader import download_videos, cancel_download, translations, detect_available_codecs

# Windows-specific import with fallback
try:
    import winreg
except ImportError:
    winreg = None

def detect_system_theme():
    """Detect system theme (light/dark)"""
    try:
        if platform.system() == "Windows" and winreg:
            # Windows 10/11 theme detection
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value == 1 else "dark"
        elif platform.system() == "Darwin":  # macOS
            import subprocess
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"], 
                capture_output=True, text=True, timeout=5
            )
            return "dark" if "Dark" in result.stdout else "light"
        else:  # Linux - fallback to light
            return "light"
    except Exception:
        return "light"  # Default fallback

def get_theme_colors(theme_mode):
    """Get color palette based on theme mode"""
    if theme_mode == "dark":
        return {
            "BG_COLOR": "#0F172A",
            "CARD_COLOR": "#1E293B", 
            "TEXT_COLOR": "#F8FAFC",
            "PRIMARY_COLOR": "#3B82F6",
            "SECONDARY_COLOR": "#374151",
            "BORDER_COLOR": "#475569",
            "ACCENT_COLOR": "#1F2937",
            "HOVER_COLOR": "#2563EB",
            "PLACEHOLDER_COLOR": "#94A3B8",
            "LABEL_COLOR": "#94A3B8",
            "WARNING_COLOR": "#F59E0B",
            "ERROR_COLOR": "#EF4444"
        }
    else:  # light theme
        return {
            "BG_COLOR": "#F9FAFB",
            "CARD_COLOR": "#FFFFFF",
            "TEXT_COLOR": "#111827",
            "PRIMARY_COLOR": "#1D4ED8",
            "SECONDARY_COLOR": "#E5E7EB",
            "BORDER_COLOR": "#D1D5DB",
            "ACCENT_COLOR": "#F8FAFC",
            "HOVER_COLOR": "#2563EB",
            "PLACEHOLDER_COLOR": "#6B7280",
            "LABEL_COLOR": "#6B7280",
            "WARNING_COLOR": "#D97706",
            "ERROR_COLOR": "#DC2626"
        }

def main():
    config = load_config()

    # === Validate FFMPEG before proceeding ===
    if not FFMPEG_PATH:
        messagebox.showerror("Error", "FFMPEG not found! Please install FFMPEG or place it in the application directory.")
        return

    # === Auto-detect system theme ===
    system_theme = detect_system_theme()
    colors = get_theme_colors(system_theme)
    
    # Extract colors for easier use
    BG_COLOR = colors["BG_COLOR"]
    CARD_COLOR = colors["CARD_COLOR"]
    TEXT_COLOR = colors["TEXT_COLOR"]
    PRIMARY_COLOR = colors["PRIMARY_COLOR"]
    SECONDARY_COLOR = colors["SECONDARY_COLOR"]
    BORDER_COLOR = colors["BORDER_COLOR"]
    ACCENT_COLOR = colors["ACCENT_COLOR"]
    HOVER_COLOR = colors["HOVER_COLOR"]

    # Set CustomTkinter appearance mode to match system
    ctk.set_appearance_mode(system_theme)

    root = ctk.CTk()
    root.title("YT-Downloader")
    
    # Validate and set geometry safely
    geometry = config.get("geometry", "645x565+423+99")
    try:
        # Basic geometry validation
        if "x" in geometry and geometry.count("x") == 1:
            parts = geometry.split("x")
            width = int(parts[0])
            # Handle position part if exists
            if "+" in parts[1]:
                height_pos = parts[1].split("+")
                height = int(height_pos[0])
                x_pos = int(height_pos[1]) if len(height_pos) > 1 else 423
                y_pos = int(height_pos[2]) if len(height_pos) > 2 else 99
            else:
                height = int(parts[1])
                x_pos, y_pos = 423, 99
            
            if 400 <= width <= 2000 and 300 <= height <= 1500:  # Reasonable bounds
                root.geometry(geometry)
            else:
                root.geometry("645x565+423+99")
        else:
            root.geometry("645x565+423+99")
    except (ValueError, IndexError):
        root.geometry("645x565+423+99")
    
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
                            fg_color=ACCENT_COLOR, text_color=TEXT_COLOR,
                            border_color=BORDER_COLOR, border_width=1,
                            placeholder_text_color=colors["PLACEHOLDER_COLOR"],
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
                               log_widget, prog_label, speed_label, download_btn, progress_bar, phase_label, root),
                         daemon=True).start()

    download_btn = ctk.CTkButton(input_frame, text="Download", command=start_or_cancel,
                                 height=40, width=110, corner_radius=12,
                                 fg_color=PRIMARY_COLOR, hover_color=HOVER_COLOR, text_color="white")
    download_btn.pack(side="left")

    open_btn = ctk.CTkButton(input_frame, text="Open Folder", command=lambda: open_folder(DOWNLOAD_DIR),
                             height=40, width=120, corner_radius=12,
                             fg_color=SECONDARY_COLOR, 
                             hover_color="#4B5563" if system_theme == "dark" else "#D1D5DB", 
                             text_color=TEXT_COLOR)
    open_btn.pack(side="left", padx=(10, 0))

    # === Codec & Resolution with Enhanced Error Handling ===
    option_frame = ctk.CTkFrame(container, fg_color="transparent")
    
    # === Labels for Dropdowns (Create BEFORE dropdowns) ===
    label_frame = ctk.CTkFrame(container, fg_color="transparent")
    label_frame.pack(fill="x", padx=25, pady=(0, 5))

    codec_label = ctk.CTkLabel(label_frame, text="Format", 
                                  font=("Arial", 11, "bold"), 
                                  text_color=colors["LABEL_COLOR"])
    codec_label.pack(side="left", padx=(0, 15))

    res_label = ctk.CTkLabel(label_frame, text="Quality", 
                                font=("Arial", 11, "bold"), 
                                text_color=colors["LABEL_COLOR"])
    res_label.pack(side="left", padx=(165, 0))

    # Now pack the option frame
    option_frame.pack(fill="x", padx=25, pady=(0, 15))

    try:
        available_codecs = detect_available_codecs(FFMPEG_PATH)
        codec_values = list(available_codecs.keys())
        
        # Ensure we have at least one codec
        if not codec_values:
            codec_values = ["H.264 (CPU libx264)"]  # Fallback
            messagebox.showwarning("Warning", "No hardware encoders detected. Using CPU encoding.")
            
    except Exception as e:
        codec_values = ["H.264 (CPU libx264)"]  # Safe fallback
        messagebox.showerror("Error", f"Codec detection failed: {e}")

    # Validate codec from config
    saved_codec = config.get("codec", "")
    if saved_codec in codec_values:
        default_codec = saved_codec
    else:
        default_codec = codec_values[0]

    codec_choice_var = ctk.StringVar(value=default_codec)

    # Codec dropdown with enhanced error handling
    codec_dropdown = ctk.CTkOptionMenu(
        option_frame,
        variable=codec_choice_var,
        values=codec_values,
        fg_color=ACCENT_COLOR,
        text_color=TEXT_COLOR,
        button_color=ACCENT_COLOR,
        button_hover_color="#374151" if system_theme == "dark" else "#DBEAFE",
        dropdown_fg_color=CARD_COLOR,
        dropdown_hover_color=PRIMARY_COLOR,
        dropdown_text_color=TEXT_COLOR,
        width=180,
        height=40,
        corner_radius=8,
        font=("Arial", 12),
        anchor="w"
    )
    codec_dropdown.pack(side="left", padx=(0, 15))
    
    # Configure dropdown menu with error handling
    try:
        codec_dropdown._dropdown_menu.configure(
            activeforeground="white",
            activebackground=PRIMARY_COLOR,
            selectcolor=PRIMARY_COLOR,
            bg=CARD_COLOR,
            fg=TEXT_COLOR,
            relief="flat",
            bd=0
        )
    except Exception:
        pass

    res_choice_var = ctk.StringVar(value=config.get("resolution", "1080p"))

    # Resolution dropdown with enhanced styling
    res_dropdown = ctk.CTkOptionMenu(
        option_frame,
        variable=res_choice_var,
        values=[
            "144p", "240p", "360p", "480p", "720p", "1080p",
            "1440p (2K)", "2160p (4K)", "4320p (8K)"
        ],
        fg_color=ACCENT_COLOR,
        text_color=TEXT_COLOR,
        button_color=ACCENT_COLOR,
        button_hover_color="#374151" if system_theme == "dark" else "#DBEAFE",
        dropdown_fg_color=CARD_COLOR,
        dropdown_hover_color=PRIMARY_COLOR,
        dropdown_text_color=TEXT_COLOR,
        width=140,
        height=40,
        corner_radius=8,
        font=("Arial", 12),
        anchor="w"
    )
    res_dropdown.pack(side="left")
    
    # Configure dropdown menu with error handling
    try:
        res_dropdown._dropdown_menu.configure(
            activeforeground="white",
            activebackground=PRIMARY_COLOR,
            selectcolor=PRIMARY_COLOR,
            bg=CARD_COLOR,
            fg=TEXT_COLOR,
            relief="flat",
            bd=0
        )
    except Exception:
        pass

    # === Callback function to show/hide resolution options ===
    def on_codec_change(*args):
        """Hide resolution dropdown when audio-only format is selected"""
        try:
            selected_codec = codec_choice_var.get()
            if "Audio Only" in selected_codec:
                # Hide resolution dropdown and label
                res_dropdown.pack_forget()
                res_label.configure(text="")
            else:
                # Show resolution dropdown and label
                res_dropdown.pack(side="left")
                res_label.configure(text="Quality")
        except Exception:
            pass

    # Bind the callback to codec selection changes
    codec_choice_var.trace_add("write", on_codec_change)
    
    # Initialize the UI state based on current codec selection
    on_codec_change()

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

    log_widget = ctk.CTkTextbox(container, height=140, fg_color=ACCENT_COLOR, text_color=TEXT_COLOR,
                                border_width=1, border_color=BORDER_COLOR, corner_radius=12)
    log_widget.pack(fill="both", expand=True, padx=25, pady=(0, 20))
    log_widget.tag_config("warning", foreground=colors["WARNING_COLOR"])
    log_widget.tag_config("error", foreground=colors["ERROR_COLOR"])

    # === Enhanced Context Menu with widget validation ===
    def paste_text():
        try:
            if not url_text.winfo_exists():
                return
            clip = root.clipboard_get()
            if clip:
                # Clear existing text and insert new
                url_text.delete(0, "end")
                url_text.insert(0, clip)
        except Exception:
            pass

    def copy_text():
        try:
            if not url_text.winfo_exists():
                return
            text = url_text.get()
            if text:
                root.clipboard_clear()
                root.clipboard_append(text)
        except Exception:
            pass

    def show_context_menu(event):
        try:
            if url_text.winfo_exists() and menu.winfo_exists():
                menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass

    menu = Menu(url_text, tearoff=0, 
                bg=CARD_COLOR, fg=TEXT_COLOR, 
                activebackground=PRIMARY_COLOR, activeforeground="white",
                relief="flat", bd=0)
    menu.add_command(label="Copy", command=copy_text)
    menu.add_command(label="Paste", command=paste_text)

    url_text.bind("<Button-3>", show_context_menu)

    # === Enhanced Close Handler ===
    def on_close():
        try:
            # Cancel any ongoing downloads
            cancel_download()
            
            # Save configuration safely
            config_data = {}
            try:
                config_data["codec"] = codec_choice_var.get()
            except Exception:
                pass
            try:
                config_data["resolution"] = res_choice_var.get()
            except Exception:
                pass
            try:
                config_data["geometry"] = root.geometry()
            except Exception:
                pass
            
            if config_data:  # Only save if we have valid data
                save_config(config_data)
                
        except Exception as e:
            print(f"Error during close: {e}")
        finally:
            try:
                root.destroy()
            except Exception:
                pass

    root.protocol("WM_DELETE_WINDOW", on_close)
    
    # Handle application shutdown gracefully
    try:
        root.mainloop()
    except KeyboardInterrupt:
        on_close()
    except Exception as e:
        print(f"Application error: {e}")
        on_close()

if __name__ == "__main__":
    main()