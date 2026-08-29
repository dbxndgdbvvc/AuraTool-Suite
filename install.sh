#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
#  AuraTool-Suite — Linux Installer (Ubuntu/Debian/Fedora/Arch)
#  Version: 6.0.0
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_MIN="3.8"

# ═══════════════════════════════════════════════════════════════════════════════
print_banner() {
    echo -e "${CYAN}"
    echo "  ╔═══════════════════════════════════════════════════════════╗"
    echo "  ║     🔧 AuraTool-Suite — Linux Installer v6.0.0         ║"
    echo "  ║     Universal Device Maintenance & Repair Platform      ║"
    echo "  ╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ═══════════════════════════════════════════════════════════════════════════════
check_python() {
    echo -e "${YELLOW}[1/6] Checking Python installation...${NC}"

    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            PY_VER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
            PY_MAJOR=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null)
            PY_MINOR=$("$cmd" -c "import sys; print(sys.version_info.minor)" 2>/dev/null)

            if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 8 ]; then
                PYTHON="$cmd"
                echo -e "  ${GREEN}✅ Python $PY_VER found: $PYTHON${NC}"
                return 0
            else
                echo -e "  ${RED}❌ Python $PY_VER is too old (need >= $PYTHON_MIN)${NC}"
            fi
        fi
    done

    echo -e "  ${RED}❌ Python 3.8+ not found. Please install Python 3.8 or newer.${NC}"
    echo -e "  ${CYAN}  Ubuntu/Debian: sudo apt install python3 python3-venv python3-tk${NC}"
    echo -e "  ${CYAN}  Fedora:        sudo dnf install python3 python3-tkinter${NC}"
    echo -e "  ${CYAN}  Arch:          sudo pacman -S python python-tk${NC}"
    exit 1
}

# ═══════════════════════════════════════════════════════════════════════════════
check_system_deps() {
    echo -e "${YELLOW}[2/6] Checking system dependencies...${NC}"

    # Check for tkinter (required for GUI)
    if "$PYTHON" -c "import tkinter" 2>/dev/null; then
        echo -e "  ${GREEN}✅ tkinter (GUI toolkit)${NC}"
    else
        echo -e "  ${YELLOW}⚠️  tkinter not found — installing...${NC}"
        if command -v apt &>/dev/null; then
            sudo apt install -y python3-tk 2>/dev/null || echo -e "  ${RED}  Failed to install python3-tk. Run: sudo apt install python3-tk${NC}"
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y python3-tkinter 2>/dev/null || echo -e "  ${RED}  Failed to install python3-tkinter. Run: sudo dnf install python3-tkinter${NC}"
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm python-tk 2>/dev/null || echo -e "  ${RED}  Failed to install python-tk. Run: sudo pacman -S python-tk${NC}"
        else
            echo -e "  ${RED}  Cannot auto-install tkinter. Please install python3-tk manually.${NC}"
        fi
    fi

    # Check for ADB/Fastboot (optional but recommended)
    if command -v adb &>/dev/null; then
        echo -e "  ${GREEN}✅ ADB (Android Debug Bridge)${NC}"
    else
        echo -e "  ${YELLOW}⚠️  ADB not found — device operations will use simulation mode${NC}"
    fi

    if command -v fastboot &>/dev/null; then
        echo -e "  ${GREEN}✅ Fastboot${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Fastboot not found — flashing operations will use simulation mode${NC}"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
create_venv() {
    echo -e "${YELLOW}[3/6] Creating Python virtual environment...${NC}"

    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
        echo -e "  ${GREEN}✅ Virtual environment already exists at $VENV_DIR${NC}"
    else
        echo -e "  Creating venv in $VENV_DIR..."
        "$PYTHON" -m venv "$VENV_DIR"
        echo -e "  ${GREEN}✅ Virtual environment created${NC}"
    fi

    # Activate
    source "$VENV_DIR/bin/activate"
    echo -e "  ${GREEN}✅ Virtual environment activated${NC}"
}

# ═══════════════════════════════════════════════════════════════════════════════
install_deps() {
    echo -e "${YELLOW}[4/6] Installing Python dependencies...${NC}"

    pip install --upgrade pip --quiet 2>/dev/null

    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
        echo -e "  ${GREEN}✅ All dependencies installed from requirements.txt${NC}"
    else
        echo -e "  ${RED}❌ requirements.txt not found${NC}"
        exit 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
run_tests() {
    echo -e "${YELLOW}[5/6] Running quick validation...${NC}"

    cd "$SCRIPT_DIR"
    if "$PYTHON" -c "
from core.license_manager import LicenseManager
from core.security import SecurityManager
from modules.localization import LocalizationManager
from modules.smart_devices import SmartDeviceManager, ECOSYSTEM_CATALOGUE
from modules.flashing_engine import FlashingEngine
from modules.biometrics_fix import BiometricsFix
from modules.data_recovery import DataRecoveryModule
from modules.account_repair import AccountRepairModule
from modules.aura_ai_assistant import AuraAIAssistant
from modules.ultimate_repair import UltimateRepairModule
from modules.device_drivers import DeviceDriverManager

# Verify localization loads
loc = LocalizationManager('en')
assert loc.get_string('title') != None

# Verify device database
cats = list(ECOSYSTEM_CATALOGUE.keys())
total = sum(len(m) for c in ECOSYSTEM_CATALOGUE.values() for m in c.values())
print(f'  ✅ {len(cats)} device categories, {total}+ models loaded')
print(f'  ✅ {len(loc.SUPPORTED_LANGUAGES)} languages supported')
print(f'  ✅ All core modules validated')
" 2>/dev/null; then
        echo -e "  ${GREEN}✅ All validation checks passed${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Some modules may have issues — running with limited features${NC}"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
launch() {
    echo -e "${YELLOW}[6/6] Launching AuraTool-Suite...${NC}"
    echo ""

    cd "$SCRIPT_DIR"

    if [ "$1" = "--no-gui" ]; then
        echo -e "  ${CYAN}Running in CLI mode...${NC}"
        "$PYTHON" -c "
from core.license_manager import LicenseManager
from core.security import SecurityManager
from modules.smart_devices import SmartDeviceManager, ECOSYSTEM_CATALOGUE

lm = LicenseManager()
status = lm.enforce_or_exit()
print(f'  License: {status[\"tier\"]} | Active: {status[\"is_active\"]} | Days: {status[\"days_remaining\"]}')

sm = SecurityManager()
report = sm.get_security_report()
print(f'  Protection: {report[\"protection_active\"]} | Anti-RE: {report[\"anti_reverse_engineering\"]}')

cats = list(ECOSYSTEM_CATALOGUE.keys())
total = sum(len(m) for c in ECOSYSTEM_CATALOGUE.values() for m in c.values())
print(f'  Device database: {len(cats)} categories, {total}+ models')
print()
print('  ✅ AuraTool-Suite is ready. Run without --no-gui for the full GUI.')
"
    else
        echo -e "  ${GREEN}🚀 Starting AuraTool-Suite GUI...${NC}"
        "$PYTHON" main.py
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

print_banner

# Parse arguments
NO_GUI=false
NO_LAUNCH=false

for arg in "$@"; do
    case $arg in
        --no-gui) NO_GUI=true ;;
        --no-launch) NO_LAUNCH=true ;;
        --help|-h)
            echo "Usage: ./install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-gui       Launch in CLI mode (no GUI)"
            echo "  --no-launch    Install only, don't launch"
            echo "  --help, -h     Show this help message"
            exit 0
            ;;
    esac
done

check_python
check_system_deps
create_venv
install_deps
run_tests

if [ "$NO_LAUNCH" = false ]; then
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✅ Installation complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""

    if [ "$NO_GUI" = true ]; then
        launch --no-gui
    else
        launch
    fi
else
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✅ Installation complete! Run './install.sh' to launch.${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
fi
