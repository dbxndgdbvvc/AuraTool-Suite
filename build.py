#!/usr/bin/env python3
"""
AuraTool-Suite — Main Build Orchestrator
==========================================
Builds standalone native desktop applications for Linux and Windows
using PyInstaller. Generates spec files dynamically, auto-discovers
modules, and packages output into release_output/.

Usage:
    python build.py                    # Build both platforms (Linux native, Windows via Wine)
    python build.py --linux-only       # Linux build only
    python build.py --windows-only     # Windows build only (requires Wine)
    python build.py --skip-windows     # Same as --linux-only
    python build.py --clean-only       # Remove all build artifacts
"""

import argparse
import glob
import os
import platform
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "AuraTool-Suite"
APP_VERSION = "3.0.0"
ENTRY_POINT = "main.py"

# Directories to scan for hidden imports
MODULE_DIRS = ["core", "modules", "drivers", "ui"]

# Data directories to bundle
DATA_DIRS = ["languages", "assets"]

# Build output locations
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
RELEASE_DIR = PROJECT_ROOT / "release_output"
SPEC_FILE = PROJECT_ROOT / "auratool-suite.spec"

# PyInstaller settings
PYINSTALLER_ARGS_BASE = [
    "--noconfirm",
    "--clean",
    "--noconsole",          # No terminal window for GUI app
    "--windowed",           # GUI mode
    "--name", APP_NAME,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg, level="INFO"):
    prefix = {"INFO": "ℹ️ ", "OK": "✅", "WARN": "⚠️ ", "ERR": "❌", "STEP": "🔹"}
    print(f"  {prefix.get(level, '  ')} {msg}")


def run_cmd(cmd, cwd=None, check=True):
    """Run a shell command and stream output."""
    print(f"    $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=check)
    return result


def discover_modules():
    """Scan MODULE_DIRS for Python modules to add as hidden imports."""
    hidden = []
    for mod_dir in MODULE_DIRS:
        dir_path = PROJECT_ROOT / mod_dir
        if not dir_path.is_dir():
            continue
        for py_file in sorted(dir_path.glob("*.py")):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue
            module_name = f"{mod_dir}.{py_file.stem}"
            hidden.append(module_name)
    # Root-level modules
    for py_file in sorted(PROJECT_ROOT.glob("*.py")):
        if py_file.name in (ENTRY_POINT, "build.py", "build_windows.py",
                            "generate_icon.py", "setup.py", "pyproject.toml"):
            continue
        if py_file.name.startswith("_"):
            continue
        hidden.append(py_file.stem)
    return hidden


def discover_data_dirs():
    """Find data directories that exist and should be bundled."""
    data = []
    for d in DATA_DIRS:
        src = PROJECT_ROOT / d
        if src.is_dir() and any(src.iterdir()):
            data.append((str(src), d))
    return data


def ensure_icon():
    """Generate application icon if not present."""
    ico = PROJECT_ROOT / "assets" / "icon.ico"
    png = PROJECT_ROOT / "assets" / "icon.png"
    gen_script = PROJECT_ROOT / "generate_icon.py"

    if ico.exists() and png.exists():
        log("Icon assets already present")
        return True

    if not gen_script.exists():
        log("generate_icon.py not found, skipping icon generation", "WARN")
        return False

    log("Generating application icons...", "STEP")
    try:
        run_cmd([sys.executable, str(gen_script)])
        return True
    except subprocess.CalledProcessError:
        log("Icon generation failed, continuing without custom icon", "WARN")
        return False


def clean_build():
    """Remove all build artifacts."""
    log("Cleaning build artifacts...", "STEP")
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d)
            log(f"Removed {d.name}/")
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()
        log(f"Removed {spec.name}")
    log("Clean complete", "OK")


# ---------------------------------------------------------------------------
# Spec File Generator
# ---------------------------------------------------------------------------

def generate_spec(target_platform="linux"):
    """
    Generate a PyInstaller .spec file for the given target platform.

    Args:
        target_platform: "linux" or "windows"
    """
    hidden = discover_modules()
    data_entries = discover_data_dirs()

    # Icon path
    icon_path = ""
    ico_file = PROJECT_ROOT / "assets" / "icon.ico"
    png_file = PROJECT_ROOT / "assets" / "icon.png"
    if target_platform == "windows" and ico_file.exists():
        icon_path = str(ico_file).replace("\\", "/")
    elif png_file.exists():
        icon_path = str(png_file).replace("\\", "/")

    # Build hidden imports Python list
    hidden_imports_str = ",\n        ".join(f'"{m}"' for m in hidden)

    # Build data list
    data_list = []
    for src, dest in data_entries:
        data_list.append(f'(r"{src}", r"{dest}")')
    data_str = ",\n        ".join(data_list) if data_list else ""

    # Entry point
    entry = str(PROJECT_ROOT / ENTRY_POINT)

    # Determine console setting
    console = "False" if target_platform == "windows" else "True"

    # Determine strip setting (Linux only)
    strip = "True" if target_platform == "linux" else "False"

    # Determine onedir vs onefile
    # Linux: onefile for easy distribution
    # Windows: onedir for portable package
    mode = "onefile" if target_platform == "linux" else "onedir"

    spec_content = textwrap.dedent(f"""\
# -*- mode: python ; coding: utf-8 -*-
# Auto-generated PyInstaller spec file for AuraTool-Suite
# Target platform: {target_platform}

import os
import sys

block_cipher = None

a = Analysis(
    [r'{entry}'],
    pathex=[r'{PROJECT_ROOT}'],
    binaries=[],
    datas=[
        {data_str}
    ] if '{data_str}' else [],
    hiddenimports=[
        {hidden_imports_str}
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'unittest', 'test',
        'distutils', 'setuptools', 'pip', 'wheel',
        'numpy', 'numpy.core', 'numpy.random', 'numpy.linalg',
        'numpy.fft', 'numpy.polynomial',
        'pandas', 'scipy', 'matplotlib', 'matplotlib.pyplot',
        'notebook', 'ipython', 'IPython',
        'pytest', 'py.test', '_pytest',
        'PIL.tests', 'PIL.TiffImagePlugin',
        'pydoc', 'doctest',
        'xmlrpc', 'pyexpat',
        'lib2to3',
        'pdb', 'profile', 'cProfile',
        'email.mime', 'html.parser',
        'pygments', 'colorama',
        'ssl', 'hashlib',  # built into bootloader
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

{'exe = EXE(' if mode == 'onefile' else 'exe = EXE('}
    pyz,
    a.scripts,
    {'' if mode == 'onedir' else 'a.binaries,'}
    {'' if mode == 'onedir' else 'a.zipfiles,'}
    {'' if mode == 'onedir' else 'a.datas,'}
    [],
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip={strip},
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={console},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'{icon_path}' if '{icon_path}' else None,
{')' if mode == 'onefile' else ')'}

{'coll = COLLECT(' if mode == 'onedir' else ''}
{'    exe,' if mode == 'onedir' else ''}
{'    a.binaries,' if mode == 'onedir' else ''}
{'    a.zipfiles,' if mode == 'onedir' else ''}
{'    a.datas,' if mode == 'onedir' else ''}
{'    strip={strip},' if mode == 'onedir' else ''}
{'    upx=True,' if mode == 'onedir' else ''}
{'    upx_exclude=[],' if mode == 'onedir' else ''}
{'    name=APP_NAME,' if mode == 'onedir' else ''}
{');' if mode == 'onedir' else ''}
""")

    spec_path = PROJECT_ROOT / f"auratool-suite-{target_platform}.spec"
    spec_path.write_text(spec_content)
    log(f"Generated spec file: {spec_path.name}")
    return spec_path


# ---------------------------------------------------------------------------
# Linux Build
# ---------------------------------------------------------------------------

def build_linux():
    """Build the Linux x86_64 native binary."""
    log("═" * 55)
    log(f"  Building {APP_NAME} for Linux x86_64")
    log("═" * 55)

    ensure_icon()

    # Generate Linux spec file (onefile mode)
    spec_path = generate_spec("linux")

    # Run PyInstaller
    log("Running PyInstaller (Linux build)...", "STEP")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onefile",
        "--console",         # Keep console for Linux (shows logs)
        "--strip",           # Strip debug symbols to reduce size
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(PROJECT_ROOT),
    ]

    # Add icon
    png_icon = PROJECT_ROOT / "assets" / "icon.png"
    if png_icon.exists():
        cmd.extend(["--icon", str(png_icon)])

    # Add data directories
    for src, dest in discover_data_dirs():
        separator = ";" if platform.system() == "Windows" else ":"
        cmd.extend(["--add-data", f"{src}{separator}{dest}"])

    # Add hidden imports
    for mod in discover_modules():
        cmd.extend(["--hidden-import", mod])

    # Entry point
    cmd.append(str(PROJECT_ROOT / ENTRY_POINT))

    run_cmd(cmd)

    # Locate the built binary
    binary = DIST_DIR / APP_NAME
    if not binary.exists():
        log(f"Binary not found at {binary}", "ERR")
        return False

    # Apply UPX compression to reduce binary size
    upx_path = shutil.which("upx") or str(Path.home() / ".local" / "bin" / "upx")
    if os.path.isfile(upx_path):
        log("Applying UPX compression...", "STEP")
        original_size = binary.stat().st_size / (1024 * 1024)
        try:
            run_cmd([upx_path, "--best", "--lzma", str(binary)])
            compressed_size = binary.stat().st_size / (1024 * 1024)
            saved = original_size - compressed_size
            ratio = (saved / original_size) * 100 if original_size > 0 else 0
            if saved > 0.1:
                log(f"UPX compressed: {original_size:.1f} MB → {compressed_size:.1f} MB (saved {saved:.1f} MB, {ratio:.0f}%)", "OK")
            else:
                log(f"UPX applied but minimal gain ({ratio:.1f}%): PyInstaller onefile is already compressed", "INFO")
        except subprocess.CalledProcessError:
            log("UPX compression failed, keeping uncompressed binary", "WARN")
    else:
        log("UPX not found, skipping compression (install: sudo apt install upx)", "WARN")

    # Create release package
    log("Creating release package...", "STEP")
    release_name = f"{APP_NAME}-v{APP_VERSION}-Linux-x64"
    release_path = RELEASE_DIR / release_name
    RELEASE_DIR.mkdir(exist_ok=True)

    if release_path.exists():
        shutil.rmtree(release_path)
    release_path.mkdir(parents=True)

    # Copy binary
    shutil.copy2(binary, release_path / APP_NAME)
    os.chmod(release_path / APP_NAME, 0o755)

    # Copy supporting files
    for fname in ["README.txt"]:
        src = PROJECT_ROOT / fname
        if src.exists():
            shutil.copy2(src, release_path / fname)

    # Copy desktop file
    desktop_src = PROJECT_ROOT / "assets" / "auratool-suite.desktop"
    if desktop_src.exists():
        shutil.copy2(desktop_src, release_path / "auratool-suite.desktop")

    # Copy icon
    if png_icon.exists():
        shutil.copy2(png_icon, release_path / "icon.png")

    # Copy Linux icons directory
    icons_src = PROJECT_ROOT / "assets" / "icons"
    if icons_src.is_dir():
        icons_dst = release_path / "icons"
        shutil.copytree(icons_src, icons_dst, dirs_exist_ok=True)

    # Create install script
    install_script = release_path / "install-desktop.sh"
    install_script.write_text(textwrap.dedent("""\
#!/bin/bash
# AuraTool-Suite — Desktop Integration Installer
# Installs the application and .desktop file for the current user.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="AuraTool-Suite"
LOCAL_DIR="$HOME/.local"
BIN_DIR="$LOCAL_DIR/bin"
ICON_DIR="$LOCAL_DIR/share/icons"
DESKTOP_DIR="$LOCAL_DIR/share/applications"

echo "Installing $APP_NAME..."

# Copy binary
mkdir -p "$BIN_DIR"
cp "$SCRIPT_DIR/$APP_NAME" "$BIN_DIR/$APP_NAME"
chmod +x "$BIN_DIR/$APP_NAME"
echo "  ✓ Binary installed to $BIN_DIR/$APP_NAME"

# Copy icon
mkdir -p "$ICON_DIR"
cp "$SCRIPT_DIR/icon.png" "$ICON_DIR/auratool-suite.png"
echo "  ✓ Icon installed to $ICON_DIR/auratool-suite.png"

# Copy desktop file
if [ -f "$SCRIPT_DIR/auratool-suite.desktop" ]; then
    mkdir -p "$DESKTOP_DIR"
    cp "$SCRIPT_DIR/auratool-suite.desktop" "$DESKTOP_DIR/"
    # Update Exec path
    sed -i "s|Exec=.*|Exec=$BIN_DIR/$APP_NAME|" "$DESKTOP_DIR/auratool-suite.desktop"
    echo "  ✓ Desktop entry installed to $DESKTOP_DIR/auratool-suite.desktop"
fi

echo ""
echo "$APP_NAME installed successfully!"
echo "Run with: $BIN_DIR/$APP_NAME"
"""))
    install_script.chmod(0o755)

    # Create tar.gz archive
    log("Creating archive...", "STEP")
    archive_path = RELEASE_DIR / f"{release_name}.tar.gz"
    run_cmd([
        "tar", "czf", str(archive_path),
        "-C", str(RELEASE_DIR), release_name
    ])

    # Summary
    binary_size = binary.stat().st_size / (1024 * 1024)
    archive_size = archive_path.stat().st_size / (1024 * 1024)
    log(f"Linux build complete!", "OK")
    log(f"  Binary:     {binary} ({binary_size:.1f} MB)")
    log(f"  Archive:    {archive_path} ({archive_size:.1f} MB)")
    log(f"  Release:    {release_path}/")
    return True


# ---------------------------------------------------------------------------
# Windows Build (via Wine cross-compilation or native)
# ---------------------------------------------------------------------------

def build_windows():
    """Build the Windows x64 portable package."""
    log("═" * 55)
    log(f"  Building {APP_NAME} for Windows x64")
    log("═" * 55)

    # Check if we're on Windows natively or need Wine
    if platform.system() == "Windows":
        return _build_windows_native()
    else:
        return _build_windows_wine()


def _build_windows_native():
    """Build Windows .exe on a native Windows machine."""
    ensure_icon()

    log("Running PyInstaller (Windows native)...", "STEP")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onedir",
        "--noconsole",
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(PROJECT_ROOT),
    ]

    # Add icon
    ico_icon = PROJECT_ROOT / "assets" / "icon.ico"
    if ico_icon.exists():
        cmd.extend(["--icon", str(ico_icon)])

    # Add data directories
    for src, dest in discover_data_dirs():
        cmd.extend(["--add-data", f"{src};{dest}"])

    # Add hidden imports
    for mod in discover_modules():
        cmd.extend(["--hidden-import", mod])

    cmd.append(str(PROJECT_ROOT / ENTRY_POINT))
    run_cmd(cmd)

    # Apply UPX compression to Windows executables
    upx_path = shutil.which("upx") or str(Path.home() / ".local" / "bin" / "upx")
    if os.path.isfile(upx_path):
        log("Applying UPX compression to Windows binaries...", "STEP")
        win_exe = DIST_DIR / APP_NAME / f"{APP_NAME}.exe"
        if win_exe.exists():
            original_size = win_exe.stat().st_size / (1024 * 1024)
            try:
                run_cmd([upx_path, "--best", "--lzma", str(win_exe)])
                compressed_size = win_exe.stat().st_size / (1024 * 1024)
                ratio = (1 - compressed_size / original_size) * 100
                log(f"UPX compressed: {original_size:.1f} MB → {compressed_size:.1f} MB ({ratio:.0f}% reduction)", "OK")
            except subprocess.CalledProcessError:
                log("UPX compression failed, keeping uncompressed binary", "WARN")

    return _package_windows()


def _build_windows_wine():
    """Build Windows .exe via Wine cross-compilation on Linux."""
    # Check Wine availability
    wine = shutil.which("wine64") or shutil.which("wine")
    if not wine:
        log("Wine not found. Install with: sudo apt install wine64", "WARN")
        log("Falling back to native Windows build script reference", "WARN")
        log("Use 'python build_windows.py' on a Windows machine instead.", "WARN")
        return False

    # Check for Wine Python
    try:
        result = subprocess.run(
            [wine, "python", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            log("Windows Python not found in Wine prefix", "WARN")
            log("Install Python in Wine: wine python-3.12.x-amd64.exe /quiet", "WARN")
            return False
        log(f"Wine Python: {result.stdout.strip()}")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        log("Wine Python not available", "WARN")
        return False

    log("Building Windows via Wine cross-compilation...", "STEP")

    # Convert paths for Wine
    wine_root = str(PROJECT_ROOT).replace("/mnt/", "Z:\\\\").replace("/", "\\\\")
    wine_entry = f"{wine_root}\\\\{ENTRY_POINT}"

    # Generate Windows spec file
    spec_path = generate_spec("windows")

    # Run PyInstaller via Wine
    cmd = [
        wine, "python", "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onedir",
        "--noconsole",
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(PROJECT_ROOT),
    ]

    ico_icon = PROJECT_ROOT / "assets" / "icon.ico"
    if ico_icon.exists():
        cmd.extend(["--icon", str(ico_icon)])

    for src, dest in discover_data_dirs():
        cmd.extend(["--add-data", f"{src};{dest}"])

    for mod in discover_modules():
        cmd.extend(["--hidden-import", mod])

    cmd.append(str(PROJECT_ROOT / ENTRY_POINT))
    run_cmd(cmd)

    # Apply UPX compression to Windows executables
    upx_path = shutil.which("upx") or str(Path.home() / ".local" / "bin" / "upx")
    if os.path.isfile(upx_path):
        log("Applying UPX compression to Windows binaries...", "STEP")
        win_exe = DIST_DIR / APP_NAME / f"{APP_NAME}.exe"
        if win_exe.exists():
            original_size = win_exe.stat().st_size / (1024 * 1024)
            try:
                run_cmd([upx_path, "--best", "--lzma", str(win_exe)])
                compressed_size = win_exe.stat().st_size / (1024 * 1024)
                ratio = (1 - compressed_size / original_size) * 100
                log(f"UPX compressed: {original_size:.1f} MB → {compressed_size:.1f} MB ({ratio:.0f}% reduction)", "OK")
            except subprocess.CalledProcessError:
                log("UPX compression failed, keeping uncompressed binary", "WARN")

    return _package_windows()


def _package_windows():
    """Package the Windows build into release_output/."""
    win_dist = DIST_DIR / APP_NAME
    if not win_dist.exists():
        log(f"Windows build output not found at {win_dist}", "ERR")
        return False

    log("Creating Windows release package...", "STEP")
    release_name = f"{APP_NAME}-v{APP_VERSION}-Windows-x64"
    release_path = RELEASE_DIR / release_name
    RELEASE_DIR.mkdir(exist_ok=True)

    if release_path.exists():
        shutil.rmtree(release_path)

    # Copy the entire dist directory
    shutil.copytree(win_dist, release_path)

    # Copy supporting files
    for fname in ["README.txt"]:
        src = PROJECT_ROOT / fname
        if src.exists():
            shutil.copy2(src, release_path / fname)

    # Create zip archive
    log("Creating archive...", "STEP")
    archive_path = RELEASE_DIR / f"{release_name}.zip"
    shutil.make_archive(
        str(archive_path.with_suffix("")),  # without .zip
        "zip",
        RELEASE_DIR,
        release_name,
    )

    # Summary
    exe_path = release_path / f"{APP_NAME}.exe"
    if exe_path.exists():
        exe_size = exe_path.stat().st_size / (1024 * 1024)
        log(f"Windows build complete!", "OK")
        log(f"  Executable: {exe_path} ({exe_size:.1f} MB)")
    else:
        log(f"Windows build complete (directory mode)", "OK")
    log(f"  Archive:    {archive_path}.zip")
    log(f"  Release:    {release_path}/")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global APP_VERSION

    parser = argparse.ArgumentParser(
        description=f"Build {APP_NAME} native desktop applications"
    )
    parser.add_argument("--linux-only", action="store_true",
                        help="Build Linux binary only")
    parser.add_argument("--windows-only", action="store_true",
                        help="Build Windows package only")
    parser.add_argument("--skip-windows", action="store_true",
                        help="Skip Windows build (same as --linux-only)")
    parser.add_argument("--clean-only", action="store_true",
                        help="Remove all build artifacts and exit")
    parser.add_argument("--version", default=APP_VERSION,
                        help=f"Version label (default: {APP_VERSION})")
    args = parser.parse_args()

    # Update global version
    APP_VERSION = args.version

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print(f"║  {APP_NAME} — Build System                              ║")
    print(f"║  Version {APP_VERSION}                                       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    if args.clean_only:
        clean_build()
        return

    # Determine what to build
    build_linux_flag = not args.windows_only
    build_win_flag = not args.linux_only and not args.skip_windows

    results = {}

    if build_linux_flag:
        results["linux"] = build_linux()
        print()

    if build_win_flag:
        results["windows"] = build_windows()
        print()

    # Summary
    print("═" * 55)
    print("  Build Summary")
    print("═" * 55)
    for platform_name, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"  {platform_name:10s}: {status}")

    if all(results.values()):
        print(f"\n  All builds completed successfully!")
        print(f"  Output: {RELEASE_DIR}/")
    else:
        print(f"\n  Some builds failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
