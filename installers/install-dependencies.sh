#!/bin/bash
# YaP Metasploit GUI - Dependency Installer
# Automatically detects Linux distribution and installs required dependencies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "YaP Metasploit GUI - Dependency Installer"
echo "=========================================="
echo ""

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_LIKE=$ID_LIKE
    else
        echo -e "${RED}Error: Cannot detect Linux distribution.${NC}"
        exit 1
    fi
}

# Install dependencies based on distribution
install_dependencies() {
    echo "Detected distribution: $DISTRO"
    echo ""
    
    case $DISTRO in
        ubuntu|debian|linuxmint|pop|elementary)
            echo "Installing dependencies for Debian/Ubuntu-based distribution..."
            sudo apt update
            sudo apt install -y python3 python3-pip python3-tk python3-dev python3-pil python3-pil.imagetk
            ;;
        fedora|rhel|centos)
            echo "Installing dependencies for Fedora/RHEL-based distribution..."
            sudo dnf install -y python3 python3-pip python3-tkinter python3-devel python3-pillow
            ;;
        arch|manjaro|endeavour|garuda)
            echo "Installing dependencies for Arch-based distribution..."
            sudo pacman -S --needed python python-pip tk python-pillow
            ;;
        opensuse*|sles)
            echo "Installing dependencies for openSUSE..."
            sudo zypper install -y python3 python3-pip python3-tk python3-devel python3-Pillow
            ;;
        alpine)
            echo "Installing dependencies for Alpine Linux..."
            sudo apk add python3 py3-pip tk python3-dev py3-pillow
            ;;
        solus)
            echo "Installing dependencies for Solus..."
            sudo eopkg install -y python3 python3-pip python3-tk python3-devel python3-pillow
            ;;
        gentoo)
            echo "Installing dependencies for Gentoo..."
            sudo emerge -av dev-lang/python:3.11 dev-python/pip tk dev-python/pillow
            ;;
        *)
            echo -e "${YELLOW}Warning: Unsupported distribution. Attempting generic installation...${NC}"
            if command -v apt &> /dev/null; then
                sudo apt update && sudo apt install -y python3 python3-pip python3-tk python3-pil
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y python3 python3-pip python3-tkinter python3-pillow
            elif command -v pacman &> /dev/null; then
                sudo pacman -S --needed python python-pip tk python-pillow
            else
                echo -e "${RED}Error: Cannot determine package manager.${NC}"
                exit 1
            fi
            ;;
    esac
}

# Install Python packages
install_python_packages() {
    echo ""
    echo "Installing Python packages..."
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        pip3 install -r "$PROJECT_DIR/requirements.txt"
    else
        pip3 install Pillow pystray
    fi
}

# Check for Metasploit
check_metasploit() {
    echo ""
    if command -v msfconsole &> /dev/null; then
        echo -e "${GREEN}Metasploit Framework is installed.${NC}"
    else
        echo -e "${YELLOW}Warning: Metasploit Framework not found.${NC}"
        echo "To use all features, please install Metasploit Framework:"
        echo "  - Debian/Ubuntu: sudo apt install metasploit-framework"
        echo "  - Arch: Install from AUR or download from Rapid7"
        echo "  - Other: Visit https://www.metasploit.com/"
    fi
}

# Main
detect_distro
install_dependencies
install_python_packages
check_metasploit

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo "You can now run the application using:"
echo "  ./launchers/start-metasploit-gui.sh"

