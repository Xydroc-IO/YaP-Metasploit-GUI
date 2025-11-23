<div align="center">

![YaP Metasploit GUI](icon.png)

# YaP Metasploit GUI

A modern, cross-platform desktop application to automate and simplify using the Metasploit Framework. Features an integrated console, exploit search, payload generation, and session management.

</div>

## Features

- **Integrated Metasploit Console**: Full-featured console tab with command input and output
- **Exploit Search**: Search and browse available exploits with quick access
- **Payload Generator**: Generate payloads with a user-friendly interface
- **Auxiliary Modules**: Search and use auxiliary modules
- **Session Manager**: Manage active Metasploit sessions
- **Quick Commands**: Pre-configured quick command buttons
- **Modern UI**: Clean, tabbed interface with syntax highlighting
- **System Tray Integration**: Minimize to system tray (Linux)
- **Cross-Platform**: Works on Linux, Windows, and macOS

## Requirements

- **Python**: 3.7 or higher
- **Metasploit Framework**: Installed and accessible via `msfconsole` command
- **Operating System**: Linux, Windows, or macOS

### System Requirements

- Python Tkinter support
- Metasploit Framework (for full functionality)

## Installation

### Linux Installation

#### Automatic Installation (Recommended)

The easiest way to install all dependencies:

```bash
./installers/install-dependencies.sh
```

This script will:
- Detect your Linux distribution automatically
- Install all required system packages
- Install Python dependencies via pip
- Check for Metasploit Framework

**Supported Linux Distributions:**
- Debian/Ubuntu/Mint/Pop!_OS/Elementary OS (apt)
- Fedora/RHEL/CentOS (dnf/yum)
- Arch/Manjaro/EndeavourOS/Garuda (pacman)
- openSUSE/SLE (zypper)
- Alpine Linux (apk)
- Solus (eopkg)
- Gentoo (emerge)

#### Manual Installation (Linux)

1. Install system dependencies:
   - **Debian/Ubuntu**: 
     ```bash
     sudo apt install python3 python3-pip python3-tk python3-pil
     ```
   - **Fedora**: 
     ```bash
     sudo dnf install python3 python3-pip python3-tkinter python3-pillow
     ```
   - **Arch/Manjaro**: 
     ```bash
     sudo pacman -S python python-pip tk python-pillow
     ```

2. Install Metasploit Framework:
   - **Debian/Ubuntu**: 
     ```bash
     sudo apt install metasploit-framework
     ```
   - **Arch**: Install from AUR or download from Rapid7
   - **Other**: Visit https://www.metasploit.com/

3. Install Python packages:
   ```bash
   pip install -r requirements.txt
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

#### 1. Metasploit Console Tab

- **Start Console**: Click "Start Console" to launch the integrated Metasploit console
- **Command Input**: Type commands in the input field and press Enter or click "Send"
- **Quick Commands**: Use the quick command buttons for common operations
- **Clear Output**: Click "Clear" to clear the console output
- **Stop Console**: Click "Stop Console" to terminate the Metasploit session

#### 2. Exploit Search Tab

- **Search Exploits**: Enter a search query and click "Search" to find exploits
- **Browse Results**: View exploit names, ranks, and descriptions
- **Use Exploit**: Double-click or select and click "Use Exploit" to load an exploit
- **Show Info**: Select an exploit and click "Show Info" to view detailed information

#### 3. Payload Generator Tab

- **Select Payload Type**: Choose from common payload types
- **Configure Options**: Set LHOST, LPORT, and output format
- **Generate**: Click "Generate Payload" to create the payload
- **Save Payload**: Save the generated payload to a file

#### 4. Auxiliary Modules Tab

- **Search Modules**: Search for auxiliary modules by name or description
- **Use Module**: Double-click or select a module to use it
- **View Results**: Browse available auxiliary modules

#### 5. Session Manager Tab

- **Refresh Sessions**: Click "Refresh Sessions" to update the session list
- **Interact**: Select a session and click "Interact" to interact with it
- **Kill Session**: Select a session and click "Kill Session" to terminate it

## Configuration

### Metasploit Framework Path

The application automatically searches for `msfconsole` in common locations:
- `/usr/bin/msfconsole`
- `/opt/metasploit-framework/msfconsole`
- `/usr/local/bin/msfconsole`
- System PATH

If Metasploit is installed in a non-standard location, ensure it's in your PATH or create a symlink.

### Console Settings

The console uses the `-q` (quiet) flag to reduce startup noise. All commands are sent directly to the Metasploit console.

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

### Missing Dependencies

If you see import errors:
1. Run the dependency installer: `./installers/install-dependencies.sh`
2. Or install manually: `pip install -r requirements.txt`

### Payload Generation Fails

If payload generation fails:
1. Ensure `msfvenom` is available (comes with Metasploit Framework)
2. Check that all required options are filled in
3. Verify the payload type is valid

### System Tray Not Working (Linux)

If the system tray icon doesn't appear:
1. Ensure `pystray` is installed: `pip install pystray`
2. Some desktop environments may require additional packages
3. Try restarting the application

## Project Structure

```
YaP-Metasploit-GUI/
├── core/
│   └── metasploit_gui.py      # Main application and GUI
├── installers/
│   └── install-dependencies.sh # Dependency installer
├── launchers/
│   └── start-metasploit-gui.sh  # Launcher script
├── requirements.txt            # Python dependencies
├── icon.png                    # Application icon (optional)
├── LICENSE                     # License file
└── README.md                   # This file
```

## Dependencies

### Python Packages

- **Pillow** (>=9.0.0): Image processing for icons
- **pystray** (>=0.19.0): System tray support (Linux)

### System Packages

- Python 3.7+ with Tkinter
- Metasploit Framework

## Development

### Running from Source

1. Clone or download the repository
2. Install dependencies (see Installation section)
3. Run using the launcher script:
   ```bash
   ./launchers/start-metasploit-gui.sh
   ```
   Or run directly:
   ```bash
   python3 core/metasploit_gui.py
   ```

## Security Notice

**Important**: This tool is designed for authorized security testing and educational purposes only. Only use Metasploit Framework and this GUI on systems you own or have explicit written permission to test. Unauthorized access to computer systems is illegal.

## License

© YaP Labs

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For issues, questions, or feature requests, please open an issue on the project repository.

---

**Note**: This application requires Metasploit Framework to be installed. Ensure you have proper authorization before using this tool for security testing.

