#!/usr/bin/env python3
"""
AuraTool-Suite — Dual-Platform Build Script
=============================================
Compiles native Linux and Windows executables from a single Ubuntu machine.

Features:
  - Auto-discovers all Python modules in core/, modules/, drivers/
  - Builds native Linux binary (--onefile)
  - Cross-compiles Windows .exe via Wine + Windows Python
  - Optional fallback to PyInstaller --cross-compile if available
  - Collects all data dirs (languages, assets, etc.)
  - Organizes all output into release_output/ for clean distribution
  - Validates builds and reports sizes

Usage:
    python build.py                 # Build both platforms
    python build.py --linux-only    # Linux only
    python build.py --windows-only  # Windows only
    python build.py --clean-only    # Clean artifacts only
    python build.py --skip-windows  # Linux + skip Wine attempt

Requirements:
    pip install pyinstaller
    sudo apt install wine64          # For Windows cross-compilation
"""

import glob
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Project Layout
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.join(PROJECT_ROOT, "release_output")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")

APP_NAME = "AuraTool-Suite"

# ---------------------------------------------------------------------------
# Auto-Discover Modules & Hidden Imports
# ---------------------------------------------------------------------------

# Directories that contain importable Python packages
PACKAGE_DIRS = ["core", "modules", "drivers", "ui"]

# Top-level Python scripts that should be bundled
TOP_LEVEL_SCRIPTS = ["auratool_factory"]


def discover_packages(base_dirs: list[str]) -> list[str]:
    """
    Walk each package directory and return fully-qualified module paths
    for every .py file found (excluding __pycache__).
    """
    modules = []
    for base in base_dirs:
        pkg_path = os.path.join(PROJECT_ROOT, base)
        if not os.path.isdir(pkg_path):
            continue
        # The package itself
        modules.append(base)
        for root, dirs, files in os.walk(pkg_path):
            # Skip __pycache__ and hidden dirs
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
    """
    Build the complete list of hidden imports by scanning the project.
    This ensures PyInstaller bundles every module even if not directly
    imported in the entry point chain.
    """
    discovered = discover_packages(PACKAGE_DIRS)
    for script in TOP_LEVEL_SCRIPTS:
        if os.path.isfile(os.path.join(PROJECT_ROOT, f"{script}.py")):
            discovered.append(script)
    # Deduplicate while preserving order
    seen = set()
    result = []
    for m in discovered:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


# ---------------------------------------------------------------------------
# Entry Point Detection
# ---------------------------------------------------------------------------

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
    print("[FATAL] No entry point found. Expected main.py, ui/app.py, or auratool_factory.py")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Data Directories to Bundle
# ---------------------------------------------------------------------------

def get_data_dirs() -> list[tuple[str, str]]:
    """
    Returns (source, dest) pairs for --add-data.
    Only includes directories that actually exist.
    """
    dirs = [
        ("languages", "languages"),
        ("ui", "ui"),
        ("assets", "assets"),
    ]
    result = []
    for src, dst in dirs:
        if os.path.isdir(os.path.join(PROJECT_ROOT, src)):
            result.append((src, dst))
    return result


# ---------------------------------------------------------------------------
# Build Helpers
# ---------------------------------------------------------------------------

def clean_build_artifacts():
    """Remove temporary build directories and spec files."""
    print("[*] Cleaning build artifacts...")
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
    print("[+] Clean complete.\n")


def ensure_pyinstaller():
    """Ensure PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"[*] PyInstaller {PyInstaller.__version__} ready.")
    except ImportError:
        print("[!] PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def ensure_wine():
    """
    Check for Wine and a Windows Python environment.
    Returns (wine_path, python_exe) or (None, None).
    """
    wine_path = shutil.which("wine64") or shutil.which("wine")
    if not wine_path:
        return None, None

    # Common Wine Python locations
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
        # Default Wine Python (if installed via wine python3-pip)
        os.path.join(home, ".wine/drive_c/windows/syswow64/python3.exe"),
    ]
    for py in candidates:
        if os.path.isfile(py):
            return wine_path, py

    # Fallback: try "wine python --version"
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


def dir_size_mb(path: str) -> float:
    """Return total directory size in MB."""
    total = 0
    for dp, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total / (1024 * 1024)


# ---------------------------------------------------------------------------
# Linux Native Build
# ---------------------------------------------------------------------------

def build_linux(entry_point: str, hidden_imports: list[str]) -> bool:
    """Build native Linux --onefile binary."""
    print("=" * 60)
    print("  BUILDING: Native Linux Binary (--onefile)")
    print("=" * 60)
    ensure_pyinstaller()

    binary_name = APP_NAME
    output_path = os.path.join(RELEASE_DIR, binary_name)

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

    # Add data directories
    separator = ";" if platform.system() == "Windows" else ":"
    for src, dst in get_data_dirs():
        cmd.append(f"--add-data={src}{separator}{dst}")

    # Add hidden imports
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Strip debug symbols on Linux for smaller binary
    if platform.system() != "Windows":
        cmd.append("--strip")

    cmd.append(entry_point)

    print(f"[*] Entry point: {entry_point}")
    print(f"[*] Output:      {output_path}")
    print(f"[*] Modules:     {len(hidden_imports)} hidden imports")
    print(f"[*] Data dirs:   {len(get_data_dirs())}")
    print()

    start = time.time()
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.time() - start

    if res.returncode == 0 and os.path.isfile(output_path):
        size = file_size_mb(output_path)
        print(f"\n[SUCCESS] Linux binary built in {elapsed:.1f}s")
        print(f"          {output_path} ({size:.1f} MB)")
        os.chmod(output_path, 0o755)
        return True
    else:
        print(f"\n[FAILED] Linux build failed (exit code {res.returncode})")
        return False


# ---------------------------------------------------------------------------
# Windows Cross-Compilation (Wine)
# ---------------------------------------------------------------------------

def build_windows_wine(entry_point: str, hidden_imports: list[str]) -> bool:
    """Build Windows .exe via Wine + Windows Python + PyInstaller."""
    print("=" * 60)
    print("  BUILDING: Windows .exe via Wine Cross-Compilation")
    print("=" * 60)

    wine_path, wine_python = ensure_wine()
    if not wine_python:
        print("[!] Wine or Windows Python not found.")
        print()
        print("  To install Wine + Python for cross-compilation:")
        print("    sudo dpkg --add-architecture i386")
        print("    sudo apt update")
        print("    sudo apt install wine64 wine32")
        print()
        print("  Then install Python inside Wine:")
        print("    wget https://www.python.org/ftp/python/3.12.5/python-3.12.5-amd64.exe")
        print("    wine python-3.12.5-amd64.exe /quiet InstallAllUsers=1 PrependPath=1")
        print()
        print("  Then install PyInstaller in Wine Python:")
        print("    wine python -m pip install pyinstaller")
        print()
        return False

    print(f"[*] Wine:      {wine_path}")
    print(f"[*] Python:    {wine_python}")

    binary_name = f"{APP_NAME}.exe"
    output_path = os.path.join(RELEASE_DIR, binary_name)

    # Build PyInstaller command for Windows
    # Use ; as path separator (Windows convention)
    separator = ";"

    cmd = [wine_path, wine_python, "-m", "PyInstaller",
           "--onefile", "--noconfirm", "--clean",
           f"--name={binary_name}",
           f"--distpath={RELEASE_DIR}",
           f"--workpath={BUILD_DIR}",
           f"--specpath={BUILD_DIR}",
           ]

    # Add data directories (Windows path separators handled by Wine)
    for src, dst in get_data_dirs():
        cmd.append(f"--add-data={src}{separator}{dst}")

    # Add hidden imports
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    cmd.append(entry_point)

    print(f"[*] Entry point: {entry_point}")
    print(f"[*] Output:      {output_path}")
    print()

    start = time.time()
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.time() - start

    if res.returncode == 0 and os.path.isfile(output_path):
        size = file_size_mb(output_path)
        print(f"\n[SUCCESS] Windows .exe built in {elapsed:.1f}s")
        print(f"          {output_path} ({size:.1f} MB)")
        return True
    else:
        print(f"\n[FAILED] Windows build failed (exit code {res.returncode})")
        return False


# ---------------------------------------------------------------------------
# Release Validation
# ---------------------------------------------------------------------------

def validate_release():
    """Check that release_output/ has the expected binaries and report sizes."""
    print("\n" + "=" * 60)
    print("  RELEASE VALIDATION")
    print("=" * 60)

    if not os.path.isdir(RELEASE_DIR):
        print("[!] release_output/ directory not found — no builds completed.")
        return

    files = sorted(os.listdir(RELEASE_DIR))
    # Filter out PyInstaller temp dirs and spec files
    binaries = [f for f in files if not f.endswith(".spec") and f != "__pycache__"]

    if not binaries:
        print("[!] No binaries found in release_output/")
        return

    print(f"\n  {'File':<40} {'Size':>10}  {'Platform'}")
    print("  " + "-" * 65)

    for name in binaries:
        path = os.path.join(RELEASE_DIR, name)
        if os.path.isfile(path):
            size = file_size_mb(path)
            platform_label = "Linux" if not name.endswith(".exe") else "Windows"
            print(f"  {name:<40} {size:>8.1f} MB  {platform_label}")
        elif os.path.isdir(path):
            size = dir_size_mb(path)
            print(f"  {name + '/':<40} {size:>8.1f} MB  (directory)")

    total = dir_size_mb(RELEASE_DIR)
    print(f"\n  Total release size: {total:.1f} MB")
    print(f"  Output directory:   {RELEASE_DIR}")
    print()


# ---------------------------------------------------------------------------
# Main Build Orchestrator
# ---------------------------------------------------------------------------

def parse_args():
    """Parse command-line arguments."""
    args = {
        "linux_only": False,
        "windows_only": False,
        "skip_windows": False,
        "clean_only": False,
    }

    for arg in sys.argv[1:]:
        arg_lower = arg.lower().strip("-")
        if arg_lower == "linux-only":
            args["linux_only"] = True
        elif arg_lower == "windows-only":
            args["windows_only"] = True
        elif arg_lower == "skip-windows":
            args["skip_windows"] = True
        elif arg_lower == "clean-only":
            args["clean_only"] = True
        elif arg_lower == "help" or arg_lower == "h":
            print(__doc__)
            sys.exit(0)

    return args


def build_all():
    """Main build workflow."""
    args = parse_args()

    print("╔" + "═" * 58 + "╗")
    print("║  AuraTool-Suite — Dual-Platform Build System              ║")
    print("║  Linux (Ubuntu) + Windows (.exe via Wine)                ║")
    print("╚" + "═" * 58 + "╝")
    print()

    # Step 1: Clean
    clean_build_artifacts()
    os.makedirs(RELEASE_DIR, exist_ok=True)

    if args["clean_only"]:
        print("[+] Clean-only mode. Artifacts removed.")
        return

    # Step 2: Discover modules
    hidden_imports = get_all_hidden_imports()
    entry_point = get_entry_point()

    print(f"[*] Project root:    {PROJECT_ROOT}")
    print(f"[*] Entry point:     {entry_point}")
    print(f"[*] Release dir:     {RELEASE_DIR}")
    print(f"[*] Discovered:      {len(hidden_imports)} modules")
    print(f"[*] Data dirs:       {get_data_dirs()}")
    print(f"[*] Platform:        {platform.system()} {platform.machine()}")
    print()

    # Step 3: Build
    linux_ok = False
    windows_ok = False

    if not args["windows_only"]:
        linux_ok = build_linux(entry_point, hidden_imports)

    if not args["linux_only"] and not args["skip_windows"]:
        windows_ok = build_windows_wine(entry_point, hidden_imports)

    # Step 4: Clean temp files (keep release_output)
    clean_build_artifacts()

    # Step 5: Validate and report
    validate_release()

    # Summary
    print("=" * 60)
    print("  BUILD SUMMARY")
    print("=" * 60)
    print(f"  Linux Binary  ({APP_NAME})       : {'✅ SUCCESS' if linux_ok else '⏭️  SKIPPED/FAILED'}")
    print(f"  Windows EXE   ({APP_NAME}.exe)   : {'✅ SUCCESS' if windows_ok else '⏭️  SKIPPED/FAILED'}")
    print(f"  Release Directory: {RELEASE_DIR}")
    print("=" * 60)

    # Exit with error if both failed
    if not linux_ok and not windows_ok and not args["skip_windows"]:
        print("\n[!] Both builds failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    build_all()
