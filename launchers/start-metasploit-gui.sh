#!/bin/bash
# YaP Metasploit GUI Launcher
# Checks dependencies and launches the application

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CORE_DIR="$PROJECT_DIR/core"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "YaP Metasploit GUI Launcher"
echo "============================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    echo "Please install Python 3 to continue."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]); then
    echo -e "${RED}Error: Python 3.7 or higher is required.${NC}"
    echo "Current version: $PYTHON_VERSION"
    exit 1
fi

# Check if Metasploit is installed
if ! command -v msfconsole &> /dev/null; then
    echo -e "${YELLOW}Warning: Metasploit Framework not found in PATH.${NC}"
    echo "The application may not work correctly without Metasploit Framework."
    echo "Please install Metasploit Framework to use all features."
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for required Python packages
echo "Checking Python dependencies..."
MISSING_PACKAGES=()

if ! python3 -c "import PIL" 2>/dev/null; then
    MISSING_PACKAGES+=("Pillow")
fi

if ! python3 -c "import pystray" 2>/dev/null; then
    MISSING_PACKAGES+=("pystray")
fi

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${YELLOW}Missing Python packages: ${MISSING_PACKAGES[*]}${NC}"
    echo ""
    read -p "Install missing packages? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "$PROJECT_DIR/requirements.txt" ]; then
            pip3 install -r "$PROJECT_DIR/requirements.txt"
        else
            pip3 install "${MISSING_PACKAGES[@]}"
        fi
    else
        echo -e "${RED}Error: Required packages are missing.${NC}"
        exit 1
    fi
fi

# Check if core directory exists
if [ ! -d "$CORE_DIR" ]; then
    echo -e "${RED}Error: Core directory not found: $CORE_DIR${NC}"
    exit 1
fi

# Check if main script exists
if [ ! -f "$CORE_DIR/metasploit_gui.py" ]; then
    echo -e "${RED}Error: Main script not found: $CORE_DIR/metasploit_gui.py${NC}"
    exit 1
fi

# Launch the application
echo -e "${GREEN}Starting YaP Metasploit GUI...${NC}"
echo ""

cd "$CORE_DIR"
python3 metasploit_gui.py



