#!/usr/bin/env python3
"""
AuraTool-Suite — Standalone Windows Build Script
==================================================
Builds a portable Windows x64 package with PyInstaller.

Usage (on Windows):
    python build_windows.py

Output goes to release_output/AuraTool-Suite-v{VERSION}-Windows-x64/
"""

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

MODULE_DIRS = ["core", "modules", "drivers", "ui"]
DATA_DIRS = ["languages", "assets"]

BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
RELEASE_DIR = PROJECT_ROOT / "release_output"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg, level="INFO"):
    prefix = {"INFO": "ℹ️ ", "OK": "✅", "WARN": "⚠️ ", "ERR": "❌", "STEP": "🔹"}
    print(f"  {prefix.get(level, '  ')} {msg}")


def run_cmd(cmd, cwd=None):
    print(f"    $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=True)
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
        if py_file.name in (ENTRY_POINT, "build.py", "build_windows.py",
                            "generate_icon.py", "setup.py"):
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


def ensure_icon():
    ico = PROJECT_ROOT / "assets" / "icon.ico"
    gen_script = PROJECT_ROOT / "generate_icon.py"
    if ico.exists():
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


# ---------------------------------------------------------------------------
# Windows Build
# ---------------------------------------------------------------------------

def build_windows():
    log("═" * 55)
    log(f"  Building {APP_NAME} for Windows x64")
    log("═" * 55)
    print()

    # 1. Generate icon
    ensure_icon()

    # 2. Clean previous builds
    log("Cleaning previous build artifacts...", "STEP")
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d)
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()
    log("Clean complete")

    # 3. Build with PyInstaller
    log("Running PyInstaller (Windows onedir mode)...", "STEP")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--noconsole",
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(PROJECT_ROOT),
    ]

    # Icon
    ico_icon = PROJECT_ROOT / "assets" / "icon.ico"
    if ico_icon.exists():
        cmd.extend(["--icon", str(ico_icon)])

    # Data
    separator = ";"  # Windows uses semicolon
    for src, dest in discover_data_dirs():
        cmd.extend(["--add-data", f"{src}{separator}{dest}"])

    # Hidden imports
    for mod in discover_modules():
        cmd.extend(["--hidden-import", mod])

    cmd.append(str(PROJECT_ROOT / ENTRY_POINT))
    run_cmd(cmd)

    # 4. Package
    log("Creating release package...", "STEP")
    win_dist = DIST_DIR / APP_NAME
    if not win_dist.exists():
        log(f"Build output not found at {win_dist}", "ERR")
        sys.exit(1)

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

    # Create .desktop-like shortcut info
    readme_shortcut = release_path / "README.txt"
    if not readme_shortcut.exists():
        readme_shortcut.write_text(textwrap.dedent(f"""\
        AuraTool-Suite v{APP_VERSION} — Windows Portable Edition
        ======================================================

        To run: Double-click AuraTool-Suite.exe
        To install: Copy the entire folder to your preferred location.

        Requirements:
          - Windows 10/11 x64
          - USB device drivers for target devices

        License: See license agreement included with the application.
        """))

    # 5. Create ZIP archive
    log("Creating ZIP archive...", "STEP")
    archive_base = str(RELEASE_DIR / release_name)
    shutil.make_archive(archive_base, "zip", RELEASE_DIR, release_name)
    archive_path = Path(archive_base + ".zip")

    # Summary
    exe_path = release_path / f"{APP_NAME}.exe"
    print()
    log("Build complete!", "OK")
    if exe_path.exists():
        exe_size = exe_path.stat().st_size / (1024 * 1024)
        log(f"  Executable: {exe_path} ({exe_size:.1f} MB)")
    log(f"  Archive:    {archive_path}")
    log(f"  Release:    {release_path}/")
    print()


if __name__ == "__main__":
    if platform.system() != "Windows":
        print("⚠️  This script is designed for native Windows builds.")
        print("   For Linux builds, use: python build.py --linux-only")
        print("   For cross-compilation, use: python build.py")
        print()
        resp = input("Continue anyway? [y/N] ").strip().lower()
        if resp != "y":
            sys.exit(0)
    build_windows()
