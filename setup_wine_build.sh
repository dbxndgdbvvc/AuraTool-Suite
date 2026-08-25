#!/bin/bash
# AuraTool-Suite — Wine Cross-Compilation Setup Script
# =====================================================
# Sets up Wine + Windows Python for building .exe from Linux.
# Run with: sudo bash setup_wine_build.sh
#
# Requirements:
#   - Ubuntu/Debian-based system
#   - Internet connection
#   - ~2 GB disk space for Wine + Windows Python

set -euo pipefail

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  AuraTool-Suite — Wine Cross-Compilation Setup          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Enable 32-bit architecture
echo "[1/5] Enabling i386 architecture..."
dpkg --add-architecture i386
apt-get update -qq# Step 2: Install Wine and UPX
    echo "[2/5] Installing Wine64, Wine32, and UPX..."
    apt-get install -y -qq wine64 wine32 upx-ucl

# Step 3: Verify Wine installation
echo "[3/5] Verifying Wine installation..."
wine64 --version || { echo "ERROR: Wine64 installation failed"; exit 1; }

# Step 4: Download and install Windows Python 3.12
echo "[4/5] Installing Windows Python 3.12 in Wine..."
PYTHON_VERSION="3.12.5"
PYTHON_INSTALLER="python-${PYTHON_VERSION}-amd64.exe"
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_INSTALLER}"

if [ ! -f "/tmp/${PYTHON_INSTALLER}" ]; then
    echo "  Downloading ${PYTHON_INSTALLER}..."
    wget -q -O "/tmp/${PYTHON_INSTALLER}" "${PYTHON_URL}"
fi

echo "  Installing Python in Wine prefix..."
wine64 "/tmp/${PYTHON_INSTALLER}" /quiet InstallAllUsers=1 PrependPath=1 2>/dev/null || true

# Verify Python in Wine
echo "  Verifying Wine Python..."
wine64 python --version || { echo "ERROR: Wine Python installation failed"; exit 1; }

# Step 5: Install PyInstaller in Wine Python
echo "[5/5] Installing PyInstaller in Wine Python..."
wine64 python -m pip install --upgrade pip 2>/dev/null || true
wine64 python -m pip install pyinstaller 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Setup complete! Wine cross-compilation is ready."
echo ""
echo "  Wine version:    $(wine64 --version)"
echo "  Python version:  $(wine64 python --version 2>&1)"
echo "  PyInstaller:     $(wine64 python -m PyInstaller --version 2>&1)"
echo ""
echo "  Usage:"
echo "    python build.py                  # Build both platforms"
echo "    python build.py --windows-only   # Windows build only"
echo "    python build.py --linux-only     # Linux build only"
echo "═══════════════════════════════════════════════════════════"
