#!/usr/bin/env python3
"""
SUDO_ASKPASS helper for YaP Metasploit GUI.
This script is called by sudo when a password is needed.
"""
import sys
import os
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

def get_password():
    """Show password dialog and return password."""
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

