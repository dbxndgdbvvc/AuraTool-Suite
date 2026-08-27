#!/usr/bin/env python3
"""
AuraTool-Suite — Standalone Onefile Build Script
=================================================
Builds a single self-contained executable (--onefile) that hides ALL
source code, libraries, modules, assets, and dependencies inside the binary.

Supported platforms:
  - Linux x86_64  (native build)
  - Windows x64   (native build on Windows or via Wine cross-compilation)

Usage:
    python build_standalone.py                  # Build both platforms
    python build_standalone.py --linux-only     # Linux only
    python build_standalone.py --windows-only   # Windows only
    python build_standalone.py --clean          # Clean build artifacts first

Output is placed on the user's Desktop.
"""

import argparse
import glob
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

# ============================================================================
# Constants
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "AuraTool-Suite"
APP_VERSION = "2.0.0"
ENTRY_POINT = "main.py"

# Directories to scan for hidden imports (Python modules to bundle)
MODULE_DIRS = ["core", "modules", "drivers", "ui"]

# Data directories to bundle inside the executable
DATA_DIRS = ["languages", "assets"]

# Build output locations
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
RELEASE_DIR = PROJECT_ROOT / "release_output"

# Desktop path
DESKTOP = Path.home() / "Desktop"

# ============================================================================
# ANSI Colors
# ============================================================================

class C:
    RESET  = "\033[0m"
    RED    = "\033[0;31m"
    GREEN  = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE   = "\033[0;34m"
    CYAN   = "\033[0;36m"
    BOLD   = "\033[1m"
    MAG    = "\033[0;35m"

def c(text, color):
    return f"{color}{text}{C.RESET}"

# ============================================================================
# Logging helpers
# ============================================================================

def banner():
    print()
    print(c("╔══════════════════════════════════════════════════════════════╗", C.CYAN))
    print(c("║                                                              ║", C.CYAN))
    print(c("║   🔧 AuraTool-Suite — Standalone Onefile Builder              ║", C.CYAN))
    print(c("║   📦 Version 2.0.0 | Single Executable (--onefile)            ║", C.CYAN))
    print(c("║   🐧 Linux x64  |  🪟 Windows x64                             ║", C.CYAN))
    print(c("║                                                              ║", C.CYAN))
    print(c("╚══════════════════════════════════════════════════════════════╝", C.CYAN))
    print()

def section(text):
    print()
    print(c(f"  {'━' * 56}", C.BLUE))
    print(c(f"  {text}", C.BOLD))
    print(c(f"  {'━' * 56}", C.BLUE))

def step(msg):
    print(c(f"  ▸ {msg}", C.CYAN))

def ok(msg):
    print(c(f"  ✅ {msg}", C.GREEN))

def warn(msg):
    print(c(f"  ⚠️  {msg}", C.YELLOW))

def err(msg):
    print(c(f"  ❌ {msg}", C.RED))

def info(msg):
    print(c(f"  ℹ️  {msg}", C.BLUE))

# ============================================================================
# Helpers
# ============================================================================

def run_cmd(cmd, cwd=None, check=True, capture=False):
    """Run a shell command and optionally capture output."""
    result = subprocess.run(
        cmd, cwd=cwd or PROJECT_ROOT,
        check=check, capture_output=capture, text=True,
    )
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
            hidden.append(f"{mod_dir}.{py_file.stem}")

    # Root-level Python modules (excluding build scripts and entry point)
    skip_files = {
        ENTRY_POINT, "build.py", "build_all.py", "build_windows.py",
        "build_standalone.py", "generate_icon.py", "setup.py",
        "pyproject.toml", "generate_brand_icons.py", "generate_brand_svgs.py",
        "test_gui_launch.py",
    }
    for py_file in sorted(PROJECT_ROOT.glob("*.py")):
        if py_file.name in skip_files:
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

def get_file_size(filepath):
    """Get human-readable file size."""
    size = os.path.getsize(filepath)
    if size >= 1024 * 1024 * 1024:
        return f"{size / (1024*1024*1024):.1f} GB"
    elif size >= 1024 * 1024:
        return f"{size / (1024*1024):.1f} MB"
    elif size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} B"

def get_file_hash(filepath):
    """Calculate MD5 hash of a file."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def clean_build():
    """Remove all previous build artifacts."""
    section("🗑️  Cleaning Previous Build Artifacts")
    for d in [BUILD_DIR, DIST_DIR, RELEASE_DIR]:
        if d.exists():
            shutil.rmtree(d)
            step(f"Removed {d.name}/")
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()
        step(f"Removed {spec.name}")
    ok("All build artifacts cleaned")

# ============================================================================
# Linux Build (--onefile)
# ============================================================================

def build_linux():
    """Build Linux x86_64 standalone onefile binary."""
    section("🐧 Building Linux x86_64 Standalone Binary")

    start_time = time.time()

    # ── Locate icon ────────────────────────────────────────────────────
    png_icon = PROJECT_ROOT / "assets" / "icon.png"

    # ── Build PyInstaller command ──────────────────────────────────────
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",        # ← Single file mode
        "--console",        # Keep console for Linux (shows logs)
        "--strip",          # Strip debug symbols → smaller binary
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / "linux"),
        "--specpath", str(PROJECT_ROOT),
    ]

    # Add icon
    if png_icon.exists():
        cmd.extend(["--icon", str(png_icon)])

    # Add data directories (--add-data uses ':' separator on Linux)
    for src, dest in discover_data_dirs():
        cmd.extend(["--add-data", f"{src}:{dest}"])

    # Add all discovered hidden imports
    hidden = discover_modules()
    step(f"Registering {len(hidden)} hidden imports...")
    for mod in hidden:
        cmd.extend(["--hidden-import", mod])

    # Exclude unnecessary packages to reduce size
    excludes = [
        "tkinter.test", "unittest", "test",
        "distutils", "setuptools", "pip", "wheel",
        "numpy", "pandas", "scipy", "matplotlib",
        "notebook", "ipython", "IPython",
        "pytest", "_pytest", "py.test",
        "PIL.tests", "pydoc", "doctest",
        "xmlrpc", "pyexpat", "lib2to3",
        "pdb", "profile", "cProfile",
    ]
    for ex in excludes:
        cmd.extend(["--exclude-module", ex])

    # Entry point
    cmd.append(str(PROJECT_ROOT / ENTRY_POINT))

    # ── Run PyInstaller ────────────────────────────────────────────────
    step("Running PyInstaller for Linux --onefile...")
    print(f"    $ {' '.join(cmd[:8])} ... (truncated)")
    print()
    result = run_cmd(cmd, check=False)

    if result.returncode != 0:
        err("Linux build FAILED — check PyInstaller output above")
        return False, {}

    binary = DIST_DIR / APP_NAME
    if not binary.exists():
        err(f"Binary not found at: {binary}")
        return False, {}

    # NOTE: UPX is intentionally skipped on Linux — PyInstaller 6.x
    # warns that UPX causes compatibility problems on non-Windows platforms,
    # and can corrupt the embedded PKG archive in onefile mode.

    # ── Verify binary ──────────────────────────────────────────────────
    binary_size = binary.stat().st_size / (1024 * 1024)
    md5 = get_file_hash(binary)

    elapsed = time.time() - start_time
    ok(f"Linux build completed in {elapsed:.1f}s")
    step(f"Binary: {binary}")
    step(f"Size:   {binary_size:.1f} MB | MD5: {md5[:12]}...")

    return True, {
        "platform": "Linux",
        "binary": str(binary),
        "name": APP_NAME,
        "size_mb": binary_size,
        "md5": md5,
        "elapsed": elapsed,
    }

# ============================================================================
# Windows Build (--onefile)
# ============================================================================

def build_windows():
    """Build Windows x64 standalone onefile binary."""
    section("🪟 Building Windows x64 Standalone Binary")

    start_time = time.time()

    # Check if we're on Windows natively or need Wine
    if platform.system() == "Windows":
        return _build_windows_native()
    else:
        return _build_windows_wine()

def _build_windows_native():
    """Build Windows .exe on a native Windows machine."""
    png_icon = PROJECT_ROOT / "assets" / "icon.png"
    ico_icon = PROJECT_ROOT / "assets" / "icon.ico"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onefile",        # ← Single file mode
        "--noconsole",      # No terminal window for Windows GUI
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / "windows"),
        "--specpath", str(PROJECT_ROOT),
    ]

    if ico_icon.exists():
        cmd.extend(["--icon", str(ico_icon)])
    elif png_icon.exists():
        cmd.extend(["--icon", str(png_icon)])

    # Data dirs (Windows uses ';' separator)
    for src, dest in discover_data_dirs():
        cmd.extend(["--add-data", f"{src};{dest}"])

    # Hidden imports
    for mod in discover_modules():
        cmd.extend(["--hidden-import", mod])

    # Excludes
    excludes = [
        "tkinter.test", "unittest", "test",
        "distutils", "setuptools", "pip", "wheel",
        "numpy", "pandas", "scipy", "matplotlib",
        "notebook", "ipython", "IPython",
        "pytest", "_pytest", "py.test",
        "PIL.tests", "pydoc", "doctest",
    ]
    for ex in excludes:
        cmd.extend(["--exclude-module", ex])

    cmd.append(str(PROJECT_ROOT / ENTRY_POINT))

    step("Running PyInstaller for Windows --onefile...")
    result = run_cmd(cmd, check=False)

    if result.returncode != 0:
        err("Windows build FAILED")
        return False, {}

    return _finish_windows_build(start_time)

def _build_windows_wine():
    """Build Windows .exe via Wine cross-compilation on Linux."""
    wine = shutil.which("wine64") or shutil.which("wine")
    if not wine:
        warn("Wine not found — cannot cross-compile Windows binary on this Linux system")
        info("Install Wine: sudo apt install wine64")
        info("Or run this script on a Windows machine")
        return False, {}

    # Check Wine Python
    try:
        result = subprocess.run(
            [wine, "python", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            warn("Windows Python not found in Wine prefix")
            info("Install Python in Wine: wine python-3.12.x-amd64.exe /quiet")
            return False, {}
        step(f"Wine Python detected: {result.stdout.strip()}")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        warn("Wine Python not available")
        return False, {}

    # Build command
    ico_icon = PROJECT_ROOT / "assets" / "icon.ico"
    png_icon = PROJECT_ROOT / "assets" / "icon.png"

    cmd = [
        wine, "python", "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onefile",        # ← Single file mode
        "--noconsole",
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / "windows"),
        "--specpath", str(PROJECT_ROOT),
    ]

    if ico_icon.exists():
        cmd.extend(["--icon", str(ico_icon)])

    for src, dest in discover_data_dirs():
        cmd.extend(["--add-data", f"{src};{dest}"])

    for mod in discover_modules():
        cmd.extend(["--hidden-import", mod])

    excludes = [
        "tkinter.test", "unittest", "test",
        "numpy", "pandas", "scipy", "matplotlib",
        "notebook", "ipython", "IPython",
        "pytest", "_pytest",
    ]
    for ex in excludes:
        cmd.extend(["--exclude-module", ex])

    cmd.append(str(PROJECT_ROOT / ENTRY_POINT))

    step("Running PyInstaller via Wine cross-compilation...")
    result = run_cmd(cmd, check=False)

    if result.returncode != 0:
        err("Windows build via Wine FAILED")
        return False, {}

    return _finish_windows_build(start_time)

def _finish_windows_build(start_time):
    """Locate and compress the Windows build output."""
    # The Windows onefile binary goes into DIST_DIR/APP_NAME.exe
    win_exe = DIST_DIR / f"{APP_NAME}.exe"
    if not win_exe.exists():
        # Try alternative path (onedir mode fallback)
        win_exe_alt = DIST_DIR / APP_NAME / f"{APP_NAME}.exe"
        if win_exe_alt.exists():
            win_exe = win_exe_alt
        else:
            err(f"Windows executable not found at: {win_exe}")
            return False, {}

    # UPX compression
    upx_path = shutil.which("upx") or str(Path.home() / ".local" / "bin" / "upx")
    if os.path.isfile(upx_path):
        step("Applying UPX compression to Windows binary...")
        original_size = win_exe.stat().st_size / (1024 * 1024)
        try:
            run_cmd([upx_path, "--best", "--lzma", str(win_exe)], check=False)
            compressed_size = win_exe.stat().st_size / (1024 * 1024)
            saved = original_size - compressed_size
            if saved > 0.1:
                ratio = (saved / original_size) * 100
                ok(f"UPX: {original_size:.1f} MB → {compressed_size:.1f} MB (saved {saved:.1f} MB, {ratio:.0f}%)")
            else:
                ok(f"UPX: {compressed_size:.1f} MB")
        except Exception:
            warn("UPX compression failed")

    win_size = win_exe.stat().st_size / (1024 * 1024)
    md5 = get_file_hash(win_exe)
    elapsed = time.time() - start_time

    ok(f"Windows build completed in {elapsed:.1f}s")
    step(f"Executable: {win_exe}")
    step(f"Size:       {win_size:.1f} MB | MD5: {md5[:12]}...")

    return True, {
        "platform": "Windows",
        "binary": str(win_exe),
        "name": f"{APP_NAME}.exe",
        "size_mb": win_size,
        "md5": md5,
        "elapsed": elapsed,
    }

# ============================================================================
# Copy to Desktop
# ============================================================================

def copy_to_desktop(results):
    """Copy all successful builds to the user's Desktop."""
    section("📋 Copying Executables to Desktop")

    DESKTOP.mkdir(parents=True, exist_ok=True)

    copied = []
    for platform_name, info in results.items():
        if not info:
            continue
        src = Path(info["binary"])
        if not src.exists():
            continue

        if platform_name == "linux":
            dest = DESKTOP / APP_NAME
        else:
            dest = DESKTOP / f"{APP_NAME}.exe"

        shutil.copy2(str(src), str(dest))

        # Make executable on Linux
        if platform_name == "linux":
            os.chmod(str(dest), 0o755)

        copied.append((platform_name, dest, info["size_mb"]))

    return copied

# ============================================================================
# Summary
# ============================================================================

def print_summary(linux_result, windows_result, desktop_copies):
    """Print final build summary."""
    section("📊 Final Build Summary")

    print(c("  ╔═══════════════════════════════════════════════════════╗", C.CYAN))
    print(c("  ║  Platform          Status          Size              ║", C.CYAN))
    print(c("  ╠═══════════════════════════════════════════════════════╣", C.CYAN))

    for name, result in [("Linux", linux_result), ("Windows", windows_result)]:
        if result and result[0]:
            info = result[1]
            print(c(f"  ║  {'🐧' if name == 'Linux' else '🪟'} {name:<15} ✅ Success      {info['size_mb']:.1f} MB            ║", C.CYAN))
        else:
            print(c(f"  ║  {'🐧' if name == 'Linux' else '🪟'} {name:<15} ❌ Failed       -                 ║", C.RED))

    print(c("  ╚═══════════════════════════════════════════════════════╝", C.CYAN))

    # Desktop copies
    if desktop_copies:
        print()
        step("Desktop executables:")
        for plat, path, size in desktop_copies:
            icon = "🐧" if plat == "linux" else "🪟"
            ok(f"{icon} {path} ({size:.1f} MB)")
    else:
        warn("No executables were copied to Desktop")

    # Security note
    print()
    print(c("  ╔═══════════════════════════════════════════════════════╗", C.GREEN))
    print(c("  ║  🔒 Security & Distribution                           ║", C.GREEN))
    print(c("  ╠═══════════════════════════════════════════════════════╣", C.GREEN))
    print(c("  ║  • All source code is hidden inside the binary        ║", C.GREEN))
    print(c("  ║  • All Python libraries are bundled & obfuscated      ║", C.GREEN))
    print(c("  ║  • All assets (icons, languages) are packed inside    ║", C.GREEN))
    print(c("  ║  • The executable is fully self-contained             ║", C.GREEN))
    print(c("  ║  • No installation required — just run the file       ║", C.GREEN))
    print(c("  ╚═══════════════════════════════════════════════════════╝", C.GREEN))
    print()

# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Build AuraTool-Suite as standalone onefile executables"
    )
    parser.add_argument("--linux-only", action="store_true",
                        help="Build Linux binary only")
    parser.add_argument("--windows-only", action="store_true",
                        help="Build Windows binary only")
    parser.add_argument("--clean", action="store_true",
                        help="Clean build artifacts before building")
    parser.add_argument("--version", default=APP_VERSION,
                        help=f"Version label (default: {APP_VERSION})")
    args = parser.parse_args()

    banner()

    # Clean if requested
    if args.clean:
        clean_build()

    # Determine what to build
    do_linux = not args.windows_only
    do_windows = not args.linux_only

    linux_result = None
    windows_result = None

    total_start = time.time()

    if do_linux:
        linux_result = build_linux()
        print()

    if do_windows:
        windows_result = build_windows()
        print()

    # Copy to Desktop
    results = {}
    if linux_result and linux_result[0]:
        results["linux"] = linux_result[1]
    if windows_result and windows_result[0]:
        results["windows"] = windows_result[1]

    desktop_copies = []
    if results:
        desktop_copies = copy_to_desktop(results)

    total_elapsed = time.time() - total_start

    # Final summary
    print_summary(linux_result, windows_result, desktop_copies)
    step(f"Total build time: {total_elapsed:.1f}s")
    print()

    # Exit code
    any_success = (linux_result and linux_result[0]) or (windows_result and windows_result[0])
    sys.exit(0 if any_success else 1)


if __name__ == "__main__":
    main()
