#!/usr/bin/env python3
"""
AuraTool-Suite — Dual-Platform Release Builder
================================================
Builds standalone, single-file executables for Linux and Windows
from a single Ubuntu/Linux host. All binaries are placed into a
dedicated release_output/ directory — zero workspace clutter.

Features:
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

APP_NAME = "AuraTool-Suite"
VERSION = "2.0.0"

# Package directories to scan for hidden imports
PACKAGE_DIRS = ["core", "modules", "drivers", "ui"]

# Top-level scripts that may not be in a package but should be bundled
TOP_LEVEL_SCRIPTS = ["auratool_factory", "main"]

# Data directories to bundle via --add-data (source_subdir, bundle_name)
DATA_DIRS = [
    ("languages", "languages"),
    ("ui", "ui"),
    ("assets", "assets"),
]

# ============================================================================
# Embedded Documentation
# ============================================================================

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
#
# Usage:  chmod +x install-desktop.sh && ./install-desktop.sh

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


# ============================================================================
# Auto-Discovery: Modules & Hidden Imports
# ============================================================================

def discover_packages(base_dirs: list[str]) -> list[str]:
    """Walk each package directory and return fully-qualified module paths."""
    modules: list[str] = []
    seen: set[str] = set()

    for base in base_dirs:
        pkg_path = os.path.join(PROJECT_ROOT, base)
        if not os.path.isdir(pkg_path):
            continue

        # Always include the package itself
        if base not in seen:
            modules.append(base)
            seen.add(base)

        for root, dirs, files in os.walk(pkg_path):
            # Skip pycache and hidden dirs
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
    """Build the complete list of hidden imports by scanning the project."""
    discovered = discover_packages(PACKAGE_DIRS)

    # Include top-level scripts
    for script in TOP_LEVEL_SCRIPTS:
        if os.path.isfile(os.path.join(PROJECT_ROOT, f"{script}.py")):
            if script not in discovered:
                discovered.append(script)

    return discovered


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
    print("[FATAL] No entry point found in project root.")
    sys.exit(1)


def get_data_args(separator: str) -> list[str]:
    """Build --add-data arguments for data directories that exist.

    Uses absolute source paths so PyInstaller can find them regardless
    of where the spec file is located.
    """
    args: list[str] = []
    for src_subdir, bundle_name in DATA_DIRS:
        abs_src = os.path.join(PROJECT_ROOT, src_subdir)
        if os.path.isdir(abs_src):
            args.append(f"--add-data={abs_src}{separator}{bundle_name}")
    return args


def get_icon_args() -> list[str]:
    """Return --icon argument if assets/icon.ico exists."""
    icon = os.path.join(PROJECT_ROOT, "assets", "icon.ico")
    if os.path.isfile(icon):
        return [f"--icon={icon}"]
    return []


# ============================================================================
# Workspace Cleaning & Tool Detection
# ============================================================================

def clean_build_artifacts():
    """Remove temporary build directories and spec files."""
    print("[*] Cleaning build artifacts...")
    for d in [BUILD_DIR, DIST_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
            print(f"    Removed: {os.path.basename(d)}/")

    for spec in glob.glob(os.path.join(PROJECT_ROOT, "*.spec")):
        try:
            os.remove(spec)
            print(f"    Removed: {os.path.basename(spec)}")
        except OSError:
            pass

    # Clean pycache directories in the project
    for root, dirs, _files in os.walk(PROJECT_ROOT):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)

    print("[+] Clean complete.\n")


def ensure_pyinstaller():
    """Ensure PyInstaller is available.

    Checks the current interpreter first, then falls back to the project
    venv if one exists (venv/ or .venv/).
    """
    try:
        import PyInstaller
        print(f"[*] PyInstaller {PyInstaller.__version__} ready.")
        return
    except ImportError:
        pass

    # Check for a local venv that has PyInstaller
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
                    print(f"[*] Hint: run with '{venv_python} build.py' for best results.")
                    return
            except Exception:
                pass

    print("[!] PyInstaller not found. Install it:")
    print(f"    python3 -m venv venv && venv/bin/pip install pyinstaller pillow")


def find_wine_python() -> tuple[str | None, str | None]:
    """Locate Wine + Windows Python on a Linux host.

    Returns (wine_binary, python_exe_path) or (None, None).
    """
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

    # Fallback: try generic wine python
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
    """Return file size in MB."""
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except OSError:
        return 0.0


def dir_size_mb(path: str) -> float:
    """Return total directory size in MB."""
    total = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, files in os.walk(path)
        for f in files
    )
    return total / (1024 * 1024)


# ============================================================================
# Packaging & Archiving
# ============================================================================

def create_portable_package(platform_name: str, binary_path: str) -> str:
    """Organize binary and assets into a clean portable package folder
    and produce a compressed archive (tar.gz for Linux, zip for Windows).
    """
    pkg_folder_name = f"{APP_NAME}-v{VERSION}-{platform_name}"
    pkg_dir = os.path.join(RELEASE_DIR, pkg_folder_name)

    # Clean any previous package
    if os.path.exists(pkg_dir):
        shutil.rmtree(pkg_dir, ignore_errors=True)
    os.makedirs(pkg_dir, exist_ok=True)

    # 1. Copy Binary
    binary_dest = os.path.join(pkg_dir, os.path.basename(binary_path))
    shutil.copy2(binary_path, binary_dest)
    if platform_name.startswith("Linux"):
        os.chmod(binary_dest, 0o755)

    # 2. Documentation
    with open(os.path.join(pkg_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(README_TEXT)

    # 3. Platform-specific extras
    is_linux = platform_name.startswith("Linux")
    if is_linux:
        # Desktop entry file
        desktop_src = os.path.join(PROJECT_ROOT, "assets", "auratool-suite.desktop")
        if os.path.isfile(desktop_src):
            shutil.copy2(desktop_src, os.path.join(pkg_dir, "auratool-suite.desktop"))

        # Multi-size icons for Linux icon theme
        icons_src = os.path.join(PROJECT_ROOT, "assets", "icons")
        if os.path.isdir(icons_src):
            icons_dst = os.path.join(pkg_dir, "icons")
            shutil.copytree(icons_src, icons_dst)

        # Scalable icon
        icon_png = os.path.join(PROJECT_ROOT, "assets", "icon.png")
        if os.path.isfile(icon_png):
            shutil.copy2(icon_png, os.path.join(pkg_dir, "icon.png"))

        # Desktop integration installer
        install_script = os.path.join(pkg_dir, "install-desktop.sh")
        with open(install_script, "w", encoding="utf-8") as f:
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


# ============================================================================
# Build: Native Linux (--onefile, --strip)
# ============================================================================

def _find_pyinstaller_python() -> str:
    """Find the Python interpreter that has PyInstaller installed.

    Checks the current interpreter, then project venvs (venv/, .venv/).
    Returns the path to the best Python to use for PyInstaller builds.
    """
    # Try current interpreter first
    try:
        import PyInstaller  # noqa: F401
        return sys.executable
    except ImportError:
        pass

    # Try project venvs
    for venv_name in ("venv", ".venv"):
        venv_python = os.path.join(PROJECT_ROOT, venv_name, "bin", "python")
        if os.path.isfile(venv_python):
            try:
                res = subprocess.run(
                    [venv_python, "-c", "import PyInstaller"],
                    capture_output=True, timeout=10,
                )
                if res.returncode == 0:
                    return venv_python
            except Exception:
                pass

    # Fall back to current interpreter (build will fail with a clear error)
    return sys.executable


def build_linux(entry_point: str, hidden_imports: list[str]) -> bool:
    """Build a native Linux --onefile binary optimized for Ubuntu x64."""
    print("=" * 62)
    print("  BUILDING: Native Linux Binary (--onefile, --strip)")
    print("=" * 62)

    ensure_pyinstaller()
    pyinstaller_python = _find_pyinstaller_python()

    binary_name = APP_NAME
    raw_output = os.path.join(RELEASE_DIR, binary_name)

    cmd = [
        pyinstaller_python, "-m", "PyInstaller",
        "--onefile",
        "--noconfirm",
        "--clean",
        f"--name={binary_name}",
        f"--distpath={RELEASE_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={BUILD_DIR}",
    ]

    # Icon
    cmd += get_icon_args()

    # Data directories
    for arg in get_data_args(":"):
        cmd.append(arg)

    # Hidden imports
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Strip debug symbols to reduce binary size on Linux
    if platform.system() != "Windows":
        cmd.append("--strip")

    cmd.append(entry_point)

    print(f"  Entry point:  {os.path.relpath(entry_point, PROJECT_ROOT)}")
    print(f"  Output:       release_output/{binary_name}")
    print(f"  Hidden mods:  {len(hidden_imports)} modules discovered")
    print(f"  Data dirs:    {', '.join(s for s, _ in DATA_DIRS if os.path.isdir(os.path.join(PROJECT_ROOT, s)))}")
    print()

    start = time.time()
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.time() - start

    if res.returncode == 0 and os.path.isfile(raw_output):
        os.chmod(raw_output, 0o755)

        # Create portable package with docs and desktop integration
        archive = create_portable_package("Linux-x64", raw_output)

        # Remove the raw binary from release_output (archive contains it)
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


# ============================================================================
# Build: Windows via Wine Cross-Compilation (--onefile)
# ============================================================================

def build_windows(entry_point: str, hidden_imports: list[str]) -> bool:
    """Build a Windows .exe via Wine cross-compilation (Linux -> Windows).

    If Wine/Windows Python is not available, provides clear setup instructions.
    """
    print("=" * 62)
    print("  BUILDING: Windows .exe via Wine (--onefile)")
    print("=" * 62)

    wine_bin, wine_python = find_wine_python()

    if not wine_python:
        print()
        print("  [!] Wine or Windows Python not found on this system.")
        print()
        print("  To enable Windows cross-compilation, run:")
        print()
        print("    # 1. Install Wine (i386 + amd64)")
        print("    sudo dpkg --add-architecture i386")
        print("    sudo apt update")
        print("    sudo apt install wine64 wine32")
        print()
        print("    # 2. Download Windows Python installer")
        print("    wget https://www.python.org/ftp/python/3.12.5/python-3.12.5-amd64.exe")
        print()
        print("    # 3. Install Python inside Wine")
        print("    wine python-3.12.5-amd64.exe /quiet InstallAllUsers=1 PrependPath=1")
        print()
        print("    # 4. Install PyInstaller inside Wine Python")
        print("    wine python -m pip install pyinstaller")
        print()
        print("  Then re-run: python3 build.py --windows-only")
        print()
        return False

    print(f"  Wine:   {wine_bin}")
    print(f"  Python: {wine_python}")
    print()

    binary_name = f"{APP_NAME}.exe"
    raw_output = os.path.join(RELEASE_DIR, binary_name)

    # Windows uses ; as path separator inside Wine
    cmd = [
        wine_bin, wine_python, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        f"--name={binary_name}",
        f"--distpath={RELEASE_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={BUILD_DIR}",
    ]

    # Icon
    cmd += get_icon_args()

    # Data directories (Windows separator ; inside Wine)
    for arg in get_data_args(";"):
        cmd.append(arg)

    # Hidden imports
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    cmd.append(entry_point)

    print(f"  Entry point:  {os.path.relpath(entry_point, PROJECT_ROOT)}")
    print(f"  Output:       release_output/{binary_name}")
    print(f"  Hidden mods:  {len(hidden_imports)} modules discovered")
    print()

    start = time.time()
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.time() - start

    if res.returncode == 0 and os.path.isfile(raw_output):
        # Create portable package with docs
        archive = create_portable_package("Windows-x64", raw_output)

        # Remove the raw binary from release_output
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


# ============================================================================
# Release Validation & Summary
# ============================================================================

def validate_release():
    """Print a summary of everything in release_output/."""
    print()
    print("=" * 62)
    print("  RELEASE DISTRIBUTION SUMMARY")
    print("=" * 62)

    if not os.path.isdir(RELEASE_DIR):
        print("  [!] release_output/ directory not found.")
        return

    items = sorted(os.listdir(RELEASE_DIR))
    if not items:
        print("  [!] No release packages found.")
        return

    print()
    print(f"  {'Item':<50} {'Type':<12} {'Size':>10}")
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

    print()
    print(f"  Output directory: {RELEASE_DIR}")
    print("=" * 62)
    print()


# ============================================================================
# Main Orchestrator
# ============================================================================

def parse_args() -> dict:
    """Parse command-line flags."""
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

    print()
    print("=" * 62)
    print(f"  {APP_NAME} — Dual-Platform Release Builder v{VERSION}")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print(f"  Python:   {sys.version.split()[0]}")
    print("=" * 62)
    print()

    # Clean previous artifacts
    clean_build_artifacts()

    # Prepare release output directory
    os.makedirs(RELEASE_DIR, exist_ok=True)

    # Clean-only mode
    if args["clean_only"]:
        print("[+] Clean-only mode — all build artifacts removed.")
        return

    # Discover modules
    hidden_imports = get_all_hidden_imports()
    entry_point = get_entry_point()

    print(f"[*] Project root:   {PROJECT_ROOT}")
    print(f"[*] Entry point:    {os.path.relpath(entry_point, PROJECT_ROOT)}")
    print(f"[*] Hidden imports: {len(hidden_imports)} modules")
    data_found = [s for s, _ in DATA_DIRS if os.path.isdir(os.path.join(PROJECT_ROOT, s))]
    print(f"[*] Data dirs:      {', '.join(data_found) if data_found else '(none)'}")
    icon = os.path.join(PROJECT_ROOT, "assets", "icon.ico")
    print(f"[*] Icon:           {'found' if os.path.isfile(icon) else 'not found'}")
    print()

    # Build targets
    linux_ok = False
    windows_ok = False

    if not args["windows_only"]:
        linux_ok = build_linux(entry_point, hidden_imports)
        # Clean temp artifacts between builds
        clean_build_artifacts()

    if not args["linux_only"]:
        windows_ok = build_windows(entry_point, hidden_imports)
        # Clean temp artifacts
        clean_build_artifacts()

    # Final summary
    validate_release()

    if linux_ok or windows_ok:
        print("  Build completed successfully. Release packages are in release_output/")
    else:
        print("  [!] No builds succeeded.")
        sys.exit(1)


if __name__ == "__main__":
    main()
