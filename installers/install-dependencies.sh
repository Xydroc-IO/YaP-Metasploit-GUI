#!/bin/bash
# YaP Metasploit GUI - Comprehensive Dependency Installer
# Automatically detects Linux distribution and installs all required dependencies
# 
# Features:
# - Installs PostgreSQL for Metasploit database support
# - Supports all major Linux distributions (Arch, Manjaro, Ubuntu, Debian, Fedora, etc.)
# - Supports all desktop environments (XFCE, Cinnamon, GNOME, KDE, MATE, etc.)
# - Uses --break-system-packages flag for pip when needed (Python 3.11+)
# - Comprehensive error handling and fallback methods

set -e  # Exit on error (but we'll handle some errors gracefully)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[-]${NC} $1"
}

echo "=========================================="
echo "YaP Metasploit GUI - Dependency Installer"
echo "=========================================="
echo ""

# Check if running as root (we need sudo, not root)
if [ "$EUID" -eq 0 ]; then 
    print_warning "Please run this script as a regular user (not root). It will use sudo when needed."
    exit 1
fi

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_LIKE=$ID_LIKE
        DISTRO_VERSION=$VERSION_ID
        print_success "Detected distribution: $PRETTY_NAME ($DISTRO)"
    else
        print_error "Cannot detect Linux distribution. /etc/os-release not found."
        exit 1
    fi
}

# Detect desktop environment
detect_desktop() {
    if [ -n "$XDG_CURRENT_DESKTOP" ]; then
        DESKTOP_ENV=$(echo "$XDG_CURRENT_DESKTOP" | cut -d: -f1 | tr '[:upper:]' '[:lower:]')
        print_status "Detected desktop environment: $DESKTOP_ENV"
    elif [ -n "$DESKTOP_SESSION" ]; then
        DESKTOP_ENV=$(echo "$DESKTOP_SESSION" | tr '[:upper:]' '[:lower:]')
        print_status "Detected desktop session: $DESKTOP_ENV"
    elif [ -n "$GDMSESSION" ]; then
        DESKTOP_ENV=$(echo "$GDMSESSION" | tr '[:upper:]' '[:lower:]')
        print_status "Detected GDM session: $DESKTOP_ENV"
    else
        DESKTOP_ENV="unknown"
        print_warning "Could not detect desktop environment. Installing generic packages."
    fi
}

# Install PostgreSQL based on distribution
install_postgresql() {
    print_status "Installing PostgreSQL for Metasploit database support..."
    
    case $DISTRO in
        ubuntu|debian|linuxmint|pop|elementary)
            sudo apt update
            sudo apt install -y postgresql postgresql-contrib postgresql-client libpq-dev
            ;;
        fedora|rhel|centos)
            if command -v dnf &> /dev/null; then
                sudo dnf install -y postgresql postgresql-server postgresql-contrib libpq-devel
                # Initialize PostgreSQL database if not already initialized
                if [ ! -d /var/lib/pgsql/data ] && [ ! -d /var/lib/pgsql/data/base ]; then
                    print_status "Initializing PostgreSQL database..."
                    sudo postgresql-setup --initdb 2>/dev/null || sudo postgresql-setup initdb 2>/dev/null || true
                fi
                sudo systemctl enable postgresql 2>/dev/null || true
                sudo systemctl start postgresql 2>/dev/null || true
            else
                sudo yum install -y postgresql postgresql-server postgresql-contrib libpq-devel
                sudo postgresql-setup initdb 2>/dev/null || true
                sudo systemctl enable postgresql 2>/dev/null || true
                sudo systemctl start postgresql 2>/dev/null || true
            fi
            ;;
        arch|manjaro|endeavour|garuda)
            sudo pacman -S --needed postgresql postgresql-libs libpqxx
            # Initialize PostgreSQL database if not already initialized
            # Check common PostgreSQL data directories
            POSTGRES_DATA_DIR=""
            if [ -d /var/lib/postgres/data ]; then
                POSTGRES_DATA_DIR="/var/lib/postgres/data"
            elif [ -d /var/lib/postgres ]; then
                POSTGRES_DATA_DIR="/var/lib/postgres"
            fi
            
            if [ -n "$POSTGRES_DATA_DIR" ] && [ ! -d "$POSTGRES_DATA_DIR/base" ] && [ ! -f "$POSTGRES_DATA_DIR/PG_VERSION" ]; then
                print_status "Initializing PostgreSQL database..."
                # Try to initialize with the postgres user
                if id "postgres" &>/dev/null; then
                    sudo -u postgres initdb -D "$POSTGRES_DATA_DIR" 2>/dev/null || \
                    sudo -u postgres initdb --locale=C --encoding=UTF8 2>/dev/null || \
                    sudo -u postgres initdb 2>/dev/null || true
                else
                    print_warning "PostgreSQL user not found. Database may need manual initialization."
                fi
            fi
            sudo systemctl enable postgresql 2>/dev/null || true
            sudo systemctl start postgresql 2>/dev/null || true
            ;;
        opensuse*|sles)
            sudo zypper install -y postgresql postgresql-server postgresql-contrib postgresql-devel
            sudo systemctl enable postgresql 2>/dev/null || true
            sudo systemctl start postgresql 2>/dev/null || true
            ;;
        alpine)
            sudo apk add postgresql postgresql-client postgresql-dev
            sudo rc-update add postgresql default 2>/dev/null || true
            sudo rc-service postgresql start 2>/dev/null || true
            ;;
        solus)
            sudo eopkg install -y postgresql postgresql-devel
            sudo systemctl enable postgresql 2>/dev/null || true
            sudo systemctl start postgresql 2>/dev/null || true
            ;;
        gentoo)
            sudo emerge -av dev-db/postgresql
            sudo rc-update add postgresql default 2>/dev/null || true
            sudo rc-service postgresql start 2>/dev/null || true
            ;;
        *)
            print_warning "Unsupported distribution for automatic PostgreSQL installation."
            if command -v apt &> /dev/null; then
                sudo apt update && sudo apt install -y postgresql postgresql-contrib postgresql-client libpq-dev
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y postgresql postgresql-server postgresql-contrib libpq-devel
            elif command -v pacman &> /dev/null; then
                sudo pacman -S --needed postgresql postgresql-libs libpqxx
            else
                print_error "Cannot determine package manager for PostgreSQL installation."
                return 1
            fi
            ;;
    esac
    
    print_success "PostgreSQL installed successfully"
}

# Install desktop environment dependencies for system tray support
install_desktop_deps() {
    print_status "Installing desktop environment dependencies for system tray support..."
    
    case $DISTRO in
        ubuntu|debian|linuxmint|pop|elementary)
            # Install packages for all major desktop environments
            # Supports XFCE, Cinnamon, GNOME, KDE, MATE, and other GTK-based DEs
            sudo apt install -y \
                libappindicator3-1 \
                gir1.2-appindicator3-0.1 \
                libgtk-3-0 \
                libgirepository1.0-dev \
                python3-gi \
                python3-gi-cairo \
                gir1.2-gtk-3.0 \
                libcairo2-dev \
                libgdk-pixbuf2.0-dev
            ;;
        fedora|rhel|centos)
            # Supports XFCE, Cinnamon, GNOME, KDE, and other GTK-based DEs
            sudo dnf install -y \
                libappindicator \
                libappindicator-gtk3 \
                gtk3 \
                gobject-introspection \
                python3-gobject \
                python3-cairo \
                cairo-gobject-devel \
                gdk-pixbuf2
            ;;
        arch|manjaro|endeavour|garuda)
            # Install comprehensive desktop environment support
            # Works with XFCE, Cinnamon, GNOME, KDE, and other GTK-based DEs
            sudo pacman -S --needed \
                libappindicator-gtk3 \
                gtk3 \
                python-gobject \
                gobject-introspection \
                cairo \
                python-cairo \
                gtk-update-icon-cache
            ;;
        opensuse*|sles)
            sudo zypper install -y \
                libappindicator3-1 \
                typelib-1_0-AppIndicator3-0_1 \
                gtk3 \
                python3-gobject \
                python3-gobject-Gdk \
                gobject-introspection \
                cairo
            ;;
        alpine)
            sudo apk add \
                libappindicator \
                gtk+3.0 \
                py3-gobject3 \
                gobject-introspection \
                cairo
            ;;
        solus)
            sudo eopkg install -y \
                libappindicator-devel \
                gtk3-devel \
                python3-gobject \
                gobject-introspection \
                cairo-devel
            ;;
        gentoo)
            sudo emerge -av \
                x11-libs/libappindicator \
                x11-libs/gtk+:3 \
                dev-python/pygobject \
                dev-libs/gobject-introspection \
                x11-libs/cairo
            ;;
        *)
            print_warning "Attempting generic desktop environment package installation..."
            if command -v apt &> /dev/null; then
                sudo apt install -y libappindicator3-1 gir1.2-appindicator3-0.1 python3-gi
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y libappindicator python3-gobject
            elif command -v pacman &> /dev/null; then
                sudo pacman -S --needed libappindicator-gtk3 python-gobject
            fi
            ;;
    esac
    
    print_success "Desktop environment dependencies installed"
}

# Install base system dependencies
install_base_dependencies() {
    print_status "Installing base system dependencies..."
    
    case $DISTRO in
        ubuntu|debian|linuxmint|pop|elementary)
            sudo apt update
            sudo apt install -y \
                python3 \
                python3-pip \
                python3-tk \
                python3-dev \
                python3-pil \
                python3-pil.imagetk \
                python3-venv \
                build-essential \
                libssl-dev \
                libffi-dev \
                pkg-config
            ;;
        fedora|rhel|centos)
            if command -v dnf &> /dev/null; then
                sudo dnf install -y \
                    python3 \
                    python3-pip \
                    python3-tkinter \
                    python3-devel \
                    python3-pillow \
                    python3-virtualenv \
                    gcc \
                    gcc-c++ \
                    openssl-devel \
                    libffi-devel \
                    pkgconfig
            else
                sudo yum install -y \
                    python3 \
                    python3-pip \
                    python3-tkinter \
                    python3-devel \
                    python3-pillow \
                    gcc \
                    gcc-c++ \
                    openssl-devel \
                    libffi-devel \
                    pkgconfig
            fi
            ;;
        arch|manjaro|endeavour|garuda)
            sudo pacman -S --needed \
                python \
                python-pip \
                tk \
                python-pillow \
                base-devel \
                openssl \
                libffi \
                pkg-config
            ;;
        opensuse*|sles)
            sudo zypper install -y \
                python3 \
                python3-pip \
                python3-tk \
                python3-devel \
                python3-Pillow \
                python3-virtualenv \
                gcc \
                gcc-c++ \
                libopenssl-devel \
                libffi-devel \
                pkg-config
            ;;
        alpine)
            sudo apk add \
                python3 \
                py3-pip \
                tk \
                python3-dev \
                py3-pillow \
                py3-virtualenv \
                gcc \
                g++ \
                musl-dev \
                openssl-dev \
                libffi-dev \
                pkgconfig
            ;;
        solus)
            sudo eopkg install -y \
                python3 \
                python3-pip \
                python3-tk \
                python3-devel \
                python3-pillow \
                system.devel \
                openssl-devel \
                libffi-devel \
                pkg-config
            ;;
        gentoo)
            sudo emerge -av \
                dev-lang/python:3.11 \
                dev-python/pip \
                x11-libs/libXt \
                dev-python/pillow \
                sys-devel/gcc \
                dev-libs/openssl \
                dev-libs/libffi
            ;;
        *)
            print_warning "Unsupported distribution. Attempting generic installation..."
            if command -v apt &> /dev/null; then
                sudo apt update && sudo apt install -y python3 python3-pip python3-tk python3-dev python3-pil build-essential
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y python3 python3-pip python3-tkinter python3-devel python3-pillow gcc gcc-c++
            elif command -v pacman &> /dev/null; then
                sudo pacman -S --needed python python-pip tk python-pillow base-devel
            else
                print_error "Cannot determine package manager."
                exit 1
            fi
            ;;
    esac
    
    print_success "Base system dependencies installed"
}

# Install Python packages
install_python_packages() {
    print_status "Installing Python packages from requirements.txt..."
    
    # Determine if we need --break-system-packages flag
    # This is needed for newer Python installations (3.11+) on systems with externally-managed environments
    BREAK_SYSTEM_FLAG=""
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
        # Python 3.11+ - try with --break-system-packages first
        BREAK_SYSTEM_FLAG="--break-system-packages"
    fi
    
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        # Upgrade pip first (try with --break-system-packages for newer systems)
        python3 -m pip install --upgrade pip --user $BREAK_SYSTEM_FLAG 2>/dev/null || \
        python3 -m pip install --upgrade pip $BREAK_SYSTEM_FLAG 2>/dev/null || \
        python3 -m pip install --upgrade pip --user 2>/dev/null || \
        python3 -m pip install --upgrade pip
        
        # Install requirements - try multiple methods with --break-system-packages
        print_status "Installing packages from requirements.txt..."
        if python3 -m pip install --user $BREAK_SYSTEM_FLAG -r "$PROJECT_DIR/requirements.txt" 2>/dev/null; then
            print_success "Python packages installed (user install)"
        elif python3 -m pip install $BREAK_SYSTEM_FLAG -r "$PROJECT_DIR/requirements.txt" 2>/dev/null; then
            print_success "Python packages installed (system install)"
        elif pip3 install --user $BREAK_SYSTEM_FLAG -r "$PROJECT_DIR/requirements.txt" 2>/dev/null; then
            print_success "Python packages installed (user install via pip3)"
        elif pip3 install $BREAK_SYSTEM_FLAG -r "$PROJECT_DIR/requirements.txt" 2>/dev/null; then
            print_success "Python packages installed (system install via pip3)"
        elif sudo pip3 install $BREAK_SYSTEM_FLAG -r "$PROJECT_DIR/requirements.txt" 2>/dev/null; then
            print_success "Python packages installed (sudo install)"
        else
            # Fallback without flag
            python3 -m pip install --user -r "$PROJECT_DIR/requirements.txt" || \
            pip3 install --user -r "$PROJECT_DIR/requirements.txt" || \
            sudo pip3 install -r "$PROJECT_DIR/requirements.txt"
            print_success "Python packages installed (fallback method)"
        fi
    else
        print_warning "requirements.txt not found. Installing default packages..."
        python3 -m pip install --upgrade pip --user $BREAK_SYSTEM_FLAG 2>/dev/null || \
        python3 -m pip install --upgrade pip $BREAK_SYSTEM_FLAG 2>/dev/null || \
        python3 -m pip install --upgrade pip --user 2>/dev/null || \
        python3 -m pip install --upgrade pip
        
        if python3 -m pip install --user $BREAK_SYSTEM_FLAG Pillow pystray PyYAML 2>/dev/null; then
            print_success "Default Python packages installed (user install)"
        elif python3 -m pip install $BREAK_SYSTEM_FLAG Pillow pystray PyYAML 2>/dev/null; then
            print_success "Default Python packages installed (system install)"
        elif pip3 install --user $BREAK_SYSTEM_FLAG Pillow pystray PyYAML 2>/dev/null; then
            print_success "Default Python packages installed (user install via pip3)"
        elif pip3 install $BREAK_SYSTEM_FLAG Pillow pystray PyYAML 2>/dev/null; then
            print_success "Default Python packages installed (system install via pip3)"
        elif sudo pip3 install $BREAK_SYSTEM_FLAG Pillow pystray PyYAML 2>/dev/null; then
            print_success "Default Python packages installed (sudo install)"
        else
            # Fallback without flag
            python3 -m pip install --user Pillow pystray PyYAML || \
            pip3 install --user Pillow pystray PyYAML || \
            sudo pip3 install Pillow pystray PyYAML
            print_success "Default Python packages installed (fallback method)"
        fi
    fi
}

# Check for Metasploit Framework
check_metasploit() {
    print_status "Checking for Metasploit Framework..."
    
    if command -v msfconsole &> /dev/null; then
        MSF_VERSION=$(msfconsole -V 2>&1 | head -n1 || echo "installed")
        print_success "Metasploit Framework is installed ($MSF_VERSION)"
    else
        print_warning "Metasploit Framework not found."
        echo ""
        echo "To install Metasploit Framework:"
        case $DISTRO in
            ubuntu|debian|linuxmint|pop|elementary)
                echo "  sudo apt install metasploit-framework"
                ;;
            fedora|rhel|centos)
                echo "  sudo dnf install metasploit-framework"
                ;;
            arch|manjaro|endeavour|garuda)
                echo "  Install from AUR: yay -S metasploit-framework"
                echo "  Or download from: https://www.metasploit.com/"
                ;;
            *)
                echo "  Visit: https://www.metasploit.com/"
                ;;
        esac
    fi
}

# Check PostgreSQL status
check_postgresql() {
    print_status "Checking PostgreSQL status..."
    
    if command -v psql &> /dev/null; then
        print_success "PostgreSQL client is installed"
        
        # Check if PostgreSQL service is running
        POSTGRES_RUNNING=false
        
        # Try multiple methods to check if PostgreSQL is running
        if systemctl is-active --quiet postgresql 2>/dev/null || \
           systemctl is-active --quiet postgresql.service 2>/dev/null; then
            POSTGRES_RUNNING=true
        elif pg_isready -q 2>/dev/null; then
            POSTGRES_RUNNING=true
        elif sudo -u postgres pg_isready -q 2>/dev/null; then
            POSTGRES_RUNNING=true
        fi
        
        if [ "$POSTGRES_RUNNING" = true ]; then
            print_success "PostgreSQL service is running"
        else
            print_warning "PostgreSQL service may not be running."
            echo "  Attempting to start PostgreSQL..."
            case $DISTRO in
                ubuntu|debian|linuxmint|pop|elementary|fedora|rhel|centos|arch|manjaro|endeavour|garuda|opensuse*|sles)
                    sudo systemctl start postgresql 2>/dev/null || \
                    sudo systemctl start postgresql.service 2>/dev/null || true
                    sudo systemctl enable postgresql 2>/dev/null || \
                    sudo systemctl enable postgresql.service 2>/dev/null || true
                    # Wait a moment and check again
                    sleep 2
                    if systemctl is-active --quiet postgresql 2>/dev/null || \
                       systemctl is-active --quiet postgresql.service 2>/dev/null; then
                        print_success "PostgreSQL service started successfully"
                    else
                        echo "    If PostgreSQL still doesn't start, try manually:"
                        echo "    sudo systemctl start postgresql"
                        echo "    sudo systemctl enable postgresql  # Enable on boot"
                    fi
                    ;;
                alpine|gentoo)
                    sudo rc-service postgresql start 2>/dev/null || true
                    sudo rc-update add postgresql default 2>/dev/null || true
                    sleep 2
                    if pg_isready -q 2>/dev/null; then
                        print_success "PostgreSQL service started successfully"
                    else
                        echo "    If PostgreSQL still doesn't start, try manually:"
                        echo "    sudo rc-service postgresql start"
                        echo "    sudo rc-update add postgresql default  # Enable on boot"
                    fi
                    ;;
            esac
        fi
    else
        print_warning "PostgreSQL client not found. This may cause database initialization issues."
    fi
}

# Main installation flow
main() {
    detect_distro
    detect_desktop
    
    echo ""
    print_status "Starting dependency installation..."
    echo ""
    
    # Install dependencies in order
    install_base_dependencies
    echo ""
    
    install_postgresql
    echo ""
    
    install_desktop_deps
    echo ""
    
    install_python_packages
    echo ""
    
    check_postgresql
    echo ""
    
    check_metasploit
    echo ""
    
    echo "=========================================="
    print_success "Installation complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "  1. Ensure PostgreSQL is running:"
    echo "     sudo systemctl start postgresql"
    echo ""
    echo "  2. Initialize Metasploit database (if not done already):"
    echo "     msfdb init"
    echo ""
    echo "  3. Run the application:"
    echo "     ./launchers/start-metasploit-gui.sh"
    echo ""
    echo "For troubleshooting, see README.md"
    echo ""
}

# Run main function
main "$@"
