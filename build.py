#!/usr/bin/env python3
"""
AuraTool-Suite — Professional Portable Dual-Platform Release Builder
====================================================================
Compiles native Linux and Windows executables and bundles them into clean,
standalone portable release packages and archives for desktop clients.

Features:
  - Auto-discovers all Python modules in core/, modules/, drivers/, ui/
  - Builds native Linux binary (--onefile) & Windows binary (.exe via Wine)
  - Packages binaries with documentation, license guides, and required data
  - Generates platform-specific release packages:
      - release_output/AuraTool-Suite-v2.0.0-Linux-x64.tar.gz
      - release_output/AuraTool-Suite-v2.0.0-Windows-x64.zip
  - Clean directory isolation and zero workspace clutter

Usage:
    python build.py                 # Package both platforms
    python build.py --linux-only    # Linux package only
    python build.py --windows-only  # Windows package only
    python build.py --clean-only    # Clean build directories only
"""

import glob
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Project Layout & Metadata
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.join(PROJECT_ROOT, "release_output")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")

APP_NAME = "AuraTool-Suite"
VERSION = "2.0.0"

PACKAGE_DIRS = ["core", "modules", "drivers", "ui"]
TOP_LEVEL_SCRIPTS = ["auratool_factory"]

README_TEXT = f"""===============================================================================
  AuraTool-Suite v{VERSION} — Universal Mobile Maintenance & Repair Framework
===============================================================================

Thank you for choosing AuraTool-Suite.

QUICK START GUIDE
-----------------
1. Launching the Application:
   - Linux: Run './AuraTool-Suite' from terminal or double click the executable.
   - Windows: Double-click 'AuraTool-Suite.exe'.

2. License Activation:
   - On first startup, enter your 6-Month or 1-Year license key in the top activation bar.
   - Your key will bind automatically to your hardware HWID for offline use.

3. USB Drivers & Connection Protocols:
   - Ensure the required device drivers (Samsung Odin/Download, Qualcomm EDL 9008,
     MediaTek BROM/Meta, ADB/Fastboot) are installed on your host system.

4. Features Included:
   - Universal Firmware Flashing & Partition Recovery (payload.bin, super.img)
   - Automated FRP & Cloud Account Bypass Algorithms
   - System Bootloop, Black Screen, and Virus Eradication Engine
   - Workshop Ticket & Client Inventory Management Subsystem

For technical support or feature requests, contact your distributor.
==============================================================================="""

INSTALL_DESKTOP_TEXT = """#!/bin/bash
# AuraTool-Suite — Linux Desktop Integration Installer
# Run this script to install the application launcher and icons
# into your system's desktop environment.
#
# Usage:  chmod +x install-desktop.sh && ./install-desktop.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="auratool-suite"

# Detect install location
if [ -w /usr/local ]; then
    INSTALL_PREFIX="/usr/local"
elif [ -w "$HOME/.local" ]; then
    INSTALL_PREFIX="$HOME/.local"
else
    echo "[!] Cannot write to /usr/local or ~/.local"
    echo "    Try: sudo ./install-desktop.sh"
    exit 1
fi

echo "AuraTool-Suite — Desktop Integration Installer"
echo "================================================"
echo "  Install prefix: $INSTALL_PREFIX"

# 1. Install binary
echo "\n[1/4] Installing binary..."
cp "$SCRIPT_DIR/AuraTool-Suite" "$INSTALL_PREFIX/bin/AuraTool-Suite"
chmod +x "$INSTALL_PREFIX/bin/AuraTool-Suite"
echo "  → $INSTALL_PREFIX/bin/AuraTool-Suite"    # 2. Install icons
echo "\n[2/4] Installing icons..."
for size_dir in "$SCRIPT_DIR/icons"/*/; do
    size=$(basename "$size_dir")
    icon_dir="$INSTALL_PREFIX/share/icons/hicolor/$size/apps"
    mkdir -p "$icon_dir"
    cp "$size_dir/${APP_NAME}.png" "$icon_dir/${APP_NAME}.png"
    echo "  → $icon_dir/${APP_NAME}.png"
done

# Also install the main PNG as scalable
mkdir -p "$INSTALL_PREFIX/share/icons/hicolor/scalable/apps"
cp "$SCRIPT_DIR/icon.png" "$INSTALL_PREFIX/share/icons/hicolor/scalable/apps/${APP_NAME}.png"
echo "  → scalable/${APP_NAME}.png"    # 3. Install .desktop file
echo "\n[3/4] Installing desktop entry..."
DESKTOP_DIR="$INSTALL_PREFIX/share/applications"
mkdir -p "$DESKTOP_DIR"

# Write .desktop with correct Exec path
cat > "$DESKTOP_DIR/${APP_NAME}.desktop" << EOF
[Desktop Entry]
Type=Application
Name=AuraTool-Suite
GenericName=Mobile Device Repair Tool
Comment=Universal mobile device maintenance and repair framework
Exec=$INSTALL_PREFIX/bin/AuraTool-Suite
Icon=${APP_NAME}
Terminal=false
Categories=Utility;System;Development;
Keywords=mobile;repair;firmware;flash;android;apple;
StartupNotify=true
StartupWMClass=AuraTool-Suite
EOF
echo "  → $DESKTOP_DIR/${APP_NAME}.desktop"    # 4. Update icon cache
echo "\n[4/4] Updating icon cache..."
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "$INSTALL_PREFIX/share/icons/hicolor" 2>/dev/null || true
    echo "  → Icon cache updated"
fi
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    echo "  → Desktop database updated"
fi

echo "\n================================================"
echo "  ✅ Installation complete!"
echo "  You can now find AuraTool-Suite in your application menu."
echo "  Or run: $INSTALL_PREFIX/bin/AuraTool-Suite"
echo "================================================"
"""

# ---------------------------------------------------------------------------
# Auto-Discover Modules & Hidden Imports
# ---------------------------------------------------------------------------

def discover_packages(base_dirs: list[str]) -> list[str]:
    """Walk each package directory and return fully-qualified module paths."""
    modules = []
    for base in base_dirs:
        pkg_path = os.path.join(PROJECT_ROOT, base)
        if not os.path.isdir(pkg_path):
            continue
        modules.append(base)
        for root, dirs, files in os.walk(pkg_path):
            dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]
            for f in files:
                if f.endswith(".py") and f != "__init__.py":
                    rel = os.path.relpath(os.path.join(root, f), PROJECT_ROOT)
                    mod = rel.replace(os.sep, ".").replace("/", ".")
                    if mod.endswith(".py"):
                        mod = mod[:-3]
                    modules.append(mod)
    return modules


def get_all_hidden_imports() -> list[str]:
    """Build the complete list of hidden imports by scanning the project."""
    discovered = discover_packages(PACKAGE_DIRS)
    for script in TOP_LEVEL_SCRIPTS:
        if os.path.isfile(os.path.join(PROJECT_ROOT, f"{script}.py")):
            discovered.append(script)
    
    seen = set()
    result = []
    for m in discovered:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def get_entry_point() -> str:
    """Determine the application entry point script."""
    candidates = [
        os.path.join(PROJECT_ROOT, "main.py"),
        os.path.join(PROJECT_ROOT, "ui", "app.py"),
        os.path.join(PROJECT_ROOT, "auratool_factory.py"),
    ]
    for ep in candidates:
        if os.path.isfile(ep):
            return ep
    print("[FATAL] No entry point found.")
    sys.exit(1)


def get_data_dirs() -> list[tuple[str, str]]:
    """Returns (absolute_source, dest) pairs for --add-data.
    
    Uses absolute source paths so PyInstaller can find them regardless
    of where the spec file is located (e.g. build/ directory).
    """
    dirs = [
        ("languages", "languages"),
        ("ui", "ui"),
        ("assets", "assets"),
    ]
    result = []
    for src, dst in dirs:
        abs_src = os.path.join(PROJECT_ROOT, src)
        if os.path.isdir(abs_src):
            result.append((abs_src, dst))
    return result

def get_icon_args() -> list[str]:
    """Return --icon argument if assets/icon.ico exists."""
    icon = os.path.join(PROJECT_ROOT, "assets", "icon.ico")
    if os.path.isfile(icon):
        return [f"--icon={icon}"]
    return []


# ---------------------------------------------------------------------------
# Workspace Cleaning & Tool Detection
# ---------------------------------------------------------------------------

def clean_build_artifacts():
    """Remove temporary build directories and spec files."""
    print("[*] Cleaning build artifacts and temporary files...")
    for d in [BUILD_DIR, DIST_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
            print(f"    Removed: {d}/")
    for spec in glob.glob(os.path.join(PROJECT_ROOT, "*.spec")):
        try:
            os.remove(spec)
            print(f"    Removed: {os.path.basename(spec)}")
        except OSError:
            pass
    print("[+] Workspace clean complete.\n")


def ensure_pyinstaller():
    """Ensure PyInstaller is available."""
    try:
        import PyInstaller
        print(f"[*] Native PyInstaller {PyInstaller.__version__} ready.")
    except ImportError:
        print("[!] PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def ensure_wine():
    """Check for Wine and a Windows Python environment."""
    wine_path = shutil.which("wine64") or shutil.which("wine")
    if not wine_path:
        return None, None

    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".wine/drive_c/Python312/python.exe"),
        os.path.join(home, ".wine/drive_c/Python311/python.exe"),
        os.path.join(home, ".wine/drive_c/Python310/python.exe"),
        os.path.join(home, ".wine/drive_c/Python39/python.exe"),
        os.path.join(home, ".wine/drive_c/Program Files/Python312/python.exe"),
        os.path.join(home, ".wine/drive_c/Program Files/Python311/python.exe"),
        os.path.join(home, ".wine/drive_c/Program Files/Python310/python.exe"),
        os.path.join(home, ".wine/drive_c/Program Files/Python39/python.exe"),
    ]
    for py in candidates:
        if os.path.isfile(py):
            return wine_path, py

    try:
        res = subprocess.run(
            [wine_path, "python", "--version"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
        )
        if res.returncode == 0:
            return wine_path, "python"
    except Exception:
        pass

    return wine_path, None


def file_size_mb(path: str) -> float:
    """Return file size in MB."""
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except OSError:
        return 0.0

# ---------------------------------------------------------------------------
# Packaging & Archiving Logic
# ---------------------------------------------------------------------------

def create_portable_package(platform_name: str, binary_path: str) -> str:
    """
    Organizes binary and assets into a clean folder and produces a portable archive.
    For Linux, includes: .desktop file, icon theme, and install script.
    """
    pkg_folder_name = f"{APP_NAME}-v{VERSION}-{platform_name}"
    pkg_dir = os.path.join(RELEASE_DIR, pkg_folder_name)

    if os.path.exists(pkg_dir):
        shutil.rmtree(pkg_dir, ignore_errors=True)

    os.makedirs(pkg_dir, exist_ok=True)

    # 1. Copy Binary
    dest_binary_name = os.path.basename(binary_path)
    target_bin_path = os.path.join(pkg_dir, dest_binary_name)
    shutil.copy2(binary_path, target_bin_path)

    # 2. Write Documentation
    with open(os.path.join(pkg_dir, "README.txt"), "w") as f:
        f.write(README_TEXT)

    # 3. Linux-specific: desktop integration files
    is_linux = "Linux" in platform_name
    if is_linux:
        # Copy .desktop file (keep relative Exec path for portability)
        desktop_src = os.path.join(PROJECT_ROOT, "assets", "auratool-suite.desktop")
        if os.path.isfile(desktop_src):
            shutil.copy2(desktop_src, os.path.join(pkg_dir, "auratool-suite.desktop"))

        # Copy icon theme directory
        icons_src = os.path.join(PROJECT_ROOT, "assets", "icons")
        icons_dst = os.path.join(pkg_dir, "icons")
        if os.path.isdir(icons_src):
            shutil.copytree(icons_src, icons_dst)

        # Copy main PNG icon for easy reference
        icon_png = os.path.join(PROJECT_ROOT, "assets", "icon.png")
        if os.path.isfile(icon_png):
            shutil.copy2(icon_png, os.path.join(pkg_dir, "icon.png"))

        # Write install helper script
        install_script = os.path.join(pkg_dir, "install-desktop.sh")
        with open(install_script, "w") as f:
            f.write(INSTALL_DESKTOP_TEXT)
        os.chmod(install_script, 0o755)

    # 4. Create Archive
    if is_linux:
        archive_path = os.path.join(RELEASE_DIR, f"{pkg_folder_name}.tar.gz")
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(pkg_dir, arcname=pkg_folder_name)
    else:
        archive_path = os.path.join(RELEASE_DIR, f"{pkg_folder_name}.zip")
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(pkg_dir):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, RELEASE_DIR)
                    zipf.write(full_p, rel_p)

    return archive_path

# ---------------------------------------------------------------------------
# Native & Cross-Compilation Targets
# ---------------------------------------------------------------------------

def build_linux(entry_point: str, hidden_imports: list[str]) -> bool:
    """Build native Linux --onefile binary and create portable release package."""
    print("=" * 60)
    print("  BUILDING: Native Linux Release Package")
    print("=" * 60)
    ensure_pyinstaller()

    binary_name = APP_NAME
    raw_output_path = os.path.join(RELEASE_DIR, binary_name)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconfirm",
        "--clean",
        f"--name={binary_name}",
        f"--distpath={RELEASE_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={BUILD_DIR}",
    ]

    cmd += get_icon_args()

    separator = ":"
    for src, dst in get_data_dirs():
        cmd.append(f"--add-data={src}{separator}{dst}")

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    if platform.system() != "Windows":
        cmd.append("--strip")

    cmd.append(entry_point)

    start = time.time()
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.time() - start

    if res.returncode == 0 and os.path.isfile(raw_output_path):
        os.chmod(raw_output_path, 0o755)
        archive_file = create_portable_package("Linux-x64", raw_output_path)
        
        # Clean temporary raw output file outside folder
        if os.path.exists(raw_output_path):
            os.remove(raw_output_path)

        size = file_size_mb(archive_file)
        print(f"\n[SUCCESS] Linux portable package built in {elapsed:.1f}s")
        print(f"          -> Archive: {archive_file} ({size:.1f} MB)")
        return True
    else:
        print(f"\n[FAILED] Linux build failed (exit code {res.returncode})")
        return False


def build_windows_wine(entry_point: str, hidden_imports: list[str]) -> bool:
    """Build Windows .exe via Wine and create portable release package."""
    print("=" * 60)
    print("  BUILDING: Windows .exe Portable Release Package")
    print("=" * 60)

    wine_path, wine_python = ensure_wine()
    if not wine_python:
        print("[!] Wine or Windows Python environment not found on Linux system.")
        return False

    binary_name = f"{APP_NAME}.exe"
    raw_output_path = os.path.join(RELEASE_DIR, binary_name)

    separator = ";"
    cmd = [
        wine_path, wine_python, "-m", "PyInstaller",
        "--onefile", "--noconfirm", "--clean",
        f"--name={binary_name}",
        f"--distpath={RELEASE_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={BUILD_DIR}",
    ]

    cmd += get_icon_args()

    for src, dst in get_data_dirs():
        cmd.append(f"--add-data={src}{separator}{dst}")

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    cmd.append(entry_point)

    start = time.time()
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.time() - start

    if res.returncode == 0 and os.path.isfile(raw_output_path):
        archive_file = create_portable_package("Windows-x64", raw_output_path)

        # Clean temporary raw output file outside folder
        if os.path.exists(raw_output_path):
            os.remove(raw_output_path)

        size = file_size_mb(archive_file)
        print(f"\n[SUCCESS] Windows portable package built in {elapsed:.1f}s")
        print(f"          -> Archive: {archive_file} ({size:.1f} MB)")
        return True
    else:
        print(f"\n[FAILED] Windows build failed (exit code {res.returncode})")
        return False

# ---------------------------------------------------------------------------
# Release Validation & Report
# ---------------------------------------------------------------------------

def validate_release():
    """Validates generated release directory structure and lists ready distribution files."""
    print("\n" + "=" * 60)
    print("  PORTABLE RELEASE DISTRIBUTION SUMMARY")
    print("=" * 60)

    if not os.path.isdir(RELEASE_DIR):
        print("[!] release_output/ directory not found.")
        return

    items = sorted(os.listdir(RELEASE_DIR))
    if not items:
        print("[!] No distribution packages found in release_output/")
        return

    print(f"\n  {'Item Name':<48} {'Type':<12} {'Size':>10}")
    print("  " + "-" * 72)

    for name in items:
        p = os.path.join(RELEASE_DIR, name)
        if os.path.isfile(p):
            size = file_size_mb(p)
            print(f"  {name:<48} {'Archive':<12} {size:>8.1f} MB")
        elif os.path.isdir(p):
            # Calculate total directory size
            total_b = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, filenames in os.walk(p) for f in filenames)
            size = total_b / (1024 * 1024)
            print(f"  {name + '/':<48} {'Directory':<12} {size:>8.1f} MB")

    print("\n  Output Directory: " + RELEASE_DIR)
    print("==============================================================\n")

# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

def parse_args():
    args = {
        "linux_only": False,
        "windows_only": False,
        "clean_only": False,
    }
    for arg in sys.argv[1:]:
        arg_l = arg.lower().strip("-")
        if arg_l == "linux-only":
            args["linux_only"] = True
        elif arg_l == "windows-only":
            args["windows_only"] = True
        elif arg_l == "clean-only":
            args["clean_only"] = True
    return args


def build_all():
    args = parse_args()

    print("╔" + "═" * 58 + "╗")
    print("║  AuraTool-Suite — Portable Desktop Distribution Builder  ║")
    print("╚" + "═" * 58 + "╝\n")

    clean_build_artifacts()
    os.makedirs(RELEASE_DIR, exist_ok=True)

    if args["clean_only"]:
        print("[+] Clean-only execution finished.")
        return

    hidden_imports = get_all_hidden_imports()
    entry_point = get_entry_point()

    linux_ok = False
    windows_ok = False

    if not args["windows_only"]:
        linux_ok = build_linux(entry_point, hidden_imports)

    if not args["linux_only"]:
        windows_ok = build_windows_wine(entry_point, hidden_imports)

    clean_build_artifacts()
    validate_release()

    if not linux_ok and not windows_ok:
        sys.exit(1)


if __name__ == "__main__":
    build_all()
