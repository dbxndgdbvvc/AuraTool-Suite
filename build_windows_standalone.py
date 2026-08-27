#!/usr/bin/env python3
"""
AuraTool-Suite — Standalone Windows Build Script
=================================================
Run this script on a Windows machine to build AuraTool-Suite.exe

Requirements:
    pip install pyinstaller pyyaml arabic-reshaper python-bidi fpdf Pillow psutil

Usage:
    python build_windows_standalone.py              # Build Windows .exe
    python build_windows_standalone.py --clean      # Clean and rebuild
    python build_windows_standalone.py --onefile    # Single .exe file
"""

import argparse
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from datetime import datetime

# ============================================================================
# Constants
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "AuraTool-Suite"
APP_VERSION = "3.0.0"
ENTRY_POINT = "main.py"
MODULE_DIRS = ["core", "modules", "drivers", "ui"]
DATA_DIRS = ["languages", "assets"]

BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
RELEASE_DIR = PROJECT_ROOT / "release_output"


# ============================================================================
# Helpers
# ============================================================================

def log(msg, level="INFO"):
    prefix = {"INFO": "ℹ️ ", "OK": "✅", "WARN": "⚠️ ", "ERR": "❌", "STEP": "🔹"}
    print(f"  {prefix.get(level, '  ')} {msg}")


def run_cmd(cmd, cwd=None, check=True):
    print(f"    $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=check)
    return result


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
        if py_file.name in (ENTRY_POINT, "build.py", "build_all.py",
                            "build_windows.py", "generate_icon.py",
                            "build_windows_standalone.py"):
            continue
        if py_file.name.startswith("_"):
            continue
        hidden.append(py_file.stem)
    return hidden


def discover_data_dirs():
    data = []
    for d in DATA_DIRS:
        src = PROJECT_ROOT / d
        if src.is_dir() and any(src.iterdir()):
            data.append((str(src), d))
    return data


def clean_build():
    log("Cleaning build artifacts...", "STEP")
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d)
            log(f"Removed {d.name}/")
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()
        log(f"Removed {spec.name}")
    log("Clean complete", "OK")


# ============================================================================
# Windows Build
# ============================================================================

def build_windows(onefile=False):
    log("=" * 55)
    log(f"  Building {APP_NAME} for Windows x64")
    log("=" * 55)

    hidden = discover_modules()
    data_entries = discover_data_dirs()

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--noconsole",
    ]

    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    cmd.extend([
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / "windows"),
        "--specpath", str(PROJECT_ROOT),
    ])

    # Icon
    ico_icon = PROJECT_ROOT / "assets" / "icon.ico"
    if ico_icon.exists():
        cmd.extend(["--icon", str(ico_icon)])

    # Data
    for src, dest in data_entries:
        cmd.extend(["--add-data", f"{src};{dest}"])

    # Hidden imports
    for mod in hidden:
        cmd.extend(["--hidden-import", mod])

    # Entry point
    cmd.append(str(PROJECT_ROOT / ENTRY_POINT))

    log("Running PyInstaller (Windows)...", "STEP")
    result = run_cmd(cmd, check=False)

    if result.returncode != 0:
        log("Windows build FAILED", "ERR")
        return False

    return package_windows()


def package_windows():
    win_dist = DIST_DIR / APP_NAME
    if not win_dist.exists():
        win_dist = DIST_DIR / APP_NAME
        if not win_dist.exists():
            log("Windows build output not found", "ERR")
            return False

    log("Creating Windows release package...", "STEP")
    release_name = f"{APP_NAME}-v{APP_VERSION}-Windows-x64"
    release_path = RELEASE_DIR / release_name
    RELEASE_DIR.mkdir(exist_ok=True)

    if release_path.exists():
        shutil.rmtree(release_path)

    shutil.copytree(win_dist, release_path)

    # Copy supporting files
    for fname in ["README.txt"]:
        src = PROJECT_ROOT / fname
        if src.exists():
            shutil.copy2(src, release_path / fname)

    # Create README if not exists
    readme = release_path / "README.txt"
    if not readme.exists():
        readme.write_text(f"""{APP_NAME} v{APP_VERSION} — Windows Portable Edition
{'='*50}

To run: Double-click AuraTool-Suite.exe
To install: Copy the entire folder to your preferred location.

Requirements:
  - Windows 10/11 x64
  - USB device drivers for target devices

License: See license agreement included with the application.

Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
""")

    # Copy icons
    icons_src = PROJECT_ROOT / "assets" / "icons"
    if icons_src.is_dir():
        icons_dst = release_path / "icons"
        shutil.copytree(icons_src, icons_dst, dirs_exist_ok=True)

    # Create ZIP
    log("Creating ZIP archive...", "STEP")
    zip_path = RELEASE_DIR / f"{release_name}.zip"
    shutil.make_archive(
        str(zip_path.with_suffix("")),
        "zip",
        RELEASE_DIR,
        release_name,
    )

    exe_path = release_path / f"{APP_NAME}.exe"
    if exe_path.exists():
        exe_size = exe_path.stat().st_size / (1024 * 1024)
        log(f"Windows build complete!", "OK")
        log(f"  Executable: {exe_path} ({exe_size:.1f} MB)")
    else:
        log(f"Windows build complete (directory mode)", "OK")
    log(f"  Archive:    {zip_path}")
    log(f"  Release:    {release_path}/")
    return True


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description=f"Build {APP_NAME} for Windows")
    parser.add_argument("--clean", action="store_true", help="Clean and rebuild")
    parser.add_argument("--onefile", action="store_true", help="Build as single .exe file")
    parser.add_argument("--version", default=APP_VERSION, help=f"Version (default: {APP_VERSION})")
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print(f"║  {APP_NAME} — Windows Build System                      ║")
    print(f"║  Version {args.version}                                       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    if args.clean:
        clean_build()

    success = build_windows(onefile=args.onefile)

    if success:
        print()
        log("Windows build completed successfully!", "OK")
        log(f"Output: {RELEASE_DIR}/")
    else:
        print()
        log("Windows build failed. Check errors above.", "ERR")
        sys.exit(1)


if __name__ == "__main__":
    main()
