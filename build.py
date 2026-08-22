import os
import platform
import subprocess
import sys

def build_executable():
    """Builds a standalone executable using PyInstaller."""
    print("[*] Starting AuraTool-Suite compilation process...")
    
    os_type = platform.system()
    entry_point = "main.py"
    app_name = "AuraTool-Suite"

    pyinstaller_args = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--name={app_name}",
        "--add-data=core:core",
        "--add-data=modules:modules",
        "--add-data=drivers:drivers",
        "--add-data=ui:ui",
        entry_point
    ]

    # Adjust path separator for Windows vs Posix data bindings
    if os_type == "Windows":
        pyinstaller_args[6] = "--add-data=core;core"
        pyinstaller_args[7] = "--add-data=modules;modules"
        pyinstaller_args[8] = "--add-data=drivers;drivers"
        pyinstaller_args[9] = "--add-data=ui;ui"

    print(f"[*] Executing PyInstaller command for {os_type}:")
    print(" ".join(pyinstaller_args))

    try:
        subprocess.check_call(pyinstaller_args)
        print(f"\n[+] Build successfully completed! Binary output located in dist/{app_name}/")
    except subprocess.CalledProcessError as e:
        print(f"\n[-] Build failed with error code: {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    build_executable()
