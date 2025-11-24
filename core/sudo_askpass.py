#!/usr/bin/env python3
"""
SUDO_ASKPASS helper for YaP Metasploit GUI.
This script is called by sudo when a password is needed.
"""
import sys
import os

# CRITICAL: Try to get and output saved password FIRST, before any other imports
# This ensures we can return the password even if GUI libraries fail to load
try:
    import json
    import base64
    import hashlib
    
    def get_original_user_home():
        """Get the original user's home directory (not root's when running via sudo)."""
        sudo_user = os.environ.get('SUDO_USER')
        original_home = os.environ.get('YAP_ORIGINAL_HOME')
        if original_home and os.path.exists(original_home):
            return original_home
        if sudo_user:
            try:
                import pwd
                return pwd.getpwnam(sudo_user).pw_dir
            except:
                home_path = os.path.join('/home', sudo_user)
                if os.path.exists(home_path):
                    return home_path
        return os.path.expanduser("~")
    
    def decrypt_password(encrypted_password, user_home):
        """Decrypt password from stored encrypted value."""
        if not encrypted_password:
            return None
        try:
            encrypted_bytes = base64.b64decode(encrypted_password.encode())
            key = hashlib.sha256(user_home.encode()).hexdigest()[:32]
            key_bytes = key.encode()
            decrypted = bytearray()
            for i, byte in enumerate(encrypted_bytes):
                decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
            return decrypted.decode()
        except:
            return None
    
    # Try to get saved password immediately
    user_home = get_original_user_home()
    settings_file = os.path.join(user_home, ".yap_metasploit_gui_settings.json")
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                encrypted_password = settings.get('sudo_password_encrypted')
                if encrypted_password:
                    password = decrypt_password(encrypted_password, user_home)
                    if password:
                        # Output password immediately - no newline, no extra bytes
                        # CRITICAL: This must be the ONLY place password is output
                        # Strip any whitespace just to be safe
                        password_clean = password.rstrip('\n\r\t ')
                        
                        # Write password using binary mode to ensure exact bytes
                        # Sudo reads from stdin, so we need to write to stdout exactly
                        if hasattr(sys.stdout, 'buffer'):
                            # Python 3 - use buffer for exact byte control
                            sys.stdout.buffer.write(password_clean.encode('utf-8'))
                            sys.stdout.buffer.flush()
                        else:
                            # Fallback for older Python
                            sys.stdout.write(password_clean)
                            sys.stdout.flush()
                        
                        # Close stderr to avoid interfering
                        try:
                            sys.stderr.close()
                            sys.stderr = open(os.devnull, 'w')
                        except:
                            pass
                        # Exit immediately - do not continue to get_password()
                        sys.exit(0)
        except Exception as e:
            # Log error to a file we can check
            try:
                error_log = os.path.join(user_home, ".yap_askpass_error.log")
                with open(error_log, 'a') as f:
                    import datetime
                    f.write(f"{datetime.datetime.now()}: Early section error: {str(e)}\n")
                    f.flush()
            except:
                pass
            # If there's an error, continue to GUI dialog
            pass
except Exception as e:
    # Log error
    try:
        error_log = os.path.expanduser("~/.yap_askpass_error.log")
        with open(error_log, 'a') as f:
            import datetime
            f.write(f"{datetime.datetime.now()}: Early section import error: {str(e)}\n")
            f.flush()
    except:
        pass
    # If there's an error in the early section, continue to GUI dialog
    pass

# If we get here, no saved password was found or there was an error
# Continue with the rest of the script to show GUI dialog
import subprocess
import re

# Redirect stderr to avoid interfering with sudo's password reading
# Sudo expects askpass to only output the password to stdout
# But keep stderr open for now - we'll close it after logging
stderr_save = sys.stderr

def find_main_window_position():
    """Try to find the main YaP Metasploit GUI window and get its position."""
    # First, try to get position from environment variable (most reliable)
    try:
        if 'YAP_GUI_X' in os.environ and 'YAP_GUI_Y' in os.environ:
            x = int(os.environ['YAP_GUI_X'])
            y = int(os.environ['YAP_GUI_Y'])
            # Validate that the position is reasonable
            if -10000 < x < 10000 and -10000 < y < 10000:
                return x, y
    except (ValueError, KeyError):
        pass
    
    # Fallback: try using xdotool to find the window
    try:
        result = subprocess.run(
            ['xdotool', 'search', '--name', 'YaP Metasploit GUI'],
            capture_output=True,
            text=True,
            timeout=1,
            stderr=subprocess.DEVNULL
        )
        if result.returncode == 0 and result.stdout.strip():
            window_id = result.stdout.strip().split('\n')[0]
            # Get window position
            pos_result = subprocess.run(
                ['xdotool', 'getwindowgeometry', window_id],
                capture_output=True,
                text=True,
                timeout=1,
                stderr=subprocess.DEVNULL
            )
            if pos_result.returncode == 0:
                # Parse position from output (format: "Position: 100,200")
                for line in pos_result.stdout.split('\n'):
                    if 'Position:' in line:
                        try:
                            pos_str = line.split('Position:')[1].strip()
                            x, y = map(int, pos_str.split(','))
                            if -10000 < x < 10000 and -10000 < y < 10000:
                                return x, y
                        except (ValueError, IndexError):
                            pass
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        # xdotool not available or failed - that's okay, we'll use environment vars
        pass
    
    return None, None

def get_original_user_home():
    """Get the original user's home directory (not root's when running via sudo)."""
    # When sudo runs this script, SUDO_USER contains the original username
    sudo_user = os.environ.get('SUDO_USER')
    
    # Also check for explicitly passed home directory
    original_home = os.environ.get('YAP_ORIGINAL_HOME')
    if original_home and os.path.exists(original_home):
        return original_home
    
    if sudo_user:
        try:
            import pwd
            user_info = pwd.getpwnam(sudo_user)
            return user_info.pw_dir
        except (KeyError, ImportError):
            # Fallback: construct home path
            home_path = os.path.join('/home', sudo_user)
            if os.path.exists(home_path):
                return home_path
    
    # If not running via sudo, use current user's home
    current_home = os.path.expanduser("~")
    # But if we're root and ~ is /root, try to find the actual user
    if current_home == '/root' and not sudo_user:
        # Try to get from environment or fallback to common locations
        for env_var in ['HOME', 'YAP_ORIGINAL_HOME']:
            if env_var in os.environ:
                potential_home = os.environ[env_var]
                if os.path.exists(potential_home) and potential_home != '/root':
                    return potential_home
    
    return current_home

def decrypt_password(encrypted_password, user_home=None):
    """Decrypt password from stored encrypted value."""
    if not encrypted_password:
        return None
    try:
        # Get the original user's home directory for key generation
        if user_home is None:
            user_home = get_original_user_home()
        
        # Decode from base64
        encrypted_bytes = base64.b64decode(encrypted_password.encode())
        # Create the same key (based on original user's home directory)
        key = hashlib.sha256(user_home.encode()).hexdigest()[:32]
        key_bytes = key.encode()
        # XOR decryption
        decrypted = bytearray()
        for i, byte in enumerate(encrypted_bytes):
            decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        return decrypted.decode()
    except Exception:
        return None

def get_saved_password():
    """Try to get saved password from settings file."""
    user_home = None
    debug_log_path = None
    try:
        # Get original user's home directory (important when running as root via sudo)
        user_home = get_original_user_home()
        settings_file = os.path.join(user_home, ".yap_metasploit_gui_settings.json")
        debug_log_path = os.path.join(user_home, ".yap_askpass_debug.log")
        
        # Log attempt
        try:
            with open(debug_log_path, 'a') as f:
                import datetime
                f.write(f"{datetime.datetime.now()}: Attempting to get saved password\n")
                f.write(f"  SUDO_USER={os.environ.get('SUDO_USER', 'NOT SET')}\n")
                f.write(f"  YAP_ORIGINAL_USER={os.environ.get('YAP_ORIGINAL_USER', 'NOT SET')}\n")
                f.write(f"  YAP_ORIGINAL_HOME={os.environ.get('YAP_ORIGINAL_HOME', 'NOT SET')}\n")
                f.write(f"  user_home={user_home}\n")
                f.write(f"  settings_file={settings_file}\n")
                f.write(f"  settings_file_exists={os.path.exists(settings_file)}\n")
                f.flush()
        except:
            pass
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                encrypted_password = settings.get('sudo_password_encrypted')
                
                # Log what we found
                try:
                    with open(debug_log_path, 'a') as f:
                        import datetime
                        f.write(f"{datetime.datetime.now()}: Settings file read\n")
                        f.write(f"  has_encrypted_password={bool(encrypted_password)}\n")
                        f.write(f"  encrypted_length={len(encrypted_password) if encrypted_password else 0}\n")
                        f.flush()
                except:
                    pass
                
                if encrypted_password:
                    decrypted = decrypt_password(encrypted_password, user_home)
                    
                    # Log decryption result
                    try:
                        with open(debug_log_path, 'a') as f:
                            import datetime
                            f.write(f"{datetime.datetime.now()}: Decryption attempted\n")
                            f.write(f"  decrypted_success={bool(decrypted)}\n")
                            f.write(f"  decrypted_length={len(decrypted) if decrypted else 0}\n")
                            f.flush()
                    except:
                        pass
                    
                    return decrypted
                else:
                    try:
                        with open(debug_log_path, 'a') as f:
                            import datetime
                            f.write(f"{datetime.datetime.now()}: No encrypted password in settings\n")
                            f.flush()
                    except:
                        pass
        else:
            try:
                with open(debug_log_path, 'a') as f:
                    import datetime
                    f.write(f"{datetime.datetime.now()}: Settings file not found at {settings_file}\n")
                    f.flush()
            except:
                pass
    except Exception as e:
        # Debug: Log error if possible
        try:
            if debug_log_path is None:
                if user_home is None:
                    user_home = get_original_user_home()
                debug_log_path = os.path.join(user_home, ".yap_askpass_debug.log")
            with open(debug_log_path, 'a') as f:
                import datetime
                import traceback
                f.write(f"{datetime.datetime.now()}: Error getting saved password: {str(e)}\n")
                f.write(f"  Traceback: {traceback.format_exc()}\n")
                f.write(f"  SUDO_USER={os.environ.get('SUDO_USER', 'NOT SET')}\n")
                f.write(f"  user_home={user_home if user_home else 'NOT SET'}\n")
                f.write(f"  settings_file={os.path.join(user_home, '.yap_metasploit_gui_settings.json') if user_home else 'NOT SET'}\n")
                f.flush()
        except:
            pass
    return None

def get_password():
    """Show password dialog and return password.
    
    NOTE: This function should only be called if the early password retrieval
    at the top of the file didn't work. The early section should exit immediately
    if a password is found, so this function should only run for GUI dialog fallback.
    """
    user_home = None
    debug_log_path = None
    
    # Try to get saved password (fallback if early section didn't work)
    saved_password = None
    try:
        user_home = get_original_user_home()
        debug_log_path = os.path.join(user_home, ".yap_askpass_debug.log")
        
        # Log that script was called (this should rarely happen if early section worked)
        try:
            with open(debug_log_path, 'a') as f:
                import datetime
                f.write(f"{datetime.datetime.now()}: ===== get_password() called (fallback) =====\n")
                f.write(f"  SUDO_USER={os.environ.get('SUDO_USER', 'NOT SET')}\n")
                f.write(f"  YAP_ORIGINAL_USER={os.environ.get('YAP_ORIGINAL_USER', 'NOT SET')}\n")
                f.write(f"  YAP_ORIGINAL_HOME={os.environ.get('YAP_ORIGINAL_HOME', 'NOT SET')}\n")
                f.write(f"  USER={os.environ.get('USER', 'NOT SET')}\n")
                f.write(f"  HOME={os.environ.get('HOME', 'NOT SET')}\n")
                f.write(f"  user_home={user_home}\n")
                f.flush()
        except:
            pass
        
        # Try to get saved password
        saved_password = get_saved_password()
    except Exception as e:
        # If we can't get user home or password, log it but continue
        try:
            if debug_log_path:
                with open(debug_log_path, 'a') as f:
                    import datetime
                    f.write(f"{datetime.datetime.now()}: Error in get_password setup: {str(e)}\n")
                    f.flush()
        except:
            pass
    
    if saved_password:
        # Debug: Log that we're using saved password
        try:
            if debug_log_path is None:
                if user_home is None:
                    user_home = get_original_user_home()
                debug_log_path = os.path.join(user_home, ".yap_askpass_debug.log")
            with open(debug_log_path, 'a') as f:
                import datetime
                f.write(f"{datetime.datetime.now()}: Using saved password from settings\n")
                f.write(f"  password_length={len(saved_password)}\n")
                f.write(f"  password_preview={'*' * min(len(saved_password), 10)}\n")
                f.flush()
        except:
            pass
        
        # Return saved password directly
        try:
            # CRITICAL: Output ONLY the password, no newline, no extra bytes
            # Sudo expects exactly the password with no trailing newline
            # Strip any potential whitespace that might have been added
            password_to_send = saved_password.rstrip('\n\r\t ')
            
            # Log exactly what we're sending (for debugging)
            try:
                if debug_log_path is None:
                    if user_home is None:
                        user_home = get_original_user_home()
                    debug_log_path = os.path.join(user_home, ".yap_askpass_debug.log")
                with open(debug_log_path, 'a') as f:
                    import datetime
                    f.write(f"{datetime.datetime.now()}: About to send password to stdout\n")
                    f.write(f"  password_length={len(password_to_send)}\n")
                    f.write(f"  password_bytes={password_to_send.encode('utf-8')}\n")
                    f.write(f"  password_repr={repr(password_to_send)}\n")
                    f.flush()
            except:
                pass
            
            # Write password to stdout - must be exact text, no newline
            # Use text mode (not buffer) as sudo expects text from askpass
            sys.stdout.write(password_to_send)
            sys.stdout.flush()
            
            # Log that we sent the password
            try:
                if debug_log_path is None:
                    if user_home is None:
                        user_home = get_original_user_home()
                    debug_log_path = os.path.join(user_home, ".yap_askpass_debug.log")
                with open(debug_log_path, 'a') as f:
                    import datetime
                    f.write(f"{datetime.datetime.now()}: Password sent to stdout\n")
                    f.flush()
            except:
                pass
            
            try:
                sys.stderr.close()
                sys.stderr = open(os.devnull, 'w')
            except:
                pass
            return 0
        except (IOError, OSError) as e:
            # If stdout write fails, log and fall through to dialog
            try:
                if debug_log_path is None:
                    if user_home is None:
                        user_home = get_original_user_home()
                    debug_log_path = os.path.join(user_home, ".yap_askpass_debug.log")
                with open(debug_log_path, 'a') as f:
                    import datetime
                    f.write(f"{datetime.datetime.now()}: Error writing password to stdout: {str(e)}\n")
                    f.flush()
            except:
                pass
    else:
        # Log that no saved password was found
        try:
            if debug_log_path is None:
                if user_home is None:
                    user_home = get_original_user_home()
                debug_log_path = os.path.join(user_home, ".yap_askpass_debug.log")
            with open(debug_log_path, 'a') as f:
                import datetime
                f.write(f"{datetime.datetime.now()}: No saved password found, will show dialog\n")
                f.flush()
        except:
            pass
    
    # No saved password or it failed - show dialog
    try:
        # Ensure DISPLAY is set (needed for GUI on Linux)
        # When called by sudo, we need to preserve the original user's DISPLAY
        if 'DISPLAY' not in os.environ:
            # Try to get DISPLAY from the original user's environment
            # Sudo preserves some environment variables, but not DISPLAY by default
            # Try common locations
            display = None
            sudo_user = os.environ.get('SUDO_USER')
            if sudo_user:
                # Try to get DISPLAY from the original user's environment
                try:
                    import pwd
                    user_info = pwd.getpwnam(sudo_user)
                    xauth_file = os.path.join(user_info.pw_dir, '.Xauthority')
                    if os.path.exists(xauth_file):
                        os.environ['XAUTHORITY'] = xauth_file
                except:
                    pass
            
            # Default to :0 if not set
            if not display:
                display = ':0'
            os.environ['DISPLAY'] = display
        
        # Debug: Write to a log file to see if script is being called
        debug_log = None
        try:
            debug_log = os.path.expanduser("~/.yap_askpass_debug.log")
            with open(debug_log, 'a') as f:
                import datetime
                f.write(f"{datetime.datetime.now()}: askpass script called\n")
                f.write(f"DISPLAY={os.environ.get('DISPLAY', 'NOT SET')}\n")
                f.write(f"USER={os.environ.get('USER', 'NOT SET')}\n")
                f.write(f"SUDO_USER={os.environ.get('SUDO_USER', 'NOT SET')}\n")
                f.flush()
        except Exception as e:
            # Can't write to log, that's okay
            pass
        
        import tkinter as tk
        from tkinter import simpledialog
        
        # Create a root window (hidden) with timeout protection
        root = None
        password = None
        
        try:
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            
            # Set a timeout to prevent hanging
            def timeout_handler():
                nonlocal password
                if password is None:
                    password = ""  # Empty string to indicate timeout
                    if root:
                        root.quit()
            
            # Set timeout for dialog (30 seconds)
            root.after(30000, timeout_handler)
            
            # Make sure it appears on top and is visible
            root.attributes('-topmost', True)  # Bring to front
            try:
                root.attributes('-type', 'dialog')  # Make it a dialog window (may not work on all systems)
            except:
                pass
            root.lift()  # Bring to front
            root.focus_force()  # Force focus
            
            # Update to ensure window is ready
            root.update_idletasks()
            root.update()
            
            # Position dialog on preferred monitor
            root.update_idletasks()
            
            # Get preferred monitor from environment (set by main GUI)
            preferred_monitor = os.environ.get('YAP_PREFERRED_MONITOR', 'primary')
            
            try:
                # Try to get monitor info using xrandr
                result = subprocess.run(
                    ['xrandr', '--query'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0:
                    monitor_found = False
                    
                    # If preferred_monitor is 'primary', find primary monitor
                    if preferred_monitor == 'primary':
                        for line in result.stdout.split('\n'):
                            if ' connected' in line and 'primary' in line.lower():
                                res_match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
                                if res_match:
                                    width = int(res_match.group(1))
                                    height = int(res_match.group(2))
                                    offset_x = int(res_match.group(3))
                                    offset_y = int(res_match.group(4))
                                    
                                    window_width = 400
                                    window_height = 150
                                    x = offset_x + (width // 2) - (window_width // 2)
                                    y = offset_y + (height // 2) - (window_height // 2)
                                    root.geometry(f"+{x}+{y}")
                                    monitor_found = True
                                    break
                    
                    # If not primary or primary not found, try to find by name
                    if not monitor_found:
                        for line in result.stdout.split('\n'):
                            if ' connected' in line and preferred_monitor in line:
                                res_match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
                                if res_match:
                                    width = int(res_match.group(1))
                                    height = int(res_match.group(2))
                                    offset_x = int(res_match.group(3))
                                    offset_y = int(res_match.group(4))
                                    
                                    window_width = 400
                                    window_height = 150
                                    x = offset_x + (width // 2) - (window_width // 2)
                                    y = offset_y + (height // 2) - (window_height // 2)
                                    root.geometry(f"+{x}+{y}")
                                    monitor_found = True
                                    break
                    
                    # Fallback to primary if specific monitor not found
                    if not monitor_found:
                        for line in result.stdout.split('\n'):
                            if ' connected' in line:
                                res_match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
                                if res_match:
                                    width = int(res_match.group(1))
                                    height = int(res_match.group(2))
                                    offset_x = int(res_match.group(3))
                                    offset_y = int(res_match.group(4))
                                    
                                    window_width = 400
                                    window_height = 150
                                    x = offset_x + (width // 2) - (window_width // 2)
                                    y = offset_y + (height // 2) - (window_height // 2)
                                    root.geometry(f"+{x}+{y}")
                                    break
            except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.SubprocessError):
                # xrandr not available, use tkinter's screen info
                screen_width = root.winfo_screenwidth()
                screen_height = root.winfo_screenheight()
                window_width = 400
                window_height = 150
                x = (screen_width // 2) - (window_width // 2)
                y = (screen_height // 2) - (window_height // 2)
                root.geometry(f"+{x}+{y}")
            
            # Show password dialog - make sure it's visible
            # Bring root to front again before showing dialog
            root.lift()
            root.focus_force()
            root.attributes('-topmost', True)
            root.update_idletasks()
            root.update()
            
            # Show password dialog directly
            try:
                password = simpledialog.askstring(
                    "Password Required",
                    "Administrator password required for Metasploit operations.\n\nEnter your password:",
                    show='*',
                    parent=root
                )
            except Exception as e:
                # If dialog fails, log and set password to empty
                try:
                    if debug_log:
                        with open(debug_log, 'a') as f:
                            import datetime
                            f.write(f"{datetime.datetime.now()}: Dialog error: {str(e)}\n")
                            f.flush()
                except:
                    pass
                password = ""
        
        except Exception as e:
            # If tkinter initialization fails, try fallback method
            try:
                if debug_log:
                    with open(debug_log, 'a') as f:
                        import datetime
                        f.write(f"{datetime.datetime.now()}: Tkinter init error: {str(e)}\n")
                        f.flush()
            except:
                pass
            password = None
        
        finally:
            # Clean up root window
            if root:
                try:
                    root.quit()
                    root.destroy()
                except:
                    pass
        
        # Check if password was provided (not None and not empty)
        if password is not None and password.strip():
            # Debug: Log that we got a password
            try:
                if debug_log:
                    with open(debug_log, 'a') as f:
                        import datetime
                        f.write(f"{datetime.datetime.now()}: Password received (length: {len(password)})\n")
                        f.flush()
            except:
                pass
            
            # Print password to stdout (sudo reads from here)
            # CRITICAL: Must output to stdout without newline, then flush
            # Sudo expects exactly the password with no trailing newline
            try:
                # Don't strip - send password exactly as entered
                # Some passwords might intentionally start or end with spaces
                # Only remove trailing newline if tkinter added one (it shouldn't)
                password_to_send = password.rstrip('\n\r') if password else ''
                
                if not password_to_send:
                    # Empty password - return error
                    if debug_log:
                        try:
                            with open(debug_log, 'a') as f:
                                import datetime
                                f.write(f"{datetime.datetime.now()}: Empty password after processing\n")
                                f.flush()
                        except:
                            pass
                    return 1
                
                # Write password to stdout - sudo reads from here
                # CRITICAL: Output ONLY the password, no newline, no extra bytes
                # Use text mode stdout directly (this is what askpass scripts should use)
                sys.stdout.write(password_to_send)
                sys.stdout.flush()
                
                # Close stderr now that we're done with logging
                try:
                    sys.stderr.close()
                    sys.stderr = open(os.devnull, 'w')
                except:
                    pass
                
                # Debug: Log password was sent (but don't log the actual password for security)
                try:
                    if debug_log:
                        with open(debug_log, 'a') as f:
                            import datetime
                            f.write(f"{datetime.datetime.now()}: Password sent to stdout (length: {len(password_to_send)} chars, {len(password_bytes)} bytes)\n")
                            f.flush()
                except:
                    pass
                
                return 0
            except (IOError, OSError) as e:
                # If stdout is closed or unavailable, return error
                try:
                    if debug_log:
                        with open(debug_log, 'a') as f:
                            import datetime
                            f.write(f"{datetime.datetime.now()}: Error writing password: {str(e)}\n")
                            f.flush()
                except:
                    pass
                return 1
        else:
            # User cancelled or empty password - return error
            # Don't output anything to stdout in this case
            try:
                if debug_log:
                    with open(debug_log, 'a') as f:
                        import datetime
                        f.write(f"{datetime.datetime.now()}: No password provided (user cancelled or empty)\n")
                        f.flush()
            except:
                pass
            return 1
    except Exception as e:
        # If GUI fails, we can't really fall back to stdin for askpass
        # because askpass scripts are expected to be non-interactive
        # Just return error - sudo will handle retrying
        # Don't output anything to stdout on error
        # Debug: Log the error
        try:
            debug_log = os.path.expanduser("~/.yap_askpass_debug.log")
            with open(debug_log, 'a') as f:
                import datetime
                import traceback
                f.write(f"{datetime.datetime.now()}: askpass error: {str(e)}\n")
                f.write(f"Traceback: {traceback.format_exc()}\n")
        except:
            pass
        return 1

if __name__ == '__main__':
    sys.exit(get_password())

