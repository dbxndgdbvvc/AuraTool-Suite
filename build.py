#!/usr/bin/env python3
"""
AuraTool-Suite — Dual-Platform Release Builder
================================================
Builds standalone, single-file executables for Linux and Windows
from a single Ubuntu/Linux host using PyInstaller and Wine. All binaries
are placed into a dedicated release_output/ directory — zero workspace clutter.

Features:
  - Uses custom auratool.spec for build configuration
  - Auto-discovers all Python modules in core/, modules/, drivers/, ui/
  - Builds native Linux binary (--onefile, --strip) optimized for Ubuntu
  - Builds Windows .exe (--onefile) via Wine + Windows Python cross-compilation
  - Creates portable release packages with docs, icons, and desktop integration
  - Generates clean archives: .tar.gz (Linux) and .zip (Windows)
  - Full cleanup of temporary build artifacts after each build

Usage:
    python3 build.py                 # Build both Linux + Windows
    python3 build.py --linux-only    # Linux package only
    python3 build.py --windows-only  # Windows package only
    python3 build.py --clean-only    # Clean all build directories only
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

# ============================================================================
# Project Layout & Metadata
# ============================================================================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.join(PROJECT_ROOT, "release_output")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
SPEC_FILE = os.path.abspath(os.path.join(PROJECT_ROOT, "auratool.spec"))

APP_NAME = "AuraTool-Suite"
VERSION = "2.0.0"

PACKAGE_DIRS = ["core", "modules", "drivers", "ui"]
TOP_LEVEL_SCRIPTS = ["auratool_factory", "main"]

DATA_DIRS = [
    ("languages", "languages"),
    ("ui", "ui"),
    ("assets", "assets"),
]

README_TEXT = f"""{'=' * 80}
  AuraTool-Suite v{VERSION} — Universal Mobile Maintenance & Repair Framework
{'=' * 80}

Thank you for choosing AuraTool-Suite.

QUICK START
-----------
  Linux:    ./AuraTool-Suite
  Windows:  Double-click AuraTool-Suite.exe

LICENSE ACTIVATION
------------------
  On first startup, enter your license key in the activation bar.
  Supported tiers:
    - 15-Day Free Trial (auto-activated)
    - 6-Month Professional (AT-6M-...)
    - 1-Year Ultimate VIP (AT-1Y-...)

USB DRIVERS
-----------
  Ensure drivers are installed for your target devices:
    - Samsung Odin / Download mode
    - Qualcomm EDL 9008
    - MediaTek BROM / Meta mode
    - ADB / Fastboot

FEATURES
--------
  - Universal Firmware Flashing & Partition Recovery
  - Automated FRP & Cloud Account Bypass
  - System Bootloop, Black Screen & Virus Removal
  - Deep Data Recovery (Photos, SMS, Contacts)
  - Workshop Ticket & Client Inventory Management
  - AI-Powered Diagnostic Assistant
  - Multi-Vendor Smart Device Support (Samsung, Apple, Xiaomi, Huawei, etc.)
  - AR/VR & Wearable Device Maintenance
  - E-Commerce Spare Parts Store

{'=' * 80}
"""

INSTALL_DESKTOP_TEXT = r"""#!/bin/bash
# AuraTool-Suite — Linux Desktop Integration Installer
# Installs the application launcher, icons, and desktop entry.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="auratool-suite"

if [ -w /usr/local ]; then
    INSTALL_PREFIX="/usr/local"
elif [ -w "$HOME/.local" ]; then
    INSTALL_PREFIX="$HOME/.local"
else
    echo "[!] Cannot write to /usr/local or ~/.local"
    echo "    Try: sudo ./install-desktop.sh"
    exit 1
fi

echo ""
echo "  AuraTool-Suite — Desktop Integration Installer"
echo "  ================================================"
echo "  Install prefix: $INSTALL_PREFIX"
echo ""

echo "[1/4] Installing binary..."
cp "$SCRIPT_DIR/AuraTool-Suite" "$INSTALL_PREFIX/bin/AuraTool-Suite"
chmod +x "$INSTALL_PREFIX/bin/AuraTool-Suite"
echo "  -> $INSTALL_PREFIX/bin/AuraTool-Suite"

echo ""
echo "[2/4] Installing icons..."
if [ -d "$SCRIPT_DIR/icons" ]; then
    for size_dir in "$SCRIPT_DIR/icons"/*/; do
        if [ -d "$size_dir" ]; then
            size=$(basename "$size_dir")
            icon_dir="$INSTALL_PREFIX/share/icons/hicolor/$size/apps"
            mkdir -p "$icon_dir"
            if [ -f "$size_dir/${APP_NAME}.png" ]; then
                cp "$size_dir/${APP_NAME}.png" "$icon_dir/${APP_NAME}.png"
                echo "  -> $icon_dir/${APP_NAME}.png"
            fi
        fi
    done
fi

if [ -f "$SCRIPT_DIR/icon.png" ]; then
    mkdir -p "$INSTALL_PREFIX/share/icons/hicolor/scalable/apps"
    cp "$SCRIPT_DIR/icon.png" "$INSTALL_PREFIX/share/icons/hicolor/scalable/apps/${APP_NAME}.png"
    echo "  -> scalable/${APP_NAME}.png"
fi

echo ""
echo "[3/4] Installing desktop entry..."
DESKTOP_DIR="$INSTALL_PREFIX/share/applications"
mkdir -p "$DESKTOP_DIR"

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
echo "  -> $DESKTOP_DIR/${APP_NAME}.desktop"

echo ""
echo "[4/4] Updating icon cache..."
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "$INSTALL_PREFIX/share/icons/hicolor" 2>/dev/null || true
    echo "  -> Icon cache updated"
fi
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    echo "  -> Desktop database updated"
fi

echo ""
echo "  ================================================"
echo "  Installation complete!"
echo "  Launch from application menu or run:"
echo "    $INSTALL_PREFIX/bin/AuraTool-Suite"
echo "  ================================================"
echo ""
"""

def discover_packages(base_dirs: list[str]) -> list[str]:
    modules: list[str] = []
    seen: set[str] = set()

    for base in base_dirs:
        pkg_path = os.path.join(PROJECT_ROOT, base)
        if not os.path.isdir(pkg_path):
            continue

        if base not in seen:
            modules.append(base)
            seen.add(base)

        for root, dirs, files in os.walk(pkg_path):
            dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]
            for f in files:
                if f.endswith(".py") and f != "__init__.py":
                    rel = os.path.relpath(os.path.join(root, f), PROJECT_ROOT)
                    mod = rel.replace(os.sep, ".").replace("/", ".")
                    if mod.endswith(".py"):
                        mod = mod[:-3]
                    if mod not in seen:
                        seen.add(mod)
                        modules.append(mod)

    return modules

def get_all_hidden_imports() -> list[str]:
    discovered = discover_packages(PACKAGE_DIRS)
    for script in TOP_LEVEL_SCRIPTS:
        if os.path.isfile(os.path.join(PROJECT_ROOT, f"{script}.py")):
            if script not in discovered:
                discovered.append(script)
    return discovered

def get_entry_point() -> str:
    candidates = [
        os.path.join(PROJECT_ROOT, "main.py"),
        os.path.join(PROJECT_ROOT, "ui", "app.py"),
        os.path.join(PROJECT_ROOT, "auratool_factory.py"),
    ]
    for ep in candidates:
        if os.path.isfile(ep):
            return ep
    print("[FATAL] No entry point found in project root.")
    sys.exit(1)

def get_data_args(separator: str) -> list[str]:
    args: list[str] = []
    for src_subdir, bundle_name in DATA_DIRS:
        abs_src = os.path.join(PROJECT_ROOT, src_subdir)
        if os.path.isdir(abs_src):
            args.append(f"--add-data={abs_src}{separator}{bundle_name}")
    return args

def get_icon_args() -> list[str]:
    icon = os.path.join(PROJECT_ROOT, "assets", "icon.ico")
    if os.path.isfile(icon):
        return [f"--icon={icon}"]
    return []

def clean_build_artifacts():
    print("[*] Cleaning temporary build artifacts...")
    for d in [BUILD_DIR, DIST_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
            print(f"    Removed: {os.path.basename(d)}/")

    for spec in glob.glob(os.path.join(PROJECT_ROOT, "*.spec")):
        if os.path.abspath(spec) != os.path.abspath(SPEC_FILE):
            try:
                os.remove(spec)
                print(f"    Removed temp spec: {os.path.basename(spec)}")
            except OSError:
                pass

    for root, dirs, _files in os.walk(PROJECT_ROOT):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)

    print("[+] Workspace clean complete.\n")

def ensure_pyinstaller():
    try:
        import PyInstaller
        print(f"[*] PyInstaller {PyInstaller.__version__} ready.")
        return
    except ImportError:
        pass

    for venv_name in ("venv", ".venv"):
        venv_python = os.path.join(PROJECT_ROOT, venv_name, "bin", "python")
        if os.path.isfile(venv_python):
            try:
                res = subprocess.run(
                    [venv_python, "-c", "import PyInstaller; print(PyInstaller.__version__)"],
                    capture_output=True, text=True, timeout=10,
                )
                if res.returncode == 0:
                    print(f"[*] PyInstaller {res.stdout.strip()} found in {venv_name}/")
                    return
            except Exception:
                pass

    print("[!] PyInstaller not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def find_wine_python() -> tuple[str | None, str | None]:
    wine_bin = shutil.which("wine64") or shutil.which("wine")
    if not wine_bin:
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
            return wine_bin, py

    try:
        res = subprocess.run(
            [wine_bin, "python", "--version"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
        )
        if res.returncode == 0:
            return wine_bin, "python"
    except Exception:
        pass

    return wine_bin, None

def file_size_mb(path: str) -> float:
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except OSError:
        return 0.0

def dir_size_mb(path: str) -> float:
    total = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, files in os.walk(path)
        for f in files
    )
    return total / (1024 * 1024)

def create_portable_package(platform_name: str, binary_path: str) -> str:
    pkg_folder_name = f"{APP_NAME}-v{VERSION}-{platform_name}"
    pkg_dir = os.path.join(RELEASE_DIR, pkg_folder_name)

    if os.path.exists(pkg_dir):
        shutil.rmtree(pkg_dir, ignore_errors=True)
    os.makedirs(pkg_dir, exist_ok=True)

    binary_dest = os.path.join(pkg_dir, os.path.basename(binary_path))
    shutil.copy2(binary_path, binary_dest)
    if platform_name.startswith("Linux"):
        os.chmod(binary_dest, 0o755)

    with open(os.path.join(pkg_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(README_TEXT)

    is_linux = platform_name.startswith("Linux")
    if is_linux:
        desktop_src = os.path.join(PROJECT_ROOT, "assets", "auratool-suite.desktop")
        if os.path.isfile(desktop_src):
            shutil.copy2(desktop_src, os.path.join(pkg_dir, "auratool-suite.desktop"))

        icons_src = os.path.join(PROJECT_ROOT, "assets", "icons")
        if os.path.isdir(icons_src):
            icons_dst = os.path.join(pkg_dir, "icons")
            shutil.copytree(icons_src, icons_dst)

        icon_png = os.path.join(PROJECT_ROOT, "assets", "icon.png")
        if os.path.isfile(icon_png):
            shutil.copy2(icon_png, os.path.join(pkg_dir, "icon.png"))

        install_script = os.path.join(pkg_dir, "install-desktop.sh")
        with open(install_script, "w", encoding="utf-8") as f:
            f.write(INSTALL_DESKTOP_TEXT)
        os.chmod(install_script, 0o755)

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

def build_linux(entry_point: str, hidden_imports: list[str]) -> bool:
    print("=" * 62)
    print("  BUILDING: Native Linux Binary (--onefile, --strip)")
    print("=" * 62)

    ensure_pyinstaller()
    os.makedirs(RELEASE_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

    binary_name = APP_NAME
    raw_output = os.path.join(RELEASE_DIR, binary_name)

    if os.path.isfile(SPEC_FILE):
        print(f"  Using spec file: {os.path.basename(SPEC_FILE)}")
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--clean",
            f"--distpath={RELEASE_DIR}",
            f"--workpath={BUILD_DIR}",
            SPEC_FILE
        ]
    else:
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
        for arg in get_data_args(":"):
            cmd.append(arg)
        for imp in hidden_imports:
            cmd.extend(["--hidden-import", imp])
        if platform.system() != "Windows":
            cmd.append("--strip")
        cmd.append(entry_point)

    start = time.time()
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.time() - start

    if res.returncode == 0 and os.path.isfile(raw_output):
        os.chmod(raw_output, 0o755)
        archive = create_portable_package("Linux-x64", raw_output)
        if os.path.exists(raw_output):
            os.remove(raw_output)
        size = file_size_mb(archive)
        print(f"\n  [SUCCESS] Linux build completed in {elapsed:.1f}s")
        print(f"            Archive: {archive}")
        print(f"            Size:    {size:.1f} MB")
        return True
    else:
        print(f"\n  [FAILED] Linux build failed (exit code {res.returncode})")
        return False

def build_windows(entry_point: str, hidden_imports: list[str]) -> bool:
    print("=" * 62)
    print("  BUILDING: Windows .exe via Wine (--onefile)")
    print("=" * 62)

    wine_bin, wine_python = find_wine_python()

    if not wine_python:
        print("\n  [!] Wine or Windows Python not found on this system.")
        return False

    os.makedirs(RELEASE_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

    binary_name = f"{APP_NAME}.exe"
    raw_output = os.path.join(RELEASE_DIR, binary_name)

    cmd = [
        wine_bin, wine_python, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        f"--name={binary_name}",
        f"--distpath={RELEASE_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={BUILD_DIR}",
    ]
    cmd += get_icon_args()
    for arg in get_data_args(";"):
        cmd.append(arg)
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])
    cmd.append(entry_point)

    start = time.time()
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.time() - start

    if res.returncode == 0 and os.path.isfile(raw_output):
        archive = create_portable_package("Windows-x64", raw_output)
        if os.path.exists(raw_output):
            os.remove(raw_output)
        size = file_size_mb(archive)
        print(f"\n  [SUCCESS] Windows build completed in {elapsed:.1f}s")
        print(f"            Archive: {archive}")
        print(f"            Size:    {size:.1f} MB")
        return True
    else:
        print(f"\n  [FAILED] Windows build failed (exit code {res.returncode})")
        return False

def validate_release():
    print("\n" + "=" * 62)
    print("  RELEASE DISTRIBUTION SUMMARY")
    print("=" * 62)

    if not os.path.isdir(RELEASE_DIR):
        print("  [!] release_output/ directory not found.")
        return

    items = sorted(os.listdir(RELEASE_DIR))
    if not items:
        print("  [!] No release packages found.")
        return

    print(f"\n  {'Item':<50} {'Type':<12} {'Size':>10}")
    print("  " + "-" * 74)

    for name in items:
        p = os.path.join(RELEASE_DIR, name)
        if os.path.isfile(p):
            size = file_size_mb(p)
            ftype = "Archive"
            if name.endswith(".tar.gz"):
                ftype = "tar.gz"
            elif name.endswith(".zip"):
                ftype = "zip"
            print(f"  {name:<50} {ftype:<12} {size:>8.1f} MB")
        elif os.path.isdir(p):
            size = dir_size_mb(p)
            print(f"  {name + '/':<50} {'Directory':<12} {size:>8.1f} MB")

    print(f"\n  Output directory: {RELEASE_DIR}\n" + "=" * 62)

def parse_args() -> dict:
    args = {
        "linux_only": False,
        "windows_only": False,
        "clean_only": False,
    }
    for arg in sys.argv[1:]:
        normalized = arg.lower().lstrip("-")
        if normalized == "linux-only":
            args["linux_only"] = True
        elif normalized == "windows-only":
            args["windows_only"] = True
        elif normalized == "clean-only":
            args["clean_only"] = True
    return args

def main():
    args = parse_args()

    print("\n" + "=" * 62)
    print(f"  {APP_NAME} — Dual-Platform Release Builder v{VERSION}")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print("=" * 62 + "\n")

    clean_build_artifacts()
    os.makedirs(RELEASE_DIR, exist_ok=True)

    if args["clean_only"]:
        print("[+] Clean-only mode — all build artifacts removed.")
        return

    hidden_imports = get_all_hidden_imports()
    entry_point = get_entry_point()

    linux_ok = False
    windows_ok = False

    if not args["windows_only"]:
        linux_ok = build_linux(entry_point, hidden_imports)
        clean_build_artifacts()

    if not args["linux_only"]:
        windows_ok = build_windows(entry_point, hidden_imports)
        clean_build_artifacts()

    validate_release()

    if not linux_ok and not windows_ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
