#!/bin/bash
# ============================================================================
# AuraTool-Suite — Windows Build via Wine Cross-Compilation
# ============================================================================
# Usage:
#   chmod +x build_windows_wine.sh
#   ./build_windows_wine.sh
#
# This script:
#   1. Installs Wine (requires sudo password)
#   2. Sets up a Python environment inside Wine
#   3. Installs PyInstaller and dependencies
#   4. Builds a Windows .exe using PyInstaller
#   5. Packages the result into a ZIP file
# ============================================================================

set -e

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PYTHON_VERSION="3.12.4"
PYTHON_INSTALLER="python-${PYTHON_VERSION}-amd64.exe"
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_INSTALLER}"
APP_NAME="AuraTool-Suite"
APP_VERSION="3.0.0"
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
WINE_PREFIX="$HOME/.wine-auratool"
WINE_DRIVE="C:\\\\"
WINE_PYTHON="C:\\\\Python312\\\\python.exe"

# Build output
BUILD_DIR="${PROJECT_ROOT}/build"
DIST_DIR="${PROJECT_ROOT}/dist"
RELEASE_DIR="${PROJECT_ROOT}/release_output"
WIN_BUILD_DIR="${PROJECT_ROOT}/build_windows"
WIN_TEMP_DIR="${WIN_BUILD_DIR}/wine_temp"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()     { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()      { echo -e "${GREEN}[  OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()     { echo -e "${RED}[ ERR]${NC} $1"; }
step()    { echo -e "\n${CYAN}══════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"; }

# ---------------------------------------------------------------------------
# Step 1: Install Wine
# ---------------------------------------------------------------------------
step "Step 1/6: Installing Wine"

if command -v wine64 &>/dev/null || command -v wine &>/dev/null; then
    WINE_CMD=$(command -v wine64 || command -v wine)
    WINE_VER=$($WINE_CMD --version 2>/dev/null || echo "unknown")
    ok "Wine already installed: $WINE_VER"
else
    log "Wine not found. Installing via apt..."
    sudo dpkg --add-architecture i386 2>/dev/null || true
    sudo apt-get update -qq
    sudo apt-get install -y -qq wine64 wine32
    WINE_CMD=$(command -v wine64 || command -v wine)
    ok "Wine installed: $($WINE_CMD --version)"
fi

# ---------------------------------------------------------------------------
# Step 2: Initialize Wine prefix
# ---------------------------------------------------------------------------
step "Step 2/6: Initializing Wine prefix"

export WINEPREFIX="$WINE_PREFIX"
export WINEDEBUG=-all

if [ -f "$WINE_PREFIX/system.reg" ]; then
    ok "Wine prefix already initialized at $WINE_PREFIX"
else
    log "Creating fresh Wine prefix..."
    $WINE_CMD wineboot --init 2>/dev/null
    ok "Wine prefix created at $WINE_PREFIX"
fi

# ---------------------------------------------------------------------------
# Step 3: Install Python inside Wine
# ---------------------------------------------------------------------------
step "Step 3/6: Installing Python ${PYTHON_VERSION} in Wine"

WINE_PYTHON_DIR="${WINE_PREFIX}/drive_c/Python312"
WIN_PYTHON_EXE="${WINE_PREFIX}/drive_c/${PYTHON_INSTALLER}"

if [ -f "$WINE_PYTHON_DIR/python.exe" ]; then
    ok "Python already installed in Wine"
else
    if [ ! -f "$WIN_PYTHON_EXE" ]; then
        log "Downloading Python ${PYTHON_VERSION} installer..."
        wget -q "$PYTHON_URL" -O "$WIN_PYTHON_EXE" 2>/dev/null || \
            curl -sL "$PYTHON_URL" -o "$WIN_PYTHON_EXE"
        ok "Python installer downloaded"
    fi

    log "Installing Python ${PYTHON_VERSION} in Wine (silent install)..."
    $WINE_CMD "C:\\${PYTHON_INSTALLER}" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 2>/dev/null

    if [ -f "$WINE_PYTHON_DIR/python.exe" ]; then
        ok "Python ${PYTHON_VERSION} installed in Wine"
    else
        # Try alternate path
        WINE_PYTHON_DIR="${WINE_PREFIX}/drive_c/Users/${USER}/AppData/Local/Programs/Python/Python312"
        if [ -f "$WINE_PYTHON_DIR/python.exe" ]; then
            ok "Python ${PYTHON_VERSION} installed (alternate path)"
        else
            err "Python installation failed. Check Wine prefix."
            warn "You may need to install Python manually in Wine."
            warn "Run: wine ${PYTHON_INSTALLER}"
            exit 1
        fi
    fi
fi

# Update the Python command path
WIN_PYTHON_EXE_PATH="C:\\Python312\\python.exe"
if [ ! -f "${WINE_PREFIX}/drive_c/Python312/python.exe" ]; then
    # Find where Python was actually installed
    FOUND_PYTHON=$(find "${WINE_PREFIX}/drive_c" -name "python.exe" -path "*/Python3*" 2>/dev/null | head -1)
    if [ -n "$FOUND_PYTHON" ]; then
        # Convert Unix path to Windows path
        WIN_PYTHON_EXE_PATH=$(echo "$FOUND_PYTHON" | sed "s|${WINE_PREFIX}/drive_c/|C:\\\\|" | sed 's|/|\\\\|g')
    fi
fi

log "Python path in Wine: $WIN_PYTHON_EXE_PATH"

# ---------------------------------------------------------------------------
# Step 4: Install PyInstaller and dependencies in Wine Python
# ---------------------------------------------------------------------------
step "Step 4/6: Installing build dependencies in Wine Python"

$WINE_CMD "$WIN_PYTHON_EXE_PATH" -m pip install --upgrade pip 2>/dev/null
$WINE_CMD "$WIN_PYTHON_EXE_PATH" -m pip install pyinstaller 2>/dev/null
$WINE_CMD "$WIN_PYTHON_EXE_PATH" -m pip install fpdf 2>/dev/null
ok "PyInstaller and dependencies installed in Wine Python"

# ---------------------------------------------------------------------------
# Step 5: Build Windows binary
# ---------------------------------------------------------------------------
step "Step 5/6: Building ${APP_NAME} for Windows via Wine"

# Create a Wine-compatible build script
WINE_BUILD_SCRIPT="${WIN_TEMP_DIR}/build_win.py"
mkdir -p "$WIN_TEMP_DIR"

# Convert project root to Windows path
WIN_PROJECT_ROOT=$(echo "$PROJECT_ROOT" | sed "s|/mnt/|Z:\\\\|" | sed 's|/|\\\\|g')

cat > "$WINE_BUILD_SCRIPT" << 'PYEOF'
#!/usr/bin/env python3
"""Build AuraTool-Suite for Windows using PyInstaller (runs inside Wine)."""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# Detect project root (mounted as Z: drive in Wine)
# or use the path provided as argument
if len(sys.argv) > 1:
    PROJECT_ROOT = Path(sys.argv[1].replace("\\", "/"))
else:
    PROJECT_ROOT = Path("Z:/home/mohammed/AuraTool-Suite")

APP_NAME = "AuraTool-Suite"
ENTRY_POINT = str(PROJECT_ROOT / "main.py")

print(f"[INFO] Project root: {PROJECT_ROOT}")
print(f"[INFO] Entry point: {ENTRY_POINT}")

# Module discovery
MODULE_DIRS = ["core", "modules", "drivers", "ui"]
DATA_DIRS = ["languages", "assets"]

def discover_modules():
    hidden = []
    for mod_dir in MODULE_DIRS:
        dir_path = PROJECT_ROOT / mod_dir
        if not dir_path.is_dir():
            continue
        for py_file in sorted(dir_path.glob("*.py")):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue
            hidden.append(f"{mod_dir}.{py_file.stem}")
    for py_file in sorted(PROJECT_ROOT.glob("*.py")):
        if py_file.name in (ENTRY_POINT.split("/")[-1], "build.py", "build_windows.py", "build_windows_wine.sh"):
            continue
        if py_file.name.startswith("_"):
            continue
        hidden.append(py_file.stem)
    return hidden

def discover_data():
    data = []
    for d in DATA_DIRS:
        src = PROJECT_ROOT / d
        if src.is_dir() and any(src.iterdir()):
            data.append((str(src), d))
    return data

# Clean
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
for d in [BUILD_DIR / "wine", DIST_DIR / "wine"]:
    if d.exists():
        shutil.rmtree(d)

# Build PyInstaller command
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--clean", "--noconfirm",
    "--onedir",
    "--noconsole",
    "--name", APP_NAME,
    "--distpath", str(DIST_DIR / "wine"),
    "--workpath", str(BUILD_DIR / "wine"),
    "--specpath", str(PROJECT_ROOT),
]

# Add icon
ico_icon = PROJECT_ROOT / "assets" / "icon.ico"
if ico_icon.exists():
    cmd.extend(["--icon", str(ico_icon)])

# Add data
for src, dest in discover_data():
    cmd.extend(["--add-data", f"{src};{dest}"])

# Add hidden imports
for mod in discover_modules():
    cmd.extend(["--hidden-import", mod])

cmd.append(ENTRY_POINT)

print(f"[INFO] Running: {' '.join(cmd[:5])} ...")
result = subprocess.run(cmd, check=True)
print("[OK] Build complete!")

# Package
win_dist = DIST_DIR / "wine" / APP_NAME
if win_dist.exists():
    release_name = f"{APP_NAME}-v2.0.0-Windows-x64"
    release_dir = PROJECT_ROOT / "release_output"
    release_dir.mkdir(exist_ok=True)
    release_path = release_dir / release_name

    if release_path.exists():
        shutil.rmtree(release_path)
    shutil.copytree(win_dist, release_path)

    # Create README
    readme = release_path / "README.txt"
    readme.write_text(f"""{APP_NAME} v2.0.0 - Windows Portable Edition
{'='*50}

To run: Double-click AuraTool-Suite.exe
To install: Copy the entire folder to your preferred location.

Requirements:
  - Windows 10/11 x64
  - USB device drivers for target devices

License: See license agreement included with the application.
""")

    print(f"[OK] Release package: {release_path}")
    print(f"[OK] Contents: {list(release_path.iterdir())}")
else:
    print(f"[ERR] Build output not found at {win_dist}")
    sys.exit(1)
PYEOF

log "Running Windows build inside Wine..."
$WINE_CMD "$WIN_PYTHON_EXE_PATH" "$(echo "$WINE_BUILD_SCRIPT" | sed 's|/|\\\\|g')" 2>&1

ok "Windows binary built successfully"

# ---------------------------------------------------------------------------
# Step 6: Create ZIP archive
# ---------------------------------------------------------------------------
step "Step 6/6: Creating Windows ZIP archive"

WIN_RELEASE_NAME="${APP_NAME}-v${APP_VERSION}-Windows-x64"
WIN_RELEASE_PATH="${RELEASE_DIR}/${WIN_RELEASE_NAME}"

if [ -d "$WIN_RELEASE_PATH" ]; then
    cd "$RELEASE_DIR"
    zip -r "${WIN_RELEASE_NAME}.zip" "${WIN_RELEASE_NAME}/" 2>/dev/null
    ok "ZIP archive created: ${RELEASE_DIR}/${WIN_RELEASE_NAME}.zip"
    cd "$PROJECT_ROOT"
else
    warn "Release directory not found, skipping ZIP creation"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
step "BUILD COMPLETE!"

echo ""
echo "  📦 Release Artifacts:"
echo ""

if [ -f "${RELEASE_DIR}/${WIN_RELEASE_NAME}.zip" ]; then
    echo "     Windows:  ${RELEASE_DIR}/${WIN_RELEASE_NAME}.zip  ($(du -h "${RELEASE_DIR}/${WIN_RELEASE_NAME}.zip" | cut -f1))"
fi

# Show existing Linux archives too
for f in "${RELEASE_DIR}"/*.tar.gz "${RELEASE_DIR}"/*.zip; do
    if [ -f "$f" ] && [ "$f" != "${RELEASE_DIR}/${WIN_RELEASE_NAME}.zip" ]; then
        echo "     Linux:    $f  ($(du -h "$f" | cut -f1))"
    fi
done

echo ""
echo "  📂 Windows Package Contents:"
echo ""
if [ -d "$WIN_RELEASE_PATH" ]; then
    ls -la "$WIN_RELEASE_PATH" | head -10
fi

echo ""
echo "  ✅ Done!"
echo ""
