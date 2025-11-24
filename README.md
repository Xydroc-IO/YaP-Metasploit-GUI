<div align="center">

![YaP Metasploit GUI](icon.png)

# YaP Metasploit GUI

A modern, cross-platform desktop application to automate and simplify using the Metasploit Framework. Features an integrated console, exploit search, payload generation, session management, database integration, and much more.

</div>

## Features

### Core Functionality

- **Integrated Metasploit Console**: Full-featured console tab with command input, output display, and quick command buttons
- **Quick Start Wizard**: Beginner-friendly wizard to guide you through common Metasploit tasks
- **Exploit Search**: Search and browse available exploits with detailed information
- **Exploit Builder**: Visual exploit configuration wizard with option management
- **Payload Generator**: Generate payloads with a user-friendly interface, encoding options, and FUD settings
- **Auxiliary Modules**: Search and use auxiliary modules for reconnaissance and information gathering
- **Handler Setup**: Configure and manage Metasploit handlers for payload connections
- **Session Manager**: Manage active Metasploit sessions with interaction capabilities
- **Meterpreter Manager**: Advanced Meterpreter session management with command execution
- **Post-Exploitation**: Comprehensive post-exploitation tools and modules
- **Database Manager**: Full database integration with workspace management, hosts, services, vulnerabilities, and loot tracking
- **Credential Manager**: Manage and organize discovered credentials
- **Resource Scripts**: Create, edit, and execute Metasploit resource scripts
- **Network Mapper**: Network scanning and mapping capabilities
- **Vulnerability Scanner**: Automated vulnerability scanning with multiple scan types
- **Logs & History**: View command history and activity logs
- **Report Generator**: Generate comprehensive reports from database data
- **Multi-Session Runner**: Execute commands across multiple sessions simultaneously
- **Workflow Automation**: Create and execute automated workflows for complex tasks
- **Session Groups**: Organize sessions into groups for better management
- **Quick Actions Hub**: One-click access to common reconnaissance and post-exploitation actions
- **Settings**: Customize application behavior, themes, and preferences
- **Sudo Password Management**: Securely store and automatically use sudo password for scans and operations requiring elevated privileges
- **Commands & Help**: Built-in command reference and help documentation

### User Interface

- **Modern Tabbed Interface**: Clean, organized interface with 22+ specialized tabs
- **Optimized Layout**: All content fits without resizing (1600x950 default window size)
- **System Tray Integration**: Minimize to system tray (Linux) for background operation
- **Syntax Highlighting**: Color-coded console output for better readability
- **Cross-Platform**: Works on Linux, Windows, and macOS
- **AppImage Support**: Full icon and logo display support in AppImage builds
- **Secure Password Storage**: Encrypted sudo password storage for seamless elevated privilege operations

## Requirements

- **Python**: 3.7 or higher
- **Metasploit Framework**: Installed and accessible via `msfconsole` command
- **PostgreSQL**: Required for database functionality (automatically installed by dependency script)
- **Operating System**: Linux, Windows, or macOS

### System Requirements

- Python Tkinter support
- Metasploit Framework (for full functionality)
- PostgreSQL (for database features)
- Desktop environment with system tray support (for Linux system tray feature)

## Installation

### Linux Installation

#### Automatic Installation (Recommended)

The easiest way to install all dependencies:

```bash
./installers/install-dependencies.sh
```

This script will:
- Detect your Linux distribution automatically
- Install all required system packages (Python, Tkinter, PIL/Pillow)
- Install PostgreSQL and configure it for Metasploit (with automatic initialization)
- Install desktop environment dependencies for system tray support (XFCE, Cinnamon, GNOME, KDE, MATE, etc.)
- Install Python dependencies via pip (automatically uses `--break-system-packages` flag when needed for Python 3.11+)
- Check for Metasploit Framework
- Verify PostgreSQL installation and status
- Automatically start and enable PostgreSQL service

**Supported Linux Distributions:**
- Debian/Ubuntu/Mint/Pop!_OS/Elementary OS (apt)
- Fedora/RHEL/CentOS (dnf/yum)
- Arch/Manjaro/EndeavourOS/Garuda (pacman) - Full PostgreSQL initialization support
- openSUSE/SLE (zypper)
- Alpine Linux (apk)
- Solus (eopkg)
- Gentoo (emerge)

**Desktop Environment Support:**
- XFCE (full support with appindicator and GTK3)
- Cinnamon (full support with appindicator and GTK3)
- GNOME (full support)
- KDE (full support)
- MATE (full support)
- All GTK-based desktop environments

**Advanced Features:**
- Automatically detects Python 3.11+ and uses `--break-system-packages` flag for pip
- Comprehensive error handling with multiple fallback methods
- Automatic PostgreSQL database initialization for Arch/Manjaro
- Cross-distribution compatibility with intelligent package detection

#### Manual Installation (Linux)

1. Install system dependencies:
   - **Debian/Ubuntu**: 
     ```bash
     sudo apt install python3 python3-pip python3-tk python3-pil python3-dev postgresql postgresql-contrib libpq-dev
     ```
   - **Fedora**: 
     ```bash
     sudo dnf install python3 python3-pip python3-tkinter python3-pillow python3-devel postgresql postgresql-server libpq-devel
     ```
   - **Arch/Manjaro**: 
     ```bash
     sudo pacman -S python python-pip tk python-pillow postgresql postgresql-libs libpqxx
     ```

2. Install Metasploit Framework:
   - **Debian/Ubuntu**: 
     ```bash
     sudo apt install metasploit-framework
     ```
   - **Arch**: Install from AUR or download from Rapid7
   - **Other**: Visit https://www.metasploit.com/

3. Initialize PostgreSQL (if not done automatically):
   ```bash
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

4. Install Python packages:
   ```bash
   # For Python 3.11+ on systems with externally-managed environments (Arch, Manjaro, etc.):
   pip install --break-system-packages -r requirements.txt
   
   # For older Python versions or systems without externally-managed environments:
   pip install -r requirements.txt
   ```

5. Initialize Metasploit database:
   ```bash
   msfdb init
   ```

## Usage

**Recommended**: Use the launcher script (automatically checks dependencies):
```bash
./launchers/start-metasploit-gui.sh
```

Or run directly:
```bash
python3 core/metasploit_gui.py
```

### Application Features

#### 1. Quick Start Wizard

Beginner-friendly wizard that guides you through common tasks:
- Generate a Payload
- Set Up a Listener
- Search for Exploits
- Scan for Vulnerabilities
- Manage Sessions
- Post-Exploitation Tasks

#### 2. Metasploit Console Tab

- **Start Console**: Click "Start Console" to launch the integrated Metasploit console
- **Command Input**: Type commands in the input field and press Enter or click "Send"
- **Quick Commands**: Use quick command buttons for common operations (help, version, show exploits, show payloads, show auxiliaries)
- **Clear Output**: Click "Clear" to clear the console output
- **Stop Console**: Click "Stop Console" to terminate the Metasploit session
- **Database Management**: Initialize, check status, and configure Metasploit database

#### 3. Exploit Search Tab

- **Search Exploits**: Enter a search query and click "Search" to find exploits
- **Browse Results**: View exploit names, ranks, and descriptions in a sortable table
- **Use Exploit**: Double-click or select and click "Use Exploit" to load an exploit
- **Show Info**: Select an exploit and click "Show Info" to view detailed information
- **Show Options**: View and configure exploit options
- **Auto Setup**: Automatically configure common exploit options

#### 4. Exploit Builder Tab

Visual exploit configuration wizard:
- **Exploit Selection**: Search and select exploits
- **Configuration Wizard**: Visual interface for setting exploit options
- **Options Management**: View and edit all exploit options with descriptions
- **Target Checking**: Verify target compatibility
- **Run Exploit**: Execute exploits with configured options
- **Background Mode**: Run exploits in background

#### 5. Payload Generator Tab

- **Select Payload Type**: Choose from comprehensive list of payload types
- **Configure Options**: Set LHOST, LPORT, output format, and encoding
- **FUD Options**: Configure Fully Undetectable (FUD) settings
- **Encoder Selection**: Choose encoders and set iteration count
- **Bad Characters**: Specify bad characters to avoid
- **Generate**: Click "Generate Payload" to create the payload
- **Save Payload**: Save the generated payload to a file

#### 6. Auxiliary Modules Tab

- **Search Modules**: Search for auxiliary modules by name or description
- **Browse Results**: View available auxiliary modules
- **Use Module**: Double-click or select a module to use it
- **Show Info**: View detailed module information
- **Show Options**: Configure module options

#### 7. Handler Setup Tab

- **Handler Type**: Select handler type (exploit/multi/handler)
- **Payload Selection**: Choose payload for handler
- **Configuration**: Set LHOST, LPORT, and other options
- **Migration Options**: Configure process migration settings
- **Exit Behavior**: Set exit behavior options
- **Start/Stop Handler**: Control handler execution

#### 8. Vulnerability Scanner Tab

- **Target Input**: Enter target IP or hostname
- **Scan Types**: Quick Port Scan, Full Port Scan, Fast Vuln Scan, Vulnerability Scan, Service Enumeration
- **Results Display**: View scan results in organized format
- **Export Results**: Save scan results to file

#### 9. Session Manager Tab

- **Refresh Sessions**: Click "Refresh Sessions" to update the session list
- **Session List**: View all active sessions with details
- **Interact**: Select a session and click "Interact" to interact with it
- **Kill Session**: Select a session and click "Kill Session" to terminate it
- **Upgrade Session**: Upgrade shell sessions to Meterpreter

#### 10. Meterpreter Manager Tab

Advanced Meterpreter session management:
- **Session Selection**: Select active Meterpreter sessions
- **Command Execution**: Execute Meterpreter commands
- **Quick Commands**: Access common Meterpreter commands via buttons
- **File Operations**: Upload and download files
- **Screenshot**: Capture screenshots from target
- **Keylogger**: Start, dump, and stop keyloggers
- **System Information**: Gather system information

#### 11. Post-Exploitation Tab

- **Session Selection**: Select active session for post-exploitation
- **Quick Actions**: One-click access to common post-exploitation tasks:
  - Get System (privilege escalation)
  - Dump Hashes
  - Screenshot
  - Webcam Snap
  - Keylogger (start, dump, stop)
  - Clear Event Logs
- **Post-Exploitation Modules**: Browse and use post-exploitation modules by category:
  - Privilege Escalation
  - Credential Collection
  - Network Pivoting
  - Persistence
  - And more

#### 12. Database Manager Tab

Full database integration with Metasploit:
- **Workspace Management**: Create, switch, and list workspaces
- **Hosts View**: View and manage discovered hosts
- **Services View**: View and manage discovered services
- **Vulnerabilities View**: Track and manage vulnerabilities
- **Loot View**: Manage collected loot and files
- **Data Export**: Export database data to various formats

#### 13. Credential Manager Tab

- **Credential List**: View all discovered credentials
- **Add Credentials**: Manually add credentials
- **Export Credentials**: Export credentials to various formats
- **Search/Filter**: Search and filter credentials

#### 14. Resource Scripts Tab

- **Create Scripts**: Create new Metasploit resource scripts
- **Edit Scripts**: Edit existing resource scripts
- **Execute Scripts**: Run resource scripts in console
- **Script Library**: Manage a library of reusable scripts

#### 15. Network Mapper Tab

- **Network Scanning**: Perform network discovery scans
- **Host Discovery**: Discover hosts on network
- **Service Detection**: Identify services on discovered hosts
- **Topology Mapping**: Visualize network topology

#### 16. Logs & History Tab

- **Command History**: View all executed commands
- **Activity Logs**: View application activity logs
- **Search Logs**: Search through log history
- **Export Logs**: Export logs to file

#### 17. Report Generator Tab

- **Report Templates**: Choose from report templates
- **Data Selection**: Select data to include in report
- **Generate Reports**: Generate comprehensive reports
- **Export Formats**: Export reports in various formats

#### 18. Multi-Session Runner Tab

- **Session Selection**: Select multiple sessions
- **Command Execution**: Execute commands across all selected sessions
- **Batch Operations**: Perform batch operations on multiple sessions
- **Results Aggregation**: View results from all sessions

#### 19. Workflow Automation Tab

- **Workflow Creation**: Create automated workflows
- **Step Management**: Add, edit, and reorder workflow steps
- **Conditional Logic**: Add conditions to workflow steps
- **Workflow Execution**: Execute complete workflows
- **Workflow Library**: Save and reuse workflows

#### 20. Session Groups Tab

- **Group Creation**: Organize sessions into groups
- **Group Management**: Manage session groups
- **Group Operations**: Perform operations on entire groups
- **Group Filtering**: Filter views by group

#### 21. Quick Actions Hub Tab

One-click access to common actions organized by category:
- **Reconnaissance**: Quick Port Scan, Service Enumeration, OS Detection, Vulnerability Scan, DNS Enumeration, SMB Enumeration
- **Post-Exploitation**: Get System, Dump Hashes, Screenshot, Keylogger, File Operations, Persistence, Clear Event Logs
- **Privilege Escalation**: Various privilege escalation techniques
- **Payload Generation**: Quick payload generation with common settings
- **Database Operations**: Quick database queries and operations

#### 22. Settings Tab

- **Theme Selection**: Choose application theme
- **Font Size**: Adjust font size
- **Auto-Save History**: Enable/disable command history auto-save
- **Default Payload**: Set default payload type
- **Default LHOST/LPORT**: Configure default connection settings
- **Auto-Init Database**: Automatically initialize database if not connected
- **Preferred Monitor**: Select preferred monitor for window placement
- **Sudo Password Storage**: Securely store your sudo password for automatic use during scans and operations requiring elevated privileges
  - Password is encrypted before storage
  - Automatically used when sudo is required
  - Can be cleared from settings at any time

#### 23. Commands & Help Tab

- **Command Reference**: Built-in Metasploit command reference
- **Help Documentation**: Access help for various features
- **Version Information**: View application and Metasploit version

## Configuration

### Metasploit Framework Path

The application automatically searches for `msfconsole` in common locations:
- `/usr/bin/msfconsole`
- `/opt/metasploit-framework/msfconsole`
- `/usr/local/bin/msfconsole`
- System PATH

If Metasploit is installed in a non-standard location, ensure it's in your PATH or create a symlink.

### Database Configuration

The application uses PostgreSQL for Metasploit database functionality. The dependency installer will:
- Install PostgreSQL (including all required packages)
- Initialize PostgreSQL database (on Arch/Manjaro and other distributions)
- Start PostgreSQL service
- Enable PostgreSQL on boot

You still need to initialize the Metasploit database:
```bash
msfdb init
```

### Sudo Password Storage

For operations requiring elevated privileges (scans, database operations, etc.), you can store your sudo password securely:

1. Go to **Settings** tab
2. Scroll to **Sudo Password Settings** section
3. Enter your sudo password (it will be masked)
4. Click **Save Settings**
5. Your password is encrypted and stored locally
6. The application will automatically use it when sudo is required

**Security Notes:**
- Password is encrypted using a user-specific key before storage
- Password is stored in `~/.yap_metasploit_gui_settings.json`
- You can clear the stored password at any time from Settings
- The password is only used when explicitly required by operations

### Console Settings

The console uses the `-q` (quiet) flag to reduce startup noise. All commands are sent directly to the Metasploit console.

### Window Size and Layout

The application defaults to 1600x950 window size with optimized layout to fit all content without resizing. The minimum window size is 1400x800.

## Troubleshooting

### Metasploit Not Found

If you see "msfconsole not found":
1. Ensure Metasploit Framework is installed
2. Verify `msfconsole` is in your PATH: `which msfconsole`
3. If installed in a custom location, add it to PATH or create a symlink

### Console Not Starting

If the console fails to start:
1. Check that Metasploit Framework is properly installed
2. Try running `msfconsole` manually from the terminal
3. Check for error messages in the console output tab
4. Verify PostgreSQL is running if using database features

### Database Connection Issues

If database features don't work:
1. Ensure PostgreSQL is installed and running: `sudo systemctl status postgresql`
2. If PostgreSQL is not running, start it:
   ```bash
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```
3. Initialize Metasploit database: `msfdb init`
4. Check database status in the console tab
5. On Arch/Manjaro, if PostgreSQL database needs initialization, the dependency installer handles this automatically

### Missing Dependencies

If you see import errors:
1. Run the dependency installer: `./installers/install-dependencies.sh`
2. Or install manually:
   - For Python 3.11+ on Arch/Manjaro or systems with externally-managed environments:
     ```bash
     pip install --break-system-packages -r requirements.txt
     ```
   - For other systems:
     ```bash
     pip install -r requirements.txt
     ```
3. Ensure system packages are installed (see Manual Installation)

### Pip Installation Errors (Python 3.11+)

If you see "externally-managed-environment" errors:
1. The dependency installer automatically handles this with `--break-system-packages` flag
2. If installing manually, use: `pip install --break-system-packages -r requirements.txt`
3. This is normal for newer Python installations on Arch, Manjaro, and other modern distributions

### Payload Generation Fails

If payload generation fails:
1. Ensure `msfvenom` is available (comes with Metasploit Framework)
2. Check that all required options are filled in
3. Verify the payload type is valid
4. Check console output for error messages

### System Tray Not Working (Linux)

If the system tray icon doesn't appear:
1. Ensure `pystray` is installed: `pip install pystray`
2. Install desktop environment dependencies (run dependency installer)
3. Some desktop environments may require additional packages
4. Try restarting the application

### Window Layout Issues

If content doesn't fit properly:
1. The default window size is 1600x950 - ensure your screen resolution supports this
2. Minimum window size is 1400x800
3. All content should fit without resizing at default size
4. If issues persist, check your desktop environment's scaling settings

## Project Structure

```
YaP-Metasploit-GUI/
├── core/
│   ├── metasploit_gui.py      # Main application and GUI
│   └── sudo_askpass.py        # Sudo password helper
├── installers/
│   └── install-dependencies.sh # Comprehensive dependency installer
├── launchers/
│   └── start-metasploit-gui.sh  # Launcher script
├── requirements.txt            # Python dependencies
├── icon.png                    # Application icon
├── yapmetasploitgui250.png     # Logo image
├── LICENSE                     # License file
└── README.md                   # This file
```

## Dependencies

### Python Packages

- **Pillow** (>=9.0.0): Image processing for icons and logos
- **pystray** (>=0.19.0): System tray support (Linux)
- **PyYAML** (>=6.0.0): YAML parsing for database configuration files

### System Packages

- Python 3.7+ with Tkinter
- Metasploit Framework
- PostgreSQL (for database features)
- Desktop environment packages (for system tray support on Linux)

## AppImage Support

YaP Metasploit GUI can be built as a portable AppImage for easy distribution and use across Linux distributions.

### Building AppImage

To build an AppImage, use the build script:
```bash
cd "/path/to/YaP Labs Releases/Metasploit GUI"
./build-appimage.sh
```

The AppImage includes:
- Full icon and logo display support
- All dependencies bundled
- Cross-distribution compatibility (Arch, Manjaro, Ubuntu, Fedora, etc.)
- Desktop environment support (XFCE, Cinnamon, GNOME, KDE, etc.)

### Using AppImage

1. Download or build the AppImage
2. Make it executable: `chmod +x YaP-Metasploit-GUI-x86_64.AppImage`
3. Run it: `./YaP-Metasploit-GUI-x86_64.AppImage`

The AppImage is self-contained and doesn't require installation. It works on all major Linux distributions.

## Development

### Running from Source

1. Clone or download the repository
2. Install dependencies (see Installation section):
   ```bash
   ./installers/install-dependencies.sh
   ```
3. Initialize Metasploit database:
   ```bash
   msfdb init
   ```
4. Run using the launcher script:
   ```bash
   ./launchers/start-metasploit-gui.sh
   ```
   Or run directly:
   ```bash
   python3 core/metasploit_gui.py
   ```

## Recent Updates

### Version Improvements

- **Sudo Password Storage**: Securely store and automatically use sudo password for operations requiring elevated privileges
- **Enhanced Dependency Installer**: 
  - Automatic PostgreSQL installation and initialization for all distributions
  - Support for `--break-system-packages` flag for Python 3.11+ systems
  - Comprehensive desktop environment support (XFCE, Cinnamon, GNOME, KDE, MATE)
  - Improved error handling and fallback methods
- **AppImage Improvements**: 
  - Full icon and logo display support in AppImage builds
  - Enhanced path detection for resources
  - Better cross-distribution compatibility

## Security Notice

**Important**: This tool is designed for authorized security testing and educational purposes only. Only use Metasploit Framework and this GUI on systems you own or have explicit written permission to test. Unauthorized access to computer systems is illegal.

**Password Storage Security**: Stored sudo passwords are encrypted using a user-specific key. However, as with any stored credentials, use this feature responsibly and only on trusted systems.



**Note**: This application requires Metasploit Framework to be installed. Ensure you have proper authorization before using this tool for security testing.
