"""
agent_ui.py — Tkinter GUI for the YantrAI Remote Agent.
Shows credentials input, live progress log, and final stream URL.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import asyncio


import json
import os
import sys

# Optional Windows-only import for registry
try:
    import winreg
except ImportError:
    winreg = None

import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw, ImageTk

class AgentUI:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(__file__), "config.json")
        self.root = tk.Tk()
        self.root.title("yantrai Onsite")
        self.root.geometry("1000x800")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)
        self.root.minsize(1000, 750)

        # Tray support
        self.tray_icon = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Callbacks
        self.on_start = None  # Called when user clicks Start
        self.on_exit = None   # Called when app is fully exiting

        self._build_ui()
        self._setup_tray()

    def _build_ui(self):
        bg = "#1a1a2e"
        card_bg = "#16213e"
        accent = "#0f3460"
        text_color = "#e0e0e0"
        dim_color = "#8892b0"
        green = "#64ffda"

        # ── Global Header ──
        header = tk.Frame(self.root, bg=bg)
        header.pack(fill="x", padx=20, pady=(15, 5))

        tk.Label(header, text="⚡ yantrai Onsite",
                 font=("Segoe UI", 20, "bold"), fg=green, bg=bg).pack(side="left")
        
        # Official Badge (visible if frozen)
        if getattr(sys, 'frozen', False):
            badge = tk.Label(header, text="OFFICIAL", font=("Segoe UI", 7, "bold"),
                             fg=bg, bg=green, padx=5, pady=0)
            badge.pack(side="left", padx=10, pady=(5, 0))
        else:
            badge = tk.Label(header, text="DEV BUILD", font=("Segoe UI", 7, "bold"),
                             fg=text_color, bg="#334155", padx=5, pady=0)
            badge.pack(side="left", padx=10, pady=(5, 0))
        
        # Status Pills in header
        status_row = tk.Frame(header, bg=bg)
        status_row.pack(side="left", padx=20)
        self.pill_cam = self._create_pill(status_row, "Camera", "#475569")
        self.pill_bridge = self._create_pill(status_row, "Bridge", "#475569")
        self.pill_cloud = self._create_pill(status_row, "Cloud", "#475569")

        tk.Label(self.root, text="Local Bridge & Sentry | v1.0.0-Stable",
                 font=("Segoe UI", 10), fg=dim_color, bg=bg).pack(anchor="w", padx=20, pady=(0, 10))

        # ── Main Content Area (Two Columns) ──
        main_content = tk.Frame(self.root, bg=bg)
        main_content.pack(fill="both", expand=True, padx=10, pady=5)

        # Left Column: Configuration & Preview (Fixed width to avoid "creeping growth")
        left_col = tk.Frame(main_content, bg=bg, width=550)
        left_col.pack_propagate(False) # CRITICAL: Prevents children from expanding this column
        left_col.pack(side="left", fill="both", expand=False, padx=(10, 5))
        
        # Right Column: Progress Logs (Takes remaining space)
        right_col = tk.Frame(main_content, bg=bg)
        right_col.pack(side="right", fill="both", expand=True, padx=(5, 10))

        # ── LEFT COLUMN ITEMS ──
        
        # 1. Server Connection
        server_frame = tk.LabelFrame(left_col, text="Server Connection",
                                      font=("Segoe UI", 10, "bold"),
                                      fg=dim_color, bg=card_bg, bd=1)
        server_frame.pack(fill="x", pady=5)

        tk.Label(server_frame, text="Server URL:", fg=text_color, bg=card_bg,
                 font=("Segoe UI", 9)).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.server_entry = tk.Entry(server_frame, width=35, font=("Consolas", 10),
                                      bg="#0d1b2a", fg=text_color, insertbackground=text_color,
                                      relief="flat", bd=5)
        self.server_entry.insert(0, "https://ask-anything-cctv-280830514033.us-central1.run.app")
        self.server_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")

        tk.Label(server_frame, text="Site Name:", fg=text_color, bg=card_bg,
                 font=("Segoe UI", 9)).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.site_entry = tk.Entry(server_frame, width=35, font=("Consolas", 10),
                                    bg="#0d1b2a", fg=text_color, insertbackground=text_color,
                                    relief="flat", bd=5)
        self.site_entry.insert(0, "Factory-Site-1")
        self.site_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
        server_frame.columnconfigure(1, weight=1)

        # 2. Camera Source (Clickable Selection)
        cam_frame = tk.LabelFrame(left_col, text="What to Stream?",
                                    font=("Segoe UI", 10, "bold"),
                                    fg=dim_color, bg=card_bg, bd=1)
        cam_frame.pack(fill="x", pady=5)

        # Source selection variable
        self.source_choice = tk.StringVar(value="cctv")
        # Hidden entry for config compatibility
        self.manual_url_entry = tk.Entry(cam_frame)
        
        btn_row = tk.Frame(cam_frame, bg=card_bg)
        btn_row.pack(fill="x", padx=10, pady=8)

        self.btn_cctv = tk.Button(
            btn_row, text="📹  CCTV (Local Network)",
            font=("Segoe UI", 10, "bold"),
            bg=accent, fg="white", activebackground="#1a5276",
            relief="flat", bd=0, cursor="hand2", padx=15, pady=8,
            command=lambda: self._select_source("cctv")
        )
        self.btn_cctv.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_device = tk.Button(
            btn_row, text="💻  Device Camera",
            font=("Segoe UI", 10, "bold"),
            bg="#334155", fg="white", activebackground="#475569",
            relief="flat", bd=0, cursor="hand2", padx=15, pady=8,
            command=lambda: self._select_source("device")
        )
        self.btn_device.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # Credential Fields (shown only for CCTV)
        self.cred_frame = tk.Frame(cam_frame, bg=card_bg)
        self.cred_frame.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(self.cred_frame, text="Camera Username:", fg=text_color, bg=card_bg,
                 font=("Segoe UI", 9)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.user_entry = tk.Entry(self.cred_frame, width=25, font=("Consolas", 10),
                                    bg="#0d1b2a", fg=text_color, insertbackground=text_color,
                                    relief="flat", bd=5)
        self.user_entry.insert(0, "admin")
        self.user_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        tk.Label(self.cred_frame, text="Camera Password:", fg=text_color, bg=card_bg,
                 font=("Segoe UI", 9)).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.pass_entry = tk.Entry(self.cred_frame, width=25, font=("Consolas", 10),
                                    bg="#0d1b2a", fg=text_color, insertbackground=text_color,
                                    relief="flat", bd=5)
        self.pass_entry.insert(0, "password")
        self.pass_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.cred_frame.columnconfigure(1, weight=1)

        # Hidden: always use yantrai tunnel
        self.tunnel_method = tk.StringVar(value="yantrai")

        # 3. Options
        opt_frame = tk.Frame(left_col, bg=bg)
        opt_frame.pack(fill="x", pady=5)

        self.startup_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            opt_frame, text="🚀 Run on Windows Startup", 
            variable=self.startup_var,
            bg=bg, fg=text_color, selectcolor=accent,
            font=("Segoe UI", 9),
            command=self._on_startup_toggle
        ).pack(anchor="w", padx=5)

        # 4. Local Preview
        preview_frame = tk.LabelFrame(left_col, text="Local Monitor",
                                       font=("Segoe UI", 10, "bold"),
                                       fg=dim_color, bg=card_bg, bd=1)
        preview_frame.pack(fill="both", expand=True, pady=5)

        self.preview_canvas = tk.Label(preview_frame, bg="#0d1b2a")
        self.preview_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.preview_canvas.config(text="Live Preview Waiting...", fg=dim_color)

        # ── RIGHT COLUMN ITEMS ──

        # 1. Progress Log
        log_frame = tk.LabelFrame(right_col, text="Execution Logs",
                                   font=("Segoe UI", 10, "bold"),
                                   fg=dim_color, bg=card_bg, bd=1)
        log_frame.pack(fill="both", expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Consolas", 9),
            bg="#0d1b2a", fg="#64ffda", relief="flat",
            state="disabled"
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # 2. Connection Link (The "Bridge" Link)
        id_frame = tk.LabelFrame(right_col, text="Cloud Connection Link",
                                  font=("Segoe UI", 10, "bold"),
                                  fg=green, bg=card_bg, bd=1)
        id_frame.pack(fill="x", pady=5)

        tk.Label(id_frame, text="Paste this in your yantrai webapp:", 
                 font=("Segoe UI", 8), fg=dim_color, bg=card_bg).pack(anchor="w", padx=10, pady=(5, 0))

        link_sub_frame = tk.Frame(id_frame, bg=card_bg)
        link_sub_frame.pack(fill="x", padx=10, pady=5)

        self.link_var = tk.StringVar(value="Waiting...")
        self.link_entry = tk.Entry(link_sub_frame, textvariable=self.link_var, 
                                    font=("Consolas", 11, "bold"), bg="white", fg="black",
                                    relief="flat", bd=5, state="readonly")
        self.link_entry.pack(side="left", fill="x", expand=True)

        # 3. Message/Status
        footer_frame = tk.Frame(right_col, bg=bg)
        footer_frame.pack(fill="x", pady=5)

        self.status_label = tk.Label(footer_frame, text="✨ Onsite is ready and active.", 
                                     font=("Segoe UI", 9, "bold"), fg=green, bg=bg)
        self.status_label.pack(pady=10)

    def _copy_link(self):
        """Copy the connection link to clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.link_var.get())
        messagebox.showinfo("Copied", "Connection link copied to clipboard!")

    def set_connection_link(self, link: str):
        """Update the connection link display."""
        def _update():
            self.link_var.set(link)
        self.root.after(0, _update)

    def update_preview(self, pil_image):
        """Update the live preview frame."""
        def _update():
            # Use stable width from the container to avoid feedback loops
            target_w = self.preview_canvas.master.winfo_width() - 20
            if target_w < 100: target_w = 480
            
            h = int(target_w * 0.5625) # 16:9
            img = pil_image.resize((target_w, h), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(image=img)
            self.preview_canvas.config(image=tk_img)
            self.preview_canvas.image = tk_img
        self.root.after(0, _update)

    def log(self, message: str):
        """Thread-safe logging to the progress area."""
        def _update():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.root.after(0, _update)

    def clear_logs(self):
        """Clear all messages from the log area."""
        def _update():
            self.log_text.config(state="normal")
            self.log_text.delete('1.0', tk.END)
            self.log_text.config(state="disabled")
        self.root.after(0, _update)

    def set_button_state(self, enabled: bool):
        # Button removed, but we can update status label instead
        def _update():
            if not enabled:
                self.status_label.config(text="⚙️ Syncing...", fg="#fbbf24")
            else:
                self.status_label.config(text="✨ Onsite is ready and active.", fg="#64ffda")
        self.root.after(0, _update)

    def _select_source(self, choice):
        """Toggle between CCTV and Device Camera."""
        self.source_choice.set(choice)
        accent = "#0f3460"
        inactive = "#334155"
        if choice == "cctv":
            self.btn_cctv.config(bg=accent)
            self.btn_device.config(bg=inactive)
            self.cred_frame.pack(fill="x", padx=10, pady=(0, 8))
        else:
            self.btn_device.config(bg=accent)
            self.btn_cctv.config(bg=inactive)
            self.cred_frame.pack_forget()  # Hide credentials for device cam
        
        # Auto-trigger restart
        self._on_start_click()

    def _on_start_click(self):
        if self.on_start:
            self.clear_logs()
            # Set manual_url based on source choice
            manual_url = "0" if self.source_choice.get() == "device" else ""
            config = {
                "server_url": self.server_entry.get(),
                "site_name": self.site_entry.get(),
                "username": self.user_entry.get(),
                "password": self.pass_entry.get(),
                "tunnel_method": self.tunnel_method.get(),
                "manual_url": manual_url
            }
            self._save_config(config)
            self.set_button_state(False)
            self.on_start(**config)

    def _on_startup_toggle(self):
        """Enable or disable Windows startup entry."""
        if not winreg:
            print("winreg not available (non-Windows system)")
            return
            
        app_name = "YantrAI_Onsite"
        # Get path to Python executable and this script
        # When converted to single-exe, sys.executable is the exe path.
        if getattr(sys, 'frozen', False):
            # Running as bundled .exe
            app_path = f'"{sys.executable}" --silent'
        else:
            # Running as script
            script_path = os.path.abspath(sys.argv[0])
            app_path = f'"{sys.executable}" "{script_path}" --silent'

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if self.startup_var.get():
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
                print(f"Startup enabled: {app_path}")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    print("Startup disabled.")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Error updating startup registry: {e}")

    def _create_pill(self, parent, text, color):
        pill = tk.Label(parent, text=text.upper(), font=("Segoe UI", 7, "bold"),
                        fg="white", bg=color, padx=8, pady=2, bd=0)
        pill.pack(side="left", padx=(0, 5))
        return pill

    def set_status(self, component, active: bool):
        """Update status pill color."""
        def _update():
            color = "#059669" if active else "#dc2626"
            if component == "camera": self.pill_cam.config(bg=color)
            elif component == "bridge": self.pill_bridge.config(bg=color)
            elif component == "cloud": self.pill_cloud.config(bg=color)
        self.root.after(0, _update)

    def _save_config(self, config):
        config["startup_enabled"] = self.startup_var.get()
        try:
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return None

    def populate_config(self):
        config = self._load_config()
        if config:
            self.server_entry.delete(0, tk.END)
            self.server_entry.insert(0, config.get("server_url", ""))
            self.site_entry.delete(0, tk.END)
            self.site_entry.insert(0, config.get("site_name", ""))
            self.user_entry.delete(0, tk.END)
            self.user_entry.insert(0, config.get("username", ""))
            self.pass_entry.delete(0, tk.END)
            self.pass_entry.insert(0, config.get("password", ""))
            self.tunnel_method.set(config.get("tunnel_method", "upnp"))
            self.manual_url_entry.delete(0, tk.END)
            self.manual_url_entry.insert(0, config.get("manual_url", ""))
            self.startup_var.set(config.get("startup_enabled", False))

    def run(self):
        self.populate_config()
        # If launched with --silent, we might want to start hidden
        if "--silent" in sys.argv:
            self.root.withdraw()
        self.root.mainloop()

    def _setup_tray(self):
        """Build the system tray icon."""
        image = self._create_placeholder_icon()
        menu = pystray.Menu(
            item('Restore', self._restore_window),
            item('Exit', self._quit_app)
        )
        self.tray_icon = pystray.Icon("YantrAI Onsite", image, "YantrAI Onsite", menu)
        
        # Start tray in a separate thread so it doesn't block Tkinter
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _create_placeholder_icon(self):
        """Create a simple Y icon if no ico file exists."""
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='#0f3460')
        dc = ImageDraw.Draw(image)
        # Draw a simple white Y
        dc.line((16, 16, 32, 32), fill="#64ffda", width=4)
        dc.line((48, 16, 32, 32), fill="#64ffda", width=4)
        dc.line((32, 32, 32, 48), fill="#64ffda", width=4)
        return image

    def _restore_window(self):
        self.root.after(0, self.root.deiconify)

    def _on_close(self):
        """Minimize to tray instead of quitting."""
        self.root.withdraw()

    def _quit_app(self):
        """Fully exit the application."""
        if self.on_exit:
            self.on_exit()
            
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)
        sys.exit(0)
